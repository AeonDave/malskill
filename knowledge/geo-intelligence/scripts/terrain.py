#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy", "tzdata"]
# ///
"""Use elevation data to "look" out from a candidate camera position: synthesize a layered terrain view and skyline to compare ridgelines with the photo.

When there is no street view, only distant mountains (group photos in the mountains, views across a river, aerial shots, a ridgeline outside a window), this replaces Google Earth oblique 3D.
Elevation comes from AWS Terrain Tiles (Terrarium encoding, ~30 m worldwide, no key).

  view     render from one camera position by heading and field of view: shading layered by distance + red skyline + bearing ticks; can be stacked above/below the photo
  profile  output the skyline elevation angle and distance at each bearing (JSON), for numeric comparison
  elev     look up the ground elevation at a point, or at every point of a {name:[lat,lon]} file (--points)
  slope    per candidate point: elevation ±span/2 along a bearing → cross-slope % (does the ground rise to the left as in the photo?)
  scan     along linear infrastructure (railway, road, power line), compute the 360° horizon point by point, keep the points that are "flat nearby + a mountain + the mountain right next to a stretch of flat horizon"
           and cluster them — when the frame shows only one piece of infrastructure and a mountain you can't recognize, use it to cut a whole large region down to a few hundred patches
  ridge    sample the photo's ridgeline: per column, find the sky-to-mountain brightness jump; output a pixel point list + flat-horizon column range + horizon row + focal length (ridge.json)
  shade    where the shadows lie at a place and time: terrain (and OSM buildings) cast shadows on a map, point checks "lit or in shadow",
           and the inverse sweep: which times of a day (or which days) leave the given points lit / shaded — the local ShadeMap
  fit      score each scan cluster against ridge.json: lay a camera-position grid in each cluster, search heading × focal length × horizon offset,
           skyline RMS + flat-horizon penalty (+ optional: near layer of a two-layer photo, heading perpendicular to a line, how far the linear
           infrastructure is at the frame's left/center/right), sort by score, --sheet draws overlays of the top N

Important: a matching skyline outline only shows that the camera position is near some sight line — moving a few hundred meters forward or back along the sight line barely changes the distant mountain outline.
To pin a point you need a second independent constraint (another near–far object alignment, a road or riverbank on the map). See references/geometry.md.

Examples:
  terrain.py elev --at 35.3606,138.7274
  terrain.py elev --points cands.json --out elev.json                       # batch: one row per candidate
  terrain.py slope --points cands.json --bearing 40 --span 60 --out slope.json   # + = ground rises toward 40°; camera heading 310 → right side of the frame
  terrain.py view --at 35.4983,138.7688 --heading 194 --hfov 50 --range 30000 --out fuji.png   # Mt. Fuji from Lake Kawaguchi
  terrain.py view --at <candidate camera position> --height 20 --heading <heading> --hfov 65 --out v.png --photo photo.jpg
  terrain.py profile --at 35.4983,138.7688 --heading 194 --hfov 50 --out prof.json
  terrain.py scan --lines rail_bridges.geojson --bbox 35.1,138.3,36.0,139.2 --out hits.json   # get the lines with osm.py geom first
  terrain.py ridge photo.jpg --x0 760 --x1 1260 --step 20 --flat 0:280 --out ridge.json --png ridge.png
  terrain.py ridge photo.jpg --points "X,Y;X,Y;..." --near "X,Y;X,Y;..." --near-clear X0:X1@ROW --hrow ROW --out ridge.json   # two-layer
  terrain.py fit --hits hits.json --ridge ridge.json --out fit.json --sheet top.jpg            # coarse search: per cluster 2 km / 250 m / z11;
                                                                                             # --sheet also writes top_skyline.jpg/.json (top 3 stacked over the photo, the live page's Skyline card)
  terrain.py fit --at <lat,lon> --ridge ridge.json --sheet top.jpg --peaks peaks.geojson      # names the summits on the skyline (osm.py geom '["natural"="peak"]["name"]')
  terrain.py fit --at 35.4983,138.7688 --ridge ridge.json --radius 800 --grid 100 --zoom 13 --az-step 0.25 \\
             --line rail.geojson --line-dist 350-750:550-900:800-1700 --out fine.json          # fine search + infrastructure distance constraint
  terrain.py fit --hits hits.json --ridge ridge.json --range 45000 --min-peak 2 --perp-line lines.geojson --out fit.json   # far range + wires overhead
  terrain.py shade --at 46.2563,10.9450 --time 2025-07-20T14:30 --tz Europe/Rome --radius 2500 --out shade.png \
             --check 46.2585,10.9560:east-wall --check 46.2628,10.9536:beach                     # shadows now; is each point lit?
  terrain.py shade --at 46.2563,10.9450 --date 2025-07-20 --tz Europe/Rome --lit 46.2585,10.9560:east-wall --shaded 46.2628,10.9536:beach
                                                                                             # which times of that day show this pattern
  terrain.py shade --at <lat,lon> --dates 2025-01-01:2025-12-31 --date-step 7 --tz <zone> --lit <lat,lon> --shaded <lat,lon> --json when.json
  terrain.py shade --at <lat,lon> --time <local time> --tz <zone> --map area.jpg --buildings b.geojson --out shade.png   # over tiles.py imagery, OSM buildings

For the fields of ridge.json and fit.json, see each subcommand's --help.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime
from geolib.net import curl_args, PROXY_HELP
import json
import math
import os
import re
import shlex
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import geo  # noqa: E402

TILE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
R_EARTH = 6371008.8
K_REFRACTION = 0.13
F35_RANGE = (13.0, 135.0)          # fit's focal ladder when the photo has no EXIF focal length: 0.5x ultra-wide to ~5x telephoto
F35_RATIO = 1.18                   # step between ladder rungs
CHECKPOINT_S = 30.0                # fit rewrites --out at most this often while scoring, and always after the last cluster
REPLACE_TRIES, REPLACE_WAIT_S = 10, 0.1   # Windows refuses os.replace while a reader (the live viewer's poll, `say`) holds the target


FETCH_TRIES = 4
MISSING_HELP = ("fill tiles that still fail after retries as missing (skipped in scan/fit, see-through in view/profile) instead of exiting; "
                "default: any failed tile is an error, because treating it as 0 m silently fakes sea-level terrain")


def _decode(p: Path) -> np.ndarray | None:
    """Decode a cached Terrarium tile; None if it is not a valid 256×256 image (truncated download, HTTP error body)."""
    try:
        with Image.open(p) as im:
            if im.size != (256, 256):
                return None
            a = np.asarray(im.convert("RGB"), dtype=np.float32)
    except Exception:  # noqa: BLE001
        return None
    return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768


def _fetch(z: int, x: int, y: int, cache: Path, proxy: str | None) -> np.ndarray | None:
    """Elevation of one tile, or None if it could not be downloaded after FETCH_TRIES attempts. Never caches a bad response."""
    p = cache / f"terrarium_{z}_{x}_{y}.png"
    if p.exists():
        a = _decode(p)
        if a is not None:
            return a
        p.unlink(missing_ok=True)                                     # unreadable cached file (partial write, HTTP error body): download again
    tmp = p.with_name(f"{p.name}.{os.getpid()}.{threading.get_ident()}.part")
    cmd = ["curl", "-q", "-fsS", "-m", "60", "-o", str(tmp), TILE.format(z=z, x=x, y=y)] + curl_args(proxy)
    for k in range(FETCH_TRIES):
        if k:
            time.sleep(2 ** (k - 1))                                  # 1, 2, 4 s backoff
        r = subprocess.run(cmd, check=False, capture_output=True)
        a = _decode(tmp) if r.returncode == 0 else None
        if a is not None:
            os.replace(tmp, p)
            return a
        tmp.unlink(missing_ok=True)
    return None


def _fetch_all(jobs: list[tuple[int, int]], zoom: int, cache: Path, proxy: str | None, threads: int, progress: bool = False):
    """Yield ((x, y), array or None) for every tile; download failures come back as None."""
    with ThreadPoolExecutor(threads) as ex:
        for i, item in enumerate(zip(jobs, ex.map(lambda t: _fetch(zoom, t[0], t[1], cache, proxy), jobs)), 1):
            if progress and i % 200 == 0:
                print(f"  tiles {i}/{len(jobs)}", file=sys.stderr)
            yield item


def _report_missing(failed: list[tuple[int, int]], total: int, zoom: int, allow_missing: bool) -> None:
    """Fail loudly on missing tiles; with --allow-missing only warn."""
    if not failed:
        return
    eg = ", ".join(f"{zoom}/{x}/{y}" for x, y in failed[:5]) + (" …" if len(failed) > 5 else "")
    msg = f"{len(failed)}/{total} elevation tiles failed to download after {FETCH_TRIES} tries ({eg})"
    if not allow_missing:
        sys.exit(f"{msg}. Good tiles are cached, so just re-run (lower --threads if it keeps failing, "
                 "or check the network with doctor.py --network); --allow-missing proceeds without them")
    print(f"WARNING: {msg}; --allow-missing: continuing without them", file=sys.stderr)


class DEM:
    """Elevation mosaic indexed by Web Mercator pixels."""

    def __init__(self, center: tuple[float, float], radius_m: float, zoom: int, cache: Path, proxy: str | None,
                 allow_missing: bool = False):
        cache.mkdir(parents=True, exist_ok=True)
        self.z = zoom
        mpp = geo.meters_per_px(zoom, center[0])
        cx, cy = geo.ll2px(zoom, *center)
        r_px = radius_m / mpp + 256
        self.tx0, self.ty0 = int((cx - r_px) // 256), int((cy - r_px) // 256)
        tx1, ty1 = int((cx + r_px) // 256), int((cy + r_px) // 256)
        nx, ny = tx1 - self.tx0 + 1, ty1 - self.ty0 + 1
        if nx * ny > 400:
            sys.exit(f"Area too large ({nx}x{ny} tiles); reduce --range or lower --zoom")
        self.h = np.full((ny * 256, nx * 256), np.nan, dtype=np.float32)   # missing tiles stay NaN, never 0 m
        jobs = [(x, y) for y in range(self.ty0, ty1 + 1) for x in range(self.tx0, tx1 + 1)]
        failed = []
        for (x, y), arr in _fetch_all(jobs, zoom, cache, proxy, 8):
            if arr is None:
                failed.append((x, y))
                continue
            self.h[(y - self.ty0) * 256:(y - self.ty0 + 1) * 256, (x - self.tx0) * 256:(x - self.tx0 + 1) * 256] = arr
        _report_missing(failed, len(jobs), zoom, allow_missing)

    def sample(self, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
        n = 256 * 2 ** self.z
        x = (lon + 180) / 360 * n - self.tx0 * 256
        y = (1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * n - self.ty0 * 256
        x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
        fx, fy = x - x0, y - y0
        H, W = self.h.shape
        x0, y0 = np.clip(x0, 0, W - 2), np.clip(y0, 0, H - 2)
        a, b = self.h[y0, x0], self.h[y0, x0 + 1]
        c, d = self.h[y0 + 1, x0], self.h[y0 + 1, x0 + 1]
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def _dest_np(lat0: float, lon0: float, brg: np.ndarray, dist: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    la1, lo1 = math.radians(lat0), math.radians(lon0)
    b = np.radians(brg)[:, None]
    d = (dist / R_EARTH)[None, :]
    la2 = np.arcsin(math.sin(la1) * np.cos(d) + math.cos(la1) * np.sin(d) * np.cos(b))
    lo2 = lo1 + np.arctan2(np.sin(b) * np.sin(d) * math.cos(la1), np.cos(d) - math.sin(la1) * np.sin(la2))
    return np.degrees(la2), np.degrees(lo2)


def cast(dem: DEM, at, eye_alt: float, azimuths: np.ndarray, rng: float, near: float = 40.0, n: int = 900, keep_nan: bool = False):
    """Return (elevation angle ° of each sample in each column, sample distance m). n = samples per sight line (view/profile use 900; fit uses --nsamp).
    Samples on missing tiles (--allow-missing) become -90° so they never form a skyline; keep_nan=True leaves them NaN for the caller to detect."""
    dist = near * (rng / near) ** (np.arange(n) / (n - 1))          # dense near, sparse far
    lat, lon = _dest_np(at[0], at[1], azimuths, dist)
    h = dem.sample(lat, lon)
    drop = dist ** 2 / (2 * R_EARTH) * (1 - K_REFRACTION)
    ang = np.degrees(np.arctan2(h - drop[None, :] - eye_alt, dist[None, :]))
    return (ang if keep_nan else np.nan_to_num(ang, nan=-90.0)), dist


def render(ang: np.ndarray, dist: np.ndarray, azimuths: np.ndarray, pitch: float, vfov: float, height: int) -> tuple[Image.Image, np.ndarray, np.ndarray]:
    W = ang.shape[0]
    img = np.zeros((height, W, 3), dtype=np.uint8)
    img[:] = (205, 225, 245)                                         # sky
    top = pitch + vfov / 2

    def row(a):
        return (top - a) / vfov * (height - 1)

    sky_ang = np.full(W, -90.0)
    sky_dist = np.full(W, np.nan)
    runmax = np.maximum.accumulate(ang, axis=1)
    visible = ang >= np.concatenate([np.full((W, 1), -90.0), runmax[:, :-1]], axis=1)
    logd = np.log(dist / dist[0]) / np.log(dist[-1] / dist[0])
    for c in range(W):
        idx = np.nonzero(visible[c])[0]
        # near to far: each visible sample paints this column from "its elevation angle" to "the previous highest point", color from dark to light by distance
        lo_row = height
        for i in idx:
            r = row(ang[c, i])
            if r >= lo_row:
                continue
            shade = int(60 + 150 * logd[i])
            r0 = max(0, int(r))
            img[r0:lo_row, c] = (shade - 25, shade, shade - 35)
            lo_row = r0
        if idx.size:
            j = idx[-1]
            sky_ang[c], sky_dist[c] = ang[c, j], dist[j]
            rr = int(round(row(ang[c, j])))
            if 0 <= rr < height:
                img[max(0, rr - 1):rr + 2, c] = (220, 30, 30)
    return Image.fromarray(img), sky_ang, sky_dist


def _font(size: int):
    """Label font from geolib.cli.font, CJK-capable (peak and place names), Windows fonts included."""
    from geolib.cli import font
    return font(size, prefer_wide=True)


def annotate(im: Image.Image, azimuths: np.ndarray, pitch: float, vfov: float, title: str) -> Image.Image:
    W, H = im.size
    d = ImageDraw.Draw(im)
    f = _font(16)
    hr = (pitch + vfov / 2) / vfov * (H - 1)
    d.line([(0, hr), (W, hr)], fill=(90, 90, 200), width=1)           # horizontal line at eye height
    names = {0: "N", 45: "NE", 90: "E", 135: "SE", 180: "S", 225: "SW", 270: "W", 315: "NW"}
    span = azimuths[-1] - azimuths[0]
    stepdeg = 5 if span <= 60 else 10 if span <= 150 else 30
    first = math.ceil(azimuths[0] / stepdeg) * stepdeg
    for a in np.arange(first, azimuths[-1] + 1e-6, stepdeg):
        x = (a - azimuths[0]) / span * (W - 1)
        d.line([(x, H - 14), (x, H)], fill="black", width=1)
        lab = f"{a % 360:.0f}°" + (names.get(int(a % 360), ""))
        d.text((x + 3, H - 32), lab, fill="black", font=f)
    d.rectangle([0, 0, W, 24], fill=(0, 0, 0))
    d.text((6, 3), title, fill="yellow", font=f)
    return im



# ---------------------------------------------------------------- scan ----
# Linear infrastructure × terrain filtering. Method in references/corridors.md 4.3.
# Difference from view/profile: this has to cover a province-sized region, far more tiles than the DEM class's 400-tile limit,
# so it builds its own large mosaic filled only with "the tiles actually needed", sampled nearest-neighbor (one z10 cell is ~150 m; interpolation is pointless).


def _parse_skip_tags(specs: list[str] | None) -> list[tuple[str, str]]:
    """--skip-tag key=value list (default electrified=no); 'none' or '-' skips nothing."""
    out = []
    for s in (specs or ["electrified=no"]):
        if s.lower() in ("none", "-"):
            continue
        if "=" not in s:
            sys.exit(f"--skip-tag must be written as key=value, got {s!r}")
        k, v = s.split("=", 1)
        out.append((k, v))
    return out


class _Mosaic:
    """A large mosaic stitched from a batch of Terrarium tiles, nearest-neighbor sampling. Tiles that failed to download hold MISSING."""

    MISSING = -32768                                                  # real elevations are clipped to -500…9000, so this never collides

    def __init__(self, need: set[tuple[int, int]], zoom: int, cache: Path, proxy: str | None, threads: int,
                 allow_missing: bool = False):
        cache.mkdir(parents=True, exist_ok=True)
        self.z = zoom
        self.tx0 = min(t[0] for t in need)
        self.ty0 = min(t[1] for t in need)
        nx = max(t[0] for t in need) - self.tx0 + 1
        ny = max(t[1] for t in need) - self.ty0 + 1
        gb = nx * ny * 256 * 256 * 2 / 1e9
        print(f"mosaic {nx}x{ny} tiles, {gb:.2f} GB memory", file=sys.stderr)
        self.h = np.full((ny * 256, nx * 256), self.MISSING, dtype=np.int16)
        jobs = sorted(need)
        failed = []
        for (x, y), arr in _fetch_all(jobs, zoom, cache, proxy, threads, progress=True):
            if arr is None:
                failed.append((x, y))
                continue
            self.h[(y - self.ty0) * 256:(y - self.ty0 + 1) * 256,
                   (x - self.tx0) * 256:(x - self.tx0 + 1) * 256] = np.clip(arr, -500, 9000).astype(np.int16)
        self.n_failed = len(failed)
        _report_missing(failed, len(jobs), zoom, allow_missing)

    def sample(self, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
        n = 256 * 2 ** self.z
        x = ((lon + 180) / 360 * n - self.tx0 * 256).astype(int)
        y = ((1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * n - self.ty0 * 256).astype(int)
        x = np.clip(x, 0, self.h.shape[1] - 1)
        y = np.clip(y, 0, self.h.shape[0] - 1)
        return self.h[y, x].astype(np.float32)


def _line_points(gj: dict, step: float, skip: list[tuple[str, str]], bbox: tuple[float, float, float, float] | None):
    """Take one point every step meters along each LineString; return [(lat, lon, properties)]."""
    pts = []
    n_line = n_skip = 0
    feats = []                                         # polygons (lakes, coasts) and multi-lines become plain lines: shores are paths too
    for f in gj.get("features", []):
        g = f.get("geometry") or {}
        gt, cc = g.get("type"), g.get("coordinates", [])
        parts = [cc] if gt == "LineString" else cc if gt in ("MultiLineString", "Polygon") else \
            [ring for poly in cc for ring in poly] if gt == "MultiPolygon" else []
        for part in parts:
            feats.append({"geometry": {"type": "LineString", "coordinates": part}, "properties": f.get("properties", {}) or {}})
    for f in feats:
        g = f.get("geometry") or {}
        if g.get("type") != "LineString" or len(g.get("coordinates", [])) < 2:
            continue
        tags = f.get("properties", {}) or {}
        n_line += 1
        if any(str(tags.get(k, "")) == v for k, v in skip):
            n_skip += 1
            continue
        c = [(y, x) for x, y in g["coordinates"]]                     # geojson is lon,lat
        if bbox and not (min(p[0] for p in c) <= bbox[2] and max(p[0] for p in c) >= bbox[0]
                         and min(p[1] for p in c) <= bbox[3] and max(p[1] for p in c) >= bbox[1]):
            continue
        got = 0
        acc = 0.0
        for i in range(1, len(c)):
            d = geo.distance(c[i - 1], c[i])
            for k in range(int((acc + d) // step)):
                t = (step * (k + 1) - acc) / d if d else 0
                pts.append((c[i - 1][0] + (c[i][0] - c[i - 1][0]) * t,
                            c[i - 1][1] + (c[i][1] - c[i - 1][1]) * t, tags))
                got += 1
            acc = (acc + d) % step
        # lines shorter than step overall, or whose ends nearly coincide (loops), get one midpoint added so the whole line isn't missed
        if got == 0 or geo.distance(c[0], c[-1]) < step:
            pts.append((c[len(c) // 2][0], c[len(c) // 2][1], tags))
    if bbox:
        s, w, n, e = bbox
        pts = [p for p in pts if s <= p[0] <= n and w <= p[1] <= e]
    print(f"{n_line} lines ({n_skip} skipped by --skip-tag), {len(pts)} sample points", file=sys.stderr)
    return pts


def _cluster(hits: list[dict], km: float) -> list[dict]:
    """Greedy clustering by max_ang from largest to smallest: the steepest point represents the cluster, points within km join it, and the representative gets n = number of points in the cluster."""
    order = sorted(hits, key=lambda h: -h["max_ang"])
    used = [False] * len(order)
    out = []
    for i, p in enumerate(order):
        if used[i]:
            continue
        n = 0
        for j in range(i, len(order)):
            if not used[j] and geo.distance((p["lat"], p["lon"]), (order[j]["lat"], order[j]["lon"])) <= km * 1000:
                used[j] = True
                n += 1
        out.append({**p, "n": n})
    return out


def _cmd_scan(args) -> None:
    az_step = args.az_step
    naz = int(round(360 / az_step))
    if abs(naz * az_step - 360) > 1e-6:
        sys.exit("--az-step must divide 360 evenly")
    if args.step <= 0 or args.near_step <= 0 or args.near_radius < 0:
        sys.exit("--step / --near-step must be greater than 0, --near-radius must not be negative")
    dist = np.array([float(x) for x in args.dist.split(",")], dtype=float)
    near = np.arange(0, args.near_radius + 1e-6, args.near_step, dtype=float)
    skip = _parse_skip_tags(args.skip_tag)
    bbox = None
    if args.bbox:
        b = [float(x) for x in args.bbox.split(",")]
        if len(b) != 4:
            sys.exit("--bbox needs 4 numbers: s,w,n,e")
        bbox = (min(b[0], b[2]), min(b[1], b[3]), max(b[0], b[2]), max(b[1], b[3]))

    gj = json.loads(Path(args.lines).read_text(encoding="utf-8"))
    pts = _line_points(gj, args.step, skip, bbox)
    if not pts:
        sys.exit("0 sample points: --bbox encloses nothing, or the geojson has no LineString")

    reach = float(dist.max()) + 500                                   # half a kilometer extra, enough even when a sample point falls on a tile edge
    need: set[tuple[int, int]] = set()
    for lat, lon, _ in pts:
        x, y = geo.ll2px(args.zoom, lat, lon)
        r = reach / geo.meters_per_px(args.zoom, lat)                 # reach in pixels at this latitude
        for tx in range(int((x - r) / 256), int((x + r) / 256) + 1):
            for ty in range(int((y - r) / 256), int((y + r) / 256) + 1):
                need.add((tx, ty))
    print(f"need {len(need)} z{args.zoom} tiles", file=sys.stderr)
    if len(need) > args.max_tiles:
        sys.exit(f"{len(need)} tiles > --max-tiles {args.max_tiles}: shrink --bbox, lower --zoom, or run in chunks")
    mos = _Mosaic(need, args.zoom, args.cache, args.proxy, args.threads, args.allow_missing)

    az = np.arange(0, 360, az_step)
    min_low = int(round((args.min_low_deg if args.min_low_deg is not None else args.flat_run) / az_step))
    need_run = int(round(args.flat_run / az_step))
    cap = int(round(args.flat_run_cap / az_step))
    hits = []
    n_missing = 0
    for idx, (lat, lon, tags) in enumerate(pts):
        if idx and idx % 2000 == 0:
            print(f"  scanned {idx}/{len(pts)}, hits {len(hits)}", file=sys.stderr)
        ln, lo = _dest_np(lat, lon, az, near)
        hn = mos.sample(ln, lo)
        if (hn == mos.MISSING).any():
            n_missing += 1
            continue
        if hn.max() - hn.min() > args.near_flat:                      # not flat nearby: a valley or hillside, not the flat ground seen in the frame
            continue
        h0 = float(np.median(hn))
        la, lo = _dest_np(lat, lon, az, dist)
        h = mos.sample(la, lo)
        if (h == mos.MISSING).any():                                  # a hole would read as a deep valley or flat horizon
            n_missing += 1
            continue
        ang = np.degrees(np.arctan2(h - h0 - args.eye, dist[None, :]))  # within a few km earth curvature is <5 m, negligible next to z10 error
        hor = ang.max(axis=1)                                         # horizon elevation angle at each bearing
        rel = (h - h0).max(axis=1)
        mt = hor >= args.min_peak
        low = hor < args.max_low
        if not mt.any() or low.sum() < min_low:
            continue
        best = 0                                                      # how long the flat horizon right next to the mountain is
        for i in range(naz):
            if not mt[i]:
                continue
            for sgn in (-1, 1):
                k = run = 0
                while k < cap:
                    jj = (i + sgn * (k + 1)) % naz
                    if low[jj]:
                        run += 1
                    elif run == 0 and k < 2:                          # allow a 2-cell transition between the mountain foot and flat ground
                        pass
                    else:
                        break
                    k += 1
                best = max(best, run)
        if best < need_run:
            continue
        i = int(np.argmax(hor))
        hits.append({"lat": round(lat, 5), "lon": round(lon, 5), "h0": round(h0), "max_ang": round(float(hor[i]), 1),
                     "az": float(az[i]), "relief": round(float(rel[i])), "flat_run_deg": best * az_step,
                     "name": tags.get("name", ""), "hs": tags.get("highspeed", ""),
                     "elec": tags.get("electrified", ""), "id": tags.get("id", tags.get("@id", ""))})

    clusters = _cluster(hits, args.cluster_km)
    print(f"{len(hits)} hit points → {len(clusters)} clusters", file=sys.stderr)
    if len(clusters) > 80:
        print(f"Note: {len(clusters)} clusters cost roughly {len(clusters) * 5 / 60:.0f}–{len(clusters) * 12 / 60:.0f} min in fit at its defaults (2 km / 250 m / z11). "
              f"fit stops at --budget-min (default 20) with a partial ranking; run it in the background, read the ranking at the stop, "
              f"continue with --select, or cut the count first (--cluster-km 6, --min-peak closer to the photo estimate).", file=sys.stderr)
    if n_missing:
        print(f"WARNING: {n_missing}/{len(pts)} sample points not scanned because they touch missing tiles", file=sys.stderr)
    out = {
        "params": {"lines": str(args.lines), "bbox": list(bbox) if bbox else None, "step_m": args.step,
                   "zoom": args.zoom, "near_flat_m": args.near_flat, "near_radius_m": args.near_radius,
                   "min_peak_deg": args.min_peak, "max_low_deg": args.max_low, "flat_run_deg": args.flat_run,
                   "min_low_deg": args.min_low_deg if args.min_low_deg is not None else args.flat_run,
                   "eye_m": args.eye, "az_step_deg": az_step, "dist_m": dist.tolist(),
                   "skip_tag": [f"{k}={v}" for k, v in skip], "cluster_km": args.cluster_km},
        "n_samples": len(pts), "n_hits": len(hits), "n_clusters": len(clusters),
        "n_failed_tiles": mos.n_failed, "n_samples_missing_dem": n_missing,
        "hits": hits, "clusters": clusters,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"→ {args.out}", file=sys.stderr)
    if args.clusters_out:
        Path(args.clusters_out).write_text(json.dumps(clusters, ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"→ {args.clusters_out} (cluster list only)", file=sys.stderr)


# ---------------------------------------------------------------- ridge ----
# Photo ridgeline sampling. Method in references/geometry.md 7.4: per column, top to bottom, find the sky→mountain brightness jump.


def _focal_px(photo: Path, w: int, h: int, f0_arg: float | None, f35_default: float):
    """Photo focal length (pixels). Priority: --f0 > EXIF 35mm-equivalent focal length > assumed from --f35.
    The 35mm equivalent converts via the diagonal: f_px = f35 / 43.27 × diagonal pixels; this holds even if the photo was resized.
    Return (f_px, source, f35)."""
    diag = math.hypot(w, h)
    if f0_arg:
        return float(f0_arg), "arg", round(f0_arg * 43.2666 / diag, 1)
    try:
        with Image.open(photo) as im:                                  # getexif() does not load pixels, so nothing else closes the file
            f35 = im.getexif().get_ifd(0x8769).get(0xA405)            # FocalLengthIn35mmFilm
        if f35 and float(f35) > 0:
            return float(f35) / 43.2666 * diag, "exif", float(f35)
    except Exception:  # noqa: BLE001
        pass
    return f35_default / 43.2666 * diag, "assumed", f35_default


def _parse_pts(spec: str, name: str, W: int, H: int) -> list[list[int]]:
    """Pixel points as "x,y;x,y;..." or a JSON file holding [[x,y],...]."""
    p = Path(spec)
    if p.suffix == ".json" and p.exists():
        raw = json.loads(p.read_text(encoding="utf-8"))
        pts = raw.get("ridge", raw) if isinstance(raw, dict) else raw
    else:
        try:
            pts = [[float(v) for v in part.split(",")] for part in spec.split(";") if part.strip()]
        except ValueError:
            sys.exit(f"{name} must be x,y;x,y;... or a .json file of [[x,y],...], got {spec!r}")
    out = []
    for q in pts:
        if len(q) != 2 or not (0 <= q[0] < W and 0 <= q[1] < H):
            sys.exit(f"{name}: point {q} is not x,y inside the {W}x{H} photo")
        out.append([int(round(q[0])), int(round(q[1]))])
    if len(out) < 3:
        sys.exit(f"{name} needs at least 3 points, got {len(out)}")
    return sorted(out)


def _sky_edge(prof: np.ndarray, ymin: int, ymax: int, k: int, drop: float, hold: int) -> int | None:
    """In one column's brightness profile, top to bottom, find the first row where "the mean of the k rows above exceeds the mean of the k rows below by drop, and the hold rows further down are still dark",
    then take the maximum-gradient row within ±k rows of it. Return the row index of the mountain's first row; None if not found.
    hold is there to skip things only a few pixels tall vertically, such as wires and antennas."""
    n = len(prof)
    cs = np.concatenate([[0.0], np.cumsum(prof, dtype=np.float64)])
    y = np.arange(max(ymin, k), min(ymax, n - k - hold))
    if y.size == 0:
        return None
    above = (cs[y] - cs[y - k]) / k
    below = (cs[y + k] - cs[y]) / k
    held = (cs[y + k + hold] - cs[y + k]) / hold
    ok = (above - below >= drop) & (above - held >= drop)
    if not ok.any():
        return None
    y0 = int(y[np.argmax(ok)])
    yy = np.arange(max(k, y0 - k), min(n - k, y0 + k + 1))
    g = (cs[yy] - cs[yy - k]) / k - (cs[yy + k] - cs[yy]) / k
    return int(yy[np.argmax(g)])


def _cmd_ridge(args) -> None:
    im = Image.open(args.photo).convert("RGB")
    W, H = im.size
    a = np.asarray(im, dtype=np.float32)
    L = a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114
    if args.x1 is None:
        args.x1 = W - 1
    if not (0 <= args.x0 < args.x1 < W):
        sys.exit(f"--x0/--x1 must satisfy 0 ≤ x0 < x1 < width {W}")
    if args.step <= 0:
        sys.exit("--step must be greater than 0")
    ymin = args.ymin if args.ymin is not None else 0
    ymax = args.ymax if args.ymax is not None else H
    f0, f_src, f35 = _focal_px(args.photo, W, H, args.f0, args.f35)

    def edge(x: int) -> int | None:
        x0, x1 = max(0, x - args.halfw), min(W, x + args.halfw + 1)
        return _sky_edge(L[:, x0:x1].mean(axis=1), ymin, ymax, args.k, args.drop, args.hold)

    ridge, missing = [], []
    if args.points:                                                   # hand-picked skyline replaces detection (cloud on the peaks, haze, snow against sky)
        ridge = _parse_pts(args.points, "--points", W, H)
    else:
        for x in range(args.x0, args.x1 + 1, args.step):
            y = edge(x)
            (ridge.append([x, y]) if y is not None else missing.append(x))
    near = _parse_pts(args.near, "--near", W, H) if args.near else []
    near_clear = []
    for spec in args.near_clear or []:
        m = re.match(r"^\s*(\d+):(\d+)@(\d+(?:\.\d+)?)\s*$", spec)
        if not m or not 0 <= int(m[1]) < int(m[2]) < W:
            sys.exit(f"--near-clear must be x0:x1@row with 0 ≤ x0 < x1 < width {W}, got {spec!r}")
        near_clear.append([int(m[1]), int(m[2]), float(m[3])])
    flat = None
    flat_rows: list[int] = []
    flat_pts: list[list[int]] = []                                    # for drawing the check image: flat_rows has only row indices and omits columns with no jump found, so index order can't map back to columns
    if args.flat:
        b = args.flat.split(":")
        if len(b) != 2:
            sys.exit("--flat must be written as x0:x1")
        flat = [int(b[0]), int(b[1])]
        if not (0 <= flat[0] < flat[1] < W):
            sys.exit(f"--flat must satisfy 0 ≤ x0 < x1 < width {W}")
        for x in range(flat[0], flat[1] + 1, args.step):
            y = edge(x)
            if y is not None:
                flat_rows.append(y)
                flat_pts.append([x, y])
    if args.hrow is not None:
        hrow, h_src = float(args.hrow), "arg"
    elif flat_rows:
        hrow, h_src = float(np.median(flat_rows)), "flat"
    else:
        hrow, h_src = H / 2, "center"
    if len(ridge) < 3:
        print(f"warning: only {len(ridge)} ridge points found ({len(missing)} columns missing), fit needs at least 3; adjust --drop/--ymin/--ymax or check --png", file=sys.stderr)
    out = {
        "photo": str(args.photo), "image_size": [W, H], "cx": W / 2,
        "ridge": ridge, "missing_cols": missing, "ridge_source": "points" if args.points else "detected",
        "near": near, "near_clear": near_clear,
        "flat": flat, "flat_rows": flat_rows,
        "hrow": round(hrow, 1), "hrow_source": h_src,
        "f0": round(f0, 1), "f0_source": f_src, "f35_equiv": f35,
        "params": {"x0": args.x0, "x1": args.x1, "step": args.step, "ymin": ymin, "ymax": ymax,
                   "drop": args.drop, "k": args.k, "hold": args.hold, "halfw": args.halfw},
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    src_txt = {"arg": "--f0", "exif": "EXIF 35mm equivalent",
               "assumed": f"no EXIF, assumed {f35} mm equivalent; fit tries {F35_RANGE[0]:g}–{F35_RANGE[1]:g} mm by default"}[f_src]
    h_txt = {"arg": "--hrow", "flat": f"median sky→ground row in the --flat columns ({len(flat_rows)} columns)", "center": "no --flat given, frame midline"}[h_src]
    print(f"{W}x{H}  ridge {len(ridge)} points ({len(missing)} columns missing)  flat-horizon columns {flat}  "
          f"hrow {hrow:.0f} ({h_txt})  f0 {f0:.0f} px ({src_txt}, horizontal FOV {2 * math.degrees(math.atan(W / 2 / f0)):.1f}°)"
          + (f"  near layer {len(near)} points, {len(near_clear)} clear ranges" if near or near_clear else "") + f" → {args.out}")
    if args.png:
        d = ImageDraw.Draw(im)
        d.line([(0, hrow), (W, hrow)], fill=(80, 80, 255), width=1)
        if flat:
            d.line([(flat[0], hrow), (flat[1], hrow)], fill=(0, 200, 255), width=4)
            for x, y in flat_pts:
                d.ellipse([x - 3, y - 3, x + 3, y + 3], outline=(0, 200, 255), width=2)
        for x, y in ridge:
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 220, 0))
        for x in missing:
            d.line([(x, ymin), (x, ymax - 1)], fill=(255, 0, 0), width=1)
        for x, y in near:
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 120, 0))
        for x0, x1, row in near_clear:
            d.line([(x0, row), (x1, row)], fill=(255, 120, 0), width=3)
        d.text((8, 8), f"ridge {len(ridge)} pts  hrow {hrow:.0f} ({h_src})  f0 {f0:.0f}px ({f_src})", fill="yellow", font=_font(20))
        im.save(args.png, quality=90)
        print(f"check image → {args.png} (yellow dots = ridge points, red vertical lines = columns not found, blue line = hrow, cyan line = flat-horizon column range, "
              "orange dots = near-layer points, orange lines = near-clear ranges)")


# ------------------------------------------------------------------ fit ----
# Batch skyline scoring. Method in references/geometry.md 7.4; infrastructure distance constraint in corridors.md 4.3.
# For each candidate camera position compute a full 360° horizon hor(az); convert photo ridge points to (bearing offset, elevation angle) and compare against all headings at once:
#   rms = RMS of the ridge elevation-angle residuals (the residual median serves as horizon offset cc, clamped to ±cc_max)
#   flatpen = mean of max(0, hor - cc - flat_clear) over the flat-horizon columns
#   score = rms + flat_w × flatpen
# With --line, also add: for each heading, the nearest distance dL/dC/dR of infrastructure sample points inside the frame's left/center/right bearing windows,
#   line_pen = meters each falls outside its --line-dist interval / --line-scale (+ penalty 1 for wrong order)
#   total = score + line_w × line_pen; without --line, total = score.
# Two-layer photos (ridge.json has near / near_clear): near(az) = highest angle within D1 m, D1 tried from --near-dist; near points join
#   the far ridge points in the same rms (one cc and roll for both), near_clear columns add nclearpen = mean of max(0, near − row angle).
# --perp-line keeps only headings within --perp-tol of perpendicular to the nearest line (wires crossing the frame almost level).


def _parse_pairs(s: str, name: str, n: int = 3, sep: str = ",", rng: str = ":") -> list[tuple[float, float]]:
    out = []
    for part in s.split(sep):
        b = part.split(rng)
        if len(b) != 2:
            sys.exit(f"{name}: each segment must be written as a{rng}b, got {part!r}")
        out.append((float(b[0]), float(b[1])))
    if len(out) != n:
        sys.exit(f"{name} needs {n} segments, got {len(out)}")
    return out


def _load_centers(args) -> tuple[list[dict], dict]:
    """Candidate centres, and the params block of the scan output given as --hits ({} for --at or a bare cluster list)."""
    if args.at:
        lat, lon = map(float, args.at.split(","))
        return [{"lat": lat, "lon": lon, "name": "", "src_idx": 0}], {}
    j = json.loads(Path(args.hits).read_text(encoding="utf-8"))
    items = j["clusters"] if isinstance(j, dict) and "clusters" in j else j
    if not isinstance(items, list):
        sys.exit("--hits must be scan output (with a clusters field) or a list of clusters/points")
    centers = []
    for i, c in enumerate(items):
        if "lat" not in c or "lon" not in c:
            sys.exit(f"--hits item {i} has no lat/lon")
        centers.append({**c, "src_idx": c.get("src_idx", i)})
    if args.select:
        want = [int(x) for x in args.select.split(",")]
        bad = [i for i in want if not 0 <= i < len(centers)]
        if bad:
            sys.exit(f"--select indices {bad} out of range 0–{len(centers) - 1}")
        centers = [centers[i] for i in want]
    scan_params = (j.get("params") or {}) if isinstance(j, dict) else {}
    return centers, scan_params


def _skyline_xy(hor: np.ndarray, az: np.ndarray, H: float, f: float, cc: float, cx: float, hrow: float, half_w: float,
                roll: float = 0.0):
    """Project the 360° horizon onto photo pixels with the pinhole model fit uses: x = cx + f·tan(bearing offset), y = hrow − f·tan(elevation angle − cc).
    roll = frame roll angle ° (clockwise positive); pass the value fit solved for, otherwise both ends will be off from the photo by a dozen-plus pixels."""
    rel = (az - H + 180) % 360 - 180
    lim = math.degrees(math.atan(half_w / f)) + 1
    m = np.abs(rel) <= lim
    x = cx + f * np.tan(np.radians(rel[m]))
    # pinhole: a ray at horizontal offset rel and elevation e lands at y = hrow − f·tan(e)/cos(rel) (the vertical scale shrinks off-axis)
    y = hrow - f * np.tan(np.radians(hor[m] - cc)) / np.cos(np.radians(rel[m])) + math.tan(math.radians(roll)) * (x - cx)
    o = np.argsort(x)
    return list(zip(x[o].tolist(), y[o].tolist()))



# ---------------------------------------------------------------- named peaks on the skyline (PeakFinder-style labels)
def load_peaks(path) -> list[dict]:
    """Named peaks from osm.py geom '["natural"="peak"]["name"]' output (Point features; the ele tag when present)."""
    gj = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for ft in gj.get("features", []):
        g = ft.get("geometry") or {}
        if g.get("type") != "Point":
            continue
        tags = ft.get("properties") or {}
        name = tags.get("name") or tags.get("name:en")
        if not name:
            continue
        ele = None
        m = re.match(r"\s*(-?[0-9]+(?:\.[0-9]+)?)", str(tags.get("ele", "")).replace(",", "."))
        if m:
            ele = float(m.group(1))
        out.append({"name": name, "lat": float(g["coordinates"][1]), "lon": float(g["coordinates"][0]), "ele": ele})
    return out


def peaks_in_view(peaks: list[dict], dem, cam, eye_alt: float, az: np.ndarray, hor: np.ndarray, rng: float, tol: float = 0.4) -> list[dict]:
    """The named peaks that stand on the skyline seen from cam: name, bearing, elevation angle, distance, height.
    hor = skyline elevation angle per az column (degrees); a peak lower than the skyline at its bearing by more than tol is hidden."""
    order = np.argsort(az)
    azs, hors = np.asarray(az, float)[order], np.asarray(hor, float)[order]
    out = []
    for p in peaks:
        d = geo.distance(cam, (p["lat"], p["lon"]))
        if d < 50 or d > rng:
            continue
        ele = p.get("ele")
        if ele is None:
            ele = float(dem.sample(np.array([p["lat"]]), np.array([p["lon"]]))[0])
            if math.isnan(ele):
                continue
        brg = geo.bearing(cam, (p["lat"], p["lon"])) % 360
        drop = d * d / (2 * R_EARTH) * (1 - K_REFRACTION)
        ang = math.degrees(math.atan2(ele - drop - eye_alt, d))
        if ang < float(np.interp(brg, azs, hors, period=360)) - tol:
            continue
        out.append({"name": p["name"], "bearing": round(brg, 1), "angle": round(ang, 2), "dist_m": int(round(d)), "ele": int(round(ele))})
    return out


def draw_peak_labels(d: ImageDraw.ImageDraw, labels: list[tuple[str, float, float]], size: int = 14) -> None:
    """labels: (text, x, y) in image pixels, y on the skyline; staggered on two levels so neighbours do not overlap."""
    font = _font(size)
    for i, (text, x, y) in enumerate(sorted(labels, key=lambda t: t[1])):
        lift = 30 + 26 * (i % 2)
        d.line([(x, y), (x, y - lift + 4)], fill=(255, 255, 255), width=1)
        d.text((x + 3, y - lift - size + 2), text, fill="white", font=font, stroke_width=2, stroke_fill="black")



def peakfinder_url(lat: float, lon: float, heading: float, hfov: float, ground: float) -> str:
    """The same camera in PeakFinder (labelled panorama, for the user's eyes). Parameters as documented by the community
    (lat, lng, azi, fov 8–90, ele); the site may ignore ones it does not know."""
    return (f"https://www.peakfinder.com/?lat={lat:.5f}&lng={lon:.5f}&azi={heading % 360:.0f}"
            f"&fov={min(max(hfov, 8), 90):.0f}&ele={ground:.0f}")


def tie_extent(cams: list[dict], best_total: float, delta: float) -> dict | None:
    """Camera positions whose total is within delta of the best: how many, how far they spread (principal axis, metres)
    and along which compass bearing. A skyline fixes a sight line; this is the stretch of it the score cannot separate."""
    ties = [c for c in cams if c.get("total") is not None and c["total"] <= best_total + delta]
    if len(ties) < 2:
        return {"n": len(ties), "span_m": 0.0, "bearing": None, "delta": delta} if ties else None
    lat0 = sum(c["cam"][0] for c in ties) / len(ties)
    lon0 = sum(c["cam"][1] for c in ties) / len(ties)
    kx = 111320 * math.cos(math.radians(lat0))
    xy = np.array([[(c["cam"][1] - lon0) * kx, (c["cam"][0] - lat0) * 110540] for c in ties])
    cov = np.cov(xy.T) if len(ties) > 2 else np.outer(xy[1] - xy[0], xy[1] - xy[0])
    w, v = np.linalg.eigh(cov)
    axis = v[:, int(np.argmax(w))]
    proj = xy @ axis
    span = float(proj.max() - proj.min())
    bearing = (math.degrees(math.atan2(axis[0], axis[1])) + 360) % 180          # an axis: 0–180°
    return {"n": len(ties), "span_m": round(span, 1), "bearing": round(bearing, 1), "delta": delta,
            "bbox": [round(min(c["cam"][0] for c in ties), 5), round(min(c["cam"][1] for c in ties), 5),
                     round(max(c["cam"][0] for c in ties), 5), round(max(c["cam"][1] for c in ties), 5)]}


def _fit_sheet(recs: list[dict], ridge: dict, photo: Path | None, out: Path, args, az: np.ndarray, dist_n: int,
               style: str = "grid", peaks: list[dict] | None = None) -> None:
    """grid: --sheet-cols × --sheet-width thumbnails with a three-line header. stack: one full-width tile per record (≤1000 px),
    one header line each, summit names when peaks are given — the image the live page shows as the Skyline card."""
    W, H = ridge["image_size"]
    tw = args.sheet_width if style == "grid" else min(1000, W)
    s = tw / W
    th = int(H * s)
    base = None
    if photo and photo.exists():
        base = Image.open(photo).convert("RGB").resize((tw, th))
    cols = max(1, min(args.sheet_cols, len(recs))) if style == "grid" else 1      # no empty tiles: one record, one tile
    rows = math.ceil(len(recs) / cols)
    sheet = Image.new("RGB", (tw * cols, th * rows), "white")
    font = _font(13 if style == "grid" else 18)
    for i, r in enumerate(recs):
        tile = base.copy() if base else Image.new("RGB", (tw, th), (120, 120, 120))
        d = ImageDraw.Draw(tile)
        hrow, f, cx = ridge["hrow"], r["f"], ridge.get("cx", W / 2)
        d.line([(0, hrow * s), (tw, hrow * s)], fill=(80, 80, 255), width=1)
        if ridge.get("flat"):
            d.line([(ridge["flat"][0] * s, hrow * s), (ridge["flat"][1] * s, hrow * s)], fill=(0, 200, 255), width=3)
        try:
            dem = DEM(tuple(r["cam"]), args.range + 500, args.zoom, args.cache, args.proxy, args.allow_missing)
            ang, dist_v = cast(dem, tuple(r["cam"]), r["g"] + args.eye, az, args.range, near=args.near, n=dist_n)
            pts = _skyline_xy(ang.max(axis=1), az, r["H"], f, r["cc"], cx, hrow, W / 2, r.get("roll", 0.0))
            d.line([(x * s, y * s) for x, y in pts], fill=(255, 40, 40), width=2 if style == "grid" else 3)
            if peaks:
                labels = []
                r["peaks"] = []
                lim = math.degrees(math.atan((W / 2) / f))          # half the horizontal field of view: behind the camera tan() wraps
                for pk in peaks_in_view(peaks, dem, tuple(r["cam"]), r["g"] + args.eye, az, ang.max(axis=1), args.range):
                    rel = (pk["bearing"] - r["H"] + 180) % 360 - 180
                    if abs(rel) > lim:
                        continue
                    x = cx + f * math.tan(math.radians(rel))
                    y = hrow - f * math.tan(math.radians(pk["angle"] - r["cc"])) / math.cos(math.radians(rel)) + math.tan(math.radians(r.get("roll", 0.0))) * (x - cx)
                    labels.append((f"{pk['name']} {pk['dist_m'] / 1000:.1f} km", x * s, y * s))
                    r["peaks"].append({**pk, "x": int(round(x)), "y": int(round(y))})
                if style != "grid":
                    draw_peak_labels(d, labels, size=15)
            if r.get("D1"):
                pts = _skyline_xy(ang[:, dist_v <= r["D1"]].max(axis=1), az, r["H"], f, r["cc"], cx, hrow, W / 2, r.get("roll", 0.0))
                d.line([(x * s, y * s) for x, y in pts], fill=(255, 140, 0), width=2)
        except SystemExit as e:
            d.text((6, th - 20), f"DEM failed: {e}", fill="red", font=font)
        for x, y in ridge["ridge"]:
            d.ellipse([x * s - 2, y * s - 2, x * s + 2, y * s + 2], fill=(255, 220, 0))
        for x, y in ridge.get("near") or []:
            d.ellipse([x * s - 2, y * s - 2, x * s + 2, y * s + 2], fill=(0, 220, 255))
        for x0, x1, row in ridge.get("near_clear") or []:
            d.line([(x0 * s, row * s), (x1 * s, row * s)], fill=(0, 220, 255), width=2)
        line_txt = f"  L/C/R {r['dL']:.0f}/{r['dC']:.0f}/{r['dR']:.0f} pen {r['line_pen']:.2f}" if "line_pen" in r else ""
        if style == "grid":
            txt = (f"#{i + 1} hit{r['hit']} {r['name'] or '-'}  {r['cam'][0]:.5f},{r['cam'][1]:.5f}\n"
                   f"H {r['H']:.1f}  f {f:.0f} ({r.get('f35', 0):.0f}mm)  cc {r['cc']:+.2f}  rms {r['rms']:.3f}  flat {r['flatpen']:.3f}{line_txt}\n"
                   f"total {r['total']:.3f}")
            d.rectangle([0, 0, tw, 46], fill=(0, 0, 0))
            d.text((4, 2), txt, fill="yellow", font=font)
        else:
            txt = (f"#{i + 1}  {r['name'] or '-'}   score {r['total']:.3f} · heading {r['H']:.0f}° · {r.get('f35', 0):.0f} mm"
                   f"{' · rms ' + str(int(round(r['rms_px']))) + ' px' if r.get('rms_px') is not None else ''} · {r['cam'][0]:.5f},{r['cam'][1]:.5f}")
            d.rectangle([0, 0, tw, 30], fill=(0, 0, 0))
            d.text((6, 4), txt, fill="yellow", font=font)
        sheet.paste(tile, ((i % cols) * tw, (i // cols) * th))
    sheet.save(out, quality=88)
    print(f"overlay → {out} (red line = synthetic skyline, orange line = synthetic near layer, yellow dots = photo ridge points, "
          "cyan dots/lines = photo near points / near-clear rows, blue line = hrow, cyan line on hrow = flat-horizon columns)", file=sys.stderr)


def _fit_photo(args, ridge: dict) -> Path | None:
    """The photo fit draws on: --photo, else ridge.json's path, recorded as typed and possibly relative, so tried from the
    current directory, then from ridge.json's directory. None when no candidate exists."""
    if args.photo:
        cands = [Path(args.photo)]
    elif ridge.get("photo"):
        cands = [Path(ridge["photo"]), Path(args.ridge).parent / ridge["photo"]]
    else:
        cands = []
    return next((p for p in cands if p.exists()), None)


def _part_of(path: Path) -> Path:
    """This process's temporary file for path: two runs never share one."""
    return path.with_name(f"{path.name}.{os.getpid()}.part")


def _save_json(path: Path, payload: dict, keep_part: bool = False) -> None:
    """Write _part_of(path), then os.replace it over path: a reader never sees half a file. On Windows os.replace fails while
    another process holds path open, usually for milliseconds: retried REPLACE_TRIES times, REPLACE_WAIT_S apart. When it still
    fails the .part is removed, or kept when it is complete and keep_part is set (the caller then names it)."""
    part, written = _part_of(path), False
    try:
        part.write_text(json.dumps(payload, ensure_ascii=False, indent=0), encoding="utf-8")
        written = True
        for attempt in range(REPLACE_TRIES):
            try:
                os.replace(part, path)
                return
            except PermissionError:
                if attempt == REPLACE_TRIES - 1:
                    raise
                time.sleep(REPLACE_WAIT_S)
    except OSError:
        if not (keep_part and written):
            with contextlib.suppress(OSError):
                part.unlink()
        raise


def _ps_quote(path: Path) -> str:
    """A PowerShell single-quoted literal (an embedded quote is doubled), for a printed command."""
    return "'" + str(path).replace("'", "''") + "'"


def _select_list(left: list[int], out: str) -> str:
    """How to continue the clusters left. A long list is named, never truncated: a pasted "…" would break --select.
    A new --out keeps the clusters already ranked in out from being overwritten by the continuation's ranking."""
    which = ",".join(map(str, left)) if len(left) <= 20 else f"<the {len(left)} unscored_clusters in {out}>"
    return f"{which} with a new --out"


def _fit_payload(st: dict, status: str) -> dict:
    """fit.json from the scoring state so far. status: running (checkpoint while scoring), budget (stopped at --budget-min)
    or done. The clusters not reached are unscored_clusters, the --select list that continues the run."""
    recs, clusters, fscales, f35_0 = st["recs"], st["clusters"], st["fscales"], st["f35_0"]
    recs.sort(key=lambda r: r["total"])
    clusters.sort(key=lambda x: x["best"]["total"] if x["best"] else float("inf"))
    for i, x in enumerate(clusters):
        x["rank"] = i + 1
    lead = ([x["best"] for x in clusters if x["best"]] if len(clusters) > 1 else recs)[:10]
    focal_edge = None
    if len(fscales) > 1 and lead:
        lo_s, hi_s = min(fscales), max(fscales)
        n_long = sum(r["fs"] == hi_s for r in lead)
        n_short = sum(r["fs"] == lo_s for r in lead)
        top1 = "long" if lead[0]["fs"] == hi_s else "short" if lead[0]["fs"] == lo_s else None
        if top1 or max(n_long, n_short) * 2 >= len(lead):
            focal_edge = {"top1": top1, "long": n_long, "short": n_short, "of": len(lead),
                          "range_f35": [round(f35_0 * lo_s, 1), round(f35_0 * hi_s, 1)]}
    unscored = [c["src_idx"] for c in st["centers"][st["n_done"]:]]
    return {"params": st["params"], "n_clusters": len(clusters), "n_cams": len(recs), "n_skipped": st["skipped"],
            "dem_failed_clusters": st["dem_failed"], "status": status, "pid": os.getpid(),
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "partial": bool(unscored), "unscored_clusters": unscored,
            "elapsed_min": round((time.monotonic() - st["t_start"]) / 60, 1), "focal_edge": focal_edge,
            "clusters": clusters, "cams": recs[:st["keep"]]}


def _cmd_fit(args) -> None:
    if bool(args.hits) == bool(args.at):
        sys.exit("give exactly one of --hits and --at")
    ridge = json.loads(Path(args.ridge).read_text(encoding="utf-8"))
    RX = np.array([p[0] for p in ridge["ridge"]], float)
    RY = np.array([p[1] for p in ridge["ridge"]], float)
    if RX.size < 3:
        sys.exit(f"ridge.json has only {RX.size} ridge points, needs at least 3")
    W, Hh = ridge["image_size"]
    hrow, f0, cx = float(ridge["hrow"]), float(ridge["f0"]), float(ridge.get("cx", W / 2))
    flat = ridge.get("flat")
    FLX = np.arange(flat[0], flat[1] + 1e-6, args.flat_step, dtype=float) if flat else np.zeros(0)
    NX = np.array([p[0] for p in ridge.get("near") or []], float)
    NY = np.array([p[1] for p in ridge.get("near") or []], float)
    ncl = ridge.get("near_clear") or []
    NCX = np.concatenate([np.arange(a, b + 1e-6, args.flat_step) for a, b, _ in ncl]) if ncl else np.zeros(0)
    NCR = np.concatenate([np.full(len(np.arange(a, b + 1e-6, args.flat_step)), r) for a, b, r in ncl]) if ncl else np.zeros(0)
    two = bool(NX.size or NCX.size)
    near_dists = [float(x) for x in args.near_dist.split(",")] if two else [None]
    if two:
        dropped = [d_ for d_ in near_dists if d_ <= args.near]
        near_dists = [d_ for d_ in near_dists if d_ > args.near]
        if not near_dists:
            sys.exit(f"every --near-dist value ({args.near_dist}) is within --near {args.near:g} m, where sight lines start: "
                     "give near distances beyond --near")
        if dropped:
            print(f"note: --near-dist {', '.join(f'{d_:g}' for d_ in dropped)} m dropped, within --near {args.near:g} m", file=sys.stderr)
    diag = math.hypot(W, Hh)
    f35_0 = f0 * 43.2666 / diag
    f_src = ridge.get("f0_source", "assumed")
    if args.focal_scales != "auto" and args.f35_range:
        sys.exit("give --focal-scales or --f35-range, not both")
    if args.focal_scales != "auto":
        fscales = [float(x) for x in args.focal_scales.split(",")]
        focal_how = "--focal-scales"
    elif args.f35_range or f_src == "assumed":
        try:
            lo, hi = (float(x) for x in args.f35_range.split(":")) if args.f35_range else F35_RANGE
        except ValueError:
            sys.exit(f"--f35-range must be lo:hi in mm, got {args.f35_range!r}")
        if not 0 < lo < hi:
            sys.exit("--f35-range needs 0 < lo < hi")
        n = max(2, math.ceil(math.log(hi / lo) / math.log(F35_RATIO)) + 1)
        fscales = [round(lo * (hi / lo) ** (i / (n - 1)) / f35_0, 4) for i in range(n)]
        focal_how = f"{lo:g}–{hi:g} mm equivalent, {n} steps"
    else:
        fscales = [0.9, 1.0, 1.12]
        focal_how = f"focal from {'EXIF' if f_src == 'exif' else '--f0'} × 0.9–1.12"
    px_metric = args.focal_metric == "px" or (args.focal_metric == "auto" and focal_how.endswith("steps"))
    print(f"focal ladder: {focal_how}, compared in {'pixels' if px_metric else 'degrees'} → " + ", ".join(f"{f35_0 * x:.0f}" for x in fscales) + " mm"
          + (f"; two-layer: {NX.size} near points, {NCX.size} near-clear columns, near distance {args.near_dist} m" if two else ""),
          file=sys.stderr)
    if args.grid <= 0 or args.radius < 0 or args.nsamp < 2 or args.near <= 0 or args.range <= args.near:
        sys.exit("need --grid > 0, --radius ≥ 0, --nsamp ≥ 2, 0 < --near < --range")
    az_step = args.az_step
    naz = int(round(360 / az_step))
    if abs(naz * az_step - 360) > 1e-6:
        sys.exit("--az-step must divide 360 evenly")
    if not 0 <= args.roll_max < 15:
        sys.exit("--roll-max must be between 0–15° (0 = don't solve roll)")
    roll_max = math.tan(math.radians(args.roll_max))
    AZ = np.arange(naz) * az_step
    HS = np.arange(naz)

    centers, scan_params = _load_centers(args)
    if not centers:
        sys.exit("no candidate clusters")
    scan_peak = scan_params.get("min_peak_deg")
    # scan kept only hits whose skyline reaches its own --min-peak: a stricter fit default would drop the cameras it found
    min_peak = args.min_peak if args.min_peak is not None else scan_peak if scan_peak is not None else 6.0

    PS = None                                                         # (n, 4) segments lat1, lon1, lat2, lon2 for the heading constraint
    if args.perp_line:
        segs = []
        for f_ in json.loads(Path(args.perp_line).read_text(encoding="utf-8")).get("features", []):
            g_ = f_.get("geometry") or {}
            parts = [g_["coordinates"]] if g_.get("type") == "LineString" else g_.get("coordinates", []) if g_.get("type") == "MultiLineString" else []
            for c_ in parts:
                segs += [(y1, x1, y2, x2) for (x1, y1, *_), (x2, y2, *_) in zip(c_, c_[1:])]
        if not segs:
            sys.exit(f"--perp-line {args.perp_line}: no LineString in it")
        PS = np.array(segs, float)

    # linear infrastructure sample points (optional)
    LP = None
    if args.line:
        if not args.line_dist:
            sys.exit("--line requires --line-dist L:C:R (three distance intervals, e.g. 350-750:550-900:800-1700)")
        wins = _parse_pairs(args.line_win, "--line-win", 3, ",", ":")
        dwin = _parse_pairs(args.line_dist, "--line-dist", 3, ":", "-")
        scales = [float(x) for x in args.line_scale.split(",")]
        if len(scales) != 3 or min(scales) <= 0:
            sys.exit("--line-scale needs 3 positive numbers, comma-separated")
        skip = _parse_skip_tags(args.skip_tag)
        reach_m = args.radius + args.line_reach
        lat_c = [c["lat"] for c in centers]
        lon_c = [c["lon"] for c in centers]
        d_lat = reach_m / 110540 + 0.01
        d_lon = reach_m / (111320 * math.cos(math.radians(max(abs(v) for v in lat_c)))) + 0.01   # a degree of longitude shrinks poleward
        bbox = (min(lat_c) - d_lat, min(lon_c) - d_lon, max(lat_c) + d_lat, max(lon_c) + d_lon)
        gj = json.loads(Path(args.line).read_text(encoding="utf-8"))
        pts = _line_points(gj, args.line_sample, skip, bbox)
        LP = np.array([[p[0], p[1]] for p in pts], dtype=float) if pts else np.zeros((0, 2))
        print(f"{len(LP)} infrastructure sample points (every {args.line_sample} m)", file=sys.stderr)

    ring_az = np.arange(0, 360, 45.0)
    ring_d = np.array([0.0, args.cam_flat_radius / 2, args.cam_flat_radius])
    done: set[tuple[int, int]] = set()
    recs: list[dict] = []
    clusters_out: list[dict] = []
    skipped = {"not_flat": 0, "off_level": 0, "no_peak": 0, "no_line": 0, "dup": 0, "missing_dem": 0, "no_perp_line": 0}
    dem_failed = []
    grid_pts = [(dx, dy) for dy in np.arange(-args.radius, args.radius + 1e-6, args.grid)
                for dx in np.arange(-args.radius, args.radius + 1e-6, args.grid) if dx * dx + dy * dy <= args.radius ** 2]
    if args.radius == 0:
        grid_pts = [(0.0, 0.0)]
    params = {"hits": args.hits, "at": args.at, "select": args.select, "ridge": str(args.ridge),
              "radius_m": args.radius, "grid_m": args.grid, "zoom": args.zoom, "focal_scales": fscales,
              "az_step_deg": az_step, "near_m": args.near, "range_m": args.range, "nsamp": args.nsamp, "eye_m": args.eye,
              "focal": focal_how, "focal_metric": "px" if px_metric else "deg", "f35_ladder": [round(f35_0 * x, 1) for x in fscales],
              "near_dist_m": near_dists if two else None, "near_clear_w": args.near_clear_w,
              "perp_line": args.perp_line, "perp_tol_deg": args.perp_tol if args.perp_line else None,
              "cam_flat_m": args.cam_flat, "cam_flat_radius_m": args.cam_flat_radius, "cam_level_m": args.cam_level, "min_peak_deg": min_peak,
              "cc_max_deg": args.cc_max, "roll_max_deg": args.roll_max, "flat_clear_deg": args.flat_clear, "flat_w": args.flat_w, "flat_step_px": args.flat_step,
              "line": args.line, "line_dist": args.line_dist, "line_win": args.line_win if args.line else None,
              "line_scale": args.line_scale if args.line else None, "line_order": args.line_order if args.line else None,
              "line_w": args.line_w, "line_min_m": args.line_min, "line_sample_m": args.line_sample, "line_reach_m": args.line_reach,
              "photo": {"f0_px": f0, "hrow": hrow, "cx": cx, "hfov_deg_at_fs1": round(2 * math.degrees(math.atan(cx / f0)), 1),
                        "n_ridge": int(RX.size), "flat": flat}}
    t_start = time.monotonic()
    st = {"params": params, "centers": centers, "recs": recs, "clusters": clusters_out, "skipped": skipped, "dem_failed": dem_failed,
          "n_done": 0, "t_start": t_start, "fscales": fscales, "f35_0": f35_0, "keep": args.keep}
    out_path = Path(args.out)
    saved, ck_err, last_save = None, None, None    # clusters in the last checkpoint written, why the latest attempt failed, when
    for ci, c in enumerate(centers):
        lat, lon = float(c["lat"]), float(c["lon"])
        name = c.get("name", "")
        elapsed_min = (time.monotonic() - t_start) / 60
        if args.budget_min and elapsed_min > args.budget_min and ci > 0:
            unscored = [cc["src_idx"] for cc in centers[ci:]]
            print(f"budget of {args.budget_min:g} min reached after {ci}/{len(centers)} clusters: writing the partial ranking; "
                  f"continue with --select {_select_list(unscored, args.out)} (or raise --budget-min)", file=sys.stderr)
            break
        try:
            dem = DEM((lat, lon), args.radius + args.range + 500, args.zoom, args.cache, args.proxy, args.allow_missing)
        except SystemExit as e:
            print(f"cluster {c['src_idx']} {name}: DEM failed ({e}), skipped", file=sys.stderr)
            dem_failed.append(c["src_idx"])
            st["n_done"] = ci + 1
            continue
        kx = 111320 * math.cos(math.radians(lat))
        level_h = None
        if args.cam_level is not None:                       # shore / bank / beach: the camera stands at the water's level
            level_h = c.get("h0")
            if level_h is None:
                level_h = float(dem.sample(np.array([lat]), np.array([lon]))[0])
            if math.isnan(level_h):
                print(f"cluster {c['src_idx']} {name}: no elevation at the cluster point, --cam-level not applied", file=sys.stderr)
                level_h = None
        sub = None
        if LP is not None and len(LP):
            m = (np.abs(LP[:, 0] - lat) * 110540 < args.radius + args.line_reach) & (np.abs(LP[:, 1] - lon) * kx < args.radius + args.line_reach)
            sub = LP[m]
        n_c = 0
        best_c = None
        for dx, dy in grid_pts:
            dx, dy = float(dx), float(dy)
            clat = lat + dy / 110540
            clon = lon + dx / kx
            key = (round(clat * 110540 / args.grid), round(clon * kx / args.grid))
            if key in done:
                skipped["dup"] += 1
                continue
            done.add(key)
            rla, rlo = _dest_np(clat, clon, ring_az, ring_d)
            g = dem.sample(rla, rlo)
            if np.isnan(g).any():
                skipped["missing_dem"] += 1
                continue
            if g.max() - g.min() > args.cam_flat:
                skipped["not_flat"] += 1
                continue
            g0 = float(g[:, 0].mean())
            if level_h is not None and abs(g0 - float(level_h)) > args.cam_level:
                skipped["off_level"] += 1
                continue
            ang, dist_v = cast(dem, (clat, clon), g0 + args.eye, AZ, args.range, near=args.near, n=args.nsamp, keep_nan=True)
            if np.isnan(ang).any():                                   # a missing far tile would drop a ridge out of the skyline; don't rank on it
                skipped["missing_dem"] += 1
                continue
            hor = ang.max(axis=1)
            if hor.max() < min_peak:
                skipped["no_peak"] += 1
                continue
            h_ok = None
            line_brg = None
            if PS is not None:
                kxc = math.cos(math.radians(clat))
                # distance to each segment, not its midpoint: a long span's midpoint can be km away while the wire passes overhead
                ay, ax = (PS[:, 0] - clat) * 110540, (PS[:, 1] - clon) * 111320 * kxc
                by, bx = (PS[:, 2] - clat) * 110540, (PS[:, 3] - clon) * 111320 * kxc
                L2 = (bx - ax) ** 2 + (by - ay) ** 2
                t = np.clip(-(ax * (bx - ax) + ay * (by - ay)) / np.where(L2 > 0, L2, 1), 0, 1)
                d2 = (ax + t * (bx - ax)) ** 2 + (ay + t * (by - ay)) ** 2
                i_ = int(np.argmin(d2))
                if d2[i_] > args.perp_reach ** 2:
                    skipped["no_perp_line"] += 1
                    continue
                y1, x1, y2, x2 = PS[i_]
                line_brg = math.degrees(math.atan2((x2 - x1) * kxc, y2 - y1)) % 180
                h_ok = np.abs((AZ - line_brg) % 180 - 90) <= args.perp_tol
            line_pen = None
            dmins = None
            if LP is not None:
                if sub is None or not len(sub):
                    skipped["no_line"] += 1
                    continue
                by = (sub[:, 0] - clat) * 110540
                bx = (sub[:, 1] - clon) * 111320 * math.cos(math.radians(clat))
                bd = np.hypot(bx, by)
                baz = np.degrees(np.arctan2(bx, by)) % 360
                off = (baz[None, :] - AZ[:, None] + 180) % 360 - 180            # (naz, n points)
                far = bd > args.line_min
                dmins = []
                for lo_, hi_ in wins:
                    mm = (off > lo_) & (off < hi_) & far[None, :]
                    dmins.append(np.where(mm, bd[None, :], np.inf).min(axis=1))
                line_pen = np.zeros(naz)
                for dm, (dlo, dhi), sc in zip(dmins, dwin, scales):
                    line_pen += np.maximum(0, dlo - dm) / sc + np.maximum(0, dm - dhi) / sc
                if args.line_order == "asc":
                    line_pen += ((dmins[0] >= dmins[1]) | (dmins[1] >= dmins[2])) * 1.0
                elif args.line_order == "desc":
                    line_pen += ((dmins[0] <= dmins[1]) | (dmins[1] <= dmins[2])) * 1.0
                if not np.isfinite(line_pen).any():
                    skipped["no_line"] += 1
                    continue
            best = None
            def idx(off):
                return (HS[:, None] + np.round(off / az_step).astype(int)[None, :]) % naz
            nhs = {D1: ang[:, dist_v <= D1].max(axis=1) if D1 else None for D1 in near_dists}   # near layer: highest angle within D1 m
            for D1, fs in ((d_, f_) for d_ in near_dists for f_ in fscales):
                nh = nhs[D1]
                f = f0 * fs
                r_off = np.degrees(np.arctan((RX - cx) / f))
                # elevation angle of a pixel off the optical axis: atan(dy·cos(rel)/f), not atan(dy/f); at a 30° offset the
                # difference is 2° on a 15° ridge, which fit would otherwise absorb into focal and heading
                r_el = np.degrees(np.arctan((hrow - RY) * np.cos(np.radians(r_off)) / f))
                # solve horizon offset cc (pitch/hrow inaccurate) and roll rr together by least squares: a 1° handheld tilt puts the ridgeline at both ends of the frame
                # off by a dozen-plus pixels; left unsolved, the ground truth gets crowded into the same rms tier as a pile of wrong candidates (one real photo: 11.1 → 6.2 px, only then did the ground truth stand out)
                diff = hor[idx(r_off)] - r_el[None, :]
                if NX.size:                                        # near points share cc and roll with the far ridge
                    n_off = np.degrees(np.arctan((NX - cx) / f))
                    diff = np.concatenate([diff, nh[idx(n_off)] - np.degrees(np.arctan((hrow - NY) * np.cos(np.radians(n_off)) / f))[None, :]], axis=1)
                    r_off = np.concatenate([r_off, n_off])
                if roll_max > 0 and (r_off != r_off.mean()).any():
                    oc = r_off - r_off.mean()
                    dmean = diff.mean(axis=1)
                    rr = np.clip(((diff - dmean[:, None]) * oc[None, :]).sum(axis=1) / (oc ** 2).sum(), -roll_max, roll_max)
                    cc = np.clip(dmean - rr * r_off.mean(), -args.cc_max, args.cc_max)
                else:                                              # --roll-max 0: no roll term, cc = residual median
                    rr = np.zeros(naz)
                    cc = np.clip(np.median(diff, axis=1), -args.cc_max, args.cc_max)
                res = diff - cc[:, None] - rr[:, None] * r_off[None, :]
                rms = np.sqrt(np.mean(res ** 2, axis=1))
                rms_near = np.sqrt(np.mean(res[:, RX.size:] ** 2, axis=1)) if NX.size else None
                if FLX.size:
                    fl_off = np.degrees(np.arctan((FLX - cx) / f))
                    pen = np.mean(np.clip(hor[idx(fl_off)] - cc[:, None] - args.flat_clear, 0, None), axis=1)
                else:
                    pen = np.zeros(naz)
                if NCX.size:                                       # near-clear columns: the near layer must stay below the given row
                    c_off = np.degrees(np.arctan((NCX - cx) / f))
                    c_el = np.degrees(np.arctan((hrow - NCR) * np.cos(np.radians(c_off)) / f))
                    ncpen = np.mean(np.clip(nh[idx(c_off)] - cc[:, None] - rr[:, None] * c_off[None, :] - c_el[None, :], 0, None), axis=1)
                else:
                    ncpen = np.zeros(naz)
                # across a wide focal ladder, compare in pixels (× fs, i.e. degrees at the base focal): in degrees the same pixel mismatch shrinks as f grows, and on a
                # real photo every candidate ran to the longest rung. Within ×0.9–1.12 degrees stay: there pixels pushed focal short and camera positions farther
                score = (rms + args.flat_w * pen + args.near_clear_w * ncpen) * (fs if px_metric else 1.0)
                total = score + args.line_w * line_pen if line_pen is not None else score
                if h_ok is not None:
                    total = np.where(h_ok, total, np.inf)
                k = int(np.argmin(total))
                if not np.isfinite(total[k]):
                    continue
                if best is None or total[k] < best["total"]:
                    best = {"hit": c["src_idx"], "name": name, "hit_ll": [round(lat, 5), round(lon, 5)],
                            "cam": [round(clat, 5), round(clon, 5)],
                            "d": round(math.hypot(dx, dy)), "brg": round(math.degrees(math.atan2(dx, dy)) % 360),
                            "g": round(g0, 1), "H": round(k * az_step, 2), "fs": fs, "f": round(f, 1), "f35": round(f35_0 * fs, 1),
                            "cc": round(float(cc[k]), 2), "roll": round(math.degrees(math.atan(float(rr[k]))), 2),
                            "rms": round(float(rms[k]), 3),
                            "rms_px": round(float(rms[k]) * f * math.pi / 180, 1), "flatpen": round(float(pen[k]), 3),
                            "score": round(float(score[k]), 3)}
                    if D1:
                        best.update({"D1": D1, "nclearpen": round(float(ncpen[k]), 3)})
                        if rms_near is not None:
                            best["rms_near_px"] = round(float(rms_near[k]) * f * math.pi / 180, 1)
                    if line_brg is not None:
                        best["line_brg"] = round(line_brg, 1)
                    if line_pen is not None:
                        best.update({"dL": round(float(dmins[0][k])), "dC": round(float(dmins[1][k])), "dR": round(float(dmins[2][k])),
                                     "line_pen": round(float(line_pen[k]), 3)})
                    best["total"] = round(float(total[k]), 3)
            if best is None:
                skipped["no_line"] += 1
                continue
            recs.append(best)
            n_c += 1
            if best_c is None or best["total"] < best_c["total"]:
                best_c = best
        tie = tie_extent([r for r in recs if r["hit"] == c["src_idx"]], best_c["total"], args.tie) if best_c else None
        clusters_out.append({"hit": c["src_idx"], "name": name, "hit_ll": [round(lat, 5), round(lon, 5)],
                             "n": c.get("n"), "max_ang": c.get("max_ang"), "n_cams": n_c, "best": best_c, "tie": tie})
        st["n_done"] = ci + 1
        now = time.monotonic()
        if last_save is None or now - last_save >= CHECKPOINT_S or ci + 1 == len(centers):
            try:
                _save_json(out_path, _fit_payload(st, "running"))
                saved, ck_err, last_save = ci + 1, None, now
            except OSError as e:                                       # a reader holding the file (Windows), a full disk: keep scoring
                ck_err = type(e).__name__
        if saved is None:
            note = f"not saved yet: {ck_err}; if killed: rerun this command"
        else:
            rem = [x["src_idx"] for x in centers[saved:]]
            note = (f"checkpoint failed: {ck_err}; " if ck_err else "") + f"saved {saved}/{len(centers)}"
            if rem:
                note += f"; if killed: --select {_select_list(rem, args.out)}"
        per = (time.monotonic() - t_start) / (ci + 1)
        eta = f"  [{per:.1f} s/cluster, ~{per * (len(centers) - ci - 1) / 60:.0f} min left]" if len(centers) > 3 else ""
        print(f"cluster {ci + 1}/{len(centers)} hit{c['src_idx']} {name or '-'}: scored {n_c} camera positions"
              + (f", best total {best_c['total']}  H {best_c['H']}  cam {best_c['cam']}" if best_c else ", no camera position passed the filters")
              + eta + f" ({note})", file=sys.stderr)

    out = _fit_payload(st, "budget" if st["n_done"] < len(centers) else "done")
    try:
        _save_json(out_path, out, keep_part=True)
    except OSError as e:                              # the scoring is done: a reader holding fit.json must not cost the ranking
        part = _part_of(out_path)
        if not part.exists():
            raise
        print(f"WARNING: {args.out} not replaced ({type(e).__name__}: another process holds it open); the full ranking is in {part}. "
              f"Close the reader, then move it over: Move-Item -Force -LiteralPath {_ps_quote(part)} -Destination {_ps_quote(out_path)} "
              f"(PowerShell) or mv -f {shlex.quote(str(part))} {shlex.quote(str(out_path))} (bash).", file=sys.stderr)
    focal_edge = out["focal_edge"]
    print(f"clusters {len(clusters_out)}, camera positions {len(recs)}, skipped {skipped} → {args.out}"
          + (f"  PARTIAL: {len(out['unscored_clusters'])} clusters not scored (budget); the ranking below covers the scored ones only"
             if out["partial"] else ""), file=sys.stderr)
    if args.min_peak is not None and scan_peak is not None and args.min_peak > scan_peak:
        print(f"note: --min-peak {args.min_peak:g}° is stricter than scan's {scan_peak:g}° (params.min_peak_deg in {args.hits})"
              + (f"; {skipped['no_peak']} camera positions were skipped as no_peak: rerun without --min-peak to score them at scan's value"
                 if skipped["no_peak"] else ""), file=sys.stderr)
    if skipped["missing_dem"]:
        print(f"WARNING: {skipped['missing_dem']} camera positions not scored because their sight lines touch missing tiles", file=sys.stderr)
    if skipped["off_level"] and skipped["off_level"] >= len(recs):        # the level filter decided the ranking more than the skyline did
        print(f"WARNING: --cam-level {args.cam_level:g} dropped {skipped['off_level']} camera positions (ground more than {args.cam_level:g} m "
              f"from the line's level) and kept {len(recs)}. A lake shore keeps a few metres; a camera on a valley floor, a meadow or a road "
              f"above the river stands higher: rerun with a larger --cam-level.", file=sys.stderr)
    for x in clusters_out[:min(args.top, 10)]:
        b = x["best"]
        if b:
            line_txt = f"  L/C/R {b['dL']}/{b['dC']}/{b['dR']} pen {b['line_pen']}" if "line_pen" in b else ""
            near_txt = (f"  D1 {b['D1'] / 1000:g} km near {b.get('rms_near_px', '-')} px clear {b['nclearpen']}" if "D1" in b else "")
            t = x.get("tie") or {}
            tie_txt = f"  span {t['span_m']:.0f} m along {t['bearing']:.0f}° ({t['n']} positions within {t['delta']})" if t.get("n", 0) > 1 else ""
            print(f"  {x['rank']:>3}. hit{x['hit']} {x['name'] or '-'}  cam {b['cam']}  H {b['H']}  f {b['f']:.0f} ({b['f35']:.0f} mm)  "
                  f"rms {b['rms']} ({b['rms_px']} px)  flat {b['flatpen']}{near_txt}{line_txt}  total {b['total']}{tie_txt}", file=sys.stderr)
    lead = clusters_out[0] if clusters_out else None
    if lead and lead.get("best"):
        t = lead.get("tie") or {}
        hfov_best = 2 * math.degrees(math.atan((W / 2) / lead["best"]["f"]))
        if t.get("n", 0) > 1 and t["span_m"] > args.grid:
            print(f"Position ambiguity: {t['n']} camera positions score within {t['delta']} of the best and span {t['span_m']:.0f} m along "
                  f"{t['bearing']:.0f}°. The skyline fixes a sight line, not a point: put the answer on the road, shore or building inside this "
                  f"stretch (osm.py geom / satellite) and give a radius of at least {t['span_m'] / 2:.0f} m; a finer grid will not separate them.", file=sys.stderr)
        elif args.radius == 0:
            print("Single camera position (--radius 0): the score says how well this point fits, not how far along the sight line the camera "
                  "could move; test the alternatives (the road, the field edge) with the same command before closing.", file=sys.stderr)
        print(f"PeakFinder, same camera for the eyes: {peakfinder_url(lead['best']['cam'][0], lead['best']['cam'][1], lead['best']['H'], hfov_best, lead['best']['g'])}", file=sys.stderr)
        b = lead["best"]
        # fit keeps the camera level and puts the horizon on hrow; view centres the principal point and tilts the camera.
        # Both put the horizon on the same row when pitch = cc + atan((hrow − image height / 2) / f): hrow below the middle = looking up
        pitch = b["cc"] + math.degrees(math.atan((hrow - Hh / 2) / b["f"]))
        photo = _fit_photo(args, ridge)
        cmd = ["terrain.py", "view", "--at", f"{b['cam'][0]:.5f},{b['cam'][1]:.5f}", "--height", f"{args.eye:g}",
               "--heading", f"{b['H']:g}", "--hfov", f"{hfov_best:.1f}", "--pitch", f"{pitch:.2f}", "--roll", f"{b['roll']:g}",
               "--range", f"{args.range:g}", "--zoom", str(args.zoom), "--near", f"{args.near:g}",
               "--photo", str(photo) if photo else "<photo>"]
        cmd += ["--peaks", args.peaks] if args.peaks else []
        cmd += ["--allow-missing"] if args.allow_missing else []
        cmd += ["--overlay", "--out", str(Path(args.out).with_name("view_best.jpg"))]
        print("Overlay check, this camera's skyline drawn on the photo: " + " ".join(shlex.quote(a) for a in cmd), file=sys.stderr)
    if focal_edge:
        lo_mm, hi_mm = focal_edge["range_f35"]
        side = focal_edge["top1"] or ("long" if focal_edge["long"] >= focal_edge["short"] else "short")
        n_side = focal_edge[side]
        if f_src != "assumed" and args.focal_scales == "auto" and not args.f35_range:
            print(f"WARNING: focal is known ({'EXIF' if f_src == 'exif' else '--f0'}) yet {n_side}/{focal_edge['of']} leading results sit on the {side} end "
                  f"of ×0.9–1.12: it is absorbing another error (hrow, ridge points, crop, wrong place). Check ridge --png before widening.", file=sys.stderr)
        else:
            wider = f"{hi_mm * 0.6:.0f}:{hi_mm * 2:.0f}" if side == "long" else f"{max(8, lo_mm / 2):.0f}:{lo_mm * 1.7:.0f}"
            print(f"WARNING: best focal sits on the {side} end of the ladder ({hi_mm if side == 'long' else lo_mm:.0f} mm) for {n_side}/{focal_edge['of']} "
                  f"leading results{' including #1' if focal_edge['top1'] else ''}. That is a signal, not noise: the photo is probably "
                  f"{'more zoomed in' if side == 'long' else 'wider'} than the ladder. Rerun with --f35-range {wider} before trusting the ranking, "
                  f"heading or focal; only if it runs to the new edge again is the focal absorbing another error (geometry.md 7.4).", file=sys.stderr)
    if args.sheet:
        top = [x["best"] for x in clusters_out if x["best"]][:args.top] if len(clusters_out) > 1 else recs[:args.top]
        if not top:
            print("no camera positions to draw, no overlay", file=sys.stderr)
        else:
            photo = _fit_photo(args, ridge)
            if photo is None:
                print("photo not found (--overlay not given, and the photo path in ridge.json can't be found either); drawing the overlay on a gray background", file=sys.stderr)
            _fit_sheet(top, ridge, photo, Path(args.sheet), args, AZ, args.nsamp)
            stack = Path(args.sheet).with_name(Path(args.sheet).stem + "_skyline.jpg")       # the live page's Skyline card
            peaks = load_peaks(args.peaks) if args.peaks else None
            best3 = top[:3]
            _fit_sheet(best3, ridge, photo, stack, args, AZ, args.nsamp, style="stack", peaks=peaks)
            side = {"image": stack.name, "fit": str(args.out), "photo": str(photo) if photo else None, "peaks_file": args.peaks,
                    "top": [{"rank": i + 1, "hit": r["hit"], "name": r["name"] or "-", "cam": r["cam"], "heading": r["H"], "f35": r.get("f35"),
                             "rms_px": r.get("rms_px"), "total": r["total"], "peaks": r.get("peaks", []),
                             "tie": next((x.get("tie") for x in clusters_out if x["hit"] == r["hit"]), None),
                             "peakfinder_url": peakfinder_url(r["cam"][0], r["cam"][1], r["H"], 2 * math.degrees(math.atan((W / 2) / r["f"])), r["g"])}
                            for i, r in enumerate(best3)]}
            stack.with_suffix(".json").write_text(json.dumps(side, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"skyline card → {stack} + {stack.with_suffix('.json').name} (top {len(best3)} stacked over the photo"
                  + (f", {sum(len(r.get('peaks', [])) for r in best3)} summit labels" if peaks else "") + ")", file=sys.stderr)
    if dem_failed:                                                    # output is written, but the ranking is missing these clusters
        sys.exit(f"{len(dem_failed)}/{len(centers)} clusters not scored because their DEM failed "
                 f"(hit {', '.join(map(str, dem_failed))}); re-run to retry them, the ranking above is incomplete")


def load_points(path: Path) -> list[tuple[str, float, float]]:
    """{name:[lat,lon]} or {name:{"lat","lon"}} or {pano_id:{"wgs":[lat,lon]}} (gsv.py area) or a list of {name,lat,lon} dicts."""
    j = json.loads(Path(path).read_text(encoding="utf-8"))
    items = list(j.items()) if isinstance(j, dict) else [(d.get("name", f"p{i}"), d) for i, d in enumerate(j)]
    out = []
    for name, v in items:
        try:
            if isinstance(v, dict):
                la, lo = (v["lat"], v["lon"]) if "lat" in v else v["wgs"]
            else:
                la, lo = v[0], v[1]
            out.append((str(name), float(la), float(lo)))
        except (KeyError, IndexError, TypeError, ValueError):
            sys.exit(f"--points {path}: {name!r} has no lat/lon")
    if not out:
        sys.exit(f"--points {path}: no points")
    return out


def _write_rows(rows: list[dict], out: Path | None) -> None:
    if out:
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"-> {out}")


def _cmd_elev(args) -> None:
    if bool(args.at) == bool(args.points):
        sys.exit("give exactly one of --at and --points")
    pts = [("", *map(float, args.at.split(",")))] if args.at else load_points(args.points)
    rows = []
    for name, lat, lon in pts:
        dem = DEM((lat, lon), 300, args.zoom, args.cache, args.proxy, args.allow_missing)
        h = float(dem.sample(np.array([lat]), np.array([lon]))[0])
        if math.isnan(h):
            if args.at:
                sys.exit("no elevation here: the tile under this point failed to download")
            print(f"{name}: no elevation (missing tile), skipped", file=sys.stderr)
            continue
        rows.append({"name": name, "lat": lat, "lon": lon, "elev_m": round(h, 1)})
        print(f"{h:.0f} m" if args.at else f"{name}\t{lat:.5f},{lon:.5f}\t{h:.0f} m")
    _write_rows(rows, args.out)


def _cmd_slope(args) -> None:
    if args.span <= 0:
        sys.exit("--span must be > 0 m")
    half = args.span / 2
    rows = []
    print(f"{'name':<24} {'elev':>7} {'fwd':>7} {'back':>7} {'slope%':>7}   (+ = ground rises toward {args.bearing % 360:g}°, span {args.span:g} m)")
    for name, lat, lon in load_points(args.points):
        dem = DEM((lat, lon), half + 300, args.zoom, args.cache, args.proxy, args.allow_missing)
        fwd, back = geo.dest((lat, lon), args.bearing, half), geo.dest((lat, lon), args.bearing + 180, half)
        h0, hf, hb = (float(v) for v in dem.sample(np.array([lat, fwd[0], back[0]]), np.array([lon, fwd[1], back[1]])))
        if any(math.isnan(v) for v in (h0, hf, hb)):
            print(f"{name}: missing tile, skipped", file=sys.stderr)
            continue
        slope = (hf - hb) / args.span * 100
        rows.append({"name": name, "lat": lat, "lon": lon, "elev_m": round(h0, 1), "fwd_m": round(hf, 1), "back_m": round(hb, 1),
                     "slope_pct": round(slope, 1), "slope_deg": round(math.degrees(math.atan(slope / 100)), 1)})
        print(f"{name[:24]:<24} {h0:7.1f} {hf:7.1f} {hb:7.1f} {slope:7.1f}")
    _write_rows(rows, args.out)



# ---------------------------------------------------------------- shade: where the shadows lie at a place and time
def shadow_mask(dem: DEM, lat, lon, az: float, el: float, step: float = 30.0, reach: float = 8000.0, lift: float = 0.0) -> np.ndarray:
    """True where the ground at (lat, lon) lies in terrain shadow for a sun at compass azimuth az and elevation el (degrees):
    march toward the sun every `step` m out to `reach` m; any terrain above the sun ray shades the point. `lift` raises the
    tested point above the ground (a roof, a window). el ≤ 0 → everything is in shadow (night)."""
    lat = np.asarray(lat, dtype=float).ravel()
    lon = np.asarray(lon, dtype=float).ravel()
    if el <= 0:
        return np.ones(lat.shape, dtype=bool)
    h0 = dem.sample(lat, lon) + lift
    k = np.arange(1, int(reach / step) + 1, dtype=float) * step
    dx = k * math.sin(math.radians(az))
    dy = k * math.cos(math.radians(az))
    drop = k ** 2 / (2 * R_EARTH) * (1 - K_REFRACTION)            # earth curvature over the march
    ray = k * math.tan(math.radians(el)) + drop
    shaded = np.zeros(lat.shape, dtype=bool)
    chunk = max(1, 4_000_000 // max(1, k.size))
    for i0 in range(0, lat.size, chunk):
        sl = slice(i0, i0 + chunk)
        kx = 111320 * np.cos(np.radians(lat[sl]))
        la = lat[sl][:, None] + dy[None, :] / 110540
        lo = lon[sl][:, None] + dx[None, :] / kx[:, None]
        rise = dem.sample(la, lo) - h0[sl][:, None] - ray[None, :]
        rise = np.where(np.isnan(rise), -np.inf, rise)
        shaded[sl] = rise.max(axis=1) > 0
    shaded[np.isnan(h0)] = False                                  # no elevation at the point itself: cannot say, treat as lit
    return shaded


def _building_height(tags: dict, default_h: float, level_h: float) -> float:
    for key in ("height", "building:height", "est_height"):
        v = tags.get(key)
        if v:
            m = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)", str(v).replace(",", "."))
            if m:
                return float(m.group(1))
    lv = tags.get("building:levels")
    if lv:
        m = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)", str(lv))
        if m:
            return float(m.group(1)) * level_h + float(tags.get("roof:levels") or 0) * level_h
    return default_h


