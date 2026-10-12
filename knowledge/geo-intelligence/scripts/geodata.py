#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Offline geodata shared by the other tools: country facts, first-level regions, populated places.

Country facts ship with the skill in assets/data/countries.json (GeoNames country info + driving side).
Places are GeoNames dumps downloaded once into ~/.cache/geoint/geonames (override the root
with GEOINT_CACHE): cities500 (about 200k populated places, 14 MB) and, on demand, a full
per-country gazetteer (villages, mountains, rivers, bridges, schools… for one country).
GeoNames data is CC BY 4.0 (https://www.geonames.org).

  geodata.py fetch                        download admin1 names + cities500 (once)
  geodata.py fetch --country PT           also the full Portugal gazetteer
  geodata.py country "Czech Republic"     facts for one country (name, ISO2/ISO3 or alias)
  geodata.py search "Évora" [--country PT] [--deep]   every place with that name (alternate names included)
  geodata.py reverse 38.57,-7.91          nearest populated place, region, country
  geodata.py sample PT --n 8 [--admin1 Alentejo]      random towns weighted by population (for reference sheets)
  geodata.py towns PE --admin1 Cusco --top 15             the biggest towns of a region: every one is a candidate
  geodata.py towns --near 30.92,-6.89 --radius 250         the biggest towns within 250 km of a point (any country)
  geodata.py build-countries              rebuild assets/data/countries.json (maintainers)

Reverse geocoding uses the nearest populated place, so within a few km of a border the
country can be wrong; treat it as a label for model outputs, not as a border test.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import pickle
import re
import subprocess
import sys
import unicodedata
import zipfile
from functools import lru_cache
from pathlib import Path

try:  # country lookups work without numpy (board.py imports this module with no dependencies)
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geolib.cli import neg_coords  # noqa: E402
from geolib.net import PROXY_HELP, curl_args, fetch_bytes  # noqa: E402
from geolib.paths import DATA_DIR as DATA, cache_dir  # noqa: E402  (cache_dir: textgeo.py and prior.py reach it through this module)

GEONAMES = "https://download.geonames.org/export/dump/"
NOMINATIM_UA = "geo-intelligence/1.0 (+https://github.com/AeonDave/malskill)"   # Nominatim's usage policy wants an identifying client
PLACES_FILE = "cities500"
CACHE_VERSION = 3

# Western Sahara is part of Morocco here. GeoNames codes some of Morocco's southern provinces as "EH" (Laâyoune, Dakhla,
# Boujdour…) and others as MA (Smara, Tarfaya, Aousserd); every such place is read as MA, in its Moroccan region:
# Laâyoune–Sakia El Hamra (MA.11) north of ≈ 24° N, Dakhla–Oued Ed-Dahab (MA.12) south of it.
COUNTRY_MERGE = {"EH": "MA"}
MA_SOUTH_SPLIT_LAT = 24.0

CONTINENTS = {"AF": "Africa", "AS": "Asia", "EU": "Europe", "NA": "North America", "OC": "Oceania",
              "SA": "South America", "AN": "Antarctica"}
NAME_OVERRIDES = {"NL": "Netherlands", "PS": "Palestine", "MO": "Macau", "BQ": "Caribbean Netherlands"}
ALIASES = {
    "usa": "US", "us": "US", "united states of america": "US", "america": "US", "u s a": "US",
    "uk": "GB", "u k": "GB", "great britain": "GB", "britain": "GB", "england": "GB", "scotland": "GB",
    "wales": "GB", "northern ireland": "GB", "czech republic": "CZ", "korea": "KR", "republic of korea": "KR",
    "korea south": "KR", "korea republic of": "KR", "north korea": "KP", "dprk": "KP", "korea north": "KP",
    "russian federation": "RU", "holland": "NL", "the netherlands": "NL", "cote d ivoire": "CI",
    "turkiye": "TR", "turkey": "TR", "swaziland": "SZ", "burma": "MM", "east timor": "TL", "timor leste": "TL",
    "timor": "TL", "vatican city": "VA", "holy see": "VA", "vatican": "VA", "macao": "MO", "macau": "MO",
    "state of palestine": "PS", "palestinian territories": "PS", "palestinian territory": "PS", "west bank": "PS",
    "gaza": "PS", "gaza strip": "PS", "cape verde": "CV", "macedonia": "MK", "dr congo": "CD", "drc": "CD",
    "congo kinshasa": "CD", "democratic republic of congo": "CD", "congo dr": "CD", "congo democratic republic of the": "CD",
    "congo brazzaville": "CG", "congo": "CG", "congo republic": "CG", "uae": "AE", "emirates": "AE",
    "lao pdr": "LA", "lao": "LA", "viet nam": "VN", "brunei darussalam": "BN", "federated states of micronesia": "FM",
    "micronesia federated states of": "FM", "bosnia": "BA", "bosnia herzegovina": "BA", "trinidad": "TT",
    "trinidad tobago": "TT", "st lucia": "LC", "st kitts and nevis": "KN", "st kitts": "KN",
    "st vincent and the grenadines": "VC", "st vincent": "VC", "the gambia": "GM", "the bahamas": "BS",
    "falklands": "FK", "falkland islands malvinas": "FK", "faroes": "FO", "faeroe islands": "FO",
    "us virgin islands": "VI", "united states virgin islands": "VI", "virgin islands u s": "VI",
    "british virgin islands": "VG", "virgin islands british": "VG", "hong kong sar": "HK", "hong kong sar china": "HK",
    "macau sar": "MO", "reunion": "RE", "curacao": "CW", "sao tome": "ST", "sao tome and principe": "ST",
    "saint barthelemy": "BL", "st barthelemy": "BL", "st martin": "MF", "sint maarten": "SX",
    "saint helena ascension and tristan da cunha": "SH", "st helena": "SH", "pitcairn islands": "PN",
    "cocos keeling islands": "CC", "keeling islands": "CC", "wallis and futuna islands": "WF",
    "svalbard": "SJ", "jan mayen": "SJ", "aland": "AX", "aland islands": "AX", "eswatini": "SZ",
    "kyrgyz republic": "KG", "slovak republic": "SK", "bahamas the": "BS", "gambia the": "GM",
    "iran islamic republic of": "IR", "syrian arab republic": "SY", "republic of moldova": "MD",
    "united republic of tanzania": "TZ", "venezuela bolivarian republic of": "VE", "bolivia plurinational state of": "BO",
    "taiwan province of china": "TW", "republic of china": "TW", "roc": "TW", "prc": "CN",
    "peoples republic of china": "CN", "mainland china": "CN", "south georgia": "GS", "caribbean netherlands": "BQ",
    "bonaire": "BQ", "saba": "BQ", "sint eustatius": "BQ", "abkhazia": "GE", "south ossetia": "GE",
    "northern cyprus": "CY", "transnistria": "MD", "somaliland": "SO", "western sahara": "MA", "moroccan sahara": "MA", "eh": "MA", "esh": "MA",
    "ivory coast": "CI", "cabo verde": "CV", "north macedonia": "MK", "republic of north macedonia": "MK",
    "guinea bissau": "GW", "papua new guinea": "PG", "png": "PG", "nz": "NZ", "aus": "AU", "rsa": "ZA",
    "azores": "PT", "madeira": "PT", "canary islands": "ES", "canaries": "ES", "balearic islands": "ES",
    "united kingdom and overseas territories": "GB", "hawaii": "US", "alaska": "US", "corsica": "FR", "sicily": "IT",
    "sardinia": "IT", "crete": "GR", "tasmania": "AU", "zanzibar": "TZ", "tibet": "CN", "xinjiang": "CN",
}


# ------------------------------------------------------------------ helpers

def norm(s: str) -> str:
    """Case- and accent-insensitive key: 'São Tomé' → 'sao tome', 'München' → 'munchen'; other scripts kept."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).casefold()
    return re.sub(r"[\W_]+", " ", s, flags=re.UNICODE).strip()


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km; accepts numpy arrays."""
    la1, lo1, la2, lo2 = (np.radians(np.asarray(v, dtype=float)) for v in (lat1, lon1, lat2, lon2))
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def download(url: str, dest: Path, proxy: str | None = None, timeout: int = 900) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f"{dest.name}.{os.getpid()}.part")
    cmd = ["curl", "-q", "-fsSL", "--retry", "2", "--max-time", str(timeout), *curl_args(proxy), "-o", str(tmp), url]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Download failed (curl exit {r.returncode}) for {url}: {r.stderr.strip()[-200:]}")
    tmp.replace(dest)
    return dest


