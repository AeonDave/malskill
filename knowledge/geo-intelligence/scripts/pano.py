#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["streetlevel", "numpy", "pillow", "pillow-heif", "requests"]
# ///
"""Street-level imagery from every source we can reach, in one format: find what covers a place, list it into a
manifest, render any direction, build sheets. sweep.py then ranks a whole city of it against the photo.

Providers (no keys unless noted; `providers` prints this with coverage notes):
  google      Google Street View, official car/trekker imagery (coverage tiles)        worldwide where covered
  apple       Apple Look Around (coverage tiles; HEIC faces via pillow-heif)            ~20 countries, mostly cities
  bing        Bing Streetside (Microsoft/TomTom)                                        US, parts of Europe
  yandex      Yandex Panoramas                                                          Russia, CIS, Turkey, some others
  naver, kakao  Korean panoramas (Naver Map, Kakao Map)                                 South Korea
  mapy        Mapy.com (Seznam) panoramas                                               Czechia, Slovakia, parts of Europe
  ja          Já.is 360                                                                 Iceland
  baidu       use baidu_pano.py                                                         mainland China
  kartaview   KartaView (ex-OpenStreetCam) crowd-sourced photos                          patchy, worldwide
  panoramax   Panoramax federated open street imagery (STAC API)                        France first, growing elsewhere
  mapillary   Mapillary crowd-sourced imagery — needs MAPILLARY_TOKEN (free account)    worldwide, patchy
  manifest    anything else you find: write a manifest yourself (_pano.py, references/streetlevel.md §3) —
              national, local or historical panorama sites found by web search (e.g. a city's 360 archive),
              a viewer's scene index, a folder of photos

Examples:
  pano.py providers
  pano.py coverage 41.0082,28.9784 --radius 400                 # who has imagery here? (counts, nearest, dates)
  pano.py list --provider yandex --near 41.0082,28.9784 --radius 3000 --spacing 40 --out town.jsonl
  pano.py list --provider apple --bbox 48.85,2.28,48.87,2.31 --out paris_apple.jsonl
  pano.py list --provider yandex --bbox … --spacing 40 --out m.jsonl        # point-lookup providers sample a grid
  pano.py render --manifest town.jsonl --id <id> --bearing 14 --pitch -9 --fov 96 --out v.jpg
  pano.py sheet --manifest m.jsonl --ids a,b,c --bearings 0,90,180,270 --out s.jpg
  pano.py sheet --manifest m.jsonl --near 41.0082,28.9784 --radius 60 --toward 41.0086,28.9790 --out s.jpg
Then: sweep.py index --manifest town.jsonl && sweep.py rank --index town --query original/photo.jpg
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geolib import pano as P  # noqa: E402  (importing it bounds every requests timeout to P.HTTP_TIMEOUT_S)
from geolib.net import model_proxy_env, request  # noqa: E402

UA = P.UA
PROVIDERS = {
    "google": "Google Street View official imagery (car, trekker); worldwide where covered; dates and history via gsv.py near",
    "apple": "Apple Look Around; US, Canada, Japan, Australia, NZ and ~15 European countries, mostly cities",
    "bing": "Bing Streetside; US and parts of Europe (Microsoft + TomTom captures)",
    "yandex": "Yandex Panoramas; Russia, Belarus, Kazakhstan, Ukraine (old), Turkey, Serbia, Uzbekistan and more",
    "naver": "Naver Map street view; South Korea",
    "kakao": "Kakao Map road view; South Korea, captures back to ~2009",
    "mapy": "Mapy.com panoramas; Czechia, Slovakia, and parts of Germany, Austria, Poland, Croatia…",
    "ja": "Já.is 360; Iceland",
    "kartaview": "KartaView crowd-sourced dashcam photos; patchy worldwide, often 2015–2020",
    "panoramax": "Panoramax open federated street imagery (CC-BY-SA); France, growing in Europe and Africa",
    "mapillary": "Mapillary crowd-sourced photos and 360s; worldwide, patchy — set MAPILLARY_TOKEN (free account)",
}


from geolib.geomath import bearing, haversine_m as dist_m  # noqa: E402,F401  (shared helpers)


def bbox_around(lat: float, lon: float, r: float) -> tuple[float, float, float, float]:
    dlat = r / 110540.0
    dlon = r / (111320.0 * max(math.cos(math.radians(lat)), 0.05))
    return lat - dlat, lon - dlon, lat + dlat, lon + dlon


def in_bbox(lat, lon, bb) -> bool:
    return bb[0] <= lat <= bb[2] and bb[1] <= lon <= bb[3]


def grid(bb, spacing: float) -> list[tuple[float, float]]:
    s, w, n, e = bb
    lat_step = spacing / 110540.0
    pts = []
    la = s + lat_step / 2
    while la <= n:
        lon_step = spacing / (111320.0 * max(math.cos(math.radians(la)), 0.05))
        lo = w + lon_step / 2
        while lo <= e:
            pts.append((la, lo))
            lo += lon_step
        la += lat_step
    return pts or [((s + n) / 2, (w + e) / 2)]


def http_json(url: str, data: dict | None = None, timeout: int = 40, proxy: str | None = None):
    """GET (or form POST) JSON; proxy None = GEO_PROXY. Transport failures and non-2xx replies both raise."""
    code, _, body = request(url, proxy, timeout, {"User-Agent": UA}, form=data)
    if not 200 <= code < 300:
        raise RuntimeError(f"HTTP {code} {url}")
    return json.loads(body.decode("utf-8", "replace"))


def tiles17(bb) -> list[tuple[int, int]]:
    from geolib import streetlevel as SL
    x0, y1 = SL.tile_xy(bb[0], bb[1])
    x1, y0 = SL.tile_xy(bb[2], bb[3])
    return [(x, y) for x in range(min(x0, x1), max(x0, x1) + 1) for y in range(min(y0, y1), max(y0, y1) + 1)]


def _date(d) -> str:
    if d is None:
        return ""
    if hasattr(d, "year") and getattr(d, "month", None):
        return f"{d.year}-{int(d.month):02d}" + (f"-{int(d.day):02d}" if getattr(d, "day", None) else "")
    return str(d)[:10]


# ---------------------------------------------------------------- providers: bbox -> manifest entries

def list_google(bb, spacing, limit) -> list[dict]:
    from geolib import streetlevel as SL
    sv = SL.streetview()
    ts = tiles17(bb)
    if len(ts) > 900:
        raise SystemExit(f"bbox covers {len(ts)} map tiles; use a smaller area (≤ ~9 km across)")
    found = {}

    def one(t):
        try:
            return sv.get_coverage_tile(*t) or []
        except Exception:  # noqa: BLE001
            return []
    with ThreadPoolExecutor(12) as ex:
        for panos in ex.map(one, ts):
            for p in panos:
                if SL.official(p.id) and in_bbox(p.lat, p.lon, bb):
                    found[p.id] = p
    rows = []
    for pid, p in found.items():
        rows.append({"provider": "google", "id": pid, "lat": p.lat, "lon": p.lon,
                     "heading": round(math.degrees(p.heading) % 360, 1) if getattr(p, "heading", None) is not None else None,
                     "date": _date(getattr(p, "date", None)),
                     "link": f"https://www.google.com/maps/@?api=1&map_action=pano&pano={pid}",
                     "low": {"kind": "streetlevel", "service": "google", "pano": pid, "zoom": 1},
                     "high": {"kind": "streetlevel", "service": "google", "pano": pid, "zoom": 3}})
    return rows


def list_apple(bb, spacing, limit) -> list[dict]:
    la = P._sl("lookaround")
    ts = tiles17(bb)
    if len(ts) > 900:
        raise SystemExit(f"bbox covers {len(ts)} map tiles; use a smaller area")
    rows = {}

    def one(t):
        try:
            return la.get_coverage_tile(*t).panos
        except Exception:  # noqa: BLE001
            return []
    with ThreadPoolExecutor(8) as ex:
        for panos in ex.map(one, ts):
            for p in panos:
                if in_bbox(p.lat, p.lon, bb):
                    hdg = (-math.degrees(p.heading)) % 360   # Look Around headings run counter-clockwise
                    rows[str(p.id)] = {"provider": "apple", "id": str(p.id), "lat": p.lat, "lon": p.lon, "heading": round(hdg, 1),
                                       "date": _date(getattr(p, "date", None)),
                                       "link": f"https://maps.apple.com/?ll={p.lat},{p.lon}",
                                       "low": {"kind": "streetlevel", "service": "apple", "pano": str(p.id), "build": p.build_id, "zoom": 5},
                                       "high": {"kind": "streetlevel", "service": "apple", "pano": str(p.id), "build": p.build_id, "zoom": 3}}
    return list(rows.values())


def list_bing(bb, spacing, limit) -> list[dict]:
    ss = P._sl("streetside")
    rows = {}
    cell = 0.004
    s, w, n, e = bb
    cells = []
    la = s
    while la < n:
        lo = w
        while lo < e:
            cells.append((min(la + cell, n), lo, la, min(lo + cell, e)))
            lo += cell
        la += cell

    def one(c):
        try:
            return ss.find_panoramas_in_bbox(*c, limit=1000) or []
        except Exception:  # noqa: BLE001
            return []
    with ThreadPoolExecutor(8) as ex:
        for panos in ex.map(one, cells):
            for p in panos:
                rows[str(p.id)] = {"provider": "bing", "id": str(p.id), "lat": p.lat, "lon": p.lon,
                                   "heading": round(math.degrees(p.heading or 0) % 360, 1), "date": _date(p.date),
                                   "link": f"https://www.bing.com/maps?cp={p.lat}~{p.lon}&lvl=19&style=x",
                                   "low": {"kind": "streetlevel", "service": "bing", "pano": str(p.id), "zoom": 1},
                                   "high": {"kind": "streetlevel", "service": "bing", "pano": str(p.id), "zoom": 3}}
    return list(rows.values())


# (low, high) zoom per service: the scales differ (Yandex and Já count down from the largest size, the others up)
ZOOMS = {"yandex": (3, 1), "naver": (0, 2), "kakao": (0, 2), "mapy": (0, 2), "ja": (1, 0)}
LOOKUP_CAP = 4000           # grid points per point-lookup listing
LOOKUPS_PER_S = 1.5         # planning rate for the first estimate (3 threads); the progress lines print the measured one
PROGRESS_S = 30             # seconds between progress lines


def _dur(s: float) -> str:
    return f"{s:.0f} s" if s < 90 else f"{s / 60:.0f} min" if s < 5400 else f"{s / 3600:.1f} h"


def _cap_refusal(service: str, bb, spacing: float, n: int) -> str:
    """Why a listing is refused, and what fits under LOOKUP_CAP: the finest spacing for this area, the widest area at this spacing."""
    fit = max(1, math.floor(spacing * math.sqrt(n / LOOKUP_CAP)))
    while len(grid(bb, fit)) > LOOKUP_CAP:
        fit += 1
    mid = ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
    r = int(spacing * math.sqrt(LOOKUP_CAP) / 2 // 10 * 10)
    while r > 10 and len(grid(bbox_around(*mid, r), spacing)) > LOOKUP_CAP:
        r -= 10
    return (f"{service}: {n} lookups at {spacing:g} m spacing would take ~{_dur(n / LOOKUPS_PER_S)}; the cap is {LOOKUP_CAP} "
            f"(~{_dur(LOOKUP_CAP / LOOKUPS_PER_S)}). Fits: --spacing {fit} for this area, or --near <lat,lon> --radius {r} "
            f"at {spacing:g} m")


def _point_lookup(service: str, bb, spacing, limit, sink=None) -> list[dict]:
    """Providers that only answer 'nearest panorama to a point': sample a grid and keep distinct panoramas. sink (_Partial)
    gets each lookup's new rows as they arrive, so a killed run keeps them."""
    mod = P._sl(service)
    pts = grid(bb, spacing)
    if len(pts) > LOOKUP_CAP:
        raise SystemExit(_cap_refusal(service, bb, spacing, len(pts)))
    print(f"{service}: {len(pts)} lookups at {spacing:g} m spacing, ~{_dur(len(pts) / LOOKUPS_PER_S)} at ~{LOOKUPS_PER_S:g} lookups/s"
          + (f"; rows go to {sink.path} as they arrive (a killed run keeps them there, part of the area only; the manifest is "
             "written when the listing ends)" if sink else ""), file=sys.stderr, flush=True)

    errors = [0]

    def one(pt):
        if errors[0] >= 12:                # the service is refusing us (rate limit / block): stop asking
            return []
        try:
            time.sleep(0.15)
            if service == "kakao":
                return mod.find_panoramas(pt[0], pt[1], radius=max(20, int(spacing)), limit=20) or []
            if service == "ja":
                p = mod.find_panorama(pt[0], pt[1], radius=max(20, int(spacing)))
            else:
                p = mod.find_panorama(pt[0], pt[1])
            return [p] if p else []
        except Exception:  # noqa: BLE001
            errors[0] += 1
            return []
    rows = {}
    t0 = last = time.monotonic()
    with ThreadPoolExecutor(3) as ex:          # point lookups are throttled: Já.is blocks bursts with HTTP 403
        for done, panos in enumerate(ex.map(one, pts), 1):
            new = []
            for p in panos:
                if not in_bbox(p.lat, p.lon, bb) or str(p.id) in rows:
                    continue
                h = math.degrees(p.heading or 0)
                if service == "yandex":           # Yandex: 0 = south, 90 = west
                    h = h + 180
                center = 0.0 if service == "mapy" else h  # Mapy shifts every panorama so north is in the middle
                if service == "kakao":            # Kakao angle = travel direction; the stitched image's middle looks back
                    center = h + 180
                zlow, zhigh = ZOOMS[service]
                rows[str(p.id)] = {"provider": service, "id": str(p.id), "lat": p.lat, "lon": p.lon, "heading": round(h % 360, 1),
                                   "date": _date(getattr(p, "date", None)),
                                   "low": {"kind": "streetlevel", "service": service, "pano": str(p.id), "zoom": zlow, "center": round(center % 360, 2)},
                                   "high": {"kind": "streetlevel", "service": service, "pano": str(p.id), "zoom": zhigh, "center": round(center % 360, 2)}}
                if service == "kakao" and getattr(p, "image_path", None):
                    # Historical captures can be downloaded from discovery metadata but cannot be looked up by ID again.
                    for level in ("low", "high"):
                        rows[str(p.id)][level]["image_path"] = p.image_path
                new.append(rows[str(p.id)])
            if sink and new:
                sink(new)
            now = time.monotonic()
            if now - last >= PROGRESS_S and done < len(pts):
                rate = done / max(now - t0, 1e-3)
                print(f"{service}: {done}/{len(pts)} lookups, {len(rows)} panoramas, {rate:.1f} lookups/s, "
                      f"~{_dur((len(pts) - done) / rate)} left", file=sys.stderr, flush=True)
                last = now
    if errors[0] >= 12:
        print(f"{service}: stopped after repeated errors (rate limit or block?) — got {len(rows)} panoramas; "
              "retry later with a larger --spacing", file=sys.stderr)
    return list(rows.values())


