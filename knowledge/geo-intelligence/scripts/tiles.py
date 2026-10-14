#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""Download satellite tiles, stitch them into one large image (mosaic), and mark points on it.

A .json with the same name is written next to the mosaic (zoom level, top-left tile index, center point);
evidence.py and the mark subcommand use it to convert lat/lon to image pixels.

Google satellite imagery is the default (WGS84, the same coordinate system as GPS, no offset correction needed in China).

Examples:
  tiles.py fetch 22.6050,114.0540 --zoom 18 --radius 4 --out area.jpg
  tiles.py mark area.jpg --points panos.json --out area_panos.jpg --label
  tiles.py mark area.jpg --points cands.json --geojson power.geojson --geojson rail.geojson \
           --sector 22.6045,114.0520,265,40,3000 --out area_lines.jpg       # overlay line features + camera-position view sector
  tiles.py sheet --points cands.json --zoom 18 --out cands_sheet.jpg     # one centered thumbnail per candidate point, numbered
  tiles.py px2ll area.jpg --px 812,440 --px 300,95                      # mosaic pixels → lat/lon (for a cropped image add --crop x0,y0 --scale s)
  tiles.py sheet --grid <s,w,n,e> --zoom 17 --size 320 --cols 5 --out town.jpg   # tile a whole urban area with a grid and look cell by cell (find running tracks, factory buildings)
  geodata.py towns PE --admin1 Cusco --json > towns.json
  tiles.py sheet --points towns.json --zoom 15 --size 640 --cols 3 --out fabric.jpg     # city fabric: candidate towns side by side, one scale
  tiles.py fetch 34.0331,-5.0003 --zoom 18 --source google-hybrid --out a.jpg        # satellite with street names (also google-map, esri-street)
  tiles.py wayback 34.0331,-5.0003 --zoom 17 --out wb.jpg                       # every archived look since 2014, capture date at the point
  tiles.py sheet --points p.json --zoom 15 --source s2:2018 --out s2.jpg           # Sentinel-2 cloudless mosaic of one year (10 m)
