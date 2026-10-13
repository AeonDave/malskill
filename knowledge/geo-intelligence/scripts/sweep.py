#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["torch", "torchvision", "numpy", "pillow", "pillow-heif", "huggingface_hub", "safetensors", "opencv-python-headless", "streetlevel"]
# ///
"""City-scale street-level search: render every panorama of one or more manifests in several directions, embed the
views with MegaLoc (a visual place-recognition model), then rank them all against the photo. Sample nothing: a
whole town is usually a few thousand panoramas (index prints its measured rate); sampling 15 % of one is how the right
junction was missed in a real case, while the full sweep put it first of 9,203 (references/streetlevel.md).

  index  download the small ("low") imagery, render --views directions per panorama, embed, cache in
         $GEOINT_CACHE/sweep/<name>/ (default ~/.cache/geoint/sweep). Resumable; reused by every later photo.
  rank   rank the indexed panoramas for a photo: whole photo + left/right crops, fused; a neighbourhood score
         (support from nearby panoramas) next to the raw score; clusters of the best hits; contact sheets of the
         top panoramas rendered at their best direction in high resolution.
  view   reproduce the photo's view from one panorama: search direction, field of view and pitch, write a
         side-by-side for the verification step.

Examples:
  pano.py list --provider apple --near <lat,lon> --radius 3000 --out town_a.jsonl   # or a manifest you wrote for a site you found
  sweep.py index --manifest town_a.jsonl                           # -> index "town_a"
  sweep.py rank --index town_a --query original/photo.jpg --out-dir sweep
  sweep.py rank --index town_a town_b town_c --query original/photo.jpg --out-dir sweep   # several towns at once
  sweep.py view --index town_a --id apple:<id> --query original/photo.jpg --out sweep/view.jpg

Scores rank; they do not prove. Hits from one neighbourhood that crowd the top (see the clusters) are a strong
signal; a lone hit with no neighbours is weaker. Verify the winner on invariant structure (verify.md), never on
local-feature inlier counts across decades (measured: noise for the truth and look-alikes alike).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geolib import pano as P  # noqa: E402
from geolib.accel import handoff  # noqa: E402
from geolib.paths import cache_root  # noqa: E402

ROOT = cache_root() / "sweep"
FIRST_BATCH, PROGRESS_S = 16, 30     # index: panoramas before the first rate line; seconds between lines inside a batch


def _font(size: int, text: str = ""):
    """Label font from geolib.cli.font: CJK-capable by default, per-script choice when text is given, Windows fonts included."""
    from geolib.cli import font
    return font(size, text, prefer_wide=True)


from geolib.geomath import haversine_m as dist_m  # noqa: E402,F401  (shared helper)


# ---------------------------------------------------------------- index

def _index_dir(name: str) -> Path:
    p = Path(name)
    return p if p.is_dir() and (p / "config.json").exists() else ROOT / name


def _load_index(name: str):
    d = _index_dir(name)
    if not (d / "config.json").exists():
        raise SystemExit(f"no index {name!r} (looked in {d}); build it with sweep.py index --manifest …")
    cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
    entries = {P.key(e): e for e in P.read_manifest(d / "entries.jsonl")} if (d / "entries.jsonl").exists() else {}
    views = json.loads((d / "views.json").read_text(encoding="utf-8")) if (d / "views.json").exists() else []
    feats = np.load(d / "views.npy") if (d / "views.npy").exists() else np.zeros((0, 8448), np.float16)
    return d, cfg, entries, views, feats


def _save_index(d: Path, cfg: dict, entries: dict, views: list, feats: np.ndarray) -> None:
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "views.npy.tmp.npy"
    np.save(tmp, feats.astype(np.float16))
    os.replace(tmp, d / "views.npy")
    (d / "views.json").write_text(json.dumps(views, ensure_ascii=False), encoding="utf-8")
    P.write_manifest(d / "entries.jsonl", list(entries.values()))
    (d / "config.json").write_text(json.dumps(cfg, indent=1, ensure_ascii=False), encoding="utf-8")


def cmd_index(a) -> None:
    from geolib import megaloc as _megaloc
    rows = P.read_manifest(*a.manifest)
    name = a.name or Path(a.manifest[0]).stem
    d = ROOT / name
    if (d / "config.json").exists():
        d, cfg, entries, views, feats = _load_index(name)
        for k in ("views", "hfov", "pitch"):
            if cfg[k] != getattr(a, k):
                print(f"note: index {name} was built with {k}={cfg[k]}; keeping that", file=sys.stderr)
    else:
        cfg = {"name": name, "model": "megaloc", "views": a.views, "hfov": a.hfov, "pitch": a.pitch, "size": [384, 256],
               "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
        entries, views, feats = {}, [], np.zeros((0, 8448), np.float16)
    done = {v[0] for v in views}
    todo = [r for r in rows if P.key(r) not in done]
    print(f"index {name}: {len(rows)} panoramas in the manifest, {len(done)} already indexed, {len(todo)} to do -> {d}", flush=True)
    if not todo:
        return
    emb = _megaloc.Embedder()
    w, h = cfg["size"]
    t0 = last = time.time()
    chunk_feats, n_since_save = [], 0
    failed = 0

    def report(n: int) -> None:
        nonlocal last
        last = time.time()
        el = last - t0
        print(f"  {n}/{len(todo)} panoramas, {len(views)} views, {el:.0f}s, {el / n:.1f} s/panorama"
              + (f", ~{el / n * (len(todo) - n) / 60:.1f} min left" if n < len(todo) else "") + (f", {failed} failed" if failed else ""),
              flush=True)
    start, size = 0, FIRST_BATCH                         # a short first batch: the measured rate shows early
    while start < len(todo):
        batch = todo[start:start + size]
        urls = []
        for r in batch:                                  # prefetch every URL-based low-level image in one parallel batch
            spec = r.get("low") or r.get("high") or {}
            if spec.get("url", "").startswith("http"):
                urls.append(spec["url"])
            for u in (spec.get("faces") or {}).values():
                urls.append(u)
        if urls:
            P.fetch_many(urls, parallel=a.parallel)

        def render(r):
            try:
                v = P.load(r, "low")
                bs = v.bearings(cfg["views"])
                return r, [(b, v.render(b, cfg["pitch"], cfg["hfov"], w, h)) for b in bs]
            except Exception as e:  # noqa: BLE001
                return r, str(e)
        ims, meta = [], []
        with ThreadPoolExecutor(a.workers) as ex:
            for k, (r, res) in enumerate(ex.map(render, batch), start + 1):
                if isinstance(res, str):
                    failed += 1
                else:
                    entries[P.key(r)] = r
                    for b, im in res:
                        ims.append(im)
                        meta.append([P.key(r), b])
                if time.time() - last >= PROGRESS_S and k < start + len(batch):
                    report(k)                            # rendered so far; this batch's views count once embedded
        if ims:
            chunk_feats.append(emb.embed(ims).astype(np.float16))
            views.extend(meta)
            n_since_save += len(ims)
        start += len(batch)
        size = 256
        if n_since_save >= 4000 or start >= len(todo):
            feats = np.concatenate([feats] + chunk_feats) if chunk_feats else feats
            chunk_feats, n_since_save = [], 0
            _save_index(d, cfg, entries, views, feats)
        report(start)
    print(f"done: {len(entries)} panoramas, {len(views)} views in {d}" + (f" ({failed} could not be loaded)" if failed else ""))


# ---------------------------------------------------------------- rank

def _query_views(path: str, masks: list[tuple[int, int, int, int]], box=None) -> dict[str, Image.Image]:
    im = Image.open(path).convert("RGB")
    if box:
        im = im.crop(box)
    W, H = im.size
    out = {"full": im, "left": im.crop((0, 0, int(W * 0.66), int(H * 0.75))), "right": im.crop((int(W * 0.55), 0, W, H))}
    if masks:
        import cv2
        arr = np.asarray(im).copy()
        m = np.zeros((H, W), np.uint8)
        for x0, y0, x1, y1 in masks:
            m[max(0, y0):y1, max(0, x0):x1] = 255
        out["masked"] = Image.fromarray(cv2.inpaint(arr, m, 9, cv2.INPAINT_TELEA))
    return out


def _neighbour_support(lat, lon, z, radius: float, k: int = 3) -> np.ndarray:
    """mean of the k best z-scores among *other* panoramas within radius m (0 when alone), via grid hashing."""
    n = len(lat)
    cell = radius
    # One longitude scale for the whole hash (the smallest cos(lat) in the set, so every cell is at least `radius`
    # wide): scaling each point by its own cos(lat) shifted same-meridian neighbours by lon·sin(lat)·Δlat metres
    # (130 m per 100 m step at lon 116°), two cells apart and outside the 3x3 search.
    ky = np.floor(lat * 110540.0 / cell).astype(np.int64)
    kx = np.floor(lon * 111320.0 * math.cos(math.radians(float(np.abs(lat).max()))) / cell).astype(np.int64)
    buckets: dict[tuple[int, int], list[int]] = {}
    for i in range(n):
        buckets.setdefault((int(ky[i]), int(kx[i])), []).append(i)
    sup = np.zeros(n)
    for i in range(n):
        cand = [j for dy in (-1, 0, 1) for dx in (-1, 0, 1) for j in buckets.get((int(ky[i]) + dy, int(kx[i]) + dx), []) if j != i]
        if not cand:
            continue
        cj = np.array(cand)
        dy_ = (lat[cj] - lat[i]) * 110540.0
        dx_ = (lon[cj] - lon[i]) * 111320.0 * math.cos(math.radians(lat[i]))
        near = cj[np.hypot(dx_, dy_) <= radius]
        if len(near):
            sup[i] = np.sort(z[near])[-k:].mean()
    return sup


def _clusters(rows: list[dict], link: float = 250.0) -> list[dict]:
    """single-linkage groups of the given hits (link metres), biggest first"""
    groups: list[list[dict]] = []
    for r in rows:
        hit = [g for g in groups if any(dist_m((r["lat"], r["lon"]), (o["lat"], o["lon"])) <= link for o in g)]
        if not hit:
            groups.append([r])
        else:
            hit[0].append(r)
            for g in hit[1:]:
                hit[0].extend(g)
                groups.remove(g)
    out = []
    for g in sorted(groups, key=lambda g: (-len(g), min(x["rank"] for x in g))):
        lat = float(np.mean([x["lat"] for x in g]))
        lon = float(np.mean([x["lon"] for x in g]))
        labels = {}
        for x in g:
            lab = " ".join(v for v in ((x.get("meta") or {}).get("city", ""), (x.get("meta") or {}).get("road", "")) if v) or x["provider"]
            labels[lab] = labels.get(lab, 0) + 1
        out.append({"n": len(g), "best_rank": min(x["rank"] for x in g), "center": [round(lat, 6), round(lon, 6)],
                    "radius_m": round(max(dist_m((lat, lon), (x["lat"], x["lon"])) for x in g)),
                    "labels": dict(sorted(labels.items(), key=lambda kv: -kv[1])[:5]),
                    "members": [x["key"] for x in sorted(g, key=lambda x: x["rank"])[:12]]})
    return out


def _best_view(emb, entry: dict, q: np.ndarray, around: float, hfov: float, pitch: float, level: str = "high"):
    v = P.load(entry, level)
    if v.kind == "photo":
        im = v.render(entry.get("heading") or 0, 0, hfov, 640, 427)
        return im, entry.get("heading") or 0, float(emb.embed([im])[0] @ q)
    bs = [around + d for d in range(-30, 31, 6)]
    ims = [v.render(b, pitch, hfov, 480, 320) for b in bs]
    s = emb.embed(ims) @ q
    j = int(np.argmax(s))
    return v.render(bs[j], pitch, hfov, 640, 427), bs[j] % 360, float(s[j])


def _sheet(cells: list[tuple[Image.Image, str]], out: Path, cols: int = 4, tw: int = 480, th: int = 320) -> None:
    from geolib.cli import contact_sheet
    contact_sheet(cells, out, cols, tw, th, bar=20, font_size=15, fit="contain")


def cmd_rank(a) -> None:
    from geolib import megaloc as _megaloc
    per_view_key, per_view_b, feats, entries = [], [], [], {}
    cfg0 = None
    for name in a.index:
        d, cfg, ents, views, F = _load_index(name)
        cfg0 = cfg0 or cfg
        entries.update(ents)
        per_view_key += [v[0] for v in views]
        per_view_b += [v[1] for v in views]
        feats.append(F)
    if not per_view_key:
        raise SystemExit("the index is empty")
    F = np.concatenate(feats).astype(np.float32)
    emb = _megaloc.Embedder()
    masks = [tuple(int(v) for v in m.split(",")) for m in a.mask]
    box = tuple(int(v) for v in a.box.split(",")) if a.box else None
    qv = _query_views(a.query, masks, box)
    qf = {k: emb.embed([im])[0] for k, im in qv.items()}
    order_keys = list(dict.fromkeys(per_view_key))
    pos = {k: i for i, k in enumerate(order_keys)}
    vidx = np.array([pos[k] for k in per_view_key])
    best = {}
    for name_, q in qf.items():
        s = F @ q
        b = np.full(len(order_keys), -9.0)
        arg = np.zeros(len(order_keys), dtype=np.int64)
        for i in np.argsort(s):            # ascending: the last write per panorama is its best view
            b[vidx[i]] = s[i]
            arg[vidx[i]] = i
        best[name_] = (b, arg)
    z = {k: (v[0] - v[0].mean()) / (v[0].std() + 1e-9) for k, v in best.items()}
    fused = np.mean([z[k] for k in ("full", "left", "right")], axis=0)
    if "masked" in z:
        fused = (3 * fused + z["masked"]) / 4
    lat = np.array([entries[k]["lat"] for k in order_keys])
    lon = np.array([entries[k]["lon"] for k in order_keys])
    sup = _neighbour_support(lat, lon, fused, a.radius)
    area = fused + 0.5 * sup
    rank_f = np.argsort(-fused)
    rank_a = np.argsort(-area)
    rf = np.empty(len(fused), int)
    rf[rank_f] = np.arange(1, len(fused) + 1)
    ra = np.empty(len(fused), int)
    ra[rank_a] = np.arange(1, len(fused) + 1)
    full_best_b = best["full"][1]
    out_rows = []
    for i in rank_f:
        e = entries[order_keys[i]]
        out_rows.append({"rank": int(rf[i]), "area_rank": int(ra[i]), "key": order_keys[i], "provider": e.get("provider"), "id": e["id"],
                         "lat": e["lat"], "lon": e["lon"], "score": round(float(fused[i]), 3), "area_score": round(float(area[i]), 3),
                         "sim_full": round(float(best["full"][0][i]), 4), "best_bearing": per_view_b[int(full_best_b[i])],
                         "date": e.get("date", ""), "link": e.get("link", ""), "meta": e.get("meta", {})})
    od = Path(a.out_dir)
    od.mkdir(parents=True, exist_ok=True)
    (od / "ranked.json").write_text(json.dumps(out_rows, ensure_ascii=False, indent=0), encoding="utf-8")
    top = out_rows[: a.top]
    top_area = sorted(out_rows, key=lambda r: r["area_rank"])[: a.top]
    cl = _clusters(out_rows[: a.cluster_top], a.link)
    (od / "clusters.json").write_text(json.dumps(cl, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out_rows)} panoramas ranked ({len(per_view_key)} views) from {', '.join(a.index)}")
    print(f"{'#':>4} {'area#':>5} {'score':>6}  id / date / where")
    for r in top[: min(15, a.top)]:
        m = r.get("meta") or {}
        print(f"{r['rank']:>4} {r['area_rank']:>5} {r['score']:>6.2f}  {r['key']} {r['date']} {m.get('city', '')} {m.get('road', '')} "
              f"brg {r['best_bearing']:.0f}  {r['lat']:.5f},{r['lon']:.5f}")
    print(f"\nclusters of the top {a.cluster_top} (link {a.link:g} m):")
    for c in cl[:6]:
        print(f"  {c['n']:>3} hits, best #{c['best_rank']}, around {c['center'][0]},{c['center'][1]} (r {c['radius_m']} m): {c['labels']}")
    if cl and cl[0]["n"] >= max(5, a.cluster_top // 5):
        print(f"→ {cl[0]['n']} of the top {a.cluster_top} sit in one area: a strong neighbourhood signal. Verify there first.")
    # contact sheets: best direction per panorama, high resolution
    qthumb = Image.open(a.query).convert("RGB")
    hf, pt = cfg0["hfov"], cfg0["pitch"]

    def cell(r):
        try:
            im, b, s = _best_view(emb, entries[r["key"]], qf["full"], r["best_bearing"], hf, pt)
            return im, f"#{r['rank']} (area #{r['area_rank']}) {r['key'][-22:]} {r['date']} brg {b:.0f}"
        except Exception as e:  # noqa: BLE001
            return Image.new("RGB", (480, 320), "gray"), f"#{r['rank']} {r['key'][-22:]} failed: {str(e)[:30]}"
    if not a.no_sheet:
        cells = [(qthumb, "query")] + [cell(r) for r in top[: a.sheet]]
        _sheet(cells, od / "top.jpg")
        seen = {r["key"] for r in top[: a.sheet]}
        cells2 = [(qthumb, "query")] + [cell(r) for r in top_area[: a.sheet] if r["key"] not in seen][: a.sheet]
        if len(cells2) > 1:
            _sheet(cells2, od / "top_area.jpg")
        print(f"\n-> {od / 'ranked.json'}, {od / 'clusters.json'}, {od / 'top.jpg'}" + (", " + str(od / "top_area.jpg") if len(cells2) > 1 else ""))
    if a.truth:
        t = a.truth
        hit = [r for r in out_rows if r["key"] == t or r["id"] == t]
        if hit:
            print(f"truth {t}: rank {hit[0]['rank']}, area rank {hit[0]['area_rank']}")


# ---------------------------------------------------------------- view

def cmd_view(a) -> None:
    from geolib import megaloc as _megaloc
    entries = {}
    for name in a.index:
        entries.update(_load_index(name)[2])
    e = entries.get(a.id) or next((x for k, x in entries.items() if x["id"] == a.id), None)
    if e is None:
        raise SystemExit(f"{a.id} is not in the index")
    emb = _megaloc.Embedder()
    q = emb.embed([Image.open(a.query).convert("RGB")])[0]
    v = P.load(e, "high")
    if v.kind == "photo":
        raise SystemExit("this entry is a single photo: compare it directly")
    centre = a.bearing
    if centre is None:                                   # coarse pass all round
        bs = list(range(0, 360, 15))
        s = emb.embed([v.render(b, 3, 65, 480, 320) for b in bs]) @ q
        centre = bs[int(np.argmax(s))]
    trials = [(centre + db, f, p) for db in range(-30, 31, 5) for f in (50, 60, 75, 90) for p in (-6, 0, 6, 12)]
    ims = [v.render(b, p, f, 384, 256) for b, f, p in trials]
    s = emb.embed(ims) @ q
    order = np.argsort(-s)
    b, f, p = trials[int(order[0])]
    qim = Image.open(a.query).convert("RGB")
    W = 900
    H = int(W * qim.height / qim.width)
    rend = v.render(b, p, f, W, H)
    S = Image.new("RGB", (2 * W + 10, H + 28), "black")
    S.paste(qim.resize((W, H)), (0, 28))
    S.paste(rend, (W + 10, 28))
    d = ImageDraw.Draw(S)
    f15 = _font(16)
    d.text((6, 5), "photo", fill="yellow", font=f15)
    d.text((W + 16, 5), f"{a.id}  {e.get('date', '')}  bearing {b % 360:.0f}°  hfov {f}°  pitch {p}°  (MegaLoc {s[order[0]]:.3f})", fill="yellow", font=f15)
    S.save(a.out, quality=92)
    alts = [{"bearing": round(trials[i][0] % 360, 1), "hfov": trials[i][1], "pitch": trials[i][2], "sim": round(float(s[i]), 4)} for i in order[:8]]
    Path(a.out).with_suffix(".json").write_text(json.dumps({"id": a.id, "lat": e["lat"], "lon": e["lon"], "link": e.get("link"),
                                                            "best": alts[0], "next": alts[1:]}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{a.out}: best bearing {b % 360:.0f}°, hfov {f}°, pitch {p}° — now compare invariant structure, not the score")


from geolib.cli import neg_coords as _neg_coords  # noqa: E402  (shared helper)


def selftest() -> None:
    """Load MegaLoc once (downloads ~1.7 GB the first time) and embed a synthetic image."""
    from geolib import megaloc as _megaloc
    e = _megaloc.Embedder()
    v = e.embed([Image.new("RGB", (640, 427), (180, 150, 120))])
    assert v.shape == (1, 8448) and abs(float((v ** 2).sum()) - 1) < 1e-3
    print("MegaLoc OK")


def main() -> None:
    handoff(__file__)
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("index")
    i.add_argument("--manifest", nargs="+", required=True)
    i.add_argument("--name", help="index name (default: the first manifest's file name)")
    i.add_argument("--views", type=int, default=8, help="directions rendered per panorama")
    i.add_argument("--hfov", type=float, default=65)
    i.add_argument("--pitch", type=float, default=3)
    i.add_argument("--workers", type=int, default=8)
    i.add_argument("--parallel", type=int, default=12, help="parallel downloads")
    r = sub.add_parser("rank")
    r.add_argument("--index", nargs="+", required=True, help="one or more index names (or folders)")
    r.add_argument("--query", required=True)
    r.add_argument("--mask", action="append", default=[], help="x0,y0,x1,y1 to paint out (people, cars); repeatable")
    r.add_argument("--box", help="x0,y0,x1,y1: use only this part of the photo")
    r.add_argument("--radius", type=float, default=120, help="neighbourhood radius for the area score (m)")
    r.add_argument("--top", type=int, default=40)
    r.add_argument("--sheet", type=int, default=15, help="panoramas per contact sheet")
    r.add_argument("--cluster-top", type=int, default=50)
    r.add_argument("--link", type=float, default=250)
    r.add_argument("--no-sheet", action="store_true")
    r.add_argument("--truth", help=argparse.SUPPRESS)
    r.add_argument("--out-dir", default="sweep")
    v = sub.add_parser("view")
    v.add_argument("--index", nargs="+", required=True)
    v.add_argument("--id", required=True, help="provider:id or id")
    v.add_argument("--query", required=True)
    v.add_argument("--bearing", type=float, help="start the search here (default: search all round)")
    v.add_argument("--out", required=True)
    a = ap.parse_args(_neg_coords(sys.argv[1:]))
    {"index": cmd_index, "rank": cmd_rank, "view": cmd_view}[a.cmd](a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