def _kartaview_url(storage_path: str) -> str:
    host, rest = storage_path.split("/", 1)
    raw = f"https://{host}.openstreetcam.org/{rest}"
    return "https://cdn.kartaview.org/pr:sharp/" + base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def list_kartaview(bb, spacing, limit) -> list[dict]:
    rows = {}
    r = 500.0
    pts = grid(bb, r * 1.4)
    for la, lo in pts:
        try:
            d = http_json("https://api.openstreetcam.org/1.0/list/nearby-photos/", {"lat": la, "lng": lo, "radius": int(r)})
        except Exception as e:  # noqa: BLE001  (the API answers some busy areas with a generic HTTP 400)
            print(f"kartaview: no answer near {la:.4f},{lo:.4f} ({str(e)[:80]})", file=sys.stderr)
            continue
        for it in d.get("currentPageItems") or []:
            lat, lon = float(it["lat"]), float(it["lng"])
            if not in_bbox(lat, lon, bb):
                continue
            sphere = (it.get("projection") or "").upper() == "SPHERE"
            spec_low = {"kind": "equirect" if sphere else "photo", "url": _kartaview_url(it["th_name"])}
            spec_high = {"kind": "equirect" if sphere else "photo", "url": _kartaview_url(it["name"])}
            if not sphere:
                spec_low["hfov"] = spec_high["hfov"] = float(it.get("field_of_view") or 70)
            rows[it["id"]] = {"provider": "kartaview", "id": str(it["id"]), "lat": lat, "lon": lon,
                              "heading": float(it.get("heading") or 0), "date": (it.get("shot_date") or "")[:10],
                              "link": f"https://kartaview.org/details/{it.get('sequence_id')}/{it.get('sequence_index')}",
                              "low": spec_low, "high": spec_high}
        if limit and len(rows) >= limit:
            break
    return list(rows.values())


