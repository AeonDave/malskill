#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""One command for the whole first pass on a photo (reverse image search included; all pre-approved).

Runs in parallel and writes everything under --out-dir (default recon/):
  meta/      deep metadata, time-zone countries, filename/platform hints, embedded previews  (meta.py)
  intake/    edge and corner crops, search variants, OCR with automatic language detection, and
             Yandex + Baidu reverse image search on the original and variants                 (intake.py)
  textgeo.*  text → countries/regions/places: scripts, letters, phones, domains, brands, place names (textgeo.py)
  detect/    numbered crops of signs, plates, poles, bollards, markings, vehicles…          (detect.py)
  calib.*    field of view, pitch/roll, horizon line                                       (calib.py)
  prior/     learned world prior (StreetCLIP + GeoCLIP), self-assessed                       (prior.py)
  recon.md   one page summarising all of it — read this, then open the crops it lists

  recon.py original/photo.jpg                      # full pass (first run downloads models, later runs ~1 min)
  recon.py original/photo.jpg --no-ml              # metadata, crops, OCR, text and reverse search, no local models
  recon.py original/photo.jpg --no-rev             # everything except the reverse image search
  recon.py original/photo.jpg --skip detect,calib  # skip some steps

The tools do not replace your own read of the image: make your gut call first (SKILL.md, step 1), then use
this page to confirm, contradict or sharpen it.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
UV = os.environ.get("UV") or "uv"


