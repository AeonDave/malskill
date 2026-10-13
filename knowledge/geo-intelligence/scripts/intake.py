#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""Steps 0–3 of geolocation in one command: metadata, zoomed four edges and four corners, search variants, OCR, reverse image search, run in parallel, one report.

Outputs (all in --out-dir):
  exif.json (meta.py --json digest)  edges/  variants/  ocr.json ocr.png  rev/<name>_<engine>.png + .json  intake.md  intake.json
intake.md is for humans (and the LLM): metadata, OCR text, Baidu similar images (count, source sites, numbered contact sheet rev/<name>_baidu_similar.jpg),
tiered vote count of image-search tags, suspected residential compound / housing development / hotel names, results on an AI-image gallery
(assets/data/ai_hosts.json, intake.json ai_gallery_hits), list of outputs, items skipped and failed.
Always open the image-search screenshots and the similar-image contact sheets; "searched, nothing found" and "not searched" are written separately in the report.

  intake.py photo.jpg --out-dir intake/ [--box x0,y0,x1,y1 ...] [--engines baidu,yandex] [--exclude word1,word2]
            [--no-rev] [--no-ocr] [--max-variants 4]

Examples:
  intake.py photo.jpg --out-dir intake/
  intake.py photo.jpg --out-dir intake/ --exclude 网络迷踪,<creator name>   # blind tests: exclude walkthrough posts (网络迷踪 = photo geolocation)
  intake.py photo.jpg --out-dir rev_crop/ --box 300,120,900,760            # after recon: only the tight crop is searched
  intake.py photo.jpg --out-dir intake/ --no-rev                           # only metadata, edge crops, OCR (under 30 seconds)