# ------------------------------------------------------------------ countries

@lru_cache(maxsize=1)
def countries() -> dict[str, dict]:
    """ISO2 → country facts (bundled assets/data/countries.json)."""
    p = DATA / "countries.json"
    if not p.exists():
        sys.exit("assets/data/countries.json is missing: run `geodata.py build-countries`")
    d = json.loads(p.read_text(encoding="utf-8"))
    return {k: v for k, v in d.items() if not k.startswith("_")}


@lru_cache(maxsize=1)
def _country_keys() -> dict[str, str]:
    keys = {}
    for cc, c in countries().items():
        for k in (cc, c.get("iso3", ""), c["name"], c.get("geonames_name", "")):
            if k:
                keys[norm(k)] = cc
    for k, cc in ALIASES.items():
        keys.setdefault(norm(k), cc)
    return keys


def _lookup_cc(q: str) -> str | None:
    cc = _country_keys().get(norm(q))
    if not cc:
        # tolerate "Republic of X", "X (country)" and similar wrappers
        s = re.sub(r"\(.*?\)", "", str(q))
        s = re.sub(r"^(the|republic of|kingdom of|state of|commonwealth of)\s+", "", norm(s))
        cc = _country_keys().get(norm(s))
    return cc


@lru_cache(maxsize=1)
def _country_name_keys() -> dict[str, str]:
    """Chinese names (simplified and traditional), former names and abbreviations from assets/data/country_names.json → ISO2.
    Consulted only after codes, English names and ALIASES fail; entries whose English name is unknown here are dropped."""
    p = DATA / "country_names.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    keys: dict[str, str] = {}
    for en, zh in (d.get("en2zh") or {}).items():
        cc = _lookup_cc(en)
        if cc:
            keys.setdefault(norm(zh), cc)
    for alias, en in (d.get("aliases") or {}).items():
        cc = _lookup_cc(en)
        if cc:
            keys.setdefault(norm(alias), cc)
    return keys