def run(name: str, cmd: list[str], log: dict, timeout: int = 1800) -> int:
    t0 = time.time()
    try:
        r = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout,
                           env={**os.environ, "PYTHONUTF8": "1", "TOKENIZERS_PARALLELISM": "false"})
        rc, err, out = r.returncode, r.stderr, r.stdout
    except subprocess.TimeoutExpired:
        rc, err, out = 124, f"timed out after {timeout}s", ""
    log[name] = {"rc": rc, "seconds": round(time.time() - t0, 1),
                 "error": "" if rc == 0 else (err or out).strip()[-600:], "stdout_tail": out.strip()[-400:]}
    return rc


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def jload(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def summary(photo: Path, out: Path, log: dict, total: float, rev: bool) -> str:
    L = [f"# Recon: {photo.name}", "",
         f"First pass in {total:.0f}s (" + ", ".join(f"{k} {v['seconds']}s" + ("" if v["rc"] == 0 else " FAILED") for k, v in log.items()) + ").",
         ("Reverse image search ran on Yandex and Baidu (original + variants). " if rev else "Reverse image search skipped (--no-rev). ")
         + "Make (or revisit) your gut call, then use the evidence below to confirm, contradict or sharpen it.", ""]
    # metadata
    meta = jload(out / "meta" / "meta.json").get("digest", {})
    L += ["## Metadata", ""]
    if meta:
        g, t = meta.get("gps") or {}, meta.get("time") or {}
        if g.get("lat") is not None:
            L.append(f"- **GPS {g['lat']}, {g['lon']}** — a hypothesis until the scene confirms it (see meta/meta.md).")
        if t.get("utc_offset"):
            ccs = t.get("countries_with_this_offset_on_that_date", [])
            L.append(f"- UTC offset {t['utc_offset']} ({t.get('utc_offset_source')}): {len(ccs)} countries used it on that date "
                     f"({', '.join(ccs[:25])}{' …' if len(ccs) > 25 else ''}).")
        if t.get("DateTimeOriginal"):
            L.append(f"- Capture time (local clock): {t['DateTimeOriginal']}")
        for h in meta.get("filename_hints", []):
            L.append(f"- Filename: {h['pattern']}")
        if meta.get("camera"):
            L.append(f"- Camera/software: {json.dumps(meta['camera'], ensure_ascii=False)}")
        for pv in jload(out / "meta" / "meta.json").get("digest", {}).get("previews", []) or []:
            if pv.get("note"):
                L.append(f"- Embedded {pv['tag']}: {pv['note']} → `meta/{pv['file']}`")
        for mv in meta.get("motion_video", []) or []:
            f = mv["file"]
            L.append(f"- **Motion photo**: embedded video `meta/{f}` ({mv['bytes'] // 1024} KB) — more frames and angles; "
                     f"`ffmpeg -i meta/{f} -vf fps=2 meta/motion_%02d.jpg` and read the clearest")
        if (meta.get("provenance") or {}).get("WARNING"):
            L.append(f"- **{meta['provenance']['WARNING']}**")
        if not g and not t and not meta.get("filename_hints"):
            L.append("- No GPS, no time, no telling filename (normal for forwarded/screenshot images).")
    else:
        L.append(f"- meta.py did not run: {log.get('meta', {}).get('error', '')[:200]}")
    # text
    L += ["", "## Text", ""]
    ocr = jload(out / "intake" / "ocr.json").get("items", [])
    import re as _re
    marks = [it["text"] for it in ocr if _re.search(r"(19|20)\d\d\s*(google|goodle|apple|yandex|baidu|bing|maxar|airbus)", it["text"], _re.I)]
    if marks:
        L.append(f"- Provider watermark read: “{marks[0]}” → street-level/map imagery screenshot; the year is the copyright year, "
                 "close to (not equal to) the capture date. See references/world/streetview.md.")
    if ocr:
        L.append("OCR lines (conf, pass) — verify each in the zoomed crop; Vision cannot read Greek, Hebrew, Georgian, Armenian, Indic, "
                 "Sinhala, Khmer, Lao, Burmese or Ethiopic: read those yourself and run `textgeo.py --text`:")
        for it in ocr[:20]:
            L.append(f"- {it['conf']:.2f} {it['pass']}: {it['text']}")
    else:
        L.append("- OCR found no text (or it is too small: zoom the crops in intake/edges and detect/).")
    tg = jload(out / "textgeo.json")
    if tg.get("shortlist"):
        L.append("")
        L.append("Text → country shortlist: " + ", ".join(f"{r['name']} ({r['log_lr']})" for r in tg["shortlist"][:8]))
        for s in tg.get("signals", [])[:12]:
            L.append(f"  - [{s['kind']}/{s['status']}] {s['clue']}")
        if tg.get("places"):
            L.append("  - Place-name matches: " + "; ".join(f"“{p['matched']}” → {p['name']}, {p['admin1']}, {p['country_name']}"
                                                       for p in tg["places"][:6] if "matched" in p))
    # reverse image search
    L += ["", "## Reverse image search (Yandex, Baidu)", ""]
    ij = jload(out / "intake" / "intake.json")
    if not rev:
        L.append("- Not run (--no-rev).")
    elif ij:
        st = ij.get("status", {})
        L.append("- Engines: " + ", ".join(f"{k.replace('rev-', '')} {v}" for k, v in st.items() if k.startswith("rev-")))
        votes = ij.get("votes", {})
        city = sorted((votes.get("city") or {}).items(), key=lambda kv: -len(kv[1]))[:6]
        place = sorted((votes.get("place") or {}).items(), key=lambda kv: -len(kv[1]))[:6]
        if city:
            L.append("- City-level labels: " + "; ".join(f"{t} ({len(e)} votes)" for t, e in city))
        if place:
            L.append("- Specific places named: " + "; ".join(f"{t} ({len(e)})" for t, e in place)
                     + f" → `poi.py \"{place[0][0]}\"` (or web search) for coordinates, then verify")
        sims = [e for e in ij.get("rev", []) if e.get("similar_sheet")]
        if sims:
            L.append("- Near-duplicate sheets to open first: " + ", ".join(f"`intake/rev/{e['similar_sheet']}`" for e in sims[:4]))
        if not city and not place and not sims:
            L.append("- No labels or similar images captured: open the screenshots in `intake/rev/`; then try tight crops of "
                     "distinctive objects (`intake.py original/<photo> --box …`) and Google Lens through the browser tool.")
        L.append("- Read the result screenshots in `intake/rev/` yourself: labels are votes, near-duplicates are leads, "
                 "neither is a location until verified.")
    else:
        L.append(f"- intake did not finish: {log.get('intake', {}).get('error', '')[:200]}")
    # prior
    pr = jload(out / "prior" / "prior.json")
    L += ["", "## World prior (learned models: ranking only)", ""]
    if pr:
        a = pr.get("assessment", {})
        L.append(("- **Uninformative here** — " + "; ".join(a.get("reasons", []))) if not a.get("informative", True) else
                 "- Combined: " + ", ".join(f"{r['name']} {r['p']:.0%}" for r in pr.get("combined", [])[:6]))
        if a.get("informative", True) and a.get("reasons"):
            L.append("- Caution: " + "; ".join(a["reasons"]))
        bg = pr.get("best_guess")
        if bg and a.get("informative", True):
            L.append(f"- Model-only point guess: {bg['lat']}, {bg['lon']}" + (f" near {bg['near']}" if bg.get("near") else "")
                     + " (benchmark median error ~270 km: an area to start from, not an answer)")
        cl = (pr.get("geoclip") or {}).get("clusters", [])[:3]
        if cl:
            L.append("- GeoCLIP clusters: " + "; ".join(f"{c['lat']},{c['lon']} near {(c.get('near') or {}).get('name')}, "
                                                       f"{(c.get('near') or {}).get('country_name')} ({c['mass']:.0%})" for c in cl))
        regs = (pr.get("streetclip") or {}).get("regions", {})
        for cc, rs in list(regs.items())[:2]:
            L.append(f"- Regions of {cc}: " + ", ".join(f"{r['admin1']} {r['p_given_country']:.0%}" for r in rs[:5]))
        L.append("- Map: `prior/prior_map.png`")
        if pr.get("scene"):
            import photo_session                                   # same directory: the scene → required checks mapping lives there
            L.append("- Scene: " + ", ".join(f"{k} {v:.0%}" for k, v in sorted(pr["scene"].items(), key=lambda kv: -kv[1])))
            req = photo_session.checks_for_scene(pr["scene"])
            if req:
                L.append("- **Required before finish** (finish refuses without their files; `photo_session.py checks <session>` lists them): "
                         + "; ".join(f"**{c['name']}** ({c['why']}) → {c['command']}" for c in req))
    else:
        L.append(f"- not run ({log.get('prior', {}).get('error', 'skipped')[:160]})")
    # camera
    cb = jload(out / "calib.json")
    L += ["", "## Camera", ""]
    if cb:
        h = cb.get("horizon") or {}
        u = cb.get("uncertainty") or {}
        shaky = (u.get("vfov_uncertainty", 0) > 8 or u.get("pitch_uncertainty", 0) > 3
                 or u.get("focal_uncertainty", 0) > 0.3 * cb.get("focal_px", 1))
        L.append(f"- hfov {cb['hfov_deg']}° (35 mm eq. {cb['focal_35mm_equiv']} mm), pitch {cb['pitch_deg']}° ±{u.get('pitch_uncertainty', '?')}, "
                 f"roll {cb['roll_deg']}° ±{u.get('roll_uncertainty', '?')}, horizon row {h.get('row_at_centre')}, vfov ±{u.get('vfov_uncertainty', '?')}°"
                 + (" — **UNRELIABLE (large uncertainty): do not feed these into geometry tools; measure the horizon by hand.**" if shaky else
                    " — check the red line in `calib.jpg` before using these numbers."))
    else:
        L.append(f"- not run ({log.get('calib', {}).get('error', 'skipped')[:160]})")
    # detections
    dt = jload(out / "detect" / "detect.json")
    L += ["", "## Things to inspect", ""]
    if dt.get("detections"):
        from collections import Counter
        cnt = Counter(d["cls"] for d in dt["detections"])
        L.append("- " + ", ".join(f"{k} {v}" for k, v in cnt.most_common()) + " → open `detect/detect_sheet.jpg`, then the numbered crops.")
    elif dt:
        L.append("- The detector found nothing above its threshold: scan the image yourself (edges, corners, distant signs).")
    L.append("- Edge and corner crops: `intake/edges/` (look at every one); OCR boxes: `intake/ocr.png`.")
    L += ["", "## Next", "",
          "0. The required checks named under Prior (scene) are not optional: a mountain or lake needs the skyline route, a street the panorama "
          "route, whatever else you find. Start them early; long ones run in the background with a budget.",
          "1. Compare this page with your gut call. Where they disagree, find out why (a misread, an unusual scene, a wrong gut).",
          "2. board.json exists since `photo_session.py start` and already holds the text and prior signals (ingested here): "
          "record your own observations as clues (`board.py clue`), then evidence for the candidates they touch.",
          "3. Separate the top candidates with the cheapest decisive test (text lookups, web search, `refsheet.py`, the world clue files).",
          "4. Follow every reverse-search lead (source pages, albums, captions); try Google Lens through the browser tool and "
          "re-run the scripted engines on a tight crop of the most distinctive object. No questions to the user — decide and continue."]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("recon"))
    ap.add_argument("--no-ml", action="store_true", help="skip detect, calib and prior")
    ap.add_argument("--skip", default="", help="comma list of steps to skip: meta,intake,textgeo,detect,calib,prior")
    ap.add_argument("--no-rev", action="store_true", help="skip the Yandex/Baidu reverse image search")
    args = ap.parse_args()
    photo = args.photo.resolve()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    skip = {s.strip() for s in args.skip.split(",") if s.strip()} | ({"detect", "calib", "prior"} if args.no_ml else set())
    log: dict = {}
    t0 = time.time()
    S = lambda n: str(HERE / n)  # noqa: E731

    def light():
        if "meta" not in skip:
            run("meta", [UV, "run", "-q", S("meta.py"), str(photo), "--out-dir", str(out / "meta")], log)
        if "intake" not in skip:
            run("intake", [UV, "run", "-q", S("intake.py"), str(photo), "--out-dir", str(out / "intake")]
                + (["--no-rev"] if args.no_rev else []), log)
        if "textgeo" not in skip and (out / "intake" / "ocr.json").exists():
            run("textgeo", [UV, "run", "-q", S("textgeo.py"), "--ocr", str(out / "intake" / "ocr.json"),
                            "--out", str(out / "textgeo.json"), "--md", str(out / "textgeo.md")], log)

    def heavy():
        if "detect" not in skip:
            run("detect", [UV, "run", "-q", S("detect.py"), str(photo), "--out-dir", str(out / "detect")], log)
        if "calib" not in skip:
            run("calib", [UV, "run", "-q", S("calib.py"), str(photo), "--out", str(out / "calib.json"), "--draw", str(out / "calib.jpg")], log)
        if "prior" not in skip:
            run("prior", [UV, "run", "-q", S("prior.py"), str(photo), "--out-dir", str(out / "prior")], log)

    with ThreadPoolExecutor(2) as ex:
        a, b = ex.submit(light), ex.submit(heavy)
        a.result()
        b.result()
    md = summary(photo, out, log, time.time() - t0, not args.no_rev)
    (out / "recon.md").write_text(md, encoding="utf-8")
    (out / "recon.json").write_text(json.dumps({"photo": str(photo), "steps": log}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(md)
    print(f"-> {out / 'recon.md'}")
    ingest_into_board(out)


def ingest_into_board(out: Path) -> list[str]:
    """board.json in the session root (photo_session.py start creates it): the text and prior signals are ingested with their
    status caps, so the board carries the first pass even when nobody runs board.py ingest by hand."""
    root = out.resolve().parent
    board = root / "board.json"
    lines: list[str] = []
    if not board.is_file():
        return lines
    for rel in ("textgeo.json", "prior/prior.json"):
        f = (out / rel).resolve()
        if not f.is_file():
            continue
        r = subprocess.run([UV, "run", "-q", str(HERE / "board.py"), "ingest", str(f)], cwd=str(root),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        tail = (r.stdout.strip().splitlines() or r.stderr.strip().splitlines() or ["ok"])[-1]
        lines.append(f"board.py ingest {rel}: {tail}")
    for line in lines:
        print(line)
    return lines


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