PANORAMAX = ("https://api.panoramax.xyz/api", "https://panoramax.openstreetmap.fr/api", "https://panoramax.ign.fr/api")


def list_panoramax(bb, spacing, limit) -> list[dict]:
    """Panoramax: ask the federation's meta-catalogue and the big instances (the catalogue is sometimes down);
    split the box whenever a page comes back full."""
    rows: dict[str, dict] = {}

    def add(f):
        pr, a = f.get("properties") or {}, f.get("assets") or {}
        lon, lat = f["geometry"]["coordinates"][:2]
        fov = (pr.get("pers:interior_orientation") or {}).get("field_of_view")
        sphere = fov == 360
        sd, hd, th = ((a.get(k) or {}).get("href") for k in ("sd", "hd", "thumb"))
        if not (sd or hd or th):
            return
        mk = (lambda u: {"kind": "equirect", "url": u}) if sphere else (lambda u: {"kind": "photo", "url": u, "hfov": float(fov or 70)})
        rows[f["id"]] = {"provider": "panoramax", "id": f["id"], "lat": lat, "lon": lon, "heading": float(pr.get("view:azimuth") or 0),
                         "date": (pr.get("datetime") or "")[:10], "link": f"https://api.panoramax.xyz/#focus=pic&pic={f['id']}",
                         "low": mk(sd if sphere else (th or sd or hd)), "high": mk(hd or sd)}

    def search(api, box, depth):
        s, w, n, e = box
        try:
            d = http_json(f"{api}/search?bbox={w},{s},{e},{n}&limit=100", timeout=25)
        except Exception:  # noqa: BLE001
            return False if depth == 0 else True
        feats = d.get("features") or []
        for f in feats:
            add(f)
        if len(feats) >= 100 and depth < 3 and not (limit and len(rows) >= limit):
            mla, mlo = (s + n) / 2, (w + e) / 2
            for q in ((s, w, mla, mlo), (s, mlo, mla, e), (mla, w, n, mlo), (mla, mlo, n, e)):
                search(api, q, depth + 1)
        return True

    ok = [api for api in PANORAMAX if search(api, bb, 0)]
    if not ok:
        print("panoramax: no endpoint answered (api.panoramax.xyz and the main instances)", file=sys.stderr)
    return list(rows.values())


