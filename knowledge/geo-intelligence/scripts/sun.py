#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "tzdata"]
# ///
"""Sky geometry: sun position, shadows, satellite TV dishes.

Sun position uses the NOAA algorithm (Meeus), error about 0.01° for 1950–2050, with atmospheric refraction correction.
Azimuths are always compass bearings: 0=north, clockwise. Times can carry a time zone (--tz Asia/Shanghai); the default is UTC.

  pos     sun azimuth, elevation angle, shadow length of a 1 m object, and shadow bearing at a given place and time
  ratio   shadow ratio ↔ sun elevation angle conversion (object height 1, shadow length r)
  locate  known capture time + measured elevation angle (or shadow ratio) / shadow bearing → find the matching band within an area
  when    known place + elevation angle / shadow bearing → work back to which times of day (or which days in a date range) match
  dish    geostationary satellite dish pointing; given the dish azimuth it can also work back to longitude
  street  known place and date + angle between shadow and street → street orientation candidates (morning and afternoon listed separately)
  facing  which walls are lit and which are shaded → camera heading range (use when there is no measurable shadow)
  compass sun in the frame → camera heading, and the true bearing of any object in the frame (with no time given, split into sunrise and sunset groups)
  weather past weather for a point on a day / over a date range (cloud cover, sunshine, rain, snow): rank days to pick which one matches a sunny or snowy photo

Examples:
  sun.py pos --at 39.9042,116.4074 --time 2023-08-15T16:20 --tz Asia/Shanghai
  sun.py ratio --shadow 1.2
  sun.py locate --time 2023-08-15T16:20 --tz Asia/Shanghai --ratio 1.2 --tol 1.5 --bbox 34,110,42,122
  sun.py locate --time 2023-08-15T16:20 --tz Asia/Shanghai --elev 40 --shadow-bearing 60 --az-tol 10 \
                --bbox 34,110,42,122 --mosaic north.jpg --out band.jpg
  sun.py when --at 30.25,120.16 --date 2024-10-01 --tz Asia/Shanghai --ratio 1.2 --shadow-bearing 55
  sun.py when --at 30.25,120.16 --dates 2024-01-01:2024-12-31 --tz Asia/Shanghai --elev 40 --shadow-bearing 330
  sun.py dish --at 31.23,121.47 --sat 92.2
  sun.py dish --at 45.46,9.19 --sat hotbird           # --sat takes degrees east or a name from `dish --list`
  sun.py dish --lat 31.2 --sat 92.2 --azimuth 215     # dish faces 215°, work back to longitude
  sun.py dish --sat astra1 --azimuth 160 --elev 32 --points band.json   # azimuth + elevation angle → latitude/longitude band
  sun.py compass --at <lat,lon> --time 07:40 --dates 2024-09-01:2024-10-15 --tz <IANA time zone> --sun-x 1200 --width 4000 --hfov 60:70 --x 2900
  sun.py compass --at <lat,lon> --tz <IANA time zone> --sun-x 2600 --width 4032 --x 1500        # no time, no date: morning and evening groups over the whole year
  sun.py street --at 49.25,-123.10 --date 2025-04-01 --tz America/Vancouver --ratio 1.5 --tol 4 --shadow-rel 90
  sun.py weather --at 38.7223,-9.1393 --date 2024-07-16                      # hourly cloud/sun that day (was it sunny?)
  sun.py weather --at 38.7223,-9.1393 --dates 2024-07-01:2024-07-31          # rank the month's days, sunniest first
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

sys.path.insert(0, str(Path(__file__).parent))

# ---------------------------------------------------------------- Sun position

_D = math.degrees
_R = math.radians


def _sun_core(dt_utc: datetime) -> tuple[float, float]:
    """Returns (solar declination °, equation of time in minutes)."""
    jd = dt_utc.timestamp() / 86400 + 2440587.5
    t = (jd - 2451545) / 36525
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360
    m = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    c = (math.sin(_R(m)) * (1.914602 - t * (0.004817 + 0.000014 * t))
         + math.sin(_R(2 * m)) * (0.019993 - 0.000101 * t) + math.sin(_R(3 * m)) * 0.000289)
    app_long = l0 + c - 0.00569 - 0.00478 * math.sin(_R(125.04 - 1934.136 * t))
    obliq0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
    obliq = obliq0 + 0.00256 * math.cos(_R(125.04 - 1934.136 * t))
    decl = _D(math.asin(math.sin(_R(obliq)) * math.sin(_R(app_long))))
    y = math.tan(_R(obliq / 2)) ** 2
    eqt = 4 * _D(y * math.sin(2 * _R(l0)) - 2 * e * math.sin(_R(m))
                 + 4 * e * y * math.sin(_R(m)) * math.cos(2 * _R(l0))
                 - 0.5 * y * y * math.sin(4 * _R(l0)) - 1.25 * e * e * math.sin(2 * _R(m)))
    return decl, eqt


def _refraction(h: float) -> float:
    if h > 85:
        return 0.0
    te = math.tan(_R(h))
    if h > 5:
        r = 58.1 / te - 0.07 / te ** 3 + 0.000086 / te ** 5
    elif h > -0.575:
        r = 1735 + h * (-518.2 + h * (103.4 + h * (-12.79 + h * 0.711)))
    else:
        r = -20.772 / te
    return r / 3600


def sun_position(lat: float, lon: float, dt_utc: datetime, refraction: bool = True) -> tuple[float, float]:
    """(azimuth °, elevation angle °). dt_utc must carry the UTC time zone."""
    decl, eqt = _sun_core(dt_utc)
    minutes = dt_utc.hour * 60 + dt_utc.minute + dt_utc.second / 60 + dt_utc.microsecond / 6e7
    tst = (minutes + eqt + 4 * lon) % 1440
    ha = tst / 4 - 180                           # tst is reduced mod 1440 above, so the hour angle already lies in [-180, 180)
    cz = math.sin(_R(lat)) * math.sin(_R(decl)) + math.cos(_R(lat)) * math.cos(_R(decl)) * math.cos(_R(ha))
    zen = _D(math.acos(max(-1.0, min(1.0, cz))))
    elev = 90 - zen
    denom = math.cos(_R(lat)) * math.sin(_R(zen))
    if abs(denom) < 1e-9:
        az = 180.0
    else:
        ca = max(-1.0, min(1.0, (math.sin(_R(lat)) * math.cos(_R(zen)) - math.sin(_R(decl))) / denom))
        az = (_D(math.acos(ca)) + 180) % 360 if ha > 0 else (540 - _D(math.acos(ca))) % 360
    if refraction:
        elev += _refraction(elev)
    return az, elev


def subsolar_point(dt_utc: datetime) -> tuple[float, float]:
    """Subsolar point (lat, lon). At a given moment, the points with the same sun elevation angle form a circle centered on it with radius 90°-elevation angle."""
    decl, eqt = _sun_core(dt_utc)
    minutes = dt_utc.hour * 60 + dt_utc.minute + dt_utc.second / 60
    lon = -(minutes + eqt - 720) / 4
    return decl, (lon + 540) % 360 - 180


def shadow_ratio(elev: float) -> float:
    """Shadow length (m) of a 1 m vertical object on level ground."""
    return math.inf if elev <= 0 else 1 / math.tan(_R(elev))


def elev_from_ratio(ratio: float) -> float:
    return _D(math.atan(1 / ratio))


def _ang_diff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def _before_solar_noon(lon: float, dt_utc: datetime) -> bool:
    """True while the sun is east of the local meridian (hour angle < 0): splits morning/afternoon by solar noon,
    not by clock 12:00, which is wrong under DST or wide time zones and in either hemisphere."""
    _, eqt = _sun_core(dt_utc)
    minutes = dt_utc.hour * 60 + dt_utc.minute + dt_utc.second / 60
    return (minutes + eqt + 4 * lon) % 1440 < 720


# ---------------------------------------------------------------- Satellite dishes

_RE, _RGEO = 6378.137, 42164.0


def dish_pointing(lat: float, lon: float, sat_lon: float) -> tuple[float, float]:
    """Ground point (lat, lon) pointing at the geostationary satellite at longitude sat_lon: (azimuth °, elevation angle °)."""
    la, lo = _R(lat), _R(lon)
    gx, gy, gz = _RE * math.cos(la) * math.cos(lo), _RE * math.cos(la) * math.sin(lo), _RE * math.sin(la)
    sx, sy, sz = _RGEO * math.cos(_R(sat_lon)), _RGEO * math.sin(_R(sat_lon)), 0.0
    dx, dy, dz = sx - gx, sy - gy, sz - gz
    east = -math.sin(lo) * dx + math.cos(lo) * dy
    north = -math.sin(la) * math.cos(lo) * dx - math.sin(la) * math.sin(lo) * dy + math.cos(la) * dz
    up = math.cos(la) * math.cos(lo) * dx + math.cos(la) * math.sin(lo) * dy + math.sin(la) * dz
    return (_D(math.atan2(east, north)) + 360) % 360, _D(math.atan2(up, math.hypot(east, north)))


# Common satellites (longitude, east positive)
SATELLITES = {
    "chinasat9": (92.2, "ChinaSat-9 (中星9号): small dishes of China's 户户通/村村通 (rural direct-to-home) programs, the most common nationwide"),
    "chinasat6b": (115.5, "ChinaSat-6B: large dishes at cable TV headends and organizations"),
    "asiasat7": (105.5, "AsiaSat 7"),
    "apstar6c": (134.0, "APStar-6C"),
    "astra1": (19.2, "Astra 1: Germany, Austria and other Central Europe"),
    "hotbird": (13.0, "Hot Bird: Italy, Poland, etc."),
    "astra2": (28.2, "Astra 2: UK, Ireland"),
    "eutelsat5w": (-5.0, "Eutelsat 5W: France, parts of Spain"),
    "nilesat": (-7.0, "Nilesat: Middle East, North Africa"),
    "turksat": (42.0, "Türksat: Turkey"),
    "arabsat": (26.0, "Arabsat/Badr 26E: Arabian Peninsula, Levant, North Africa"),
    "yamal": (90.0, "Yamal 401 (90E): Russia, Central Asia"),
    "express": (53.0, "Express AM6 (53E): European Russia"),
}


def _sat(s: str) -> float:
    """--sat value: degrees east (negative = west) or a SATELLITES name, case-insensitive (hotbird, Astra1, chinasat-9)."""
    key = s.strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    if key in SATELLITES:
        return SATELLITES[key][0]
    try:
        return float(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{s!r} is neither a longitude nor a satellite name; see `dish --list`") from None


def _sat_text(sat_lon: float) -> str:
    ew = f"{abs(sat_lon):g}°{'E' if sat_lon >= 0 else 'W'}"
    names = [k for k, (lo, _) in SATELLITES.items() if abs(lo - sat_lon) < 1e-9]
    return f"{ew} ({names[0]})" if names else ew


# ---------------------------------------------------------------- Input parsing

def _pair(s: str) -> tuple[float, float]:
    a, b = s.split(",")
    return float(a), float(b)


def _zone(tz: str | None):
    """IANA zone or UTC; a typo exits with a readable message instead of a ZoneInfoNotFoundError traceback."""
    if not tz:
        return timezone.utc
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        sys.exit(f"Unknown time zone {tz!r}: use an IANA name such as Europe/Paris or Asia/Shanghai")


def _to_utc(s: str, tz: str | None) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_zone(tz))
    return dt.astimezone(timezone.utc)


def _target_elev(args) -> float | None:
    if getattr(args, "ratio", None) is not None:
        return elev_from_ratio(args.ratio)
    return getattr(args, "elev", None)


def _target_az(args) -> float | None:
    """Normalize to sun azimuth. Shadow bearing = sun azimuth + 180."""
    if getattr(args, "shadow_bearing", None) is not None:
        return (args.shadow_bearing + 180) % 360
    return getattr(args, "sun_azimuth", None)


# ---------------------------------------------------------------- Subcommands

def cmd_pos(args) -> None:
    lat, lon = args.at
    t = _to_utc(args.time, args.tz)
    az, el = sun_position(lat, lon, t)
    ss = subsolar_point(t)
    local = t.astimezone(_zone(args.tz))
    print(json.dumps({
        "utc": t.isoformat(timespec="minutes"), "sun_azimuth": round(az, 2), "sun_elevation": round(el, 2),
        "shadow_len_per_1m": None if el <= 0 else round(shadow_ratio(el), 3),
        "shadow_bearing": round((az + 180) % 360, 1), "subsolar_point": [round(ss[0], 3), round(ss[1], 3)],
        # the same moment in the two web tools, for the user's eyes: SunCalc draws the sun path and one object's shadow,
        # ShadeMap draws every terrain and building shadow on the map (terrain.py shade is the offline counterpart)
        "suncalc_url": f"https://www.suncalc.org/#/{lat:.5f},{lon:.5f},15/{local.strftime('%Y.%m.%d')}/{local.strftime('%H:%M')}/{args.object_height:g}/1",
        "shademap_url": f"https://shademap.app/@{lat:.5f},{lon:.5f},15z,{int(t.timestamp() * 1000)}t",
    }, ensure_ascii=False))


def cmd_ratio(args) -> None:
    if args.shadow is not None:
        print(f"Shadow ratio 1:{args.shadow} → sun elevation angle {elev_from_ratio(args.shadow):.2f}°")
    else:
        print(f"Sun elevation angle {args.elev}° → shadow length of a 1 m object {shadow_ratio(args.elev):.3f} m")


def _matches(lat, lon, times, tel, tol, taz, az_tol) -> bool:
    for t in times:
        az, el = sun_position(lat, lon, t)
        if tel is not None and abs(el - tel) > tol:
            continue
        if taz is not None and _ang_diff(az, taz) > az_tol:
            continue
        if el <= 0:
            continue
        return True
    return False


def cmd_locate(args) -> None:
    tel, taz = _target_elev(args), _target_az(args)
    if tel is None and taz is None:
        sys.exit("Need at least one of --elev / --ratio or --shadow-bearing / --sun-azimuth")
    t0 = _to_utc(args.time, args.tz)
    k = max(0, int(args.time_tol // 5))
    times = [t0 + timedelta(minutes=5 * i) for i in range(-k, k + 1)] if args.time_tol else [t0]
    s, w, n, e = args.bbox
    step = args.step
    pts = []
    lat = s
    while lat <= n + 1e-9:
        lon = w
        while lon <= e + 1e-9:
            if _matches(lat, lon, times, tel, args.tol, taz, args.az_tol):
                pts.append((round(lat, 4), round(lon, 4)))
            lon += step
        lat += step
    ss = subsolar_point(t0)
    out = {"utc": t0.isoformat(timespec="minutes"), "target_elev": None if tel is None else round(tel, 2),
           "target_sun_azimuth": None if taz is None else round(taz, 1), "subsolar_point": [round(ss[0], 3), round(ss[1], 3)],
           "equal_elev_circle_radius_km": None if tel is None else round((90 - tel) * 111.195, 0),
           "grid_step_deg": step, "matched_points": len(pts)}
    if pts:
        lats, lons = [p[0] for p in pts], [p[1] for p in pts]
        out["matched_bbox"] = [min(lats), min(lons), max(lats), max(lons)]
        cols: dict[float, list[float]] = {}
        for la, lo in pts:
            cols.setdefault(round(lo, 2), []).append(la)
        every = max(1, len(cols) // 12)
        out["lat_range_by_lon"] = {f"{lo:.2f}": [min(v), max(v)] for i, (lo, v) in enumerate(sorted(cols.items())) if i % every == 0}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if args.points:
        args.points.write_text(json.dumps({f"p{i}": list(p) for i, p in enumerate(pts)}, ensure_ascii=False), encoding="utf-8")
        print(f"points -> {args.points}")
    if args.mosaic:
        _draw(args.mosaic, pts, step, args.out or args.mosaic.with_name(args.mosaic.stem + "_sun.jpg"))
    elif args.out:
        print("--out needs --mosaic (base map from tiles.py fetch); nothing drawn. --points writes the raw cells.", file=sys.stderr)


def _draw(mosaic: Path, pts, step, out: Path) -> None:
    from PIL import Image, ImageDraw
    from tiles import Mosaic
    m = Mosaic(mosaic)
    im = Image.open(mosaic).convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for la, lo in pts:
        x0, y0 = m.to_px(la + step / 2, lo - step / 2)
        x1, y1 = m.to_px(la - step / 2, lo + step / 2)
        d.rectangle([x0, y0, x1, y1], fill=(255, 210, 0, 90))
    Image.alpha_composite(im, ov).convert("RGB").save(out, quality=88)
    print(f"map -> {out}")


def _scan_day(lat, lon, day: date, tz: ZoneInfo, tel, tol, taz, az_tol, step_min: int):
    """Returns the matching time windows in this day [(start, end, midpoint azimuth, midpoint elevation angle)]."""
    start = datetime(day.year, day.month, day.day, tzinfo=tz)
    wins, cur = [], None
    for i in range(0, 24 * 60, step_min):
        lt = start + timedelta(minutes=i)
        az, el = sun_position(lat, lon, lt.astimezone(timezone.utc))
        ok = el > 0 and (tel is None or abs(el - tel) <= tol) and (taz is None or _ang_diff(az, taz) <= az_tol)
        if ok:
            cur = [lt, lt, []] if cur is None else [cur[0], lt, cur[2]]
            cur[2].append((az, el))
        elif cur is not None:
            wins.append(cur)
            cur = None
    if cur is not None:
        wins.append(cur)
    res = []
    for a, b, vals in wins:
        az, el = vals[len(vals) // 2]
        res.append((a, b, az, el))
    return res


def cmd_when(args) -> None:
    tel, taz = _target_elev(args), _target_az(args)
    if tel is None and taz is None:
        sys.exit("Need at least one of --elev / --ratio or --shadow-bearing / --sun-azimuth")
    tz = _zone(args.tz)
    lat, lon = args.at
    if args.dates:
        a, b = (date.fromisoformat(x) for x in args.dates.split(":"))
        days = [a + timedelta(days=i) for i in range((b - a).days + 1)]
    else:
        days = [date.fromisoformat(args.date)]
    hits = 0
    for d in days:
        for s, e, az, el in _scan_day(lat, lon, d, tz, tel, args.tol, taz, args.az_tol, args.step_min):
            hits += 1
            mid = s + (e - s) / 2
            _, e1 = sun_position(lat, lon, (mid - timedelta(minutes=5)).astimezone(timezone.utc))
            _, e2 = sun_position(lat, lon, (mid + timedelta(minutes=5)).astimezone(timezone.utc))
            rate = abs(e2 - e1) / 10
            sens = f"  elevation angle changes {rate:.2f}° per minute, 1° off ≈ {1 / rate:.0f} minutes" if rate > 1e-3 else "  elevation angle barely changes around noon; time resolution is poor"
            print(f"{d} {s:%H:%M}–{e:%H:%M}  sun azimuth {az:5.1f}°  elevation {el:4.1f}°  shadow bearing {(az + 180) % 360:5.1f}°  "
                  f"shadow ratio 1:{shadow_ratio(el):.2f}{sens}")
    if not hits:
        print("No matching times (loosen --tol / --az-tol, or check whether the time zone or bearing is backwards)")


def cmd_dish(args) -> None:
    if args.list:
        for name, (lo, desc) in SATELLITES.items():
            print(f"{name:<11} {abs(lo):5.1f}°{'E' if lo >= 0 else 'W'}  {desc}")
        return
    sat = args.sat
    sat_txt = _sat_text(sat)
    if args.at:
        lat, lon = args.at
        az, el = dish_pointing(lat, lon, sat)
        print(f"Place {lat},{lon} pointing at the satellite at longitude {sat_txt}: azimuth {az:.1f}°, elevation angle {el:.1f}°")
        return
    if args.azimuth is None or (args.lat is None and args.elev is None):
        sys.exit("Forward calculation: give --at; working back: give --azimuth with --lat (→ longitude range) and/or --elev (→ latitude/longitude band)")
    el_txt = f", elevation angle {args.elev}±{args.el_tol}°" if args.elev is not None else ""

    def ok(az, el):
        return el > 0 and _ang_diff(az, args.azimuth) <= args.az_tol and (args.elev is None or abs(el - args.elev) <= args.el_tol)

    if args.lat is not None:
        best = [(i / 10, az, el) for i in range(-1800, 1801) for az, el in [dish_pointing(args.lat, i / 10, sat)] if ok(az, el)]
        if not best:
            print("No longitude at this latitude matches (the dish may point at a different satellite)")
            return
        print(f"Latitude {args.lat}, dish azimuth {args.azimuth}±{args.az_tol}°{el_txt} to the satellite at longitude {sat_txt} → longitude range {best[0][0]}° ~ {best[-1][0]}°, "
              f"elevation angle about {best[len(best) // 2][2]:.0f}°")
        pts = [(args.lat, lo) for lo, _, _ in best]
    else:
        # azimuth + elevation angle pin a patch: 0.5° grid over ±80° latitude
        pts = [(i / 2, j / 2) for i in range(-160, 161) for j in range(-360, 361) if ok(*dish_pointing(i / 2, j / 2, sat))]
        if not pts:
            print("No place matches this azimuth and elevation angle for that satellite (check the satellite, or loosen --az-tol / --el-tol)")
            return
        lats, lons = [p[0] for p in pts], [p[1] for p in pts]
        print(f"Dish azimuth {args.azimuth}±{args.az_tol}°{el_txt} to the satellite at longitude {sat_txt} → "
              f"latitude {min(lats)}° ~ {max(lats)}°, longitude {min(lons)}° ~ {max(lons)}° ({len(pts)} cells of 0.5°)")
        rows: dict[float, list[float]] = {}
        for la, lo in pts:
            rows.setdefault(la, []).append(lo)
        every = max(1, len(rows) // 12)
        for k, la in enumerate(sorted(rows)):
            if k % every == 0:
                print(f"  lat {la:6.1f}: lon {min(rows[la]):7.1f} ~ {max(rows[la]):7.1f}")
    if args.points:
        args.points.write_text(json.dumps({f"p{i}": [la, lo] for i, (la, lo) in enumerate(pts)}, ensure_ascii=False), encoding="utf-8")
        print(f"points -> {args.points}")


def cmd_facing(args) -> None:
    """Which walls are lit / shaded → camera heading range. A wall is lit ⟺ |sun azimuth − wall normal| < 90°.

    Walls are described by "which way they face in the frame": camera=faces the camera (normal = heading+180), left=faces frame left (heading−90),
    right=faces frame right (heading+90), away=faces away from the camera (normal = heading).
    """
    lat, lon = args.at
    t = _to_utc(args.time, args.tz)
    az, el = sun_position(lat, lon, t)
    if el <= 0:
        print(f"The sun is below the horizon at this time (elevation {el:.1f}°); the lit-face method doesn't apply")
        return
    offs = {"camera": 180.0, "left": -90.0, "right": 90.0, "away": 0.0}
    lit = [w for w in (args.lit or "").split(",") if w]
    shaded = [w for w in (args.shaded or "").split(",") if w]
    bad = [w for w in lit + shaded if w not in offs]
    if bad:
        sys.exit(f"Walls can only be camera/left/right/away, got: {bad}")
    ok = []
    for h in range(0, 360):
        good = True
        for w in lit:
            if _ang_diff(az, (h + offs[w]) % 360) >= 90 - args.margin:
                good = False
        for w in shaded:
            if _ang_diff(az, (h + offs[w]) % 360) <= 90 + args.margin:
                good = False
        if good:
            ok.append(h)
    print(f"Sun azimuth {az:.1f}°, elevation {el:.1f}° (shadow bearing {(az + 180) % 360:.1f}°)")
    if not ok:
        print("No heading satisfies all these lit/shaded conditions: check whether you misread which wall is lit, or whether the time / time zone is wrong (the photo may also be a composite)")
        return
    runs, start = [], ok[0]
    for a, b in zip(ok, ok[1:] + [None]):
        if b is None or b != a + 1:
            runs.append((start, a))
            start = b
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][1] == 359:      # merge across north
        runs = [(runs[-1][0] - 360, runs[0][1])] + runs[1:-1]
    print("Possible camera heading ranges: " + ", ".join(f"{a % 360}°–{b % 360}°" for a, b in runs))
    print("Tip: at the range edges the walls are nearly parallel to the sunlight and the light/dark difference is small; don't treat them as hard edges (--margin sets how conservative)")


def cmd_street(args) -> None:
    """Measure the angle in a top-down view: clockwise from the street direction to the shadow direction. If you can't tell clockwise from counterclockwise, list both (--both)."""
    tz = _zone(args.tz)
    lat, lon = args.at
    tel = _target_elev(args)
    day = date.fromisoformat(args.date)
    start = datetime(day.year, day.month, day.day, tzinfo=tz)
    rows = []
    for i in range(0, 24 * 60, args.step_min):
        lt = start + timedelta(minutes=i)
        az, el = sun_position(lat, lon, lt.astimezone(timezone.utc))
        if el <= 2 or (tel is not None and abs(el - tel) > args.tol):
            continue
        shadow = (az + 180) % 360
        cands = {round((shadow - args.shadow_rel) % 180)}
        if args.both:
            cands.add(round((shadow + args.shadow_rel) % 180))
        rows.append((lt, az, el, shadow, sorted(cands)))
    if not rows:
        print("No matching times (loosen the elevation angle tolerance, or check the date / time zone)")
        return
    step = max(1, len(rows) // 16)
    for k, (lt, az, el, shadow, cands) in enumerate(rows):
        if k % step and k != len(rows) - 1:
            continue
        half = "morning" if _before_solar_noon(lon, lt.astimezone(timezone.utc)) else "afternoon"
        print(f"{lt:%H:%M} {half}  sun {az:5.1f}°/{el:4.1f}°  shadow bearing {shadow:5.1f}°  → street orientation "
              + " or ".join(f"{c}°–{c + 180}°" for c in cands))
    print("Street orientation is given as 0–180° (47° means northeast–southwest). You must keep both the morning and the afternoon group, unless other evidence tells morning from afternoon.")



def _px_angle(x: float, width: float, hfov: float) -> float:
    """Horizontal angle (°, right positive) of pixel column x relative to the frame center."""
    f = (width / 2) / math.tan(math.radians(hfov) / 2)
    return math.degrees(math.atan((x - width / 2) / f))


def _arc(angles: list[float]) -> tuple[float, float]:
    """Smallest clockwise arc (start, end) covering all bearings; a set that straddles north gives (358, 2), not (2, 358)."""
    a = sorted(x % 360 for x in angles)
    gaps = [(a[i + 1] - a[i], i) for i in range(len(a) - 1)] + [(a[0] + 360 - a[-1], len(a) - 1)]
    _, i = max(gaps)
    return a[(i + 1) % len(a)], a[i]


def cmd_compass(args) -> None:
    """Sun in the frame → camera heading, and the true bearing of any pixel column in the frame (tower, chimney, intersection).

    Time given: use the sun azimuth at that moment directly (if the date is uncertain, give a range with --dates and the bearing becomes a range too).
    No time given: compute the morning and evening stretches of each day in --dates where the sun elevation is between 0 and --elev-max separately; list both the sunrise and the sunset group.
    """
    lat, lon = args.at
    tz = _zone(args.tz)
    if args.dates:
        a, b = (date.fromisoformat(x) for x in args.dates.split(":"))
    elif args.time and "T" in args.time:
        a = b = datetime.fromisoformat(args.time).date()
    else:
        a, b = date(2025, 1, 1), date(2025, 12, 31)
        print("No date given: computing over the whole year. Posting time is not capture time; when phenology, clothing or snow can pin down the season, narrow it with --dates")
    groups: dict[str, list[float]] = {}
    lo_el, hi_el = (float(x) for x in args.elev.split(":")) if args.elev else (None, None)
    dropped: list[date] = []
    d = a
    while d <= b:
        if args.time:
            hh, mm = (args.time.split("T")[-1].split(":") + ["0"])[:2]
            lt = datetime(d.year, d.month, d.day, int(hh), int(mm), tzinfo=tz)
            az, el = sun_position(lat, lon, lt.astimezone(timezone.utc))
            if (el > -1 if lo_el is None else lo_el <= el <= hi_el):
                groups.setdefault(f"{int(hh):02d}:{int(mm):02d}", []).append(az)
            elif lo_el is not None:
                dropped.append(d)
        else:
            start = datetime(d.year, d.month, d.day, tzinfo=tz)
            for i in range(0, 24 * 60, 4):
                ut = (start + timedelta(minutes=i)).astimezone(timezone.utc)
                az, el = sun_position(lat, lon, ut)
                if (0 < el <= args.elev_max) if lo_el is None else (lo_el <= el <= hi_el):
                    groups.setdefault("morning (sunrise side)" if _before_solar_noon(lon, ut) else "evening (sunset side)", []).append(az)
        d += timedelta(days=max(1, args.step_days))
    if dropped:
        runs, s0 = [], dropped[0]
        for x, y in zip(dropped, dropped[1:] + [None]):
            if y is None or (y - x).days > max(1, args.step_days):
                runs.append((s0, x))
                s0 = y
        print("Dates excluded because the sun elevation is outside --elev: " + ", ".join(f"{p:%m-%d}–{q:%m-%d}" for p, q in runs))
    if not groups:
        print("No matching sun position on these dates (sun below the horizon, or --elev / --elev-max too narrow)")
        return
    h0, h1 = (float(x) for x in args.hfov.split(":"))
    xs = [float(v) for s in (args.x or []) for v in s.split(",")]
    offs = [_px_angle(args.sun_x, args.width, hf) for hf in (h0, h1)]
    for name, azs in groups.items():
        # clockwise arcs throughout: heading = sun azimuth − sun offset, so the arc shifts by the offset range and
        # still reads clockwise when it crosses north (southern-hemisphere noon, polar sunrise)
        lo, hi = _arc(azs)
        print(f"{name}: sun azimuth {lo:.1f}°–{hi:.1f}°; sun at frame x={args.sun_x:.0f} (offset from center "
              f"{offs[0]:+.1f}° to {offs[1]:+.1f}°)"
              f" → camera heading about {(lo - max(offs)) % 360:.0f}°–{(hi - min(offs)) % 360:.0f}°")
        for x in xs:
            rels = [_px_angle(x, args.width, hf) - off for hf, off in zip((h0, h1), offs)]
            print(f"    object at x={x:.0f}: bearing about {(lo + min(rels)) % 360:.0f}°–{(hi + max(rels)) % 360:.0f}° "
                  f"(relative to the sun {rels[0]:+.1f}° to {rels[1]:+.1f}°)")
    print("When a range crosses north (e.g. 350°–10°), read it clockwise. If the field of view is uncertain, widen --hfov; when the sunrise and sunset groups can't be told apart, you must build top-down templates for both headings.")


_WMO = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "rime fog",
        51: "light drizzle", 53: "drizzle", 55: "dense drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
        71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains", 80: "light showers", 81: "showers",
        82: "violent showers", 85: "snow showers", 86: "heavy snow showers", 95: "thunderstorm",
        96: "thunderstorm + hail", 99: "thunderstorm + heavy hail"}