def country(q: str) -> dict | None:
    """Country facts by ISO2, ISO3, English name or alias (incl. Chinese and former names); None if unknown."""
    if not q:
        return None
    cc = _lookup_cc(q) or _country_name_keys().get(norm(q))
    return countries().get(cc) if cc else None


def country_name(cc: str) -> str:
    c = countries().get((cc or "").upper())
    return c["name"] if c else cc


# ------------------------------------------------------------------ admin1

@lru_cache(maxsize=1)
def admin1(proxy: str | None = None) -> dict[str, dict]:
    """'CC.code' → {name, ascii}; downloads admin1CodesASCII.txt once."""
    p = cache_dir("geonames") / "admin1CodesASCII.txt"
    if not p.exists():
        download(GEONAMES + "admin1CodesASCII.txt", p, proxy)
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            out[parts[0]] = {"name": parts[1], "ascii": parts[2]}
    return out


def admin1_name(cc: str, code: str) -> str:
    try:
        return admin1().get(f"{cc}.{code}", {}).get("name", code or "")
    except Exception:  # noqa: BLE001 - names are a convenience; never fail a lookup over them
        return code or ""


ADMIN_WORDS = re.compile(r"\b(voivodeship|province|provincia|region|regione|krai|kray|oblast|okrug|republic|county|"
                         r"state|prefecture|governorate|department|departement|district|autonomous|community|"
                         r"municipality|the|of)\b")


def _admin_key(s: str) -> str:
    return re.sub(r"\s+", " ", ADMIN_WORDS.sub(" ", norm(s))).strip()


def admin1_codes(cc: str, query: str) -> list[str]:
    """Admin1 codes in country cc whose name or code matches query: exact, then ignoring words such as
    'Voivodeship', 'Krai', 'Oblast', 'Province', then substring either way ('Pomeranian' → 'Pomerania')."""
    q = norm(query)
    rows = [(k.split(".", 1)[1], v) for k, v in admin1().items() if k.startswith(cc.upper() + ".")]
    exact = [c for c, v in rows if q in (norm(c), norm(v["name"]), norm(v["ascii"]))]
    if exact:
        return exact
    qk = _admin_key(query)
    keyed = [c for c, v in rows if qk and qk in (_admin_key(v["name"]), _admin_key(v["ascii"]))]
    if keyed:
        return keyed
    sub = [c for c, v in rows if q and (q in norm(v["name"]) or q in norm(v["ascii"]))]
    if sub:
        return sub
    return [c for c, v in rows if qk and len(_admin_key(v["ascii"])) >= 4 and _admin_key(v["ascii"]) in qk]


