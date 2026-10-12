#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Maintainer tool: re-fetch the bundled lookup tables from their sources and rewrite them in the shared formats.

Global tables go to assets/data/; the China pack's tables go to assets/data/regions/cn/data/ in the prefix-table and
admin-table formats (regions.py docstring). Lookups never call this; they read the JSON only.

  refresh.py [table|all]       tables: calling_codes driving_side territories plate_codes cn/admin cn/plates cn/area_codes
  refresh.py all --from-dir D  parse already-downloaded source files instead of fetching (names in LOCAL_NAMES;
                               plate_codes reads plates_<CC>.html)
  clues.py update [table]      the same (old table names cn_plates / cn_area_codes / cn_admin are accepted)

cn/plates and cn/area_codes resolve place names against cn/admin, so refresh cn/admin first (all does).
driving_side keeps every row marked "curated" in the current table (hand corrections the scrape would undo).
"""
from __future__ import annotations

import argparse
import html as H
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from geolib.net import curl_args, PROXY_HELP  # noqa: E402
from geolib.paths import DATA_DIR  # noqa: E402

DATA = DATA_DIR
CN = DATA_DIR / "regions" / "cn" / "data"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

SOURCES = {
    "calling_codes": ["https://en.wikipedia.org/wiki/List_of_telephone_country_codes"],
    "driving_side": ["https://en.wikipedia.org/wiki/Left-_and_right-hand_traffic"],
    "territories": ["https://en.wikipedia.org/wiki/List_of_dependent_territories"],
    "cn/admin": ["https://raw.githubusercontent.com/modood/Administrative-divisions-of-China/master/dist/pca-code.json"],
    "cn/plates": ["https://zh.wikipedia.org/zh-cn/中华人民共和国民用机动车号牌"],
    "cn/area_codes": ["https://zh.wikipedia.org/zh-cn/中国大陆固定电话号码"],
    "plate_codes": ["https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Europe (one page per country, see PLATE_PAGES)"],
}
LOCAL_NAMES = {"cn/plates": "plates_zh.html", "cn/area_codes": "areacodes2_zh.html", "calling_codes": "calling_en.html",
               "driving_side": "driving_en.html", "territories": "dependent_en.html", "cn/admin": "pca-code.json"}
LICENSE = {"cn/admin": "WTFPL (modood/Administrative-divisions-of-China)"}
WIKI_LICENSE = "Derived from Wikipedia, CC BY-SA 4.0"

# Letter splits inside municipalities: source is common knowledge of the former prefecture divisions; the Wikipedia page only goes down to “重庆市” (Chongqing). Marked unverified; verify before use.
MUNICIPAL_LETTER_NOTES = {
    "渝": {"A": "main urban districts", "B": "main urban districts", "C": "永川、江津、合川、璧山、铜梁、大足、荣昌、潼南 (former 永川 prefecture)", "D": "main urban districts (added later)",
          "F": "万州、开州、梁平、忠县、云阳、奉节、巫山、巫溪、城口 (former 万县 prefecture)", "G": "涪陵、南川、垫江、丰都、武隆 (former 涪陵 prefecture)",
          "H": "黔江、石柱、秀山、酉阳、彭水 (former 黔江 prefecture)"},
}

# Wikipedia's “List of dependent territories” leaves out overseas territories integrated into the home country (French overseas departments, Spain's Canaries, US Hawaii…), but they are exactly the intersection that “IP country × hinted continent” is looking for, so they are added here.
# Sources: Wikipedia Overseas France / Outermost regions of the EU / per-country articles; region/subregion follow the UN geoscheme.
INTEGRAL_OVERSEAS = [
    {"name": "French Guiana", "sovereign": "France", "region": "Americas", "subregion": "South America", "status": "Overseas department and region (integral part of France, EU)"},
    {"name": "Guadeloupe", "sovereign": "France", "region": "Americas", "subregion": "Caribbean", "status": "Overseas department and region"},
    {"name": "Martinique", "sovereign": "France", "region": "Americas", "subregion": "Caribbean", "status": "Overseas department and region"},
    {"name": "Réunion", "sovereign": "France", "region": "Africa", "subregion": "Eastern Africa", "status": "Overseas department and region"},
    {"name": "Mayotte", "sovereign": "France", "region": "Africa", "subregion": "Eastern Africa", "status": "Overseas department and region"},
    {"name": "Saint Martin", "sovereign": "France", "region": "Americas", "subregion": "Caribbean", "status": "Overseas collectivity"},
    {"name": "Saint Barthélemy", "sovereign": "France", "region": "Americas", "subregion": "Caribbean", "status": "Overseas collectivity"},
    {"name": "Saint Pierre and Miquelon", "sovereign": "France", "region": "Americas", "subregion": "Northern America", "status": "Overseas collectivity"},
    {"name": "French Polynesia", "sovereign": "France", "region": "Oceania", "subregion": "Polynesia", "status": "Overseas collectivity"},
    {"name": "New Caledonia", "sovereign": "France", "region": "Oceania", "subregion": "Melanesia", "status": "Sui generis collectivity"},
    {"name": "Wallis and Futuna", "sovereign": "France", "region": "Oceania", "subregion": "Polynesia", "status": "Overseas collectivity"},
    {"name": "Canary Islands", "sovereign": "Spain", "region": "Africa", "subregion": "Northern Africa (Atlantic)", "status": "Autonomous community (integral part of Spain)"},
    {"name": "Ceuta", "sovereign": "Spain", "region": "Africa", "subregion": "Northern Africa", "status": "Autonomous city (integral part of Spain)"},
    {"name": "Melilla", "sovereign": "Spain", "region": "Africa", "subregion": "Northern Africa", "status": "Autonomous city (integral part of Spain)"},
    {"name": "Azores", "sovereign": "Portugal", "region": "Europe", "subregion": "Southern Europe (Atlantic)", "status": "Autonomous region (integral part of Portugal)"},
    {"name": "Madeira", "sovereign": "Portugal", "region": "Europe", "subregion": "Southern Europe (Atlantic, off Africa)", "status": "Autonomous region (integral part of Portugal)"},
    {"name": "Hawaii", "sovereign": "United States", "region": "Oceania", "subregion": "Polynesia", "status": "State (integral part of the US)"},
    {"name": "Alaska", "sovereign": "United States", "region": "Americas", "subregion": "Northern America", "status": "State (integral part of the US)"},
    {"name": "Bonaire", "sovereign": "Netherlands", "region": "Americas", "subregion": "Caribbean", "status": "Special municipality (integral part of the Netherlands)"},
    {"name": "Sint Eustatius", "sovereign": "Netherlands", "region": "Americas", "subregion": "Caribbean", "status": "Special municipality"},
    {"name": "Saba", "sovereign": "Netherlands", "region": "Americas", "subregion": "Caribbean", "status": "Special municipality"},
    {"name": "Svalbard", "sovereign": "Norway", "region": "Europe", "subregion": "Northern Europe (Arctic)", "status": "Unincorporated area (integral part of Norway)"},
    {"name": "Easter Island", "sovereign": "Chile", "region": "Oceania", "subregion": "Polynesia", "status": "Special territory (integral part of Chile)"},
    {"name": "Galápagos Islands", "sovereign": "Ecuador", "region": "Americas", "subregion": "South America (Pacific)", "status": "Province (integral part of Ecuador)"},
    {"name": "Andaman and Nicobar Islands", "sovereign": "India", "region": "Asia", "subregion": "Southern Asia (Bay of Bengal)", "status": "Union territory (integral part of India)"},
    {"name": "Kaliningrad Oblast", "sovereign": "Russia", "region": "Europe", "subregion": "Eastern Europe (exclave on the Baltic)", "status": "Oblast (integral part of Russia)"},
    {"name": "Okinawa", "sovereign": "Japan", "region": "Asia", "subregion": "Eastern Asia", "status": "Prefecture (integral part of Japan)"},
]

# ---------------------------------------------------------------- HTML table parsing (handles rowspan/colspan)

def _clean(c: str) -> str:
    c = re.sub(r"<sup[^>]*>.*?</sup>", "", c, flags=re.S)
    c = re.sub(r"<br\s*/?>", " | ", c)
    c = H.unescape(re.sub(r"<[^>]+>", "", c))
    c = re.sub(r"\[[^\]]*\]", "", c)
    return re.sub(r"\s+", " ", c).strip()


def _tables(html: str) -> list[list[list[str]]]:
    out = []
    for t in re.findall(r"<table[^>]*>(.*?)</table>", html, re.S):
        rows, pending = [], {}
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
            cells = re.findall(r"<t([dh])([^>]*)>(.*?)</t[dh]>", tr, re.S)
            row, col, k = [], 0, 0
            while k < len(cells) or col in pending:
                if col in pending:
                    text, left = pending[col]
                    row.append(text)
                    if left <= 1:
                        del pending[col]
                    else:
                        pending[col] = (text, left - 1)
                    col += 1
                    continue
                _, attrs, body = cells[k]
                k += 1
                text = _clean(body)
                rs = re.search(r'rowspan="?(\d+)', attrs)
                cs = re.search(r'colspan="?(\d+)', attrs)
                n = int(cs.group(1)) if cs else 1
                for _ in range(n):
                    row.append(text)
                    if rs and int(rs.group(1)) > 1:
                        pending[col] = (text, int(rs.group(1)) - 1)
                    col += 1
            rows.append(row)
        out.append(rows)
    return out


def _sections_h3(html: str) -> list[tuple[str, str]]:
    parts = re.split(r"<h3[^>]*>", html)
    secs = []
    for part in parts[1:]:
        if "</h3>" not in part:
            continue
        title, body = part.split("</h3>", 1)
        secs.append((_clean(title), body.split("<h2", 1)[0]))
    return secs


# ---------------------------------------------------------------- per-table parsers

def parse_cn_plates(html: str) -> dict:
    out = {}
    for title, body in _sections_h3(html):
        m = re.match(r"^(.+?)（(.)）$", title)
        if not m:
            continue
        prov, abbr = m.group(1), m.group(2)
        letters = {}
        for li in re.findall(r"<li[^>]*>(.*?)</li>", body, re.S):
            text = _clean(li)
            text = re.split(r"[。；;]", text)[0]
            text = re.sub(r"^(参见：.*?)(?=[A-Z](?:[/、，,]|\s))", "", text)
            text = re.sub(r"^(汽车|小型汽车|大型汽车)\s*", "", text)
            if "摩托车" in text or "拖拉机" in text:
                continue
            mm = re.match(r"^([A-Z](?:\s*[/、，,–\-~～至]\s*[A-Z])*)\s*[：:]?\s*(.+)$", text)
            if not mm:
                continue
            place = mm.group(2).strip()
            spec = mm.group(1)
            Ls: list[str] = []
            for seg in re.split(r"[/、，,]", spec):
                seg = seg.strip()
                r = re.match(r"^([A-Z])\s*[–\-~～至]\s*([A-Z])$", seg)
                if r:
                    Ls += [chr(c) for c in range(ord(r.group(1)), ord(r.group(2)) + 1) if chr(c) not in "IO"]
                elif seg:
                    Ls.append(seg)
            for L in Ls:
                letters[L] = place
        if letters:
            out[abbr] = {"province": prov, "letters": letters}
    for abbr, notes in MUNICIPAL_LETTER_NOTES.items():
        if abbr in out:
            out[abbr]["letter_notes_unverified"] = notes
    return out


def parse_cn_area_codes(html: str) -> dict:
    out = {}
    for t in _tables(html):
        if not t or not t[0] or t[0][0] != "区号":
            continue
        for row in t[1:]:
            if len(row) < 3 or not re.match(r"^\d{2,4}$", row[0]):
                continue
            code = "0" + row[0]
            entry = {"admin1": row[1], "admin2": [x.strip() for x in row[2].split("|") if x.strip()],
                     "digits": row[3] if len(row) > 3 else "", "note": row[4] if len(row) > 4 else ""}
            # "/" in the digits column marks a retired code; the note alone isn't enough (023's note tells the history of 811 being retired)
            if entry["digits"] == "/":
                entry["deprecated"] = True
            out[code] = entry
    return out


def parse_calling_codes(html: str) -> dict:
    out = {}
    for t in _tables(html):
        if len(t) < 50 or not t[0] or t[0][0] != "Serving":
            continue
        for row in t[1:]:
            if len(row) < 2 or not re.match(r"^\d", row[1]):
                continue
            country = row[0]
            m = re.match(r"^(\d+)\s*(?:\(([^)]*)\))?", row[1])
            if not m:
                continue
            code = m.group(1)
            subs = [s.strip() for s in (m.group(2) or "").split(",") if s.strip()]
            keys = [f"{code}-{s}" for s in subs] or [code]
            for k in keys:
                out.setdefault(k, []).append({"country": country, "utc": row[2] if len(row) > 2 else ""})
    return out


DRIVING_SUPPLEMENT = {  # regions without their own row in the Wikipedia table (source: each region's article, common knowledge)
    "Hong Kong": ("left", "kept from British rule, opposite to the mainland"), "Macau": ("left", "kept from Portuguese rule, opposite to the mainland"), "Taiwan": ("right", ""),
    "French Guiana": ("right", "French overseas department"), "Guadeloupe": ("right", "French overseas department"), "Martinique": ("right", "French overseas department"),
    "Réunion": ("right", "French overseas department"), "Mayotte": ("right", "French overseas department"), "New Caledonia": ("right", "French territory"), "French Polynesia": ("right", "French territory"),
    "Puerto Rico": ("right", "US territory"), "Guam": ("right", "US territory"), "U.S. Virgin Islands": ("left", "US territory, a rare left-hand one"),
    "American Samoa": ("right", "US territory"), "Northern Mariana Islands": ("right", "US territory"),
    "Greenland": ("right", "Denmark"), "Faroe Islands": ("right", "Denmark"), "Aruba": ("right", "Netherlands"), "Curaçao": ("right", "Netherlands"), "Sint Maarten": ("right", "Netherlands"),
    "Gibraltar": ("right", "British territory, a rare right-hand one"), "Bermuda": ("left", "British territory"), "Cayman Islands": ("left", "British territory"),
    "British Virgin Islands": ("left", "British territory"), "Anguilla": ("left", "British territory"), "Montserrat": ("left", "British territory"),
    "Turks and Caicos Islands": ("left", "British territory"), "Falkland Islands": ("left", "British territory"), "Saint Helena": ("left", "British territory"),
    "Isle of Man": ("left", "British Crown Dependency"), "Jersey": ("left", "British Crown Dependency"), "Guernsey": ("left", "British Crown Dependency"),
    "Cook Islands": ("left", "New Zealand associated state"), "Niue": ("left", "New Zealand associated state"), "Tokelau": ("left", "New Zealand territory"),
    "Canary Islands": ("right", "Spain"), "Azores": ("right", "Portugal"), "Madeira": ("right", "Portugal"), "Svalbard": ("right", "Norway"),
}


def parse_driving_side(html: str) -> dict:
    """The table's "Country" header spans two columns: sovereign state, then a sub-unit for states listed in parts
    (China → Mainland / Hong Kong / Macau). Keying every row by the first column let the last sub-row overwrite the
    country (China came out as LHT with Macau's note), so sub-rows are resolved explicitly."""
    out: dict = {}
    groups: dict[str, list[tuple[str, dict]]] = {}
    for t in _tables(html):
        if len(t) < 100 or not t[0] or t[0][0] != "Country":
            continue
        for row in t[1:]:
            if len(row) < 2:
                continue
            idx = next((i for i, c in enumerate(row) if re.match(r"^(LHT|RHT)", c.upper())), None)
            if idx is None:
                continue
            e = {"side": "left" if row[idx].upper().startswith("LHT") else "right",
                 "switched": row[idx + 1] if len(row) > idx + 1 else "", "note": row[idx + 2] if len(row) > idx + 2 else ""}
            if idx >= 2 and row[1] != row[0]:
                groups.setdefault(re.sub(r" and overseas territories$", "", row[0]), []).append((row[1], e))
            else:
                out[row[0]] = e
    for parent, subs in groups.items():
        main = [e for sub, e in subs if sub == "Mainland" or sub.endswith(" proper") or sub.startswith("Contiguous")]
        if main:
            out[parent] = main[0]
        elif len({e["side"] for _, e in subs}) == 1:
            # Listed by province/state, all the same side (Canada): the country takes that side, provinces aren't countries
            out[parent] = dict(subs[0][1], note="; ".join(f"{sub}: {e['note']}" for sub, e in subs if e["note"]))
            continue
        for sub, e in subs:
            if e in main:
                continue
            out[sub] = dict(e, part_of=parent, note="; ".join(x for x in (f"part of {parent}", e["note"]) if x))
    for k, (side, note) in DRIVING_SUPPLEMENT.items():
        if k not in out:
            out[k] = {"side": side, "switched": "", "note": note, "curated": True}
    return out


def parse_territories(html: str) -> dict:
    items = []
    for t in _tables(html):
        if not t or not t[0] or t[0][0] != "Name" or "Sovereign state" not in t[0]:
            continue
        hi = {h: i for i, h in enumerate(t[0])}
        for row in t[1:]:
            if len(row) < len(t[0]) - 1:
                continue
            items.append({"name": row[hi["Name"]], "sovereign": row[hi["Sovereign state"]], "region": row[hi["UN region"]],
                          "subregion": row[hi["UN subregion"]], "status": row[hi.get("Legal status", len(row) - 1)],
                          "population": row[hi.get("Population (2016)", 1)], "area_km2": row[hi.get("Area (km)", 2)]})
    names = {it["name"].lower() for it in items}
    for it in INTEGRAL_OVERSEAS:
        if it["name"].lower() not in names:
            items.append(dict(it, population="", area_km2="", curated=True))
    by_sov: dict = {}
    for it in items:
        by_sov.setdefault(it["sovereign"], []).append(it)
    return {"by_sovereign": by_sov, "count": len(items),
            "note": "Wikipedia's “List of dependent territories” excludes overseas territories integrated into the home country, such as French overseas departments; INTEGRAL_OVERSEAS adds them (curated=true)"}


def parse_cn_admin(raw: str) -> dict:
    nodes = json.loads(raw)
    items = []

    def walk(ns, parent, level):
        for n in ns:
            name, code = n.get("name", ""), n.get("code", "")
            ch = n.get("children") or []
            if level == 2 and name in ("市辖区", "县", "省直辖县级行政区划", "自治区直辖县级行政区划", "市"):
                walk(ch, parent, 3)      # dummy level for municipalities / province-administered units: attach children directly to the province
                continue
            items.append({"name": name, "code": code, "level": level, "parent": parent})
            walk(ch, name, level + 1)

    walk(nodes, "", 1)
    return {"items": items}



# ---------------------------------------------------------------- regional plate codes (outside China)
# Each page is fetched through the MediaWiki parse API and one or more of its tables (or lists) become
# {code: [{"place", "region", "era", "note"}]}. Eras matter as much as places: many countries dropped
# regional codes (Italy 1994, Spain 2000, France 2009), so a regional code also dates the photo.
PLATE_PAGES = {
    "IT": ("en", "Vehicle registration plates of Italy"),
    "ES": ("en", "Vehicle registration plates of Spain"),
    "FR": ("en", "Departments of France"),
    "DE": ("de", "Liste der Kfz-Kennzeichen in Deutschland"),
    "AT": ("en", "Vehicle registration plates of Austria"),
    "CH": ("en", "Vehicle registration plates of Switzerland"),
    "GR": ("en", "Vehicle registration plates of Greece"),
    "TR": ("en", "Vehicle registration plates of Turkey"),
    "GB": ("en", "Vehicle registration plates of the United Kingdom"),
    "MA": ("fr", "Plaque d'immatriculation marocaine"),
}
WIKI_API = "https://{lang}.wikipedia.org/w/api.php?action=parse&format=json&prop=text&redirects=1&page={title}"   # sources_check.py probes it


def _wiki_url(lang: str, title: str) -> str:
    return f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"


def _wiki_html(lang: str, title: str, proxy: str | None) -> str:
    raw = _fetch(WIKI_API.format(lang=lang, title=quote(title)), proxy)
    return json.loads(raw)["parse"]["text"]["*"]


def _find_table(tables: list, *head: str):
    for t in tables:
        h = [x.strip().lower() for x in t[0]]
        if len(h) >= len(head) and all(h[i].startswith(head[i].lower()) for i in range(len(head))):
            return t
    return None


def _add(codes: dict, code: str, place: str, era: str, region: str = "", note: str = "") -> None:
    code, place = code.strip().upper(), re.sub(r"\[\d+\]", "", place).strip()
    if code and place and code.lower() not in ("code", "abk."):
        codes.setdefault(code, []).append({"place": place, "region": region.strip(), "era": era, "note": note.strip()})


def _pairs(t, codes: dict, era: str) -> None:
    for r in t[1:]:
        for i in range(0, len(r) - 1, 2):
            _add(codes, r[i], r[i + 1], era)


def parse_plate_page(cc: str, html: str) -> dict:
    """One country's page → {"codes": {...}, "dating": {...}, "note": "..."}."""
    tabs = _tables(html)
    codes: dict = {}
    dating: dict = {}
    note = ""
    if cc == "IT":
        note = "Province code: on plates 1927–1994 (Rome spelled out ROMA); optional on the right blue band since 1999."
        t = _find_table(tabs, "code", "province", "code")
        if t:
            _pairs(t, codes, "1927–1994 plates; optional right band since 1999")
        t = _find_table(tabs, "number", "province", "number")
        if t:
            _pairs(t, codes, "1905–1927 plates (province number)")
        t = _find_table(tabs, "code", "province", "reason", "years")
        if t:
            for r in t[1:]:
                if len(r) >= 4:
                    _add(codes, r[0], r[1], r[3], note=r[2])
        if "ROMA" in codes and "RM" not in codes:          # old plates spelled ROMA out; the modern abbreviation is RM
            _add(codes, "RM", "Rome", "optional right band since 1999 (old plates spell out ROMA)")
    elif cc == "ES":
        note = "Provincial code at the start of plates 1900–2000 (M-1234-AB); the national system since September 2000 has none."
        t = _find_table(tabs, "code", "province", "notes")
        for r in (t or [])[1:]:
            _add(codes, r[0], r[1], "1900–2000 plates", note=r[2] if len(r) > 2 else "")
    elif cc == "FR":
        note = ("Département number: at the end of FNI plates 1950–2009 (1234 AB 75); optional on the right band of SIV "
                "plates since 2009 (the owner's choice, not proof of residence). Algerian numbers are French Algeria (until 1962).")
        t = _find_table(tabs, "insee code")
        for r in (t or [])[1:]:
            if len(r) >= 6:
                _add(codes, r[0], r[3], "FNI 1950–2009; optional SIV band since 2009", region=r[5], note=f"prefecture {r[4]}")
        for head, era in (("before 1957 no.", "French Algeria, until 1957"), ("1957–1962 no.", "French Algeria, 1957–1962")):
            t = _find_table(tabs, head)
            for r in (t or [])[1:]:
                if len(r) >= 3:
                    _add(codes, r[0], r[1], era, region="Algeria", note=f"prefecture {r[2]}")
    elif cc == "DE":
        note = "District code (Unterscheidungszeichen) before the hyphen; old codes reintroduced since 2012 also appear."
        for t in tabs:
            h = [x.strip().lower() for x in t[0]]
            if len(h) >= 4 and h[0].startswith("abk") and h[1].startswith("stadt"):
                for r in t[1:]:
                    if len(r) >= 4:
                        _add(codes, r[0], r[1], "current", region=r[3], note=f"from {r[2]}" if r[2] else "")
    elif cc == "AT":
        note = "District code on the left since 1990, with the state's coat of arms."
        t = _find_table(tabs, "code", "city, district")
        for r in (t or [])[1:]:
            _add(codes, r[0], r[1], "current", region=r[2] if len(r) > 2 else "", note=r[3] if len(r) > 3 else "")
    elif cc == "CH":
        note = "Canton code on every plate (ZH 123456); the canton arms are on the rear plate."
        t = _find_table(tabs, "code", "flag", "canton")
        for r in (t or [])[1:]:
            if len(r) >= 3:
                _add(codes, r[0], r[2], "current")
    elif cc == "GR":
        note = "Two Greek letters (only Latin look-alikes are used) give the prefecture of registration."
        t = _find_table(tabs, "code", "prefecture")
        for r in (t or [])[1:]:
            if len(r) >= 2:
                _add(codes, r[0].upper(), r[1], (r[3] if len(r) > 3 else "") or "?", note=r[2] if len(r) > 2 else "")
    elif cc == "TR":
        note = "Province number first on every plate (34 ABC 123 = Istanbul)."
        t = _find_table(tabs, "code", "province", "code")
        if t:
            _pairs(t, codes, "current")
    elif cc == "GB":
        note = ("Since Sept 2001: first letter = region, second = DVLA office (memory tag); the two digits after it are "
                "the age identifier (see 'dating'). Older suffix (1963–83) and prefix (1983–2001) letters date the car.")
        t = _find_table(tabs, "first letter", "official local mnemonic")
        for r in (t or [])[1:]:
            if len(r) >= 4:
                for s in r[3].split():
                    if re.fullmatch(r"[A-Z]", s):
                        _add(codes, r[0].strip() + s, r[2], "since 2001 (memory tag)", region=r[1])
        for t in tabs:
            h = [x.strip().lower() for x in t[0]]
            if len(h) >= 3 and h[0] == "year" and h[1].startswith("1 march"):
                for r in t[1:]:
                    if len(r) >= 3:
                        dating.setdefault("age_identifier", {})[r[1].strip()] = f"registered 1 Mar–31 Aug, year {r[0].strip()}"
                        dating["age_identifier"][r[2].strip()] = f"registered 1 Sep–end Feb, year {r[0].strip()}"
        t = _find_table(tabs, "suffix letter")
        for r in (t or [])[1:]:
            if len(r) >= 2:
                dating.setdefault("suffix_1963_1983", {})[r[0].strip()] = r[1].strip()
        t = _find_table(tabs, "letter", "dates of issue")
        for r in (t or [])[1:]:
            if len(r) >= 2:
                dating.setdefault("prefix_1983_2001", {})[r[0].strip()] = r[1].strip()
    elif cc == "MA":
        note = ("Since 2000: number | Arabic letter | prefecture number (1–89). 1983–2000 plates ended with a region "
                "number 1–9 (not tabled). Codes 63, 68–71, 89 are the southern provinces.")
        sec = html[html.find("Liste_des_num"):] if "Liste_des_num" in html else html
        m = re.search(r"<ol[^>]*>(.*?)</ol>", sec, re.S)
        if m:
            items = [_clean(li) for li in re.findall(r"<li[^>]*>(.*?)</li>", m.group(1), re.S)]
            for k, place in enumerate(items, 1):
                _add(codes, str(k), place, "since 2000")
    return {"codes": codes, "dating": dating, "note": note}


def build_plate_codes(proxy: str | None, from_dir: str | None = None) -> dict:
    out, n = {}, 0
    for cc, (lang, title) in PLATE_PAGES.items():
        if from_dir:
            html = (Path(from_dir) / f"plates_{cc}.html").read_text(encoding="utf-8", errors="replace")
        else:
            html = _wiki_html(lang, title, proxy)
        d = parse_plate_page(cc, html)
        d["source"] = _wiki_url(lang, title)
        out[cc] = d
        n += len(d["codes"])
        print(f"  {cc}: {len(d['codes'])} codes" + (f", dating tables {sorted(d['dating'])}" if d["dating"] else ""), flush=True)
    return {"count": n, "countries": out}


# ---------------------------------------------------------------- China pack: raw tables → shared formats

CN_ADMIN_LEVELS = {1: "admin1", 2: "admin2", 3: "district"}   # must match regions/cn/region.json admin_levels


class _CNAdmin:
    def __init__(self, items: list[dict]):
        self.items = items
        self.by: dict[str, list[dict]] = {}
        for it in items:
            self.by.setdefault(it["name"], []).append(it)

    def chain(self, it: dict) -> list[dict]:
        out, cur = [it], it
        while cur.get("parent"):
            nxt = self.by.get(cur["parent"])
            if not nxt:
                break
            cur = nxt[0]
            out.append(cur)
        return list(reversed(out))

    def under(self, prov: str, name: str) -> dict | None:
        """The one item called name (or name without its 市/区/县 suffix) inside province prov."""
        cands = self.by.get(name) or [it for n, its in self.by.items() if n.rstrip("市区县") == name.rstrip("市区县") for it in its]
        cands = [it for it in cands if prov in [c["name"] for c in self.chain(it)]]
        return cands[0] if len(cands) == 1 else None

    def match(self, it: dict) -> dict:
        return {CN_ADMIN_LEVELS[c["level"]]: c["name"] for c in self.chain(it)}


def _cn_places(adm: _CNAdmin, prov: str, place: str) -> list[dict]:
    """Free-text place from a Wikipedia table cell → matches. Unresolvable text (vehicle classes, "直辖市全境", historic areas)
    stays at province level with the text as the note, instead of becoming a fake place."""
    place = place.strip()
    if place == prov or place.rstrip("市") == prov.rstrip("市"):
        return [{"admin1": prov}]
    m = re.match(r"^(.+?)（(.+)）$", place)
    head, inner = (m.group(1), m.group(2)) if m else (place, "")
    it = adm.under(prov, head)
    if not it:
        return [{"admin1": prov, "note": place}]
    if inner:
        subs = [x.strip() for x in re.split(r"[、，,]", inner) if x.strip()]
        kids = [adm.under(prov, x) for x in subs]
        if subs and all(kids) and not re.search(r"不含|部分|地级|地区", inner):
            return [adm.match(k) for k in kids]
        return [dict(adm.match(it), note=inner)]
    return [adm.match(it)]


def cn_plates_table(raw: dict, adm: _CNAdmin) -> dict:
    entries: dict[str, list[dict]] = {}
    for abbr, v in raw.items():
        prov = v["province"]
        entries[abbr] = [{"admin1": prov, "note": "province abbreviation only"}]
        unv = v.get("letter_notes_unverified") or {}
        for letter, place in v["letters"].items():
            rows = []
            for p in re.split(r"[、，,/]", place):
                if not p.strip():
                    continue
                for r in _cn_places(adm, prov, p):
                    if set(r) <= {"admin1", "note"} and not r.get("note") and letter in unv:
                        r.update(note=f"whole municipality; district split from common knowledge: {unv[letter]}", unverified=True)
                    elif set(r) <= {"admin1", "note"} and not r.get("note"):
                        r["note"] = "whole municipality" if prov.endswith("市") else "whole province"
                    rows.append(r)
            entries[abbr + letter] = _dedup(rows)
    return entries


def cn_area_codes_table(raw: dict, adm: _CNAdmin) -> dict:
    entries: dict[str, list[dict]] = {}
    for code, e in raw.items():
        note = ("deprecated; " if e.get("deprecated") else "") + (e.get("note") or "")
        rows = []
        for a in e["admin2"] or [e["admin1"]]:
            for r in _cn_places(adm, e["admin1"], a):
                r["note"] = "; ".join(x for x in (r.get("note", ""), note) if x)
                if e.get("digits"):
                    r["digits"] = e["digits"]
                rows.append(r)
        entries[code] = _dedup(rows)
    return entries


def _dedup(rows: list[dict]) -> list[dict]:
    """One match per place: rows naming the same place (several vehicle classes under one letter) merge, notes joined."""
    out: dict[str, dict] = {}
    for r in rows:
        k = json.dumps({lv: r[lv] for lv in ("admin1", "admin2", "district") if r.get(lv)}, ensure_ascii=False, sort_keys=True)
        if k not in out:
            out[k] = dict(r)
            continue
        notes = [x for x in out[k].get("note", "").split("; ") if x]
        notes += [x for x in r.get("note", "").split("; ") if x and x not in notes]
        out[k]["note"] = "; ".join(notes)
    return list(out.values())


PLATE_META = {"kind": "plate", "normalize": {"strip": " ·-", "upper": True},
              "key_pattern": "^[\\u4e00-\\u9fff][A-Z]?",
              "usage": "first Han character (province) + issuing letter, e.g. <abbr><letter>; the rest of the plate is ignored",
              "note": "Municipality letter splits come from common knowledge, marked unverified; Hong Kong/Macau/Taiwan, military and police plates are not in the table.",
              "miss_note": "province abbreviation not in the table"}
AREA_META = {"kind": "area-code", "normalize": {"digits_only": True, "ensure_prefix": "0"},
             "usage": "landline area code; accepts 0817, 0817-1234567, (0817) 123. 010/02X are 3 digits, the rest 4",
             "miss_note": "not a mainland China landline area code (mobile number, 400/800, foreign number)"}


# ---------------------------------------------------------------- fetch / write

def _fetch(url: str, proxy: str | None) -> str:
    cmd = ["curl", "-q", "-s", "-m", "90", "-A", UA, "-L"]
    cmd += curl_args(proxy)
    r = subprocess.run(cmd + [url], capture_output=True)
    if r.returncode != 0 or len(r.stdout) < 1000:
        sys.exit(f"fetch failed: {url} (check service availability with doctor.py --network)")
    return r.stdout.decode("utf-8", "replace")


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    shown = path.relative_to(DATA.parent) if path.is_relative_to(DATA.parent) else path
    print(f"{shown.as_posix()}: {payload['_meta'].get('count')} entries ({path.stat().st_size // 1024} KB)")


def keep_curated(path: Path, data: dict) -> dict:
    """Rows marked "curated" in the current table win over a fresh scrape (the scrape once flipped mainland China to LHT)."""
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return data
    for k, v in old.items():
        if not k.startswith("_") and isinstance(v, dict) and v.get("curated"):
            data[k] = dict(data[k], **v) if isinstance(data.get(k), dict) else v
    return data


def refresh(name: str, raw: str) -> None:
    today = date.today().isoformat()
    meta = {"source": SOURCES[name], "fetched": today, "license": LICENSE.get(name, WIKI_LICENSE)}
    if name in ("calling_codes", "driving_side", "territories"):
        data = {"calling_codes": parse_calling_codes, "driving_side": parse_driving_side, "territories": parse_territories}[name](raw)
        if name == "driving_side":
            data = keep_curated(DATA / "driving_side.json", data)
            meta["note"] = "rows marked curated were corrected or added by hand and survive refreshes"
        _write(DATA / f"{name}.json", {"_meta": dict(meta, count=data.get("count") or len(data)), **data})
    elif name == "cn/admin":
        data = parse_cn_admin(raw)
        _write(CN / "admin.json", {"_meta": dict(meta, count=len(data["items"])), **data})
    else:
        adm = _CNAdmin(json.loads((CN / "admin.json").read_text(encoding="utf-8"))["items"])
        if name == "cn/plates":
            entries, extra = cn_plates_table(parse_cn_plates(raw), adm), PLATE_META
        else:
            entries, extra = cn_area_codes_table(parse_cn_area_codes(raw), adm), AREA_META
        _write(CN / f"{name.split('/')[1]}.json", {"_meta": dict(extra, **meta, count=len(entries)), "entries": entries})


ALIASES = {"cn_plates": "cn/plates", "cn_area_codes": "cn/area_codes", "cn_admin": "cn/admin"}   # old table names, still documented by clues.py update


def run(table: str, proxy: str | None, from_dir: Path | None) -> None:
    names = list(SOURCES) if table in ("all", None) else [ALIASES.get(table, table)]
    for name in names:
        if name not in SOURCES:
            sys.exit(f"unknown table {name}; one of {', '.join(SOURCES)}")
        if name == "plate_codes":
            data = build_plate_codes(proxy, str(from_dir) if from_dir else None)
            srcs = [_wiki_url(lang, title) for lang, title in PLATE_PAGES.values()]
            meta = {"source": srcs, "fetched": date.today().isoformat(), "license": WIKI_LICENSE, "count": data["count"]}
            _write(DATA / "plate_codes.json", {"_meta": meta, **data})
            continue
        raw = (from_dir / LOCAL_NAMES[name]).read_text(encoding="utf-8", errors="replace") if from_dir else _fetch(SOURCES[name][0], proxy)
        refresh(name, raw)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("table", nargs="?", default="all", help=f"all or one of {', '.join(SOURCES)}")
    ap.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)
    ap.add_argument("--from-dir", type=Path, help="directory of already-downloaded source files (for development)")
    args = ap.parse_args()
    run(args.table, args.proxy, args.from_dir)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