def cmd_weather(args) -> None:
    """Past weather for a point on a day or over a date range (ERA5 reanalysis via Open-Meteo, ~9 km, hourly, 1940→~5 days ago).

    Rank the days of a range by how sunny or overcast they were to pick which day a photo was taken,
    or read the cloud cover and precipitation at the capture hour. Pair with a GIBS daily image (tiles.py --source gibs:DATE)
    to match the actual cloud pattern. The image still has the final say; weather only ranks candidate days.
    """
    from urllib.parse import urlencode
    from geolib import net as _net
    lat, lon = args.at
    if args.dates:
        start, end = args.dates.split(":")
    else:
        start = end = args.date
    hourly = ["cloud_cover", "cloud_cover_low", "sunshine_duration", "precipitation", "snowfall", "weather_code", "temperature_2m"]
    q = urlencode({"latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}", "start_date": start, "end_date": end,
                   "hourly": ",".join(hourly), "timezone": args.tz or "auto"})
    url = f"https://archive-api.open-meteo.com/v1/archive?{q}"
    try:
        data = json.loads(_net.fetch_bytes(url, args.proxy, timeout=30))
    except Exception as e:                                                      # noqa: BLE001
        raise SystemExit(f"Open-Meteo request failed ({e}). The archive lags ~5 days; for the last few days use the "
                         "forecast API's past_days, and note recent dates may be missing.")
    if "hourly" not in data or not data["hourly"].get("time"):
        raise SystemExit(f"No data for {start}..{end} at {lat},{lon} (archive lags ~5 days; recent dates may be missing).")
    H = data["hourly"]
    tz = data.get("timezone", "UTC")
    rows = list(zip(H["time"], H["cloud_cover"], H["cloud_cover_low"], H["sunshine_duration"],
                    H["precipitation"], H["snowfall"], H["weather_code"], H["temperature_2m"]))
    by_day: dict[str, list] = {}
    for r in rows:
        by_day.setdefault(r[0][:10], []).append(r)

    def num(v):
        return v if isinstance(v, (int, float)) else None

    if not args.dates:                                                          # one day: hourly table
        lo, hi = (int(x) for x in args.hours.split(":")) if args.hours else (6, 20)
        print(f"{args.date} at {lat},{lon}  (times {tz}; ERA5 reanalysis)\n"
              f"{'hour':5} {'cloud%':>6} {'low%':>5} {'sun min':>7} {'rain mm':>7} {'snow cm':>7} {'°C':>5}  code")
        day = 0.0
        for t, cc, ccl, sun, rain, snow, wc, temp in by_day.get(args.date, []):
            hh = int(t[11:13])
            if not lo <= hh <= hi:
                continue
            s = num(sun)
            day += (s or 0) / 60
            print(f"{t[11:16]:5} {num(cc) if num(cc) is not None else '-':>6} {num(ccl) if num(ccl) is not None else '-':>5} "
                  f"{(s or 0)/60:7.0f} {num(rain) if num(rain) is not None else '-':>7} "
                  f"{(num(snow) or 0):7.1f} {num(temp) if num(temp) is not None else '-':>5}  {_WMO.get(wc, wc)}")
        ccs = [num(r[1]) for r in by_day.get(args.date, []) if lo <= int(r[0][11:13]) <= hi and num(r[1]) is not None]
        print(f"\n{lo}:00–{hi}:00 mean cloud {sum(ccs)/len(ccs):.0f}%  total sunshine {day:.0f} min" if ccs else "\n(no data in window)")
        return

    summ = []                                                                   # range: rank days by a daytime window
    lo, hi = (int(x) for x in args.hours.split(":")) if args.hours else (9, 16)
    for d, rs in sorted(by_day.items()):
        win = [r for r in rs if lo <= int(r[0][11:13]) <= hi]
        ccs = [num(r[1]) for r in win if num(r[1]) is not None]
        sun = sum((num(r[3]) or 0) for r in win) / 60
        rain = sum((num(r[4]) or 0) for r in win)
        snow = sum((num(r[5]) or 0) for r in win)
        codes = [r[6] for r in win if r[6] is not None]
        summ.append((d, (sum(ccs) / len(ccs)) if ccs else None, sun, rain, snow,
                     max(set(codes), key=codes.count) if codes else None))
    summ.sort(key=lambda r: (r[1] if r[1] is not None else 999))                # sunniest (lowest cloud) first
    print(f"{start}..{end} at {lat},{lon}  ({lo}:00–{hi}:00 {tz}; sunniest first; ERA5)\n"
          f"{'date':12} {'cloud%':>6} {'sun min':>7} {'rain mm':>7} {'snow cm':>7}  code")
    for d, cc, sun, rain, snow, wc in summ:
        dow = date.fromisoformat(d).strftime("%a")
        ccs = f"{cc:.0f}" if cc is not None else "-"
        print(f"{d} {dow} {ccs:>5}  {sun:7.0f} {rain:7.1f} {snow:7.1f}  {_WMO.get(wc, wc)}")