def regions(cc: str) -> dict[str, dict]:
    """First-level regions of a country with a population-weighted centre and an extent from its populated places."""
    P = places()
    cc = cc.upper()
    ccs = np.array(P.cc)
    a1s = np.array(P.a1)
    out: dict[str, dict] = {}
    for key, v in admin1().items():
        if not key.startswith(cc + "."):
            continue
        code = key.split(".", 1)[1]
        m = (ccs == cc) & (a1s == code)
        rec = {"code": code, "ascii": v["ascii"]}
        if m.any():
            la, lo, w = P.lat[m].astype(float), P.lon[m].astype(float), P.pop[m].astype(float) + 50.0
            rec["center"] = [round(float(np.average(la, weights=w)), 4), round(float(np.average(lo, weights=w)), 4)]
            pad = 0.05
            rec["bbox"] = [round(float(la.min()) - pad, 3), round(float(lo.min()) - pad, 3),
                           round(float(la.max()) + pad, 3), round(float(lo.max()) + pad, 3)]
            rec["places"] = int(m.sum())
        out[v["name"]] = rec
    return out


def admin1_names(cc: str) -> list[str]:
    return sorted(v["name"] for k, v in admin1().items() if k.startswith(cc.upper() + "."))


# ------------------------------------------------------------------ places

class Places:
    """Columnar GeoNames places with a name index (name, ascii name and alternate names)."""

    def __init__(self, d: dict):
        self.__dict__.update(d)

    def __len__(self) -> int:
        return len(self.lat)

    def row(self, i: int, dist_km: float | None = None) -> dict:
        cc = self.cc[i]
        r = {"name": self.name[i], "country": cc, "country_name": country_name(cc),
             "admin1": admin1_name(cc, self.a1[i]), "admin1_code": self.a1[i],
             "lat": round(float(self.lat[i]), 5), "lon": round(float(self.lon[i]), 5),
             "population": int(self.pop[i]), "feature": self.fcode[i], "geonameid": int(self.gid[i])}
        if dist_km is not None:
            r["distance_km"] = round(float(dist_km), 2)
        return r


def _parse_geonames(text: io.TextIOBase) -> dict:
    lat, lon, pop, gid = [], [], [], []
    name, cc, a1, fcode, tz = [], [], [], [], []
    index: dict[str, list[int]] = {}
    for line in text:
        p = line.rstrip("\n").split("\t")
        if len(p) < 19:
            continue
        i = len(lat)
        gid.append(int(p[0]))
        name.append(p[1])
        lat.append(float(p[4]))
        lon.append(float(p[5]))
        fcode.append(f"{p[6]}.{p[7]}")
        c, r = p[8], p[10]
        if c in COUNTRY_MERGE:
            c = COUNTRY_MERGE[c]
            if r not in ("11", "12"):
                r = "11" if float(p[4]) >= MA_SOUTH_SPLIT_LAT else "12"
        cc.append(c)
        a1.append(r)
        pop.append(int(p[14] or 0))
        tz.append(p[17])
        keys = {norm(p[1]), norm(p[2])}
        for alt in p[3].split(","):
            if 2 <= len(alt) <= 80 and not alt.startswith("http") and any(ch.isalpha() for ch in alt):
                keys.add(norm(alt))
        for k in keys:
            if k:
                index.setdefault(k, []).append(i)
    return {"lat": np.array(lat, dtype=np.float32), "lon": np.array(lon, dtype=np.float32),
            "pop": np.array(pop, dtype=np.int64), "gid": np.array(gid, dtype=np.int64),
            "name": name, "cc": cc, "a1": a1, "fcode": fcode, "tz": tz, "index": index}


def _load_dump(stem: str, url: str, proxy: str | None) -> Places:
    base = cache_dir("geonames")
    pkl = base / f"{stem}.v{CACHE_VERSION}.pkl"
    if pkl.exists():
        with pkl.open("rb") as f:
            return Places(pickle.load(f))
    z = base / f"{stem}.zip"
    if not z.exists():
        print(f"Downloading {url} (one time) …", file=sys.stderr)
        download(url, z, proxy)
    with zipfile.ZipFile(z) as zf:
        member = next(n for n in zf.namelist() if n.endswith(".txt") and not n.lower().startswith("readme"))
        with zf.open(member) as raw:
            d = _parse_geonames(io.TextIOWrapper(raw, encoding="utf-8"))
    tmp = pkl.with_name(f"{pkl.name}.{os.getpid()}.tmp")  # atomic: parallel sessions may build the same cache
    with tmp.open("wb") as f:
        pickle.dump(d, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, pkl)
    return Places(d)