def building_shadows(gj: dict, az: float, el: float, default_h: float = 8.0, level_h: float = 3.0) -> list[dict]:
    """Shadow polygons (lon/lat rings) of every polygon feature in a GeoJSON (osm.py geom '["building"]' output): the footprint,
    the footprint moved by the shadow vector, and one quad per edge in between. el ≤ 0 → no building shadows (night, the
    terrain mask already covers everything)."""
    out = []
    if el <= 0:
        return out
    L_per_m = 1.0 / math.tan(math.radians(el))
    sb = math.radians((az + 180) % 360)
    for ft in gj.get("features", []):
        g = ft.get("geometry") or {}
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        rings = g["coordinates"] if g["type"] == "Polygon" else [r for poly in g["coordinates"] for r in poly[:1]]
        tags = ft.get("properties") or {}
        h = _building_height(tags, default_h, level_h)
        L = h * L_per_m
        for ring in rings[:1]:                                  # outer ring only: a courtyard does not cast a shadow outward
            if len(ring) < 3:
                continue
            lat0 = ring[0][1]
            dlat = L * math.cos(sb) / 110540
            dlon = L * math.sin(sb) / (111320 * math.cos(math.radians(lat0)))
            moved = [[x + dlon, y + dlat] for x, y in ring]
            polys = [ring, moved]
            for (x1, y1), (x2, y2), (mx1, my1), (mx2, my2) in zip(ring, ring[1:], moved, moved[1:]):
                polys.append([[x1, y1], [x2, y2], [mx2, my2], [mx1, my1]])
            out.append({"id": ft.get("id"), "height_m": round(h, 1), "shadow_m": round(L, 1), "polys": polys})
    return out