def list_mapillary(bb, spacing, limit) -> list[dict]:
    tok = os.environ.get("MAPILLARY_TOKEN")
    if not tok:
        raise SystemExit("Mapillary needs MAPILLARY_TOKEN (a free client token from mapillary.com/dashboard/developers). "
                         "Without one, browse https://www.mapillary.com/app/?lat=…&lng=…&z=16 in the browser instead.")
    rows = {}
    cell = 0.01
    s, w, n, e = bb
    la = s
    while la < n:
        lo = w
        while lo < e:
            q = (f"https://graph.mapillary.com/images?access_token={tok}&bbox={lo},{la},{min(lo + cell, e)},{min(la + cell, n)}"
                 "&fields=id,geometry,compass_angle,captured_at,is_pano,thumb_1024_url,thumb_2048_url&limit=2000")
            try:
                d = http_json(q)
            except Exception as ex:  # noqa: BLE001
                print(f"mapillary: {str(ex).replace(tok, '***')}", file=sys.stderr)
                d = {}
            for it in d.get("data") or []:
                lo2, la2 = it["geometry"]["coordinates"][:2]
                pano = bool(it.get("is_pano"))
                mk = (lambda u: {"kind": "equirect", "url": u}) if pano else (lambda u: {"kind": "photo", "url": u, "hfov": 70.0})
                when = time.strftime("%Y-%m-%d", time.gmtime((it.get("captured_at") or 0) / 1000)) if it.get("captured_at") else ""
                rows[it["id"]] = {"provider": "mapillary", "id": str(it["id"]), "lat": la2, "lon": lo2,
                                  "heading": float(it.get("compass_angle") or 0), "date": when,
                                  "link": f"https://www.mapillary.com/app/?pKey={it['id']}",
                                  "low": mk(it.get("thumb_1024_url")), "high": mk(it.get("thumb_2048_url") or it.get("thumb_1024_url"))}
            lo += cell
        la += cell
    return list(rows.values())