@lru_cache(maxsize=1)
def places(proxy: str | None = None) -> Places:
    """Worldwide populated places (GeoNames cities500)."""
    return _load_dump(PLACES_FILE, GEONAMES + f"{PLACES_FILE}.zip", proxy)


def _concat(a: Places, b: Places) -> Places:
    """Two GeoNames dumps as one (b's name index shifted after a's rows)."""
    n = len(a)
    index = {k: list(v) for k, v in a.index.items()}
    for k, v in b.index.items():
        index.setdefault(k, []).extend(i + n for i in v)
    d = {k: (np.concatenate([getattr(a, k), getattr(b, k)]) if k in ("lat", "lon", "pop", "gid") else getattr(a, k) + getattr(b, k))
         for k in ("lat", "lon", "pop", "gid", "name", "cc", "a1", "fcode", "tz")}
    d["index"] = index
    return Places(d)


@lru_cache(maxsize=8)
def country_gazetteer(cc: str, proxy: str | None = None) -> Places:
    """Every GeoNames feature in one country (populated places, hills, streams, bridges, schools, farms…)."""
    cc = cc.upper()
    if not re.fullmatch(r"[A-Z]{2}", cc):
        raise ValueError(f"Not an ISO2 country code: {cc}")
    cc = COUNTRY_MERGE.get(cc, cc)
    P = _load_dump(f"country_{cc}", GEONAMES + f"{cc}.zip", proxy)
    for src, dst in COUNTRY_MERGE.items():  # Morocco's gazetteer includes GeoNames' EH file (see COUNTRY_MERGE)
        if dst == cc:
            P = _concat(P, _load_dump(f"country_{src}", GEONAMES + f"{src}.zip", proxy))
    return P


def reverse(lat: float, lon: float, k: int = 1, min_pop: int = 0) -> list[dict]:
    """Nearest populated places to a point (k results, nearest first)."""
    P = places()
    w = 0.5
    while True:
        dlon = min(180.0, w / max(math.cos(math.radians(lat)), 0.05))
        m = (np.abs(P.lat - lat) <= w) & ((np.abs(P.lon - lon) <= dlon) | (np.abs(P.lon - lon) >= 360 - dlon))
        if min_pop:
            m &= P.pop >= min_pop
        idx = np.nonzero(m)[0]
        if len(idx) >= k or w >= 90:
            break
        w *= 2
    if not len(idx):
        return []
    d = haversine_km(lat, lon, P.lat[idx], P.lon[idx])
    order = np.argsort(d)[:k]
    return [P.row(int(idx[o]), d[o]) for o in order]


def reverse_country(lat: float, lon: float) -> str:
    r = reverse(lat, lon, 1)
    return r[0]["country"] if r else ""


def search(text: str, cc: str | None = None, limit: int = 25, deep: bool = False,
           proxy: str | None = None) -> list[dict]:
    """Places whose name or alternate name equals text (accent/case-insensitive), largest first.
    deep=True searches the full gazetteer of country cc (needs cc)."""
    key = norm(text)
    if not key:
        return []
    if deep:
        if not cc:
            raise ValueError("deep search needs a country code")
        P = country_gazetteer(cc, proxy)
    else:
        P = places(proxy)
    idx = P.index.get(key, [])
    if cc:
        idx = [i for i in idx if P.cc[i] == cc.upper()]
    # primary-name matches before alternate names (historical/foreign names such as Augusta → Augsburg)
    primary = {i for i in idx if norm(P.name[i]) == key}
    idx = sorted(idx, key=lambda i: (i not in primary, -int(P.pop[i])))[:limit]
    return [{**P.row(i), "match": "name" if i in primary else "alternate"} for i in idx]


