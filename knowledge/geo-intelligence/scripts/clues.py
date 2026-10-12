#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Lookup-table clues. Tables are local JSON; lookups don't go online.

Global tables (assets/data/):
  lookup calling-code +594      international calling code → country/region
  lookup driving-side left      countries that drive on the left; `driving-side GB` or `driving-side --country Japan` → that country's side
  lookup territories France     overseas territories/dependencies of France; `--continent "South America"` lists only that continent
  lookup plate-code PA --country IT   regional plate code outside China (IT ES FR DE AT CH GR TR GB MA) → place + the era
                                it was used (a regional code also dates the photo); without --country every country is searched
  lookup coverage streetview    countries/territories with official Google Street View (plus partial ones); `coverage NA` → one country's status
Region-pack tables (assets/data/regions/<cc>/, see `regions.py list`):
  lookup <kind> <value> [--country cc]   kinds the packs declare, e.g. plate, area-code; without --country every pack with
                                that kind is searched and matches from several countries are all returned; with --country only
                                that pack is used, and a pack that lacks the kind (or isn't installed) answers "unsupported"
  lookup admin <name> [--country cc]     parent chain from a pack's admin table; `admin --children <name>` lists the children
  list                          global tables and installed packs with entry counts and fetch dates
  update [table|all]            maintainers: refetch tables (same as refresh.py; cn_plates/cn_area_codes/cn_admin accepted)

--json output follows one contract (used by board.py apply):
  {"kind", "value", "status": ok|no_match|unsupported|error (error = that country's pack is broken), "matches": [...], "searched": [pack codes], "source", "table_fetched", "note"}
  region matches: {"country", "country_code", "admin1", "admin2"?, "city"?, "district"?, "note", "unverified"?} — levels are explicit
  global matches: {"country", "continent"?, "subregion"?, "side"?, "switched"? (date the side changed), "utc"?, "note"}

Examples:
  clues.py lookup plate <plate prefix> --country cn
  clues.py lookup area-code 0817 --json
  clues.py lookup calling-code +594
  clues.py lookup territories France --continent "South America"
Tables are refreshed by maintainers with refresh.py (or `clues.py update`).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import regions  # noqa: E402
from geolib.paths import DATA_DIR  # noqa: E402

DATA = DATA_DIR
GLOBAL_TABLES = ("calling_codes", "driving_side", "territories", "country_names", "plate_codes", "streetview_coverage")
GLOBAL_KINDS = ("calling-code", "driving-side", "territories", "plate-code", "coverage")

# Chinese → English country aliases (common ones only; if not found, retry with the English name)
COUNTRY_ZH = {
    "中国": "China", "日本": "Japan", "英国": "United Kingdom", "法国": "France", "美国": "United States", "澳大利亚": "Australia",
    "香港": "Hong Kong", "澳门": "Macau", "美属维尔京群岛": "U.S. Virgin Islands", "直布罗陀": "Gibraltar", "百慕大": "Bermuda", "开曼群岛": "Cayman Islands", "新喀里多尼亚": "New Caledonia", "法属波利尼西亚": "French Polynesia", "马约特": "Mayotte", "加那利群岛": "Canary Islands", "印度": "India", "泰国": "Thailand", "印尼": "Indonesia", "印度尼西亚": "Indonesia",
    "马来西亚": "Malaysia", "新加坡": "Singapore", "新西兰": "New Zealand", "南非": "South Africa", "巴西": "Brazil", "墨西哥": "Mexico",
    "德国": "Germany", "意大利": "Italy", "西班牙": "Spain", "俄罗斯": "Russia", "韩国": "South Korea", "越南": "Vietnam",
    "菲律宾": "Philippines", "巴基斯坦": "Pakistan", "孟加拉国": "Bangladesh", "斯里兰卡": "Sri Lanka", "尼泊尔": "Nepal", "肯尼亚": "Kenya",
    "爱尔兰": "Ireland", "加拿大": "Canada", "法属圭亚那": "French Guiana", "荷兰": "Netherlands", "葡萄牙": "Portugal", "丹麦": "Denmark",
    "挪威": "Norway", "瑞典": "Sweden", "芬兰": "Finland", "阿根廷": "Argentina", "智利": "Chile", "秘鲁": "Peru", "哥伦比亚": "Colombia",
    "埃及": "Egypt", "土耳其": "Turkey", "伊朗": "Iran", "沙特阿拉伯": "Saudi Arabia", "阿联酋": "United Arab Emirates", "以色列": "Israel",
    "缅甸": "Myanmar", "柬埔寨": "Cambodia", "老挝": "Laos", "蒙古": "Mongolia", "朝鲜": "North Korea", "台湾": "Taiwan", "瑞士": "Switzerland",
    "奥地利": "Austria", "比利时": "Belgium", "波兰": "Poland", "捷克": "Czech Republic", "希腊": "Greece", "乌克兰": "Ukraine",
    "哈萨克斯坦": "Kazakhstan", "摩洛哥": "Morocco", "尼日利亚": "Nigeria", "埃塞俄比亚": "Ethiopia", "坦桑尼亚": "Tanzania", "乌干达": "Uganda",
    "莫桑比克": "Mozambique", "纳米比亚": "Namibia", "津巴布韦": "Zimbabwe", "赞比亚": "Zambia", "马耳他": "Malta", "塞浦路斯": "Cyprus",
    "冰岛": "Iceland", "古巴": "Cuba", "牙买加": "Jamaica", "巴哈马": "Bahamas", "圭亚那": "Guyana", "苏里南": "Suriname",
    "巴布亚新几内亚": "Papua New Guinea", "斐济": "Fiji", "萨摩亚": "Samoa", "汤加": "Tonga", "阿尔及利亚": "Algeria", "突尼斯": "Tunisia",
    "塞内加尔": "Senegal", "科特迪瓦": "Ivory Coast", "加纳": "Ghana", "喀麦隆": "Cameroon", "马达加斯加": "Madagascar", "毛里求斯": "Mauritius",
    "留尼汪": "Réunion", "马提尼克": "Martinique", "瓜德罗普": "Guadeloupe", "波多黎各": "Puerto Rico", "关岛": "Guam", "格陵兰": "Greenland",
}
CONTINENT_ZH = {"亚洲": ["Asia"], "欧洲": ["Europe"], "非洲": ["Africa"], "大洋洲": ["Oceania"], "北美洲": ["Northern America", "North America"],
                "南美洲": ["South America"], "美洲": ["Americas"], "加勒比": ["Caribbean"], "中美洲": ["Central America"], "南极洲": ["Antarctica"]}

# ---------------------------------------------------------------- read/write

def load(table: str) -> dict:
    f = DATA / f"{table}.json"
    if not f.exists():
        sys.exit(f"{f} not found: reinstall the skill folder, or refetch with `refresh.py {table}`")
    return json.loads(f.read_text(encoding="utf-8"))


def _result(kind, value, matches, source, fetched, note="", status=None):
    return {"kind": kind, "value": value, "status": status or ("ok" if matches else "no_match"), "matches": matches,
            "searched": [], "source": source, "table_fetched": fetched, "note": note}

def lookup_calling_code(value: str) -> dict:
    d = load("calling_codes")
    src, fetched = d["_meta"]["source"][0], d["_meta"]["fetched"]
    digits = re.sub(r"\D", "", value)
    if digits.startswith("00"):
        digits = digits[2:]
    for L in (3, 2, 1):
        code = digits[:L]
        if code in d:
            hits = d[code]
            # shared codes like 1 and 7: look at the area code that follows
            subs = [k for k in d if k.startswith(code + "-") and digits[L:].startswith(k.split("-")[1])]
            if subs:
                hits = [h for k in subs for h in d[k]]
            return _result("calling-code", value, [{"country": h["country"], "utc": h.get("utc", ""), "note": ""} for h in hits], src, fetched)
    return _result("calling-code", value, [], src, fetched, "no matching country code")


_CN_NAMES: dict | None = None


def _country_en(name: str) -> str:
    """Chinese name / alias → the English name the tables use. Checks data/country_names.json (300 countries + aliases) first, then the built-in COUNTRY_ZH."""
    global _CN_NAMES
    n = name.strip()
    if _CN_NAMES is None:
        f = DATA / "country_names.json"
        _CN_NAMES = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    aliases = _CN_NAMES.get("aliases") or {}
    en2zh = _CN_NAMES.get("en2zh") or {}
    if n in aliases:
        return aliases[n]
    for en, zh in en2zh.items():
        if zh == n:
            return en
    return COUNTRY_ZH.get(n, n)


SIDE_WORDS = {"left": "left", "l": "left", "lht": "left", "左": "left", "right": "right", "r": "right", "rht": "right", "右": "right"}


def _country_rec(q: str) -> dict | None:
    """Country facts (iso2, name, geonames_name) by ISO2/ISO3/name/alias via geodata.py; None if unknown or geodata unavailable."""
    try:
        import geodata
        return geodata.country(q)
    except (Exception, SystemExit):  # noqa: BLE001 - countries.json unreadable: fall back to name matching only
        return None


def _country_names(q: str) -> list[str]:
    """Spellings to try against a table keyed by English country name: alias-resolved input, then geodata's canonical names."""
    en = _country_en(q)
    rec = _country_rec(en)
    names = [en] + ([rec["name"], rec.get("geonames_name", "")] if rec else [])
    return [n for i, n in enumerate(names) if n and n not in names[:i]]


def lookup_driving_side(value: str | None, country: str | None) -> dict:
    d = load("driving_side")
    src, fetched = d["_meta"]["source"][0], d["_meta"]["fetched"]
    v = (value or "").strip()
    side = SIDE_WORDS.get(v.lower())
    if v and not side and not country:
        country = v   # `driving-side GB` / `driving-side Japan`: the value is a country, not a side
    if country:
        names = [n.lower() for n in _country_names(country)]
        hit = next(((k, v2) for k, v2 in d.items() if k != "_meta" and k.lower() in names), None) or \
            next(((k, v2) for k, v2 in d.items() if k != "_meta" and any(n in k.lower() for n in names)), None)
        if not hit:
            return _result("driving-side", country, [], src, fetched,
                           "not a country code/name in the table (try the English name), nor a side: use left|right")
        k, v2 = hit
        return _result("driving-side", country, [{"country": k, "side": v2["side"], "switched": v2.get("switched", ""), "note": v2.get("note", "")}], src, fetched)
    side = side or "right"
    ms = [{"country": k, "side": v2["side"], "switched": v2.get("switched", ""), "note": v2.get("note", "")}
          for k, v2 in d.items() if k != "_meta" and v2["side"] == side]
    return _result("driving-side", side, ms, src, fetched)


def lookup_territories(value: str, continent: str | None) -> dict:
    d = load("territories")
    src, fetched = d["_meta"]["source"][0], d["_meta"]["fetched"]
    en = _country_en(value)
    sovs = [k for k in d["by_sovereign"] if k.lower() == en.lower()] or [k for k in d["by_sovereign"] if en.lower() in k.lower()]
    if not sovs:
        return _result("territories", value, [], src, fetched, "sovereign state not in the table (or it has no territories); former colonies are not in this table")
    items = [it for k in sovs for it in d["by_sovereign"][k]]
    if continent:
        keys = [x.lower() for x in CONTINENT_ZH.get(continent, [continent])]
        items = [it for it in items if any(k in (it["region"] + " " + it["subregion"]).lower() for k in keys)]
    return _result("territories", value, [{"country": it["name"], "continent": it["region"], "subregion": it["subregion"],
                                           "note": f"{it['status']}; sovereign state {it['sovereign']}"} for it in items], src, fetched)


# ---------------------------------------------------------------- regional plate codes outside China

GREEK_LOOKALIKE = str.maketrans("ABEZHIKMNOPTYX", "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ")      # Greek plates use only letters that look Latin
_PLATE_NAMES = {"italy": "IT", "spain": "ES", "france": "FR", "germany": "DE", "austria": "AT", "switzerland": "CH",
                "greece": "GR", "turkey": "TR", "türkiye": "TR", "united kingdom": "GB", "uk": "GB", "great britain": "GB",
                "britain": "GB", "england": "GB", "scotland": "GB", "wales": "GB", "morocco": "MA"}
PLATE_COUNTRY = {"IT": "Italy", "ES": "Spain", "FR": "France", "DE": "Germany", "AT": "Austria", "CH": "Switzerland",
                 "GR": "Greece", "TR": "Turkey", "GB": "United Kingdom", "MA": "Morocco"}
# board level of a code's place: cantons and Turkish provinces are first-level; UK memory tags name DVLA office towns
PLATE_LEVEL = {"CH": "admin1", "TR": "admin1", "GB": "city"}


def _plate_cc(country: str) -> str:
    c = country.strip()
    if c.upper() in PLATE_COUNTRY:
        return c.upper()
    return _PLATE_NAMES.get(_country_en(c).lower(), _PLATE_NAMES.get(c.lower(), c.upper()))


def _plate_keys(cc: str, v: str) -> list[str]:
    s = re.sub(r"[\s\-·.]", "", v).upper()
    keys = [s]
    if s.isdigit():
        if cc == "TR":
            keys.append(s.zfill(2))
        elif cc == "FR" and len(s) == 1:
            keys.append(s.zfill(2))
        elif cc == "MA":
            keys.append(str(int(s)))
    if cc == "GR":
        keys.append(s.translate(GREEK_LOOKALIKE))
    if cc == "IT" and s == "ROMA":
        keys.append("RM")
    return list(dict.fromkeys(keys))


def lookup_plate_code(value: str, country: str | None = None) -> dict:
    """Regional plate code outside China → place + the era it was used. Matches carry country/country_code with the
    region as admin1 and the place at its board level (PLATE_LEVEL), so board.py apply can place them."""
    d = load("plate_codes")
    fetched = d["_meta"]["fetched"]
    ccs = list(d["countries"])
    if country:
        cc = _plate_cc(country)
        if cc not in d["countries"]:
            r = _result("plate-code", value, [], "", fetched, f"no regional table for {country}; tables: {', '.join(ccs)}",
                        status="unsupported")
            return r
        ccs = [cc]
    ms = []
    for cc in ccs:
        ent = d["countries"][cc]
        lv = PLATE_LEVEL.get(cc, "admin2")
        for k in _plate_keys(cc, value or ""):
            for e in ent["codes"].get(k, []):
                m = {"country": PLATE_COUNTRY.get(cc, cc), "country_code": cc, "key": k}
                if e.get("region") and lv != "admin1":
                    m["admin1"] = e["region"]
                m[lv] = e["place"]
                m["note"] = f"[{cc} {k}] {e['era']}" + (f"; {e['note']}" if e.get("note") else "")
                ms.append(m)
        if cc == "GB":
            key = re.sub(r"\s", "", value or "").upper()
            for tname, tab in (ent.get("dating") or {}).items():
                if key in tab:
                    ms.append({"country": PLATE_COUNTRY["GB"], "country_code": "GB", "key": key,
                               "note": f"[GB] {tab[key]} (dates the registration, not a place: {tname.replace('_', ' ')} {key})"})
    src = d["countries"][ccs[0]]["source"] if len(ccs) == 1 else "Wikipedia, one page per country (assets/data/plate_codes.json)"
    note = d["countries"][ccs[0]]["note"] if len(ccs) == 1 else ("" if ms else "no country has this regional code; give --country or check the reading")
    if len({m["country_code"] for m in ms}) > 1:
        note = "; ".join(x for x in ("matches in several countries: keep each as a hypothesis, or pass --country", note) if x)
    r = _result("plate-code", value, ms, src, fetched, note)
    r["searched"] = ccs
    return r


def lookup_coverage(value: str | None) -> dict:
    """Countries/territories with official Google Street View car coverage, plus partial/limited ones."""
    f = DATA / "streetview_coverage.json"
    if not f.exists():
        return _result("coverage", value or "streetview", [], "", "", "assets/data/streetview_coverage.json is missing")
    d = json.loads(f.read_text(encoding="utf-8"))
    meta = d.get("_meta", {})
    ms = [{"country": c["name"], "country_code": c.get("iso2", ""), "note": "official coverage"} for c in d.get("official", [])]
    # partial/limited countries stay in: a game round can land on their few covered roads
    ms += [{"country": c["name"], "country_code": c.get("iso2", ""), "note": "partial/limited: " + c.get("note", "")}
           for c in d.get("partial", [])]
    src, as_of = (meta.get("source") or [""])[0], meta.get("as_of", "")
    q = (value or "").strip()
    if q and q.lower() not in ("streetview", "all", "*"):
        # one country (code or name): answer its coverage status instead of the whole list
        rec = _country_rec(_country_en(q))
        iso = rec["iso2"] if rec else None
        names = {n.lower() for n in _country_names(q)}
        sel = [m for m in ms if (iso and m["country_code"] == iso) or m["country"].lower() in names
               or (not iso and q.lower() in m["country"].lower())]
        if sel:
            return _result("coverage", q, sel, src, as_of, "coverage changes, verify edge cases with refsheet.py")
        if not rec and not any(c["name"].lower() in names for c in d.get("none_notable", [])):
            return _result("coverage", q, [], src, as_of, "not a country code/name; `coverage streetview` lists every covered country")
        return _result("coverage", q, [], src, as_of, f"{rec['name'] if rec else q}: no official Google Street View road coverage")
    return _result("coverage", q or "streetview", ms, src, as_of,
                   "official car coverage plus partial/limited countries; coverage changes, verify edge cases with refsheet.py")


# ---------------------------------------------------------------- region-pack lookups

def lookup_region(kind: str, value: str, country: str | None) -> dict:
    r = regions.lookup(kind, value, country)
    return {"kind": kind, "value": value, "status": r["status"], "matches": r["matches"], "searched": r.get("searched", []),
            "source": r.get("source", ""), "table_fetched": r.get("fetched", ""), "note": r.get("note", "")}


def lookup_admin(value: str | None, children: str | None, level: str | None, country: str | None) -> dict:
    want = {"city": "admin2", "county": "district"}.get(level or "", level)
    if children:
        p, kids = regions.admin_children(children.strip(), country)
        if not p:
            return _result("admin-children", children, [], "", "", "no installed pack has this admin area (use the full name, or gazetteer.py for OSM)",
                           status="unsupported" if country and not regions.resolve(country) else None)
        rows = []
        for k in kids:
            m = regions.match_from_item(p, k)
            m.update(code=k.get("code", ""), level=regions.level_name(p, k["level"]))
            if not want or m["level"] == want:
                rows.append(m)
        meta = regions.load_table(p, p["admin_table"]).get("_meta", {})
        return _result("admin-children", children, rows, ", ".join(meta.get("source") or []), meta.get("fetched", ""))
    name = (value or "").strip()
    rows, srcs = [], set()
    for p, it in regions.admin_find(name, country):
        m = regions.match_from_item(p, it)
        m.update(chain=regions.admin_chain(p, it), code=it.get("code", ""), level=regions.level_name(p, it["level"]))
        rows.append(m)
        srcs.add(", ".join(regions.load_table(p, p["admin_table"]).get("_meta", {}).get("source") or []))
    return _result("admin", name, rows, " | ".join(sorted(srcs)), "", "" if rows else "no admin area with this name in the installed packs (use the full name)")


def cmd_lookup(args) -> None:
    k = "plate" if args.kind == "plate-prefix" else args.kind
    if k == "calling-code":
        res = lookup_calling_code(args.value or "")
    elif k == "driving-side":
        res = lookup_driving_side(args.value, args.country)
    elif k == "territories":
        res = lookup_territories(args.value or "", args.continent)
    elif k == "admin":
        res = lookup_admin(args.value, args.children, args.level, args.country)
    elif k == "plate-code":
        res = lookup_plate_code(args.value or "", args.country)
    elif k == "coverage":
        res = lookup_coverage(args.value)
    else:
        kinds = sorted({x for p in regions.packs().values() for x in (p.get("lookups") or {})})
        if k not in kinds:
            sys.exit(f"kind: {' / '.join([*GLOBAL_KINDS, 'admin', *kinds])} (region kinds come from installed packs: `regions.py list`)")
        res = lookup_region(k, args.value or "", args.country)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return
    head = f"[{res['kind']}] {res['value']} → {len(res['matches'])} matches"
    if res["status"] == "unsupported":
        head = f"[{res['kind']}] {res['value']} → unsupported"
    if res.get("searched"):
        head += f" (packs searched: {', '.join(res['searched'])})"
    print(head + (f" ({res['note']})" if res["note"] else ""))
    for m in res["matches"][: args.limit]:
        if "country_code" in m and any(m.get(lv) for lv in regions.MATCH_LEVELS):
            chain = " / ".join(m[lv] for lv in regions.MATCH_LEVELS if m.get(lv))
            print(f"  {m['country_code']}: {chain}" + (f"  [{m['level']}]" if m.get("level") else "") + ("  (unverified)" if m.get("unverified") else "")
                  + (f"  {m['note']}" if m.get("note") else ""))
        else:
            print("  " + " / ".join(str(m.get(x)) for x in ("country", "side", "continent", "subregion", "utc") if m.get(x))
                  + (f"  switched {m['switched']}" if m.get("switched") else "") + (f"  {m['note']}" if m.get("note") else ""))
    if len(res["matches"]) > args.limit:
        print(f"  … {len(res['matches'])} in total; raise --limit")
    if res["source"]:
        print(f"source {res['source']}" + (f" ({res['table_fetched']})" if res["table_fetched"] else ""))


def cmd_list(args) -> None:
    for name in GLOBAL_TABLES:
        f = DATA / f"{name}.json"
        if not f.exists():
            print(f"{name}: missing")
            continue
        t = json.loads(f.read_text(encoding="utf-8"))
        m = t.get("_meta", {})
        src = m.get("source") or ["hand-compiled"]
        count = m.get("count") or sum(len(v) for k, v in t.items() if k != "_meta" and isinstance(v, (list, dict)))
        print(f"{name}: {count} entries, {f.stat().st_size // 1024} KB, fetched {m.get('fetched') or m.get('as_of')}, "
              f"source {src[0] if isinstance(src, list) else src}")
    for code, p in sorted(regions.packs().items()):
        for kind, spec in (p.get("lookups") or {}).items():
            try:
                meta = regions.load_table(p, spec["file"]).get("_meta", {})
            except regions.PACK_ERRORS as exc:
                print(f"{code.lower()}/{kind}: broken ({type(exc).__name__}); `regions.py lint {code.lower()}`")
                continue
            print(f"{code.lower()}/{kind}: {meta.get('count')} keys, fetched {meta.get('fetched')}, source {(meta.get('source') or ['?'])[0]}")
        if p.get("admin_table"):
            print(f"{code.lower()}/admin: {len(regions.admin_items(p))} areas")


def cmd_update(args) -> None:
    import refresh
    refresh.run(args.table, args.proxy, Path(args.from_dir) if args.from_dir else None)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    lk = sub.add_parser("lookup")
    lk.add_argument("kind")
    lk.add_argument("value", nargs="?")
    lk.add_argument("--country", help="region-pack kinds: restrict to this country's pack (code or name); driving-side: the country to look up")
    lk.add_argument("--continent")
    lk.add_argument("--children")
    lk.add_argument("--level", help="with --children: keep one level (admin2/district; city/county also accepted)")
    lk.add_argument("--json", action="store_true")
    lk.add_argument("--limit", type=int, default=40)
    sub.add_parser("list")
    up = sub.add_parser("update", help="refetch tables (refresh.py)")
    up.add_argument("table", nargs="?", default="all")
    up.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help="proxy URL or 'direct'")
    up.add_argument("--from-dir", help="directory of already-downloaded source files (for development)")
    args = ap.parse_args()
    {"lookup": cmd_lookup, "list": cmd_list, "update": cmd_update}[args.cmd](args)


if __name__ == "__main__":
    # Chinese-locale Windows writes GBK by default: m², ñ make it crash, and the Chinese the agent reads comes out garbled
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