def _point_in_poly(x: float, y: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi > x:
                inside = not inside
    return inside


def in_building_shadow(lat: float, lon: float, shadows: list[dict]) -> bool:
    return any(_point_in_poly(lon, lat, ring) for b in shadows for ring in b["polys"])


def _parse_pt(s: str) -> tuple[float, float, str]:
    """lat,lon[:label] → (lat, lon, label)."""
    body, _, label = s.partition(":")
    lat, lon = map(float, body.split(","))
    return lat, lon, label or f"{lat:.5f},{lon:.5f}"


def _shade_state(dem: DEM, pts: list, az: float, el: float, step: float, reach: float, shadows: list[dict]) -> list[dict]:
    lat = np.array([p[0] for p in pts]); lon = np.array([p[1] for p in pts])
    terr = shadow_mask(dem, lat, lon, az, el, step, reach) if len(pts) else np.zeros(0, dtype=bool)
    rows = []
    for (la, lo, label), ts in zip(pts, terr):
        bs = bool(in_building_shadow(la, lo, shadows)) if el > 0 else False
        rows.append({"label": label, "lat": la, "lon": lo, "terrain_shadow": bool(ts), "building_shadow": bs, "lit": not (ts or bs) and el > 0})
    return rows


def _hillshade(h: np.ndarray, mpp: float, az: float, el: float) -> np.ndarray:
    """Lambertian shading 0..1 of an elevation grid (rows = north→south, cols = west→east)."""
    hh = np.where(np.isnan(h), np.nanmean(h) if np.isfinite(np.nanmean(h)) else 0.0, h)
    gy, gx = np.gradient(hh, mpp)                               # gy: increase southward; gx: eastward
    nx, ny, nz = -gx, gy, np.ones_like(hh)                      # outward normal (east, north, up)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    sa, se = math.radians(az), math.radians(max(el, 0.0))
    sx, sy, sz = math.sin(sa) * math.cos(se), math.cos(sa) * math.cos(se), math.sin(se)
    return np.clip((nx * sx + ny * sy + nz * sz) / norm, 0.0, 1.0)


def _cmd_shade(args) -> None:
    import sun                                                   # same directory: NOAA sun position, time zone parsing
    lat, lon = map(float, args.at.split(","))
    zone = sun._zone(args.tz)
    if not args.time and not (args.date or args.dates):
        sys.exit("give --time (render the shadows at that moment) and/or --date / --dates (sweep the day for the --lit / --shaded pattern)")
    checks = [_parse_pt(s) for s in (args.check or [])]
    lit_pts = [_parse_pt(s) for s in (args.lit or [])]
    shd_pts = [_parse_pt(s) for s in (args.shaded or [])]
    far = max([geo.distance((lat, lon), (p[0], p[1])) for p in checks + lit_pts + shd_pts] + [0.0])
    dem = DEM((lat, lon), args.radius + args.reach + far + 500, args.zoom, args.cache, args.proxy, args.allow_missing)
    bgj = json.loads(Path(args.buildings).read_text(encoding="utf-8")) if args.buildings else None
    result: dict = {"at": [lat, lon], "tz": args.tz or "UTC", "step_m": args.step, "reach_m": args.reach, "zoom": args.zoom}

    if args.time:
        t = sun._to_utc(args.time, args.tz)
        az, el = sun.sun_position(lat, lon, t)
        shadows = building_shadows(bgj, az, el, args.default_height, args.level_height) if bgj else []
        local = t.astimezone(zone)
        result.update({"time_local": local.isoformat(timespec="minutes"), "utc": t.isoformat(timespec="minutes"),
                       "sun_azimuth": round(az, 2), "sun_elevation": round(el, 2), "shadow_bearing": round((az + 180) % 360, 1),
                       "shadow_len_per_1m": None if el <= 0 else round(1 / math.tan(math.radians(el)), 3),
                       "buildings": len(shadows)})
        states = _shade_state(dem, checks, az, el, args.step, args.reach, shadows)
        if args.out:
            # render grid: the mosaic's pixels when --map is given, else a square of --size px around --at
            if args.map:
                meta = json.loads(Path(args.map).with_suffix(".json").read_text(encoding="utf-8"))
                base = Image.open(args.map).convert("RGB")
                W, H = base.size
                z, (ox, oy) = meta["zoom"], meta["origin_tile"]
                px = np.arange(W, dtype=float) + ox * 256 + 0.5
                py = np.arange(H, dtype=float) + oy * 256 + 0.5
                n = 256 * 2 ** z
                lons = px / n * 360 - 180
                lats = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * py / n))))
                mpp = geo.meters_per_px(z, lat)

                def to_px(la, lo):
                    x, y = geo.ll2px(z, la, lo)
                    return x - ox * 256, y - oy * 256
            else:
                W = H = args.size
                mpp = 2 * args.radius / args.size
                base = None
                kx = 111320 * math.cos(math.radians(lat))
                lons = lon + (np.arange(W, dtype=float) - W / 2 + 0.5) * mpp / kx
                lats = lat - (np.arange(H, dtype=float) - H / 2 + 0.5) * mpp / 110540

                def to_px(la, lo):
                    return (lo - lon) * kx / mpp + W / 2, (lat - la) * 110540 / mpp + H / 2
            LA, LO = np.meshgrid(lats, lons, indexing="ij")
            hgrid = dem.sample(LA, LO)
            mask = np.zeros((H, W), dtype=bool)
            rows = max(1, 2_000_000 // max(1, W * int(args.reach / args.step)))
            for r0 in range(0, H, rows):
                sl = slice(r0, min(H, r0 + rows))
                mask[sl] = shadow_mask(dem, LA[sl], LO[sl], az, el, args.step, args.reach).reshape(LA[sl].shape)
            if base is None:
                hs = _hillshade(hgrid, mpp, az, el)
                g = (70 + 170 * hs).astype(np.uint8)
                arr = np.stack([g, g, g], axis=-1)
            else:
                arr = np.asarray(base).copy()
            arr = arr.astype(np.float32)
            arr[mask] *= 0.42                                       # terrain shadow: darkened
            img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
            lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            for b in shadows:                                      # building shadows: blue-black
                for ring in b["polys"]:
                    pts = [to_px(y, x) for x, y in ring]
                    if len(pts) >= 3:
                        d.polygon(pts, fill=(10, 20, 70, 150))
            if bgj:
                for ft in bgj.get("features", []):
                    g2 = ft.get("geometry") or {}
                    if g2.get("type") == "Polygon":
                        pts = [to_px(y, x) for x, y in g2["coordinates"][0]]
                        if len(pts) >= 3:
                            d.polygon(pts, outline=(255, 255, 255, 200))
            img = Image.alpha_composite(img, lay)
            d = ImageDraw.Draw(img)
            cx, cy = to_px(lat, lon)
            d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], outline="yellow", width=3)
            if el > 0:                                             # arrow toward the sun; the shadow of the centre point falls the other way
                ax, ay = cx + 70 * math.sin(math.radians(az)), cy - 70 * math.cos(math.radians(az))
                d.line([(cx, cy), (ax, ay)], fill="yellow", width=4)
                d.ellipse([ax - 7, ay - 7, ax + 7, ay + 7], fill="yellow")
            for row in states:
                x, y = to_px(row["lat"], row["lon"])
                col = "lime" if row["lit"] else "red"
                d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=col, outline="black", width=2)
                d.text((x + 10, y - 7), f"{row['label']}: {'lit' if row['lit'] else 'shadow'}", fill=col, font=_font(16), stroke_width=2, stroke_fill="black")
            txt = (f"{local.strftime('%Y-%m-%d %H:%M')} {args.tz or 'UTC'}  sun az {az:.1f}° el {el:.1f}°  shadow → {(az + 180) % 360:.0f}°, "
                   f"1 m casts {1 / math.tan(math.radians(el)) if el > 0 else float('inf'):.2f} m  |  dark = terrain shadow, blue = building shadow  |  {mpp:.1f} m/px")
            d.rectangle([0, 0, img.size[0], 26], fill=(0, 0, 0, 180))
            d.text((6, 4), txt, fill="yellow", font=_font(16))
            img.convert("RGB").save(args.out)
            result["image"] = str(args.out)
            result["shaded_fraction"] = round(float(mask.mean()), 3)
            print(f"{txt}\n{mask.mean() * 100:.0f}% of the frame in terrain shadow → {args.out}")
        result["checks"] = states
        for row in states:
            print(f"  {row['label']:<28} {'LIT' if row['lit'] else 'SHADOW'}" + ("  (terrain)" if row["terrain_shadow"] else "") + ("  (building)" if row["building_shadow"] else ""))

    if args.date or args.dates:
        from datetime import date, datetime, timedelta, timezone
        if args.dates:
            a, b = args.dates.split(":")
            d0, d1 = date.fromisoformat(a), date.fromisoformat(b)
        else:
            d0 = d1 = date.fromisoformat(args.date)
        if not lit_pts and not shd_pts:
            lit_pts = [(lat, lon, "centre")]
        days = []
        day = d0
        while day <= d1:
            prev_ok, start, spans = False, None, []
            n_steps = 24 * 60 // args.minutes
            for i in range(n_steps + 1):
                local = datetime(day.year, day.month, day.day, tzinfo=zone) + timedelta(minutes=i * args.minutes)
                t = local.astimezone(timezone.utc)
                az, el = sun.sun_position(lat, lon, t)
                ok = el > 0
                if ok:
                    shadows = building_shadows(bgj, az, el, args.default_height, args.level_height) if bgj else []
                    st = _shade_state(dem, lit_pts + shd_pts, az, el, args.step, args.reach, shadows)
                    ok = all(r["lit"] for r in st[:len(lit_pts)]) and all(not r["lit"] for r in st[len(lit_pts):])
                if ok and not prev_ok:
                    start = local
                if (not ok or i == n_steps) and prev_ok:
                    spans.append((start, local))
                prev_ok = ok
            days.append({"date": day.isoformat(), "spans": [[s.strftime("%H:%M"), e.strftime("%H:%M")] for s, e in spans]})
            day += timedelta(days=args.date_step)
        result["sweep"] = {"lit": [p[2] for p in lit_pts], "shaded": [p[2] for p in shd_pts], "minutes": args.minutes, "days": days}
        print(f"pattern: lit {[p[2] for p in lit_pts]} and shaded {[p[2] for p in shd_pts]} (every {args.minutes} min, local {args.tz or 'UTC'})")
        for dd in days:
            print(f"  {dd['date']}: " + (", ".join(f"{s}–{e}" for s, e in dd["spans"]) if dd["spans"] else "never"))
        if not any(dd["spans"] for dd in days):
            print("  no time matches: a lit/shaded point may be mislabelled, or the camera position is wrong; loosen one constraint at a time", file=sys.stderr)
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"→ {args.json}")