def sample(cc: str, n: int, admin1_query: str | None = None, alpha: float = 0.5, seed: int | None = None,
           min_pop: int = 0) -> list[dict]:
    """n distinct towns in country cc (optionally one admin1 region), weighted by population**alpha."""
    P = places()
    cc = cc.upper()
    mask = np.array([c == cc for c in P.cc]) & (P.pop >= min_pop)
    if admin1_query:
        codes = set(admin1_codes(cc, admin1_query))
        if not codes:
            raise ValueError(f"No region matching '{admin1_query}' in {cc}")
        mask &= np.array([a in codes for a in P.a1])
    idx = np.nonzero(mask)[0]
    if not len(idx):
        return []
    w = (P.pop[idx].astype(float) + 50.0) ** alpha
    rng = np.random.default_rng(seed)
    pick = rng.choice(idx, size=min(n, len(idx)), replace=False, p=w / w.sum())
    return [P.row(int(i)) for i in pick]


def towns(cc: str | None = None, admin1_query: str | None = None, near: tuple[float, float] | None = None,
          radius_km: float = 100.0, top: int = 20, min_pop: int = 0) -> list[dict]:
    """The largest populated places of a country, one of its regions, and/or a radius around a point, biggest
    first. Sections of towns, abandoned and historical places are left out (GeoNames PPLX/PPLQ/PPLH/PPLW)."""
    P = places()
    mask = P.pop >= min_pop
    if cc:
        mask &= np.array([c == cc.upper() for c in P.cc])
    if admin1_query:
        if not cc:
            raise ValueError("--admin1 needs a country")
        codes = set(admin1_codes(cc.upper(), admin1_query))
        if not codes:
            raise ValueError(f"No region matching '{admin1_query}' in {cc} (see: geodata.py regions {cc})")
        mask &= np.array([a in codes for a in P.a1])
    if near:
        mask &= haversine_km(near[0], near[1], P.lat, P.lon) <= radius_km
    mask &= np.array([not f.endswith(("PPLX", "PPLQ", "PPLH", "PPLW", "PPLCH")) for f in P.fcode])
    idx = np.nonzero(mask)[0]
    idx = idx[np.argsort(-P.pop[idx], kind="stable")][:top]
    return [P.row(int(i), haversine_km(near[0], near[1], P.lat[i], P.lon[i]) if near else None) for i in idx]


# ------------------------------------------------------------------ build countries.json