from geolib.cli import neg_coords as _neg_coords  # noqa: E402  (shared helper)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pos", help="sun position at a given place and time")
    p.add_argument("--at", type=_pair, required=True, help="lat,lon")
    p.add_argument("--time", required=True, help="2024-06-06T15:39, may include +08:00")
    p.add_argument("--tz", help="IANA time zone, e.g. Asia/Shanghai, Europe/Berlin")
    p.add_argument("--object-height", type=float, default=1.0, help="object height m for the shadow drawn in the SunCalc link (default 1)")

    r = sub.add_parser("ratio", help="shadow ratio ↔ elevation angle")
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--shadow", type=float, help="shadow length for an object of height 1")
    g.add_argument("--elev", type=float)

    def targets(sp):
        sp.add_argument("--elev", type=float, help="sun elevation angle °")
        sp.add_argument("--ratio", type=float, help="shadow ratio (shadow length for an object of height 1); either this or --elev")
        sp.add_argument("--tol", type=float, default=2.0, help="elevation angle tolerance °, default 2")
        sp.add_argument("--shadow-bearing", type=float, help="compass bearing ° the shadow points to (from the object to the shadow tip)")
        sp.add_argument("--sun-azimuth", type=float, help="sun azimuth °; either this or --shadow-bearing")
        sp.add_argument("--az-tol", type=float, default=10.0, help="azimuth tolerance °, default 10")
        sp.add_argument("--tz")

    lo = sub.add_parser("locate", help="known time → find the band that matches the sun conditions")
    lo.add_argument("--time", required=True)
    targets(lo)
    lo.add_argument("--time-tol", type=float, default=0, help="uncertainty of the capture time in minutes (±)")
    lo.add_argument("--bbox", type=lambda s: tuple(map(float, s.split(","))), required=True, help="south,west,north,east")
    lo.add_argument("--step", type=float, default=0.1, help="grid step °, default 0.1 (about 11 km)")
    lo.add_argument("--points", type=Path, help="write matching points as {name:[lat,lon]}, for tiles.py mark")
    lo.add_argument("--mosaic", type=Path, help="base map from tiles.py fetch; the matching band is drawn on it")
    lo.add_argument("--out", type=Path)

    w = sub.add_parser("when", help="known place → work back to capture time / date")
    w.add_argument("--at", type=_pair, required=True)
    dg = w.add_mutually_exclusive_group(required=True)
    dg.add_argument("--date", help="single day 2024-10-01")
    dg.add_argument("--dates", help="date range 2024-01-01:2024-12-31")
    targets(w)
    w.add_argument("--step-min", type=int, default=2)

    d = sub.add_parser("dish", help="satellite dish pointing / work back to longitude from the pointing")
    d.add_argument("--sat", type=_sat, default=92.2, help="satellite: degrees east (negative = west) or a name from --list (hotbird, astra1, chinasat9…); default ChinaSat-9 92.2")
    d.add_argument("--list", action="store_true", help="print the satellite table and exit")
    d.add_argument("--at", type=_pair, help="lat,lon: forward calculation")
    d.add_argument("--lat", type=float, help="work back: known latitude")
    d.add_argument("--azimuth", type=float, help="work back: dish azimuth")
    d.add_argument("--elev", type=float, help="work back: dish elevation angle ° above the horizon; with --azimuth alone → latitude/longitude band, with --lat → narrower longitude range")
    d.add_argument("--az-tol", type=float, default=5.0)
    d.add_argument("--el-tol", type=float, default=3.0, help="elevation angle tolerance °, default 3")
    d.add_argument("--points", type=Path, help="write the matching band as {name:[lat,lon]} for tiles.py mark")

    st = sub.add_parser("street", help="angle between shadow and street → street orientation candidates")
    st.add_argument("--at", type=_pair, required=True, help="any point in the city, lat,lon")
    st.add_argument("--date", required=True)
    st.add_argument("--shadow-rel", type=float, required=True, help="angle in a top-down view, clockwise from the street direction to the shadow direction; 90 if the shadow is perpendicular to the street")
    st.add_argument("--both", action="store_true", help="list both when you can't tell clockwise from counterclockwise")
    st.add_argument("--elev", type=float, help="measured sun elevation angle, used to keep only the matching times")
    st.add_argument("--ratio", type=float, help="shadow ratio; either this or --elev")
    st.add_argument("--tol", type=float, default=3.0)
    st.add_argument("--tz")
    st.add_argument("--step-min", type=int, default=10)

    fc = sub.add_parser("facing", help="which walls are lit → camera heading range")
    fc.add_argument("--at", type=_pair, required=True)
    fc.add_argument("--time", required=True)
    fc.add_argument("--tz")
    fc.add_argument("--lit", help="lit walls, comma-separated: camera,left,right,away")
    fc.add_argument("--shaded", help="shaded walls, same format")
    fc.add_argument("--margin", type=float, default=5, help="edge margin °, default 5")

    cp = sub.add_parser("compass", help="sun in the frame → camera heading, bearings of objects in the frame (lists sunrise and sunset groups when there is no time)")
    cp.add_argument("--at", type=_pair, required=True, help="any point in the candidate region, lat,lon")
    cp.add_argument("--time", help="clock time 07:40, or full 2024-09-20T07:40; if omitted, computes morning and evening groups for a low sun")
    cp.add_argument("--dates", help="date range 2024-09-01:2024-10-15; if omitted, uses the whole year")
    cp.add_argument("--step-days", type=int, default=3)
    cp.add_argument("--tz")
    cp.add_argument("--elev-max", type=float, default=12, help="when no time is given: upper limit of sun elevation ° (use 5–12 when the sun in the frame is close to the horizon)")
    cp.add_argument("--elev", help="sun elevation range ° lo:hi (estimate from how high the sun is above the horizon / tree line in the frame): with a time given, drops dates whose elevation doesn't fit; with no time, replaces 0–--elev-max")
    cp.add_argument("--sun-x", type=float, required=True, help="pixel column of the sun in the frame")
    cp.add_argument("--width", type=float, required=True, help="frame width (pixels)")
    cp.add_argument("--hfov", default="55:75", help="horizontal field of view range °; phone main camera about 65–75 in landscape, about 50–60 in portrait, narrower for crops / zoom")
    cp.add_argument("--x", action="append", help="pixel columns of objects to compute bearings for, comma-separated or repeated")

    we = sub.add_parser("weather", help="past weather for a point: hourly on a day, or rank the days of a range (sunny/overcast/snow)")
    we.add_argument("--at", type=_pair, required=True, help="lat,lon")
    wg = we.add_mutually_exclusive_group(required=True)
    wg.add_argument("--date", help="single day 2024-07-16")
    wg.add_argument("--dates", help="date range 2024-07-01:2024-07-31")
    we.add_argument("--hours", help="local hour window lo:hi (default 6:20 for a day, 9:16 for a range)")
    we.add_argument("--tz", help="IANA time zone; default auto (resolved from the point)")
    we.add_argument("--proxy", help="proxy URL or 'direct' (default: $GEO_PROXY)")

    args = ap.parse_args(_neg_coords(sys.argv[1:]))
    {"pos": cmd_pos, "ratio": cmd_ratio, "locate": cmd_locate, "when": cmd_when, "dish": cmd_dish,
     "street": cmd_street, "facing": cmd_facing, "compass": cmd_compass, "weather": cmd_weather}[args.cmd](args)


if __name__ == "__main__":
    # Chinese Windows outputs GBK by default: it crashes on m² or ñ, and the Chinese the agent reads is garbled
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
