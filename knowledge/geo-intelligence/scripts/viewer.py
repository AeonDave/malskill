#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Live view of one geolocation session in the browser: a globe that turns and zooms to the answer, and a panel with
what the analysis is doing right now.

  viewer.py serve [SESSION] [--port N] [--open] [--tiles esri|osm]      serve the session on 127.0.0.1 on a random free port (printed, and
                                                                        stored as viewer_url in session.json); --open starts the browser
  viewer.py say "text" [--session SESSION]                              one line about the current step; shown first in the panel;
                                                                        prints `said · ` and photo_session.status_line (minutes since
                                                                        start, verification files, required checks)
  viewer.py state [SESSION]                                             print the JSON the page polls (debugging, tests)
  viewer.py export [SESSION] [--out viewer.html]                        one self-contained HTML snapshot next to the photos (offline, no server)
  viewer.py stop [SESSION | --port N] [--force]                         stop this session's viewer (another session's only with --force)
  viewer.py mark camera --lat L --lon L --heading H [--fov 90] [--label T]   camera point with its view cone on the map
  viewer.py mark line --from lat,lon (--to lat,lon | --bearing B --km N) [--label T]   a sight line or alignment
  viewer.py mark point --lat L --lon L --label T [--image FILE]             a named place (anchor, peak, building)
  viewer.py mark image FILE --lat L --lon L [--heading H] [--label T]       a found photo or panorama at its position
  viewer.py mark area FILE.geojson [--label T] [--level L]                  outlines and lines of any GeoJSON (osm.py geom: footprints,
                                                                            indoor rooms and corridors, shores, routes), first 500 features;
                                                                            --level for features that carry none (-1: underground)
  viewer.py mark list | clear [--kind camera|line|point|image|area]

SESSION defaults to the current directory (or a parent) holding session.json; the folder keeps being served after
photo_session.py finish renames it. The server stops on Close, on `stop`, on Ctrl+C, and by itself after
--idle-minutes (30) without a single request, so a forgotten viewer never outlives its session. Nothing leaves the machine except the close-up imagery tiles the browser fetches
(Esri World Imagery, or OpenStreetMap with --tiles osm); the globe itself is drawn from a bundled Natural Earth file.

The page re-reads the folder every 2 s and shows:
  focus       the finished result, else the top-ranked candidate at the finest open board level that has a position
              (before any board.py call: the gut call leader read from report.md, country names in English):
              countries get theirs from assets/data/countries.json, every other level needs a bbox on the board
              (board.py add --bbox s,w,n,e, --from pois.json, or scan-bbox); without one the globe stays on the parent
  candidates  every board level with shares, verified-evidence counts and exclusions
  activity    `say` lines, board.py log entries and every new file, newest first
  truth       after photo_session.py truth: the real spot in teal, a dashed line to the answer, the error in km
  generated   a finish --generated answer: "Generated image: no real place" with its basis and a red badge, no globe target;
              before the finish, recon/aidet/aidet.json at or above its threshold adds one muted line to Now (a ranking,
              not a verdict), replaced by "Operator: real, continue" once photo_session.py not-generated recorded the operator
  map layers  marks (viewer_marks.json, from `mark`), the top rows of every *_rank.json written by match.py
              (position, heading, score, the saved view as a thumbnail), the panoramas of every *.index.json as
              faint coverage dots; click a marker for its card, buttons toggle the layers. Area marks draw rings (faint fill)
              and lines, dashed below ground (level or layer < 0), names once a feature is large enough to read; when a
              feature carries a level, chips (all, then each level) show one floor plus the features without a level.
              Display only: no coordinate, radius or confidence changes
  analysis    images whose name says what they are (ridge, fit, overlay, evidence, match, sheet, pose, _rank)
  skyline     terrain.py fit --sheet's <sheet>_skyline.jpg/.json: the top three synthetic skylines over the photo, ranked, summit names
  coverage    every panorama of the session's lists (gsv.py area, pano.py list/index) as selectable dots: id, provider, date, road, a link to open it
              in their own gallery
  close       the page's Close button stops this server (POST /api/stop); the analysis is not affected
  snapshot    finish, truth, stop and Close all write <session>/viewer.html: the same page with the state, the
              outlines, the styles and the script inlined and file links relative, so it opens from the folder
              without a server (imagery tiles still need the network)
  files       images open full size on click; report.md and recon/recon.md are rendered; the folder path under the
              title opens the session folder in the file manager (POST /api/open, local only)
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import http.server
import json
import math
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from functools import partial
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
UI_DIR = SKILL_DIR / "assets" / "viewer"
COUNTRIES_FILE = SKILL_DIR / "assets" / "data" / "countries.json"
sys.path.insert(0, str(HERE))
import board as _board  # noqa: E402  (share computation and level order stay in one place)
import photo_session as _ps  # noqa: E402  (gut call parser, required checks, status line, When text, heading hint, session.json writer)
from geolib.geomath import dest as _dest  # noqa: E402

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
TEXT_EXT = {".md", ".txt", ".log", ".json", ".geojson", ".csv"}
SKIP_DIRS = {".geo-cache", "__pycache__", ".playwright-mcp", "node_modules"}
SKIP_FILES = {"session.json", "board.json", "activity.log"}
ACTIVITY_FILE = "activity.log"
MARKS_FILE = "viewer_marks.json"
RANK_NAME = re.compile(r"(^rank\.json$|_rank\.json$|^rank_.*\.json$|_rank_.*\.json$)")
ANALYSIS_MARK = re.compile(r"(ridge|skyline|fit|overlay|evidence|match|sheet|pose|_rank|intersect|compass|refsheet|profile|scan)", re.I)
MAX_MATCHES = 60
MAX_COVERAGE = 3000
STAGES = ["Gut call", "Recon", "Candidates", "Pinpoint", "Verify", "Done"]
PINPOINT_MARK = re.compile(r"(_rank\.|^rank[._]|_views/|^match|^gsv|^sweep|^terrain|^sun|^pose|^sat_scan|^pano|^refsheet|^osm|^tiles?[_/]|^evidence|\.index\.json$)", re.I)
MAX_ACTIVITY = 150
MAX_ARTIFACTS = 400
MAX_AREA_FEATURES = 500                                    # per `mark area` file: the page redraws every feature each frame
AREA_TAGS = ("name", "level", "layer", "indoor", "building", "highway", "ref")   # the OSM tags an area feature keeps


# ---------------------------------------------------------------- session folder