def build_countries(proxy: str | None) -> dict:
    try:
        text = fetch_bytes(GEONAMES + "countryInfo.txt", proxy, 60).decode("utf-8")
    except RuntimeError as e:
        sys.exit(f"Could not fetch countryInfo.txt: {e}")
    out: dict[str, dict] = {}
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        p = line.split("\t")
        if len(p) < 18:
            continue
        cc = p[0]
        if cc in ("CS", "AN"):  # Serbia and Montenegro, Netherlands Antilles: dissolved, kept by GeoNames for history
            continue
        out[cc] = {"iso2": cc, "iso3": p[1], "name": NAME_OVERRIDES.get(cc, p[4].strip()), "geonames_name": p[4].strip(),
                   "capital": p[5], "area_km2": float(p[6] or 0), "population": int(p[7] or 0),
                   "continent": p[8], "continent_name": CONTINENTS.get(p[8], p[8]), "tld": p[9],
                   "currency": p[10], "currency_name": p[11], "phone": p[12], "postal_format": p[13],
                   "postal_regex": p[14], "languages": [x for x in p[15].split(",") if x],
                   "neighbours": [x for x in p[17].split(",") if x], "geonameid": int(p[16] or 0)}
    # Western Sahara is part of Morocco (COUNTRY_MERGE): its area and population count for MA, borders point to MA
    for src, dst in COUNTRY_MERGE.items():
        e = out.pop(src, None)
        if e and dst in out:
            out[dst]["area_km2"] += e["area_km2"]
            out[dst]["population"] += e["population"]
            out[dst]["neighbours"] += e["neighbours"]
        for c in out.values():
            nb = [dst if n == src else n for n in c["neighbours"]]
            c["neighbours"] = [n for i, n in enumerate(nb) if n != c["iso2"] and n not in nb[:i]]
    # driving side from the bundled Wikipedia-derived table (keyed by English name)
    ds = json.loads((DATA / "driving_side.json").read_text(encoding="utf-8"))
    keys = {norm(v["name"]): k for k, v in out.items()} | {norm(v["geonames_name"]): k for k, v in out.items()}
    keys.update({norm(k): v for k, v in ALIASES.items()})
    unmatched = []
    for name, v in ds.items():
        if name.startswith("_"):
            continue
        cc = keys.get(norm(name)) or keys.get(norm(re.sub(r"\(.*?\)", "", name)))
        if not cc or cc not in out:
            unmatched.append(name)
            continue
        if out[cc].get("drive") and out[cc]["drive"] != v["side"]:
            out[cc]["drive_note"] = (out[cc].get("drive_note", "") + f" Mixed: {name} {v['side']}.").strip()
            continue
        out[cc]["drive"] = v["side"]
        if v.get("note"):
            out[cc]["drive_note"] = v["note"]
    # Territories whose traffic side differs from the sovereign's entry in the Wikipedia table
    for cc, side in {"HK": "left", "MO": "left", "CN": "right", "GI": "right", "VI": "left", "GB": "left",
                     "CC": "left", "CX": "left", "NF": "left", "PN": "left", "AX": "right", "BL": "right",
                     "BQ": "right", "MF": "right", "PM": "right", "WF": "right"}.items():
        if cc in out:
            out[cc]["drive"] = side
    # Population-weighted centre and a robust extent from populated places, when the cache exists
    try:
        P = places(proxy)
        ccs = np.array(P.cc)
        for cc, c in out.items():
            m = ccs == cc
            if not m.any():
                continue
            la, lo, w = P.lat[m].astype(float), P.lon[m].astype(float), (P.pop[m].astype(float) + 50.0)
            if lo.max() - lo.min() > 180:  # crosses the antimeridian: shift to 0..360 for the averages
                lo = np.where(lo < 0, lo + 360, lo)
            clon = float(np.average(lo, weights=w))
            c["center"] = [round(float(np.average(la, weights=w)), 4), round(((clon + 180) % 360) - 180, 4)]
            if m.sum() >= 5 and np.percentile(lo, 99.5) - np.percentile(lo, 0.5) < 180:
                q = lambda a, x: float(np.percentile(a, x))  # noqa: E731
                c["bbox"] = [round(q(la, 0.5), 3), round(((q(lo, 0.5) + 180) % 360) - 180, 3),
                             round(q(la, 99.5), 3), round(((q(lo, 99.5) + 180) % 360) - 180, 3)]
    except Exception as e:  # noqa: BLE001
        print(f"centres skipped: {e}", file=sys.stderr)
    meta = {"source": ["https://download.geonames.org/export/dump/countryInfo.txt (CC BY 4.0)",
                       "assets/data/driving_side.json (Wikipedia, CC BY-SA 4.0)"],
            "note": "center/bbox are population-weighted from GeoNames cities500; bbox is a 0.5–99.5 percentile extent "
                    "of populated places, omitted for countries spanning the antimeridian.",
            "count": len(out), "unmatched_driving_side_names": unmatched}
    return {"_meta": meta, **dict(sorted(out.items()))}


# ------------------------------------------------------------------ CLI

