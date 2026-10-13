#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["streetlevel", "numpy", "pillow"]
# ///
"""Benchmarks: measure whether a change to the skill actually helps.

  bench.py make-streetview --n 40 --out bench/sv40 [--seed 1] [--countries PT,ES,…]
        GeoGuessr-style test set: random towns (one random covered country per round), the nearest official
        Street View panorama, a random heading → images/0001.jpg … and truth.json (kept apart from the images).
  bench.py score preds.json --truth bench/sv40/truth.json
        preds: {"0001": {"lat": …, "lon": …, "country": "PT"}, …} (or a CSV id,lat,lon[,country]).
  bench.py prior bench/sv40 --out preds_prior.json
        run prior.py on every image and keep the best GeoCLIP cluster as the guess (a model-only baseline).
  bench.py sessions [--root photos/]
        same metrics over finished archive sessions that have a recorded truth (photo_session.py truth); sessions where the
        answer or the truth is a generated image have no distance and count only in the generated block
        {called, confirmed, false_stops, missed}.
  bench.py match --panos panos.json --radius 150 --n 8 [--seed 1] [--method clip] [--dry-run]
        street-view re-identification: per site the oldest historical capture is rendered as the query and match.py rank
        (--within radius) ranks today's panoramas; prints the truth rank per case and the share at #1 / in the top 6.
        --dry-run lists the planned cases without any network access.
  bench.py satscan --cells ranked.json --truth tracks.json [--match-m 120]
        sat_scan.py ranking against known targets ({name:[lat,lon]}): recall@20/30/100 and the median rank of the truth cells.
  bench.py terrain --n 8 --seed 1
        synthetic ridgelines with a small frame roll: median camera-position error of terrain.py fit with roll solved vs not.

Metrics: median and mean error (km), share within 1 / 25 / 200 / 750 / 2500 km, country accuracy, and the
approximate world-map game score 5000·exp(−d/1492.7 km). Use the same seed to compare versions fairly.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geolib import streetlevel as SL  # noqa: E402
from geolib.paths import cache_root  # noqa: E402
import geodata  # noqa: E402

HERE = Path(__file__).resolve().parent
THRESHOLDS = (1, 25, 200, 750, 2500)
# Countries with broad official Street View coverage; rounds are drawn uniformly from this list unless --countries
DEFAULT_POOL = ("US,CA,MX,GT,CR,PA,CO,EC,PE,BO,CL,AR,UY,BR,PR,DO,GB,IE,FR,ES,PT,IT,DE,AT,CH,NL,BE,LU,DK,NO,SE,FI,"
                "IS,EE,LV,LT,PL,CZ,SK,HU,SI,HR,RS,ME,AL,MK,BG,RO,GR,TR,UA,RU,IL,JO,AE,QA,JP,KR,TW,HK,TH,KH,LA,MY,SG,"
                "ID,PH,IN,BD,LK,MN,KZ,KG,AU,NZ,ZA,BW,LS,SZ,NA,KE,UG,RW,GH,NG,SN,TN").split(",")


def score_km(d: float) -> int:
    return int(round(5000 * math.exp(-d / 1492.7)))


def metrics(pairs: list[dict]) -> dict:
    errs = sorted(p["error_km"] for p in pairs)
    n = len(errs)
    if not n:
        return {"n": 0}
    med = errs[n // 2] if n % 2 else (errs[n // 2 - 1] + errs[n // 2]) / 2
    cc = [p for p in pairs if p.get("country_true") and p.get("country_pred")]
    return {"n": n, "median_km": round(med, 1), "mean_km": round(sum(errs) / n, 1),
            "within": {f"{k}km": round(sum(e <= k for e in errs) / n, 3) for k in THRESHOLDS},
            "country_accuracy": round(sum(p["country_true"] == p["country_pred"] for p in cc) / len(cc), 3) if cc else None,
            "mean_game_score": round(sum(score_km(e) for e in errs) / n)}


def load_preds(path: Path) -> dict:
    if path.suffix.lower() == ".csv":
        out = {}
        with path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                out[row["id"]] = {"lat": float(row["lat"]), "lon": float(row["lon"]), "country": row.get("country") or None}
        return out
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_make(args) -> None:
    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    pool = [c.strip().upper() for c in (args.countries.split(",") if args.countries else DEFAULT_POOL)]
    truth, made, tries = {}, 0, 0
    cache = Path(args.cache)
    while made < args.n and tries < args.n * 8:
        tries += 1
        cc = rng.choice(pool)
        towns = geodata.sample(cc, 1, seed=rng.randrange(1 << 30), alpha=0.35, min_pop=0)
        if not towns:
            continue
        t = towns[0]
        # wander off the town centre a little so rounds are not always on the main square
        lat = t["lat"] + rng.uniform(-0.03, 0.03)
        lon = t["lon"] + rng.uniform(-0.03, 0.03) / max(math.cos(math.radians(t["lat"])), 0.2)
        hits = SL.find_near(lat, lon, args.radius, max_ring=3)
        if not hits:
            continue
        m = SL.metadata(hits[0]["id"])
        if not m:
            continue
        heading = rng.uniform(0, 360)
        try:
            eq, ph = SL.equirect(m["id"], cache, 3)
        except Exception:  # noqa: BLE001
            continue
        made += 1
        rid = f"{made:04d}"
        SL.perspective(eq, ph, heading, 0, args.fov, 1280, 800).save(out / "images" / f"{rid}.jpg", quality=90)
        truth[rid] = {"lat": round(m["wgs"][0], 6), "lon": round(m["wgs"][1], 6), "country": m.get("country_code") or cc,
                      "pano": m["id"], "date": m["date"], "heading": round(heading, 1), "town": t["name"], "admin1": t["admin1"]}
        print(f"{rid} {truth[rid]['country']} {t['name']}, {t['admin1']} ({m['date']})", flush=True)
    (out / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "README.md").write_text(
        f"# Street View benchmark ({made} rounds, seed {args.seed})\n\nImages are in images/. truth.json holds the answers: "
        "do not show it to the solver. Score predictions with `bench.py score preds.json --truth truth.json`.\n", encoding="utf-8")
    print(f"-> {out} ({made} images; truth in truth.json — keep it away from the solver)")


def cmd_score(args) -> None:
    truth = json.loads(Path(args.truth).read_text(encoding="utf-8"))
    preds = load_preds(Path(args.preds))
    pairs = []
    for rid, t in truth.items():
        p = preds.get(rid)
        if not p:
            continue
        d = float(geodata.haversine_km(t["lat"], t["lon"], p["lat"], p["lon"]))
        pairs.append({"id": rid, "error_km": round(d, 2), "country_true": t.get("country"),
                      "country_pred": (p.get("country") or geodata.reverse_country(p["lat"], p["lon"])) or None})
    m = metrics(pairs)
    m["missing"] = sorted(set(truth) - set(preds))
    print(json.dumps(m, indent=1, ensure_ascii=False))
    if args.out:
        Path(args.out).write_text(json.dumps({"metrics": m, "rounds": pairs}, indent=1, ensure_ascii=False), encoding="utf-8")


def cmd_prior(args) -> None:
    root = Path(args.bench)
    imgs = sorted((root / "images").glob("*.jpg"))
    preds, preds_gc = {}, {}
    for im in imgs:
        od = root / "prior_runs" / im.stem
        if not (args.reuse and (od / "prior.json").exists()):
            r = subprocess.run(["uv", "run", "-q", str(HERE / "prior.py"), str(im), "--out-dir", str(od)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode:
                print(f"{im.stem}: prior failed {r.stderr[-200:]}")
                continue
        d = json.loads((od / "prior.json").read_text(encoding="utf-8"))
        cl = (d.get("geoclip") or {}).get("clusters") or []
        gc_top = {"lat": cl[0]["lat"], "lon": cl[0]["lon"], "country": (cl[0].get("near") or {}).get("country")} if cl else None
        # prior.py's consistent guess when a combined country ranking exists (None if its ladder found no point);
        # GeoCLIP's top cluster only when there is no combined ranking at all
        g = d.get("best_guess") if d.get("combined") else gc_top
        if g:
            preds[im.stem] = {k: g.get(k) for k in ("lat", "lon", "country")}
        if gc_top:
            preds_gc[im.stem] = gc_top
        print(f"{im.stem}: {preds.get(im.stem)}", flush=True)
    Path(args.out).write_text(json.dumps(preds, indent=1, ensure_ascii=False), encoding="utf-8")
    gc_out = Path(args.out).with_name(Path(args.out).stem + "_geoclip_only.json")
    gc_out.write_text(json.dumps(preds_gc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"-> {args.out} (top combined country + its best GeoCLIP cluster) and {gc_out} (GeoCLIP top cluster only); "
          f"score with: bench.py score {args.out} --truth {root / 'truth.json'}")


def cmd_sessions(args) -> None:
    from photo_session import DEFAULT_ROOT, generated_summary
    root = Path(args.root if args.root is not None else DEFAULT_ROOT)
    pairs, scored = [], []
    for f in sorted(root.glob("*/session.json")):
        m = json.loads(f.read_text(encoding="utf-8-sig"))      # photo_session.py reads session files with utf-8-sig
        t, r = m.get("truth"), m.get("result")
        if t and r:
            scored.append((r, t))
            if t.get("error_km") is not None:                  # a generated answer or truth has no distance
                pairs.append({"id": f.parent.name, "error_km": t["error_km"], "country_true": t.get("country"), "country_pred": r.get("country")})
    print(json.dumps({**metrics(pairs), "generated": generated_summary(scored)}, indent=1, ensure_ascii=False))


def _eligible_sites(panos: dict, radius: float, rng: random.Random) -> list[tuple[str, float, float, int]]:
    """Panoramas with at least one other panorama within radius, in seeded random order: (id, lat, lon, candidates within)."""
    ids = sorted(pid for pid, v in panos.items() if v.get("wgs"))
    rng.shuffle(ids)
    out = []
    for pid in ids:
        la, lo = panos[pid]["wgs"]
        n_in = sum(SL.dist_m((la, lo), tuple(v["wgs"])) <= radius for v in panos.values() if v.get("wgs"))
        if n_in >= 2:
            out.append((pid, la, lo, n_in))
    return out


def cmd_match(args) -> None:
    panos = json.loads(Path(args.panos).read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    planned = _eligible_sites(panos, args.radius, rng)
    if args.dry_run:
        for k, (pid, la, lo, n_in) in enumerate(planned[: args.n], 1):
            print(f"case {k}: site …{pid[-8:]} {la:.5f},{lo:.5f}  {n_in} candidates within {args.radius:g} m  (query: its oldest capture at a seeded heading)")
        print(f"{min(args.n, len(planned))} planned cases of {len(planned)} eligible sites; drop --dry-run to run them")
        return
    cache = Path(args.cache)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for pid, la, lo, n_in in planned:
        if len(results) >= args.n:
            break
        m = SL.metadata(pid)
        hist = [h for h in (m or {}).get("history", []) if h.get("date")]
        if not hist:
            print(f"site …{pid[-8:]}: no dated historical capture, skipped", flush=True)
            continue
        old = min(hist, key=lambda h: h["date"])
        heading = rng.uniform(0, 360)
        k = len(results) + 1
        q = out_dir / f"case{k:02d}_query.jpg"
        try:
            eq, ph = SL.equirect(old["id"], cache / "gsv", 3)
        except Exception as e:  # noqa: BLE001
            print(f"site …{pid[-8:]}: query render failed ({type(e).__name__}), skipped", flush=True)
            continue
        SL.perspective(eq, ph, heading, 0, args.fov, 640, 480).save(q, quality=90)
        ranked = out_dir / f"case{k:02d}_ranked.json"
        cmd = ["uv", "run", "-q", str(HERE / "match.py"), "--cache", str(cache), "rank", "--query", str(q), "--panos", str(args.panos),
               "--within", f"{la},{lo},{args.radius}", "--headings", f"{heading:.1f}", "--render", "gsv", "--method", args.method,
               "--refine", "none", "--fov", str(args.fov), "--pitch", "0", "--top", "10", "--out", str(ranked)]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode or not ranked.exists():
            print(f"site …{pid[-8:]}: match.py failed {r.stderr[-300:]}", flush=True)
            continue
        rows = json.loads(ranked.read_text(encoding="utf-8"))
        rank = next((row["rank"] for row in rows if row["id"] == pid), None)
        results.append({"case": k, "site": pid, "query": old["id"], "query_date": old["date"], "truth_date": m.get("date"),
                        "heading": round(heading, 1), "n_candidates": len(rows), "truth_rank": rank})
        print(f"case {k}: site …{pid[-8:]} query {old['date']} → truth {m.get('date')}  {len(rows)} candidates  "
              f"truth rank {rank if rank else 'not rendered'}", flush=True)
    n = len(results)
    if not n:
        sys.exit("no case ran (no site with a dated historical capture, or every render failed)")
    ranks = sorted(r["truth_rank"] for r in results if r["truth_rank"])
    top1, top6 = sum(r == 1 for r in ranks), sum(r <= 6 for r in ranks)
    print(f"{n} cases (radius {args.radius:g} m, {args.method}): truth at #1 {top1}/{n} ({top1 / n:.0%}), in top 6 {top6}/{n} ({top6 / n:.0%})"
          + (f", median truth rank {ranks[len(ranks) // 2]}" if ranks else ""))
    (out_dir / "match_bench.json").write_text(json.dumps({"radius_m": args.radius, "method": args.method, "seed": args.seed, "cases": results},
                                                         ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out_dir / 'match_bench.json'}")


def _cell_pitch_m(rows: list[dict]) -> float:
    """Median nearest-neighbour spacing of the first 200 cells (the grid pitch)."""
    pts = [(r["lat"], r["lon"]) for r in rows[:200]]
    nn = sorted(min((geodata.haversine_km(la, lo, lb, lob) * 1000 for j, (lb, lob) in enumerate(pts) if j != i), default=0.0)
                for i, (la, lo) in enumerate(pts))
    return nn[len(nn) // 2] if nn else 0.0


def satscan_metrics(cells: list[dict], truth: dict[str, tuple[float, float]], match_m: float) -> dict:
    """Rank of the first cell within match_m of each truth point; recall@20/30/100 over all truth points, median over the matched."""
    rows = sorted((r for r in cells if "lat" in r and "lon" in r), key=lambda r: r.get("rank", float("inf")))
    per = []
    for name, (la, lo) in truth.items():
        hit = next(((r.get("rank", i + 1), r) for i, r in enumerate(rows) if geodata.haversine_km(la, lo, r["lat"], r["lon"]) * 1000 <= match_m), None)
        per.append({"name": name, "rank": hit[0] if hit else None, "cell": hit[1].get("cell") if hit else None,
                    "dist_m": round(geodata.haversine_km(la, lo, hit[1]["lat"], hit[1]["lon"]) * 1000) if hit else None})
    ranks = sorted(p["rank"] for p in per if p["rank"] is not None)
    n, k = len(per), len(ranks)
    med = None if not k else (ranks[k // 2] if k % 2 else (ranks[k // 2 - 1] + ranks[k // 2]) / 2)
    return {"n_truth": n, "n_cells": len(rows), "match_m": round(match_m, 1), "matched": k,
            "recall": {f"@{t}": sum(r <= t for r in ranks) for t in (20, 30, 100)}, "median_rank": med, "per_point": per}


def cmd_satscan(args) -> None:
    import terrain
    cells = json.loads(Path(args.cells).read_text(encoding="utf-8"))
    if not isinstance(cells, list):
        sys.exit("--cells must be the ranked list sat_scan.py writes with --out")
    truth = {name: (la, lo) for name, la, lo in terrain.load_points(Path(args.truth))}
    match_m = args.match_m or 0.75 * _cell_pitch_m(sorted(cells, key=lambda r: r.get("rank", float("inf"))))
    if match_m <= 0:
        sys.exit("cannot infer the cell size from --cells; give --match-m")
    m = satscan_metrics(cells, truth, match_m)
    for p in m["per_point"]:
        print(f"  {p['name'][:30]:<30} rank {p['rank'] if p['rank'] else '-':>5}  cell {p['cell'] or '-'}  {('%d m' % p['dist_m']) if p['dist_m'] is not None else 'no cell within radius'}")
    n = m["n_truth"]
    print(f"{n} truth points vs {m['n_cells']} cells (match radius {m['match_m']:.0f} m): "
          + ", ".join(f"recall{t} {v}/{n}" for t, v in m["recall"].items())
          + f"; median rank {m['median_rank'] if m['median_rank'] is not None else '-'}; unmatched {n - m['matched']}")
    if args.out:
        Path(args.out).write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_terrain(args) -> None:
    import contextlib
    import io
    import tempfile
    from unittest.mock import patch
    sys.path.insert(0, str(HERE / "tests"))
    import terrain
    import test_terrain as tt           # the synthetic terrain and ridge writer of the regression suite
    rng = random.Random(args.seed)
    errs: dict[str, list[float]] = {"untilted": [], "tilted": []}
    kx = 111320 * math.cos(math.radians(tt.LAT0))
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        for i in range(1, args.n + 1):
            f35 = rng.choice((26, 40, 60, 90))
            heading = rng.uniform(250, 290)
            roll = rng.choice((-1, 1)) * rng.uniform(0.4, 0.9 * args.roll_max)
            tt.synth_ridge(d / "r.json", f35, heading, two_layer=False, roll=roll)
            # grid centre off the truth by a random fraction of a cell, so the truth is never exactly a grid node
            clat = tt.LAT0 + rng.uniform(-0.5, 0.5) * args.grid / 110540
            clon = tt.LON0 + rng.uniform(-0.5, 0.5) * args.grid / kx
            line = f"case {i}: f35 {f35} heading {heading:.1f} roll {roll:+.2f}°"
            for label, rmax in (("untilted", 0.0), ("tilted", args.roll_max)):
                argv = ["terrain.py", "fit", "--at", f"{clat},{clon}", "--radius", str(args.radius), "--grid", str(args.grid),
                        "--ridge", str(d / "r.json"), "--out", str(d / "f.json"), "--range", "30000", "--min-peak", "2",
                        "--nsamp", "400", "--roll-max", str(rmax)]
                with patch.object(terrain, "DEM", tt.FakeDEM), patch.object(sys, "argv", argv), contextlib.redirect_stderr(io.StringIO()):
                    terrain.main()
                best = json.loads((d / "f.json").read_text(encoding="utf-8"))["cams"][0]
                err = geodata.haversine_km(tt.LAT0, tt.LON0, best["cam"][0], best["cam"][1]) * 1000
                errs[label].append(err)
                line += f"  {label}: err {err:.0f} m H {best['H']:.1f} roll {best['roll']:+.2f} rms {best['rms_px']} px"
            print(line, flush=True)
    med = lambda v: sorted(v)[len(v) // 2]  # noqa: E731
    print(f"median position error over {args.n} cases (grid {args.grid:g} m, radius {args.radius:g} m): "
          f"untilted {med(errs['untilted']):.0f} m, tilted {med(errs['tilted']):.0f} m")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make-streetview")
    mk.add_argument("--n", type=int, default=40)
    mk.add_argument("--out", required=True)
    mk.add_argument("--seed", type=int, default=1)
    mk.add_argument("--countries", help="comma list of ISO2 codes (default: a pool of covered countries)")
    mk.add_argument("--radius", type=float, default=900)
    mk.add_argument("--fov", type=float, default=90)
    mk.add_argument("--cache", default=str(cache_root() / "bench-panos"))
    sc = sub.add_parser("score")
    sc.add_argument("preds")
    sc.add_argument("--truth", required=True)
    sc.add_argument("--out")
    pr = sub.add_parser("prior")
    pr.add_argument("bench")
    pr.add_argument("--out", default="preds_prior.json")
    pr.add_argument("--reuse", action="store_true", help="reuse prior_runs/*/prior.json instead of rerunning the models")
    se = sub.add_parser("sessions")
    se.add_argument("--root", default=None, help="archive root (default: the same as photo_session.py)")
    ma = sub.add_parser("match", help="historical capture as query → rank of today's panorama among the candidates within --radius")
    ma.add_argument("--panos", required=True, help="panos.json from gsv.py area ({id: {wgs, date, road}})")
    ma.add_argument("--radius", type=float, default=150, help="candidate radius m around each site (default 150)")
    ma.add_argument("--n", type=int, default=8)
    ma.add_argument("--seed", type=int, default=1)
    ma.add_argument("--method", choices=["megaloc", "dino", "clip"], default="clip")
    ma.add_argument("--fov", type=float, default=80)
    ma.add_argument("--cache", default=".geo-cache", help="panorama cache shared with match.py / gsv.py (default .geo-cache)")
    ma.add_argument("--out-dir", default="bench_match", help="query renders, ranked.json per case, match_bench.json")
    ma.add_argument("--dry-run", action="store_true", help="only list the planned cases (no network)")
    ss = sub.add_parser("satscan", help="sat_scan ranking vs known targets: recall@20/30/100, median rank")
    ss.add_argument("--cells", required=True, help="ranked.json written by sat_scan.py grid/points --out")
    ss.add_argument("--truth", required=True, help="{name:[lat,lon]} of the real targets (e.g. osm.py output)")
    ss.add_argument("--match-m", type=float, help="a cell counts as the truth within this distance m (default: 0.75 × the grid pitch)")
    ss.add_argument("--out", help="write the metrics and per-point ranks as JSON")
    tb = sub.add_parser("terrain", help="synthetic rolled ridgelines: fit position error with roll solved vs not")
    tb.add_argument("--n", type=int, default=8)
    tb.add_argument("--seed", type=int, default=1)
    tb.add_argument("--grid", type=float, default=200, help="camera grid spacing m (default 200)")
    tb.add_argument("--radius", type=float, default=600, help="camera grid radius m (default 600)")
    tb.add_argument("--roll-max", type=float, default=1.0, help="fit --roll-max of the tilted run; synthetic rolls stay within 0.9× of it")
    args = ap.parse_args()
    {"make-streetview": cmd_make, "score": cmd_score, "prior": cmd_prior, "sessions": cmd_sessions,
     "match": cmd_match, "satscan": cmd_satscan, "terrain": cmd_terrain}[args.cmd](args)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
