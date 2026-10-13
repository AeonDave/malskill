#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["streetlevel", "numpy", "pillow"]
# ///
"""Google Street View (the main ground-level source outside China): find panoramas, read dates/history/address,
render views by compass heading, build comparison sheets. Mainland China: use baidu_pano.py.

No API key. Discovery uses Google Maps coverage tiles + the photometa call (via the maintained `streetlevel`
package); views are rendered locally from the downloaded equirectangular panorama (cached in --cache).
Discovery skips user photospheres; `render <id>` works on a user or business 360 id copied from a Google Maps URL (!1s<id>);
a single upload often sits at the venue pin, publish_api tour nodes carry their own positions; neither is a verified capture
point until matched. A coverage lookup that fails (network, 429, changed reply) is reported as a failure, never as
"no panorama"; failed tiles aren't cached, so a rerun retries them.

Examples:
  gsv.py near 35.6595,139.7005 --radius 50              # nearest panorama: id, coordinates, capture date, history, address, street names, nearby ids
  gsv.py render <pano id> --heading 90 --out v.jpg      # heading = compass bearing; --pitch + looks up; --fov horizontal
  gsv.py sheet --at 35.6595,139.7005 --headings 0,60,120,180,240,300 --out around.jpg    # look around from one point
  gsv.py sheet --ids ID1,ID2 --toward 35.6600,139.7010 --out s.jpg                      # every point faces the same target
  gsv.py sheet --points pts.json --heading 90 --date 2018 --out s2018.jpg               # one capture year only (the "© year" in a screenshot is the
                                                                                      # display year, ≥ capture year: use near's dates to pick)
  gsv.py sheet --points pts.json --along --out road.jpg                                 # look along the road at each point
  gsv.py area --bbox 35.676,139.760,35.686,139.775 --spacing 120 --out panos.json       # every covered spot in an area, no Overpass needed
  gsv.py targets --points churches.json --per 2 --out churches.index.json              # every target seen from the panoramas around it,
                                                                                      # rendered facing it (for match.py rank --items)
  match.py rank --query photo.jpg --panos panos.json --headings 0,90,180,270 --render gsv --top 10 --sheet m.jpg  # then rank them
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geolib import streetlevel as SL  # noqa: E402
from geolib.cli import contact_sheet, failed_cells, neg_coords as _neg_coords, sheet_failures, sheet_pages  # noqa: E402
from geolib.paths import cache_dir  # noqa: E402
from geolib.streetlevel import ServiceError, _coverage_rows, panos_around, tile_panos, tiles_around  # noqa: E402,F401
import geo  # noqa: E402
from geolib.net import PROXY_HELP, model_proxy_env  # noqa: E402


def near(lat: float, lon: float, radius: float, proxy: str | None = None) -> dict | None:
    """Nearest official panorama within radius metres, with metadata; None if there is none."""
    model_proxy_env(proxy)
    hits = SL.find_near(lat, lon, radius, proxy=proxy)      # raises ServiceError when the lookup itself failed
    for h in hits[:3]:
        m = SL.metadata(h["id"])
        if m:
            m["distance_m"] = round(h["dist_m"], 1)
            m["candidates_within_radius"] = len(hits)
            return m
    return None


def area(bbox: list[float], spacing: float, max_tiles: int = 400, meta: bool = False, proxy: str | None = None) -> dict[str, dict]:
    """Official panoramas inside a bbox (s,w,n,e) from zoom-17 coverage tiles, thinned to one per `spacing` metres.
    Output matches match.py --panos: {pano_id: {"wgs": [lat, lon], "date": "", "road": ""}}."""
    s_, w_, n_, e_ = bbox
    x0, y1 = SL.tile_xy(s_, w_)
    x1, y0 = SL.tile_xy(n_, e_)
    tiles = [(x, y) for x in range(min(x0, x1), max(x0, x1) + 1) for y in range(min(y0, y1), max(y0, y1) + 1)]
    if len(tiles) > max_tiles:
        sys.exit(f"bbox covers {len(tiles)} map tiles (limit {max_tiles}, ~300 m each): use a smaller area or raise --max-tiles")
    cov = cache_dir("gsv", "coverage")
    failed: list[str] = []

    def fetch(xy):
        try:
            return SL.tile_panos(*xy, proxy, cov, SL.COVERAGE_MAX_AGE_S)
        except ServiceError as e:
            failed.append(str(e))
            return []

    found = {}
    with ThreadPoolExecutor(12) as ex:
        for panos in ex.map(fetch, tiles):
            for pid, la, lo in panos:
                if s_ <= la <= n_ and w_ <= lo <= e_:
                    found[pid] = (la, lo)
    if failed and len(failed) == len(tiles):
        raise ServiceError(f"every coverage lookup failed ({failed[0]})")
    if failed:
        print(f"WARNING: {len(failed)}/{len(tiles)} coverage tiles failed ({failed[0][:120]}); rerun to retry them", file=sys.stderr)
    kept: dict[str, dict] = {}
    for pid, (la, lo) in sorted(found.items(), key=lambda kv: (round(kv[1][0], 4), kv[1][1])):
        if all(SL.dist_m((la, lo), tuple(v["wgs"])) >= spacing for v in kept.values()):
            kept[pid] = {"wgs": [la, lo], "date": "", "road": ""}
    if meta and kept:
        with ThreadPoolExecutor(8) as ex:
            for pid, m in zip(list(kept), ex.map(SL.metadata, list(kept))):
                if m:
                    kept[pid].update(date=m.get("date") or "", road=(m.get("streets") or [""])[0],
                                     pano_heading=m.get("pano_heading"))
    print(f"{len(found)} official panoramas in {len(tiles)} tiles; kept {len(kept)} at ≥{spacing:g} m spacing", file=sys.stderr)
    return kept


def pick_date(res: dict, date: str) -> dict | None:
    """One capture ('2018' or '2018-07') from a near() result: this panorama or one of its historical captures."""
    for p in [{"id": res["id"], "wgs": res["wgs"], "date": res["date"]}, *res.get("history", [])]:
        if p["date"] and p["date"].startswith(date):
            return p
    return None


def view(pid: str, heading: float, pitch: float, fov: float, w: int, h: int, proxy: str | None, cache: Path,
         zoom: int = 3) -> Image.Image:
    """heading: compass bearing; positive pitch = looking up; fov: horizontal field of view in degrees.
    Raises when the streetlevel package is missing or the panorama cannot be fetched."""
    model_proxy_env(proxy)
    eq, pano_heading = SL.equirect(pid, cache, zoom)
    return SL.perspective(eq, pano_heading, heading % 360, pitch, fov, w, h)


def render(pid: str, heading: float, pitch: float, fov: float, w: int, h: int, proxy: str | None, cache: Path,
           zoom: int = 3) -> Image.Image:
    """view(), or a grey 'render failed' cell when it raises: one bad panorama must not sink a sheet or a ranking run."""
    try:
        return view(pid, heading, pitch, fov, w, h, proxy, cache, zoom)
    except Exception as e:  # noqa: BLE001
        print(f"gsv render failed for {pid}: {type(e).__name__}: {str(e)[:160]}", file=sys.stderr)
        im = Image.new("RGB", (w, h), "gray")
        ImageDraw.Draw(im).text((10, 10), f"render failed: {str(e)[:60]}", fill="white")
        im.info["failed"] = f"{type(e).__name__}: {str(e)[:120]}"
        return im


def cells(items: list[dict], proxy: str | None, cache: Path) -> list[Image.Image]:
    """Every item's view, rendered in parallel; a failed one is render()'s grey cell."""
    with ThreadPoolExecutor(4) as ex:
        return list(ex.map(lambda it: render(it["id"], it["heading"], it.get("pitch", 0), it.get("fov", 90),
                                            640, 480, proxy, cache), items))


def sheet(items: list[dict], ims: list[Image.Image], out: Path, cols: int = 3, tw: int = 480, th: int = 360) -> None:
    """The items' rendered views as one numbered contact sheet."""
    contact_sheet([(im, it.get("label") or f"{i}: …{it['id'][-8:]} h{it['heading']:.0f}") for i, (it, im) in enumerate(zip(items, ims))],
                  out, cols, tw, th, bar=22, font_size=16)


