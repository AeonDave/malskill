"""Street-level imagery helpers shared by gsv.py, refsheet.py, bench.py and pano.py.

Google retired the GET GeoPhotoService.SingleImageSearch endpoint and the streetviewpixels thumbnail endpoint refuses
anonymous callers (403). Discovery therefore reads Google Maps coverage tiles (every official panorama inside a zoom-17
map tile, fetched with curl so GEO_PROXY applies, cached per tile); metadata and panoramas come from the maintained
`streetlevel` package; views are rendered locally from the equirectangular panorama.
A coverage reply that is not a coverage tile (network failure, 429 page, changed layout) raises ServiceError: a failed
lookup is never reported as "no panorama".
"""
from __future__ import annotations

import json
import math
import sys
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

# coverage tiles live in coverage.py (stdlib only); re-exported here for gsv.py, refsheet.py, bench.py and the tests
from .coverage import COVERAGE_MAX_AGE_S, ServiceError, _coverage_rows, official, panos_around, tile_panos, tiles_around  # noqa: F401
from .geomath import haversine_m as dist_m, tile_xy  # noqa: F401  (gsv.py, pano.py and bench.py use SL.tile_xy / SL.dist_m)
from .pano import bound_requests_timeout, equirect_view, read_image, read_or_build, write_atomic
from .paths import cache_dir

_SV = None


def streetview():
    """streetlevel.streetview, importable even without pyexiv2's native library (only used to write EXIF)."""
    global _SV
    if _SV is not None:
        return _SV
    try:
        import pyexiv2  # noqa: F401
    except Exception:  # noqa: BLE001 - missing dylib raises OSError, not ImportError
        stub = types.ModuleType("pyexiv2")

        class _Unavailable:
            def __init__(self, *a, **k):
                raise RuntimeError("pyexiv2 is unavailable; streetlevel's EXIF writing is disabled")

        stub.ImageData = stub.Image = _Unavailable   # streetlevel/exif.py references pyexiv2.ImageData at import time
        sys.modules["pyexiv2"] = stub
    bound_requests_timeout()                # bound every streetlevel HTTP call (60 s default)
    from streetlevel import streetview as sv
    _SV = sv
    return sv


def find_near(lat: float, lon: float, radius: float = 50.0, max_ring: int = 5, workers: int = 8,
              proxy: str | None = None, cache: Path | None = None) -> list[dict]:
    """Official panoramas within radius metres, nearest first: [{id, lat, lon, dist_m}]. Searches z17 coverage tiles
    (~300 m wide at the equator) in rings around the point. Raises ServiceError when nothing was found and some
    coverage lookups failed (a failed lookup is not "no coverage")."""
    cache = cache or cache_dir("gsv", "coverage")
    x0, y0 = tile_xy(lat, lon)
    tile_m = 40075016.686 * max(math.cos(math.radians(lat)), 0.05) / 2 ** 17
    rings = min(max_ring, max(1, math.ceil(radius / tile_m)))
    seen: dict[str, dict] = {}
    errors: list[str] = []

    def fetch(xy):
        try:
            return tile_panos(*xy, proxy, cache, COVERAGE_MAX_AGE_S)
        except ServiceError as e:
            errors.append(str(e))
            return []

    for ring in range(0, rings + 1):
        xys = [(x0 + dx, y0 + dy) for dx in range(-ring, ring + 1) for dy in range(-ring, ring + 1)
               if max(abs(dx), abs(dy)) == ring]
        with ThreadPoolExecutor(workers) as ex:
            for panos in ex.map(fetch, xys):
                for pid, la, lo in panos:
                    if pid not in seen:
                        seen[pid] = {"id": pid, "lat": la, "lon": lo, "dist_m": dist_m((lat, lon), (la, lo))}
        inside = [v for v in seen.values() if v["dist_m"] <= radius]
        # stop once we have a hit and the next ring can only be farther away than the best hit
        if inside and min(v["dist_m"] for v in inside) < (ring + 0.5) * tile_m:
            break
    hits = sorted((v for v in seen.values() if v["dist_m"] <= radius), key=lambda v: v["dist_m"])
    if not hits and errors:
        raise ServiceError(f"{len(errors)} coverage lookup(s) failed: {errors[0]}")
    return hits


def metadata(pid: str) -> dict | None:
    sv = streetview()
    try:
        p = sv.find_panorama_by_id(pid)
    except Exception:  # noqa: BLE001
        return None
    if p is None:
        return None
    ym = lambda d: f"{d.year}-{int(d.month):02d}" if d and getattr(d, "month", None) else (str(d.year) if d else None)  # noqa: E731
    hist = []
    for h in p.historical or []:
        if official(h.id):
            hist.append({"id": h.id, "wgs": [h.lat, h.lon], "date": ym(h.date)})
    addr = " / ".join(str(getattr(a, "value", a)) for a in (p.address or []))
    streets = [str(getattr(s.name, "value", s.name)) for s in (p.street_names or [])]
    return {"id": p.id, "wgs": [p.lat, p.lon], "pano_heading": round(math.degrees(p.heading or 0) % 360, 1),
            "date": ym(p.date), "country_code": p.country_code, "address": addr, "streets": streets,
            "elevation_m": p.elevation, "source": p.source, "copyright": p.copyright_message,
            "history": sorted(hist, key=lambda h: h["date"] or "", reverse=True),
            "dates_seen": sorted({d for d in [ym(p.date), *(h["date"] for h in hist)] if d}),
            "neighbors": [{"id": n.id, "wgs": [n.lat, n.lon]} for n in (p.neighbors or [])][:40]}


def equirect(pid: str, cache: Path, zoom: int = 3) -> tuple[np.ndarray, float]:
    """Equirectangular panorama as an array plus the car heading (degrees) at the image centre; cached with a JSON sidecar,
    downloaded once however many threads ask for it, downloaded again when the cached pair is broken."""
    img_p, meta_p = cache / f"{pid}_z{zoom}.jpg", cache / f"{pid}_z{zoom}.json"

    def build():
        sv = streetview()
        p = sv.find_panorama_by_id(pid)
        if p is None:
            raise RuntimeError(f"panorama {pid} not found")
        im = sv.get_panorama(p, zoom=zoom).convert("RGB")
        heading = math.degrees(p.heading or 0.0) % 360
        write_atomic(img_p, lambda tmp: im.save(tmp, "JPEG", quality=90))
        write_atomic(meta_p, lambda tmp: tmp.write_text(json.dumps({"heading": heading}, ensure_ascii=False), encoding="utf-8"))
    return read_or_build([img_p, meta_p],
                         lambda: (np.asarray(read_image(img_p)), json.loads(meta_p.read_text(encoding="utf-8"))["heading"]), build)


def perspective(eq: np.ndarray, pano_heading: float, yaw: float, pitch: float = 0.0, hfov: float = 90.0,
                w: int = 1024, h: int = 768) -> Image.Image:
    """Pinhole view from an equirectangular panorama. yaw: compass bearing; pitch: + looks up; hfov in degrees.
    Same renderer as pano.equirect_view (the panorama centre column looks along pano_heading)."""
    return equirect_view(eq, pano_heading, yaw, pitch, hfov, w, h)
