#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""City / government open data: turn a specific clue into a short list of coordinates.

Many cities publish every bus lane, street tree, fire hydrant, bench, street light, speed-limit road or school as
open data with coordinates. A clue you can read off the photo (a coloured bus lane, a less common tree species,
a posted limit, a building height) becomes a filter that collapses a whole city to a few candidate points you
then check on satellite and street level. See references/datasets.md for the method.

  search   find datasets on the Socrata network by keyword (optionally one city's portal)
  columns  list a Socrata dataset's fields (+ a sample row) so you know what to filter on
  get      download a Socrata dataset (filter with --eq / --range / --where), optionally extract candidate points
  points   extract {name:[lat,lon]} points from any CSV or GeoJSON file or URL (for ArcGIS Hub, CKAN, a direct export)
  group    aggregate a points file into grid cells with ≥ N points (which blocks hold several matching trees), one point per cell

Points JSON is {name: [lat, lon]} (WGS84) — feed it straight to tiles.py sheet / gsv.py sheet / board.py add.
Lines and polygons (a bus lane, a road) become one representative point each (midpoint / average of vertices).

Portals: Socrata hosts thousands of US/EU city and state portals (NYC, Chicago, LA, Seattle, many more). Cities on
ArcGIS Hub or CKAN aren't in the Socrata catalog: find the dataset's CSV or GeoJSON export URL in the browser and
use `points <url>`. Find a city's portal with a web search: "<city> open data portal".

Examples:
  opendata.py search "street tree census" --domain data.cityofnewyork.us
  opendata.py columns data.cityofnewyork.us uvpi-gqnh
  opendata.py get data.cityofnewyork.us uvpi-gqnh --eq spc_common=sassafras --eq boroname=Manhattan --points --name-field address --out trees.json
  opendata.py get data.cityofnewyork.us ycrg-ses3 --eq lane_color=Red --range streetwidt:30:50 --points --name-field street --out lanes.json
  opendata.py points "https://<host>/.../export.geojson" --name-field species --out pts.json
  opendata.py group --points trees.json --cell 80 --min 3 --out blocks.json      # cells with ≥3 of the species → tiles.py sheet / gsv.py sheet
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from pathlib import Path
from urllib.parse import quote, urlencode

sys.path.insert(0, str(Path(__file__).parent))
from geolib.net import fetch_bytes, PROXY_HELP  # noqa: E402

CATALOG = {"us": "https://api.us.socrata.com/api/catalog/v1", "eu": "https://api.eu.socrata.com/api/catalog/v1"}


def _get_json(url: str, proxy, timeout: int = 60):
    return json.loads(fetch_bytes(url, proxy, timeout=timeout))


def cmd_search(args) -> None:
    q = {"q": args.query, "limit": args.limit, "only": "dataset"}
    if args.domain:
        q["domains"] = args.domain
    data = _get_json(f"{CATALOG[args.region]}?{urlencode(q)}", args.proxy)
    total = data.get("resultSetSize", 0)
    results = data.get("results", [])
    print(f"{total} dataset(s) match {args.query!r}" + (f" on {args.domain}" if args.domain else " across all Socrata portals")
          + f"; showing {len(results)}:")
    for r in results:
        res = r.get("resource", {})
        dom = (r.get("metadata") or {}).get("domain", "?")
        rows = res.get("rows_size")
        desc = (res.get("description") or "").replace("\n", " ")[:90]
        print(f"\n  {dom}  {res.get('id','?')}   {res.get('name','?')}" + (f"   ({rows:,} rows)" if isinstance(rows, int) else ""))
        if desc:
            print(f"      {desc}")
    if not args.domain:
        print("\nNarrow with --domain <portal host> (from a result above, or a web search '<city> open data').")


def cmd_columns(args) -> None:
    meta = _get_json(f"https://{args.domain}/api/views/{args.id}.json", args.proxy)
    print(f"{meta.get('name','?')}  ({args.domain}/{args.id})")
    if meta.get("description"):
        print(f"  {meta['description'][:200]}")
    cols = meta.get("columns", [])
    print(f"\n  {'field name':28} {'type':12} name")
    for c in cols:
        print(f"  {c.get('fieldName',''):28} {c.get('dataTypeName',''):12} {c.get('name','')}")
    sample = _get_json(f"https://{args.domain}/resource/{args.id}.json?$limit=1", args.proxy)
    if sample:
        print("\n  sample row:")
        for k, v in sample[0].items():
            print(f"    {k} = {json.dumps(v, ensure_ascii=False)[:80]}")


NUMERIC = {"number", "money", "double", "percent"}


def _col_types(domain: str, dsid: str, proxy) -> dict:
    """{field name: Socrata data type} from the dataset's metadata (decides whether a value must be quoted)."""
    try:
        meta = _get_json(f"https://{domain}/api/views/{dsid}.json", proxy)
        return {c.get("fieldName"): (c.get("dataTypeName") or "").lower() for c in meta.get("columns", [])}
    except Exception:                                                           # noqa: BLE001
        return {}


def _soql(args, types: dict | None = None) -> str:
    types = types or {}
    clauses = []
    for e in args.eq or []:
        k, v = e.split("=", 1)
        t = types.get(k)
        looks_num = v.replace('.', '', 1).replace('-', '', 1).isdigit()
        if t == "checkbox":
            clauses.append(f"{k}={v.lower()}")
        elif t in NUMERIC or (t is None and looks_num):
            clauses.append(f"{k}={v}")
        else:                                                                   # text (incl. digit strings like '0029245')
            clauses.append(f"{k}='{v}'")
    for r in args.range or []:
        k, lo, hi = r.split(":")
        clauses.append(f"{k} between {lo} and {hi}")
    if args.where:
        clauses.append(args.where)
    return " AND ".join(clauses)


def _rep_point(geom: dict):
    """One representative (lat, lon) for a GeoJSON geometry: a point as is, a line's midpoint, a polygon's vertex average."""
    if not geom:
        return None
    t, co = geom.get("type"), geom.get("coordinates")
    if not co:
        return None
    if t == "Point":
        return [round(co[1], 6), round(co[0], 6)]
    pts = []

    def walk(x):
        if x and isinstance(x[0], (int, float)):
            pts.append(x)
        else:
            for y in x:
                walk(y)
    walk(co)
    if not pts:
        return None
    if t in ("LineString", "MultiLineString"):
        p = pts[len(pts) // 2]
    else:
        p = [sum(c[0] for c in pts) / len(pts), sum(c[1] for c in pts) / len(pts)]
    return [round(p[1], 6), round(p[0], 6)]


def _points_from_geojson(fc: dict, name_field: str | None, limit: int) -> dict:
    out = {}
    feats = fc.get("features", [])[:limit]
    la, lon = _latlon_cols((feats[0].get("properties") or {}).keys()) if feats else (None, None)
    for i, feat in enumerate(feats):
        props = feat.get("properties") or {}
        ll = _rep_point(feat.get("geometry") or {})
        if not ll and la and props.get(la) not in (None, ""):          # many exports carry a null geometry + lat/lon columns
            try:
                ll = [round(float(props[la]), 6), round(float(props[lon]), 6)]
            except (TypeError, ValueError):
                ll = None
        if not ll:
            continue
        name = str(props.get(name_field)) if name_field and props.get(name_field) is not None else f"f{i}"
        while name in out:
            name += "_"
        out[name] = ll
    return out


def _latlon_cols(fieldnames):
    lo = {f.lower(): f for f in fieldnames}
    for la, lon in (("latitude", "longitude"), ("lat", "lon"), ("lat", "lng"), ("y", "x")):
        if la in lo and lon in lo:
            return lo[la], lo[lon]
    return None, None


def _points_from_rows(rows: list[dict], name_field: str | None, limit: int) -> dict:
    out = {}
    if not rows:
        return out
    la, lon = _latlon_cols(rows[0].keys())
    geomcol = next((k for k in rows[0] if k in ("the_geom", "geom", "location", "point", "geolocation")), None)
    for i, row in enumerate(rows[:limit]):
        ll = None
        if la and row.get(la) not in (None, ""):
            try:
                ll = [round(float(row[la]), 6), round(float(row[lon]), 6)]
            except (ValueError, TypeError):
                ll = None
        elif geomcol and isinstance(row.get(geomcol), dict):
            g = row[geomcol]
            ll = _rep_point(g if "coordinates" in g else {"type": "Point", "coordinates": [g.get("longitude"), g.get("latitude")]}) \
                if (g.get("coordinates") or g.get("latitude")) else None
        if not ll:
            continue
        name = str(row.get(name_field)) if name_field and row.get(name_field) else f"r{i}"
        while name in out:
            name += "_"
        out[name] = ll
    return out


def cmd_get(args) -> None:
    where = _soql(args, _col_types(args.domain, args.id, args.proxy) if args.eq else None)
    params = {"$limit": args.limit}
    if where:
        params["$where"] = where
    if args.select:
        params["$select"] = args.select
    qs = urlencode(params, quote_via=quote)
    if args.points:
        try:
            fc = _get_json(f"https://{args.domain}/resource/{args.id}.geojson?{qs}", args.proxy)
            pts = _points_from_geojson(fc, args.name_field, args.limit)
        except Exception:                                                       # noqa: BLE001  (no geometry column → fall back to rows)
            pts = {}
        if not pts:                                                             # geometry missing or empty → lat/lon columns in the rows
            pts = _points_from_rows(_get_json(f"https://{args.domain}/resource/{args.id}.json?{qs}", args.proxy), args.name_field, args.limit)
        print(f"{len(pts)} candidate point(s)" + (f" where {where}" if where else ""))
        _emit(pts, args.out)
        return
    rows = _get_json(f"https://{args.domain}/resource/{args.id}.json?{qs}", args.proxy)
    print(f"{len(rows)} row(s)" + (f" where {where}" if where else ""))
    for row in rows[:args.show]:
        print("  " + json.dumps(row, ensure_ascii=False)[:200])
    if args.out:
        Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"-> {args.out}")


def cmd_points(args) -> None:
    src = args.source
    raw = fetch_bytes(src, args.proxy, timeout=90) if src.startswith(("http://", "https://")) else Path(src).read_bytes()
    text = raw.decode("utf-8", "replace").lstrip()
    if text[:1] in "{[":
        obj = json.loads(text)
        fc = obj if isinstance(obj, dict) and obj.get("type") == "FeatureCollection" else {"features": obj if isinstance(obj, list) else [obj]}
        pts = _points_from_geojson(fc, args.name_field, args.limit) or _points_from_rows(
            [f.get("properties", f) for f in fc["features"]], args.name_field, args.limit)
    else:
        rows = list(csv.DictReader(io.StringIO(text)))
        pts = _points_from_rows(rows, args.name_field, args.limit)
    print(f"{len(pts)} point(s) from {src}")
    _emit(pts, args.out)


def group_points(pts: dict, cell_m: float, min_n: int) -> dict:
    """Grid cells of cell_m metres holding ≥ min_n points → {"g<i> x<count>": [mean lat, mean lon]}, largest cell first."""
    ll = []
    for v in pts.values():
        la, lo = (v["lat"], v["lon"]) if isinstance(v, dict) else (v[0], v[1])
        ll.append((float(la), float(lo)))
    if not ll:
        return {}
    kx = 111320 * math.cos(math.radians(sum(p[0] for p in ll) / len(ll)))
    cells: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for la, lo in ll:
        cells.setdefault((math.floor(la * 110540 / cell_m), math.floor(lo * kx / cell_m)), []).append((la, lo))
    groups = sorted((m for m in cells.values() if len(m) >= min_n), key=len, reverse=True)
    return {f"g{i} x{len(m)}": [round(sum(p[0] for p in m) / len(m), 6), round(sum(p[1] for p in m) / len(m), 6)]
            for i, m in enumerate(groups, 1)}


def cmd_group(args) -> None:
    if args.cell <= 0 or args.min < 1:
        sys.exit("--cell must be > 0 m and --min ≥ 1")
    pts = json.loads(args.points.read_text(encoding="utf-8"))
    if not isinstance(pts, dict):
        sys.exit("--points must be a {name:[lat,lon]} JSON (make it with `points` or `get --points`)")
    groups = group_points(pts, args.cell, args.min)
    print(f"{len(pts)} points → {len(groups)} cell(s) of {args.cell:g} m with ≥{args.min} points (name carries the count)")
    _emit(groups, args.out)


def _emit(pts: dict, out) -> None:
    for k, (name, ll) in enumerate(pts.items()):
        if k >= 30:
            print("  …")
            break
        print(f"  {name}  {ll[0]},{ll[1]}")
    if out:
        Path(out).write_text(json.dumps(pts, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"-> {out}")
    elif pts:
        print("  (use --out points.json to feed tiles.py sheet / gsv.py sheet / board.py add)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proxy", default=None, help=PROXY_HELP)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--domain", help="one portal host, e.g. data.cityofnewyork.us")
    s.add_argument("--region", choices=["us", "eu"], default="us", help="Socrata catalog host (us covers North America, eu the rest)")
    s.add_argument("--limit", type=int, default=20)

    c = sub.add_parser("columns")
    c.add_argument("domain")
    c.add_argument("id", help="4x4 dataset id, e.g. ycrg-ses3")

    g = sub.add_parser("get")
    g.add_argument("domain")
    g.add_argument("id")
    g.add_argument("--eq", action="append", help="column=value filter (repeatable), e.g. lane_color=Red")
    g.add_argument("--range", action="append", help="column:lo:hi numeric range (repeatable), e.g. stories:4:4")
    g.add_argument("--where", help="raw SoQL $where, for anything --eq/--range can't express")
    g.add_argument("--select", help="SoQL $select (columns to return)")
    g.add_argument("--limit", type=int, default=50000, help="max rows to pull, default 50000")
    g.add_argument("--show", type=int, default=5, help="rows to print (non-points mode)")
    g.add_argument("--points", action="store_true", help="extract candidate {name:[lat,lon]} points")
    g.add_argument("--name-field", help="column to name each point by (e.g. a street name or species)")
    g.add_argument("--out", type=Path)

    p = sub.add_parser("points")
    p.add_argument("source", help="a .geojson/.json/.csv URL or local file")
    p.add_argument("--name-field")
    p.add_argument("--limit", type=int, default=50000)
    p.add_argument("--out", type=Path)

    gr = sub.add_parser("group", help="aggregate a points file into grid cells holding ≥ --min points (street trees → the blocks with several matches)")
    gr.add_argument("--points", type=Path, required=True, help="{name:[lat,lon]} from points / get --points")
    gr.add_argument("--cell", type=float, default=80, help="cell size m (default 80, about one block side)")
    gr.add_argument("--min", type=int, default=3, help="keep cells with at least this many points (default 3)")
    gr.add_argument("--out", type=Path)

    args = ap.parse_args()
    try:
        {"search": cmd_search, "columns": cmd_columns, "get": cmd_get, "points": cmd_points, "group": cmd_group}[args.cmd](args)
    except RuntimeError as e:
        sys.exit(f"Request failed: {e}\nIf this was a filter, check the field names and value types with "
                 "`opendata.py columns <domain> <id>` (text values are quoted, numbers are not).")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