def cmd_targets(args) -> None:
    """Every target point seen from the panoramas around it, each view facing the target."""
    pts = json.loads(args.points.read_text(encoding="utf-8"))
    cov = args.cache / "coverage"

    def around(kv):
        name, v = kv
        la, lo = (v[0], v[1]) if isinstance(v, (list, tuple)) else (v["lat"], v["lon"])
        try:
            return name, (la, lo), panos_around(la, lo, args.min_dist, args.max_dist, args.per, args.spacing,
                                                args.proxy, cov), None
        except ServiceError as e:
            return name, (la, lo), [], e

    items, empty, failed = [], [], []
    with ThreadPoolExecutor(8) as ex:
        for name, tgt, picked, err in ex.map(around, pts.items()):
            if err:
                failed.append(name)
                print(f"{name}: coverage lookup failed ({err})", file=sys.stderr)
                continue
            if not picked:
                empty.append(name)
            for pid, la, lo, d in picked:
                hd = geo.bearing((la, lo), tgt)
                items.append({"id": pid, "heading": round(hd, 1), "pitch": args.pitch, "fov": args.fov,
                              "label": f"{len(items)}: {str(name)[:18]} {d:.0f}m h{hd:.0f}", "point": name,
                              "wgs": [la, lo], "target": list(tgt), "dist": round(d), "date": ""})
    out = args.out if args.out.name.endswith(".index.json") else args.out.with_suffix(".index.json")
    out.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(pts)} targets -> {len(items)} views ({len(empty)} targets without a panorama "
          f"within {args.min_dist:.0f}–{args.max_dist:.0f} m, {len(failed)} lookups failed) -> {out}")
    if len(items) > 400:
        print("match.py loads all candidate images into memory and caps candidates at 400 by default: "
              "split the target points into smaller batches or narrow the area before ranking", file=sys.stderr)
    if args.sheet and items:
        model_proxy_env(args.proxy)       # rendering downloads panoramas through the streetlevel package
        shown = items[:args.limit]
        ims = cells(shown, args.proxy, args.cache)
        bad = failed_cells(ims)
        if len(bad) == len(shown):
            print(f"every one of the {len(shown)} sheet cells failed ({bad[0]}): no sheet written; the index stays the candidate "
                  "list for match.py", file=sys.stderr)
        else:
            sheet(shown, ims, args.sheet)
            print(args.sheet)
            sheet_failures(bad, len(shown))         # the k/n line only: some cell rendered
    if failed:
        # failed tiles aren't cached, so running the same command again retries only those
        sys.exit(f"Google Street View coverage lookup failed for {len(failed)} of {len(pts)} targets; "
                 "rerun later or run doctor.py --network to check service access")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)
    ap.add_argument("--cache", type=Path, default=Path(".geo-cache/gsv"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--proxy", default=argparse.SUPPRESS, help="can go before or after the subcommand")
        sp.add_argument("--cache", type=Path, default=argparse.SUPPRESS)

    n = sub.add_parser("near")
    common(n)
    n.add_argument("latlon")
    n.add_argument("--radius", type=float, default=50)

    r = sub.add_parser("render")
    common(r)
    r.add_argument("id")
    r.add_argument("--heading", type=float, required=True)
    r.add_argument("--pitch", type=float, default=0, help="positive = looking up")
    r.add_argument("--fov", type=float, default=90, help="horizontal field of view")
    r.add_argument("--width", type=int, default=1024)
    r.add_argument("--height", type=int, default=768)
    r.add_argument("--zoom", type=int, default=3, help="panorama resolution level 1–5 (3 ≈ 4096 px wide)")
    r.add_argument("--out", type=Path, required=True)

    s = sub.add_parser("sheet")
    common(s)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--ids", help="comma-separated panoids")
    g.add_argument("--at", help="lat,lon: take the nearest panorama point")
    g.add_argument("--points", type=Path, help="JSON {name:[lat,lon]}: take the nearest panorama point for each")
    h = s.add_mutually_exclusive_group(required=True)
    h.add_argument("--heading", type=float)
    h.add_argument("--headings", help="comma-separated, e.g. 0,60,120,180,240,300")
    h.add_argument("--toward", help="lat,lon: every point faces this target")
    h.add_argument("--along", action="store_true", help="face the direction the camera car was driving")
    s.add_argument("--offset", type=float, default=0)
    s.add_argument("--pitch", type=float, default=0)
    s.add_argument("--fov", type=float, default=90)
    s.add_argument("--radius", type=float, default=50)
    s.add_argument("--date", help="only this capture (2018 or 2018-07), picked from this panorama and its historical captures; "
                                  "a screenshot's © year is when it was displayed, not captured")
    s.add_argument("--limit", type=int, default=12)
    s.add_argument("--out", type=Path, required=True)

    a = sub.add_parser("area")
    common(a)
    a.add_argument("--bbox", required=True, help="south,west,north,east")
    a.add_argument("--spacing", type=float, default=100, help="keep one panorama per this many metres")
    a.add_argument("--max-tiles", type=int, default=400)
    a.add_argument("--meta", action="store_true", help="also fetch capture date, street name and car heading for each kept panorama")
    a.add_argument("--out", type=Path, required=True)

    t = sub.add_parser("targets", help="for every target point, the panoramas around it rendered facing it -> .index.json for match.py")
    common(t)
    t.add_argument("--points", type=Path, required=True, help="JSON {name:[lat,lon]}, e.g. osm.py find output (every church in a region)")
    t.add_argument("--per", type=int, default=2, help="panoramas per target")
    t.add_argument("--min-dist", type=float, default=12, help="skip panoramas closer than this (m): too close shows only a wall")
    t.add_argument("--max-dist", type=float, default=70, help="m")
    t.add_argument("--spacing", type=float, default=15, help="minimum distance between the panoramas picked for one target (m)")
    t.add_argument("--pitch", type=float, default=8)
    t.add_argument("--fov", type=float, default=90)
    t.add_argument("--sheet", type=Path, help="also draw the first --limit items as a contact sheet")
    t.add_argument("--limit", type=int, default=12)
    t.add_argument("--out", type=Path, required=True, help="writes the .index.json for match.py rank --items")

    args = ap.parse_args(_neg_coords(sys.argv[1:]))
    if args.cmd == "targets":
        return cmd_targets(args)
    if args.cmd == "area":
        model_proxy_env(args.proxy)
        bb = [float(v) for v in args.bbox.split(",")]
        try:
            res = area(bb, args.spacing, args.max_tiles, args.meta, args.proxy)
        except ServiceError as e:
            sys.exit(f"Google Street View coverage lookup failed ({e}); run doctor.py --network to check service access")
        args.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"-> {args.out} ({len(res)} panoramas). Next: `match.py rank --query <photo> --panos {args.out} --headings 0,90,180,270 "
              f"--render gsv --top 10 --sheet m.jpg` or `gsv.py sheet --points {args.out} --along --out s.jpg`")
        return
    if args.cmd == "near":
        lat, lon = map(float, args.latlon.split(","))
        try:
            res = near(lat, lon, args.radius, args.proxy)
        except ServiceError as e:
            sys.exit(f"Google Street View lookup failed ({e}); run doctor.py --network to check service access")
        print(json.dumps({"found": True, **res} if res else
                         {"found": False, "radius_m": args.radius,
                          "message": "no official Google Street View panorama within the radius (increase --radius, check coverage, "
                                     "or run doctor.py --network)"}, ensure_ascii=False, indent=1))
    elif args.cmd == "render":
        try:
            im = view(args.id, args.heading, args.pitch, args.fov, args.width, args.height, args.proxy, args.cache, args.zoom)
        except ImportError as e:
            sys.exit(f"gsv render {args.id}: {e}; nothing written. Run it as `uv run gsv.py render …` (installs streetlevel) "
                     "or check the environment with doctor.py")
        except Exception as e:  # noqa: BLE001
            sys.exit(f"gsv render {args.id} failed ({type(e).__name__}: {str(e)[:160]}); nothing written. Check the id (the part "
                     "after !1s in a Google Maps URL, up to the next !), retry, or run doctor.py --network to check service access")
        im.save(args.out)
        print(args.out)
    else:
        panos: dict[str, dict] = {}
        if args.ids:
            for pid in args.ids.split(","):
                m = SL.metadata(pid) or {}
                panos[pid] = {"ll": m.get("wgs"), "name": "", "date": m.get("date") or "", "pano_heading": m.get("pano_heading")}
        else:
            pts = {"at": list(map(float, args.at.split(",")))} if args.at else json.loads(args.points.read_text(encoding="utf-8"))
            for name, v in pts.items():
                if isinstance(v, dict) and "wgs" in v and SL.official(name):  # gsv.py area output: already panorama ids
                    m = SL.metadata(name) or {}
                    panos.setdefault(name, {"ll": v["wgs"], "name": (m.get("streets") or [""])[0], "date": m.get("date") or "",
                                            "pano_heading": m.get("pano_heading")})
                    continue
                la, lo = (v[0], v[1]) if isinstance(v, (list, tuple)) else (v["lat"], v["lon"])
                try:
                    res = near(la, lo, args.radius, args.proxy)
                except ServiceError as e:
                    sys.exit(f"Google Street View lookup failed ({e}); run doctor.py --network to check service access")
                if res and args.date:
                    p = pick_date(res, args.date)
                    if not p:
                        print(f"{name}: no {args.date} capture (available: {', '.join(res['dates_seen'])})", file=sys.stderr)
                        continue
                    m = SL.metadata(p["id"]) or {}
                    panos.setdefault(p["id"], {"ll": p["wgs"], "name": name, "date": p["date"], "pano_heading": m.get("pano_heading")})
                elif res:
                    street = (res.get("streets") or [""])[0]
                    label = f"{name} [{street}]" if street and name != "at" else (street or name)
                    panos.setdefault(res["id"], {"ll": res["wgs"], "name": label, "date": res.get("date") or "",
                                                 "pano_heading": res.get("pano_heading")})
                else:
                    print(f"{name}: no panorama nearby", file=sys.stderr)
        target = tuple(map(float, args.toward.split(","))) if args.toward else None
        items = []
        for pid, meta in panos.items():
            ll = meta["ll"]
            if args.headings:
                heads = [float(x) for x in args.headings.split(",")]
            elif target:
                heads = [geo.bearing(tuple(ll), target) + args.offset] if ll else [args.offset]
            elif args.along:
                heads = [(meta.get("pano_heading") or 0) + args.offset]
            else:
                heads = [args.heading]
            for hd in heads:
                where = f"{ll[0]:.5f},{ll[1]:.5f}" if ll else f"…{pid[-8:]}"
                label = " ".join(x for x in (meta["name"][:26], where, meta["date"], f"h{hd % 360:.0f}") if x)
                items.append({"id": pid, "heading": hd % 360, "pitch": args.pitch, "fov": args.fov,
                              "label": f"{len(items)}: {label}", "point": meta["name"], "wgs": ll, "date": meta["date"]})
        if not items:
            sys.exit(f"No panorama within --radius {args.radius:g} m of any requested point: nothing rendered. "
                     "Increase --radius (e.g. 300–1000) or check coverage with `gsv.py near <lat,lon> --radius 1000`.")
        pages = [items[k:k + args.limit] for k in range(0, len(items), args.limit)]
        for out in sheet_pages(pages, args.out, lambda page: cells(page, args.proxy, args.cache), sheet):
            print(out)
        args.out.with_suffix(".index.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