def _cmd_view(args) -> None:
    """view and profile: sight lines from one camera position; profile writes the skyline JSON, view renders and overlays it."""
    lat, lon = map(float, args.at.split(","))
    dem = DEM((lat, lon), args.range, args.zoom, args.cache, args.proxy, args.allow_missing)
    ground = float(dem.sample(np.array([lat]), np.array([lon]))[0])
    if math.isnan(ground):
        sys.exit("no elevation at the camera position: the tile under it failed to download")
    eye = args.alt if args.alt is not None else ground + args.height
    az = np.linspace(args.heading - args.hfov / 2, args.heading + args.hfov / 2, args.width)
    if eye < ground + 1:
        print(f"note: eye height {eye:.0f} m is below the ground at this point {ground:.0f} m, so nearby terrain will be taken as the skyline (--alt is wrong, or you should use --height)")
    ang, dist = cast(dem, (lat, lon), eye, az % 360, args.range, near=args.near)

    if args.cmd == "profile":
        runmax = np.max(ang, axis=1)
        far = dist[np.argmax(ang, axis=1)]
        step = max(1, args.width // 180)
        out = [{"azimuth": round(float(az[i] % 360), 2), "skyline_deg": round(float(runmax[i]), 3), "skyline_dist_m": round(float(far[i]))}
               for i in range(0, args.width, step)]
        args.out.write_text(json.dumps({"at": [lat, lon], "eye_alt_m": round(eye, 1), "ground_m": round(ground, 1), "profile": out}, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"ground {ground:.0f} m, eye height {eye:.0f} m → {args.out}")
        return

    if args.vfov:
        vfov = args.vfov
    elif args.hfov >= 170:
        vfov = 40.0  # panoramic strip (angles map linearly), e.g. --hfov 360 when the heading is unknown
    else:
        vfov = 2 * math.degrees(math.atan(math.tan(math.radians(args.hfov / 2)) * 2 / 3))
    height = int(args.width * vfov / args.hfov)
    im, sky_ang, sky_dist = render(ang, dist, az, args.pitch, vfov, height)
    title = (f"camera {lat:.5f},{lon:.5f}  ground {ground:.0f} m eye {eye:.0f} m  heading {args.heading % 360:.0f}°  "
             f"hfov {args.hfov:.0f}°  farthest skyline {np.nanmax(sky_dist) / 1000:.1f} km")
    im = annotate(im, az, args.pitch, vfov, title)
    # summit names, PeakFinder-style: (peak, bearing offset from the frame centre) for the peaks inside the frame, shared by render and overlay.
    # Only loaded when a label pass will draw them (render below 170 deg hfov, or the photo overlay).
    want_peaks = bool(args.peaks) and (args.hfov < 170 or bool(args.photo and args.overlay))
    in_view = [(pk, (pk["bearing"] - args.heading + 180) % 360 - 180)
               for pk in (peaks_in_view(load_peaks(args.peaks), dem, (lat, lon), eye, az, sky_ang, args.range) if want_peaks else [])]
    in_view = [(pk, rel) for pk, rel in in_view if abs(rel) <= args.hfov / 2]
    if args.peaks and args.hfov < 170:
        labels = [(f"{pk['name']} {pk['ele']} m", (rel + args.hfov / 2) / args.hfov * im.width, (args.pitch + vfov / 2 - pk["angle"]) / vfov * (height - 1))
                  for pk, rel in in_view]
        draw_peak_labels(ImageDraw.Draw(im), labels, size=max(13, im.width // 100))
    if args.roll:
        im = im.rotate(-args.roll, resample=Image.BICUBIC, fillcolor=(255, 255, 255))
    if args.photo and args.overlay:
        ph = Image.open(args.photo).convert("RGB")
        fpx = (ph.width / 2) / math.tan(math.radians(args.hfov / 2))
        cr, sr = math.cos(math.radians(args.roll)), math.sin(math.radians(args.roll))

        def proj(rel: float, el: float) -> tuple[float, float]:
            """Photo pixel of a direction (bearing offset, elevation) under the pinhole model, frame roll applied."""
            x = fpx * math.tan(math.radians(rel))
            y = -fpx * math.tan(math.radians(el - args.pitch)) / math.cos(math.radians(rel))
            return ph.width / 2 + x * cr - y * sr, ph.height / 2 + x * sr + y * cr

        pts = [proj(a - args.heading, e) for a, e in zip(az, sky_ang) if e > -89]
        ImageDraw.Draw(ph).line(pts, fill=(255, 40, 40), width=max(2, ph.width // 400))
        if args.peaks:
            labels = [(f"{pk['name']} {pk['dist_m'] / 1000:.1f} km", *proj(rel, pk["angle"])) for pk, rel in in_view]
            draw_peak_labels(ImageDraw.Draw(ph), labels, size=max(14, ph.width // 90))
        ov = args.out.with_name(args.out.stem + "_overlay" + args.out.suffix)
        ph.save(ov, quality=90)
        print(f"skyline overlaid on photo -> {ov} (if the red line doesn't match the photo's ridgeline, first adjust --heading/--pitch/--hfov/--roll, then suspect the camera position)")
    if args.photo:
        ph = Image.open(args.photo).convert("RGB")
        ph = ph.resize((args.width, int(ph.height * args.width / ph.width)))
        S = Image.new("RGB", (args.width, ph.height + im.height), "white")
        S.paste(ph, (0, 0))
        S.paste(im, (0, ph.height))
        im = S
    im.save(args.out)
    print(f"ground {ground:.0f} m, eye height {eye:.0f} m, skyline distance {np.nanmin(sky_dist) / 1000:.1f}–{np.nanmax(sky_dist) / 1000:.1f} km → {args.out}")
    if args.hfov < 170:
        print(f"PeakFinder, same camera for the eyes: {peakfinder_url(lat, lon, args.heading, args.hfov, ground)}")



def _neg_coords(argv: list[str]) -> list[str]:
    """argparse treats negative coordinates like -1.45,-48.5 as option names; prefixing a space makes them plain values (float ignores spaces). Needed for any photo in the southern or western hemisphere.
    fit's --line-win -27:-21,-3:3,18:27 is the same case (a string of numbers separated by commas or colons)."""
    return [" " + a if re.match(r"^-\d[\d.]*([,:]-?[\d.]+)+$", a) else a for a in argv]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)
    ap.add_argument("--cache", type=Path, default=Path(".geo-cache/dem"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("elev")
    e.add_argument("--at", help="lat,lon of one point")
    e.add_argument("--points", type=Path, help="{name:[lat,lon]} file (board.py / tiles.py / opendata.py form, or gsv.py area output): one row per point")
    e.add_argument("--zoom", type=int, default=13)
    e.add_argument("--out", type=Path, help="with --points: write the rows as JSON")
    e.add_argument("--allow-missing", action="store_true", help=MISSING_HELP)

    sl = sub.add_parser("slope", help="cross-slope at candidate points: elevation ±span/2 along a bearing → slope %%")
    sl.add_argument("--points", type=Path, required=True, help="{name:[lat,lon]} candidates")
    sl.add_argument("--bearing", type=float, required=True,
                    help="compass bearing the slope is measured along; for the slope across the frame use camera heading ± 90. Positive output = ground rises toward this bearing")
    sl.add_argument("--span", type=float, default=60, help="baseline length m (default 60); spans under ~3 DEM cells (z14 ≈ 10 m per cell) are smoothed by interpolation")
    sl.add_argument("--zoom", type=int, default=14, help="elevation tile zoom level (default 14, the finest with worldwide coverage)")
    sl.add_argument("--out", type=Path, help="write the rows as JSON")
    sl.add_argument("--allow-missing", action="store_true", help=MISSING_HELP)

    def common(sp):
        sp.add_argument("--at", required=True, help="candidate camera position lat,lon (WGS84)")
        g = sp.add_mutually_exclusive_group()
        g.add_argument("--height", type=float, default=1.6, help="height above ground m (for a shot from a building, use floor × 3)")
        g.add_argument("--alt", type=float, help="absolute altitude m (for aerial and mountaintop camera positions)")
        sp.add_argument("--heading", type=float, required=True, help="compass bearing of the frame center")
        sp.add_argument("--hfov", type=float, default=65, help="horizontal field of view; phone main camera about 65 landscape, about 50 portrait")
        sp.add_argument("--range", type=float, default=30000, help="how far to look (m)")
        sp.add_argument("--zoom", type=int, default=12, help="elevation tile zoom level, 12 ≈ 25–30 m per cell")
        sp.add_argument("--width", type=int, default=1400)
        sp.add_argument("--near", type=float, default=40, help="how near to start sampling, m; if spiky false ridgelines appear up close, raise to 150–300")
        sp.add_argument("--out", type=Path, required=True)
        sp.add_argument("--allow-missing", action="store_true", help=MISSING_HELP)

    v = sub.add_parser("view")
    common(v)
    v.add_argument("--pitch", type=float, default=0, help="pitch of the frame center, looking up is positive: a photo whose horizon sits below its middle was shot looking up (positive pitch)")
    v.add_argument("--vfov", type=float, help="vertical field of view; default derived from hfov for a 3:2 frame")
    v.add_argument("--photo", type=Path, help="scale the photo to the same width and place it above the render for comparison")
    v.add_argument("--roll", type=float, default=0, help="frame roll angle (clockwise positive), for downward shots from tall buildings and handheld tilt")
    v.add_argument("--overlay", action="store_true", help="also output a separate image: draw the synthetic skyline (red line) directly on the photo with the same heading/pitch/field of view")
    v.add_argument("--peaks", help="named peaks GeoJSON (osm.py geom '[\"natural\"=\"peak\"][\"name\"]' --bbox …): label the summits that stand on the skyline, on the render and on --overlay")

    pr = sub.add_parser("profile")
    common(pr)

    sc = sub.add_parser("scan", formatter_class=argparse.RawDescriptionHelpFormatter, description="""\
Along linear infrastructure, compute the 360° horizon point by point, keep the points that are "flat nearby + a mountain + the mountain right next to a stretch of flat horizon", then cluster them.

Use when: the frame shows only one railway/road/power line and a mountain you can't recognize, with no text at all. First
get the lines with `osm.py geom '<filter>' --bbox <large region> --out lines.geojson`, then run this to cut the large region down to a few hundred patches;
the selected clusters go into `terrain.py fit` for skyline scoring. Method and the reasoning behind the values: references/corridors.md 4.3.

Set thresholds at about half of the photo estimate: one z10 cell is ~150 m, peaks get smoothed away, and the computed elevation angles come out smaller than the real ones.
In a real case, a threshold set at the photo's estimated 6° left not a single point near the ground truth; it only got in after loosening to 4.5° — better too many than a miss; leave the count to the next ranking step.

Output JSON (--out):
  {"params": {...all thresholds used in this run, recorded as is...},
   "n_samples": number of sample points, "n_hits": number of hit points, "n_clusters": number of clusters,
   "hits":     [{"lat","lon","h0": ground elevation at the point m, "max_ang": highest horizon elevation angle °,
                 "az": that bearing °, "relief": max relative height difference at that bearing m, "flat_run_deg": length of flat horizon right next to the mountain °,
                 "name","hs"(highspeed),"elec"(electrified),"id": OSM tags of the line}, ...],
   "clusters": [{...same as above..., "n": number of points in the cluster}, ...]}   # sorted by max_ang from largest to smallest; the cluster representative is the steepest point
--clusters-out writes a separate JSON with only the cluster list (exactly the clusters field).""")
    sc.add_argument("--lines", required=True, help="GeoJSON from osm.py geom: LineString, MultiLineString and the rings of polygons (lake shores, coasts) are all read as lines")
    sc.add_argument("--out", required=True, help="output JSON")
    sc.add_argument("--clusters-out", help="also write a separate JSON with only the cluster list")
    sc.add_argument("--bbox", help="only scan sample points inside this range s,w,n,e (for validation and chunked runs; omitted = the whole geojson)")
    sc.add_argument("--step", type=float, default=400, help="take one point every this many meters along the line (default 400; anything in 300–500 works)")
    sc.add_argument("--zoom", type=int, default=10, help="elevation tile zoom level (default 10, one cell ~150 m, enough for mountain outlines)")
    sc.add_argument("--near-flat", type=float, default=40,
                    help="nearby relief limit m: if the height difference within --near-radius of the point exceeds it, the point is not flat and is dropped (default 40; the loosened version used 60)")
    sc.add_argument("--near-radius", type=float, default=1200, help="radius m for judging whether the nearby ground is flat (default 1200)")
    sc.add_argument("--near-step", type=float, default=300, help="nearby sampling interval m (default 300)")
    sc.add_argument("--min-peak", type=float, default=4.5,
                    help="mountain: horizon elevation angle of at least this many degrees (default 4.5, the value after loosening in a real case; the original strict value 6, estimated from that photo, filtered out all of the ground truth)")
    sc.add_argument("--max-low", type=float, default=1.2,
                    help="flat: a horizon elevation angle below this many degrees counts as flat horizon (default 1.2; the loosened version used 1.5)")
    sc.add_argument("--flat-run", type=float, default=20,
                    help="the stretch of flat horizon right next to the mountain must be at least this many degrees (default 20; original strict value 30)")
    sc.add_argument("--min-low-deg", type=float,
                    help="total flat horizon around the full circle of at least this many degrees (default same as --flat-run)")
    sc.add_argument("--flat-run-cap", type=float, default=100, help="count flat-horizon length at most this many degrees to one side (default 100)")
    sc.add_argument("--eye", type=float, default=1.5, help="eye height above ground m (default 1.5)")
    sc.add_argument("--az-step", type=float, default=5, help="bearing step ° (default 5, must divide 360 evenly)")
    sc.add_argument("--dist", default="1500,2000,2500,3000,3500,4000,5000,6000,7000,8000,9000",
                    help="distance steps measured outward along each bearing m, comma-separated (default 1.5–9 km)")
    sc.add_argument("--skip-tag", action="append",
                    help="skip lines carrying this tag, key=value, repeatable (default electrified=no; --skip-tag none means skip none)")
    sc.add_argument("--cluster-km", type=float, default=3.5, help="clustering radius km (default 3.5)")
    sc.add_argument("--threads", type=int, default=8, help="tile download concurrency (default 8; failed tiles are retried with backoff)")
    sc.add_argument("--allow-missing", action="store_true", help=MISSING_HELP)
    sc.add_argument("--max-tiles", type=int, default=4000,
                    help="limit on the number of tiles to download; exits immediately if exceeded (default 4000). Memory is set by the bounding rectangle of these tiles, "
                         "which can be several times the tile count when the line network is sparse; the actual usage is printed before the mosaic is built")

    rg = sub.add_parser("ridge", formatter_class=argparse.RawDescriptionHelpFormatter, description="""\
Photo ridgeline sampling: in --x0..--x1, every --step columns, top to bottom, find the sky→mountain brightness jump (the k rows above are brighter than the k rows below by --drop or more,
and the --hold rows further down are still dark), and take the maximum-gradient row as the ridge pixel. The output is for terrain.py fit.

--flat gives the column range where "the frame shows flat horizon" (the stretch on the left or right with no distant mountains); fit uses it to penalize "a mountain blocking where it should be flat".
Without --hrow, the horizon row is the median of the sky→ground jump rows in the --flat columns; without --flat, it is the frame midline.
Note that this estimate lands on top of things like distant treetops and bridge decks, 10–30 px above the true 0° horizon (on that photo: auto estimate 909,
hand-set 935); fit's horizon offset cc only absorbs ±0.7° (about ±16 px at f≈1300 px), so when there are tall objects in the distance, give --hrow by hand.
Focal length: --f0 > EXIF 35mm-equivalent focal length > assumed from --f35 (default 26 mm, phone main camera), converted to pixels via the diagonal; the source is written to f0_source.
An assumed focal is only the base: fit then searches 13–135 mm equivalent by default, so a zoomed shot is not forced into a main-camera fit.

--points replaces detection with hand-picked skyline points (cloud on the peaks, snow against a pale sky).
Two-layer photos (a lower near range in front of a higher far range, the near range ending mid-frame so the far range's foot shows):
  --near x,y;...        points on the near range's top edge; fit scores them against the highest terrain within a near distance
  --near-clear x0:x1@ROW columns past the near range's end, where nothing near may rise above ROW (the far range's foot / plain)

Output JSON (--out):
  {"photo": photo path (recorded exactly as given on the command line; if fit can't find it, it retries relative to the directory of ridge.json),
   "image_size": [width, height], "cx": center column,
   "ridge": [[x, y], ...],           # ridge pixel points, x column y row (y is the mountain's first row)
   "missing_cols": [x, ...],         # columns where no jump was found
   "ridge_source": "detected"|"points",
   "near": [[x, y], ...], "near_clear": [[x0, x1, row], ...],   # two-layer input, empty when not given
   "flat": [x0, x1] | null, "flat_rows": [jump row of each column in that range],
   "hrow": horizon row, "hrow_source": "arg"|"flat"|"center",
   "f0": focal length px, "f0_source": "arg"|"exif"|"assumed", "f35_equiv": 35mm-equivalent focal length,
   "params": {...parameters used in this run...}}
--png also outputs a check image: yellow dots = ridge points, red vertical lines = columns not found, blue line = hrow, cyan line = flat-horizon column range,
orange dots / lines = near points / near-clear rows. Look at the image before going to fit.""")
    rg.add_argument("photo", type=Path, help="photo")
    rg.add_argument("--x0", type=int, default=0, help="ridge start column (inclusive, default 0)")
    rg.add_argument("--x1", type=int, help="ridge end column (inclusive, default the last column)")
    rg.add_argument("--step", type=int, default=20, help="take one point every this many columns (default 20)")
    rg.add_argument("--flat", help="flat-horizon column range x0:x1 (e.g. 0:280); omit if there is none")
    rg.add_argument("--hrow", type=float, help="row of the horizon; if omitted, estimated from the --flat columns, and failing that, the frame midline")
    rg.add_argument("--f0", type=float, help="focal length px; if given, EXIF is not read")
    rg.add_argument("--f35", type=float, default=26.0, help="assumed 35mm-equivalent focal length mm when there is no EXIF (default 26, phone main camera; 2x telephoto 48–52)")
    rg.add_argument("--ymin", type=int, help="only search below this row (default 0; for clouds in the sky or foreground occlusion)")
    rg.add_argument("--ymax", type=int, help="only search above this row (default the frame bottom)")
    rg.add_argument("--drop", type=float, default=30, help="minimum amount the sky must be brighter than the mountain (0–255 brightness, default 30; in heavy haze lower to 15–20)")
    rg.add_argument("--k", type=int, default=4, help="rows taken above and below each when comparing brightness (default 4)")
    rg.add_argument("--hold", type=int, default=12, help="rows that must stay dark below the jump for it to count as mountain (default 12, used to skip wires and antennas)")
    rg.add_argument("--halfw", type=int, default=1, help="also average this many columns on each side of each column (default 1, i.e. 3 columns)")
    rg.add_argument("--points", help="hand-picked skyline points x,y;x,y;... (or a .json of [[x,y],...]) used instead of detection, "
                    "when cloud, haze or snow against a pale sky breaks the brightness jump; --x0/--x1 are then ignored")
    rg.add_argument("--near", help="two-layer photos: points x,y;x,y;... on the top edge of the NEAR range where it stands in front of a higher far range "
                    "(or a .json of [[x,y],...]); fit then scores the near layer too, see geometry.md 7.4")
    rg.add_argument("--near-clear", action="append",
                    help="two-layer photos: x0:x1@row = in these columns the near layer ends and the far range's foot or plain shows, "
                         "so nothing within the near distance may rise above this row; repeatable")
    rg.add_argument("--out", required=True, help="output ridge.json")
    rg.add_argument("--png", help="check image path")

    sh = sub.add_parser("shade", formatter_class=argparse.RawDescriptionHelpFormatter, description="""\
Where the shadows lie at a place and time (the local counterpart of shademap.app; sun.py pos is the suncalc.org counterpart).
Terrain shadows come from the elevation tiles (march toward the sun from every pixel; any terrain above the ray shades it);
building shadows from an OSM footprint GeoJSON (osm.py geom '["building"]' --bbox …): height tag, else building:levels × --level-height, else --default-height.

  --time    render the moment: --out shade.png (over --map imagery from tiles.py fetch, else a hillshade square of --size px, --radius m around --at);
            --check lat,lon[:label] prints LIT / SHADOW per point (a slope, a wall, a beach seen lit or dark in the photo).
  --date / --dates   the inverse: every --minutes, which times leave all --lit points lit and all --shaded points in shadow
            (terrain or building). With --dates (step --date-step days) the pattern's windows per day; the same pattern repeats on
            two date sets a year, say so. Nothing given: the centre point's own daylight windows.
Use when the photo shows which faces or slopes are lit and which are dark, or a mountain's shadow on a valley, lake or town:
with the place known it brackets the time of day and the season; with the time known it tests a candidate position.
A 10 m DEM cell softens shadow edges by a few minutes; a 30 m cell by 5–10 minutes near the edge: give --lit / --shaded points well inside their state.
Output JSON (--json): sun position, per-point states, and "sweep": {days: [{date, spans: [[HH:MM, HH:MM], …]}]}.""")
    sh.add_argument("--at", required=True, help="centre lat,lon (WGS84); the sun position is computed here")
    sh.add_argument("--time", help="local date-time YYYY-MM-DDTHH:MM (in --tz) to render / check")
    sh.add_argument("--date", help="sweep this day (YYYY-MM-DD)")
    sh.add_argument("--dates", help="sweep a date range A:B (YYYY-MM-DD:YYYY-MM-DD), one day every --date-step")
    sh.add_argument("--date-step", type=int, default=7, help="days between swept dates in --dates (default 7)")
    sh.add_argument("--minutes", type=int, default=5, help="sweep step in minutes (default 5)")
    sh.add_argument("--tz", help="IANA time zone of --time / --date (default UTC)")
    sh.add_argument("--radius", type=float, default=2500, help="half-size of the rendered square m (default 2500; ignored with --map)")
    sh.add_argument("--size", type=int, default=900, help="rendered square px without --map (default 900)")
    sh.add_argument("--zoom", type=int, default=13, help="elevation tile zoom (default 13, ~15 m per cell at mid latitudes; 14 for a town, 12 for a wide valley)")
    sh.add_argument("--step", type=float, default=30, help="march step toward the sun m (default 30)")
    sh.add_argument("--reach", type=float, default=8000, help="how far a mountain may stand to cast a shadow m (default 8000; 20000 for a low sun under high ranges)")
    sh.add_argument("--map", help="tiles.py fetch mosaic (its .json must sit beside it): render on it instead of a hillshade")
    sh.add_argument("--buildings", help="building footprint GeoJSON (osm.py geom '[\"building\"]' output) for building shadows")
    sh.add_argument("--default-height", type=float, default=8, help="building height m when OSM has no height/levels (default 8)")
    sh.add_argument("--level-height", type=float, default=3, help="metres per building:levels (default 3)")
    sh.add_argument("--check", action="append", help="lat,lon[:label], repeatable: report LIT / SHADOW at --time")
    sh.add_argument("--lit", action="append", help="lat,lon[:label], repeatable: must be lit in the sweep")
    sh.add_argument("--shaded", action="append", help="lat,lon[:label], repeatable: must be in shadow in the sweep")
    sh.add_argument("--out", type=Path, help="rendered PNG (with --time)")
    sh.add_argument("--json", type=Path, help="write the states and sweep as JSON")
    sh.add_argument("--allow-missing", action="store_true", help=MISSING_HELP)

    ft = sub.add_parser("fit", formatter_class=argparse.RawDescriptionHelpFormatter, description="""\
Batch skyline scoring: in each candidate cluster, lay a camera-position grid (one every --grid meters within --radius), compute the 360° horizon at each camera position,
convert ridge.json's ridge points to (bearing offset, elevation angle), and compare against all headings × --focal-scales at once:
  rms     = RMS of the ridge elevation-angle residuals (the residual median serves as horizon offset cc, clamped to ±--cc-max)
  flatpen = mean of max(0, horizon elevation angle − cc − --flat-clear) over the flat-horizon columns
  score   = rms + --flat-w × flatpen (+ --near-clear-w × nclearpen for two-layer ridge.json)
  rms_px  = rms converted to pixels (rms × f × π/180), for judging whether candidates can be separated (on an f35 ladder the score itself is compared in pixels, --focal-metric): when the top few all come out about as large as
            the error of the ridge sampling itself (a few to a dozen or so pixels), the skyline can't separate them; you need a second constraint
Camera positions first pass two filters: height difference within --cam-flat-radius ≤ --cam-flat (the camera stands on flat ground in the frame),
highest horizon elevation angle ≥ --min-peak (there are mountains to compare).
Lake shore, coast, riverbank (the camera stands at the water's edge with a slope right behind it): the flat filter rejects the true position, and
with it off the grid climbs the slope and scores cameras 100 m above the water. Use --cam-level N instead: only positions whose ground elevation is
within N m of the cluster point's (the scan hit's h0, or the --at point) are scored; --cam-flat 10000 turns the flat filter off.
With --line (GeoJSON from osm.py geom), one more independent constraint is added: for each heading, the nearest distance dL/dC/dR of infrastructure sample points inside the frame's left/center/right bearing windows
(--line-win); distances outside the --line-dist intervals are penalized by meters/--line-scale (--line-order can also penalize the order),
total = score + --line-w × line_pen; headings where any of the three windows has no infrastructure don't count. Without --line, total = score.

Focal: --focal-scales auto (default) tries ×0.9/1/1.12 around an EXIF or --f0 focal, and a 13–135 mm equivalent ladder when ridge.json's focal was
assumed (no EXIF). If the leading results sit on an end of the ladder, fit prints a WARNING and writes focal_edge: rerun with --f35-range widened past
that end before trusting ranking, heading or focal. Running to the new end again means the focal is absorbing another error (bad ridge points, hrow, wrong place).
Two-layer (ridge.json has near / near_clear): the near layer = highest terrain within D1 m, D1 tried from --near-dist; near points share rms, cc and roll
with the far ridge. A far-only fit of a two-layer photo can match the far outline at a wrong heading and focal.
--perp-line keeps headings within --perp-tol of perpendicular to the nearest line (wires crossing the frame almost level).
Distant ranges: --range (default 15 km) must reach the far ridge; for ranges 20–40 km away use --range 45000 and lower --min-peak.

The coarse-search defaults are the ones from the real case: 2 km / 250 m / z11 / 0.5°; for fine search switch to --radius 800 --grid 100 --zoom 13 --az-step 0.25.
The skyline only gives one sight line (moving a few hundred meters forward or back along it doesn't change the outline); always look at the --sheet overlay for the top few, then pin the point with a second constraint.
After the ranking, fit prints a ready `terrain.py view … --overlay` command for the lead camera (heading, hfov, pitch, roll from the fit): run it to see that skyline on the full photo.

Two things not to treat as conclusions:
  1. The output H and f have a systematic bias, which comes from hrow in ridge.json. In the same coarse search, hand-set hrow 935 gave H 80.5 / f 1436,
     and the auto-estimated 909 gave H 79.0 / f 1282 — a difference of 1.5° and 12% in focal length (cc can only absorb ±--cc-max). Cluster ranking isn't affected
     (both runs ranked the ground-truth cluster 1st), but before you argue from H/f, get hrow right first (check the blue line on ridge --png).
  2. Fine search (z13) is not guaranteed to be more accurate than coarse search. In tests on the same pipeline, fine search actually ended up farther from the ground truth than coarse search:
     the z13 flat filter (--cam-flat / --cam-flat-radius) filters out the points near the ground truth, and the skyline only gives one sight line anyway.
     In this pipeline, fine search's job is to give geo.py spacing a reliable --center, not to bring the error down by itself.
Method in references/geometry.md 7.4, corridors.md 4.3.

Output JSON (--out):
  {"params": {...all parameters used in this run, including f0/hrow/cx/hfov under photo...},
   "n_clusters", "n_cams": number of camera positions scored, "n_skipped": {"not_flat","off_level","no_peak","no_line","dup","missing_dem","no_perp_line"},
   "status": "running" (checkpoint while scoring) | "budget" (stopped at --budget-min) | "done",
   "pid", "updated_at": the process that wrote the file and when (status running whose pid no longer runs = a dead run),
   "partial": true while clusters are left, "unscored_clusters": their --hits indices (continue them with --select and a new --out), "elapsed_min",
   "focal_edge": null | {"top1": "long"|"short"|null, "long", "short", "of": leading results counted, "range_f35": [lo, hi] mm},
   "dem_failed_clusters": hit indices whose elevation tiles failed to download (not scored),
   "clusters": [{"hit": the cluster's index in --hits, "name", "hit_ll": [lat,lon], "n", "max_ang", "n_cams", "rank",
                 "best": <camera record>}, ...],                      # best camera position of each cluster, ascending by total
   "cams":     [<camera record>, ...]}                                 # all camera positions ascending by total, at most --keep entries
  camera record: {"hit","name","hit_ll", "cam": [lat,lon], "d": distance from cluster center m, "brg": bearing cluster center→camera position °,
            "g": ground elevation m, "H": heading °, "fs": focal scale, "f": focal length px, "f35": 35mm-equivalent mm, "cc": horizon offset °, "roll",
            "rms", "rms_px", "flatpen", "score", [two-layer: "D1" m, "rms_near_px", "nclearpen"], [--perp-line: "line_brg"],
            [with --line: "dL","dC","dR" m, "line_pen"], "total"}
--sheet: with multiple clusters, draws the top --top of the per-cluster best camera positions; with a single cluster/--at, draws the top --top camera positions; red line = synthetic skyline, orange line = synthetic near layer, yellow dots = photo ridge points,
cyan dots = photo near points.""")
    src = ft.add_mutually_exclusive_group(required=True)
    src.add_argument("--hits", help="scan output JSON (uses the clusters field) or a cluster-list JSON")
    src.add_argument("--at", help="instead of --hits, give one center lat,lon directly (for fine search)")
    ft.add_argument("--select", help="only run the clusters at these indices in --hits, comma-separated (for validation and chunked runs)")
    ft.add_argument("--ridge", type=Path, required=True, help="output of terrain.py ridge")
    ft.add_argument("--out", required=True, help="output JSON")
    ft.add_argument("--radius", type=float, default=2000, help="camera-position grid radius per cluster m (default 2000; fine search 800)")
    ft.add_argument("--grid", type=float, default=250, help="camera-position grid spacing m (default 250; fine search 100)")
    ft.add_argument("--zoom", type=int, default=11, help="elevation tile zoom level (default 11, one cell ~70 m; fine search 13)")
    ft.add_argument("--focal-scales", default="auto",
                    help="focal length scales of ridge.json's f0, comma-separated. Default auto: EXIF or --f0 focal → 0.9,1,1.12; "
                         "no EXIF → a ladder over --f35-range (13–135 mm equivalent, ~18%% steps), because a guessed main camera "
                         "misses zoomed shots, which are common for distant mountains")
    ft.add_argument("--f35-range", help="lo:hi 35mm-equivalent focal range for the ladder, e.g. 40:270 after the best focal hit the long end; "
                    "overrides auto even with EXIF")
    ft.add_argument("--focal-metric", choices=["auto", "deg", "px"], default="auto",
                    help="unit in which scores are compared across focal lengths: deg or px (score × focal scale). "
                         "Default auto: px for an f35 ladder, deg for ×0.9–1.12; degrees favour the longest focal on a wide ladder")
    ft.add_argument("--near-dist", default="3000,5000,8000,12000",
                    help="two-layer only: candidate distances m out to which the near layer reaches, comma-separated (default 3000,5000,8000,12000)")
    ft.add_argument("--near-clear-w", type=float, default=1.5, help="two-layer only: weight of nclearpen (default 1.5)")
    ft.add_argument("--perp-line", help="linear infrastructure GeoJSON (osm.py geom); keep only headings near perpendicular to the nearest line, "
                    "for wires crossing the frame almost level overhead")
    ft.add_argument("--perp-tol", type=float, default=35, help="with --perp-line: allowed deviation ° from perpendicular (default 35)")
    ft.add_argument("--perp-reach", type=float, default=1500, help="with --perp-line: camera positions farther than this from any line m are skipped (default 1500)")
    ft.add_argument("--az-step", type=float, default=0.5, help="heading/bearing step ° (default 0.5; fine search 0.25; must divide 360 evenly)")
    ft.add_argument("--near", type=float, default=150, help="how near the sight line starts sampling m (default 150)")
    ft.add_argument("--range", type=float, default=15000, help="how far the sight line looks m (default 15000)")
    ft.add_argument("--nsamp", type=int, default=260, help="samples per sight line, dense near and sparse far (default 260; fine search 400)")
    ft.add_argument("--eye", type=float, default=1.6, help="eye height above ground m (default 1.6)")
    ft.add_argument("--cam-flat", type=float, default=8, help="height difference limit around the camera position m; above it, it isn't a flat-ground camera position (default 8; fine search has used 6)")
    ft.add_argument("--cam-flat-radius", type=float, default=300, help="radius m for judging whether the camera position is flat (default 300; fine search has used 200)")
    ft.add_argument("--cam-level", type=float, default=None, metavar="M", help="only camera positions whose ground elevation is within M m of the cluster point's (scan hit h0 or the --at point): lake shore, coast, riverbank; pair with --cam-flat 10000 (default off)")
    ft.add_argument("--min-peak", type=float, default=None,
                    help="minimum highest horizon elevation angle in degrees for a camera position to be scored (default: scan's --min-peak from --hits, else 6)")
    ft.add_argument("--cc-max", type=float, default=0.7, help="limit of horizon offset cc ° (default 0.7, i.e. hrow may be off by a dozen or so pixels)")
    ft.add_argument("--roll-max", type=float, default=1.0,
                    help="roll angle limit ° (default 1.0, the usual range of handheld tilt; 0 = don't solve roll)")
    ft.add_argument("--flat-clear", type=float, default=1.0, help="on the flat-horizon columns, horizon up to this many degrees above cc is not penalized (default 1.0)")
    ft.add_argument("--flat-w", type=float, default=1.5, help="flatpen weight (default 1.5)")
    ft.add_argument("--flat-step", type=float, default=20, help="take one column every this many pixels in the flat-horizon column range (default 20)")
    ft.add_argument("--line", help="linear infrastructure GeoJSON (output of osm.py geom); if given, adds the left/center/right distance constraint")
    ft.add_argument("--line-dist", help="three distance intervals left:center:right m, e.g. 350-750:550-900:800-1700 (required with --line)")
    ft.add_argument("--line-win", default="-27:-21,-3:3,18:27",
                    help="three bearing windows left/center/right, offset angle ° from the frame center (default -27:-21,-3:3,18:27, set for a 53° horizontal field of view; "
                         "writing --line-win=-27:... or putting the value right after both work)")
    ft.add_argument("--line-scale", default="200,200,300", help="penalty scale m of each of the three windows (default 200,200,300: 200 m out of bounds = penalty 1)")
    ft.add_argument("--line-order", choices=["none", "asc", "desc"], default="none",
                    help="order constraint on the three distances: asc = left<center<right (the infrastructure crosses the frame diagonally from near on the left to far on the right), desc the reverse; penalty 1 if not met (default none)")
    ft.add_argument("--line-w", type=float, default=0.3, help="line_pen weight (default 0.3)")
    ft.add_argument("--line-min", type=float, default=150, help="infrastructure points closer to the camera position than this distance don't count (default 150)")
    ft.add_argument("--line-sample", type=float, default=50, help="take one point every this many meters along the infrastructure line (default 50)")
    ft.add_argument("--line-reach", type=float, default=3000, help="only consider infrastructure points within this distance of the camera position m (default 3000)")
    ft.add_argument("--skip-tag", action="append", help="in --line, skip lines carrying this tag, key=value, repeatable (default electrified=no; none means skip none)")
    ft.add_argument("--budget-min", type=float, default=20, help="stop scoring new clusters after this many minutes and write the partial ranking (default 20; 0 = no limit); "
                    "the clusters left are listed in fit.json (unscored_clusters) and in the --select command printed at the stop. "
                    "While scoring, fit.json is rewritten at most every 30 s and after the last cluster (status running, with pid and updated_at); "
                    "status running whose pid no longer runs is a dead run: continue its unscored_clusters with --select and a new --out. "
                    "While that pid runs, do not start a second fit")
    ft.add_argument("--tie", type=float, default=0.03, help="position ambiguity: camera positions whose total lies within this of a cluster's best are reported as one stretch (span and bearing; default 0.03)")
    ft.add_argument("--top", type=int, default=20, help="how many top entries to print in the terminal and draw in --sheet (default 20)")
    ft.add_argument("--keep", type=int, default=5000, help="maximum number of entries written to the cams list (default 5000)")
    ft.add_argument("--sheet", help="overlay sheet jpg of the top --top; also writes <sheet>_skyline.jpg/.json, the top 3 stacked full-width over the photo (the live page's Skyline card)")
    ft.add_argument("--peaks", help="named peaks GeoJSON (osm.py geom '[\"natural\"=\"peak\"][\"name\"]' --bbox …): summit names on the stacked skyline image and in its .json")
    ft.add_argument("--overlay", "--photo", dest="photo", help="photo for the overlay; if omitted, uses the path recorded in ridge.json")
    ft.add_argument("--sheet-cols", type=int, default=4, help="overlay images per row (default 4)")
    ft.add_argument("--sheet-width", type=int, default=360, help="width of each overlay image px (default 360)")
    ft.add_argument("--allow-missing", action="store_true", help=MISSING_HELP)

    args = ap.parse_args(_neg_coords(sys.argv[1:]))
    {"scan": _cmd_scan, "ridge": _cmd_ridge, "fit": _cmd_fit, "shade": _cmd_shade, "elev": _cmd_elev, "slope": _cmd_slope,
     "view": _cmd_view, "profile": _cmd_view}[args.cmd](args)


if __name__ == "__main__":
    # Chinese-locale Windows outputs GBK by default: it crashes on m² or ñ, and any Chinese the agent reads comes out garbled
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
