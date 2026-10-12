"""Spherical-earth helpers shared by the scripts: distance, bearing, destination point, Web Mercator pixels and tiles.
Points are (lat, lon) in degrees (WGS84); distances in metres; bearings are compass degrees (0 = north, clockwise)."""
from __future__ import annotations

import math

R = 6371008.8           # mean Earth radius (m)


def haversine_m(p: tuple[float, float], q: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*p[:2], *q[:2]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))


def bearing(p: tuple[float, float], q: tuple[float, float]) -> float:
    """Compass bearing from p looking at q."""
    la1, lo1, la2, lo2 = map(math.radians, (*p[:2], *q[:2]))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def dest(p: tuple[float, float], brg: float, dist_m: float) -> tuple[float, float]:
    """Point reached from p after dist_m metres on bearing brg (great circle)."""
    la1, lo1 = map(math.radians, p[:2])
    b = math.radians(brg)
    d = dist_m / R
    la2 = math.asin(math.sin(la1) * math.cos(d) + math.cos(la1) * math.sin(d) * math.cos(b))
    lo2 = lo1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(la1), math.cos(d) - math.sin(la1) * math.sin(la2))
    return math.degrees(la2), math.degrees(lo2)


def ll2px(zoom: int, lat: float, lon: float) -> tuple[float, float]:
    """lat/lon -> global pixel coordinates at this zoom level (256 px tiles)."""
    n = 256 * 2 ** zoom
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def px2ll(zoom: int, x: float, y: float) -> tuple[float, float]:
    n = 256 * 2 ** zoom
    lon = x / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def tile_xy(lat: float, lon: float, z: int = 17) -> tuple[int, int]:
    """Web Mercator tile (x, y) containing the point at zoom z."""
    x, y = ll2px(z, lat, lon)
    return int(x // 256), int(y // 256)


def meters_per_px(zoom: int, lat: float) -> float:
    """Ground size of one Web Mercator pixel at this zoom and latitude (256 px tiles)."""
    return 156543.03392 * math.cos(math.radians(lat)) / 2 ** zoom
