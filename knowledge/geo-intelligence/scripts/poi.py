#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "tzdata"]
# ///
"""Place name, residential compound name, housing development name, shop name → coordinate candidates (no API key).

Reverse image search often returns "the photo may be XX花园 (XX Garden)" or "XX大厦 (XX Tower)"; a compound name or hotel name read on a web page must be placed at coordinates before it can be checked.
The same name often exists dozens of times across China; the script lists the same-name points in every region, and other clues in the photo pick among them.

Sources:
  so    360 Maps search: good coverage of residential compounds, housing developments, shops and organizations, with address; raw coordinates are GCJ-02, converted to WGS84
  osm   OpenStreetMap Nominatim: named compounds, parks, roads; coordinates WGS84
  sug   Baidu Maps search suggestions: only "city + district + name", no coordinates; use it to see which districts in China have this name

Examples:
  poi.py "<compound name>" --city <city>                 # all same-name points in the city, outputs {name: [lat, lon]}
  poi.py "<district> <road name> 学校" --city <municipality or prefecture-level city>   # --city only accepts prefecture-level cities; put the district in the keyword (学校 = school)
  poi.py "<compound name>" --city <city> --region cn       # sources from the region pack (CN: 360 Maps + OSM + Baidu suggestions)
  poi.py "<street address or place name>" --region mx     # packs without a poi service: OSM restricted to that country
  poi.py "<compound name>"                                # no city: lists which cities in China have a same-name point
  poi.py "<hotel name>" --city <city> --out pois.json && tiles.py sheet --points pois.json --zoom 18 --out pois_sheet.jpg

Baidu Maps web place search requires a CAPTCHA, so the script doesn't use it; the Tencent and Amap APIs require a key, so it doesn't use them either.

Map subcommands (OpenStreetMap Nominatim / Overpass, OSRM, timeapi.io; JSON on stdout; "lat,lon" works wherever a place is asked):
  poi.py nearby 48.8584,2.2945 --category cafe --category bakery [--radius 500] [--limit 10] [--out near.json]
  poi.py nearby --near "Rua Augusta, Lisboa" --category pharmacy        # also raw OSM tags: --category shop=car_repair
  poi.py reverse 48.8584,2.2945                                          # address of a point
  poi.py distance "Paris" --to "Lyon" [--mode driving|walking|cycling]   # road distance + time, plus straight line
  poi.py directions "45.764,4.836" --to "Villeurbanne" --mode walking    # turn-by-turn steps
  poi.py timezone 48.8584,2.2945                                         # IANA zone and current UTC offset
  poi.py area "Manhattan"                                                # bounding box (s w n e) for bbox / osm.py --bbox
  poi.py bbox 40.70 -74.02 40.78 -73.95 restaurant [--limit 20] [--out pois.json]
Categories: `poi.py nearby --help`. Nominatim is called at most once per second with a descriptive User-Agent; nearby and bbox
return the nearest results (sorted by distance before --limit); walking/cycling use FOSSGIS OSRM per-profile routers.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geo  # noqa: E402
import regions  # noqa: E402
from geolib import net  # noqa: E402
from geolib.cli import neg_coords  # noqa: E402
from geolib.geomath import haversine_m  # noqa: E402
from geolib.net import curl_args, PROXY_HELP  # noqa: E402

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def _curl(url: str, proxy: str | None = None, ua: str = UA, timeout: int = 25) -> str:
    cmd = ["curl", "-q", "-sS", "-m", str(timeout), "-A", ua, url]
    cmd += curl_args(proxy)
    # Pages are UTF-8. Without encoding=, Chinese Windows decodes as GBK, and stdout is None when decoding fails
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"Request failed (curl exit code {r.returncode}): {r.stderr.strip()[:200]}", file=sys.stderr)
    return r.stdout


def search_so(kw: str, city: str | None, n: int, proxy: str | None = None) -> tuple[list[dict], list[dict]]:
    q = {"keyword": kw, "batch": 1, "number": n, "ext": 1, "sid": 1000}
    if city:
        q["cityname"] = city
    raw = _curl("https://restapi.map.so.com/newapi?" + urllib.parse.urlencode(q), proxy=proxy)
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        print(f"360 Maps did not return JSON: {raw[:120]}", file=sys.stderr)
        return [], []
    rows = []
    for p in d.get("poi") or []:
        if not p.get("x") or not p.get("y"):
            continue
        lat, lon = geo.gcj2wgs(float(p["y"]), float(p["x"]))
        rows.append({"src": "so", "name": p.get("name", ""), "city": p.get("city", ""), "area": p.get("area", ""),
                     "address": p.get("address", ""), "type": p.get("cat_new_name") or p.get("type", ""),
                     "wgs": [round(lat, 6), round(lon, 6)]})
    cities = [{"city": c.get("name"), "province": c.get("province"), "count": c.get("resultnum")}
              for c in d.get("citysuggestion") or []]
    return rows, cities


def search_osm(kw: str, city: str | None, n: int, proxy: str | None, country: str) -> list[dict]:
    q = {"q": f"{kw} {city}" if city else kw, "format": "jsonv2", "limit": n, "accept-language": "en"}
    if country:
        q["countrycodes"] = country
    raw = _curl("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(q), proxy=proxy, ua=OSM_UA)
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        print(f"Nominatim did not return JSON (check service availability with doctor.py --network): {raw[:120]}", file=sys.stderr)
        return []
    return [{"src": "osm", "name": p.get("name") or p.get("display_name", "").split(",")[0],
             "city": "", "area": "", "address": p.get("display_name", ""), "type": f"{p.get('category')}/{p.get('type')}",
             "wgs": [round(float(p["lat"]), 6), round(float(p["lon"]), 6)]} for p in d]


def search_sug(kw: str, proxy: str | None = None) -> list[dict]:
    raw = _curl("https://map.baidu.com/su?" + urllib.parse.urlencode({"wd": kw, "cid": 1, "type": 0, "newmap": 1, "ie": "utf-8"}), proxy=proxy)
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        return []
    out = []
    for s in d.get("s") or []:
        parts = s.split("$")
        if len(parts) >= 4:
            out.append({"src": "sug", "city": parts[0], "area": parts[1], "name": parts[3]})
    return out


def cmd_search(args) -> None:
    svc = {}
    if args.region:
        pk = regions.resolve(args.region)
        if pk:
            svc = (pk.get("services") or {}).get("poi") or {"sources": "osm", "country": pk["code"].lower()}
        elif re.fullmatch(r"[A-Za-z]{2}", args.region.strip()):
            # No pack for this country: still restrict Nominatim to it rather than searching the whole world
            svc = {"sources": "osm", "country": args.region.strip().lower()}
            print(f"No region pack for '{args.region}': OSM only, restricted to countrycodes={svc['country']}", file=sys.stderr)
        else:
            sys.exit(f"No region pack for '{args.region}' (installed: {', '.join(sorted(regions.packs()))}): "
                     f"pass its ISO 3166-1 alpha-2 code (e.g. --region in) so the search stays inside that country")
    han = re.search(r"[\u4e00-\u9fff]", args.keyword)
    args.sources = args.sources or svc.get("sources") or ("so,osm,sug" if han and not args.region else "osm")
    args.country = args.country if args.country is not None else svc.get("country", "")

    src = set(args.sources.split(","))
    rows: list[dict] = []
    if "so" in src:
        so_rows, cities = search_so(args.keyword, args.city, args.limit, args.proxy)
        if args.city and so_rows and not any(args.city in (r["city"] + r["area"] + r["address"]) for r in so_rows):
            print(f"Note: none of the 360 Maps results is in \"{args.city}\" — it doesn't recognize this city name and silently switched to another city. "
                  f"Pass a prefecture-level city or municipality to --city (e.g. 重庆 (Chongqing)), and put the district name in the keyword (e.g. \"<district> <name>\")")
        rows += so_rows
        if cities and not args.city:
            print("360 Maps: cities in China with same-name results (result count)")
            print("  " + ", ".join(f"{c['city']}({c['count']})" for c in cities[:30]))
    if "osm" in src:
        rows += search_osm(args.keyword, args.city, args.limit, args.proxy, args.country)
    if "sug" in src:
        sug = search_sug(args.keyword, args.proxy)
        if sug:
            print("Baidu suggestions (no coordinates; only shows which districts have this name):")
            print("  " + "; ".join(f"{s['city']}{s['area']} {s['name']}" for s in sug[:15]))

    # Deduplicate when two sources return the same place (within 150 m and one name contains the other)
    uniq: list[dict] = []
    for r in rows:
        if any(haversine_m(r["wgs"], u["wgs"]) < 150 and (r["name"] in u["name"] or u["name"] in r["name"]) for u in uniq):
            continue
        uniq.append(r)
    print(f"\n{len(uniq)} candidates with coordinates (WGS84):")
    pts = {}
    for i, r in enumerate(uniq, 1):
        label = f"{i:02d} {r['name']} {r['area']}".strip()
        pts[label] = r["wgs"]
        print(f"  {label}  {r['wgs'][0]},{r['wgs'][1]}  [{r['src']}] {r['type']}  {r['address'][:60]}")
    if not uniq:
        cc = (args.country or ("cn" if han else "xx"))[:2].upper()     # revimg.py takes one ISO2 code; Nominatim may hold a list
        print("  None. Try another spelling (drop the \"小区/花园\" (compound/garden) suffix, add the district name), "
              f"or search the address on that country's image engines: revimg.py --query \"<address>\" --country {cc}")
    if args.out:
        args.out.write_text(json.dumps(pts, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"-> {args.out}")
    if len(uniq) >= 2:
        # Several campuses of one school or several branches of a chain all show up here; the first one is not necessarily the right one
        print(f"\nAll {len(uniq)} places must be candidates; don't take only the first one: "
              + (f"`board.py add --from {args.out} --level area --parent <parent>` puts them all on the candidate board" if args.out
                 else "add --out pois.json, then `board.py add --from pois.json --level area` puts them all on the candidate board"))


# ---------------------------------------------------------------- map subcommands (Nominatim, OSRM, time zone)

NOMINATIM = "https://nominatim.openstreetmap.org"
# router.project-osrm.org serves only the car profile (a "foot" request returns car times), so every mode first uses the
# FOSSGIS OSRM instance for that profile (behind openstreetmap.org's directions); the demo server is the driving fallback.
OSRM_ROUTES = {"driving": "https://routing.openstreetmap.de/routed-car/route/v1/driving",
               "walking": "https://routing.openstreetmap.de/routed-foot/route/v1/driving",
               "cycling": "https://routing.openstreetmap.de/routed-bike/route/v1/driving"}
OSRM_FALLBACK = "https://router.project-osrm.org/route/v1/driving"
TIMEAPI = "https://timeapi.io/api/timezone/coordinate"
OSM_UA = "geo-intelligence/1.0 (+https://github.com/AeonDave/malskill)"
NOMINATIM_INTERVAL_S = 1.0          # Nominatim usage policy: at most one request per second

# category -> OSM (key, value) pairs; several pairs are unioned. Raw "key=value" is also accepted on the command line.
CATEGORY_TAGS: dict[str, list[tuple[str, str]]] = {
    "restaurant": [("amenity", "restaurant")], "cafe": [("amenity", "cafe")], "bar": [("amenity", "bar")],
    "bakery": [("shop", "bakery"), ("amenity", "bakery")], "convenience_store": [("shop", "convenience")],
    "hospital": [("amenity", "hospital")], "pharmacy": [("amenity", "pharmacy")], "dentist": [("amenity", "dentist")],
    "doctor": [("amenity", "doctors")], "veterinary": [("amenity", "veterinary")],
    "hotel": [("tourism", "hotel")], "guest_house": [("tourism", "guest_house")], "camp_site": [("tourism", "camp_site")],
    "supermarket": [("shop", "supermarket")], "bookshop": [("shop", "books")], "laundry": [("shop", "laundry")],
    "atm": [("amenity", "atm")], "bank": [("amenity", "bank")],
    "gas_station": [("amenity", "fuel")], "parking": [("amenity", "parking")], "airport": [("aeroway", "aerodrome")],
    "train_station": [("railway", "station")], "bus_stop": [("highway", "bus_stop")], "taxi": [("amenity", "taxi")],
    "car_wash": [("amenity", "car_wash")], "car_rental": [("amenity", "car_rental")],
    "bicycle_rental": [("amenity", "bicycle_rental")],
    "museum": [("tourism", "museum")], "cinema": [("amenity", "cinema")], "theatre": [("amenity", "theatre")],
    "nightclub": [("amenity", "nightclub")], "zoo": [("tourism", "zoo")],
    "school": [("amenity", "school")], "university": [("amenity", "university")], "library": [("amenity", "library")],
    "police": [("amenity", "police")], "fire_station": [("amenity", "fire_station")], "post_office": [("amenity", "post_office")],
    "church": [("amenity", "place_of_worship")], "mosque": [("amenity", "place_of_worship")],
    "synagogue": [("amenity", "place_of_worship")],
    "park": [("leisure", "park")], "gym": [("leisure", "fitness_centre")], "swimming_pool": [("leisure", "swimming_pool")],
    "playground": [("leisure", "playground")], "stadium": [("leisure", "stadium")],
}
RELIGION_FILTER = {"church": "christian", "mosque": "muslim", "synagogue": "jewish"}
PROMOTED_TAGS = (("cuisine", "cuisine"), ("opening_hours", "hours"), ("phone", "phone"), ("website", "website"))
_last_nominatim = 0.0


def category_tags(cat: str) -> tuple[list[tuple[str, str]], str | None]:
    """OSM tag pairs and religion filter for a category name or a raw 'key=value'."""
    c = cat.strip()
    if c.lower() in CATEGORY_TAGS:
        return list(CATEGORY_TAGS[c.lower()]), RELIGION_FILTER.get(c.lower())
    if re.fullmatch(r"[\w:.-]+=[^\s\"]+", c):
        k, v = c.split("=", 1)
        return [(k, v)], None
    raise ValueError(f"unknown category {cat!r}; use key=value or one of: {', '.join(sorted(CATEGORY_TAGS))}")


def _get_json(url: str, proxy: str | None, timeout: int = 25):
    return json.loads(net.fetch_bytes(url, proxy, timeout, {"User-Agent": OSM_UA}).decode("utf-8"))


def nominatim(endpoint: str, params: dict, proxy: str | None):
    """GET /search or /reverse (jsonv2), spaced at least NOMINATIM_INTERVAL_S apart within this process."""
    global _last_nominatim
    wait = NOMINATIM_INTERVAL_S - (time.monotonic() - _last_nominatim)
    if wait > 0:
        time.sleep(wait)
    try:
        return _get_json(f"{NOMINATIM}/{endpoint}?" + urllib.parse.urlencode({**params, "format": "jsonv2"}), proxy)
    finally:
        _last_nominatim = time.monotonic()


def parse_point(text: str) -> tuple[float, float] | None:
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*", text or "")
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    return (lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 else None


def geocode(place: str, proxy: str | None) -> tuple[float, float, str]:
    """'lat,lon' as given, else the first Nominatim hit."""
    pt = parse_point(place)
    if pt:
        return pt[0], pt[1], f"{pt[0]},{pt[1]}"
    rows = nominatim("search", {"q": place, "limit": 1, "addressdetails": 1}, proxy)
    if not rows:
        sys.exit(f"Could not geocode: {place}")
    return float(rows[0]["lat"]), float(rows[0]["lon"]), rows[0].get("display_name", place)


def overpass_ql(pairs: list[tuple[str, str]], religion: str | None, scope: str) -> str:
    """Nodes, ways and relations (with centre) matching any pair inside scope ('around:r,lat,lon' or 's,w,n,e').
    No server-side limit: Overpass would cut in its own order, so the nearest N are chosen after sorting by distance."""
    rel = f'["religion"="{religion}"]' if religion else ""
    body = "".join(f'nwr["{k}"="{v}"]{rel}({scope});' for k, v in pairs)
    return f"[out:json][timeout:60];({body});out center tags;"


def _overpass(ql: str, proxy: str | None, cache: Path) -> dict:
    import osm                          # shared mirror list, 429/406 back-off and per-query cache
    return osm.run(ql, proxy, cache, timeout=60)


def parse_elements(elements: list[dict], ref: tuple[float, float] | None = None) -> list[dict]:
    """Overpass elements -> POI rows (name, address, lat, lon, distance_m, maps_url, promoted tags, other tags)."""
    out = []
    for el in elements:
        c = el.get("center") or {}
        lat, lon = el.get("lat", c.get("lat")), el.get("lon", c.get("lon"))
        if lat is None or lon is None:
            continue
        tags = el.get("tags") or {}
        addr = ", ".join(tags[k] for k in ("addr:housenumber", "addr:street", "addr:city") if tags.get(k))
        row = {"name": tags.get("name") or tags.get("name:en") or "", "address": addr, "lat": lat, "lon": lon,
               "osm_type": el.get("type", ""), "osm_id": el.get("id", ""),
               "maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"}
        for src, dst in PROMOTED_TAGS:
            if tags.get(src):
                row[dst] = tags[src]
        if ref:
            row["distance_m"] = round(haversine_m(ref, (lat, lon)), 1)
        row["tags"] = {k: v for k, v in tags.items()
                       if k not in ("name", "name:en", "addr:housenumber", "addr:street", "addr:city")}
        out.append(row)
    if ref:
        out.sort(key=lambda r: r["distance_m"])
    return out


def _points_out(rows: list[dict], out: Path | None) -> None:
    """{label: [lat, lon]} for tiles.py mark / sheet and board.py add --from (same format as the search --out)."""
    if not out:
        return
    pts = {f"{i:02d} {r.get('name') or r.get('category', '')}".strip(): [r["lat"], r["lon"]] for i, r in enumerate(rows, 1)}
    out.write_text(json.dumps(pts, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}", file=sys.stderr)


def _print(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=1))


def _point_and_rest(tokens: list[str]) -> tuple[tuple[float, float] | None, list[str]]:
    """'lat,lon' or 'lat lon' at the start of tokens; returns (point, remaining tokens)."""
    toks = [x.strip() for x in tokens if x.strip()]
    if toks and parse_point(toks[0]) and "," in toks[0]:
        return parse_point(toks[0]), toks[1:]
    if len(toks) >= 2 and parse_point(f"{toks[0]},{toks[1]}"):
        return parse_point(f"{toks[0]},{toks[1]}"), toks[2:]
    return None, toks


def cmd_nearby(args) -> None:
    pt, rest = _point_and_rest(args.point)
    if args.near:
        lat, lon, label = geocode(" ".join(args.near), args.proxy)
    elif pt:
        lat, lon, label = pt[0], pt[1], f"{pt[0]},{pt[1]}"
    else:
        sys.exit("Give a point (lat,lon) or --near \"<place>\".")
    cats = list(dict.fromkeys(c.lower() if c.lower() in CATEGORY_TAGS else c for c in [*args.category, *rest]))
    if not cats:
        sys.exit("Give at least one --category (see --help for the list) or a raw OSM tag key=value.")
    if args.radius <= 0 or args.limit <= 0:
        sys.exit("--radius and --limit must be positive.")
    merged: dict = {}
    for cat in cats:
        try:
            pairs, religion = category_tags(cat)
        except ValueError as e:
            sys.exit(str(e))
        data = _overpass(overpass_ql(pairs, religion, f"around:{args.radius},{lat},{lon}"), args.proxy, args.cache)
        for row in parse_elements(data.get("elements", []), (lat, lon)):
            row["category"] = cat
            merged.setdefault((row["osm_type"], row["osm_id"]), row)
    rows = sorted(merged.values(), key=lambda r: r.get("distance_m", float("inf")))[:args.limit]
    _print({"center": [lat, lon], "near": label, "categories": cats, "radius_m": args.radius, "count": len(rows),
            "results": rows, "source": "OpenStreetMap Overpass"})
    _points_out(rows, args.out)


def cmd_bbox(args) -> None:
    s, n = sorted((args.s, args.n))
    w, e = sorted((args.w, args.e))
    try:
        pairs, religion = category_tags(args.category)
    except ValueError as exc:
        sys.exit(str(exc))
    data = _overpass(overpass_ql(pairs, religion, f"{s},{w},{n},{e}"), args.proxy, args.cache)
    rows = parse_elements(data.get("elements", []), ((s + n) / 2, (w + e) / 2))
    total = len(rows)
    rows = rows[:args.limit]
    for r in rows:
        r["category"] = args.category
    _print({"bbox": {"south": s, "west": w, "north": n, "east": e}, "category": args.category, "count": len(rows),
            "total_in_bbox": total, "results": rows, "source": "OpenStreetMap Overpass (nearest to the bbox centre first)"})
    _points_out(rows, args.out)


def cmd_reverse(args) -> None:
    pt, _ = _point_and_rest(args.point)
    if not pt:
        sys.exit("Give a point as lat,lon or lat lon.")
    d = nominatim("reverse", {"lat": pt[0], "lon": pt[1], "addressdetails": 1}, args.proxy)
    if "error" in d:
        sys.exit(f"Reverse geocoding failed: {d['error']}")
    a = d.get("address") or {}
    _print({"lat": pt[0], "lon": pt[1], "display_name": d.get("display_name", ""),
            "address": {"house_number": a.get("house_number", ""), "road": a.get("road", ""),
                        "neighbourhood": a.get("neighbourhood", ""), "suburb": a.get("suburb", ""),
                        "city": a.get("city") or a.get("town") or a.get("village", ""), "county": a.get("county", ""),
                        "state": a.get("state", ""), "postcode": a.get("postcode", ""), "country": a.get("country", ""),
                        "country_code": a.get("country_code", "")},
            "osm_type": d.get("osm_type", ""), "osm_id": d.get("osm_id", ""), "source": "OpenStreetMap Nominatim"})


def _route(args, steps: bool) -> tuple[dict, dict, dict]:
    o = geocode(" ".join(args.origin), args.proxy)
    d = geocode(" ".join(args.to), args.proxy)
    path = f"{o[1]},{o[0]};{d[1]},{d[0]}?overview=false&steps={'true' if steps else 'false'}"
    servers = [OSRM_ROUTES[args.mode], OSRM_FALLBACK]
    data, used, errors = None, None, []
    for base in servers:
        try:
            data = _get_json(f"{base}/{path}", args.proxy, 40)
        except (RuntimeError, ValueError) as e:
            errors.append(f"{urllib.parse.urlsplit(base).netloc}: {str(e)[:80]}")
            continue
        if data.get("code") == "Ok" and data.get("routes"):
            used = base
            break
        errors.append(f"{urllib.parse.urlsplit(base).netloc}: {data.get('message', data.get('code'))}")
    if not used:
        sys.exit(f"OSRM routing failed: {'; '.join(errors)}")
    extra = {"straight_line_km": round(haversine_m(o[:2], d[:2]) / 1000, 3),
             "source": "OSRM " + urllib.parse.urlsplit(used).netloc + "/" + urllib.parse.urlsplit(used).path.strip("/").split("/")[0]}
    if used == OSRM_FALLBACK and args.mode != "driving":
        extra["warning"] = "FOSSGIS router unavailable: router.project-osrm.org routes cars only, so this is a car route and time"
        print(f"WARNING: {extra['warning']}", file=sys.stderr)
    ends = {"origin": {"query": " ".join(args.origin), "display_name": o[2], "lat": o[0], "lon": o[1]},
            "destination": {"query": " ".join(args.to), "display_name": d[2], "lat": d[0], "lon": d[1]}}
    return data["routes"][0], ends, extra


def cmd_distance(args) -> None:
    r, ends, extra = _route(args, False)
    _print({**ends, "mode": args.mode, "distance_km": round(r.get("distance", 0) / 1000, 3),
            "distance_m": round(r.get("distance", 0), 1), "duration_minutes": round(r.get("duration", 0) / 60, 2),
            "duration_seconds": round(r.get("duration", 0), 1), **extra})


def _fmt_s(s: float) -> str:
    return f"{round(s)}s" if s < 60 else (f"{round(s / 60, 1)} min" if s < 3600 else f"{int(s // 3600)}h {round(s % 3600 / 60)}min")


def _instruction(step: dict) -> str:
    m, name = step.get("maneuver") or {}, step.get("name", "")
    kind, mod = m.get("type", ""), m.get("modifier", "")
    onto = f" onto {name}" if name else ""
    return {"depart": f"Depart on {name}" if name else "Depart", "arrive": "Arrive at destination",
            "turn": f"Turn {mod}{onto}", "new name": f"Continue onto {name}" if name else "Continue",
            "merge": f"Merge {mod}{onto}", "fork": f"Take the {mod} fork{onto}",
            "roundabout": f"Enter roundabout, exit{onto}" if name else "Enter roundabout",
            "rotary": f"Enter rotary, exit{onto}" if name else "Enter rotary",
            "end of road": f"At end of road, turn {mod}{onto}",
            "continue": " ".join(x for x in ("Continue", mod, f"on {name}" if name else "") if x),
            "on ramp": f"Take ramp{onto}", "off ramp": f"Take exit{onto}"}.get(kind, f"{kind} {mod} {name}".strip())


def cmd_directions(args) -> None:
    r, ends, extra = _route(args, True)
    steps = []
    for leg in r.get("legs", []):
        for st in leg.get("steps", []):
            steps.append({"step": len(steps) + 1, "instruction": _instruction(st), "distance_m": round(st.get("distance", 0), 1),
                          "duration": _fmt_s(st.get("duration", 0)), "road_name": st.get("name", ""),
                          "maneuver": (st.get("maneuver") or {}).get("type", "")})
    _print({**ends, "mode": args.mode, "total_distance_m": round(r.get("distance", 0), 1),
            "total_duration": _fmt_s(r.get("duration", 0)), "total_duration_s": round(r.get("duration", 0), 1),
            **extra, "step_count": len(steps), "steps": steps})


def _offset_str(sec: int) -> str:
    return f"{'+' if sec >= 0 else '-'}{abs(sec) // 3600:02d}:{abs(sec) % 3600 // 60:02d}"


def _offline_zone(lat: float, lon: float) -> tuple[str, float] | None:
    """(IANA zone, km) of the nearest GeoNames populated place when cities500 is already cached; never downloads."""
    try:
        from geolib.paths import cache_dir
        if not any(cache_dir("geonames").glob("cities500*.pkl")):
            return None
        import geodata
        import numpy as np
        P = geodata.places()
        dist = geodata.haversine_km(lat, lon, P.lat, P.lon)
        i = int(np.argmin(dist))
        return (P.tz[i], float(dist[i])) if P.tz[i] and dist[i] < 300 else None
    except Exception:  # noqa: BLE001 - no numpy / unreadable cache: fall through to the online lookup
        return None


def cmd_timezone(args) -> None:
    pt, _ = _point_and_rest(args.point)
    if not pt:
        sys.exit("Give a point as lat,lon or lat lon.")
    out = {"lat": pt[0], "lon": pt[1], "timezone": None, "utc_offset": None, "current_time": None, "source": None}
    off = _offline_zone(*pt)
    if off:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        try:
            now = datetime.now(ZoneInfo(off[0]))
            out.update(timezone=off[0], utc_offset=_offset_str(int(now.utcoffset().total_seconds())),
                       current_time=now.isoformat(timespec="seconds"), dst_active=bool(now.dst()),
                       source=f"GeoNames nearest populated place ({off[1]:.0f} km, offline)")
        except Exception:  # noqa: BLE001 - zone unknown to the local tz database
            pass
    if not out["timezone"]:
        try:
            d = _get_json(f"{TIMEAPI}?" + urllib.parse.urlencode({"latitude": pt[0], "longitude": pt[1]}), args.proxy, 20)
            cur = d.get("currentUtcOffset") or d.get("standardUtcOffset") or {}
            if isinstance(cur, dict) and "seconds" in cur:        # timeapi.io gives only seconds, no hours/minutes keys
                out["utc_offset"] = _offset_str(int(cur["seconds"]))
            out.update(timezone=d.get("timeZone"), current_time=d.get("currentLocalTime"), source="timeapi.io",
                       dst_active=d.get("isDayLightSavingActive"))
        except (RuntimeError, ValueError, AttributeError) as e:
            print(f"timeapi.io unavailable ({str(e)[:120]}); using the longitude approximation", file=sys.stderr)
    if not out["timezone"]:
        h = round(pt[1] / 15)
        out.update(utc_offset=f"{'+' if h >= 0 else '-'}{abs(h):02d}:00", timezone=f"UTC{'+' if h >= 0 else '-'}{abs(h):02d}:00",
                   source="longitude approximation (lon/15): political zones differ widely")
    _print(out)


def cmd_area(args) -> None:
    q = " ".join(args.place)
    rows = nominatim("search", {"q": q, "limit": 1}, args.proxy)
    if not rows or len(rows[0].get("boundingbox") or []) < 4:
        sys.exit(f"No bounding box for: {q}")
    it = rows[0]
    s, n, w, e = (float(x) for x in it["boundingbox"])
    h_km = haversine_m((s, w), (n, w)) / 1000
    w_km = haversine_m(((s + n) / 2, w), ((s + n) / 2, e)) / 1000
    _print({"query": q, "display_name": it.get("display_name", ""), "lat": float(it["lat"]), "lon": float(it["lon"]),
            "type": it.get("type", ""), "category": it.get("category", ""),
            "bbox": {"south": s, "west": w, "north": n, "east": e}, "bbox_swne": f"{s},{w},{n},{e}",
            "dimensions_km": {"width": round(w_km, 3), "height": round(h_km, 3)}, "approx_area_km2": round(w_km * h_km, 3),
            "osm_type": it.get("osm_type", ""), "osm_id": it.get("osm_id", ""), "source": "OpenStreetMap Nominatim"})


SUBCOMMANDS = ("search", "nearby", "reverse", "distance", "directions", "timezone", "area", "bbox")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="{" + ",".join(SUBCOMMANDS) + "}",
                            help="search is the default: `poi.py \"<name>\" ...` == `poi.py search \"<name>\" ...`")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)

    s = sub.add_parser("search", parents=[common], help="name -> coordinate candidates (360 Maps, Nominatim, Baidu suggestions)")
    s.add_argument("keyword", nargs="+", help="place name, residential compound name, housing development name, or shop name (several words are joined)")
    s.add_argument("--city", help="city name, e.g. <name>市 or <name> (omit to search the whole country)")
    s.add_argument("--region", help="region pack (code or name): sources and Nominatim country come from its services.poi")
    s.add_argument("--sources", help="any of so,osm,sug, comma-separated (default: the region pack's; without one, so,osm,sug for Han-script keywords, else osm)")
    s.add_argument("--limit", type=int, default=10, help="max results per source")
    s.add_argument("--country", help="Nominatim country code (default: the region pack's; without one, no restriction)")
    s.add_argument("--out", type=Path, help="write {name: [lat, lon]} (WGS84) for tiles.py mark / sheet")
    s.set_defaults(func=cmd_search)

    cats = ", ".join(sorted(CATEGORY_TAGS))
    nb = sub.add_parser("nearby", parents=[common], help="POIs of some categories around a point (Overpass)",
                        description=f"Categories: {cats}; or a raw OSM tag key=value.")
    nb.add_argument("point", nargs="*", help="lat,lon (or lat lon), optionally followed by a category")
    nb.add_argument("--near", nargs="+", metavar="PLACE", help="geocode this place (Nominatim) instead of giving a point")
    nb.add_argument("--category", action="append", default=[], metavar="CAT", help="repeatable")
    nb.add_argument("--radius", "-r", type=int, default=500, help="metres, default 500")
    nb.add_argument("--limit", "-n", type=int, default=10)
    nb.add_argument("--cache", type=Path, default=Path(".geo-cache/osm"))
    nb.add_argument("--out", type=Path, help="write {label: [lat, lon]} for tiles.py / board.py add --from")
    nb.set_defaults(func=cmd_nearby)

    rv = sub.add_parser("reverse", parents=[common], help="address of a point (Nominatim)")
    rv.add_argument("point", nargs="+", help="lat,lon or lat lon")
    rv.set_defaults(func=cmd_reverse)

    for name, fn, hlp in (("distance", cmd_distance, "road distance and time between two places (OSRM)"),
                          ("directions", cmd_directions, "turn-by-turn route between two places (OSRM)")):
        r = sub.add_parser(name, parents=[common], help=hlp)
        r.add_argument("origin", nargs="+", help="place name or lat,lon")
        r.add_argument("--to", nargs="+", required=True, metavar="PLACE", help="place name or lat,lon")
        r.add_argument("--mode", "-m", default="driving", choices=list(OSRM_ROUTES))
        r.set_defaults(func=fn)

    tz = sub.add_parser("timezone", parents=[common], help="IANA time zone and current offset of a point (GeoNames cache, else timeapi.io)")
    tz.add_argument("point", nargs="+", help="lat,lon or lat lon")
    tz.set_defaults(func=cmd_timezone)

    ar = sub.add_parser("area", parents=[common], help="bounding box and size of a named place (Nominatim)")
    ar.add_argument("place", nargs="+")
    ar.set_defaults(func=cmd_area)

    bb = sub.add_parser("bbox", parents=[common], help="POIs of one category inside s w n e (Overpass)",
                        description=f"Categories: {cats}; or a raw OSM tag key=value.")
    for k in ("s", "w", "n", "e"):
        bb.add_argument(k, type=float)
    bb.add_argument("category")
    bb.add_argument("--limit", "-n", type=int, default=20)
    bb.add_argument("--cache", type=Path, default=Path(".geo-cache/osm"))
    bb.add_argument("--out", type=Path, help="write {label: [lat, lon]} for tiles.py / board.py add --from")
    bb.set_defaults(func=cmd_bbox)
    return ap


def main(argv: list[str] | None = None) -> None:
    argv = neg_coords(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in SUBCOMMANDS and argv[0] not in ("-h", "--help"):
        argv = ["search", *argv]          # historical CLI: poi.py "<name>" [--city ...]
    args = build_parser().parse_args(argv)
    if isinstance(getattr(args, "keyword", None), list):
        args.keyword = " ".join(args.keyword)
    args.func(args)


if __name__ == "__main__":
    # Chinese Windows outputs GBK by default: it crashes on m² or ñ, and the Chinese the agent reads is garbled
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
