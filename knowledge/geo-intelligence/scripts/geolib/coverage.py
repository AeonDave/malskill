"""Google Maps Street View coverage tiles: every official panorama inside one zoom-17 tile, fetched with curl (GEO_PROXY
applies) and cached per tile. Stdlib only, so doctor.py and sources_check.py can use it. A reply that is not a coverage
tile (network failure, 429 page, changed layout) raises ServiceError: a failed lookup is never "no panorama".
Exposes tile_panos, tiles_around and panos_around."""
from __future__ import annotations

import json
import math
import os
import subprocess
import threading
import time
from pathlib import Path

from .geomath import R, haversine_m, ll2px
from .net import curl_args

USER_UPLOAD_PREFIXES = ("CIHM", "CIAB", "CAoS", "AF1Q")


def official(pid: str) -> bool:
    """Official car/trekker panorama id. Discovery keeps only these: user uploads sit at the venue pin, not at their capture
    point, and render only by an id copied from a Maps URL (`gsv.py render <id>`)."""
    return len(pid) == 22 and not pid.startswith(USER_UPLOAD_PREFIXES)


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
# Coverage layer the Maps web client draws: every official panorama inside one z17 tile (~300 m), one request per tile
COVERAGE = "https://www.google.com/maps/photometa/ac/v1?pb=!1m1!1smaps_sv.tactile!6m3!1i{x}!2i{y}!3i17!8b1"
COVERAGE_MAX_AGE_S = 30 * 86400           # find_near re-fetches cached tiles older than this
_COVERAGE_LOCKS = [threading.Lock() for _ in range(64)]   # bounded lock pool: workers sharing a tile fetch it once


class ServiceError(RuntimeError):
    """Google answered with an error instead of a lookup result (endpoint changed, blocked, rate-limited)."""


def _curl(url: str, proxy: str | None, out: Path | None = None, data: str | None = None) -> bytes:
    cmd = ["curl", "-q", "-s", "-m", "40", "-A", UA, *curl_args(proxy)]
    if out:
        cmd += ["-o", str(out)]
    if data is not None:
        cmd += ["-X", "POST", "-H", "content-type: application/json+protobuf",
                "-H", "x-user-agent: grpc-web-javascript/0.1", "--data", data]
    return subprocess.run(cmd + [url], capture_output=True).stdout


def _coverage_rows(t: str) -> list:
    """Rows of one coverage reply. An empty tile (sea, no coverage) is []; anything else that isn't a coverage reply
    (network failure, 429 page, changed layout) raises ServiceError so it isn't mistaken for missing coverage."""
    if not t.startswith(")]}'"):
        raise ServiceError(f"unreadable coverage reply: {' '.join(t.split())[:160] or 'empty (network?)'}")
    try:
        d = json.loads(t[t.index("\n") + 1:])
    except ValueError:
        raise ServiceError(f"unreadable coverage reply: {t[:160]}") from None
    # with panoramas: [null, [null, [rows...]], ...]; an empty tile: [null, null, [cells...]]
    if not isinstance(d, list) or len(d) < 2 or not (d[1] is None or isinstance(d[1], list)):
        raise ServiceError(f"unexpected coverage reply: {t[:160]}")
    if d[1] is None:
        return []
    rows = d[1][1] if len(d[1]) > 1 else None
    if not (rows is None or isinstance(rows, list)):
        raise ServiceError(f"unexpected coverage reply: {t[:160]}")
    return rows or []


def tile_panos(x: int, y: int, proxy: str | None, cache: Path, max_age_s: float | None = None) -> list[tuple[str, float, float]]:
    """All official panoramas in z17 tile (x, y) as (id, lat, lon); an empty tile is []. Only replies that parse as
    coverage are cached (atomically); a failed lookup raises ServiceError and is retried next time."""
    cache.mkdir(parents=True, exist_ok=True)
    x %= 2 ** 17  # tiles wrap at the antimeridian
    p = cache / f"cov17_{x}_{y}.txt"
    with _COVERAGE_LOCKS[hash(str(p.resolve())) % len(_COVERAGE_LOCKS)]:
        try:
            if max_age_s is not None and time.time() - p.stat().st_mtime > max_age_s:
                raise FileNotFoundError(p)
            rows = _coverage_rows(p.read_text(encoding="utf-8", errors="replace"))
        except (FileNotFoundError, ServiceError):
            p.unlink(missing_ok=True)  # missing, stale or invalid cache: fetch again
            t = _curl(COVERAGE.format(x=x, y=y), proxy).decode("utf-8", "replace")
            rows = _coverage_rows(t)
            tmp = p.with_name(f"{p.name}.{os.getpid()}.{threading.get_ident()}.tmp")
            tmp.write_text(t, encoding="utf-8")
            os.replace(tmp, p)
    out = []
    for r in rows:
        try:
            pid, ll = r[0][0][1], r[0][2][0]
            if official(pid):           # user uploads are not discovered (see official)
                out.append((pid, float(ll[2]), float(ll[3])))
        except (IndexError, TypeError, ValueError):
            continue
    return out


def tiles_around(lat: float, lon: float, max_d: float) -> list[tuple[int, int]]:
    """z17 tiles covering every point within max_d metres of (lat, lon); tiles get narrower towards the poles."""
    dlat = math.degrees(max_d / R)
    dlon = math.degrees(max_d / (R * max(math.cos(math.radians(lat)), 1e-6)))
    top, bottom = min(lat + dlat, 85.05), max(lat - dlat, -85.05)
    x0, y0 = (int(v // 256) for v in ll2px(17, top, lon - min(dlon, 180)))
    x1, y1 = (int(v // 256) for v in ll2px(17, bottom, lon + min(dlon, 180)))
    n = 2 ** 17
    xs = sorted({x % n for x in range(x0, x1 + 1)})
    return [(x, y) for x in xs for y in range(max(y0, 0), min(y1, n - 1) + 1)]


def panos_around(lat: float, lon: float, min_d: float, max_d: float, per: int, spacing: float,
                 proxy: str | None, cache: Path) -> list[tuple[str, float, float, float]]:
    """Up to `per` panoramas between min_d and max_d metres from (lat, lon), nearest first and at least `spacing` m apart:
    (id, lat, lon, distance). Raises ServiceError when a coverage lookup fails."""
    cands = []
    for tx, ty in tiles_around(lat, lon, max_d):
        for pid, la, lo in tile_panos(tx, ty, proxy, cache):
            d = haversine_m((lat, lon), (la, lo))
            if min_d <= d <= max_d:
                cands.append((d, pid, la, lo))
    picked: list[tuple[str, float, float, float]] = []
    for d, pid, la, lo in sorted(cands):
        if all(haversine_m((la, lo), (p[1], p[2])) >= spacing for p in picked):
            picked.append((pid, la, lo, d))
        if len(picked) >= per:
            break
    return picked