def find_session(arg: str | None) -> Path:
    """The folder holding session.json: the argument (followed through finish's rename), the cwd, or one of its parents."""
    start = Path(arg).expanduser() if arg else Path.cwd()
    if arg and not start.exists():
        start = follow_rename(start)
    start = start.resolve()
    for p in (start, *start.parents):
        if (p / "session.json").is_file():
            return p
    raise SystemExit(f"{start} is not a session folder (no session.json here or above): pass the folder printed by photo_session.py start")


def follow_rename(folder: Path) -> Path:
    """photo_session.py finish renames <timestamp> to <timestamp>__country__region__city; keep serving it."""
    if folder.is_dir():
        return folder
    stem = folder.name.split("__", 1)[0]
    for cand in sorted(folder.parent.glob(stem + "*")):
        if cand.is_dir() and (cand / "session.json").is_file():
            return cand
    return folder


def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))   # -sig: a file rewritten by PowerShell carries a BOM
    except (OSError, ValueError):
        return None


def _read_text(p: Path, limit: int = 200_000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------- geometry

_COUNTRIES: dict | None = None


def countries() -> dict:
    """name/iso2/iso3 (lower-cased) -> countries.json entry."""
    global _COUNTRIES
    if _COUNTRIES is None:
        table = _read_json(COUNTRIES_FILE) or {}
        index: dict[str, dict] = {}
        for code, row in table.items():
            if code.startswith("_") or not isinstance(row, dict):
                continue
            for key in (row.get("name"), row.get("geonames_name"), row.get("iso2"), row.get("iso3"), code):
                if key:
                    index.setdefault(str(key).strip().lower(), row)
        _COUNTRIES = index
    return _COUNTRIES


def bbox_geometry(bbox: list | tuple) -> dict | None:
    """s,w,n,e -> centre and a radius (km) that covers the box."""
    try:
        s, w, n, e = (float(v) for v in bbox)
    except (TypeError, ValueError):
        return None
    lat, lon = (s + n) / 2, (w + e) / 2
    dlat = (n - s) / 2 * 111.0
    dlon = (e - w) / 2 * 111.0 * max(math.cos(math.radians(lat)), 0.05)
    return {"lat": round(lat, 5), "lon": round(lon, 5), "radius_km": round(max(math.hypot(dlat, dlon), 0.05), 3)}


def country_geometry(name: str) -> dict | None:
    row = countries().get(name.strip().lower())
    if not row:
        try:
            row = _board._country(name)           # aliases and local names (geodata.country), when its table is readable
        except Exception:  # noqa: BLE001
            row = None
    if not row or not row.get("center"):
        return None
    geo = bbox_geometry(row["bbox"]) if row.get("bbox") else None
    lat, lon = row["center"]
    return {"lat": lat, "lon": lon, "radius_km": max(geo["radius_km"], 30.0) if geo else 300.0, "iso2": row.get("iso2")}


def candidate_geometry(level: str, cand: dict, name: str) -> dict | None:
    """bbox first (the candidate's extent), else scan_bbox (its built-up part), else the country table."""
    for key in ("bbox", "scan_bbox"):
        if cand.get(key):
            geo = bbox_geometry(cand[key])
            if geo:
                return geo
    if level == "country":
        return country_geometry(name)
    return None


# ---------------------------------------------------------------- state

def gut_candidates(report: str) -> list[dict]:
    """The ranked shortlist of the report's gut call, as candidate rows, for the time before board.py is used."""
    rows, total = [], 0.0
    for name, pct in _ps.gut_call(report):          # the same parser that scores the gut call later
        if not name or name.lower().startswith(("region", "would change")):
            continue
        geo = country_geometry(name)
        rows.append({"name": name, "level": "country", "label": "gut call", "share": pct, "excluded": False,
                     "n_ev": 0, "n_verified": 0, "parent": None, "note": "", "has_geo": geo is not None, **(geo or {})})
        total += pct
    for r in rows:
        r["share"] = round(r["share"] / total, 4) if total else 0.0
    rows.sort(key=lambda r: -r["share"])
    return rows


def candidate_rows(b: dict) -> list[dict]:
    rows = []
    for level in _board.LEVELS:
        for r in _board._scores(b, level, "equal"):
            c = r["c"]
            geo = candidate_geometry(level, c, r["name"])
            rows.append({
                "name": r["name"], "level": level, "label": _board.LEVEL_LABEL.get(level, level),
                "share": round(float(r["share"]), 4), "excluded": bool(r["excluded"]),
                "n_ev": r["n_ev"], "n_verified": r["n_verified"], "parent": c.get("parent"),
                "settled": bool(r.get("settled")), "superseded": bool(r.get("superseded")), "dormant": bool(r.get("dormant")),
                "note": (c.get("note") or "")[:120], "has_geo": geo is not None, **(geo or {}),
            })
    return rows


def coherence_notes(b: dict | None, rows: list[dict]) -> list[str]:
    """Finer candidates without evidence while their parent level is still contested: the page explains the 50/50."""
    if not b:
        return []
    by_level: dict[str, list[dict]] = {}
    for r in rows:
        by_level.setdefault(r["level"], []).append(r)
    notes = []
    for r in rows:
        parent = r.get("parent")
        if r["excluded"] or not parent or r["n_ev"]:
            continue
        pc = b["candidates"].get(parent)
        if not pc:
            continue
        rivals = [x for x in by_level.get(pc["level"], []) if not x["excluded"] and not x.get("dormant") and not x.get("superseded") and x["name"] != parent]
        if rivals:
            notes.append(f"{r['name']} sits under {parent} without any evidence, so {', '.join(x['name'] for x in rivals[:3])} stay{'s' if len(rivals) == 1 else ''} open: "
                         f"record the clue that named {r['name']} (board.py clue + evidence) or settle the country (board.py country)")
    return notes[:4]


def focus_of(session: dict, b: dict | None, rows: list[dict]) -> dict | None:
    """Where the globe points: the finished result, else the top open candidate at the frontier (geometry from the
    nearest ancestor that has one)."""
    result = session.get("result") or {}
    if session.get("status") == "completed" and result.get("latitude") is not None and result.get("longitude") is not None:
        name = ", ".join(str(v) for v in (result.get("city_or_nearest_locality"), result.get("region"), result.get("country")) if v)
        radius_m = result.get("radius_m")
        return {"lat": float(result["latitude"]), "lon": float(result["longitude"]),
                "radius_km": (float(radius_m) / 1000.0) if radius_m else 0.5, "radius_known": bool(radius_m),
                "level": "point", "name": name or "Final answer", "heading": result.get("heading"),
                "heading_hint": (result.get("heading_hint") or {}).get("heading"),
                "confidence": result.get("confidence"), "final": True}
    if not b or not rows:
        return None
    level = _board._frontier(b)
    if not level:
        return None
    top = next((r for r in rows if r["level"] == level and not r["excluded"]), None)
    if not top:
        return None
    by_name = {r["name"]: r for r in rows}
    node: dict | None = top
    while node and not node.get("has_geo"):
        parent = b["candidates"].get(node["name"], {}).get("parent")
        node = by_name.get(parent) if parent else None
    if not node:
        return None
    return {"lat": node["lat"], "lon": node["lon"], "radius_km": node["radius_km"], "level": top["level"],
            "label": top["label"], "name": top["name"], "share": top["share"], "placed_by": node["name"],
            "iso2": node.get("iso2"), "final": False}


# ---------------------------------------------------------------- map layers

def read_marks(folder: Path) -> list[dict]:
    rows = _read_json(folder / MARKS_FILE)
    return [r for r in rows if isinstance(r, dict) and r.get("kind")] if isinstance(rows, list) else []


def write_marks(folder: Path, marks: list[dict]) -> None:
    (folder / MARKS_FILE).write_text(json.dumps(marks, ensure_ascii=False, indent=1), encoding="utf-8")


def destination(lat: float, lon: float, bearing_deg: float, km: float) -> tuple[float, float]:
    """Point km away along a bearing (geolib.geomath.dest), longitude wrapped to [-180, 180)."""
    lat2, lon2 = _dest((lat, lon), bearing_deg, km * 1000)
    return round(lat2, 6), round((lon2 + 540) % 360 - 180, 6)


def _numbers(value) -> list[int | float]:
    """An OSM level or layer value as numbers: '-1' → [-1], '0;1' → [0, 1]; parts that are no number ('B1') are skipped."""
    out = []
    for part in str(value).split(";") if value is not None else ():
        try:
            v = float(part)
        except ValueError:
            continue
        if math.isfinite(v):
            out.append(int(v) if v.is_integer() else v)
    return out


def _paths(geom) -> tuple[list, list]:
    """A GeoJSON geometry as (rings, lines) of [lon, lat] rounded to 1e-6°. A closed LineString is a ring: osm.py writes a closed
    way without a building or area tag (a mall, a platform) as a line. Points and unreadable geometry give ([], [])."""
    if not isinstance(geom, dict):
        return [], []
    kind, coords = geom.get("type"), geom.get("coordinates")
    rings, lines = [], []
    try:
        if kind == "Polygon":
            parts, closed = coords, True
        elif kind == "MultiPolygon":
            parts, closed = [ring for poly in coords for ring in poly], True
        elif kind in ("LineString", "MultiLineString"):
            parts, closed = ([coords] if kind == "LineString" else coords), False
        else:
            return [], []
        for part in parts:
            pts = [[round(float(p[0]), 6), round(float(p[1]), 6)] for p in part]
            if closed or (len(pts) >= 4 and pts[0] == pts[-1]):
                if len(pts) >= 3:
                    rings.append(pts)
            elif len(pts) >= 2:
                lines.append(pts)
    except (TypeError, ValueError, IndexError):
        return [], []
    return rings, lines


def _anchor(rings: list, lines: list) -> tuple[float, float, float]:
    """(lat, lon, radius_km) of a feature: the area centroid of its first ring (its vertex mean when the ring has no area), else
    the middle vertex of its first line; the radius reaches the farthest vertex."""
    if rings:
        ring = rings[0]
        x0, y0 = ring[0]                             # relative to the first vertex: no cancellation for a room 1e-5° wide
        a = cx = cy = 0.0
        for (xa, ya), (xb, yb) in zip(ring, ring[1:] + ring[:1]):
            xa, ya, xb, yb = xa - x0, ya - y0, xb - x0, yb - y0
            k = xa * yb - xb * ya
            a, cx, cy = a + k, cx + (xa + xb) * k, cy + (ya + yb) * k
        if abs(a) > 1e-14:
            lon, lat = x0 + cx / (3 * a), y0 + cy / (3 * a)
        else:
            lon, lat = sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    else:
        lon, lat = lines[0][len(lines[0]) // 2]
    k = math.cos(math.radians(lat))
    r_km = max(math.hypot((p[0] - lon) * k, p[1] - lat) for path in rings + lines for p in path) * 111.32
    return round(lat, 6), round(lon, 6), round(r_km, 4)


def area_mark(path: Path, label: str | None, level: float | None) -> tuple[dict, str]:
    """`mark area`: the rings and lines of a GeoJSON file's first MAX_AREA_FEATURES line or area features, each with its AREA_TAGS,
    its levels and an underground flag (level or layer below 0); --level fills features without a level. Returns the mark and
    the line that reports what was kept, dropped over the cap, and skipped (points, no geometry)."""
    data = _read_json(path)
    kind = data.get("type") if isinstance(data, dict) else None
    if kind == "FeatureCollection" and isinstance(data.get("features"), list):
        raw = data["features"]
    elif kind == "Feature":
        raw = [data]
    elif isinstance(data, dict) and "coordinates" in data:
        raw = [{"geometry": data}]
    else:
        raise SystemExit(f"{path} is not GeoJSON (a FeatureCollection, a Feature or a geometry): mark area reads osm.py geom output")
    feats, skipped = [], {}
    for f in raw:
        f = f if isinstance(f, dict) else {}
        rings, lines = _paths(f.get("geometry"))
        if not rings and not lines:
            geom = f.get("geometry")
            name = str(geom.get("type")) if isinstance(geom, dict) else "no geometry"
            skipped[name] = skipped.get(name, 0) + 1
            continue
        props = f.get("properties") if isinstance(f.get("properties"), dict) else {}
        tags = {k: str(props[k])[:120] for k in AREA_TAGS if props.get(k) not in (None, "")}
        if level is not None and "level" not in tags:
            tags["level"] = f"{level:g}"
        levels = _numbers(tags.get("level"))
        lat, lon, r_km = _anchor(rings, lines)
        feats.append({"id": str(f.get("id") or ""), "tags": tags, "levels": levels, "dashed": any(v < 0 for v in levels + _numbers(tags.get("layer"))),
                      "rings": rings, "lines": lines, "lat": lat, "lon": lon, "r_km": r_km})
    skip_note = f"skipped {sum(skipped.values())} ({', '.join(sorted(skipped))}): not lines or areas" if skipped else ""
    if not feats:
        raise SystemExit(f"{path} holds no line or area to draw ({skip_note or 'no features'}); mark point draws a single place")
    kept, dropped = feats[:MAX_AREA_FEATURES], len(feats) - min(len(feats), MAX_AREA_FEATURES)
    lat, lon = sum(f["lat"] for f in kept) / len(kept), sum(f["lon"] for f in kept) / len(kept)
    k = math.cos(math.radians(lat))
    r_km = max(math.hypot((f["lon"] - lon) * k, f["lat"] - lat) * 111.32 + f["r_km"] for f in kept)
    levels = sorted({v for f in kept for v in f["levels"]})
    mark = {"kind": "area", "source": path.name, "label": label or "", "features": kept, "lat": round(lat, 6), "lon": round(lon, 6),
            "r_km": round(r_km, 4), "dropped": dropped, "skipped": sum(skipped.values())}
    log = "; ".join(x for x in (
        f"area {label or path.name}: {len(kept)} features" + (f", levels {', '.join(f'{v:g}' for v in levels)}" if levels else ", no levels"),
        f"dropped {dropped} over the {MAX_AREA_FEATURES} cap: narrow the query or split the file" if dropped else "", skip_note) if x)
    return mark, log


def ingest_ranks(folder: Path) -> list[dict]:
    """Top rows of the newest match.py rank files: position, heading, score, saved view."""
    files = sorted((p for p in folder.rglob("*.json") if not p.name.endswith(".index.json") and p.name not in SKIP_FILES
                    and p.name not in ("result.json", MARKS_FILE) and ".geo-cache" not in p.parts and p.stat().st_size < 20_000_000),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    out, seen, used = [], set(), 0
    for f in files:
        if used >= 8:
            break
        rows = _read_json(f) if RANK_NAME.search(f.name) or f.stat().st_size < 4_000_000 else None
        if not (isinstance(rows, list) and rows and isinstance(rows[0], dict) and "rank" in rows[0] and "wgs" in rows[0]):
            continue                              # a match.py rank file is known by its rows, not by its name
        used += 1
        for r in rows[:10]:
            if not isinstance(r, dict):
                continue
            wgs = r.get("wgs")
            if not (isinstance(wgs, list) and len(wgs) == 2):
                continue
            key = (str(r.get("id")), r.get("heading"))
            if key in seen:
                continue
            seen.add(key)
            view = None
            if r.get("view"):
                p = f.parent / r["view"]
                if p.is_file():
                    view = "/files/" + p.relative_to(folder).as_posix()
            out.append({"lat": wgs[0], "lon": wgs[1], "heading": r.get("heading"), "score": r.get("score_global"),
                        "inliers": r.get("inliers"), "rank": r.get("rank"), "id": str(r.get("id") or ""),
                        "source": f.relative_to(folder).as_posix(), "view": view, "label": r.get("label") or r.get("road") or ""})
    out.sort(key=lambda m: (-(m["inliers"] or 0), -(m["score"] or 0)))
    return out[:MAX_MATCHES]


def index_files(folder: Path) -> list[Path]:
    """Panorama lists: *.index.json anywhere, plus top-level JSON lists written without the suffix (gsv.py area --out name)."""
    files = list(folder.rglob("*.index.json"))
    for f in folder.iterdir():
        if f.is_file() and f.suffix in ("", ".json") and f.name not in SKIP_FILES and not f.name.endswith(("_rank.json", "result.json", MARKS_FILE)) \
                and f.stat().st_size < 20_000_000 and f not in files:
            files.append(f)
    return sorted(files)[:24]


def ingest_coverage(folder: Path) -> list[dict]:
    """Every panorama of the session's panorama lists, thinned to MAX_COVERAGE, with what its card shows.
    gsv.py area/targets: {id: {wgs, date, road}} or a list of {id, wgs, …}; pano.py list/index: {id: {provider, id, lat, lon,
    heading, low/high: {url}}} or a list of those. Ranked lists (match.py) are the Matches layer, not coverage."""
    pts = []
    for f in index_files(folder):
        items = _read_json(f)
        if isinstance(items, dict):
            items = [{"id": k, **v} if isinstance(v, dict) else v for k, v in items.items()]
        if not (isinstance(items, list) and items and isinstance(items[0], dict)) or "rank" in items[0]:
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            w = it.get("wgs")
            if isinstance(w, list) and len(w) == 2:
                lat, lon = w
            elif isinstance(it.get("lat"), (int, float)) and isinstance(it.get("lon"), (int, float)):
                lat, lon = it["lat"], it["lon"]
            else:
                continue
            try:
                lat, lon = float(lat), float(lon)
            except (TypeError, ValueError):
                continue
            spec = it.get("high") if isinstance(it.get("high"), dict) else it.get("low") if isinstance(it.get("low"), dict) else {}
            url = it.get("url") or spec.get("url")
            pts.append({"lat": round(lat, 5), "lon": round(lon, 5), "id": (str(it.get("id"))[:80] if it.get("id") is not None else None),
                        "provider": it.get("provider") or None, "date": it.get("date") or None, "road": it.get("road") or it.get("name") or None,
                        "heading": it["heading"] if isinstance(it.get("heading"), (int, float)) else None,
                        "url": url if isinstance(url, str) and url.startswith("http") else None, "list": f.name})
    if len(pts) > MAX_COVERAGE:
        pts = pts[:: max(1, len(pts) // MAX_COVERAGE)]
    return pts


def map_layers(folder: Path) -> dict:
    marks = read_marks(folder)
    for m in marks:
        if m.get("file"):                                 # image marks, and point marks with --image: the card shows the file
            m["url"] = "/files/" + m["file"] if (folder / m["file"]).is_file() else None
    areas = [m for m in marks if m["kind"] == "area" and isinstance(m.get("features"), list)]
    return {"cameras": [m for m in marks if m["kind"] == "camera"], "lines": [m for m in marks if m["kind"] == "line"],
            "points": [m for m in marks if m["kind"] == "point"], "images": [m for m in marks if m["kind"] == "image"],
            "areas": areas, "levels": sorted({v for a in areas for f in a["features"] if isinstance(f, dict) for v in f.get("levels") or []}),
            "matches": ingest_ranks(folder), "coverage": ingest_coverage(folder)}


def gut_focus(session: dict, rows: list[dict]) -> dict | None:
    """Before any board: the finished result, else the gut call leader that has a position."""
    final = focus_of(session, None, [])
    if final:
        return final
    top = next((r for r in rows if r.get("has_geo")), None)
    if not top:
        return None
    return {"lat": top["lat"], "lon": top["lon"], "radius_km": top["radius_km"], "level": "country", "label": "gut call",
            "name": top["name"], "share": top["share"], "placed_by": top["name"], "iso2": top.get("iso2"), "final": False}


def list_artifacts(folder: Path) -> list[dict]:
    out = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for f in files:
            if f in SKIP_FILES or f.startswith("."):
                continue
            p = Path(root) / f
            ext = p.suffix.lower()
            kind = "image" if ext in IMAGE_EXT else "text" if ext in TEXT_EXT else "other"
            try:
                st = p.stat()
            except OSError:
                continue
            rel = p.relative_to(folder).as_posix()
            out.append({"path": rel, "url": "/files/" + rel, "kind": kind, "mtime": st.st_mtime,
                        "time": _iso(st.st_mtime), "size": st.st_size})
    out.sort(key=lambda a: (-a["mtime"], a["path"]))
    return out[:MAX_ARTIFACTS]


def read_activity(folder: Path) -> list[dict]:
    lines = []
    for raw in _read_text(folder / ACTIVITY_FILE).splitlines():
        try:
            row = json.loads(raw)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("text"):
            lines.append({"time": row.get("t", ""), "text": str(row["text"]), "source": "say"})
    return lines


def board_activity(b: dict | None) -> list[dict]:
    if not b:
        return []
    day = (b.get("updated") or b.get("created") or "")[:10]
    out = []
    for entry in b.get("log", []):
        m = re.match(r"(\d\d:\d\d)\s+(.*)", str(entry))
        if m:
            out.append({"time": f"{day}T{m.group(1)}:00", "text": m.group(2), "source": "board"})
        else:
            out.append({"time": "", "text": str(entry), "source": "board"})
    return out


def stage_of(session: dict, b: dict | None, artifacts: list[dict], folder: Path) -> str:
    """The stage a step is *in*, from its first trace on disk (a folder being filled counts), never only from its end."""
    if session.get("status") == "completed":
        return "Done"
    names = [a["path"] for a in artifacts]
    if any(n.startswith(("evidence", "verify/")) or n == "result.json" for n in names) or (folder / "verify").is_dir():
        return "Verify"
    if any(PINPOINT_MARK.search(n.rsplit("/", 1)[-1]) or PINPOINT_MARK.search(n) for n in names) or (folder / MARKS_FILE).is_file():
        return "Pinpoint"
    if b and b.get("candidates"):
        return "Candidates"
    if (folder / "recon").is_dir():                # recon.py creates its folder first and fills it for a minute
        return "Recon"
    return "Gut call"                              # a session starts with the gut call, written or not yet


def build_state(folder: Path, tiles: str = "esri") -> dict:
    folder = follow_rename(folder)
    if not folder.is_dir():
        gone = {"folder": str(folder), "name": folder.name, "title": folder.name, "photos": [], "status": "pending", "stage": "Gut call",
                "stages": STAGES, "focus": None, "candidates": [], "candidates_source": "board", "coherence": [], "clues": [], "evidence": [],
                "now": "", "warning": f"the session folder is gone: {folder}", "activity": [], "artifacts": [], "report_md": "", "recon_md": "",
                "tiles": tiles, "layers": {"cameras": [], "lines": [], "points": [], "images": [], "areas": [], "levels": [], "matches": [], "coverage": []},
                "analysis_images": []}
        gone["version"] = hashlib.sha1(json.dumps(gone, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        return gone
    session = _read_json(folder / "session.json") or {}
    warning = None
    result = session.get("result") or {}
    if result and result.get("latitude") is not None:
        try:                                              # the When text and the heading hint of older sessions
            if not result.get("when_text"):
                result["when_text"] = _ps.when_text(_read_text(folder / "report.md"))
            if result.get("heading") is None and not result.get("heading_hint"):
                result["heading_hint"] = _ps.heading_hint(folder, float(result["latitude"]), float(result["longitude"]))
            session = {**session, "result": result}
        except Exception:  # noqa: BLE001  (best effort: the page must never fail on an old session)
            pass
    generated = session.get("status") == "completed" and _ps.outcome(result) == "generated"   # finish --generated: done, with no place
    if session.get("status") == "completed" and result.get("latitude") is None and not generated:
        # closed by hand (status edited, no answer): photo_session.py finish never does this; keep the page in analysis mode
        session = {**session, "status": "pending"}
        warning = "session.json says completed but holds no answer: close the session with photo_session.py finish (coordinates and a radius), never by editing the file"
    b = _read_json(folder / "board.json")
    rows = candidate_rows(b) if b and b.get("candidates") else []
    source = "board"
    report = _read_text(folder / "report.md")
    if not rows:                                   # quick mode often never touches the board: show the gut call instead
        rows = gut_candidates(report)
        source = "gut" if rows else "board"
    recon = _read_text(folder / "recon" / "recon.md")
    artifacts = list_artifacts(folder)
    originals = session.get("originals") or ([session["original"]] if session.get("original") else [])
    photos = [{"path": r["relative_path"], "url": "/files/" + r["relative_path"], "name": Path(r["relative_path"]).name}
              for r in originals if r and r.get("relative_path")]
    original_paths = {p["path"] for p in photos}
    activity = read_activity(folder) + board_activity(b)
    for a in artifacts:
        if a["path"] in original_paths:
            continue
        activity.append({"time": a["time"], "text": a["path"], "source": "file", "url": a["url"], "kind": a["kind"]})
    activity.sort(key=lambda e: e["time"], reverse=True)
    said = [e for e in activity if e["source"] == "say"]   # before the cut: 150 new files must not hide the current step
    activity = activity[:MAX_ACTIVITY]
    now = said[0]["text"] if said else (activity[0]["text"] if activity else "")
    state = {
        "folder": str(folder), "name": folder.name, "title": photos[0]["name"] if photos else folder.name, "photos": photos,
        "status": session.get("status", "pending"), "started_at": session.get("started_at"),
        "completed_at": session.get("completed_at"), "result": session.get("result"), "truth": _ps.current_truth(folder, session),
        "photo_url": photos[0]["url"] if photos else None,
        "stage": stage_of(session, b, artifacts, folder), "stages": STAGES,
        "focus": None if generated else focus_of(session, b, rows) if source == "board" else gut_focus(session, rows),
        "aidet": _ps.detector(folder), "generated_override": session.get("generated_override"),
        "candidates": rows, "candidates_source": source, "coherence": coherence_notes(b, rows) if source == "board" else [],
        "clues": [{"id": k, **v} for k, v in (b or {}).get("clues", {}).items()],
        "evidence": (b or {}).get("evidence", []),
        "now": now, "warning": warning, "activity": activity, "artifacts": artifacts,
        "layers": map_layers(folder),
        "analysis_images": [a for a in artifacts if a["kind"] == "image" and a["path"] not in original_paths
                            and "_views/" not in a["path"] and not a["path"].endswith("_skyline.jpg") and ANALYSIS_MARK.search(a["path"])][:24],
        "skyline": skyline_of(folder, artifacts),
        "checks": _checks_of(folder),
        "report_md": report, "recon_md": recon, "tiles": tiles,
    }
    state["version"] = hashlib.sha1(json.dumps(state, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
    return state


def _checks_of(folder: Path) -> list[dict]:
    """The scene's required checks as `checks` and `say` report them: done, waived, skipped or missing
    (photo_session._checks_with_waiver), never fatal."""
    try:
        return [{k: c.get(k) for k in ("name", "why", "done", "files", "waived_by", "skipped")} for c in _ps._checks_with_waiver(folder)]
    except Exception:  # noqa: BLE001
        return []


def skyline_of(folder: Path, artifacts: list[dict]) -> dict | None:
    """The newest Skyline card: terrain.py fit --sheet writes <sheet>_skyline.json beside <sheet>_skyline.jpg (top 3 stacked)."""
    for a in artifacts:                                       # newest first
        if not a["path"].endswith("_skyline.json"):
            continue
        side = _read_json(folder / a["path"]) or {}
        img = a["path"][:-len(".json")] + ".jpg"
        if not side.get("top") or not (folder / img).exists():
            continue
        return {"image": "/files/" + img, "json": a["url"], "fit": side.get("fit"), "top": side["top"], "time": a["time"]}
    return None


def open_folder(folder: Path) -> None:
    """Show the session folder in the file manager (Explorer, Finder, or the desktop's opener)."""
    if sys.platform.startswith("win"):
        os.startfile(str(folder))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(folder)])
    else:
        subprocess.Popen(["xdg-open", str(folder)])


# ---------------------------------------------------------------- offline snapshot

SNAPSHOT_NAME = "viewer.html"
STOP_GRACE_S = 3.5


def _relative_urls(value):
    """'/files/x' -> 'x': the snapshot sits in the session folder, so every served file is a relative link."""
    if isinstance(value, dict):
        return {k: _relative_urls(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_relative_urls(v) for v in value]
    if isinstance(value, str) and value.startswith("/files/"):
        return value[len("/files/"):]
    return value


def export_html(folder: Path, out: Path | None = None, tiles: str = "esri") -> Path:
    """The live page as one HTML file (state, outlines, CSS and JS inlined; links relative) saved beside the photos."""
    folder = follow_rename(folder)
    state = _relative_urls(build_state(folder, tiles))
    state["snapshot_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    html = (UI_DIR / "index.html").read_text(encoding="utf-8")
    css = (UI_DIR / "style.css").read_text(encoding="utf-8")
    js = (UI_DIR / "app.js").read_text(encoding="utf-8")
    countries = (UI_DIR / "countries.json").read_text(encoding="utf-8")
    payload = json.dumps(state, ensure_ascii=False, default=str).replace("</", "<\\/")
    html = html.replace('<link rel="stylesheet" href="/style.css">', "<style>\n" + css + "\n</style>")
    html = html.replace('<script src="/app.js"></script>',
                        "<script>window.GEO_STATE = " + payload + ";\nwindow.GEO_COUNTRIES = " + countries.replace("</", "<\\/") + ";</script>\n"
                        "<script>\n" + js + "\n</script>")
    target = out or (folder / SNAPSHOT_NAME)
    target.write_text(html, encoding="utf-8")
    return target


# ---------------------------------------------------------------- server

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, session: Path, tiles: str, **kwargs):
        self.session = session
        self.tiles = tiles
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def log_request(self, code="-", size="-"):  # quiet: only failed requests reach the terminal
        if str(code).startswith(("4", "5")):
            sys.stderr.write(f"viewer: {code} {self.requestline}\n")

    def log_error(self, fmt, *args):
        sys.stderr.write("viewer: " + (fmt % args) + "\n")

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def end_headers(self):  # every reply, static files included: the page and app.js must never come from the browser cache
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _local(self) -> bool:
        """Only the page served here may call the API: Host must be this loopback server, a foreign Origin is refused."""
        host = (self.headers.get("Host") or "").split(":")[0].strip("[]").lower()
        if host not in ("127.0.0.1", "localhost", "::1"):
            return False
        origin = self.headers.get("Origin")
        if origin and origin != "null":
            ohost = urlsplit(origin).hostname or ""
            if ohost.lower() not in ("127.0.0.1", "localhost", "::1"):
                return False
        return True

    def do_GET(self):  # noqa: N802
        self.server.last_seen = time.time()
        if not self._local():
            self._send(403, b"viewer: local page only", "text/plain")
            return
        path = unquote(urlsplit(self.path).path)
        if path == "/api/state":
            state = build_state(self.session, self.tiles)
            stopping = getattr(self.server, "stopping", None)
            if stopping:                                   # the last polls before shutdown carry the final state and the snapshot path
                state["stopping"] = True
                state["snapshot"] = str(stopping)
                state["version"] = state["version"] + "-stop"
            etag = '"' + state["version"] + '"'
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.end_headers()
                return
            self._send(200, json.dumps(state, ensure_ascii=False, default=str).encode("utf-8"),
                       "application/json; charset=utf-8", {"ETag": etag})
            return
        if path.startswith("/files/"):
            self._serve_session_file(path[len("/files/"):])
            return
        if path == "/":
            self.path = "/index.html"
        if "/" in path.strip("/"):
            self._send(404, b"not found", "text/plain")
            return
        super().do_GET()

    def do_POST(self):  # noqa: N802
        self.server.last_seen = time.time()
        if not self._local():
            self._send(403, b"viewer: local page only", "text/plain")
            return
        path = unquote(urlsplit(self.path).path)
        if path == "/api/open":
            try:
                open_folder(follow_rename(self.session))
            except OSError as exc:
                self._send(500, str(exc).encode("utf-8"), "text/plain; charset=utf-8")
                return
            self._send(204, b"", "text/plain")
            return
        if path == "/api/stop":                       # Close button or viewer.py stop: the analysis goes on
            snapshot = None
            try:
                snapshot = export_html(self.session, tiles=self.tiles)   # the page survives as a file beside the photos
            except OSError as exc:
                sys.stderr.write(f"viewer: snapshot not written ({exc})\n")
            self.server.stopping = snapshot or follow_rename(self.session) / SNAPSHOT_NAME
            self._send(204, b"", "text/plain")
            # one more poll cycle: the open page must see the final state (Done after finish) before the server is gone
            threading.Timer(STOP_GRACE_S, self.server.shutdown).start()
            return
        self._send(404, b"not found", "text/plain")

    def _serve_session_file(self, rel: str) -> None:
        folder = follow_rename(self.session).resolve()
        target = (folder / rel).resolve()
        if folder not in (target, *target.parents) or not target.is_file():
            self._send(404, b"not found", "text/plain")
            return
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/json",):
            ctype += "; charset=utf-8"
        try:
            self._send(200, target.read_bytes(), ctype)
        except OSError:
            self._send(404, b"not found", "text/plain")


class _Server(http.server.ThreadingHTTPServer):
    # On Windows SO_REUSEADDR lets a second viewer bind a port another viewer still listens on, and the old one keeps
    # answering; an exclusive bind makes the second start fail loudly instead. POSIX keeps the quick-restart behaviour.
    allow_reuse_address = os.name != "nt"


def record_viewer_url(session: Path, url: str) -> None:
    """viewer_url in session.json: how `stop <session>`, the page's reader and the analyst find this viewer (never fatal)."""
    p = session / "session.json"
    try:
        meta = json.loads(p.read_text(encoding="utf-8-sig"))
        if meta.get("viewer_url") != url:
            meta["viewer_url"] = url
            _ps.save_json(p, meta)                        # atomic, like every other session.json write
    except (OSError, ValueError):
        pass


def make_server(session: Path, port: int, tiles: str) -> http.server.ThreadingHTTPServer:
    handler = partial(Handler, session=session, tiles=tiles)
    server = _Server(("127.0.0.1", port), handler)
    server.daemon_threads = True
    server.last_seen = time.time()
    return server


def start_watchdog(server: http.server.ThreadingHTTPServer, idle_seconds: float, tick: float = 5.0) -> threading.Thread:
    """Shut the server down once no request has arrived for idle_seconds: a viewer nobody reads must not keep running."""
    def run():
        while True:
            time.sleep(min(tick, idle_seconds))
            if time.time() - server.last_seen > idle_seconds:
                server.shutdown()
                return
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def viewer_port(session_arg: str | None, port: int | None) -> int:
    """--port, else the port photo_session.py start --viewer recorded in session.json, else the default."""
    if port is not None:
        return port
    try:
        meta = _read_json(find_session(session_arg) / "session.json") or {}
    except SystemExit:
        meta = {}
    m = re.search(r":(\d+)/?$", meta.get("viewer_url") or "")
    if not m:
        raise SystemExit("no viewer_url in session.json and no --port given: which viewer? (ports are random; the URL is printed by serve)")
    return int(m.group(1))


def cmd_serve(args) -> int:
    session = find_session(args.session)
    if not (UI_DIR / "index.html").is_file():
        raise SystemExit(f"viewer page missing: {UI_DIR}")
    port = 0 if args.port is None else args.port       # a random free port every time: parallel analyses never collide
    try:
        server = make_server(session, port, args.tiles)
    except OSError as exc:
        raise SystemExit(f"cannot listen on 127.0.0.1:{port} ({exc}): omit --port to get a free one") from exc
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    record_viewer_url(session, url)
    print(f"Viewer: {url}  (session {session.name}; Ctrl+C stops)", flush=True)
    if args.idle_minutes > 0:
        start_watchdog(server, args.idle_minutes * 60)
    if args.open:
        threading.Timer(0.3, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    print("Viewer stopped.", flush=True)
    return 0


def cmd_say(args) -> int:
    session = find_session(args.session)
    text = " ".join(args.text).strip()
    if not text:
        raise SystemExit("say needs a text")
    line = json.dumps({"t": datetime.now().astimezone().isoformat(timespec="seconds"), "text": text}, ensure_ascii=False)
    with (session / ACTIVITY_FILE).open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print("said · " + _ps.status_line(session))     # recorded first: the line confirms the say and reads the session's state
    return 0


def served_session(port: int) -> Path | None:
    """The folder the viewer on this port serves (None when nothing answers)."""
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/api/state")
        r = conn.getresponse()
        state = json.loads(r.read()) if r.status == 200 else {}
        conn.close()
    except (OSError, ValueError):
        return None
    return Path(state["folder"]) if state.get("folder") else None


def cmd_stop(args) -> int:
    port = viewer_port(args.session, args.port)
    served = served_session(port)
    if served is None:
        print(f"No viewer answering on 127.0.0.1:{port}")
        return 1
    if not args.force:
        # parallel sessions share the default port: only the viewer of the named (or current) session may be stopped
        try:
            wanted = find_session(args.session)
        except SystemExit:
            wanted = None
        mine = wanted is not None and (served.resolve() == wanted.resolve() or follow_rename(wanted).resolve() == served.resolve())
        if not mine:
            print(f"The viewer on 127.0.0.1:{port} serves {served.name}, not {wanted.name if wanted else 'a session of yours'}: "
                  f"left running. Pass that session folder, or --force to stop it anyway.")
            return 2
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("POST", "/api/stop")
        status = conn.getresponse().status
        conn.close()
    except OSError:
        print(f"No viewer answering on 127.0.0.1:{port}")
        return 1
    if status == 204:
        deadline = time.time() + STOP_GRACE_S + 6
        while time.time() < deadline and served_session(port) is not None:
            time.sleep(0.5)                                # the server lingers a few seconds for the page's last poll
        print(f"Viewer on 127.0.0.1:{port} stopped ({served.name}); offline copy: {follow_rename(served) / SNAPSHOT_NAME}")
        return 0
    print(f"Viewer on 127.0.0.1:{port} answered {status}")
    return 1


def cmd_mark(args) -> int:
    session = find_session(args.session)
    marks = read_marks(session)
    if args.what == "list":
        for i, m in enumerate(marks):
            brief = {**m, "features": len(m["features"])} if isinstance(m.get("features"), list) else m   # an area: its count, not its rings
            print(i, json.dumps(brief, ensure_ascii=False))
        return 0
    if args.what == "clear":
        keep = [m for m in marks if args.kind and m["kind"] != args.kind]
        write_marks(session, keep)
        print(f"{len(marks) - len(keep)} marks removed")
        return 0
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    needed = {"camera": ("lat", "lon", "heading"), "point": ("lat", "lon", "label"), "image": ("file", "lat", "lon"), "line": ("from_",),
              "area": ("file",)}
    missing = [f"--{n.rstrip('_')}" for n in needed.get(args.what, ()) if getattr(args, n, None) in (None, "")]
    if missing:
        raise SystemExit(f"mark {args.what} needs {', '.join(missing)} (see viewer.py --help)")
    log = None
    if args.what == "area":
        f = Path(args.file).expanduser()
        if not f.is_file():
            raise SystemExit(f"{args.file} is not a file")
        mark, log = area_mark(f, args.label, args.level)
        mark["t"] = stamp
    elif args.what == "camera":
        mark = {"kind": "camera", "lat": args.lat, "lon": args.lon, "heading": args.heading % 360, "fov": args.fov,
                "label": args.label or "camera", "radius_m": args.radius_m, "t": stamp}
    elif args.what == "point":
        mark = {"kind": "point", "lat": args.lat, "lon": args.lon, "label": args.label, "t": stamp}
        if args.image:
            mark["file"] = Path(args.image).resolve().relative_to(session).as_posix() if Path(args.image).resolve().is_relative_to(session) else None
    elif args.what == "image":
        f = Path(args.file).resolve()
        if not f.is_file():
            raise SystemExit(f"{args.file} is not a file")
        if not f.is_relative_to(session):
            raise SystemExit(f"{args.file} must live inside the session folder so the page can show it")
        mark = {"kind": "image", "file": f.relative_to(session).as_posix(), "lat": args.lat, "lon": args.lon,
                "heading": (args.heading % 360) if args.heading is not None else None, "label": args.label or f.name, "t": stamp}
    else:  # line
        a = [float(v) for v in args.from_.split(",")]
        if args.to:
            b = [float(v) for v in args.to.split(",")]
        elif args.bearing is not None and args.km:
            b = list(destination(a[0], a[1], args.bearing, args.km))
        else:
            raise SystemExit("line needs --to lat,lon, or --bearing and --km")
        mark = {"kind": "line", "from": a, "to": b, "bearing": args.bearing, "label": args.label or "", "t": stamp}
    marks.append(mark)
    write_marks(session, marks)
    print(log or json.dumps(mark, ensure_ascii=False))
    if args.what == "camera":                     # a cone drawn after finish does not change the answer: name the correction path
        meta = _read_json(session / "session.json")
        result = meta.get("result") if isinstance(meta, dict) and meta.get("status") == "completed" else None
        if isinstance(result, dict) and _ps.outcome(result) == "place":
            rh, h = result.get("heading"), mark["heading"]
            rh = rh if isinstance(rh, (int, float)) else None
            if rh is None or abs((rh - h + 180) % 360 - 180) > (args.fov or 90) / 2:
                print(f"Note: the answer in session.json has heading {'unknown' if rh is None else f'{rh:.0f}°'}; this cone is only drawn on "
                      f"the map. To make it the answer, run photo_session.py finish \"{session}\" again with the same flags and --heading {h:.0f}.",
                      file=sys.stderr)
    return 0


def cmd_export(args) -> int:
    session = find_session(args.session)
    out = export_html(session, Path(args.out) if args.out else None, args.tiles)
    print(f"-> {out}")
    return 0


def cmd_state(args) -> int:
    print(json.dumps(build_state(find_session(args.session), args.tiles), ensure_ascii=False, indent=1, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="serve the live page for one session")
    s.add_argument("session", nargs="?", help="session folder (default: cwd or a parent holding session.json)")
    s.add_argument("--port", type=int, default=None, help="127.0.0.1 port (default: a random free one, recorded in session.json)")
    s.add_argument("--open", action="store_true", help="open the page in the default browser")
    s.add_argument("--tiles", choices=("esri", "osm"), default="esri", help="close-up tile source fetched by the browser")
    s.add_argument("--idle-minutes", type=float, default=30.0, help="exit after this long without any request (0 = never)")
    s.set_defaults(fn=cmd_serve)
    k = sub.add_parser("stop", help="stop a running viewer")
    k.add_argument("session", nargs="?", help="session folder whose session.json records the viewer port")
    k.add_argument("--port", type=int, help="port of the viewer to stop (default: viewer_url in session.json)")
    k.add_argument("--force", action="store_true", help="stop whatever viewer answers on that port, even another session's")
    k.set_defaults(fn=cmd_stop)
    y = sub.add_parser("say", help="record what the analysis is doing now; prints the session's status line")
    y.add_argument("text", nargs="+")
    y.add_argument("--session", help="session folder (default: cwd or a parent)")
    y.set_defaults(fn=cmd_say)
    m = sub.add_parser("mark", help="put a camera, line, point, image or area outline on the map")
    m.add_argument("what", choices=("camera", "line", "point", "image", "area", "list", "clear"))
    m.add_argument("file", nargs="?", help="image: a file inside the session folder; area: a GeoJSON file (osm.py geom output)")
    m.add_argument("--session", help="session folder (default: cwd or a parent)")
    m.add_argument("--lat", type=float)
    m.add_argument("--lon", type=float)
    m.add_argument("--heading", type=float, help="degrees clockwise from north")
    m.add_argument("--fov", type=float, default=90.0, help="camera: horizontal field of view in degrees")
    m.add_argument("--radius-m", type=float, help="camera: position uncertainty")
    m.add_argument("--from", dest="from_", help="line: lat,lon")
    m.add_argument("--to", help="line: lat,lon")
    m.add_argument("--bearing", type=float, help="line: degrees from --from")
    m.add_argument("--km", type=float, help="line: length when given as a bearing")
    m.add_argument("--label")
    m.add_argument("--image", help="point: a file inside the session folder to show on its card")
    m.add_argument("--level", type=float, help="area: the level of features that carry none (-1: one floor below ground, drawn dashed)")
    m.add_argument("--kind", choices=("camera", "line", "point", "image", "area"), help="clear: only this kind")
    m.set_defaults(fn=cmd_mark)
    e = sub.add_parser("export", help="write the self-contained viewer.html snapshot beside the photos")
    e.add_argument("session", nargs="?")
    e.add_argument("--out", help="target file (default: <session>/viewer.html)")
    e.add_argument("--tiles", choices=("esri", "osm"), default="esri")
    e.set_defaults(fn=cmd_export)
    t = sub.add_parser("state", help="print the page's JSON once")
    t.add_argument("session", nargs="?")
    t.add_argument("--tiles", choices=("esri", "osm"), default="esri")
    t.set_defaults(fn=cmd_state)
    from geolib.cli import neg_coords
    args = ap.parse_args(neg_coords(list(sys.argv[1:]) if argv is None else list(argv)))
    return args.fn(args)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