"""
from __future__ import annotations

import argparse
from geolib.net import PROXY_HELP
import itertools
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

from geolib.paths import DATA_DIR

HERE = Path(__file__).parent
AI_HOSTS = tuple(json.loads((DATA_DIR / "ai_hosts.json").read_text(encoding="utf-8"))["hosts"])
# uv run writes its own path into the UV env var: call child scripts with it, so uv is found even when it isn't on PATH (e.g. just installed, terminal not reopened)
UV = os.environ.get("UV") or "uv"
CITY_SUFFIX = ("省", "市", "区", "县", "州", "盟", "旗", "国", "府", "道", "自治区", "特别行政区", "City", "Province", "County", "Prefecture")
PLACE_WORDS = ("公园", "大厦", "小区", "花园", "广场", "学校", "中学", "小学", "大学", "酒店", "宾馆", "景区", "寺", "塔", "桥", "大楼",
               "中心", "村", "镇", "街", "路", "湖", "山", "站", "港", "码头", "厂", "园", "苑", "府", "城", "馆", "庙", "教堂", "Park",
               "Tower", "Hotel", "Bridge", "Station", "Square", "Plaza", "Church", "Temple", "Mall", "Street", "Road", "Avenue")
KNOWN_CITIES = ("北京", "上海", "天津", "重庆", "广州", "深圳", "成都", "杭州", "武汉", "西安", "南京", "苏州", "郑州", "长沙", "青岛", "沈阳",
                "大连", "厦门", "福州", "济南", "合肥", "昆明", "贵阳", "南宁", "哈尔滨", "长春", "石家庄", "太原", "兰州", "乌鲁木齐", "拉萨",
                "呼和浩特", "银川", "西宁", "海口", "三亚", "宁波", "无锡", "东莞", "佛山", "珠海", "香港", "澳门", "台北", "东京", "大阪", "首尔",
                "曼谷", "新加坡", "吉隆坡", "伦敦", "巴黎", "纽约", "洛杉矶", "悉尼", "墨尔本", "温哥华", "多伦多", "莫斯科", "柏林", "罗马", "马德里")


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 900) -> tuple[int, str, str]:
    try:
        # Child scripts and this one both use UTF-8: Chinese Windows reads and writes GBK by default, and if the two sides differ you get mojibake or crashes
        r = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace", capture_output=True, cwd=cwd, timeout=timeout,
                           env={**os.environ, "PYTHONUTF8": "1"})
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"


def _script(name: str) -> str:
    return str(HERE / name)


GENERIC = ("城市街道", "城市", "街道", "市区", "街景", "建筑", "楼房", "高楼", "夜景", "风景", "天空", "道路", "马路", "小镇", "乡村", "都市",
           "city", "street", "town", "building", "skyline", "road", "urban")
KNOWN_CITIES_EN = ("hong kong", "kowloon", "tokyo", "osaka", "kyoto", "seoul", "bangkok", "singapore", "kuala lumpur", "taipei", "shanghai",
                   "beijing", "shenzhen", "guangzhou", "chengdu", "chongqing", "london", "paris", "new york", "los angeles", "sydney",
                   "melbourne", "vancouver", "toronto", "moscow", "berlin", "rome", "madrid", "dubai", "istanbul", "mumbai", "delhi",
                   "hanoi", "ho chi minh", "manila", "jakarta", "macau", "lisbon", "barcelona", "amsterdam", "prague", "vienna", "cairo")


def _classify(tag: str) -> str:
    t = tag.strip("：: ，,。.")
    low = t.lower()
    if low in GENERIC or t in GENERIC:
        return "other"
    if any(c in low for c in KNOWN_CITIES_EN):
        return "city"
    if any(c in t for c in KNOWN_CITIES):
        return "city"
    if len(t) >= 3 and any(t.endswith(s) for s in CITY_SUFFIX) and not any(g in t for g in ("街道", "城市")):
        return "city"
    if any(w in t for w in PLACE_WORDS):
        return "place"
    return "other"


def _ai_host(url: str, site: str) -> str | None:
    """The AI-gallery host a result link sits on (suffix match on the URL's host, else on the site label), or None. A scraped
    string with an unbalanced '[' or ']' makes urlsplit raise ValueError: no host, never a crash that loses the whole search."""
    try:
        host = (urlparse(url).hostname or urlparse("//" + site.strip()).hostname or "").lower()
    except ValueError:
        return None
    return next((h for h in AI_HOSTS if host == h or host.endswith("." + h)), None)


def _collect_rev(rev_dir: Path, only: set[str] | None = None) -> tuple[list[dict], dict, list[dict]]:
    """Read revimg's .json files (only the names in `only`, when given): guess/links for each image and engine, the tiered
    vote count, and the results that sit on an AI-image gallery (every link and similar-image source, not only the ones shown)."""
    entries, hits, seen = [], [], set()
    for jf in sorted(rev_dir.glob("*.json")):
        if only is not None and jf.name not in only:
            continue
        try:
            d = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        m = re.match(r"(.+)_(baidu|yandex|bing|baiduimg|sogouimg)$", jf.stem)
        if not m:
            continue
        simi = d.get("similar") or []
        for url, site in [(x.get("url") or "", x.get("site") or "") for x in d.get("links") or []] + \
                         [(x.get("from") or "", x.get("site") or "") for x in simi]:
            host = _ai_host(url, site)
            if host and url not in seen:
                seen.add(url)
                hits.append({"site": host, "url": url})
        entries.append({"variant": m.group(1), "engine": m.group(2), "guess": d.get("guess") or [], "links": (d.get("links") or [])[:8],
                        "error": d.get("error"), "refused": bool(d.get("refused")), "shot": str(jf.with_suffix(".png").name),
                        "json": jf.name, "similar_n": len(simi), "similar_sites": Counter(x.get("site") or "?" for x in simi).most_common(),
                        "similar_sheet": Path(d["similar_sheet"]).name if d.get("similar_sheet") else None,
                        "similar_note": d.get("similar_sheet_note")})
    votes: dict = {"city": {}, "place": {}}
    for e in entries:
        seen_city = set()
        for g in e["guess"]:
            body = re.sub(r"^(图中可能是|Image appears to contain)[：:]?", "", g).strip()
            for tag in re.split(r"[、/，,;；|]", body):
                tag = tag.strip()
                if len(tag) < 2:
                    continue
                k = _classify(tag)
                if k == "city":
                    key = tag
                    if (e["engine"], key) in seen_city:      # several variants from one engine naming the same city count as one vote
                        continue
                    seen_city.add((e["engine"], key))
                    votes["city"].setdefault(key, set()).add(e["engine"])
                elif k == "place":
                    votes["place"].setdefault(tag, set()).add(f"{e['engine']}/{e['variant']}")
    return entries, {k: {t: sorted(v) for t, v in d.items()} for k, d in votes.items()}, hits


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--box", action="append", help="x0,y0,x1,y1: search only this tight crop (the full frame is searched by recon "
                                                       "or a run without --box); repeatable")
    ap.add_argument("--engines", default="baidu,yandex")
    ap.add_argument("--exclude", help="words to exclude from reverse image search results (for blind tests)")
    ap.add_argument("--no-rev", action="store_true")
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--max-variants", type=int, default=4,
                    help="max number of variants each engine searches (plus the original when there is no --box)")
    ap.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)
    args = ap.parse_args()

    photo = Path(args.photo).resolve()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    if not args.box:
        (out / "edges").mkdir(exist_ok=True)
    (out / "variants").mkdir(exist_ok=True)
    t_all = time.time()
    timings: dict = {}
    status: dict = {}
    variant_files: list[Path] = []

    def timed(name, fn):
        t0 = time.time()
        try:
            res = fn()
            status[name] = "ok" if res[0] == 0 else f"failed: {(res[2] or res[1])[-300:].strip()}"
        except Exception as e:  # noqa: BLE001
            status[name] = f"exception: {e}"
            res = (1, "", str(e))
        timings[name] = round(time.time() - t0, 1)
        return res

    def exif():
        return _run([UV, "run", _script("meta.py"), str(photo), "--json"])

    def edges():
        return _run([UV, "run", _script("imgprep.py"), "edges", str(photo), "--out-dir", str(out / "edges")])

    def variants():
        prep = [UV, "run", _script("imgprep.py"), "variants", str(photo), "--out-dir", str(out / "variants")]
        calls = ([prep + ["--box", b, "--prefix", f"box{i}"] for i, b in enumerate(args.box, 1)] if args.box
                 else [prep + ["--prefix", "full"]])
        res = [_run(c) for c in calls]
        for rc, stdout, _ in res:
            if rc == 0:
                variant_files.extend(p for line in stdout.splitlines()
                                     if (p := Path(line.strip())).suffix.lower() in (".jpg", ".png")
                                     and p.is_file() and p.resolve().parent == (out / "variants").resolve())
        return max(r[0] for r in res), "".join(r[1] for r in res), "".join(r[2] for r in res)

    def ocr():
        return _run([UV, "run", _script("ocr.py"), str(photo), "--out", str(out / "ocr.json"), "--draw", str(out / "ocr.png")])

    # Batch 1: metadata, edges, variants, OCR in parallel; --box: crop variants only, the full frame's edges and variants are recon's
    with ThreadPoolExecutor(4) as ex:
        f_exif = ex.submit(timed, "exif", exif)
        f_edges = None if args.box else ex.submit(timed, "edges", edges)
        f_var = ex.submit(timed, "variants", variants)
        f_ocr = None if args.no_ocr else ex.submit(timed, "ocr", ocr)
        exif_res = f_exif.result()
        if f_edges:
            f_edges.result()
        f_var.result()
        if f_ocr:
            f_ocr.result()
    try:
        exif_json = json.loads(exif_res[1].strip().splitlines()[0]) if exif_res[1].strip() else {}
    except Exception:  # noqa: BLE001
        exif_json = {"raw": exif_res[1][:500]}
    (out / "exif.json").write_text(json.dumps(exif_json, ensure_ascii=False, indent=1), encoding="utf-8")

    # Batch 2: reverse image search, two engines in parallel, each searches the original (not with --box: recon searched it)
    # + up to max-variants variants
    rev_dir = out / "rev"
    entries, votes, hits = [], {"city": {}, "place": {}}, []
    if not args.no_rev:
        rev_dir.mkdir(exist_ok=True)
        # the report holds only the results this call's searches write (new or rewritten files): a rerun in the same folder,
        # e.g. --box after a full run, leaves the older results on disk as evidence, outside this report
        before = {p.name: p.stat().st_mtime_ns for p in rev_dir.glob("*.json")}
        var_files = sorted(variant_files)     # only this call's successful preparation, never earlier crops or failed outputs
        if args.box:                    # boxes share the slots round-robin, each box's crop first
            groups = [sorted(f for f in var_files if f.stem.startswith(f"box{i}_")) for i in range(1, len(args.box) + 1)]
            prefer = [f for tier in itertools.zip_longest(*groups) for f in tier if f]
        else:
            prefer = [f for f in var_files if any(k in f.stem for k in ("crop", "flip", "box"))] + [f for f in var_files if not any(k in f.stem for k in ("crop", "flip", "box"))]
        images = ([] if args.box else [str(photo)]) + [str(f) for f in prefer[: args.max_variants]]

        def rev(engine):
            cmd = [UV, "run", _script("revimg.py"), *images, "--out-dir", str(rev_dir), "--engines", engine]
            if args.exclude:
                cmd += ["--exclude", args.exclude]
            if args.proxy:
                cmd += ["--proxy", args.proxy]
            return _run(cmd, timeout=900)

        engines = [e for e in args.engines.split(",") if e]
        if images:
            with ThreadPoolExecutor(2) as ex:
                futs = {eng: ex.submit(timed, f"rev-{eng}", (lambda e=eng: (lambda: rev(e)))()) for eng in engines}
                for eng, f in futs.items():
                    f.result()
        else:
            status.update({f"rev-{eng}": "not run: no crop variants prepared" for eng in engines})
        written = {p.name for p in rev_dir.glob("*.json") if before.get(p.name) != p.stat().st_mtime_ns}
        entries, votes, hits = _collect_rev(rev_dir, written)

    ocr_items = []
    if (out / "ocr.json").exists():
        try:
            ocr_items = json.loads((out / "ocr.json").read_text(encoding="utf-8")).get("items", [])
        except Exception:  # noqa: BLE001
            pass

    # ---- report
    L = [f"# Steps 0–3 report: {photo.name}", "", f"Total time {time.time() - t_all:.0f}s; per step: " + ", ".join(f"{k} {v}s" for k, v in timings.items()), "",
         "Next: record clues on board.py (`clue`), lookup clues with `apply`; list the candidates in full first (`children`), then rank.", ""]
    L += ["## Metadata", ""]
    gps = exif_json.get("gps")
    if exif_json and (gps or (exif_json.get("time") or {}).get("DateTimeOriginal")):
        shown = {k: exif_json[k] for k in ("gps", "time", "optics", "camera", "notice") if exif_json.get(k)} or exif_json
        L.append("```\n" + json.dumps(shown, ensure_ascii=False, indent=1)[:1500] + "\n```")
        L.append("Metadata is an assumption (it can be edited, it can be stripped): check both GPS and time against the image.")
    else:
        L.append("No metadata (common for forwarded images, screenshots, rephotographed images)." + (f" Raw output: `{json.dumps(exif_json, ensure_ascii=False)[:300]}`" if exif_json else ""))
    L += ["", "## OCR text (second reader; pass=up/tile was only read after zooming, treat it as an assumption)", ""]
    if args.no_ocr:
        L.append("Not done (--no-ocr).")
    elif ocr_items:
        L.append("| Conf | Pass | Box (px) | Text |")
        L.append("|---|---|---|---|")
        for t in ocr_items[:40]:
            L.append(f"| {t['conf']:.2f} | {t['pass']} | {t['box']} | {t['text']} |")
        L.append("")
        L.append("Phone numbers, plates, proper names on road signs, issuing authorities: first `clues.py lookup`, then `board.py apply`.")
    else:
        L.append("No text read" + (f" (OCR {status.get('ocr')})" if status.get("ocr") != "ok" else ". Maybe there really is no text, or it's too small: zoom in by hand with imgprep.py zoom and look again"))
    L += ["", "## Reverse image search", ""]
    if args.no_rev:
        L.append("Not done (--no-rev). This is not \"searched, nothing found\".")
    else:
        for eng in args.engines.split(","):
            st = status.get(f"rev-{eng}", "not run")
            L.append(f"- {eng}: {st}")
        if hits:
            L.append("- **AI-gallery host: open and compare (a host alone only down-weights)**: "
                     + "; ".join(f"{h['site']} {h['url'][:100]}" for h in hits[:8]))
        refused = [e for e in entries if e["error"] or e["refused"]]
        if refused:
            L.append("- Items the engine refused or failed (not the same as nothing found): " + ", ".join(f"{e['variant']}/{e['engine']}: {e['error'] or 'refused'}" for e in refused))
        L.append("")
        baidu = sorted([e for e in entries if e["engine"] == "baidu"], key=lambda e: e["variant"] != photo.stem)
        if baidu:
            L.append("### Similar images (Baidu; open the contact sheet first)")
            L.append("")
            L.append("A near-duplicate photo is the fastest route to a location: the same object or scene has often been photographed by others and posted on Dianping, Douyin, Xiaohongshu, and the source page's shop name, scenic-area name or location tag gives the place directly. "
                     "Open the contact sheet and compare each cell with the query image in the top-left corner on **fixed features** (shapes of structural parts, soot and damage, the mountains/buildings/bridges/pylons behind); merely the same kind of object doesn't count. "
                     "For a near-duplicate: number i is `similar[i]` in that image's JSON, `from` is the source page, `site` is the site; look through the other images on the same source page too. "
                     "For sources that need a login, don't log in and don't bypass verification; instead do a keyword search from image features + site type. "
                     + ("Only the --box crops were searched here (recon or a run without --box searched the full frame); compare each crop's sheet with the crop."
                        if args.box else "Look at the original image's sheet first; look at the variants' sheets only if the original's has no near-duplicate."))
            L.append("")
            for e in baidu:
                head = f"**{e['variant']}**: "
                if e["error"]:
                    L.append(f"- {head}Baidu error ({e['error'][:80]}), no similar images captured; doesn't count as searched with nothing found")
                elif not e["similar_n"]:
                    L.append(f"- {head}no similar images captured (Baidu returned none, or the page layout changed); open the screenshot `rev/{e['shot']}` and check for a \"相似图片\" (similar images) section")
                else:
                    sites = ", ".join(f"{s} {n}" for s, n in e["similar_sites"][:8])
                    sheet = f"contact sheet `rev/{e['similar_sheet']}` (first {min(24, e['similar_n'])})" if e["similar_sheet"] else "no contact sheet"
                    note = f"; {e['similar_note']}" if e["similar_note"] else ""
                    L.append(f"- {head}{e['similar_n']} images ({sites}); {sheet}{note}; source list in `similar` of `rev/{e['json']}`")
            L.append("")
        L.append("### Tiered vote count (several variants from one engine naming the same city count as one vote; conflicting place labels don't cancel city votes)")
        L.append("")
        if votes["city"]:
            for t, engs in sorted(votes["city"].items(), key=lambda kv: -len(kv[1])):
                L.append(f"- City level **{t}**: {len(engs)} votes ({', '.join(engs)})")
        else:
            L.append("- City level: none")
        if votes["place"]:
            for t, srcs in sorted(votes["place"].items(), key=lambda kv: -len(kv[1])):
                L.append(f"- Label **{t}** (scene/object word or place name): {len(srcs)} times ({', '.join(srcs)}); if it is a proper name "
                         f"→ `poi.py \"{t}\" --city <city> --region <cc>`, list every same-name place, then verify")
        else:
            L.append("- Place-name labels: none")
        L.append("")
        L.append("### Each image, each engine")
        L.append("")
        for e in entries:
            L.append(f"**{e['variant']} / {e['engine']}** (screenshot `rev/{e['shot']}`, always open it)")
            if e["similar_sheet"]:
                L.append(f"- Similar images: {e['similar_n']}, contact sheet `rev/{e['similar_sheet']}` (see above)")
            for g in e["guess"]:
                L.append(f"- Tag: {g[:200]}")
            for ln in e["links"][:8]:
                L.append(f"- [{ln.get('site', '')}] {ln.get('title', '')[:80]} — {ln.get('url', '')[:100]}")
            L.append("")
    L += ["## Output files", "",
          None if args.box else f"- Edge crops: `edges/` ({len(list((out / 'edges').glob('*')))} images; look at the four edges and four corners one by one)",
          f"- Variants: `variants/` ({len(list((out / 'variants').glob('*')))} images)", "- OCR annotated image: `ocr.png`" if not args.no_ocr else "",
          f"- Image-search screenshots: `rev/` ({sum((rev_dir / e['shot']).is_file() for e in entries)} images)" if not args.no_rev else "",
          f"- Baidu similar-image contact sheets: `rev/*_baidu_similar.jpg` ({sum(bool(e['similar_sheet']) for e in entries)})" if not args.no_rev else "", "",
          "## Status", ""]
    for k, v in status.items():
        L.append(f"- {k}: {v}")
    (out / "intake.md").write_text("\n".join(x for x in L if x is not None), encoding="utf-8")
    (out / "intake.json").write_text(json.dumps({"photo": str(photo), "exif": exif_json, "ocr": ocr_items, "rev": entries, "votes": votes, "ai_gallery_hits": hits,
                                                 "status": status, "timings": timings}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(L[:6]))
    print(f"-> {out / 'intake.md'} (read this)")


if __name__ == "__main__":
    # Chinese Windows outputs GBK by default: it crashes on m², ñ, and Chinese text the agent reads comes out garbled
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
