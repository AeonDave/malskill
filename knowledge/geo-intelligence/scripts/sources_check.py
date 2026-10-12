#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["streetlevel", "numpy", "pillow"]
# ///
"""Live known-answer probes for every external service the toolkit calls; prints which ones answer correctly.

Each probe asks a question with a known answer (Eiffel Tower coordinates, Mont Blanc elevation, Paris->Lyon road
distance...), so a 200 page that no longer carries the data still fails. URLs come from the scripts themselves
(module constants or the same helper functions), so a probe tests what the code really calls.

  sources_check.py                          all probes; exit 1 if a non-optional probe fails
  sources_check.py --only nominatim,overpass --timeout 30
  sources_check.py --no-models --json sources.json
  sources_check.py --list                   the registry without running it

Status: PASS (expected answer), FAIL (unreachable or wrong answer), SKIP (needs a token or was excluded).
Optional probes (alternate mirrors, secondary street-level providers, model hubs) never change the exit code.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import tempfile
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from geolib import net  # noqa: E402
from geolib.geomath import ll2px, tile_xy  # noqa: E402
from geolib.net import PROXY_HELP  # noqa: E402

UA = "geo-intelligence/1.0 (+https://github.com/AeonDave/malskill; sources_check)"
PARIS = (48.8584, 2.2945)                 # Eiffel Tower
PARIS_STREET = (48.8698, 2.3075)          # Champs-Elysees: dense official Street View
LYON = (45.7640, 4.8357)
MONT_BLANC = (45.8326, 6.8652, 4808.0)
BEIJING = (39.9075, 116.3972)             # Chang'an Avenue at Tiananmen


class Fail(Exception):
    """Wrong answer or unreachable service."""


class Skip(Exception):
    """Probe not applicable (missing token, excluded group)."""


@dataclass
class Ctx:
    proxy: str | None
    timeout: int
    locks: dict[str, threading.Lock] = field(default_factory=lambda: {"nominatim": threading.Lock(), "overpass": threading.Lock()})


@dataclass(frozen=True)
class Probe:
    key: str                              # short id for --only
    source: str                           # display name
    scripts: str                          # scripts this probe guards (comma-separated)
    url: str                              # representative URL actually requested
    expect: str                           # the known answer
    check: Callable[[Ctx], str]           # returns a detail line on success; raises Fail / Skip
    optional: bool = False
    group: str = "core"                   # "models" is excluded by --no-models
    serial: str = ""                      # probes sharing a name run one at a time (per-IP slots, 1 req/s policies)


# ---------------------------------------------------------------- helpers

def const(script: str, name: str):
    """Module-level literal from a script without importing it (heavy ML scripts stay unimported)."""
    tree = ast.parse((HERE / script).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(f"{script}: {name} not found")


def get(url: str, ctx: Ctx, headers: dict | None = None, form: dict | None = None) -> bytes:
    status, _, body = net.request(url, ctx.proxy, ctx.timeout, {"User-Agent": UA, **(headers or {})}, form=form)
    if status != 200:
        raise Fail(f"HTTP {status}")
    return body


def get_json(url: str, ctx: Ctx, **kw):
    body = get(url, ctx, **kw)
    try:
        return json.loads(body)
    except ValueError:
        raise Fail(f"not JSON: {body[:80]!r}") from None


def head(url: str, ctx: Ctx) -> dict:
    status, hdrs, _ = net.request(url, ctx.proxy, ctx.timeout, {"User-Agent": UA}, head=True)
    if status != 200:
        raise Fail(f"HTTP {status}")
    return hdrs


def image_magic(url: str, ctx: Ctx) -> str:
    b = get(url, ctx)
    kind = "JPEG" if b[:3] == b"\xff\xd8\xff" else "PNG" if b[:8] == b"\x89PNG\r\n\x1a\n" else None
    if not kind:
        raise Fail(f"not an image: {b[:24]!r}")
    if len(b) < 600:
        raise Fail(f"{kind} only {len(b)} bytes (blank placeholder tile?)")
    return f"{kind} {len(b)} bytes"


def near(a: float, b: float, tol: float, what: str) -> None:
    if abs(a - b) > tol:
        raise Fail(f"{what} {a:.4f}, expected {b} +/- {tol}")


# ---------------------------------------------------------------- probe bodies needing code paths

def _poi():
    import poi
    return poi


def nominatim_search(ctx: Ctx) -> str:
    rows = _poi().nominatim("search", {"q": "Eiffel Tower, Paris", "limit": 1}, ctx.proxy)
    if not rows:
        raise Fail("no result")
    lat, lon = float(rows[0]["lat"]), float(rows[0]["lon"])
    near(lat, 48.858, 0.01, "lat")
    near(lon, 2.2945, 0.01, "lon")
    return f"{lat:.5f},{lon:.5f} {rows[0].get('name', '')}"


def nominatim_reverse(ctx: Ctx) -> str:
    d = _poi().nominatim("reverse", {"lat": PARIS[0], "lon": PARIS[1], "addressdetails": 1}, ctx.proxy)
    cc = (d.get("address") or {}).get("country_code")
    if cc != "fr":
        raise Fail(f"country_code {cc!r}, expected 'fr'")
    return d.get("display_name", "")[:70]


def poi_search_osm(ctx: Ctx) -> str:
    time.sleep(1.0)                       # search_osm bypasses poi.nominatim's spacing; keep the 1 req/s policy
    rows = _poi().search_osm("Eiffel Tower", None, 1, ctx.proxy, "fr")
    if not rows:
        raise Fail("no result")
    lat, lon = rows[0]["wgs"]
    near(lat, 48.858, 0.01, "lat")
    return f"{rows[0]['name']} {lat},{lon}"


def overpass_mirror(ep: str) -> Callable[[Ctx], str]:
    def run(ctx: Ctx) -> str:
        import osm
        data, err = osm._post(ep, "[out:json][timeout:25];node(1);out;", ctx.proxy, ctx.timeout)
        if data is None:
            raise Fail(err[:120] or "no reply")
        els = data.get("elements") or []
        if not els or els[0].get("id") != 1:
            raise Fail(f"node 1 missing: {str(els)[:80]}")
        return f"node 1 at {els[0].get('lat')},{els[0].get('lon')}"
    return run


def overpass_any(ctx: Ctx) -> str:
    import contextlib
    import io
    import osm
    ql = f"[out:json][timeout:25];node[amenity]({PARIS[0] - 0.001},{PARIS[1] - 0.001},{PARIS[0] + 0.001},{PARIS[1] + 0.001});out count;"
    err = io.StringIO()
    with tempfile.TemporaryDirectory() as d, contextlib.redirect_stderr(err):
        try:
            data = osm.run(ql, ctx.proxy, Path(d), timeout=25, rounds=1)
        except SystemExit as e:
            raise Fail(str(e)[:120]) from None
    els = data.get("elements") or []
    if not els or "tags" not in els[0]:
        raise Fail(f"no count element: {str(data)[:80]}")
    return f"amenity count {els[0]['tags'].get('nodes', '?')} (first mirror that answered)"


def tile_probe(source: str, lat: float, lon: float, z: int) -> tuple[str, Callable[[Ctx], str]]:
    import tiles
    x, y = tile_xy(lat, lon, z)
    url = tiles.tile_url(source, x, y, z)
    return url, lambda ctx: image_magic(url, ctx)


def wayback(ctx: Ctx) -> str:
    d = get_json(const("tiles.py", "WAYBACK_CONFIG"), ctx)
    rel = [v for v in d.values() if isinstance(v, dict) and "{level}" in v.get("itemURL", "")]
    if len(rel) < 50:
        raise Fail(f"only {len(rel)} releases with an itemURL template")
    dates = sorted(m.group(1) for v in rel if (m := re.search(r"(\d{4}-\d{2}-\d{2})", v.get("itemTitle", ""))))
    return f"{len(rel)} releases {dates[0] if dates else '?'} .. {dates[-1] if dates else '?'}"


def terrarium(ctx: Ctx) -> str:
    import io
    from PIL import Image
    z = 12
    lat, lon, elev = MONT_BLANC
    xf, yf = (v / 256 for v in ll2px(z, lat, lon))        # fractional tile coordinates: the pixel inside the tile
    url = const("terrain.py", "TILE").format(z=z, x=int(xf), y=int(yf))
    im = Image.open(io.BytesIO(get(url, ctx))).convert("RGB")
    px, py = int((xf % 1) * 256), int((yf % 1) * 256)
    best = max(r * 256 + g + b / 256 - 32768
               for i in range(max(0, px - 3), min(256, px + 4)) for j in range(max(0, py - 3), min(256, py + 4))
               for r, g, b in [im.getpixel((i, j))])
    near(best, elev, 300, "summit elevation m")
    return f"Mont Blanc summit {best:.0f} m"


def open_meteo(ctx: Ctx) -> str:
    # same endpoint and parameters as sun.py cmd_weather
    q = urllib.parse.urlencode({"latitude": "38.7200", "longitude": "-9.1400", "start_date": "2024-07-16",
                                "end_date": "2024-07-16", "hourly": "cloud_cover,sunshine_duration", "timezone": "auto"})
    d = get_json(f"https://archive-api.open-meteo.com/v1/archive?{q}", ctx)
    cc = (d.get("hourly") or {}).get("cloud_cover") or []
    if len(cc) != 24 or not all(isinstance(v, (int, float)) for v in cc):
        raise Fail(f"hourly cloud_cover has {len(cc)} values")
    return f"24 hourly cloud_cover values, mean {sum(cc) / 24:.0f}%"


def geonames_info(ctx: Ctx) -> str:
    txt = get(const("geodata.py", "GEONAMES") + "countryInfo.txt", ctx).decode("utf-8", "replace")
    if not re.search(r"^FR\tFRA\t250\t", txt, re.M):
        raise Fail("France row missing")
    return f"{sum(1 for ln in txt.splitlines() if ln and not ln.startswith('#'))} country rows"


def head_size(url: str, min_bytes: int) -> Callable[[Ctx], str]:
    def run(ctx: Ctx) -> str:
        h = head(url, ctx)
        size = int(h.get("content-length") or 0)
        if size and size < min_bytes:
            raise Fail(f"only {size} bytes")
        if not size and "json" not in h.get("content-type", "") and "zip" not in h.get("content-type", ""):
            raise Fail(f"no length, content-type {h.get('content-type')!r}")
        return f"{size / 1e6:.1f} MB" if size else f"{h.get('content-type')} (chunked)"
    return run


def baidu_qsdata(ctx: Ctx) -> str:
    import geo
    x, y = geo.convert(BEIJING[0], BEIJING[1], "wgs", "bdmc")
    d = get_json(f"{const('baidu_pano.py', 'API')}?qt=qsdata&x={x:.0f}&y={y:.0f}", ctx)
    c = d.get("content")
    if not c or not c.get("id"):
        raise Fail(f"no panorama content: {str(d)[:80]}")
    return f"pano {c['id']} {c.get('RoadName', '')}"


def so_search(ctx: Ctx) -> str:
    rows, _ = _poi().search_so("天安门", "北京", 3, ctx.proxy)
    if not rows:
        raise Fail("no POI")
    lat, lon = rows[0]["wgs"]
    near(lat, 39.906, 0.1, "lat")
    return f"{rows[0]['name']} {lat},{lon}"


def _sl():
    from geolib import streetlevel as SL
    return SL


def gsv_coverage(ctx: Ctx) -> str:
    hits = _sl().find_near(*PARIS_STREET, radius=100)
    if not hits:
        raise Fail("no official panorama within 100 m of the Champs-Elysees")
    return f"{len(hits)} panoramas, nearest {hits[0]['id']} at {hits[0]['dist_m']:.0f} m"


def gsv_targets(ctx: Ctx) -> str:
    """The exact path of `gsv.py targets`: geolib.coverage.panos_around over fresh (uncached) z17 tiles."""
    from geolib import coverage
    with tempfile.TemporaryDirectory() as d:
        try:
            picked = coverage.panos_around(48.8738, 2.2950, 12, 70, 2, 15, ctx.proxy, Path(d))
        except coverage.ServiceError as e:
            raise Fail(f"coverage lookup failed: {str(e)[:120]}") from None
    if not picked:
        raise Fail("no official panorama 12-70 m from the Arc de Triomphe (reply layout changed?)")
    return f"{len(picked)} views, nearest {picked[0][0]} at {picked[0][3]:.0f} m"


def gsv_metadata(ctx: Ctx) -> str:
    SL = _sl()
    hits = SL.find_near(*PARIS_STREET, radius=100)
    if not hits:
        raise Fail("no panorama to look up")
    m = SL.metadata(hits[0]["id"])
    if not m or m.get("country_code") != "FR" or not m.get("date"):
        raise Fail(f"metadata {str(m)[:80]}")
    return f"{m['id']} {m['date']} {m['country_code']} {m.get('address', '')[:40]}"


def pano_lister(provider: str, lat: float, lon: float, radius: float = 150) -> Callable[[Ctx], str]:
    def run(ctx: Ctx) -> str:
        import contextlib
        import io
        import pano
        bb = pano.bbox_around(lat, lon, radius)
        with contextlib.redirect_stderr(io.StringIO()):
            if provider in pano.ZOOMS:
                res = pano._nearest_one(provider, lat, lon, radius * 4, time.time())
                if not res.get("nearest_id"):
                    raise Fail(res.get("note") or "no panorama")
                return f"nearest {res['nearest_id']} at {res['nearest_m']} m"
            rows = pano.LISTERS[provider](bb, max(radius / 6, 25), 50)
        if not rows:
            raise Fail("no panoramas returned (service down, blocked or format changed)")
        return f"{len(rows)} panoramas, e.g. {rows[0]['id']}"
    return run


def mapillary(ctx: Ctx) -> str:
    tok = os.environ.get("MAPILLARY_TOKEN")
    if not tok:
        raise Skip("MAPILLARY_TOKEN not set")
    w, s = PARIS[1] - 0.002, PARIS[0] - 0.002
    d = get_json(f"https://graph.mapillary.com/images?access_token={tok}&bbox={w},{s},{w + 0.004},{s + 0.004}&fields=id&limit=5", ctx)
    if not d.get("data"):
        raise Fail(f"no images: {str(d)[:80]}")
    return f"{len(d['data'])} images"


def socrata(ctx: Ctx) -> str:
    import opendata
    d = get_json(f"{opendata.CATALOG['us']}?q=trees&limit=1", ctx)
    res = d.get("results") or []
    if not res or not (res[0].get("resource") or {}).get("id"):
        raise Fail(f"no dataset: {str(d)[:80]}")
    return f"{res[0]['resource']['id']} {res[0]['resource'].get('name', '')[:50]}"


def commons(ctx: Ctx) -> str:
    q = urllib.parse.urlencode({"action": "query", "list": "geosearch", "gscoord": f"{PARIS[0]}|{PARIS[1]}", "gsradius": 500,
                                "gsnamespace": 6, "gslimit": 5, "format": "json"})
    d = get_json(f"https://commons.wikimedia.org/w/api.php?{q}", ctx)
    rows = (d.get("query") or {}).get("geosearch") or []
    if not rows:
        raise Fail("no geotagged file near the Eiffel Tower")
    return f"{len(rows)} files, e.g. {rows[0]['title'][:50]}"


def html_markers(url: str, must: tuple[str, ...], deny: tuple[str, ...] = ()) -> Callable[[Ctx], str]:
    def run(ctx: Ctx) -> str:
        page = get(url, ctx, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}).decode("utf-8", "replace").lower()
        miss = [m for m in must if m not in page]
        if miss:
            raise Fail(f"markers missing: {miss}")
        hit = [m for m in deny if m in page]
        if hit:
            raise Fail(f"blocked page ({hit[0]})")
        return f"{len(page) // 1024} KB page with {', '.join(must)}"
    return run


def osrm(mode: str, a: tuple, b: tuple, lo_km: float, hi_km: float, max_kmh: float | None = None,
         base: str | None = None) -> tuple[str, Callable[[Ctx], str]]:
    base = base or const("poi.py", "OSRM_ROUTES")[mode]
    url = f"{base}/{a[1]},{a[0]};{b[1]},{b[0]}?overview=false&steps=false"

    def run(ctx: Ctx) -> str:
        d = get_json(url, ctx)
        if d.get("code") != "Ok" or not d.get("routes"):
            raise Fail(f"code {d.get('code')}")
        km, h = d["routes"][0]["distance"] / 1000, d["routes"][0]["duration"] / 3600
        if not lo_km <= km <= hi_km:
            raise Fail(f"{km:.0f} km, expected {lo_km:g}-{hi_km:g}")
        if max_kmh and h and km / h > max_kmh:
            raise Fail(f"{km / h:.0f} km/h: not a {mode} profile")
        return f"{km:.1f} km, {h * 60:.0f} min"
    return url, run


# refresh.py (maintainers): MediaWiki parse API for the plate pages, raw GitHub for the China admin table; the exact URLs it requests
_IT_LANG, _IT_TITLE = const("refresh.py", "PLATE_PAGES")["IT"]
WIKI_PLATES = const("refresh.py", "WIKI_API").format(lang=_IT_LANG, title=urllib.parse.quote(_IT_TITLE))
CN_ADMIN_URL = const("refresh.py", "SOURCES")["cn/admin"][0]


def wikipedia_plates(ctx: Ctx) -> str:
    d = get_json(WIKI_PLATES, ctx)
    html = ((d.get("parse") or {}).get("text") or {}).get("*", "")
    if "Palermo" not in html:
        raise Fail("parsed page has no Palermo row")
    return f"{len(html) // 1024} KB of table HTML"


def timeapi(ctx: Ctx) -> str:
    d = get_json(f"{const('poi.py', 'TIMEAPI')}?latitude={PARIS[0]}&longitude={PARIS[1]}", ctx)
    if d.get("timeZone") != "Europe/Paris":
        raise Fail(f"timeZone {d.get('timeZone')!r}")
    return f"Europe/Paris, now {str(d.get('currentLocalTime'))[:16]}"


def hf_model(repo: str, needs_file: str | None = None) -> Callable[[Ctx], str]:
    def run(ctx: Ctx) -> str:
        d = get_json(f"https://huggingface.co/api/models/{repo}", ctx)
        if (d.get("id") or "").lower() != repo.lower():
            raise Fail(f"id {d.get('id')!r}")
        files = [s.get("rfilename") for s in d.get("siblings") or []]
        if needs_file and needs_file not in files:
            raise Fail(f"{needs_file} not in repo")
        return f"{repo} ({len(files)} files)"
    return run


# ---------------------------------------------------------------- registry

def build_registry() -> list[Probe]:
    """Every external endpoint, one entry each. Adding a source = one Probe(...) line."""
    nom = const("poi.py", "NOMINATIM")
    P: list[Probe] = [
        Probe("nominatim-search", "Nominatim search", "poi.py", f"{nom}/search?q=Eiffel+Tower",
              "Eiffel Tower at 48.858 +/- 0.01, 2.2945 +/- 0.01", nominatim_search, serial="nominatim"),
        Probe("nominatim-reverse", "Nominatim reverse", "poi.py,geodata.py", f"{nom}/reverse?lat={PARIS[0]}&lon={PARIS[1]}",
              "country_code fr", nominatim_reverse, serial="nominatim"),
        Probe("poi-osm", "Nominatim via poi.py search", "poi.py", f"{nom}/search?q=Eiffel+Tower&countrycodes=fr",
              "first row within 0.01 deg of 48.858", poi_search_osm, serial="nominatim"),
        Probe("overpass", "Overpass (any mirror, osm.run)", "osm.py,gazetteer.py,poi.py",
              const("osm.py", "ENDPOINTS")[0], "count element for a 0.002 deg bbox", overpass_any, serial="overpass"),
    ]
    import osm
    for ep in osm.endpoints():
        host = urllib.parse.urlsplit(ep).netloc
        P.append(Probe(f"overpass-{host}", f"Overpass mirror {host}", "osm.py", ep, "node 1 returned as JSON",
                       overpass_mirror(ep), optional=True, serial="overpass"))
    for key, src, lbl, z, opt in (("google-sat", "google", "Google satellite tile z17", 17, False),
                                  ("google-hybrid", "google-hybrid", "Google hybrid tile z17", 17, False),
                                  ("esri", "esri", "Esri World Imagery tile z17", 17, False),
                                  ("bing-aerial", "bing", "Bing aerial tile (quadkey) z17", 17, True),
                                  ("eox-s2", "s2:2024", "EOX Sentinel-2 cloudless 2024 z12", 12, False),
                                  ("gibs", "gibs:2024-07-16", "NASA GIBS MODIS 2024-07-16 z6", 6, False)):
        url, fn = tile_probe(src, PARIS[0], PARIS[1], z)
        P.append(Probe(key, lbl, "tiles.py", url, "JPEG/PNG bytes over a Paris tile", fn, optional=opt))
    osrm_url, osrm_fn = osrm("driving", PARIS, LYON, 380, 520)
    demo_url, demo_fn = osrm("driving", PARIS, LYON, 380, 520, base=const("poi.py", "OSRM_FALLBACK"))
    foot_url, foot_fn = osrm("walking", (45.764, 4.836), (45.771, 4.880), 3, 7, max_kmh=8)
    bike_url, bike_fn = osrm("cycling", (45.764, 4.836), (45.771, 4.880), 3, 7, max_kmh=30)
    nsi = const("textgeo.py", "NSI_URL")
    P += [
        Probe("esri-wayback", "Esri Wayback releases", "tiles.py", const("tiles.py", "WAYBACK_CONFIG"),
              ">= 50 releases with a {level}/{row}/{col} URL", wayback),
        Probe("terrarium", "AWS Terrarium elevation tiles", "terrain.py,geo.py", const("terrain.py", "TILE"),
              "Mont Blanc summit 4808 +/- 300 m", terrarium),
        Probe("open-meteo", "Open-Meteo ERA5 archive", "sun.py", "https://archive-api.open-meteo.com/v1/archive",
              "24 hourly cloud_cover values for 2024-07-16", open_meteo),
        Probe("geonames-info", "GeoNames countryInfo.txt", "geodata.py", const("geodata.py", "GEONAMES") + "countryInfo.txt",
              "France row FR FRA 250", geonames_info),
        Probe("geonames-cities500", "GeoNames cities500.zip", "geodata.py,textgeo.py,board.py",
              const("geodata.py", "GEONAMES") + "cities500.zip", "HEAD 200, > 5 MB",
              head_size(const("geodata.py", "GEONAMES") + "cities500.zip", 5_000_000)),
        Probe("nsi", "jsDelivr name-suggestion-index", "textgeo.py", nsi, "HEAD 200, > 1 MB", head_size(nsi, 1_000_000)),
        Probe("baidu-pano", "Baidu panorama qsdata", "baidu_pano.py,match.py", const("baidu_pano.py", "API") + "?qt=qsdata",
              "panorama id on Chang'an Avenue, Beijing", baidu_qsdata),
        Probe("so-search", "360 Maps search", "poi.py", "https://restapi.map.so.com/newapi",
              "天安门 in Beijing (lat 39.906 +/- 0.1)", so_search),
        Probe("gsv-coverage", "Google Street View coverage tiles (streetlevel)", "gsv.py,refsheet.py,bench.py,pano.py",
              "https://www.google.com/maps/photometa/ac/v1", "official pano id within 100 m of the Champs-Elysees", gsv_coverage),
        Probe("gsv-metadata", "Google Street View metadata (streetlevel)", "gsv.py,refsheet.py",
              "https://www.google.com/maps/photometa/v1", "date and country_code FR", gsv_metadata),
        Probe("gsv-targets", "Google coverage tiles via gsv.py targets (panos_around)", "gsv.py",
              "https://www.google.com/maps/photometa/ac/v1", "official panoramas 12-70 m from the Arc de Triomphe", gsv_targets),
        Probe("apple-lookaround", "Apple Look Around (streetlevel)", "pano.py", "https://gspe76-ssl.ls.apple.com/api/tile",
              "Look Around panoramas near the Eiffel Tower", pano_lister("apple", *PARIS_STREET), optional=True),
        Probe("bing-streetside", "Bing Streetside (streetlevel)", "pano.py", "https://t.ssl.ak.tiles.virtualearth.net",
              "Streetside bubbles near the Champs-Elysees", pano_lister("bing", *PARIS_STREET), optional=True),
        Probe("yandex-pano", "Yandex panoramas (streetlevel)", "pano.py", "https://api-maps.yandex.ru/services/panoramas/1.x/",
              "panorama near Red Square", pano_lister("yandex", 55.7539, 37.6208), optional=True),
        Probe("mapy-pano", "Mapy.cz panoramas (streetlevel)", "pano.py", "https://pro.mapy.cz/panorpc",
              "panorama in Prague old town", pano_lister("mapy", 50.0870, 14.4208), optional=True),
        Probe("kartaview", "KartaView nearby-photos", "pano.py", "https://api.openstreetcam.org/1.0/list/nearby-photos/",
              "photos near the Champs-Elysees", pano_lister("kartaview", *PARIS_STREET, radius=400), optional=True),
        Probe("panoramax", "Panoramax search", "pano.py", const("pano.py", "PANORAMAX")[0] + "/search",
              "pictures near the Champs-Elysees", pano_lister("panoramax", *PARIS_STREET, radius=300), optional=True),
        Probe("mapillary", "Mapillary graph API", "pano.py", "https://graph.mapillary.com/images",
              "images near the Eiffel Tower (needs MAPILLARY_TOKEN)", mapillary, optional=True),
        Probe("socrata", "Socrata catalogue (US)", "opendata.py", "https://api.us.socrata.com/api/catalog/v1?q=trees",
              "a dataset id for 'trees'", socrata),
        Probe("commons", "Wikimedia Commons geosearch", "-", "https://commons.wikimedia.org/w/api.php?list=geosearch",
              "geotagged files within 500 m of the Eiffel Tower (no script calls it yet)", commons, optional=True),
        Probe("yandex-images", "Yandex Images page", "revimg.py", "https://yandex.com/images/",
              "HTTP 200 page with 'yandex', no captcha", html_markers("https://yandex.com/images/", ("yandex",), ("showcaptcha", "smartcaptcha")),
              optional=True),
        Probe("baidu-images", "Baidu image search page", "revimg.py", "https://graph.baidu.com/pcpage/index?tpl_from=pc",
              "HTTP 200 page with 'baidu'", html_markers("https://graph.baidu.com/pcpage/index?tpl_from=pc", ("baidu",)), optional=True),
        Probe("osrm-driving", "OSRM car (routing.openstreetmap.de)", "poi.py", osrm_url, "Paris->Lyon 380-520 km", osrm_fn),
        Probe("osrm-demo", "OSRM demo car fallback (router.project-osrm.org)", "poi.py", demo_url, "Paris->Lyon 380-520 km",
              demo_fn, optional=True),
        Probe("osrm-foot", "OSRM foot (routing.openstreetmap.de)", "poi.py", foot_url,
              "Lyon->Villeurbanne 3-7 km at walking speed (< 8 km/h)", foot_fn, optional=True),
        Probe("osrm-bike", "OSRM bike (routing.openstreetmap.de)", "poi.py", bike_url,
              "Lyon->Villeurbanne 3-7 km below 30 km/h", bike_fn, optional=True),
        Probe("wikipedia-parse", "Wikipedia parse API (plate tables)", "refresh.py,clues.py", WIKI_PLATES,
              "Italian plate page lists Palermo (PA)", wikipedia_plates, optional=True),
        Probe("cn-admin-source", "modood China admin divisions (GitHub raw)", "refresh.py", CN_ADMIN_URL,
              "HEAD 200, > 100 KB", head_size(CN_ADMIN_URL, 100_000), optional=True),
        Probe("timeapi", "timeapi.io coordinate lookup", "poi.py", const("poi.py", "TIMEAPI"), "Europe/Paris", timeapi, optional=True),
    ]
    for key, repo, scripts, need in (("hf-streetclip", const("prior.py", "STREETCLIP"), "prior.py", None),
                                     ("hf-geoclip-backbone", "openai/clip-vit-large-patch14", "prior.py", None),
                                     ("hf-owlv2", const("detect.py", "MODEL"), "detect.py", None),
                                     ("hf-megaloc", const("geolib/megaloc.py", "HF_REPO"), "match.py,sweep.py", "model.safetensors"),
                                     ("hf-clip-b32", const("sat_scan.py", "CLIP_ID"), "sat_scan.py,match.py", None),
                                     ("hf-dinov2", const("match.py", "MODELS")["dino"], "match.py", None)):
        P.append(Probe(key, f"Hugging Face {repo}", scripts, f"https://huggingface.co/api/models/{repo}",
                       f"model card id {repo}" + (f" with {need}" if need else ""), hf_model(repo, need), optional=True, group="models"))
    return P


# ---------------------------------------------------------------- runner

def run_probe(p: Probe, ctx: Ctx, skip_models: bool) -> dict:
    row = {"key": p.key, "source": p.source, "scripts": p.scripts, "optional": p.optional, "url": p.url, "expect": p.expect}
    t0 = time.monotonic()
    try:
        if skip_models and p.group == "models":
            raise Skip("--no-models")
        if p.serial:
            with ctx.locks.setdefault(p.serial, threading.Lock()):
                t0 = time.monotonic()     # latency excludes the wait for the shared slot
                row.update(status="PASS", detail=p.check(ctx))
        else:
            row.update(status="PASS", detail=p.check(ctx))
    except Skip as e:
        row.update(status="SKIP", detail=str(e))
    except Fail as e:
        row.update(status="FAIL", detail=str(e))
    except Exception as e:  # noqa: BLE001 - transport errors, changed formats, missing packages
        row.update(status="FAIL", detail=f"{type(e).__name__}: {str(e)[:150]}")
    row["ms"] = round((time.monotonic() - t0) * 1000)
    return row


def select(probes: list[Probe], only: str | None) -> list[Probe]:
    if not only:
        return probes
    wanted = [w.strip().lower() for w in only.split(",") if w.strip()]
    return [p for p in probes if any(w == p.key or w in p.key or w in p.source.lower() for w in wanted)]


def table(rows: list[dict]) -> str:
    head = ("source", "script(s)", "status", "ms", "detail")
    data = [(r["source"] + (" (optional)" if r["optional"] else ""), r["scripts"], r["status"], str(r["ms"]), r["detail"]) for r in rows]
    w = [min(46, max(len(head[i]), *(len(d[i]) for d in data))) for i in range(4)]
    out = [" | ".join(h.ljust(w[i]) if i < 4 else h for i, h in enumerate(head)),
           "-+-".join("-" * x for x in w) + "-+-" + "-" * 6]
    for d in data:
        out.append(" | ".join((c[:w[i]].ljust(w[i]) if i < 4 else c) for i, c in enumerate(d)))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated probe keys or name fragments (e.g. nominatim,overpass,gsv)")
    ap.add_argument("--timeout", type=int, default=20, help="per-request timeout in seconds (default 20)")
    ap.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)
    ap.add_argument("--no-models", action="store_true", help="skip the Hugging Face model probes")
    ap.add_argument("--json", type=Path, metavar="OUT", help="also write the results as JSON")
    ap.add_argument("--list", action="store_true", help="print the probe registry and exit")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    probes = select(build_registry(), args.only)
    if args.list:
        for p in probes:
            print(f"{p.key:24s} {'opt ' if p.optional else '    '}{p.scripts:34s} {p.expect}")
        return 0
    if not probes:
        print("no probe matches --only", file=sys.stderr)
        return 2
    ctx = Ctx(args.proxy, args.timeout)
    with ThreadPoolExecutor(max(1, args.workers)) as ex:
        rows = list(ex.map(lambda p: run_probe(p, ctx, args.no_models), probes))
    print(table(rows))
    bad = [r for r in rows if r["status"] == "FAIL" and not r["optional"]]
    n = {s: sum(r["status"] == s for r in rows) for s in ("PASS", "FAIL", "SKIP")}
    print(f"\n{n['PASS']} pass, {n['FAIL']} fail ({len(bad)} required), {n['SKIP']} skipped")
    if args.json:
        args.json.write_text(json.dumps({"checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "proxy": bool(net.resolve_proxy(args.proxy)),
                                         "results": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"-> {args.json}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
