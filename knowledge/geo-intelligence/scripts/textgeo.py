#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "phonenumbers>=8.13", "lingua-language-detector>=2.0"]
# ///
"""Text in the photo → countries, regions and places, as board-ready evidence.

Reads OCR output (ocr.py / intake.py ocr.json) and/or strings you typed from a zoomed crop, then checks:
  scripts and digits (Thai, Hangul, Georgian, Tifinagh…; simplified vs traditional vs Japanese kanji)
  letters unique to a language (ő → Hungarian, ł → Polish, ș → Romanian, ї → Ukrainian, ђ → Serbian…)
  language identification of longer lines (lingua, offline)
  phone numbers (libphonenumber: country, and region/city for many landlines)
  web domains and e-mail addresses (ccTLD), postal codes with distinctive formats, currency marks
  regional sign/shop words (borracharia → Brazil, talho → Portugal, dairy → New Zealand, soi → Thailand…)
  brand names (OpenStreetMap name-suggestion-index: where each chain operates, incl. US states)
  place names (GeoNames: every town matching a word or phrase; --country XX --deep for a whole national gazetteer)

  textgeo.py --ocr intake/ocr.json --out textgeo.json [--md textgeo.md] [--min-conf 0.5]
  textgeo.py --text "Rua Augusta 24" --text "+351 21 342 0000"
  textgeo.py --text "ul. Długa 5, 80-831 Gdańsk" --country PL --deep
  textgeo.py --phone-pattern "6941 2?7788" --country GR    # a phone on a sign with one blurred digit → the valid candidates to search
  textgeo.py --phone-pattern "0522 2?-14-60" --country MA   # a landline: the area code still gives the city

Every signal says which text produced it. OCR mistakes produce wrong signals: check the zoomed crop
before you ingest (`board.py ingest textgeo.json`). Scripts and letters narrow languages, not borders
(minorities, tourists, diaspora shops, imported goods). Text you typed (--text/--file) is scored on its own; a script
signal read by RapidOCR stays `observed` unless the typed text gives one of the same kind over the same countries.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geodata  # noqa: E402
from geolib.net import PROXY_HELP  # noqa: E402
from geolib.paths import DATA_DIR  # noqa: E402

SIG = json.loads((DATA_DIR / "text_signals.json").read_text(encoding="utf-8"))
NSI_URL = "https://cdn.jsdelivr.net/npm/name-suggestion-index@8.0.20260918/dist/json/nsi.min.json"
M49 = {"001": "world", "150": "Europe", "002": "Africa", "019": "Americas", "142": "Asia", "009": "Oceania",
       "419": "Latin America and the Caribbean", "021": "Northern America", "005": "South America",
       "013": "Central America", "029": "Caribbean", "155": "Western Europe", "151": "Eastern Europe",
       "154": "Northern Europe", "039": "Southern Europe", "145": "Western Asia", "030": "Eastern Asia",
       "035": "South-eastern Asia", "034": "Southern Asia", "143": "Central Asia", "015": "Northern Africa",
       "202": "Sub-Saharan Africa", "011": "Western Africa", "014": "Eastern Africa", "017": "Middle Africa",
       "018": "Southern Africa", "053": "Australia and New Zealand", "054": "Melanesia", "057": "Micronesia",
       "061": "Polynesia", "eu": "European Union"}
SPECIAL_LOC = {"fx": "FR", "conus": "US", "uk": "GB", "northern cyprus": "CY", "gb-eng": "GB", "gb-sct": "GB",
               "gb-wls": "GB", "gb-nir": "GB"}
POSTAL_CONTEXT = re.compile(r"\b(plz|cp|c\.p\.|cep|cap|zip|postcode|post code|postal|código postal|codigo postal|"
                            r"code postal|postleitzahl|psč|psc|irányítószám|posta kodu|индекс|〒)\b", re.I)
SCRIPT_PREFIXES = ["CANADIAN SYLLABICS", "EXTENDED ARABIC-INDIC DIGIT", "ARABIC-INDIC DIGIT", "OL CHIKI", "NEW TAI LUE",
                   "TAI THAM", "TAI LE", "CJK", "HALFWIDTH KATAKANA", "FULLWIDTH LATIN", "HALFWIDTH HANGUL",
                   "KANGXI RADICAL", "IDEOGRAPHIC"]
SCRIPT_MAP = {"CJK": "CJK", "HALFWIDTH KATAKANA": "KATAKANA", "FULLWIDTH LATIN": "LATIN", "HALFWIDTH HANGUL": "HANGUL",
              "KANGXI RADICAL": "CJK", "IDEOGRAPHIC": "CJK", "EXTENDED ARABIC-INDIC DIGIT": "EXTENDED ARABIC-INDIC",
              "ARABIC-INDIC DIGIT": "ARABIC-INDIC"}
KNOWN_FIRST = {"LATIN", "CYRILLIC", "GREEK", "ARMENIAN", "GEORGIAN", "HEBREW", "ARABIC", "THAANA", "DEVANAGARI", "BENGALI",
               "GURMUKHI", "GUJARATI", "ORIYA", "TAMIL", "TELUGU", "KANNADA", "MALAYALAM", "SINHALA", "THAI", "LAO",
               "KHMER", "MYANMAR", "TIBETAN", "MONGOLIAN", "ETHIOPIC", "HANGUL", "HIRAGANA", "KATAKANA", "TIFINAGH",
               "CHEROKEE", "BALINESE", "JAVANESE", "SUNDANESE", "NKO", "VAI", "SYRIAC", "YI"}
# LR given to a script's main countries depending on how many share it
def _script_lr(n: int) -> float:
    return 25.0 if n <= 2 else 12.0 if n <= 4 else 6.0 if n <= 8 else 3.0


# ------------------------------------------------------------------ inputs

WATERMARK = re.compile(r"(©|\(c\)|copyright)?\s*(19|20)\d\d\s*(google|goog1e|goodle|apple|yandex|baidu|bing|microsoft|maxar|airbus)"
                       r"|^\W*(google|goodle|imagery|street view)\W*$|image ©|map data", re.I)
RAPIDOCR = "rapidocr"                    # ocr.json "backend" of the OCR used where Apple Vision is unavailable
RAPIDOCR_NOTE = ("OCR backend RapidOCR reads only Chinese characters, Latin letters and digits, and may drop Latin diacritics. "
                 "Any other script (Cyrillic, Greek, Hangul, kana, Arabic, Hebrew, Thai, Indic…) comes out as Latin/Chinese "
                 "look-alikes or nothing: read the zoomed crop and run `textgeo.py --text \"…\"`.")
RAPIDOCR_EMPTY = ("OCR backend RapidOCR reads only Chinese characters, Latin letters and digits: if the photo shows text in any "
                  "other script, read it from the zoomed crop and run `textgeo.py --text \"…\"`.")


def load_lines(args) -> tuple[list[dict], str | None]:
    """(lines to analyse, OCR backend named in the --ocr file or None)."""
    lines: list[dict] = []
    backend = None
    if args.ocr:
        d = json.loads(Path(args.ocr).read_text(encoding="utf-8"))
        backend = d.get("backend")
        for it in d.get("items", []):
            if WATERMARK.search(str(it.get("text", ""))):
                continue  # imagery/map provider watermark, not scene text (its year is a dating clue: see meta/recon)
            if it.get("conf", 1) >= args.min_conf and str(it.get("text", "")).strip():
                lines.append({"text": str(it["text"]).strip(), "conf": float(it.get("conf", 1)),
                              "box": it.get("box"), "pass": it.get("pass", "full"), "src": "ocr", "backend": backend})
    for t in args.text or []:
        if WATERMARK.search(t):
            continue
        lines.append({"text": t.strip(), "conf": 1.0, "box": None, "pass": "typed", "src": "typed"})
    if args.file:
        for t in Path(args.file).read_text(encoding="utf-8").splitlines():
            if t.strip():
                lines.append({"text": t.strip(), "conf": 1.0, "box": None, "pass": "typed", "src": "file"})
    return lines, backend


def script_of(ch: str) -> tuple[str | None, bool]:
    """(script, is_digit) of one character; None for punctuation, spaces, symbols."""
    if not ch.strip():
        return None, False
    try:
        n = unicodedata.name(ch)
    except ValueError:
        return None, False
    digit = "DIGIT" in n
    for p in SCRIPT_PREFIXES:
        if n.startswith(p):
            return SCRIPT_MAP.get(p, p), digit
    first = n.split(" ")[0]
    if first in KNOWN_FIRST:
        return first, digit
    return None, False


# ------------------------------------------------------------------ evidence helpers

class Board:
    """Collects signals; each has its own clue text, status and per-country LR."""

    def __init__(self, ocr_file: str | None):
        self.signals: list[dict] = []
        self.file = ocr_file or ""

    def add(self, kind: str, clue: str, lr: dict[str, float], status: str = "read", level: str = "country",
            **extra) -> None:
        lr = {k.upper(): round(float(v), 2) for k, v in lr.items() if k and v and abs(math.log(v)) > 1e-6}
        if lr:
            self.signals.append({"kind": kind, "clue": clue, "status": status, "level": level, "lr": lr,
                                 "file": self.file, **extra})


def lang_countries(lang: str) -> list[tuple[str, int]]:
    """(ISO2, rank) for countries that list the language (GeoNames country languages; rank 0 = first listed)."""
    base = lang.split("-")[0].lower()
    out = []
    for cc, c in geodata.countries().items():
        for i, l in enumerate(c.get("languages", [])):
            if l.split("-")[0].lower() == base:
                out.append((cc, i))
                break
    return out


def lang_lr(lang: str, primary: float, secondary: float) -> dict[str, float]:
    return {cc: (primary if rank == 0 else secondary) for cc, rank in lang_countries(lang)}


# ------------------------------------------------------------------ analyses

def analyse_scripts(lines: list[dict], ev: Board) -> dict:
    """Script, Han-form and digit-system signals. RapidOCR turns scripts it cannot read into Chinese/Latin look-alikes, so its
    lines are scored apart from the others (typed, another OCR): those give `read` signals of their own, and a RapidOCR signal
    is kept, `observed`, only where they give none of its kind over the same countries. The LR depends on character counts,
    so a typed confirmation is matched by kind and country set, never by value."""
    rapid = [ln for ln in lines if ln.get("backend") == RAPIDOCR]
    if not rapid:
        return _script_signals(lines, ev)
    own, seen = Board(ev.file), Board(ev.file)
    _script_signals([ln for ln in lines if ln.get("backend") != RAPIDOCR], own)
    _script_signals(rapid, seen)
    covered = {(s["kind"], frozenset(s["lr"])) for s in own.signals}
    for s in seen.signals:
        if (s["kind"], frozenset(s["lr"])) not in covered:
            own.signals.append({**s, "status": "observed", "clue": s["clue"] + " (RapidOCR, unconfirmed)"})
    ev.signals += own.signals
    return _script_signals(lines, Board(ev.file))              # the counts over every line; the signals come from the split above


def _script_signals(lines: list[dict], ev: Board) -> dict:
    letters: Counter = Counter()
    digits: Counter = Counter()
    examples: dict[str, str] = {}
    for ln in lines:
        for ch in ln["text"]:
            s, is_digit = script_of(ch)
            if not s:
                continue
            if is_digit:
                digits[s] += 1        # script_of() returns None for ASCII digits, so only non-Latin digit systems land here
                continue
            letters[s] += 1
            examples.setdefault(s, ln["text"][:40])
    for s, n in letters.items():
        if s == "LATIN" or s in ("CJK", "HIRAGANA", "KATAKANA") or n < 2:
            continue
        info = SIG["scripts"].get(s)
        if not info:
            continue
        main = info.get("countries", [])
        lr = {cc: _script_lr(len(main)) for cc in main}
        lr.update({cc: 2.0 for cc in info.get("weak_countries", []) if cc not in lr})
        ev.add("script", f"{s.title()} script ({n} characters, e.g. “{examples[s]}”)", lr,
               note=info.get("note", ""))
    # Han characters: simplified / traditional / Japanese forms
    text = "".join(ln["text"] for ln in lines)
    kana = letters.get("HIRAGANA", 0) + letters.get("KATAKANA", 0)
    han = letters.get("CJK", 0)
    H = SIG["hanzi"]
    simp = sorted({c for c in text if c in H["simplified"]})
    trad = sorted({c for c in text if c in H["traditional"]})
    jp = sorted({c for c in text if c in H["japanese"]})
    han_info = {"han": han, "kana": kana, "simplified_only": "".join(simp), "traditional_only": "".join(trad),
                "japanese_forms": "".join(jp)}
    if kana >= 2 or (jp and not simp):
        ev.add("script", f"Japanese writing (kana {kana}, Japanese kanji forms “{''.join(jp)}”)", {"JP": 25.0})
    elif han >= 2:
        if simp and not trad:
            k = 15.0 if len(simp) >= 2 else 5.0
            ev.add("script", f"Simplified Chinese characters (“{''.join(simp[:12])}”)", {"CN": k, "SG": 4.0, "MY": 2.0})
        elif trad and not simp:
            k = 8.0 if len(trad) >= 2 else 4.0
            ev.add("script", f"Traditional Chinese characters (“{''.join(trad[:12])}”)", {"TW": k, "HK": k, "MO": k * 0.75})
        else:
            ev.add("script", f"Chinese characters, simplified/traditional undecided ({han} characters)",
                   {"CN": 3.0, "TW": 3.0, "HK": 3.0, "MO": 3.0, "SG": 2.0, "JP": 1.5})
    if letters.get("HANGUL", 0) >= 2:
        ev.add("script", f"Hangul ({letters['HANGUL']} characters)", {"KR": 25.0, "KP": 3.0})
    for s, n in digits.items():
        info = SIG["digits"].get(s)
        if info and n >= 2:
            k = len(info["countries"])
            ev.add("digits", f"{s.title()} digits ({n})", {cc: (8.0 if k <= 3 else 3.0) for cc in info["countries"]},
                   note=info["note"])
    return {"letters_by_script": dict(letters.most_common()), "digits_by_script": dict(digits), "han": han_info}


def analyse_letters(lines: list[dict], ev: Board) -> dict:
    found: dict[str, list[str]] = defaultdict(list)
    for ln in lines:
        if ln["conf"] < 0.5:
            continue
        for ch in set(ln["text"]):
            key = ch if ch in SIG["letters"] else ch.lower()
            if key in SIG["letters"]:
                found[key].append(ln["text"][:40])
    # A language is "confirmed" only by a letter no other language uses (ł → pl, ő → hu, ї → uk).
    # Shared letters (ą: pl/lt) are then explained by a confirmed language instead of crediting the others.
    unique: dict[str, list[str]] = defaultdict(list)
    for ch in found:
        langs = SIG["letters"][ch]["langs"]
        if len(langs) == 1:
            unique[langs[0]].append(ch)
        if SIG["letters"][ch].get("countries"):
            info = SIG["letters"][ch]
            ev.add("letters", f"letter “{ch}” ({info.get('note', '')}) in “{found[ch][0]}”", {cc: 4.0 for cc in info["countries"]})
    confirmed = set(unique)
    lang_score: dict[str, float] = defaultdict(float)
    lang_letters: dict[str, list[str]] = defaultdict(list)
    for ch in found:
        langs = SIG["letters"][ch]["langs"]
        if len(langs) > 1 and confirmed & set(langs):
            for l in confirmed & set(langs):
                lang_letters[l].append(ch)
            continue
        for l in langs:
            lang_score[l] += 1.0 / len(langs)
            lang_letters[l].append(ch)
    for l in sorted(confirmed, key=lambda l: -len(unique[l])):
        lr = lang_lr(l, 10.0, 3.0)
        if lr:
            ev.add("letters", f"letters {' '.join(sorted(set(unique[l] + lang_letters[l])))} → language “{l}”", lr, language=l)
    weak = {l: v for l, v in lang_score.items() if v >= 0.2 and l not in confirmed}
    if weak:
        lr: dict[str, float] = {}
        for l in weak:
            for cc, v in lang_lr(l, 2.0, 1.3).items():
                lr[cc] = max(lr.get(cc, 1.0), v)
        letters_txt = " ".join(sorted({c for l in weak for c in lang_letters[l]}))
        ev.add("letters", f"shared letters {letters_txt} → one of {', '.join(sorted(weak))}", lr, status="inferred")
    for l in confirmed:
        lang_score[l] += len(unique[l])
    return {"letters": {k: v[:3] for k, v in found.items()}, "languages_by_letters": dict(sorted(lang_score.items(), key=lambda kv: -kv[1]))}


_DETECTOR = None


def _phone_types() -> dict[int, str]:
    """phonenumbers.number_type() code → name (FIXED_LINE, MOBILE, …)."""
    import phonenumbers
    return {v: k for k, v in vars(phonenumbers.PhoneNumberType).items() if k.isupper() and isinstance(v, int)}


def analyse_language(lines: list[dict], ev: Board) -> list[dict]:
    """lingua on lines with enough letters and on all text together."""
    global _DETECTOR
    try:
        from lingua import LanguageDetectorBuilder
    except Exception as e:  # noqa: BLE001
        return [{"error": f"lingua unavailable: {e}"}]
    if _DETECTOR is None:
        _DETECTOR = LanguageDetectorBuilder.from_all_languages().build()
    out = []
    chunks = [ln["text"] for ln in lines if sum(ch.isalpha() for ch in ln["text"]) >= 12 and ln["conf"] >= 0.5]
    alltext = " · ".join(ln["text"] for ln in lines if ln["conf"] >= 0.5)
    if sum(ch.isalpha() for ch in alltext) >= 20:
        chunks.append(alltext)
    votes: dict[str, float] = defaultdict(float)
    for t in chunks[:40]:
        vals = _DETECTOR.compute_language_confidence_values(t)
        if not vals:
            continue
        top = vals[0]
        second = vals[1].value if len(vals) > 1 else 0.0
        code = top.language.iso_code_639_1.name.lower()
        out.append({"text": t[:60], "language": code, "confidence": round(top.value, 3), "margin": round(top.value - second, 3)})
        if top.value >= 0.6 and top.value - second >= 0.2:
            votes[code] += min(1.0, len(t) / 40)
    for code, v in sorted(votes.items(), key=lambda kv: -kv[1])[:3]:
        if v < 0.3:
            continue
        lr = lang_lr(code, 3.0, 1.5)
        if lr:
            ev.add("language", f"language identified as “{code}” (lingua, weight {v:.1f})", lr, status="inferred", language=code)
    return out


def analyse_phones(lines: list[dict], ev: Board, shortlist: list[str]) -> list[dict]:
    import phonenumbers
    from phonenumbers import carrier, geocoder
    types = _phone_types()
    found: dict[str, dict] = {}
    regions = [r for r in shortlist if r in phonenumbers.SUPPORTED_REGIONS][:12]
    texts = [ln["text"] for ln in lines]
    texts += [a["text"] + " " + b["text"] for a, b in zip(lines, lines[1:])]  # numbers split across OCR lines
    for t in texts:
        if sum(ch.isdigit() for ch in t) < 6:
            continue
        for region in ["ZZ", *regions]:
            try:
                matches = list(phonenumbers.PhoneNumberMatcher(t, region, leniency=phonenumbers.Leniency.VALID))
            except Exception:  # noqa: BLE001
                continue
            for m in matches:
                n = m.number
                e164 = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)
                rc = phonenumbers.region_code_for_number(n)
                rec = found.setdefault(e164, {"raw": m.raw_string, "e164": e164, "international": t.strip().startswith("+") or m.raw_string.strip().startswith("+") or m.raw_string.strip().startswith("00"),
                                              "regions": set(), "description": geocoder.description_for_number(n, "en"),
                                              "carrier": carrier.name_for_number(n, "en"),
                                              "type": types.get(phonenumbers.number_type(n), "UNKNOWN")})
                if rc:
                    rec["regions"].add(rc)
                if region == "ZZ":
                    rec["international"] = True
    out = []
    for e164, r in found.items():
        regions_ = sorted(r["regions"])
        r["regions"] = regions_
        out.append(r)
        if not regions_:
            continue
        where = f" ({r['description']})" if r["description"] else ""
        if r["international"] and len(regions_) == 1:
            ev.add("phone", f"phone number {r['raw']} → {geodata.country_name(regions_[0])}{where}", {regions_[0]: 20.0},
                   region=r["description"])
        elif len(regions_) == 1:
            ev.add("phone", f"phone number {r['raw']} valid as a national number in {geodata.country_name(regions_[0])}{where} "
                   f"(tested regions: {', '.join(regions) or 'none'})", {regions_[0]: 6.0}, region=r["description"])
        elif len(regions_) <= 3:
            ev.add("phone", f"phone number {r['raw']} valid in {', '.join(regions_)}", {cc: 3.0 for cc in regions_})
    return out


TLD_RE = re.compile(r"(?:https?://)?(?:www\.)?((?:[a-z0-9-]+\.)+([a-z]{2,24}))(?![a-z0-9-])", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@((?:[\w-]+\.)+([a-z]{2,24}))", re.I)


def analyse_domains(lines: list[dict], ev: Board) -> list[dict]:
    tld2cc = {c["tld"].lstrip(".").lower(): cc for cc, c in geodata.countries().items() if c.get("tld")}
    out = []
    seen = set()
    for ln in lines:
        t = ln["text"]
        for m in list(EMAIL_RE.finditer(t)) + list(TLD_RE.finditer(t)):
            host, tld = m.group(1).lower(), m.group(2).lower()
            if host in seen or "." not in host or re.fullmatch(r"[\d.]+", host):
                continue
            # skip things like "St. Mary" / "No. 5": require a plausible host (letters before the TLD, no spaces)
            if len(host.split(".")[-2]) < 2:
                continue
            seen.add(host)
            cc = tld2cc.get(tld)
            rec = {"host": host, "tld": tld, "country": cc}
            out.append(rec)
            if cc and tld not in SIG["vanity_tlds"]:
                ev.add("domain", f"web address {host} (.{tld} = {geodata.country_name(cc)})", {cc: 6.0})
    return out


def analyse_postal(lines: list[dict], ev: Board) -> list[dict]:
    pats = []
    for cc, c in geodata.countries().items():
        rx = c.get("postal_regex")
        if rx:
            try:
                pats.append((cc, re.compile(rx, re.I), c.get("postal_format", "")))
            except re.error:
                pass
    out = []
    for ln in lines:
        toks = re.findall(r"[A-Za-z0-9]+(?:[- ][A-Za-z0-9]+)?", ln["text"])
        cands = set(toks) | set(re.findall(r"\b[A-Za-z0-9]{2,4}[- ][A-Za-z0-9]{2,4}\b", ln["text"]))
        context = bool(POSTAL_CONTEXT.search(ln["text"]))
        # a run of 9+ digits (with spaces/dashes) is a phone number, not an address line
        if not context and re.search(r"(?:\+|\b00)\d|(?:\d[\s\-./()]*){9,}", ln["text"]):
            continue
        for tok in cands:
            if not any(ch.isdigit() for ch in tok) or len(tok) < 3:
                continue
            hits = [cc for cc, rx, _ in pats if rx.fullmatch(tok) or rx.fullmatch(tok.upper())]
            if not hits:
                continue
            distinctive = bool(re.search(r"[A-Za-z]", tok) or re.search(r"[- ]", tok))
            if not (distinctive or context):
                continue
            if len(hits) > 6 and not context:
                continue
            out.append({"token": tok, "countries": hits, "line": ln["text"][:60], "context_word": context})
            lr = 4.0 if len(hits) <= 3 else 2.0
            ev.add("postal", f"postal-code format “{tok}” in “{ln['text'][:40]}” fits {', '.join(hits[:8])}",
                   {cc: lr for cc in hits}, status="read" if len(hits) <= 3 else "inferred")
    return out


def analyse_currency(lines: list[dict], ev: Board) -> list[dict]:
    out = []
    text = " \n".join(ln["text"] for ln in lines)
    for c in SIG["currency"]:
        p = c["pattern"]
        if c.get("word"):
            hit = re.search(r"(?<![\w])" + re.escape(p) + r"(?![\w])", text) and re.search(r"\d", text)
        else:
            hit = p in text
        if not hit:
            continue
        out.append({"pattern": p, "countries": c["countries"], "note": c.get("note", "")})
        k = len(c["countries"])
        lr = 8.0 if k == 1 else 4.0 if k <= 4 else 2.0
        status = "read" if not c.get("word") else "inferred"
        ev.add("currency", f"currency mark “{p}”" + (f" ({c['note']})" if c.get("note") else ""),
               {cc: lr for cc in c["countries"]} | {cc: 1.5 for cc in c.get("weak_countries", [])}, status=status)
    return out


def _tokens(text: str) -> list[str]:
    return [t for t in geodata.norm(text).split(" ") if t]


def _ngrams(toks: list[str], nmax: int = 4) -> list[str]:
    out = []
    for n in range(1, nmax + 1):
        for i in range(len(toks) - n + 1):
            out.append(" ".join(toks[i:i + n]))
    return out


WORDS = {geodata.norm(k): v for k, v in SIG["words"].items() if not k.startswith("_")}


def analyse_words(lines: list[dict], ev: Board) -> list[dict]:
    out = []
    seen = set()
    for ln in lines:
        for g in _ngrams(_tokens(ln["text"]), 2):
            if g in WORDS and g not in seen:
                seen.add(g)
                w = WORDS[g]
                out.append({"word": g, "line": ln["text"][:60], **w})
                if w.get("countries"):
                    ev.add("word", f"regional word “{g}” in “{ln['text'][:40]}”" + (f" ({w['note']})" if w.get("note") else ""),
                           {cc: 4.0 for cc in w["countries"]}, status="read" if len(w["countries"]) <= 3 else "inferred")
    # language support from words without a country
    lang_votes: Counter = Counter()
    for o in out:
        if not o.get("countries"):
            for l in o["langs"]:
                lang_votes[l] += 1.0 / len(o["langs"])
    for l, v in lang_votes.most_common(2):
        if v >= 0.99:
            lr = lang_lr(l, 3.0, 1.5)
            if lr:
                ev.add("word", f"sign/shop words in “{l}” ({', '.join(o['word'] for o in out if l in o['langs'])[:80]})",
                       lr, status="inferred", language=l)
    return out


# ------------------------------------------------------------------ brands (name-suggestion-index)

def _brand_index(proxy: str | None) -> dict[str, list[dict]]:
    base = geodata.cache_dir("nsi")
    pkl = base / "brands.v1.pkl"
    if pkl.exists():
        with pkl.open("rb") as f:
            return pickle.load(f)
    src = base / "nsi.min.json"
    if not src.exists():
        print("Downloading the brand index (name-suggestion-index, 12 MB, one time) …", file=sys.stderr)
        geodata.download(NSI_URL, src, proxy)
    d = json.loads(src.read_text(encoding="utf-8"))["nsi"]
    idx: dict[str, list[dict]] = defaultdict(list)
    for cat, v in d.items():
        if not cat.startswith("brands/"):
            continue
        for it in v.get("items", []):
            tags = it.get("tags", {})
            names = {it.get("displayName", ""), tags.get("brand", ""), tags.get("name", "")}
            names |= {val for k, val in tags.items() if k.startswith(("brand:", "name:")) and not k.endswith("wikidata")
                      and not k.endswith("wikipedia")}
            rec = {"brand": it.get("displayName", ""), "category": cat.split("/", 1)[1],
                   "include": it.get("locationSet", {}).get("include", []),
                   "exclude": it.get("locationSet", {}).get("exclude", [])}
            for n in names:
                k = geodata.norm(n)
                if len(k) >= 3:
                    idx[k].append(rec)
    idx = dict(idx)
    tmp = pkl.with_name(f"{pkl.name}.{os.getpid()}.tmp")  # atomic for parallel sessions
    with tmp.open("wb") as f:
        pickle.dump(idx, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, pkl)
    return idx


def _loc(inc) -> tuple[str | None, str]:
    """locationSet entry → (ISO2 or None, label)."""
    if isinstance(inc, list):
        return None, f"point {inc}"
    s = str(inc).lower()
    if s in SPECIAL_LOC:
        return SPECIAL_LOC[s], s
    if s in M49:
        return None, M49[s]
    if re.fullmatch(r"[a-z]{2}", s):
        return s.upper(), s.upper()
    m = re.match(r"([a-z]{2})-([a-z0-9_]+)", s)
    if m:
        return m.group(1).upper(), s.replace(".geojson", "")
    return None, s


def analyse_brands(lines: list[dict], ev: Board, proxy: str | None) -> list[dict]:
    try:
        idx = _brand_index(proxy)
    except Exception as e:  # noqa: BLE001
        return [{"error": f"brand index unavailable: {e}"}]
    out = []
    seen = set()
    for ln in lines:
        toks = _tokens(ln["text"])
        for g in _ngrams(toks, 4):
            if g in seen or g not in idx or g in WORDS:
                continue
            if len(g) < 4 and g != " ".join(toks):
                continue
            seen.add(g)
            recs = idx[g]
            countries: set[str] = set()
            regions: set[str] = set()
            worldwide = False
            for r in recs:
                for inc in r["include"]:
                    cc, label = _loc(inc)
                    if label == "world" or (cc is None and label in M49.values()):
                        worldwide = worldwide or label == "world"
                        regions.add(label)
                    elif cc:
                        countries.add(cc)
                        if "-" in label:
                            regions.add(label)
            cats = sorted({r["category"] for r in recs})[:4]
            rec = {"text": g, "brand": recs[0]["brand"], "categories": cats, "countries": sorted(countries),
                   "regions": sorted(regions)[:12], "worldwide": worldwide, "line": ln["text"][:60]}
            out.append(rec)
            if worldwide or not countries or len(countries) > 8:
                continue
            lr = 6.0 if len(countries) <= 2 else 3.0 if len(countries) <= 5 else 1.7
            sub = [r for r in regions if "-" in r]
            ev.add("brand", f"brand “{recs[0]['brand']}” ({', '.join(cats[:2])}) operates in {', '.join(sorted(countries))}"
                   + (f"; regions {', '.join(sub[:6])}" if sub else ""), {cc: lr for cc in countries},
                   status="read" if len(countries) <= 2 else "inferred", regions=sub)
    return out


# ------------------------------------------------------------------ places (GeoNames)

STOP = set(WORDS) | {"the", "and", "for", "of", "de", "la", "le", "el", "los", "las", "les", "der", "die", "das", "und", "da", "do",
                     "dos", "das", "del", "di", "du", "des", "van", "von", "hotel", "bar", "cafe", "park", "centro", "center",
                     "centre", "taxi", "bus", "stop", "open", "closed", "sale", "new", "city", "market", "bank", "school",
                     "church", "station", "police", "hospital", "airport", "exit", "north", "south", "east", "west", "km",
                     "nord", "sud", "est", "ouest", "norte", "sul", "este", "oeste", "zona", "info", "shop", "store",
                     "restaurant", "pizza", "parking", "entrance", "toilet", "wc", "free", "only", "one", "way", "no",
                     "san", "santa", "saint", "st", "mount", "lake", "river", "beach", "port", "ville", "town", "village",
                     "google", "apple", "yandex", "baidu", "bing", "maxar", "airbus", "copyright", "image", "imagery"}


def analyse_places(lines: list[dict], ev: Board, cc: str | None, deep: bool, proxy: str | None) -> list[dict]:
    try:
        geodata.places(proxy)
    except Exception as e:  # noqa: BLE001
        return [{"error": f"GeoNames places unavailable: {e}"}]
    hits: dict[int, dict] = {}
    for ln in lines:
        toks = _tokens(ln["text"])
        grams = _ngrams(toks, 4)
        for g in sorted(set(grams), key=lambda s: -len(s)):
            if len(g) < 4 or g in STOP or g.isdigit() or all(t in STOP for t in g.split()):
                continue
            rows = geodata.search(g, cc, limit=40, deep=deep, proxy=proxy)
            for r in rows:
                key = r["geonameid"]
                if key not in hits:
                    hits[key] = {**r, "matched": g, "line": ln["text"][:60]}
    rows = sorted(hits.values(), key=lambda r: (r.get("match") != "name", -len(r["matched"]), -r["population"]))
    # country-level hint: a long name whose matches concentrate in one country
    by_name: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_name[r["matched"]].append(r)
    for name, rs in by_name.items():
        if len(name) < 6:
            continue
        pop = Counter()
        for r in rs:
            pop[r["country"]] += r["population"] + 50
        top, v = pop.most_common(1)[0]
        share = v / sum(pop.values())
        if share >= 0.8 and len(pop) <= 3:
            ev.add("place-name", f"place name “{name}” matches {len(rs)} GeoNames places, {share:.0%} of them by population "
                   f"in {geodata.country_name(top)} (largest: {rs[0]['name']}, {rs[0]['admin1']})", {top: 3.0}, status="inferred")
    return rows[:40]


# ------------------------------------------------------------------ combine

def shortlist(ev: Board) -> list[dict]:
    caps = {"inferred": 3.0, "observed": 5.0, "read": 50.0, "computed": 50.0, "model": 3.0}
    score: dict[str, float] = defaultdict(float)
    reasons: dict[str, list[str]] = defaultdict(list)
    for s in ev.signals:
        cap = caps.get(s["status"], 3.0)
        for cc, lr in s["lr"].items():
            lr2 = min(max(lr, 1 / cap), cap)
            score[cc] += math.log(lr2)
            reasons[cc].append(f"{s['kind']}×{lr2:g}")
    rows = [{"iso2": cc, "name": geodata.country_name(cc), "log_lr": round(v, 2), "reasons": reasons[cc]}
            for cc, v in score.items()]
    rows.sort(key=lambda r: -r["log_lr"])
    return rows


def to_md(res: dict) -> str:
    L = ["# Text → place signals", ""]
    if res.get("ocr_backend") == RAPIDOCR and res.get("n_ocr_lines"):
        L += [f"**{RAPIDOCR_NOTE}**", ""]
    L.append(f"{res['n_lines']} text lines analysed (min OCR confidence {res['min_conf']}). Each signal names the text it came from: "
             "check the zoomed crop before trusting it. Ingest with `board.py ingest textgeo.json`.")
    L += ["", "## Country shortlist from text", ""]
    if res["shortlist"]:
        L.append("| Country | log LR | from |")
        L.append("|---|---|---|")
        for r in res["shortlist"][:12]:
            L.append(f"| {r['name']} ({r['iso2']}) | {r['log_lr']} | {', '.join(r['reasons'][:6])} |")
    else:
        L.append("No country-level signal from text.")
    L += ["", "## Signals", ""]
    for s in res["signals"]:
        top = ", ".join(f"{k}×{v:g}" for k, v in sorted(s["lr"].items(), key=lambda kv: -kv[1])[:8])
        L.append(f"- [{s['kind']}/{s['status']}] {s['clue']} → {top}")
    if res.get("phones"):
        L += ["", "## Phone numbers", ""]
        for p in res["phones"]:
            L.append(f"- {p['raw']} → {p['e164']} regions {p['regions']} {p['description']} {p['carrier']} ({p['type']})")
    if res.get("brands"):
        L += ["", "## Brands (name-suggestion-index)", ""]
        for b in res["brands"][:15]:
            if "error" in b:
                L.append(f"- {b['error']}")
                continue
            where = "worldwide" if b["worldwide"] else ", ".join(b["countries"][:12])
            L.append(f"- “{b['text']}” = {b['brand']} ({', '.join(b['categories'][:2])}): {where}"
                     + (f"; {', '.join(b['regions'][:6])}" if b["regions"] else ""))
    if res.get("places"):
        L += ["", "## Place names (GeoNames; many are coincidences — check context)", ""]
        for p in res["places"][:20]:
            if "error" in p:
                L.append(f"- {p['error']}")
                continue
            alt = " (alternate name)" if p.get("match") == "alternate" else ""
            L.append(f"- “{p['matched']}” → {p['name']}{alt}, {p['admin1']}, {p['country_name']} "
                     f"({p['lat']}, {p['lon']}; pop {p['population']}; {p['feature']})")
    if res.get("languages"):
        L += ["", "## Language identification (lingua)", ""]
        for x in res["languages"][:10]:
            if "error" in x:
                L.append(f"- {x['error']}")
            else:
                L.append(f"- {x['language']} {x['confidence']:.2f} (margin {x['margin']:.2f}): “{x['text']}”")
    return "\n".join(L) + "\n"


def enumerate_phone(pattern: str, region: str | None) -> None:
    """A phone number on a sign with one or more unreadable digits: '?' is an unknown digit. Keep only valid numbers, show where each lands, and print exact-match search queries (one blurred digit = 10 candidates; search each in quotes)."""
    import phonenumbers
    from phonenumbers import carrier, geocoder
    raw = re.sub(r"[^\d?+]", "", pattern)
    qmarks = raw.count("?")
    if qmarks == 0:
        print("No '?' in the pattern; nothing to enumerate. Mark each unreadable digit with '?'.")
    if qmarks > 5:
        sys.exit(f"{qmarks} unknown digits = {10 ** qmarks} combinations; read more of the number first (max 5 '?').")
    pos = [i for i, ch in enumerate(raw) if ch == "?"]
    types = _phone_types()
    hits = []
    for combo in range(10 ** qmarks):
        s = list(raw)
        for k, p in enumerate(pos):
            s[p] = str((combo // 10 ** (qmarks - 1 - k)) % 10)
        cand = "".join(s)
        try:
            n = phonenumbers.parse(cand, region)
        except phonenumbers.NumberParseException:
            continue
        if not phonenumbers.is_valid_number(n):
            continue
        e164 = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)
        natl = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.NATIONAL)
        rc = phonenumbers.region_code_for_number(n)
        where = geocoder.description_for_number(n, "en")
        typ = types.get(phonenumbers.number_type(n), "?")
        hits.append((e164, natl, rc, typ, where, carrier.name_for_number(n, "en")))
    print(f"{qmarks} unknown digit(s) → {len(hits)} valid number(s)" + (f" in region {region}" if region else "") + ":")
    for e164, natl, rc, typ, where, car in hits:
        extra = " · ".join(x for x in (rc, typ.lower(), where, car) if x)
        print(f"  {e164:16}  {natl:18}  {extra}")
    if hits:
        print("\nSearch each in quotes (exact match), e.g. a web search and national directories:")
        for e164, natl, *_ in hits:
            digits = re.sub(r"\D", "", natl)
            print(f'  "{e164}"   "{natl}"   "{digits}"')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phone-pattern", help="a phone number with unreadable digits as '?', e.g. \"6941 2?7788\"; enumerate valid numbers (use with --country)")
    ap.add_argument("--ocr", help="ocr.json from ocr.py / intake.py")
    ap.add_argument("--text", action="append", help="a string you read yourself (repeatable)")
    ap.add_argument("--file", help="text file, one line per sign")
    ap.add_argument("--min-conf", type=float, default=0.4, help="ignore OCR lines below this confidence")
    ap.add_argument("--country", help="restrict place-name search to this country (name or ISO2)")
    ap.add_argument("--deep", action="store_true", help="search the full national gazetteer of --country (villages, hills, rivers…)")
    ap.add_argument("--no-lingua", action="store_true")
    ap.add_argument("--no-brands", action="store_true")
    ap.add_argument("--no-places", action="store_true")
    ap.add_argument("--out", help="JSON output (board-ready signals)")
    ap.add_argument("--md", help="Markdown summary")
    ap.add_argument("--proxy", default=os.environ.get("GEO_PROXY"), help=PROXY_HELP)
    args = ap.parse_args()
    if args.phone_pattern:
        region = None
        if args.country:
            c = geodata.country(args.country)
            region = c["iso2"] if c else args.country.upper()
        enumerate_phone(args.phone_pattern, region)
        return
    lines, backend = load_lines(args)
    ocr_info = {"ocr_backend": backend} if args.ocr else {}
    if not lines:
        if not (args.ocr or args.text or args.file):
            sys.exit("No text: give --ocr ocr.json, --text \"…\" or --file")
        # OCR ran but found nothing usable: an empty result, not an error
        blind = f"\n{RAPIDOCR_EMPTY}\n" if backend == RAPIDOCR else ""
        empty = {"tool": "textgeo.py", "n_lines": 0, "min_conf": args.min_conf, **ocr_info, "lines": [], "signals": [], "shortlist": [],
                 "note": "no text above the confidence threshold (watermarks ignored); read small or unsupported scripts yourself"}
        if args.out:
            Path(args.out).write_text(json.dumps(empty, ensure_ascii=False, indent=1), encoding="utf-8")
        if args.md:
            Path(args.md).write_text("# Text → place signals\n\nNo usable text found.\n" + blind, encoding="utf-8")
        print("No usable text found (nothing to analyse)." + blind.rstrip())
        return
    ocr_file = None
    if args.ocr:
        png = Path(args.ocr).with_suffix(".png")
        ocr_file = str(png if png.exists() else Path(args.ocr))
    ev = Board(ocr_file)
    res: dict = {"tool": "textgeo.py", "n_lines": len(lines), "n_ocr_lines": sum(ln["src"] == "ocr" for ln in lines),
                 "min_conf": args.min_conf, **ocr_info, "lines": [ln["text"] for ln in lines][:200]}
    res["scripts"] = analyse_scripts(lines, ev)
    res["letters"] = analyse_letters(lines, ev)
    res["languages"] = [] if args.no_lingua else analyse_language(lines, ev)
    res["domains"] = analyse_domains(lines, ev)
    res["postal"] = analyse_postal(lines, ev)
    res["currency"] = analyse_currency(lines, ev)
    res["words"] = analyse_words(lines, ev)
    res["brands"] = [] if args.no_brands else analyse_brands(lines, ev, args.proxy)
    cc = None
    if args.country:
        c = geodata.country(args.country)
        cc = c["iso2"] if c else args.country.upper()
    short = [r["iso2"] for r in shortlist(ev)]
    if cc and cc not in short:
        short.insert(0, cc)
    res["phones"] = analyse_phones(lines, ev, short or ["US", "GB", "IN", "BR", "DE", "FR", "ES", "IT", "MX", "JP"])
    res["places"] = [] if args.no_places else analyse_places(lines, ev, cc, args.deep, args.proxy)
    res["signals"] = ev.signals
    res["shortlist"] = shortlist(ev)
    if args.out:
        Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    md = to_md(res)
    if args.md:
        Path(args.md).write_text(md, encoding="utf-8")
    print(md if len(md) < 6000 else md[:6000] + "\n…(truncated; see --md/--out)")
    if args.out:
        print(f"-> {args.out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