"""
from __future__ import annotations

import argparse
from geolib.cli import font, neg_coords as _neg_coords
from geolib.net import curl_args, fetch_bytes, PROXY_HELP
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import geo  # noqa: E402

SOURCES = {
    "google": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",                 # satellite
    "google-hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",          # satellite + street names
    "google-map": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",             # road map with labels
    "esri": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}?blankTile=false",
    "esri-street": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}?blankTile=false",
    "bing": "https://ecn.t{s}.tiles.virtualearth.net/tiles/a{q}.jpeg?g=14536",       # Bing aerial (quadkey)
}
SOURCE_HELP = ("google | google-hybrid | google-map | esri | esri-street | bing | wayback:<release id or YYYY[-MM]> "
               "(Esri World Imagery Wayback, archived releases since 2014) | s2:<year> (EOX Sentinel-2 cloudless, 10 m, 2018+) | "
               "gibs:<YYYY-MM-DD>[:<layer>] (NASA GIBS near-real-time daily imagery, one pass that day; match clouds/snow/smoke; "
               "zoom ≤9, default layer MODIS_Terra_CorrectedReflectance_TrueColor, also VIIRS_SNPP_/VIIRS_NOAA20_/MODIS_Aqua_CorrectedReflectance_TrueColor)")
WAYBACK_CONFIG = "https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json"


def _quadkey(x: int, y: int, z: int) -> str:
    q = ""
    for i in range(z, 0, -1):
        m = 1 << (i - 1)
        q += str((1 if x & m else 0) + (2 if y & m else 0))
    return q


def wayback_releases(proxy: str | None = None) -> list[dict]:
    """Esri World Imagery Wayback releases, oldest first: [{id, date, url, metadataLayerUrl}] (config cached for a week)."""
    import time as _t
    from geolib.paths import cache_root
    cache = cache_root() / "wayback.json"
    if not cache.exists() or _t.time() - cache.stat().st_mtime > 7 * 86400:
        cache.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-q", "-sS", "-L", "-m", "60", "-o", str(cache), WAYBACK_CONFIG] + curl_args(proxy), check=False)
    d = json.loads(cache.read_text(encoding="utf-8"))
    out = []
    for rid, v in d.items():
        m = re.search(r"(\d{4}-\d{2}-\d{2})", v.get("itemTitle", ""))
        out.append({"id": int(rid), "date": m.group(1) if m else "", "url": v["itemURL"],
                    "metadataLayerUrl": v.get("metadataLayerUrl", "")})
    return sorted(out, key=lambda r: r["date"])


def _wayback_pick(spec: str, proxy: str | None) -> dict:
    """A release by id, or by date (YYYY, YYYY-MM or YYYY-MM-DD): the last release published on or before it."""
    rel = wayback_releases(proxy)
    if re.fullmatch(r"\d+", spec) and not re.fullmatch(r"(19|20)\d\d", spec):
        hit = [r for r in rel if r["id"] == int(spec)]
        if hit:
            return hit[0]
    before = [r for r in rel if r["date"] <= spec + "-99"]
    return before[-1] if before else rel[0]


def _identify(meta_url: str, lat: float, lon: float, proxy: str | None, cache: Path) -> list[dict]:
    """Wayback metadata at the point, every resolution layer at once (the zoom is applied by _capture).
    Cached per metadata service and point; a transport error or an error reply raises and is not cached."""
    path = cache / f"wayback-meta_{hashlib.sha1(f'{meta_url}|{lat:.6f}|{lon:.6f}'.encode()).hexdigest()[:16]}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))["results"]
    except (OSError, ValueError, KeyError):
        pass                                                  # not cached yet, or a torn write: ask again
    pad = 0.001                                               # mapExtent/imageDisplay are required; tolerance 0 = the point only
    q = urlencode({"f": "json", "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "sr": 4326, "layers": "all",
                   "tolerance": 0, "mapExtent": f"{lon - pad},{lat - pad},{lon + pad},{lat + pad}",
                   "imageDisplay": "100,100,96", "returnGeometry": "false"})
    d = json.loads(fetch_bytes(f"{meta_url}/identify?{q}", proxy, timeout=20))
    if not isinstance(d.get("results"), list):
        raise RuntimeError(f"metadata service: {(d.get('error') or {}).get('message', 'no results in the reply')}")
    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d["results"]


def _capture(results: list[dict], zoom: int) -> dict:
    """Capture date of the imagery drawn at `zoom`: the layer whose MinMapLevel..MaxMapLevel spans the zoom, else the one with
    the highest MaxMapLevel below it (its tiles are upsampled). SRC_DATE is YYYYMMDD; 'Null', empty or missing = unknown
    (SRC_DATE2 repeats it in another format and is ignored)."""
    spans, below = [], []
    for r in results:
        a = r.get("attributes") or {}
        try:
            lo, hi = int(a["MinMapLevel"]), int(a["MaxMapLevel"])
        except (KeyError, TypeError, ValueError):
            continue
        if lo <= zoom <= hi:
            spans.append(a)
        elif hi < zoom:
            below.append((hi, a))
    a = spans[0] if spans else max(below, key=lambda x: x[0])[1] if below else {}
    date = str(a.get("SRC_DATE") or "")
    try:
        captured = datetime.strptime(date, "%Y%m%d").strftime("%Y-%m-%d") if re.fullmatch(r"\d{8}", date) else None
    except ValueError:
        captured = None
    try:
        res = float(a["SRC_RES"])
    except (KeyError, TypeError, ValueError):
        res = None
    src = a.get("SRC_DESC")
    return {"captured": captured, "capture_source": src if src not in (None, "", "Null") else None, "capture_res_m": res}


def capture_at(release: dict, lat: float, lon: float, zoom: int, proxy: str | None, cache: Path) -> dict:
    """_capture for one Wayback release at the point; a failed lookup comes back as capture_error, never raised."""
    try:
        if not release.get("metadataLayerUrl"):
            raise RuntimeError("no metadata layer for this release in the Wayback config")
        return _capture(_identify(release["metadataLayerUrl"], lat, lon, proxy, cache), zoom)
    except Exception as e:  # noqa: BLE001 - one failed lookup must not abort the contact sheet
        return {"captured": None, "capture_source": None, "capture_res_m": None, "capture_error": str(e)[:160]}


def _capture_text(cap: dict, published: str) -> str:
    """One line per Wayback version: the capture date at the point, else the publication date as an upper bound."""
    res = cap.get("capture_res_m")
    what = ", ".join(x for x in (cap.get("capture_source"), f"{res:g} m" if res else "") if x)
    if cap.get("captured"):
        return f"captured {cap['captured']} at the point (published {published})" + (f", {what}" if what else "")
    why = what or (f"metadata: {cap['capture_error']}" if cap.get("capture_error") else "")
    return f"capture unknown; published {published} = upper bound" + (f" ({why})" if why else "")


def tile_url(source: str, x: int, y: int, z: int, proxy: str | None = None) -> str:
    if source.startswith("wayback:"):
        r = _wayback_pick(source.split(":", 1)[1], proxy)
        return r["url"].replace("{level}", str(z)).replace("{row}", str(y)).replace("{col}", str(x))
    if source.startswith("s2:"):
        year = source.split(":", 1)[1]
        return f"https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-{year}_3857/default/g/{z}/{y}/{x}.jpg"
    if source.startswith("gibs:"):
        parts = source.split(":", 2)[1:]            # gibs:<date>[:<layer>]
        date = parts[0]
        layer = parts[1] if len(parts) > 1 and parts[1] else "MODIS_Terra_CorrectedReflectance_TrueColor"
        return (f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/{date}/"
                f"GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg")
    if source == "bing":
        return SOURCES["bing"].format(s=(x + y) % 4, q=_quadkey(x, y, z))
    if source not in SOURCES:
        raise SystemExit(f"unknown tile source {source!r}; use {SOURCE_HELP}")
    return SOURCES[source].format(x=x, y=y, z=z)


def _src_tag(source: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", source)


def load_points(obj) -> dict:
    """{name: [lat, lon]} from any of: {name: [lat, lon]}, {id: {"wgs": [lat, lon]}} (gsv.py area), {id: {"lat", "lon"}},
    a list of {"id"/"name", "lat", "lon"} (geodata.py towns --json), or a .jsonl manifest (pano.py list)."""
    if isinstance(obj, (str, Path)):
        text = Path(obj).read_text(encoding="utf-8").strip()
        if text.startswith("{") and "\n{" in text:
            obj = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            obj = json.loads(text)
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (list, tuple)):
                out[str(k)] = [float(v[0]), float(v[1])]
            elif isinstance(v, dict) and "wgs" in v:
                out[str(k)] = [float(v["wgs"][0]), float(v["wgs"][1])]
            elif isinstance(v, dict) and "lat" in v:
                out[str(k)] = [float(v["lat"]), float(v.get("lon", v.get("lng")))]
    else:
        for i, v in enumerate(obj):
            name = v.get("name") or v.get("id") or f"p{i + 1}"
            out[str(name)] = [float(v["lat"]), float(v.get("lon", v.get("lng")))]
    return out


def _get(url: str, path: Path, proxy: str | None) -> bool:
    if path.exists() and path.stat().st_size > 1000:
        return True
    cmd = ["curl", "-q", "-s", "-f", "-m", "60", "-o", str(path), url]
    cmd += curl_args(proxy)
    subprocess.run(cmd, check=False)
    return path.exists() and path.stat().st_size > 1000


def tile_path(cache: Path, source: str, zoom: int, x: int, y: int) -> Path:
    """Cached tile file; one name per source so sat_scan.py and the sheet/wayback commands share downloads."""
    # Older Esri entries can be HTTP-200 no-data pictures rather than imagery.
    tag = _src_tag(source) + ("-strict" if source in ("esri", "esri-street") else "")
    return cache / f"{tag}_{zoom}_{x}_{y}.jpg"


def cell_tiles(x0: float, y0: float, size: int) -> list[tuple[int, int]]:
    """Tiles (x, y) touched by a size×size pixel window whose top-left global pixel is (x0, y0)."""
    return [(tx, ty) for tx in range(int(x0 // 256), int((x0 + size) // 256) + 1)
            for ty in range(int(y0 // 256), int((y0 + size) // 256) + 1)]


def cell_image(lat: float, lon: float, zoom: int, size: int, source: str, proxy: str | None, cache: Path) -> Image.Image:
    """size×size image centred on (lat, lon), stitched from cached tiles (grey where a tile is missing)."""
    cache.mkdir(parents=True, exist_ok=True)
    gx, gy = geo.ll2px(zoom, lat, lon)
    x0, y0 = gx - size / 2, gy - size / 2
    tile = Image.new("RGB", (size, size), "gray")
    for tx, ty in cell_tiles(x0, y0, size):
        p = tile_path(cache, source, zoom, tx, ty)
        if _get(tile_url(source, tx, ty, zoom, proxy), p, proxy):
            try:
                tile.paste(Image.open(p), (int(tx * 256 - x0), int(ty * 256 - y0)))
            except Exception:  # noqa: BLE001
                pass
    return tile


def fetch(center: tuple[float, float], zoom: int, radius: int, out: Path, source: str,
          proxy: str | None, cache: Path) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    gx, gy = geo.ll2px(zoom, *center)
    cx, cy = int(gx // 256), int(gy // 256)
    xs = range(cx - radius, cx + radius + 1)
    ys = range(cy - radius, cy + radius + 1)
    jobs = [(x, y) for x in xs for y in ys]

    def job(t):
        x, y = t
        p = tile_path(cache, source, zoom, x, y)
        ok = _get(tile_url(source, x, y, zoom, proxy), p, proxy)
        return t, p, ok

    img = Image.new("RGB", (256 * len(xs), 256 * len(ys)), "black")
    failed = 0
    with ThreadPoolExecutor(16) as ex:
        for (x, y), p, ok in ex.map(job, jobs):
            if not ok:
                failed += 1
                continue
            try:
                img.paste(Image.open(p), ((x - xs[0]) * 256, (y - ys[0]) * 256))
            except Exception:
                failed += 1
    if failed == len(jobs):
        raise SystemExit(f"No usable tiles from {source} at zoom {zoom}; no mosaic written. Lower --zoom or choose another --source.")
    img.save(out, quality=90)
    meta = {"zoom": zoom, "origin_tile": [xs[0], ys[0]], "center": list(center), "source": source,
            "size": list(img.size), "m_per_px": geo.meters_per_px(zoom, center[0]), "failed_tiles": failed}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


class Mosaic:
    """lat/lon ↔ mosaic pixels."""

    def __init__(self, image: Path):
        self.meta = json.loads(Path(image).with_suffix(".json").read_text(encoding="utf-8"))
        self.z = self.meta["zoom"]
        self.ox, self.oy = self.meta["origin_tile"]

    def to_px(self, lat: float, lon: float) -> tuple[float, float]:
        x, y = geo.ll2px(self.z, lat, lon)
        return x - self.ox * 256, y - self.oy * 256

    def to_ll(self, x: float, y: float) -> tuple[float, float]:
        return geo.px2ll(self.z, x + self.ox * 256, y + self.oy * 256)


PALETTE = ["yellow", "cyan", "magenta", "lime", "orange", "white", "red", "deepskyblue"]


LINE_COLORS = ["orange", "deepskyblue", "magenta", "lime", "white", "red"]


def _draw_geojson(d: ImageDraw.ImageDraw, m: "Mosaic", gj: dict, color: str) -> int:
    """Draw GeoJSON lines, polygons and points on the mosaic (line width 3, polygons as outlines only). Returns how many features were drawn."""
    n = 0
    for ft in gj.get("features", []):
        g = ft.get("geometry") or {}
        t, cs = g.get("type"), g.get("coordinates")
        if not cs:
            continue
        # Branch per type (not a dict literal): the MultiPolygon comprehension must not run on Point coordinates.
        if t == "LineString":
            lines = [cs]
        elif t in ("MultiLineString", "Polygon"):
            lines = cs
        elif t == "MultiPolygon":
            lines = [ring for poly in cs for ring in poly]
        else:
            lines = None
        if lines is not None:
            for ln in lines:
                xy = [m.to_px(c[1], c[0]) for c in ln]
                if len(xy) >= 2:
                    d.line(xy, fill=color, width=3)
            n += 1
        elif t == "Point":
            x, y = m.to_px(cs[1], cs[0])
            d.rectangle([x - 3, y - 3, x + 3, y + 3], outline=color, width=2)
            n += 1
    return n


def _draw_sector(d: ImageDraw.ImageDraw, m: "Mosaic", spec: str) -> None:
    """lat,lon,heading,horizontal FOV,radius m → camera-position view sector."""
    lat, lon, hd, fov, rng = map(float, spec.split(","))
    pts = [m.to_px(lat, lon)]
    steps = max(4, int(fov // 3))
    for k in range(steps + 1):
        a = hd - fov / 2 + fov * k / steps
        pts.append(m.to_px(*geo.dest((lat, lon), a, rng)))
    d.line(pts + [pts[0]], fill="yellow", width=3)
    mid = m.to_px(*geo.dest((lat, lon), hd, rng))
    d.line([pts[0], mid], fill="yellow", width=1)
    x, y = pts[0]
    d.ellipse([x - 7, y - 7, x + 7, y + 7], fill="red", outline="yellow", width=2)


def mark(image: Path, points: dict, out: Path, label: bool, geojsons: list[Path] | None = None,
         sectors: list[str] | None = None) -> None:
    """points: {name: [lat, lon]} (wgs). Colored by the name prefix before the first space; with --label, writes the first 12 characters of the name."""
    m = Mosaic(image)
    img = Image.open(image).convert("RGB")
    d = ImageDraw.Draw(img)
    for i, gp in enumerate(geojsons or []):
        n = _draw_geojson(d, m, json.loads(Path(gp).read_text(encoding="utf-8")), LINE_COLORS[i % len(LINE_COLORS)])
        print(f"{gp}: {n} features, color {LINE_COLORS[i % len(LINE_COLORS)]}")
    for sp in sectors or []:
        _draw_sector(d, m, sp)
    groups: dict[str, str] = {}
    for name, ll in points.items():
        lat, lon = ll[0], ll[1]
        prefix = str(name).split(" ")[0].rstrip("0123456789") or "_"
        color = groups.setdefault(prefix, PALETTE[len(groups) % len(PALETTE)])
        x, y = m.to_px(lat, lon)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=color, outline="black")
        if label:
            lab = str(name)[:12]
            d.text((x + 7, y - 6), lab, fill=color, font=font(14, lab))      # Pillow's default font draws CJK, Hangul, Thai… as boxes
    img.save(out, quality=90)


def grid_points(bbox: str, zoom: int, size: int, step: float | None) -> dict:
    """Tile s,w,n,e into grid points; default spacing = 90% of the width each cell covers."""
    s, w, n, e = (float(v) for v in bbox.split(","))
    mid = (s + n) / 2
    step = step or size * geo.meters_per_px(zoom, mid) * 0.9
    dlat, dlon = step / 110574, step / (111320 * math.cos(math.radians(mid)))
    pts, r, lat = {}, 0, n - dlat / 2
    while lat > s:
        c, lon = 0, w + dlon / 2
        while lon < e:
            pts[f"r{r:02d}c{c:02d}"] = [round(lat, 6), round(lon, 6)]
            c, lon = c + 1, lon + dlon
        r, lat = r + 1, lat - dlat
    return pts


def sheet(points: dict, zoom: int, size: int, cols: int, out: Path, source: str, proxy: str | None, cache: Path) -> list[Path]:
    """One size×size satellite thumbnail centered on each candidate point, with number and name, laid out on one page (more pages automatically when there are too many)."""
    cache.mkdir(parents=True, exist_ok=True)
    items = list(points.items())
    per = cols * cols
    pages = []
    for pi in range(0, len(items), per):
        chunk = items[pi:pi + per]
        rows = (len(chunk) + cols - 1) // cols
        S = Image.new("RGB", (cols * size, rows * size), "black")
        dr = ImageDraw.Draw(S)
        for k, (name, ll) in enumerate(chunk):
            cx, cy = (k % cols) * size, (k // cols) * size
            S.paste(cell_image(ll[0], ll[1], zoom, size, source, proxy, cache), (cx, cy))
            c = size / 2
            dr.line([cx + c - 12, cy + c, cx + c + 12, cy + c], fill="red", width=2)
            dr.line([cx + c, cy + c - 12, cx + c, cy + c + 12], fill="red", width=2)
            dr.rectangle([cx, cy, cx + size, cy + 20], fill="black")
            lab = f"#{pi + k + 1} {str(name)[:28]}"
            dr.text((cx + 4, cy + 3), lab, fill="yellow", font=font(14, lab))
        o = out if pi == 0 else out.with_name(f"{out.stem}_{pi // per + 1}{out.suffix}")
        S.save(o, quality=88)
        pages.append(o)
    return pages


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch")
    f.add_argument("center", help="lat,lon (wgs)")
    f.add_argument("--zoom", type=int, default=18, help="17≈1.1m/px for an area, 19≈0.28m/px for a single building")
    f.add_argument("--radius", type=int, default=4, help="rings of tiles around the center tile, 4 → 9x9 tiles")
    f.add_argument("--out", type=Path, required=True)
    f.add_argument("--source", default="google", help=SOURCE_HELP)
    f.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)
    f.add_argument("--cache", type=Path, default=Path(".geo-cache/tiles"))

    mk = sub.add_parser("mark")
    mk.add_argument("image", type=Path)
    mk.add_argument("--points", type=Path, help="points: {name: [lat, lon]}, gsv.py area output, geodata.py towns --json, or a pano.py manifest")
    mk.add_argument("--out", type=Path, required=True)
    mk.add_argument("--label", action="store_true")
    mk.add_argument("--geojson", type=Path, action="append", help="overlay GeoJSON (output of osm.py geom), repeatable, one color per file")
    mk.add_argument("--sector", action="append", help="camera-position view sector lat,lon,heading,horizontal FOV,radius m, repeatable")

    sh = sub.add_parser("sheet", help="centered satellite thumbnail for each candidate point, laid out as a numbered comparison page")
    shg = sh.add_mutually_exclusive_group(required=True)
    shg.add_argument("--points", type=Path, help="points ({name: [lat, lon]}, geodata.py towns --json, a pano.py manifest, gsv.py area output)")
    shg.add_argument("--grid", help="s,w,n,e: cover an area with a grid and render cell by cell (cell name r<row>c<col>: r00 northernmost, c00 westernmost; center coordinates written to <out>.cells.json)")
    sh.add_argument("--step", type=float, help="--grid cell spacing (meters); default leaves 10%% overlap of the area each cell covers")
    sh.add_argument("--zoom", type=int, default=18)
    sh.add_argument("--size", type=int, default=320, help="pixels per cell")
    sh.add_argument("--cols", type=int, default=4, help="cols×cols cells per page")
    sh.add_argument("--out", type=Path, required=True)
    sh.add_argument("--source", default="google", help=SOURCE_HELP)
    sh.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)
    sh.add_argument("--cache", type=Path, default=Path(".geo-cache/tiles"))

    pl = sub.add_parser("px2ll", help="pixels on a mosaic (or a cropped/scaled copy of it) → lat/lon")
    pl.add_argument("image", type=Path, help="mosaic from tiles.py fetch (needs the same-name .json next to it)")
    pl.add_argument("--px", action="append", required=True, help="x,y, repeatable; if you measured on a cropped/scaled image, pair with --crop/--scale")
    pl.add_argument("--crop", default="0,0", help="top-left x0,y0, in the original mosaic, of the image you measured pixels on")
    pl.add_argument("--scale", type=float, default=1.0, help="scale of that image relative to the original mosaic (0.5 for half size)")
    pl.add_argument("--out", type=Path, help="write {p1: [lat, lon], ...}")

    wb = sub.add_parser("wayback", help="historical satellite imagery at a point: every Esri Wayback release where it changed, "
                                        "with its capture date at the point")
    wb.add_argument("center", help="lat,lon")
    wb.add_argument("--zoom", type=int, default=17)
    wb.add_argument("--size", type=int, default=384, help="pixels per thumbnail")
    wb.add_argument("--out", type=Path, required=True, help="contact sheet of the distinct versions")
    wb.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)
    wb.add_argument("--cache", type=Path, default=Path(".geo-cache/tiles"))

    args = ap.parse_args(_neg_coords(sys.argv[1:]))
    if args.cmd == "wayback":
        lat, lon = map(float, args.center.split(","))
        gx, gy = geo.ll2px(args.zoom, lat, lon)
        tx, ty = int(gx // 256), int(gy // 256)
        rel = wayback_releases(args.proxy)
        args.cache.mkdir(parents=True, exist_ok=True)

        def probe(r):
            p = tile_path(args.cache, f"wayback:{r['id']}", args.zoom, tx, ty)
            ok = _get(tile_url(f"wayback:{r['id']}", tx, ty, args.zoom, args.proxy), p, args.proxy)
            return r, (hashlib.sha1(p.read_bytes()).hexdigest() if ok else None)
        with ThreadPoolExecutor(12) as ex:
            probed = list(ex.map(probe, rel))
            versions, last = [], None
            for r, h in probed:
                if h and h != last:
                    versions.append(r)
                    last = h
            caps = list(ex.map(lambda r: capture_at(r, lat, lon, args.zoom, args.proxy, args.cache), versions))
        notes = [_capture_text(c, r["date"]) for r, c in zip(versions, caps)]
        print(f"{len(rel)} Wayback releases {rel[0]['date']} … {rel[-1]['date']}; the imagery here changed {len(versions)} times:")
        for r, note in zip(versions, notes):
            print(f"  release {r['id']:>6}  {note}")
        if any(c["captured"] for c in caps):
            print("Capture dates are read at the point itself: a thumbnail can cross a mosaic seam, and the rest of it may have another date.")
        thumbs = []
        for r, c in zip(versions, caps):     # one thumbnail per version, same framing; the label fits the 28-character cell title
            o = args.out.with_name(f"{args.out.stem}_{r['id']}.jpg")
            label = f"{c['captured'] or 'capture ?'} (pub {r['date']})"
            thumbs.append(sheet({label: [lat, lon]}, args.zoom, args.size, 1, o, f"wayback:{r['id']}", args.proxy, args.cache)[0])
        cols = min(4, len(thumbs)) or 1
        S = Image.new("RGB", (cols * args.size, max(1, (len(thumbs) + cols - 1) // cols) * args.size), "black")
        for k, pg in enumerate(thumbs):
            S.paste(Image.open(pg), ((k % cols) * args.size, (k // cols) * args.size))
            pg.unlink()
        S.save(args.out, quality=88)
        rows = [{"id": r["id"], "published": r["date"], **c, "note": note, "url": r["url"]} for r, c, note in zip(versions, caps, notes)]
        args.out.with_suffix(".json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
        unknown = sum(not c["captured"] for c in caps)
        print(f"-> {args.out}" + (f" ({unknown} version(s) with capture unknown: there the date is the publication date; "
                                  "the capture is earlier)" if unknown else ""))
        return
    if args.cmd == "px2ll":
        m = Mosaic(args.image)
        x0, y0 = (float(v) for v in args.crop.split(","))
        pts = {}
        for i, s in enumerate(args.px, 1):
            x, y = (float(v) for v in s.split(","))
            lat, lon = m.to_ll(x0 + x / args.scale, y0 + y / args.scale)
            pts[f"p{i}"] = [round(lat, 6), round(lon, 6)]
            print(f"p{i}  ({x:.0f},{y:.0f}) → {lat:.6f},{lon:.6f}")
        if args.out:
            args.out.write_text(json.dumps(pts, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"-> {args.out}")
        return
    if args.cmd == "sheet":
        pts = load_points(args.points) if args.points else grid_points(args.grid, args.zoom, args.size, args.step)
        if args.grid:
            args.out.with_suffix(".cells.json").write_text(json.dumps(pts, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"grid: {len(pts)} cells (cell name r<row>c<col>, rows north to south, columns west to east; cell center coordinates -> {args.out.with_suffix('.cells.json')})")
        for p in sheet(pts, args.zoom, args.size, args.cols, args.out, args.source, args.proxy, args.cache):
            print(p)
        return
    if args.cmd == "fetch":
        lat, lon = map(float, args.center.split(","))
        meta = fetch((lat, lon), args.zoom, args.radius, args.out, args.source, args.proxy, args.cache)
        print(json.dumps(meta, ensure_ascii=False))
    elif args.cmd == "mark":
        if not (args.points or args.geojson or args.sector):
            ap.error("mark needs at least one of --points, --geojson, --sector")
        mark(args.image, load_points(args.points) if args.points else {}, args.out, args.label,
             args.geojson, args.sector)
        print(args.out)


if __name__ == "__main__":
    # Chinese-locale Windows writes GBK by default: m², ñ make it crash, and the Chinese the agent reads comes out garbled
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