LISTERS = {"google": list_google, "apple": list_apple, "bing": list_bing, "kartaview": list_kartaview,
           "panoramax": list_panoramax, "mapillary": list_mapillary,
           **{s: (lambda s_: (lambda bb, sp, lim, sink=None: _point_lookup(s_, bb, sp, lim, sink)))(s) for s in ZOOMS}}


def thin(rows: list[dict], spacing: float) -> list[dict]:
    """Keep panoramas at least `spacing` m apart (grid hashing, first come first kept)."""
    if not spacing or spacing <= 0:
        return rows
    kept, cells = [], {}
    for r in rows:
        cx, cy = int(r["lat"] * 110540 // spacing), int(r["lon"] * 111320 * math.cos(math.radians(r["lat"])) // spacing)
        near = [k for dx in (-1, 0, 1) for dy in (-1, 0, 1) for k in cells.get((cx + dx, cy + dy), [])]
        if all(dist_m((r["lat"], r["lon"]), (k["lat"], k["lon"])) >= spacing for k in near):
            kept.append(r)
            cells.setdefault((cx, cy), []).append(r)
    return kept


# ---------------------------------------------------------------- commands

def cmd_providers(_a) -> None:
    for k, v in PROVIDERS.items():
        print(f"{k:10s} {v}")
    print("\nThese are only the scriptable ones. Always also search the web (in the local languages) for national, local and "
          "historical street-level sites, check Google Maps photo spheres and place photos in the browser, and turn what you "
          "find into a manifest (references/streetlevel.md §1–3).")


def _nearest_one(service: str, lat: float, lon: float, radius: float, t0: float) -> dict:
    mod = P._sl(service)
    try:
        if service == "kakao":
            ps = mod.find_panoramas(lat, lon, radius=int(radius), limit=50) or []
        elif service == "ja":
            ps = [mod.find_panorama(lat, lon, radius=int(radius))]
        else:
            ps = [mod.find_panorama(lat, lon)]
    except Exception as e:  # noqa: BLE001  (several services raise instead of returning nothing)
        return {"n": 0, "note": f"no answer ({type(e).__name__})", "seconds": round(time.time() - t0, 1)}
    ps = [p for p in ps if p is not None]
    if not ps:
        return {"n": 0, "seconds": round(time.time() - t0, 1)}
    p = min(ps, key=lambda p: dist_m((lat, lon), (p.lat, p.lon)))
    dm = dist_m((lat, lon), (p.lat, p.lon))
    res = {"n": len([q for q in ps if dist_m((lat, lon), (q.lat, q.lon)) <= radius]), "nearest_m": round(dm), "nearest_id": str(p.id),
           "dates": _date(getattr(p, "date", None)), "seconds": round(time.time() - t0, 1)}
    if dm > radius:
        res["note"] = "nearest panorama is outside the radius"
    return res


def cmd_coverage(a) -> None:
    lat, lon = (float(v) for v in a.latlon.split(","))
    bb = bbox_around(lat, lon, a.radius)
    provs = a.providers.split(",") if a.providers else list(LISTERS)
    out = {}

    def one(pv):
        if pv == "mapillary" and not os.environ.get("MAPILLARY_TOKEN"):
            return pv, {"status": "skipped: set MAPILLARY_TOKEN, or browse mapillary.com/app in the browser"}
        t0 = time.time()
        if pv in ZOOMS:                      # point-lookup services: one nearest-panorama question is enough here
            return pv, _nearest_one(pv, lat, lon, a.radius, t0)
        try:
            rows = LISTERS[pv](bb, max(a.radius / 6, 25), 400)
        except SystemExit as e:
            return pv, {"status": f"error: {e}"}
        except Exception as e:  # noqa: BLE001
            return pv, {"status": f"error: {type(e).__name__}: {str(e)[:120]}"}
        if not rows:
            return pv, {"n": 0, "seconds": round(time.time() - t0, 1)}
        ds = sorted(r["date"] for r in rows if r.get("date"))
        near = min(rows, key=lambda r: dist_m((lat, lon), (r["lat"], r["lon"])))
        return pv, {"n": len(rows), "nearest_m": round(dist_m((lat, lon), (near["lat"], near["lon"]))), "nearest_id": near["id"],
                    "dates": f"{ds[0]} … {ds[-1]}" if ds else "", "seconds": round(time.time() - t0, 1)}
    with ThreadPoolExecutor(6) as ex:
        for pv, res in ex.map(one, provs):
            out[pv] = res
            print(f"{pv:10s} {json.dumps(res, ensure_ascii=False)}", flush=True)
    if not any(v.get("n") for v in out.values()):
        print("\nNothing scriptable covers this place. Next: (1) search the web for local/historical street-level sites "
              "(references/streetlevel.md), (2) Google Maps in the browser: Street View layer (blue dots = user photo spheres) "
              "and place photos, (3) Mapillary/KartaView web maps, (4) YouTube walking/driving videos, (5) satellite + OSM.")
    if a.out:
        Path(a.out).write_text(json.dumps({"center": [lat, lon], "radius_m": a.radius, "providers": out}, indent=1, ensure_ascii=False), encoding="utf-8")


def _area(a):
    if a.bbox:
        s, w, n, e = (float(v) for v in a.bbox.split(","))
        return (s, w, n, e)
    if a.near:
        la, lo = (float(v) for v in a.near.split(","))
        return bbox_around(la, lo, a.radius)
    raise SystemExit("give --bbox s,w,n,e or --near lat,lon --radius m")


def _periods(rows: list[dict]) -> str:
    """Capture months present, for a --date that matched nothing."""
    return ", ".join(sorted({str(r["date"])[:7] for r in rows if r.get("date")}))


class _Partial:
    """Sink for a point-lookup listing: the rows that pass keep go to <out>.partial.jsonl as they arrive, so a killed run keeps
    them there; --out is written only when the listing ends. The sidecar is truncated at the first such row, so a run refused
    or killed before any leaves an older one alone."""

    def __init__(self, out: str, keep):
        self.path, self.keep, self.mode = f"{out}.partial.jsonl", keep, "w"

    def __call__(self, rows: list[dict]) -> None:
        rows = [r for r in rows if self.keep(r)]
        if rows:
            with open(self.path, self.mode, encoding="utf-8") as f:
                f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
            self.mode = "a"


def cmd_list(a) -> None:
    bb = _area(a)
    t0 = time.time()
    near = tuple(float(v) for v in a.near.split(",")) if a.near else None

    def in_area(r) -> bool:
        return near is None or dist_m(near, (r["lat"], r["lon"])) <= a.radius

    def dated(r) -> bool:
        return not a.date or str(r.get("date", "")).startswith(a.date)
    sink = _Partial(a.out, lambda r: in_area(r) and dated(r)) if a.provider in ZOOMS else None
    # the lister stops at --limit only when nothing after it drops rows; otherwise it lists the whole area and the limit caps the result
    rows = LISTERS[a.provider](bb, a.spacing, 0 if (a.near or a.date or a.thin) else a.limit, **({"sink": sink} if sink else {}))
    if near:                          # nearest first, as sheet selects: thinning and the limit keep the panoramas at the point
        rows = sorted(filter(in_area, rows), key=lambda r: dist_m(near, (r["lat"], r["lon"])))
    n0 = len(rows)
    if a.date:                        # before thinning: first-come thinning could drop a whole capture period
        kept = list(filter(dated, rows))
        if rows and not kept:
            print(f"--date {a.date} kept 0 of {n0} panoramas ({sum(not r.get('date') for r in rows)} undated; periods here: "
                  f"{_periods(rows) or 'none'}): rerun with one of these periods, or without --date", file=sys.stderr)
        rows = kept
    rows = thin(rows, a.thin)
    if a.limit > 0:
        rows = rows[: a.limit]
    P.write_manifest(a.out, rows)     # in place: a reader holding --out open (Windows) never blocks it
    if sink:
        Path(sink.path).unlink(missing_ok=True)
    ds = sorted(r["date"] for r in rows if r.get("date"))
    print(f"{a.provider}: {n0} panoramas in the area ({time.time() - t0:.0f}s), kept {len(rows)}"
          + (f", dates {ds[0]} … {ds[-1]}" if ds else "") + f" -> {a.out}")
    if rows:
        print(f"next: sweep.py index --manifest {a.out}   then   sweep.py rank --index {Path(a.out).stem} --query original/<photo>")


def _select(a) -> list[dict]:
    rows = P.read_manifest(*a.manifest)
    if getattr(a, "ids", None):
        want = a.ids.split(",")
        byid = {r["id"]: r for r in rows}
        rows = [byid[i] for i in want if i in byid]
    if getattr(a, "near", None):
        la, lo = (float(v) for v in a.near.split(","))
        rows = sorted((r for r in rows if dist_m((la, lo), (r["lat"], r["lon"])) <= a.radius),
                      key=lambda r: dist_m((la, lo), (r["lat"], r["lon"])))
    return rows


def cmd_render(a) -> None:
    rows = [r for r in P.read_manifest(*a.manifest) if r["id"] == a.id]
    if not rows:
        raise SystemExit(f"{a.id} not in the manifest")
    v = P.load(rows[0], a.level)
    v.render(a.bearing, a.pitch, a.fov, a.width, a.height).save(a.out, quality=92)
    print(a.out)


def cmd_sheet(a) -> None:
    rows = _select(a)
    if a.date:
        sel = [r for r in rows if str(r.get("date") or "").startswith(a.date)]
        if rows and not sel:
            raise SystemExit(f"no {a.date} capture in the selection (available: {_periods(rows) or 'undated'}); widen --radius or "
                             "pick another period")
        rows = sel
    rows = rows[: a.limit]
    if not rows:
        raise SystemExit("no panoramas selected")
    target = tuple(float(v) for v in a.toward.split(",")) if a.toward else None
    items = []
    for r in rows:
        if target:
            bs = [bearing((r["lat"], r["lon"]), target)]
        elif a.along:
            bs = [r.get("heading") or 0]
        else:
            bs = [float(x) for x in a.bearings.split(",")]
        for b in bs:
            items.append((r, b))
    tw, th = 480, 320

    def one(it):
        r, b = it
        try:
            return P.load(r, a.level).render(b, a.pitch, a.fov, tw, th)
        except Exception as e:  # noqa: BLE001
            im = Image.new("RGB", (tw, th), "gray")
            ImageDraw.Draw(im).text((8, 30), f"failed: {str(e)[:60]}", fill="white")
            im.info["failed"] = f"{type(e).__name__}: {str(e)[:120]}"
            return im
    with ThreadPoolExecutor(6) as ex:
        ims = list(ex.map(one, items))
    from geolib.cli import contact_sheet, failed_cells, sheet_failures
    sheet_failures(failed_cells(ims), len(ims))            # exits when every cell failed: neither sheet nor index
    contact_sheet([(im, f"{i}: {r['provider']} {r['id'][-14:]} {r.get('date', '')} brg {b:.0f}") for i, ((r, b), im) in enumerate(zip(items, ims))],
                  a.out, a.cols, tw, th, bar=20, font_size=15)
    Path(a.out).with_suffix(".index.json").write_text(json.dumps(
        [{"cell": i, "provider": r["provider"], "id": r["id"], "lat": r["lat"], "lon": r["lon"], "bearing": round(b, 1),
          "date": r.get("date"), "link": r.get("link")} for i, (r, b) in enumerate(items)], indent=1, ensure_ascii=False), encoding="utf-8")
    print(a.out)


from geolib.cli import neg_coords as _neg_coords  # noqa: E402  (shared helper)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("providers")
    c = sub.add_parser("coverage")
    c.add_argument("latlon")
    c.add_argument("--radius", type=float, default=400)
    c.add_argument("--providers", help="comma list (default: all)")
    c.add_argument("--out")
    li = sub.add_parser("list")
    li.add_argument("--provider", required=True, choices=sorted(LISTERS))
    li.add_argument("--bbox", help="south,west,north,east")
    li.add_argument("--near", help="lat,lon (with --radius)")
    li.add_argument("--radius", type=float, default=1000)
    li.add_argument("--spacing", type=float, default=30, help="grid step for point-lookup providers (m)")
    li.add_argument("--thin", type=float, default=0, help="keep panoramas at least this far apart (m)")
    li.add_argument("--date", help="keep one capture period, e.g. 2014 or 2014-04")
    li.add_argument("--limit", type=int, default=0, help="keep at most this many panoramas, after --date and --thin; nearest first with --near (0: all)")
    li.add_argument("--out", required=True)
    for name in ("render", "sheet"):
        s = sub.add_parser(name)
        s.add_argument("--manifest", nargs="+", required=True)
        s.add_argument("--pitch", type=float, default=0)
        s.add_argument("--fov", type=float, default=80)
        s.add_argument("--level", choices=["low", "high"], default="high")
        s.add_argument("--out", required=True)
        if name == "render":
            s.add_argument("--id", required=True)
            s.add_argument("--bearing", type=float, required=True)
            s.add_argument("--width", type=int, default=1280)
            s.add_argument("--height", type=int, default=853)
        else:
            s.add_argument("--ids")
            s.add_argument("--near")
            s.add_argument("--radius", type=float, default=50)
            s.add_argument("--date", help="keep one capture period, e.g. 2026 or 2026-03 (default: all dates)")
            g = s.add_mutually_exclusive_group()
            g.add_argument("--bearings", default="0,90,180,270")
            g.add_argument("--toward", help="lat,lon: every panorama faces this point")
            g.add_argument("--along", action="store_true", help="face the capture direction")
            s.add_argument("--limit", type=int, default=12)
            s.add_argument("--cols", type=int, default=4)
    a = ap.parse_args(_neg_coords(sys.argv[1:]))
    model_proxy_env()     # GEO_PROXY (or direct) also for the streetlevel package's requests calls, as curl already honours it
    {"providers": cmd_providers, "coverage": cmd_coverage, "list": cmd_list, "render": cmd_render, "sheet": cmd_sheet}[a.cmd](a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