def _latlon(s: str) -> tuple[float, float]:
    a, b = (float(x) for x in s.replace(" ", "").split(","))
    return a, b


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--country", action="append", help="ISO2 code(s) for a full national gazetteer, repeatable")
    c = sub.add_parser("country")
    c.add_argument("query")
    s = sub.add_parser("search")
    s.add_argument("name")
    s.add_argument("--country")
    s.add_argument("--deep", action="store_true", help="search the full national gazetteer (needs --country)")
    s.add_argument("--limit", type=int, default=25)
    s.add_argument("--json", action="store_true", help="full JSON instead of a compact table")
    r = sub.add_parser("reverse")
    r.add_argument("latlon")
    r.add_argument("-k", type=int, default=3)
    r.add_argument("--osm", action="store_true", help="also ask OpenStreetMap Nominatim for the street/neighbourhood (sends the coordinates)")
    sm = sub.add_parser("sample")
    sm.add_argument("country")
    sm.add_argument("--n", type=int, default=8)
    sm.add_argument("--admin1")
    sm.add_argument("--seed", type=int)
    sm.add_argument("--min-pop", type=int, default=0)
    tw = sub.add_parser("towns", help="largest towns of a country / region / radius, biggest first")
    tw.add_argument("country", nargs="?")
    tw.add_argument("--admin1", help="first-level region name (fuzzy), e.g. 'Cusco'")
    tw.add_argument("--near", help="lat,lon")
    tw.add_argument("--radius", type=float, default=100, help="km around --near")
    tw.add_argument("--top", type=int, default=20)
    tw.add_argument("--min-pop", type=int, default=0)
    tw.add_argument("--json", action="store_true")
    rg = sub.add_parser("regions", help="first-level regions of a country with centre and extent (JSON)")
    rg.add_argument("country")
    rg.add_argument("--out")
    sub.add_parser("build-countries")
    args = ap.parse_args(neg_coords(sys.argv[1:]))

    if args.cmd == "fetch":
        admin1(args.proxy)
        P = places(args.proxy)
        print(f"admin1 names: {len(admin1())}; places: {len(P)} ({PLACES_FILE}) in {cache_dir('geonames')}")
        for cc in args.country or []:
            G = country_gazetteer(cc, args.proxy)
            print(f"{cc.upper()} gazetteer: {len(G)} features")
    elif args.cmd == "country":
        c = country(args.query)
        print(json.dumps(c, ensure_ascii=False, indent=1) if c else f"Unknown country: {args.query}")
    elif args.cmd == "search":
        cc = None
        if args.country:
            c = country(args.country)
            cc = c["iso2"] if c else args.country.upper()
        rows = search(args.name, cc, args.limit, args.deep, args.proxy)
        if not rows:
            print("No place with that name" + ("" if args.deep or not cc else " (try --deep for the full national gazetteer)"))
        elif args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
        else:
            print(f"{'name':<28} {'region':<24} {'cc':<3} {'lat':>9} {'lon':>10} {'pop':>9}  type")
            for r in rows:
                alt = " (alt name)" if r.get("match") == "alternate" else ""
                print(f"{r['name'][:28]:<28} {r['admin1'][:24]:<24} {r['country']:<3} {r['lat']:>9.4f} {r['lon']:>10.4f} "
                      f"{r['population']:>9}  {r['feature']}{alt}")
    elif args.cmd == "reverse":
        lat, lon = _latlon(args.latlon)
        out = {"nearest_places": reverse(lat, lon, args.k)}
        if args.osm:
            url = ("https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=17&addressdetails=1&accept-language=en&"
                   f"lat={lat}&lon={lon}")
            # Optional enrichment: any failure (curl exit, timeout, malformed body) is reported in-band, never a traceback
            try:
                d = json.loads(fetch_bytes(url, args.proxy, 20, {"User-Agent": NOMINATIM_UA}).decode("utf-8", "replace"))
                out["osm"] = {"display_name": d.get("display_name"), "address": d.get("address")}
            except Exception as e:  # noqa: BLE001
                out["osm"] = {"error": f"Nominatim unavailable ({e})"}
        print(json.dumps(out, ensure_ascii=False, indent=1))
    elif args.cmd == "sample":
        c = country(args.country)
        if not c:
            sys.exit(f"Unknown country: {args.country}")
        print(json.dumps(sample(c["iso2"], args.n, args.admin1, seed=args.seed, min_pop=args.min_pop),
                         ensure_ascii=False, indent=1))
    elif args.cmd == "towns":
        cc = None
        if args.country:
            c = country(args.country)
            if not c:
                sys.exit(f"Unknown country: {args.country}")
            cc = c["iso2"]
        if not cc and not args.near:
            sys.exit("give a country and/or --near lat,lon")
        near = _latlon(args.near) if args.near else None
        rows = towns(cc, args.admin1, near, args.radius, args.top, args.min_pop)
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
        else:
            print(f"{'name':<26} {'region':<24} {'cc':<3} {'population':>10} {'lat':>9} {'lon':>10}" + ("  km" if near else ""))
            for r in rows:
                print(f"{r['name'][:26]:<26} {r['admin1'][:24]:<24} {r['country']:<3} {r['population']:>10} {r['lat']:>9.4f} "
                      f"{r['lon']:>10.4f}" + (f"  {r['distance_km']:.0f}" if near else ""))
    elif args.cmd == "regions":
        c = country(args.country)
        if not c:
            sys.exit(f"Unknown country: {args.country}")
        rows = regions(c["iso2"])
        txt = json.dumps(rows, ensure_ascii=False, indent=1)
        if args.out:
            Path(args.out).write_text(txt, encoding="utf-8")
            print(f"{len(rows)} first-level regions of {c['name']} → {args.out}")
        else:
            print(txt)
    elif args.cmd == "build-countries":
        d = build_countries(args.proxy)
        (DATA / "countries.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        um = d["_meta"]["unmatched_driving_side_names"]
        print(f"Wrote {DATA / 'countries.json'}: {d['_meta']['count']} countries; driving side unmatched: {um}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
