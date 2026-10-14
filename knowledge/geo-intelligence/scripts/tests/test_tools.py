#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow", "phonenumbers>=8.13", "lingua-language-detector>=2.0", "tzdata", "cbor2>=6.1.5,<7"]
# ///
"""Offline checks for the newer tools. Run: uv run scripts/tests/test_tools.py
Network-free: GeoNames- and brand-index-dependent checks are skipped when those caches are absent."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import numpy as np
import cbor2
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import geodata  # noqa: E402
import textgeo  # noqa: E402
import meta  # noqa: E402
from geolib import streetlevel as SL  # noqa: E402
from geolib.paths import cache_root  # noqa: E402

CACHE = cache_root()
HAVE_PLACES = any((CACHE / "geonames").glob("cities500*.pkl"))
HAVE_BRANDS = (CACHE / "nsi" / "brands.v1.pkl").exists()


def signals(*texts: str, places: bool = False, brands: bool = False) -> tuple[list[dict], list[dict]]:
    lines = [{"text": t, "conf": 1.0, "box": None, "pass": "typed", "src": "typed"} for t in texts]
    ev = textgeo.Board(None)
    textgeo.analyse_scripts(lines, ev)
    textgeo.analyse_letters(lines, ev)
    textgeo.analyse_domains(lines, ev)
    textgeo.analyse_postal(lines, ev)
    textgeo.analyse_currency(lines, ev)
    textgeo.analyse_words(lines, ev)
    if brands:
        textgeo.analyse_brands(lines, ev, None)
    textgeo.analyse_phones(lines, ev, [r["iso2"] for r in textgeo.shortlist(ev)] or ["US"])
    if places:
        textgeo.analyse_places(lines, ev, None, False, None)
    return ev.signals, textgeo.shortlist(ev)


class CountryDataTests(unittest.TestCase):
    def test_osm_geom_keeps_relations_as_multilinestrings(self):
        import osm
        rel = {"type": "relation", "id": 6422525, "tags": {"natural": "water", "name": "Lago di Tovel", "type": "multipolygon"},
               "members": [{"type": "way", "ref": 1, "role": "outer", "geometry": [{"lat": 46.26, "lon": 10.94}, {"lat": 46.27, "lon": 10.95}]},
                           {"type": "way", "ref": 2, "role": "outer", "geometry": [{"lat": 46.27, "lon": 10.95}, {"lat": 46.26, "lon": 10.96}]},
                           {"type": "node", "ref": 3, "role": "label", "lat": 46.265, "lon": 10.95}]}
        f = osm._geom_feature(rel)
        self.assertEqual(f["geometry"]["type"], "MultiLineString")
        self.assertEqual(len(f["geometry"]["coordinates"]), 2)
        self.assertEqual(f["properties"]["name"], "Lago di Tovel")
        self.assertIsNone(osm._geom_feature({"type": "relation", "id": 1, "tags": {}}))          # `out tags` reply: no members
        way = {"type": "way", "id": 5, "tags": {"natural": "water"}, "geometry": [{"lat": 46.0, "lon": 11.0}, {"lat": 46.1, "lon": 11.0}]}
        self.assertEqual(osm._geom_feature(way)["geometry"]["type"], "LineString")

    def test_aliases_and_driving_side(self):
        self.assertEqual(geodata.country("Czech Republic")["iso2"], "CZ")
        self.assertEqual(geodata.country("UK")["iso2"], "GB")
        self.assertEqual(geodata.country("Ivory Coast")["iso2"], "CI")
        self.assertEqual(geodata.country("Azores")["iso2"], "PT")
        self.assertEqual(geodata.country("GB")["drive"], "left")
        self.assertEqual(geodata.country("CN")["drive"], "right")
        self.assertEqual(geodata.country("HK")["drive"], "left")
        self.assertEqual(geodata.country("GI")["drive"], "right")
        self.assertNotIn("CS", geodata.countries())

    def test_norm_folds_accents_not_scripts(self):
        self.assertEqual(geodata.norm("São Tomé"), "sao tome")
        self.assertEqual(geodata.norm("Москва"), "москва")

    def test_chinese_and_former_names_resolve(self):
        self.assertEqual(geodata.country("葡萄牙")["iso2"], "PT")
        self.assertEqual(geodata.country("德國")["iso2"], "DE")       # traditional form
        self.assertEqual(geodata.country("Ceylon")["iso2"], "LK")
        self.assertIsNone(geodata.country("Atlantis"))


class TextSignalTests(unittest.TestCase):
    def top(self, *texts, **kw):
        _, short = signals(*texts, **kw)
        return short[0]["iso2"] if short else None

    def test_scripts(self):
        self.assertEqual(self.top("ถนนสุขุมวิท ซอย 11"), "TH")
        self.assertEqual(self.top("東京駅 丸の内北口"), "JP")
        self.assertEqual(self.top("서울특별시 종로구"), "KR")
        self.assertIn(self.top("台北市忠孝東路四段"), ("TW", "HK"))

    def test_unique_letters_confirm_language_and_explain_shared_ones(self):
        sigs, short = signals("Zażółć gęślą jaźń, ul. Długa 5")
        self.assertEqual(short[0]["iso2"], "PL")
        pl = [s for s in sigs if s.get("language") == "pl"]
        self.assertTrue(pl and pl[0]["lr"]["PL"] == 10.0)
        self.assertFalse(any(s.get("language") == "lt" for s in sigs))

    def test_phone_domain_currency_words(self):
        self.assertEqual(self.top("+351 21 342 0000"), "PT")
        self.assertEqual(self.top("www.example.co.uk"), "GB")
        self.assertEqual(self.top("Fiyat 25 ₺"), "TR")
        self.assertEqual(self.top("Borracharia do Zé"), "BR")
        self.assertEqual(self.top("Talho Central"), "PT")

    def test_municipal_words(self):
        sigs, short = signals("Ayuntamiento de Sevilla")
        words = [s for s in sigs if s["kind"] == "word"]
        self.assertEqual(words[0]["lr"]["ES"], 4.0)
        self.assertIn("ES", {r["iso2"] for r in short[:3]})
        self.assertEqual(self.top("Prefeitura Municipal de Curitiba"), "BR")
        self.assertEqual(self.top("Concello de Vigo"), "ES")
        self.assertEqual(self.top("Ankara Büyükşehir Belediyesi"), "TR")

    def test_phone_digits_are_not_postal_codes(self):
        sigs, _ = signals("+351 21 342 0000")
        self.assertFalse([s for s in sigs if s["kind"] == "postal"])

    def test_watermarks_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ocr.json"
            p.write_text(json.dumps({"items": [{"text": "© 2026 Google", "conf": 1.0}, {"text": "Rua Augusta", "conf": 1.0}]}, ensure_ascii=False), encoding="utf-8")
            lines, backend = textgeo.load_lines(Namespace(ocr=str(p), text=None, file=None, min_conf=0.4))
            self.assertEqual([ln["text"] for ln in lines], ["Rua Augusta"])
            self.assertIsNone(backend)

    def run_main(self, d: Path, *args: str) -> tuple[dict, str]:
        """textgeo.py main offline (no lingua, brands or places) → (JSON result, Markdown)."""
        import contextlib
        import io
        from unittest.mock import patch
        out, md = d / "tg.json", d / "tg.md"
        argv = ["textgeo.py", *args, "--no-lingua", "--no-brands", "--no-places", "--out", str(out), "--md", str(md)]
        with patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            textgeo.main()
        return json.loads(out.read_text(encoding="utf-8")), md.read_text(encoding="utf-8")

    @staticmethod
    def write_ocr(d: Path, backend: str, *texts: str) -> str:
        p = d / f"ocr_{backend}.json"
        p.write_text(json.dumps({"backend": backend, "items": [{"text": t, "conf": 0.9} for t in texts]}, ensure_ascii=False),
                     encoding="utf-8")
        return str(p)

    def test_rapidocr_script_signals_are_observed_and_warned(self):
        sign = "台北市忠孝東路四段"
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for backend, rapid in (("rapidocr", True), ("apple-vision", False)):
                res, md = self.run_main(d, "--ocr", self.write_ocr(d, backend, sign))
                self.assertEqual(res["ocr_backend"], backend)
                self.assertEqual("OCR backend RapidOCR reads only Chinese characters" in md, rapid, backend)
                han = [s for s in res["signals"] if s["kind"] == "script"]
                self.assertTrue(han, backend)
                for s in han:
                    self.assertEqual(s["status"], "observed" if rapid else "read", s)
                    self.assertEqual(s["clue"].endswith("(RapidOCR, unconfirmed)"), rapid, s)
            res, md = self.run_main(d, "--text", sign)                                      # typed by the agent: read, no warning
            self.assertNotIn("ocr_backend", res)
            self.assertNotIn("RapidOCR", md)
            self.assertTrue(all(s["status"] == "read" for s in res["signals"] if s["kind"] == "script"))
            res, _ = self.run_main(d, "--ocr", self.write_ocr(d, "rapidocr", sign), "--text", sign)
            self.assertTrue(all(s["status"] == "read" for s in res["signals"] if s["kind"] == "script"))   # the agent's own reading
            res, _ = self.run_main(d, "--ocr", self.write_ocr(d, "rapidocr", sign), "--text", "台北")
            trad = [s for s in res["signals"] if s["clue"].startswith("Traditional")]
            self.assertEqual(trad[0]["status"], "observed")              # typed Han without the traditional form 東 confirms Han only

    def test_typed_text_is_scored_apart_from_rapidocr(self):
        def script(res):
            return sorted((s["clue"].split(" (")[0], s["status"]) for s in res["signals"] if s["kind"] == "script")
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ocr = self.write_ocr(d, "rapidocr", "东城银行大药房")
            res, _ = self.run_main(d, "--ocr", ocr, "--text", "银行")           # agrees with the OCR on fewer characters
            self.assertEqual(script(res), [("Simplified Chinese characters", "read")])
            res, _ = self.run_main(d, "--ocr", ocr, "--text", "東城銀行")       # corrects the OCR: the typed reading stands, the OCR's stays a lead
            self.assertEqual(script(res), [("Simplified Chinese characters", "observed"), ("Traditional Chinese characters", "read")])

    def test_rapidocr_empty_result_names_the_blind_spot(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for backend, rapid in (("rapidocr", True), ("apple-vision", False)):
                res, md = self.run_main(d, "--ocr", self.write_ocr(d, backend))
                self.assertEqual((res["n_lines"], res["ocr_backend"]), (0, backend))
                self.assertEqual(textgeo.RAPIDOCR_EMPTY in md, rapid, backend)

    @unittest.skipUnless(HAVE_BRANDS, "brand index not cached")
    def test_brand(self):
        self.assertEqual(self.top("Żabka", brands=True), "PL")
        _, short = signals("Biedronka", brands=True)
        self.assertEqual({r["iso2"] for r in short[:2]}, {"PL", "SK"})  # operates in both: a tie is the right answer

    @unittest.skipUnless((CACHE / "geonames" / "admin1CodesASCII.txt").exists(), "admin1 names not cached")
    def test_region_names_tolerate_admin_words(self):
        names = lambda cc, q: [geodata.admin1_name(cc, c) for c in geodata.admin1_codes(cc, q)]  # noqa: E731
        self.assertEqual(names("PL", "Pomeranian Voivodeship"), ["Pomerania"])
        self.assertEqual(names("RU", "Moscow Oblast"), ["Moscow Oblast"])
        self.assertIn("Munster", geodata.admin1_names("IE"))

    @unittest.skipUnless(HAVE_PLACES, "GeoNames not cached")
    def test_places_primary_names_first(self):
        rows = geodata.search("Augusta")
        self.assertEqual(rows[0]["match"], "name")
        self.assertEqual(geodata.reverse(38.57, -7.91)[0]["country"], "PT")


class MetaTests(unittest.TestCase):
    def test_offset_countries_are_dst_aware(self):
        from datetime import datetime
        summer = meta.countries_for_offset(60, datetime(2024, 7, 12, 10))
        winter = meta.countries_for_offset(60, datetime(2024, 1, 12, 10))
        self.assertIn("PT", summer)   # WEST in summer
        self.assertIn("GB", summer)   # BST
        self.assertNotIn("PT", winter)
        self.assertIn("FR", winter)   # CET in winter
        self.assertNotIn("FR", summer)

    def test_generator_software_and_jumbf_flagged_without_exiftool(self):
        with tempfile.TemporaryDirectory() as d:
            gen = Path(d) / "gen.jpg"
            ex = Image.Exif()
            ex[0x0131] = "Midjourney"                                   # Software
            Image.new("RGB", (64, 48), (120, 120, 120)).save(gen, exif=ex)
            prov = meta.digest(gen, meta.pillow_fallback(gen))["provenance"]
            self.assertIn("generative model (Midjourney)", prov["WARNING"])
            plain = Path(d) / "plain.jpg"
            Image.new("RGB", (64, 48), (120, 120, 120)).save(plain)
            self.assertNotIn("WARNING", meta.digest(plain, meta.pillow_fallback(plain))["provenance"])
            self.assertNotIn("error", meta.pillow_fallback(gen))       # no GPS block is not a read error
            self.assertIsNone(meta.AI_GENERATOR.search("Randall E"))        # 'dall e' needs its own word start
            # APP11 JUMBF segment (ISO 19566-5: 'JP' signature, box instance, packet sequence, then a 'jumb' superbox labelled c2pa) after SOI
            jumd = b"\x00" * 16 + b"\x03" + b"c2pa\x00"
            jumd = (8 + len(jumd)).to_bytes(4, "big") + b"jumd" + jumd
            jumb = (8 + len(jumd)).to_bytes(4, "big") + b"jumb" + jumd
            payload = b"JP" + b"\x00\x01" + b"\x00\x00\x00\x00" + jumb
            seg = b"\xff\xeb" + (len(payload) + 2).to_bytes(2, "big") + payload
            data = plain.read_bytes()
            c2pa = Path(d) / "c2pa.jpg"
            c2pa.write_bytes(data[:2] + seg + data[2:])
            raw = meta.pillow_fallback(c2pa)
            self.assertIn("C2PA/JUMBF manifest present (1 APP11 segment(s), label c2pa", raw["JUMBF:Manifest"])
            prov = meta.digest(c2pa, raw)["provenance"]
            self.assertIn("JUMBF:Manifest", prov)
            self.assertNotIn("WARNING", prov)                             # a manifest is provenance, not an AI verdict
            self.assertIn("C2PA present, source type unread", prov["C2PA"])
            self.assertEqual(prov["generated"], {"declared": False, "term": None, "composite": False, "source": None})
            self.assertEqual(meta._jumbf(data), {})

    IPTC = "http://cv.iptc.org/newscodes/digitalsourcetype/"

    @classmethod
    def xmp(cls, body: str) -> str:
        return ('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
                '<rdf:Description xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/">' + body
                + "</rdf:Description></rdf:RDF></x:xmpmeta>")

    @staticmethod
    def with_segments(src: Path, dst: Path, segments: bytes) -> Path:
        data = src.read_bytes()
        dst.write_bytes(data[:2] + segments + data[2:])
        return dst

    @staticmethod
    def app11(store: bytes, split: int | None = None) -> bytes:
        """One JUMBF superbox in APP11 segments; with split, a second segment repeats the 8-byte box header and continues the box."""
        box = (8 + len(store)).to_bytes(4, "big") + b"jumb" + store
        parts = [box] if split is None else [box[:split], box[:8] + box[split:]]
        out = b""
        for z, part in enumerate(parts, 1):
            payload = b"JP" + b"\x00\x01" + z.to_bytes(4, "big") + part
            out += b"\xff\xeb" + (len(payload) + 2).to_bytes(2, "big") + payload
        return out

    @staticmethod
    def c2pa_store(data: dict, *, jsonld: bool = False) -> bytes:
        """jumd 'c2pa' description box, then a real CBOR or JSON assertion content box."""
        jumd = b"\x00" * 16 + b"\x03" + b"c2pa\x00"
        payload = json.dumps(data).encode() if jsonld else cbor2.dumps(data, canonical=True)
        content = (8 + len(payload)).to_bytes(4, "big") + (b"json" if jsonld else b"cbor") + payload
        return (8 + len(jumd)).to_bytes(4, "big") + b"jumd" + jumd + content

    @classmethod
    def c2pa_source(cls, term: str) -> dict:
        return {"digitalSourceType": cls.IPTC + term, "softwareAgent": "test camera"}

    def test_source_type_in_xmp_png_and_exiftool_lists(self):
        with tempfile.TemporaryDirectory() as d:
            plain = Path(d) / "plain.jpg"
            Image.new("RGB", (64, 48), (120, 120, 120)).save(plain)
            for body, term in ((f"<Iptc4xmpExt:DigitalSourceType>{self.IPTC}trainedAlgorithmicMedia</Iptc4xmpExt:DigitalSourceType>",
                                "trainedAlgorithmicMedia"),
                               (f'<Iptc4xmpExt:DigitalSourceType rdf:resource="{self.IPTC}algorithmicMedia"/>', "algorithmicMedia")):
                app1 = b"http://ns.adobe.com/xap/1.0/\x00" + self.xmp(body).encode()
                f = self.with_segments(plain, Path(d) / f"{term}.jpg", b"\xff\xe1" + (len(app1) + 2).to_bytes(2, "big") + app1)
                dg = meta.digest(f, meta.pillow_fallback(f))
                self.assertEqual(dg["provenance"]["generated"], {"declared": True, "term": term, "composite": False, "source": "XMP"})
                self.assertIn(f"File declares generated content ({term})", dg["provenance"]["WARNING"])
                self.assertIn("File declares generated content", meta.to_md(dg, []))
            from PIL.PngImagePlugin import PngInfo
            info = PngInfo()                                          # compressed iTXt: invisible to a byte scan, read through Pillow
            info.add_itxt("XML:com.adobe.xmp", self.xmp(f'<Iptc4xmpExt:DigitalSourceType rdf:resource="{self.IPTC}trainedAlgorithmicMedia"/>'),
                          zip=True)
            png = Path(d) / "gen.png"
            Image.new("RGB", (64, 48), (90, 90, 90)).save(png, pnginfo=info)
            self.assertNotIn(b"digitalsourcetype", png.read_bytes())
            gen = meta.digest(png, meta.pillow_fallback(png))["provenance"]["generated"]
            self.assertEqual(gen, {"declared": True, "term": "trainedAlgorithmicMedia", "composite": False, "source": "PNG"})
            # exiftool reports one value per C2PA action as a list: a capture plus an AI composite is an AI-edited real photo
            raw = {"ExifTool:ExifToolVersion": 13.1, "JUMBF:ActionsAction": ["c2pa.opened", "c2pa.edited"],
                   "JUMBF:ActionsDigitalSourceType": [self.IPTC + "digitalCapture", self.IPTC + "compositeWithTrainedAlgorithmicMedia"]}
            prov = meta.digest(plain, raw)["provenance"]
            self.assertEqual(prov["generated"], {"declared": False, "term": "compositeWithTrainedAlgorithmicMedia", "composite": True,
                                                 "source": "exiftool"})
            self.assertIn("AI-edited real photo (compositeWithTrainedAlgorithmicMedia): edited regions are not evidence", prov["WARNING"])
            self.assertNotIn("declares generated", prov["WARNING"])
            self.assertIn("compositeWithTrainedAlgorithmicMedia", prov["JUMBF:ActionsDigitalSourceType"])
            # compositeCapture merges real captures (HDR, panorama): neither generated nor AI-edited
            hdr = meta.digest(plain, {"XMP-Iptc4xmpExt:DigitalSourceType": self.IPTC + "compositeCapture"})["provenance"]
            self.assertEqual((hdr["generated"]["declared"], hdr["generated"]["composite"]), (False, False))
            self.assertNotIn("WARNING", hdr)

    def test_c2pa_source_type_from_app11_segments_and_png_chunks(self):
        with tempfile.TemporaryDirectory() as d:
            plain = Path(d) / "plain.jpg"
            Image.new("RGB", (64, 48), (120, 120, 120)).save(plain)

            store, src = self.c2pa_store, self.c2pa_source
            created = store({"actions": [{"action": "c2pa.created", **src("trainedAlgorithmicMedia")}]})
            box = (8 + len(created)).to_bytes(4, "big") + b"jumb" + created
            cut = box.index(b"digitalsourcetype/") + 9                   # the URI straddles the segment boundary
            f = self.with_segments(plain, Path(d) / "split.jpg", self.app11(created, split=cut))
            self.assertNotIn(b"digitalsourcetype/", f.read_bytes().lower())   # no plain-byte match: only the rejoined store reads it
            raw = meta.pillow_fallback(f)
            self.assertEqual(raw["JUMBF:DigitalSourceType"], "trainedAlgorithmicMedia")
            self.assertIn("2 APP11 segment(s), label c2pa", raw["JUMBF:Manifest"])
            dg = meta.digest(f, raw)
            self.assertEqual(dg["provenance"]["generated"], {"declared": True, "term": "trainedAlgorithmicMedia", "composite": False,
                                                             "source": "JUMBF"})
            self.assertNotIn("C2PA", dg["provenance"])
            # an AI composite on an opened ingredient: the composite term wins, generation is not declared
            edited = store({"actions": [{"action": "c2pa.opened", **src("trainedAlgorithmicMedia")},
                                        {"action": "c2pa.edited", **src("compositeWithTrainedAlgorithmicMedia")}]})
            f = self.with_segments(plain, Path(d) / "edited.jpg", self.app11(edited))
            prov = meta.digest(f, meta.pillow_fallback(f))["provenance"]
            self.assertEqual(prov["generated"], {"declared": False, "term": "compositeWithTrainedAlgorithmicMedia", "composite": True,
                                                 "source": "JUMBF"})
            self.assertIn("AI-edited real photo", prov["WARNING"])
            # generation inside a file made from an opened ingredient: not a declaration, and not called real either
            opened = store({"actions": [{"action": "c2pa.opened", **src("trainedAlgorithmicMedia")}]})
            f = self.with_segments(plain, Path(d) / "opened.jpg", self.app11(opened))
            prov = meta.digest(f, meta.pillow_fallback(f))["provenance"]
            self.assertEqual((prov["generated"]["declared"], prov["generated"]["composite"], prov["generated"]["term"]),
                             (False, False, "trainedAlgorithmicMedia"))
            self.assertIn("possible generated image, unconfirmed", prov["WARNING"])
            self.assertNotIn("real photo", prov["WARNING"])
            # PNG keeps the store whole in a caBX chunk
            import zlib
            png = Path(d) / "chat.png"
            Image.new("RGB", (64, 48), (90, 90, 90)).save(png)
            chunk = len(box).to_bytes(4, "big") + b"caBX" + box + zlib.crc32(b"caBX" + box).to_bytes(4, "big")
            data = png.read_bytes()
            png.write_bytes(data[:-12] + chunk + data[-12:])           # before IEND
            gen = meta.digest(png, meta.pillow_fallback(png))["provenance"]["generated"]
            self.assertEqual(gen, {"declared": True, "term": "trainedAlgorithmicMedia", "composite": False, "source": "JUMBF"})

    def test_source_type_only_from_the_property_never_from_a_mention(self):
        uri = "https://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
        note = f"Documentation {uri}"
        described = self.xmp('<dc:description xmlns:dc="http://purl.org/dc/elements/1.1/"><rdf:Alt>'
                             f'<rdf:li xml:lang="x-default">{note}</rdf:li></rdf:Alt></dc:description>')
        unread = {"declared": False, "term": None, "composite": False, "source": None}
        declared = {"declared": True, "term": "trainedAlgorithmicMedia", "composite": False}
        from PIL.PngImagePlugin import PngInfo
        with tempfile.TemporaryDirectory() as d:
            plain = Path(d) / "plain.jpg"
            Image.new("RGB", (64, 48), (120, 120, 120)).save(plain)

            def generated(f: Path) -> dict:
                return meta.digest(f, meta.pillow_fallback(f))["provenance"]["generated"]

            def jpeg(name: str, packet: str) -> Path:
                app1 = b"http://ns.adobe.com/xap/1.0/\x00" + packet.encode()
                return self.with_segments(plain, Path(d) / name, b"\xff\xe1" + (len(app1) + 2).to_bytes(2, "big") + app1)

            def png(name: str, key: str, value: str) -> Path:
                info = PngInfo()
                if key == "XML:com.adobe.xmp":                       # compressed iTXt: only the PNG text path reads it
                    info.add_itxt(key, value, zip=True)
                else:
                    info.add_text(key, value)
                f = Path(d) / name
                Image.new("RGB", (64, 48), (90, 90, 90)).save(f, pnginfo=info)
                return f

            # the vocabulary URI quoted in a comment, a description or a foreign namespace is ordinary text
            comment = png("comment.png", "Comment", note)
            self.assertNotIn("PNG:DigitalSourceType", meta.pillow_fallback(comment))
            self.assertEqual(meta.source_type(meta.pillow_fallback(comment)), (unread, None))
            for f in (comment, jpeg("described.jpg", described), png("described.png", "XML:com.adobe.xmp", described),
                      jpeg("foreign.jpg", self.xmp(f'<o:DigitalSourceType xmlns:o="http://example.com/other/">{uri}</o:DigitalSourceType>'))):
                self.assertEqual(generated(f), unread, f.name)
            noted = self.c2pa_store({"actions": [{"action": "c2pa.created", "description": note}]})
            f = self.with_segments(plain, Path(d) / "noted.jpg", self.app11(noted))
            raw = meta.pillow_fallback(f)
            self.assertNotIn("JUMBF:DigitalSourceType", raw)
            self.assertIn("C2PA present, source type unread", meta.digest(f, raw)["provenance"]["C2PA"])
            # the property itself: any prefix bound to the IPTC Extension namespace, attribute form, a bare term, C2PA JSON-LD
            ext = ('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
                   f'<rdf:Description xmlns:ext="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" ext:DigitalSourceType="{uri}"/>'
                   "</rdf:RDF></x:xmpmeta>")
            bare = self.xmp("<Iptc4xmpExt:DigitalSourceType>trainedAlgorithmicMedia</Iptc4xmpExt:DigitalSourceType>")
            for f in (jpeg("ext.jpg", ext), jpeg("bare.jpg", bare)):
                self.assertEqual(generated(f), {**declared, "source": "XMP"}, f.name)
            self.assertEqual(generated(png("ext.png", "XML:com.adobe.xmp", ext)), {**declared, "source": "PNG"})
            jsonld = self.c2pa_store({"Iptc4xmpExt:DigitalSourceType": uri}, jsonld=True)
            f = self.with_segments(plain, Path(d) / "jsonld.jpg", self.app11(jsonld))
            self.assertEqual(generated(f), {**declared, "source": "JUMBF"})

    def test_c2pa_descriptions_never_supply_source_types_or_actions(self):
        uri = self.IPTC + "trainedAlgorithmicMedia"
        with tempfile.TemporaryDirectory() as d:
            plain = Path(d) / "plain.jpg"
            Image.new("RGB", (64, 48), (120, 120, 120)).save(plain)
            example = 'Documentation example: {"digitalSourceType":"' + uri + '"}'
            for jsonld in (False, True):
                store = self.c2pa_store({"actions": [{"action": "c2pa.created", "description": example}]}, jsonld=jsonld)
                f = self.with_segments(plain, Path(d) / f"description-{jsonld}.jpg", self.app11(store))
                raw = meta.pillow_fallback(f)
                self.assertNotIn("JUMBF:DigitalSourceType", raw)
                self.assertFalse(meta.source_type(raw)[0]["declared"])
                store = self.c2pa_store({"actions": [{"action": "c2pa.created", "digitalSourceType": uri,
                                                       "description": "Documentation mentions c2pa.opened."}]}, jsonld=jsonld)
                f = self.with_segments(plain, Path(d) / f"created-{jsonld}.jpg", self.app11(store))
                raw = meta.pillow_fallback(f)
                self.assertNotIn("JUMBF:Actions", raw)
                self.assertTrue(meta.source_type(raw)[0]["declared"])
            # ExifTool -G1 reports CBOR/JSON action fields, not a free-text mention of an action.
            raw = {"ExifTool:ExifToolVersion": 13.1, "CBOR:ActionsDigitalSourceType": uri,
                   "CBOR:ActionsAction": ["c2pa.created"], "CBOR:ActionsDescription": "c2pa.opened"}
            self.assertTrue(meta.source_type(raw)[0]["declared"])
            raw["CBOR:ActionsAction"] = ["c2pa.opened", "c2pa.edited"]
            self.assertFalse(meta.source_type(raw)[0]["declared"])

    def test_c2pa_jsonld_context_is_not_a_source_value(self):
        uri = self.IPTC + "trainedAlgorithmicMedia"
        context = {"DigitalSourceType": "http://iptc.org/std/Iptc4xmpExt/2008-02-29/DigitalSourceType"}
        with tempfile.TemporaryDirectory() as d:
            plain = Path(d) / "plain.jpg"
            Image.new("RGB", (64, 48), (120, 120, 120)).save(plain)
            for name, data, declared in (
                    ("property", {"@context": context, "DigitalSourceType": uri}, True),
                    ("description", {"@context": context, "description": uri}, False),
                    ("context-only", {"@context": {"DigitalSourceType": uri}}, False)):
                store = self.c2pa_store(data, jsonld=True)
                f = self.with_segments(plain, Path(d) / f"{name}.jpg", self.app11(store))
                raw = meta.pillow_fallback(f)
                gen = meta.source_type(raw)[0]
                self.assertEqual(gen["declared"], declared, name)
                self.assertEqual(gen["term"], "trainedAlgorithmicMedia" if declared else None, name)
                self.assertEqual(raw.get("JUMBF:DigitalSourceType"), "trainedAlgorithmicMedia" if declared else None, name)

    def test_c2pa_nested_content_and_unreadable_assertions(self):
        store = self.c2pa_store({"actions": [{"action": "c2pa.created", **self.c2pa_source("algorithmicMedia")}]})
        nested = (8 + len(store)).to_bytes(4, "big") + b"jumb" + store
        with tempfile.TemporaryDirectory() as d:
            plain = Path(d) / "plain.jpg"
            Image.new("RGB", (64, 48), (120, 120, 120)).save(plain)
            f = self.with_segments(plain, Path(d) / "nested.jpg", self.app11(nested))
            self.assertTrue(meta.source_type(meta.pillow_fallback(f))[0]["declared"])
            for name, data in (("truncated", store[:-5]), ("compressed", store.replace(b"cbor", b"brob", 1)),
                               ("remote", self.c2pa_store({"url": "https://example.org/manifest"}))):
                f = self.with_segments(plain, Path(d) / f"{name}.jpg", self.app11(data))
                raw = meta.pillow_fallback(f)
                self.assertIn("JUMBF:Manifest", raw)
                self.assertNotIn("JUMBF:DigitalSourceType", raw)
                self.assertIn("C2PA present, source type unread", meta.digest(f, raw)["provenance"]["C2PA"])

    def test_video_time_prefers_creation_date_and_hedges_container_time(self):
        with tempfile.TemporaryDirectory() as d:
            v = Path(d) / "clip.mov"
            v.write_bytes(b"\x00\x00\x00\x14ftypqt  " + b"\x00" * 64)
            t = meta.digest(v, {"QuickTime:CreateDate": "2024:07:12 09:15:30", "Keys:CreationDate": "2024:07:12 10:15:30+01:00"})["time"]
            self.assertEqual((t["utc_offset"], t["utc_offset_source"]), ("+01:00", "offset inside the date string"))
            self.assertNotIn("clock", t)
            only = meta.digest(v, {"QuickTime:CreateDate": "2024:07:12 09:15:30"})
            self.assertEqual(only["time"]["clock"], meta.CONTAINER_CLOCK)
            self.assertNotIn("utc_offset", only["time"])
            self.assertIn("CreateDate is container time, zone unknown", meta.to_md(only, []))
            same = meta.digest(v, {"QuickTime:CreateDate": "2024:07:12 09:15:30", "GPS:GPSDateTime": "2024:07:12 09:15:30Z"})["time"]
            self.assertNotIn("utc_offset", same)                       # equal to GPS UTC: a UTC container or a UTC+0 clock, undecidable
            self.assertEqual(same["clock"], meta.CONTAINER_CLOCK)
            local = meta.digest(v, {"QuickTime:CreateDate": "2024:07:12 10:15:30", "GPS:GPSDateTime": "2024:07:12 09:15:30Z"})["time"]
            self.assertEqual(local["utc_offset"], "+01:00")            # one hour off GPS UTC: the camera clock ran on local time
            self.assertNotIn("clock", local)
            photo = Path(d) / "p.jpg"
            photo.write_bytes(b"\xff\xd8\xff\xd9")
            self.assertNotIn("clock", meta.digest(photo, {"ExifIFD:CreateDate": "2024:07:12 10:15:30"})["time"])

    @unittest.skipUnless(shutil.which("exiftool"), "exiftool missing")
    def test_offset_from_gps_time_and_thumbnail_crop(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "PXL_20240712_101530123.jpg"
            Image.new("RGB", (400, 300), (90, 140, 90)).save(f)
            Image.new("RGB", (160, 90)).save(Path(d) / "t.jpg")
            subprocess.run(["exiftool", "-q", "-overwrite_original", "-DateTimeOriginal=2024:07:12 10:15:30",
                            "-GPSDateStamp=2024:07:12", "-GPSTimeStamp=09:15:30", "-GPSLatitude=38.71", "-GPSLatitudeRef=N",
                            "-GPSLongitude=9.13", "-GPSLongitudeRef=W", f"-ThumbnailImage<={Path(d) / 't.jpg'}", str(f)], check=True)
            raw = meta.exiftool(f)
            dg = meta.digest(f, raw)
            self.assertAlmostEqual(dg["gps"]["lon"], -9.13, places=2)
            self.assertEqual(dg["time"]["utc_offset"], "+01:00")
            self.assertIn("PT", dg["time"]["countries_with_this_offset_on_that_date"])
            prev = meta.extract_previews(f, Path(d), dg["image"]["size"])
            self.assertTrue(any("cropped" in p.get("note", "") for p in prev))


class BoardTests(unittest.TestCase):
    def run_board(self, d: Path, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / "board.py"), *args], cwd=d, capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_ingest_caps_model_and_model_cannot_exclude(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.run_board(d, "init", "--photo", "x.jpg")
            sig = {"tool": "prior.py", "signals": [{"kind": "model", "status": "model", "level": "country", "clue": "model says PT",
                                                    "p": {"PT": 0.9, "ES": 0.05}, "n_classes": 200}]}
            (d / "prior.json").write_text(json.dumps(sig, ensure_ascii=False), encoding="utf-8")
            r = self.run_board(d, "ingest", "prior.json")
            self.assertEqual(r.returncode, 0, r.stderr)
            b = json.loads((d / "board.json").read_text(encoding="utf-8"))
            pt = [e for e in b["evidence"] if e["candidate"] == "Portugal"]
            self.assertEqual(pt[0]["lr"], 3.0)          # 0.9 × 200 capped at 3
            self.assertEqual(b["candidates"]["Portugal"]["iso2"], "PT")
            again = self.run_board(d, "ingest", "prior.json")
            self.assertIn("Ingested 0 signals", again.stdout)
            r = self.run_board(d, "exclude", "Spain", "--clue", "K1", "--computed", "prior.json")
            self.assertNotEqual(r.returncode, 0)
            r = self.run_board(d, "check")
            self.assertIn("no read/computed evidence", r.stdout)


    def test_retract_report_json_and_status_cap(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.run_board(d, "init", "--photo", "x.jpg")
            r = self.run_board(d, "apply", "--kind", "driving-side", "--value", "left", "--status", "observed")
            self.assertEqual(r.returncode, 0, r.stderr)
            b = json.loads((d / "board.json").read_text(encoding="utf-8"))
            self.assertEqual(b["clues"]["K1"]["status"], "observed")
            self.assertTrue(all(e["lr"] <= 5.0 for e in b["evidence"]))
            r = self.run_board(d, "retract", "K1", "--why", "it was a mirrored image")
            self.assertEqual(r.returncode, 0, r.stderr)
            b = json.loads((d / "board.json").read_text(encoding="utf-8"))
            self.assertTrue(all(e["lr"] == 1.0 for e in b["evidence"] if e["clue"] == "K1"))
            r = self.run_board(d, "report")
            json.loads(r.stdout)  # stdout must be valid JSON (reminders go to stderr)

    def test_streetview_coverage_prior(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.run_board(d, "init", "--photo", "x.jpg")
            r = self.run_board(d, "apply", "--kind", "coverage", "--value", "streetview")
            self.assertEqual(r.returncode, 0, r.stderr)
            b = json.loads((d / "board.json").read_text(encoding="utf-8"))
            iso = {v.get("iso2") for v in b["candidates"].values()}
            self.assertIn("KE", iso)          # official coverage
            self.assertNotIn("MA", iso)       # Morocco: no official road coverage
            self.assertTrue(all(v.get("iso2") for v in b["candidates"].values()))

    @unittest.skipUnless(HAVE_PLACES and shutil.which("uv"), "GeoNames or uv missing")
    def test_children_of_a_country_are_offline_regions(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.run_board(d, "init", "--photo", "x.jpg")
            r = self.run_board(d, "children", "Ghana")
            self.assertEqual(r.returncode, 0, r.stderr)
            b = json.loads((d / "board.json").read_text(encoding="utf-8"))
            regions = {k: v for k, v in b["candidates"].items() if v["level"] == "admin1"}
            self.assertIn("Greater Accra", regions)
            self.assertTrue(regions["Greater Accra"]["center"])


class StreetViewProjectionTests(unittest.TestCase):
    def test_heading_maps_to_the_right_part_of_the_panorama(self):
        W, H = 720, 360
        eq = np.zeros((H, W, 3), dtype=np.uint8)
        pano_heading = 40.0
        # paint a red column at compass bearing 130° = pano_heading + 90° → x = W * (90/360 + 0.5)
        x = int(W * (90 / 360 + 0.5))
        eq[:, x - 3:x + 4] = (255, 0, 0)
        im = np.asarray(SL.perspective(eq, pano_heading, 130.0, 0, 60, 101, 61))
        self.assertGreater(im[30, 50, 0], 200)
        self.assertLess(np.asarray(SL.perspective(eq, pano_heading, 40.0, 0, 60, 101, 61))[30, 50, 0], 50)

    def test_tile_math(self):
        self.assertEqual(SL.tile_xy(40.7580, -73.9855), (38598, 49258))


class BenchTests(unittest.TestCase):
    def test_metrics(self):
        import importlib
        bench = importlib.import_module("bench")
        m = bench.metrics([{"error_km": 0.5, "country_true": "PT", "country_pred": "PT"},
                           {"error_km": 300, "country_true": "PT", "country_pred": "ES"}])
        self.assertEqual(m["within"]["1km"], 0.5)
        self.assertEqual(m["within"]["750km"], 1.0)
        self.assertEqual(m["country_accuracy"], 0.5)
        self.assertEqual(bench.score_km(0), 5000)


class GeometrySanityTests(unittest.TestCase):
    def test_horizon_sanity_agrees_with_projection(self):
        import pose
        import numpy as np
        import math
        for pitch, roll in [(20, 0), (-20, 0), (20, 25), (-20, -25), (0, 25)]:
            with self.subTest(pitch=pitch, roll=roll):
                p, r = map(math.radians, (pitch, roll))
                forward = np.array([0, math.cos(p), math.sin(p)])
                right = np.array([math.cos(r), -math.sin(p)*math.sin(r), math.cos(p)*math.sin(r)])
                direction = np.cross([0., 0., 1.], right)
                if direction @ forward < 0:
                    direction = -direction
                params = [0, 0, 1.7, 0, pitch, roll, 800]
                point = direction * 100000 + np.array([0., 0., 1.7])
                xy, _ = pose.project(np.array(params), np.array([point]), 1000, 600)
                self.assertAlmostEqual(xy[0, 0], 500)
                sample = {"_frame": {"image_size": [1000, 600], "lat0": 0, "lon0": 0}, "_params": params}
                notes = "\n".join(pose.sanity(sample, [], horizon_row=float(xy[0, 1])))
                self.assertIn(f"row {xy[0, 1]:.0f}", notes.splitlines()[0])
                self.assertNotIn("contradicts", notes)
                wrong = "\n".join(pose.sanity(sample, [], horizon_row=float(xy[0, 1])+100))
                self.assertIn("contradicts", wrong)

    def test_vertical_horizon_does_not_check_a_centre_row(self):
        import pose
        sample = {"_frame": {"image_size": [1000, 600], "lat0": 0, "lon0": 0},
                  "_params": [0, 0, 1.7, 0, 20, 90, 800]}
        notes = "\n".join(pose.sanity(sample, [], horizon_row=300))
        self.assertIn("cannot", notes)
        self.assertNotIn("contradicts", notes)


class TileAvailabilityTests(unittest.TestCase):
    def test_esri_missing_tiles_are_requested_as_http_failures(self):
        import tiles
        for source in ("esri", "esri-street"):
            self.assertIn("blankTile=false", tiles.tile_url(source, 1, 2, 3))
            self.assertNotEqual(tiles.tile_path(Path("cache"), source, 3, 1, 2), Path("cache") / f"{source}_3_1_2.jpg")
        self.assertNotIn("blankTile", tiles.tile_url("google", 1, 2, 3))
        self.assertEqual(tiles.tile_path(Path("cache"), "google", 3, 1, 2), Path("cache/google_3_1_2.jpg"))

    def test_no_tiles_does_not_publish_a_verification_image(self):
        import tiles
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp, patch.object(tiles, "_get", return_value=False):
            root = Path(tmp)
            with self.assertRaisesRegex(SystemExit, "No.*tiles"):
                tiles.fetch((45, 10), 20, 0, root / "map.jpg", "esri", None, root / "cache")
            self.assertFalse((root / "map.jpg").exists())
            self.assertFalse((root / "map.json").exists())

    def test_uniform_valid_tile_and_partial_mosaic_still_work(self):
        import tiles
        from unittest.mock import patch
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def get_one(url, path, proxy):
                if url != wanted:
                    return False
                Image.new("RGB", (256, 256), "white").save(path)
                return True
            gx, gy = tiles.geo.ll2px(18, 45, 10)
            wanted = tiles.tile_url("esri", int(gx//256), int(gy//256), 18)
            with patch.object(tiles, "_get", side_effect=get_one):
                meta = tiles.fetch((45, 10), 18, 1, root / "map.jpg", "esri", None, root / "cache")
            self.assertEqual(meta["failed_tiles"], 8)
            self.assertTrue((root / "map.jpg").exists())


class NewToolTests(unittest.TestCase):
    """Offline checks for reveal, opendata, phone patterns, GIBS tiles, motion photos, match sheets, town sheets,
    house-number queries and the weather ranking (network calls are stubbed)."""

    def test_reveal_surfaces_dark_text(self):
        import imgprep
        from PIL import ImageDraw
        im = Image.new("RGB", (300, 120), (10, 10, 12))
        ImageDraw.Draw(im).text((20, 50), "PA 471 KT", fill=(34, 32, 30))
        panels = dict(imgprep.reveal(im, 2))
        self.assertEqual(set(panels), {"crop", "levels", "equalize", "gamma1.8", "gamma2.6", "shadows", "gray", "clahe"})
        std = lambda p: float(np.asarray(p.convert("L"), dtype=float).std())
        self.assertGreater(std(panels["levels"]), 3 * std(panels["crop"]))      # the stretch makes the faint text stand out
        g = np.asarray(im.convert("L"))
        self.assertEqual(imgprep._clahe(g).shape, g.shape)

    def test_opendata_points_from_any_geometry(self):
        import opendata
        self.assertEqual(opendata._rep_point({"type": "Point", "coordinates": [-73.9, 40.7]}), [40.7, -73.9])
        line = {"type": "MultiLineString", "coordinates": [[[0, 0], [1, 1], [2, 2]]]}
        self.assertEqual(opendata._rep_point(line), [1, 1])                    # a lane → its midpoint
        poly = {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2]]]}
        self.assertEqual(opendata._rep_point(poly), [1.0, 1.0])
        fc = {"features": [{"geometry": {"type": "Point", "coordinates": [1, 2]}, "properties": {"street": "MAIN"}},
                           {"geometry": {"type": "Point", "coordinates": [3, 4]}, "properties": {"street": "MAIN"}}]}
        self.assertEqual(opendata._points_from_geojson(fc, "street", 10), {"MAIN": [2, 1], "MAIN_": [4, 3]})
        rows = [{"Latitude": "40.1", "Longitude": "-73.2", "species": "pine"}]
        self.assertEqual(opendata._points_from_rows(rows, "species", 10), {"pine": [40.1, -73.2]})
        q = opendata._soql(Namespace(eq=["lane_color=Red", "boro=3"], range=["streetwidt:40:45"], where=None))
        self.assertEqual(q, "lane_color='Red' AND boro=3 AND streetwidt between 40 and 45")
        typed = opendata._soql(Namespace(eq=["segmentid=0029245", "tree_id=180683", "alive=TRUE"], range=None, where=None),
                               {"segmentid": "text", "tree_id": "number", "alive": "checkbox"})
        self.assertEqual(typed, "segmentid='0029245' AND tree_id=180683 AND alive=true")   # a digit string in a text column stays quoted

    def test_phone_pattern_enumerates_valid_candidates(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            textgeo.enumerate_phone("6941 2?7788", "GR")
        out = buf.getvalue()
        self.assertIn("10 valid number(s)", out)
        self.assertIn("+306941207788", out)
        self.assertIn('"6941297788"', out)

    def test_gibs_daily_tiles(self):
        import tiles
        u = tiles.tile_url("gibs:2024-07-16", 22, 19, 6)
        self.assertIn("/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-07-16/GoogleMapsCompatible_Level9/6/19/22.jpg", u)
        self.assertIn("/VIIRS_SNPP_CorrectedReflectance_TrueColor/", tiles.tile_url("gibs:2024-07-16:VIIRS_SNPP_CorrectedReflectance_TrueColor", 1, 1, 3))

    def test_wayback_capture_date_at_the_point(self):
        import tiles

        def layer(date, lo, hi, src="WV02", res="0.5"):
            return {"layerId": 0, "attributes": {"SRC_DATE": date, "SRC_DATE2": "1/2/1999", "SRC_RES": res, "SRC_DESC": src,
                                                 "MinMapLevel": str(lo), "MaxMapLevel": str(hi)}}
        fine, mid, coarse = layer("20250930", 19, 19, "GE01", "0.46"), layer("20170518", 14, 18), layer("Null", 0, 11, "TerraColor", "15")
        cap = tiles._capture([fine, mid, coarse], 17)
        self.assertEqual(cap, {"captured": "2017-05-18", "capture_source": "WV02", "capture_res_m": 0.5})      # the layer spanning z17
        self.assertEqual(tiles._capture([fine, mid, coarse], 19)["captured"], "2025-09-30")
        self.assertEqual(tiles._capture([mid, coarse], 19)["captured"], "2017-05-18")      # nothing spans z19: z18 imagery upsampled
        null = tiles._capture([fine, mid, coarse], 10)
        self.assertEqual((null["captured"], null["capture_source"], null["capture_res_m"]), (None, "TerraColor", 15.0))  # SRC_DATE2 ignored
        self.assertIsNone(tiles._capture([], 17)["captured"])
        self.assertIsNone(tiles._capture([layer("", 14, 18)], 17)["captured"])
        self.assertEqual(tiles._capture_text(cap, "2018-05-16"), "captured 2017-05-18 at the point (published 2018-05-16), WV02, 0.5 m")
        self.assertTrue(tiles._capture_text(null, "2014-02-20").startswith("capture unknown; published 2014-02-20 = upper bound"))
        calls = []
        real = tiles.fetch_bytes
        try:
            with tempfile.TemporaryDirectory() as d:
                tiles.fetch_bytes = lambda url, proxy=None, timeout=20: calls.append(url) or json.dumps({"results": [mid]}).encode()
                rel = {"id": 1, "date": "2018-05-16", "metadataLayerUrl": "https://example.org/Metadata_2018/MapServer"}
                self.assertEqual(tiles.capture_at(rel, 34.0331, -5.0003, 17, None, Path(d))["captured"], "2017-05-18")
                self.assertEqual(tiles.capture_at(rel, 34.0331, -5.0003, 17, None, Path(d))["captured"], "2017-05-18")   # cached
                tiles.fetch_bytes = lambda *a, **k: b'{"error": {"code": 400, "message": "Invalid geometry"}}'
                bad = tiles.capture_at(dict(rel, metadataLayerUrl="https://example.org/Other/MapServer"), 34.0331, -5.0003, 17, None, Path(d))
                self.assertIn("Invalid geometry", bad["capture_error"])                     # reported per version, never raised
                self.assertIn("capture_error", tiles.capture_at(dict(rel, metadataLayerUrl=""), 34.0331, -5.0003, 17, None, Path(d)))
        finally:
            tiles.fetch_bytes = real
        self.assertEqual(len(calls), 1)
        for part in ("/identify?", "layers=all", "tolerance=0", "sr=4326", "geometry=-5.0003%2C34.0331"):
            self.assertIn(part, calls[0])

    def test_motion_photo_video_is_extracted(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            still = td / "still.jpg"
            Image.new("RGB", (200, 150), (90, 90, 90)).save(still, "JPEG")
            mp = td / "motion.jpg"
            mp.write_bytes(still.read_bytes() + b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 3000)
            got = meta.extract_motion(mp, td)
            self.assertEqual(len(got), 1)
            self.assertTrue((td / got[0]["file"]).read_bytes()[4:8] == b"ftyp")
            self.assertEqual(meta.extract_motion(still, td), [])

    def test_match_sheet_renders(self):
        import evidence
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            Image.new("RGB", (400, 300), "gray").save(td / "a.jpg")
            Image.new("RGB", (500, 360), "gray").save(td / "b.jpg")
            spec = {"left": {"image": "a.jpg"}, "right": {"image": "b.jpg"}, "height": 300,
                    "pairs": [{"color": "#ff5bbf", "label": "window", "a": [100, 80], "b": [120, 100]}]}
            with self.assertRaises(ValueError) as cm:                 # no pairs = no match proof: refused, never a silent side-by-side
                evidence.build_match(dict(spec, pairs=[]), td, td / "none.jpg")
            self.assertIn("at least one pair", str(cm.exception))
            self.assertFalse((td / "none.jpg").exists())
            evidence.build_match(spec, td, td / "m.jpg")
            with Image.open(td / "m.jpg") as m:
                self.assertEqual(m.size[1], 300 + 34)
                self.assertGreater(m.size[0], 400 + 500 * 300 // 360)
            # the workflow's layout: spec saved in evidence/, image paths relative to the session folder (the cwd)
            import os
            (td / "evidence").mkdir()
            for n in ("a.jpg", "b.jpg"):
                (td / n).rename(td / "evidence" / n)
            spec2 = dict(spec, left={"image": "evidence/a.jpg"}, right={"image": "evidence/b.jpg"})
            old = os.getcwd()
            os.chdir(td)
            try:
                evidence.build_match(spec2, td / "evidence", td / "evidence" / "m2.jpg")
            finally:
                os.chdir(old)
            self.assertTrue((td / "evidence" / "m2.jpg").exists())

    def test_refsheet_towns_sample_inside_each_town(self):
        import refsheet
        cands = refsheet.candidates("45.764,4.836:Lyon;45.771,4.880:Villeurbanne", "towns", Namespace(points=None))
        self.assertEqual([c["label"] for c in cands], ["Lyon", "Villeurbanne"])
        pts = refsheet.sample_towns(cands[0], Namespace(n=3, spread=500, seed=1))
        self.assertEqual(len(pts), 12)
        for p in pts:
            self.assertLess(SL.dist_m((p["lat"], p["lon"]), tuple(cands[0]["center"])), 501)

    def test_house_number_pair_query(self):
        import osm
        seen = {}
        real = osm.run
        osm.run = lambda ql, proxy, cache, **kw: seen.setdefault("ql", ql) and {"elements": []}
        try:
            pts = osm.cmd_addr(Namespace(area=None, bbox=(38.70, -9.20, 38.76, -9.10), number="214,226", within=60,
                                         proxy=None, cache=Path(tempfile.gettempdir())))
        finally:
            osm.run = real
        self.assertEqual(pts, {})
        self.assertIn('nwr["addr:housenumber"="214"](38.7,-9.2,38.76,-9.1)->.a;', seen["ql"])
        self.assertIn('nwr["addr:housenumber"="226"](around.a:60)', seen["ql"])
        self.assertIn("nwr.a(around.x:60)", seen["ql"])

    def test_regional_plate_codes_with_eras(self):
        import clues
        if not (clues.DATA / "plate_codes.json").exists():
            self.skipTest("assets/data/plate_codes.json not built (clues.py update plate_codes)")
        # the place sits at its board level (admin2 / city, cantons and Turkish provinces admin1); admin1 holds the region
        place = lambda v, c=None: [m.get("admin2") or m.get("city") or m.get("admin1") for m in clues.lookup_plate_code(v, c)["matches"]]
        self.assertIn("Palermo", place("PA", "IT"))
        self.assertIn("Rome", place("ROMA", "Italy"))
        self.assertIn("Rabat", place("1", "MA"))
        self.assertIn("Corse-du-Sud", place("2A", "FR"))
        self.assertTrue(any("Constantine" in p for p in place("93", "FR")))       # French Algeria before 1957
        self.assertTrue(any("Patras" in p for p in place("AA", "GR")))            # Latin look-alikes → Greek letters
        self.assertTrue(any(m["note"].startswith("[GB] registered 1 Sep") for m in clues.lookup_plate_code("51", "GB")["matches"]))
        self.assertGreaterEqual(len({m["note"][1:3] for m in clues.lookup_plate_code("BA")["matches"]}), 4)   # no country: every match

    def test_weather_ranks_sunniest_day_first(self):
        import contextlib
        import io
        from geolib import net as _net
        import sun
        hours = [f"2024-07-{d:02d}T{h:02d}:00" for d in (15, 16) for h in range(24)]
        cloud = [90] * 24 + [5] * 24                                            # the 15th overcast, the 16th clear
        fake = {"timezone": "Europe/Lisbon", "hourly": {"time": hours, "cloud_cover": cloud, "cloud_cover_low": cloud,
                "sunshine_duration": [0] * 24 + [3600] * 24, "precipitation": [0.2] * 24 + [0] * 24,
                "snowfall": [0] * 48, "weather_code": [3] * 24 + [0] * 24, "temperature_2m": [15] * 48}}
        real = _net.fetch_bytes
        _net.fetch_bytes = lambda *a, **k: json.dumps(fake, ensure_ascii=False).encode()
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                sun.cmd_weather(Namespace(at=(38.72, -9.14), date=None, dates="2024-07-15:2024-07-16", hours=None, tz=None, proxy=None))
        finally:
            _net.fetch_bytes = real
        import re
        rows = [ln for ln in buf.getvalue().splitlines() if re.match(r"\d{4}-\d\d-\d\d [A-Z][a-z]{2} ", ln)]
        self.assertTrue(rows[0].startswith("2024-07-16 Tue"))
        self.assertIn("clear", rows[0])


class ReconSummaryTests(unittest.TestCase):
    @staticmethod
    def summary(out: Path) -> str:
        import recon
        return recon.summary(Path("photo.jpg"), out, {}, 1.0, False)

    def test_untagged_scene_is_said(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self.assertIn("- Scene: not tagged (prior did not run) → finish requires no skyline/street check", self.summary(out))
            (out / "prior").mkdir()
            (out / "prior" / "prior.json").write_text(json.dumps({"assessment": {"informative": False, "reasons": ["flat"]}}),
                                                      encoding="utf-8")
            self.assertIn("- Scene: not tagged (no StreetCLIP)", self.summary(out))

    def test_ocr_hint_follows_the_backend(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "intake").mkdir()
            for backend, rapid in (("rapidocr", True), ("apple-vision", False), (None, False)):
                ocr = {"items": [{"text": "Rua Augusta", "conf": 0.9, "pass": "full"}], **({"backend": backend} if backend else {})}
                (out / "intake" / "ocr.json").write_text(json.dumps(ocr), encoding="utf-8")
                md = self.summary(out)
                self.assertEqual(textgeo.RAPIDOCR_NOTE in md, rapid, backend)
                self.assertEqual("Vision cannot read Greek" in md, not rapid, backend)
            (out / "intake" / "ocr.json").write_text(json.dumps({"backend": "rapidocr", "items": []}), encoding="utf-8")
            self.assertIn(textgeo.RAPIDOCR_EMPTY, self.summary(out))

    @staticmethod
    def put(out: Path, rel: str, data: dict) -> None:
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(json.dumps(data), encoding="utf-8")

    @staticmethod
    def next0(md: str) -> str:
        items = [ln for ln in md.splitlines() if ln.startswith("0. ")]
        assert len(items) == 1, items                                  # one item 0, whatever fires
        return items[0]

    def test_ai_image_score_bands_and_skips(self):
        import recon
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self.assertIn("- AI-image check: skipped (not run)", self.summary(out))
            timed = recon.summary(Path("photo.jpg"), out, {"aidet": {"rc": 124, "seconds": 20.0, "error": "timed out after 20s"}}, 1.0, False)
            self.assertIn("- AI-image check: skipped (timed out after 20s", timed)
            self.put(out, "aidet/aidet.json", {"tool": "aidet.py", "skipped": "model unavailable: offline"})
            self.assertIn("- AI-image check: skipped (model unavailable: offline)", self.summary(out))
            self.put(out, "aidet/aidet.json", {"tool": "aidet.py", "p_ai": 0.04, "threshold": 0.65})
            md = self.summary(out)
            self.assertIn("- AI-image score 0.04 (model rank, not proof; threshold 0.65): not flagged; a low score never clears", md)
            self.assertNotIn("Generated-image check", md)
            self.put(out, "aidet/aidet.json", {"tool": "aidet.py", "p_ai": 0.97, "threshold": 0.65})
            md = self.summary(out)
            self.assertIn("- **AI-image score 0.97 (model rank, not proof; threshold 0.65)**", md)
            self.assertIn("possible generated image, unconfirmed (model 0.97): continue and say so", self.next0(md))
            self.assertNotIn("STOP", md)

    def test_generated_check_folds_into_next_item_0(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self.put(out, "aidet/aidet.json", {"tool": "aidet.py", "p_ai": 0.97, "threshold": 0.65})
            self.put(out, "intake/intake.json", {"ai_gallery_hits": [{"site": "civitai.com", "url": "https://civitai.com/images/1"}]})
            item = self.next0(self.summary(out))                       # a gallery page outranks the score
            self.assertIn("https://civitai.com/images/1", item)
            self.assertIn("open the page, confirm the duplicate", item)
            self.assertNotIn("possible generated image", item)
            gen = {"declared": True, "term": "trainedAlgorithmicMedia", "composite": False, "source": "XMP"}
            self.put(out, "meta/meta.json", {"digest": {"provenance": {"WARNING": "File declares generated content (trainedAlgorithmicMedia)",
                                                                       "generated": gen}}})
            md = self.summary(out)                                     # the declaration outranks both
            self.assertIn("- **File declares generated content (trainedAlgorithmicMedia)**", md)
            self.assertIn('`photo_session.py finish "<session folder>" --generated "trainedAlgorithmicMedia"`', self.next0(md))   # runnable as printed
            self.assertIn("operator", self.next0(md))
            self.assertIn("not-generated", self.next0(md))                     # the operator's "it is real" ends this exit
            self.assertNotIn("STOP", md)
            self.put(out, "meta/meta.json", {"digest": {"provenance": {"generated": {**gen, "declared": False, "composite": True}}}})
            self.put(out, "intake/intake.json", {})
            self.put(out, "aidet/aidet.json", {"tool": "aidet.py", "p_ai": 0.2, "threshold": 0.65})
            self.assertNotIn("Generated-image check", self.summary(out))  # an AI-edited real photo is a real photo

    def test_aidet_lane_runs_beside_the_others_with_its_own_timeout(self):
        import contextlib
        import io
        from unittest.mock import patch
        import recon
        with tempfile.TemporaryDirectory() as d:
            photo = Path(d) / "photo.jpg"
            Image.new("RGB", (64, 48)).save(photo)
            for argv, expect in ((["--no-ml"], False), (["--skip", "aidet"], False), ([], True)):
                calls = []

                def run(name, cmd, log, timeout=1800):
                    calls.append((name, cmd, timeout))
                    rc = 124 if name == "aidet" else 0
                    log[name] = {"rc": rc, "seconds": 0.1, "error": f"timed out after {timeout}s" if rc else "", "stdout_tail": ""}
                    return rc

                buf = io.StringIO()
                with patch.object(recon, "run", run), patch.object(sys, "argv", ["recon.py", str(photo), "--out-dir", str(Path(d) / "recon"), *argv]), \
                        contextlib.redirect_stdout(buf):
                    recon.main()
                lane = [c for c in calls if c[0] == "aidet"]
                self.assertEqual(bool(lane), expect, argv)
                if lane:
                    name, cmd, timeout = lane[0]
                    self.assertEqual(timeout, recon.AIDET_TIMEOUT)
                    self.assertTrue(cmd[3].endswith("aidet.py"))
                    self.assertEqual(Path(cmd[cmd.index("--out-dir") + 1]), Path(d) / "recon" / "aidet")
                    self.assertIn(f"aidet: skipped (timed out after {recon.AIDET_TIMEOUT}s", buf.getvalue())
            self.assertIn("aidet", recon.main.__globals__["ML_STEPS"])

    def test_a_stale_score_never_passes_for_this_run(self):
        import contextlib
        import io
        from unittest.mock import patch
        import recon
        with tempfile.TemporaryDirectory() as d:
            photo = Path(d) / "frame_031.jpg"
            Image.new("RGB", (64, 48)).save(photo)
            out = Path(d) / "recon"
            for argv, rc, reason in ((["--no-ml"], None, "not run (--no-ml)"), (["--skip", "aidet"], None, "not run (--skip aidet)"),
                                     ([], 124, f"timed out after {recon.AIDET_TIMEOUT}s"), ([], 0, "not run")):
                self.put(out, "aidet/aidet.json", {"tool": "aidet.py", "p_ai": 0.97, "threshold": 0.65})   # an earlier run, another frame

                def run(name, cmd, log, timeout=1800):
                    code = rc if name == "aidet" else 0
                    log[name] = {"rc": code, "seconds": 0.1, "error": f"timed out after {timeout}s" if code else "", "stdout_tail": ""}
                    return code

                with patch.object(recon, "run", run), patch.object(sys, "argv", ["recon.py", str(photo), "--out-dir", str(out), *argv]),                         contextlib.redirect_stdout(io.StringIO()):
                    recon.main()
                md = (out / "recon.md").read_text(encoding="utf-8")
                self.assertIn(f"- AI-image check: skipped ({reason}", md, argv)
                self.assertNotIn("0.97", md, argv)
                rec = json.loads((out / "aidet" / "aidet.json").read_text(encoding="utf-8"))   # one current record for the viewer and finish
                self.assertEqual(rec["tool"], "aidet.py")
                self.assertTrue(rec["skipped"].startswith(reason), (argv, rec))
                self.assertNotIn("p_ai", rec)

    def test_run_stops_the_whole_tree_on_timeout(self):
        import time
        import recon
        log: dict = {}
        child = "import subprocess, sys; subprocess.run([sys.executable, '-c', 'import time; time.sleep(30)'])"
        t0 = time.time()
        rc = recon.run("slow", [sys.executable, "-c", child], log, timeout=1)
        self.assertEqual(rc, 124)
        self.assertLess(time.time() - t0, 20)                          # a grandchild holding the pipes no longer blocks the read
        self.assertEqual(log["slow"]["error"], "timed out after 1s")


class AidetTests(unittest.TestCase):
    def test_score_record_with_a_stubbed_model(self):
        import aidet
        seen = []

        def logit(x):
            seen.append(x)
            return 3.0

        with tempfile.TemporaryDirectory() as d:
            photo = Path(d) / "wide.png"
            Image.new("RGB", (880, 440), (255, 0, 0)).save(photo)
            rec = aidet.analyse(photo, logit)
            self.assertEqual(set(rec), {"tool", "model", "revision", "file", "licence", "p_ai", "raw_logit", "threshold", "interpolation",
                                        "seconds"})
            self.assertEqual((rec["tool"], rec["model"], rec["licence"], rec["threshold"], rec["interpolation"]),
                             ("aidet.py", aidet.REPO, "MIT", 0.65, "bilinear"))
            self.assertRegex(rec["revision"], r"^[0-9a-f]{40}$")
            self.assertEqual(rec["file"], "community_forensics_frontier_fp16.onnx")
            self.assertEqual(rec["raw_logit"], 3.0)
            self.assertAlmostEqual(rec["p_ai"], 1 / (1 + math.exp(-(3.0 - 0.7403357915937764))), places=4)
            x = seen[0]                                                # short edge 440, centre crop 384, ImageNet normalisation
            self.assertEqual((x.shape, x.dtype), ((1, 3, 384, 384), np.float32))
            self.assertAlmostEqual(float(x[0, 0, 0, 0]), (1 - 0.485) / 0.229, places=4)
            self.assertAlmostEqual(float(x[0, 2, 383, 383]), (0 - 0.406) / 0.225, places=4)

    def test_failures_are_skips_written_with_exit_0(self):
        import contextlib
        import io
        from unittest.mock import patch
        import aidet

        def offline():
            raise OSError("offline")

        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.jpg"
            bad.write_bytes(b"not an image")
            rec = aidet.analyse(bad, lambda x: 0.0)
            self.assertEqual(set(rec), {"tool", "skipped"})
            self.assertIn("image unreadable", rec["skipped"])
            photo = Path(d) / "p.jpg"
            Image.new("RGB", (500, 400)).save(photo)
            with patch.object(aidet, "onnx_logit", offline), patch.object(sys, "argv", ["aidet.py", str(photo), "--out-dir", str(Path(d) / "a")]), \
                    contextlib.redirect_stdout(io.StringIO()):
                aidet.main()                                           # returns: no SystemExit, so the exit code is 0
            rec = json.loads((Path(d) / "a" / "aidet.json").read_text(encoding="utf-8"))
            self.assertEqual(rec["tool"], "aidet.py")
            self.assertIn("model unavailable", rec["skipped"])
            self.assertIn("doctor.py --models", rec["skipped"])


class IntakeGalleryTests(unittest.TestCase):
    def test_ai_gallery_hosts_are_flagged_by_suffix(self):
        from unittest.mock import patch
        import intake
        with tempfile.TemporaryDirectory() as d:
            photo = Path(d) / "photo.jpg"
            Image.new("RGB", (100, 100), "white").save(photo)
            out = Path(d) / "out"
            docs = {"yandex": {"links": [{"title": "a", "url": "https://civitai.com/images/123", "site": "civitai.com"},
                                         {"title": "b", "url": "https://stock.adobe.com/images/1", "site": "stock.adobe.com"},
                                         {"title": "c", "url": "https://notcivitai.com/a", "site": "notcivitai.com"},
                                         {"title": "d", "url": "https://jimeng.jianying.com/ai-tool/work/7", "site": "jimeng.jianying.com"}]},
                    "baidu": {"similar": [{"thumb": "t", "from": "https://www.tensor.art/images/9", "site": "tensor.art"},
                                          {"thumb": "t", "from": "https://www.freepik.com/photo/2", "site": "freepik.com"}]}}

            def run(cmd, **kwargs):
                if any(str(c).endswith("revimg.py") for c in cmd):
                    engine = cmd[cmd.index("--engines") + 1]
                    rev = Path(cmd[cmd.index("--out-dir") + 1])
                    (rev / f"photo_{engine}.json").write_text(json.dumps(docs[engine]), encoding="utf-8")
                return 0, "", ""

            with patch.object(intake, "_run", run), patch.object(sys, "argv", ["intake.py", str(photo), "--out-dir", str(out), "--no-ocr"]), \
                    patch("sys.stdout", new=__import__("io").StringIO()):
                intake.main()
            hits = json.loads((out / "intake.json").read_text(encoding="utf-8"))["ai_gallery_hits"]
            self.assertEqual(sorted(h["url"] for h in hits), ["https://civitai.com/images/123", "https://jimeng.jianying.com/ai-tool/work/7",
                                                              "https://www.tensor.art/images/9"])
            self.assertEqual({h["site"] for h in hits}, {"civitai.com", "jimeng.jianying.com", "tensor.art"})
            md = (out / "intake.md").read_text(encoding="utf-8")
            self.assertIn("AI-gallery host: open and compare (a host alone only down-weights)", md)
            self.assertNotIn("stock.adobe.com", md.split("AI-gallery host")[1].splitlines()[0])

    def test_unparsable_links_are_skipped_not_fatal(self):
        import intake
        with tempfile.TemporaryDirectory() as d:
            rev = Path(d)
            (rev / "photo_yandex.json").write_text(json.dumps({"links": [
                {"url": "https://[civitai.com/images/1", "site": "civitai.com"},          # an unbalanced '[' raises ValueError in urlsplit
                {"url": "", "site": "tensor.art › [images]"},
                {"url": "https://civitai.com/images/2", "site": "civitai.com"}]}), encoding="utf-8")
            entries, _, hits = intake._collect_rev(rev)
            self.assertEqual(len(entries), 1)
            self.assertEqual(hits, [{"site": "civitai.com", "url": "https://civitai.com/images/2"}])   # a link that does not parse is no hit


class CluesOcrTests(unittest.TestCase):
    def test_driving_side_reports_switch_year(self):
        import clues
        m = clues.lookup_driving_side("SE", None)["matches"][0]
        self.assertEqual((m["country"], m["side"]), ("Sweden", "right"))
        self.assertIn("1967", m["switched"])                       # Dagen H, 3 September 1967
        self.assertIn("switched", clues.lookup_driving_side("left", None)["matches"][0])

    def test_rapidocr_notice_only_when_langs_given(self):
        import contextlib
        import io
        import types
        import ocr
        real = sys.modules.get("rapidocr_onnxruntime")
        fake = types.ModuleType("rapidocr_onnxruntime")
        fake.RapidOCR = lambda: None
        sys.modules["rapidocr_onnxruntime"] = fake
        try:
            for langs, expect in ((["auto"], False), ([], False), (["pl", "en"], True)):
                buf = io.StringIO()
                with contextlib.redirect_stderr(buf):
                    ocr.RapidOCRBackend(langs)
                self.assertEqual("ignores --langs" in buf.getvalue(), expect, langs)
        finally:
            if real is None:
                sys.modules.pop("rapidocr_onnxruntime", None)
            else:
                sys.modules["rapidocr_onnxruntime"] = real


class EvidenceBuildTests(unittest.TestCase):
    LAT0, LON0 = 37.5665, 126.9780

    def _map(self, td: Path) -> Path:
        """A 512x512 black zoom-19 mosaic whose second tile column/row holds (LAT0, LON0)."""
        import geo
        tx, ty = (int(v // 256) for v in geo.ll2px(19, self.LAT0, self.LON0))
        Image.new("RGB", (512, 512), "black").save(td / "map.jpg")
        (td / "map.json").write_text(json.dumps({"zoom": 19, "origin_tile": [tx - 1, ty - 1], "size": [512, 512]}),
                                     encoding="utf-8")
        return td / "map.jpg"

    def _build(self, spec: dict, td: Path, out: str = "ev.jpg") -> str:
        import contextlib
        import io
        import evidence
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            evidence.build(dict({"map": "map.jpg", "width": 512}, **spec), td, td / out)
        self.assertTrue((td / out).exists())
        return err.getvalue()

    def test_camera_outside_map_warns_with_refetch_that_covers_it(self):
        import re
        import geo
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            self._map(td)
            cam = geo.dest((self.LAT0, self.LON0), 90, 600)
            err = self._build({"camera": list(cam), "heading": 90}, td)
            for s in ("outside this map", "tiles.py fetch", "--radius"):
                self.assertIn(s, err)
            m = re.search(r"fetch ([-\d.]+),([-\d.]+) --zoom (\d+) --radius (\d+)", err)
            z, rad = int(m[3]), int(m[4])
            cx, cy = (int(v // 256) for v in geo.ll2px(z, float(m[1]), float(m[2])))
            tx, ty = (int(v // 256) for v in geo.ll2px(z, self.LAT0, self.LON0))
            kx, ky = (int(v // 256) for v in geo.ll2px(z, *cam))
            for x, y in ((kx, ky), (tx - 1, ty - 1), (tx, ty)):             # the new map holds the camera and the old extent
                self.assertLessEqual(abs(x - cx), rad)
                self.assertLessEqual(abs(y - cy), rad)

    def test_far_camera_refetch_zooms_out_instead_of_growing(self):
        # 5 km at zoom 19 would need 41 rings (6,889 tiles, beyond PIL's decompression-bomb limit): the suggestion stays within
        # 8 rings (17x17 tiles) by lowering the zoom, and still holds the camera and the old extent
        import re
        import geo
        from tiles import Mosaic
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            mosaic = Mosaic(self._map(td))
            corners = [mosaic.to_ll(0, 0), mosaic.to_ll(511, 511)]
            for km, crop in ((5, [0, 0, 512, 512]), (20, None)):
                cam = geo.dest((self.LAT0, self.LON0), 90, km * 1000)
                err = self._build(dict({"camera": list(cam)}, **({"crop": crop} if crop else {})), td)
                m = re.search(r"fetch ([-\d.]+),([-\d.]+) --zoom (\d+) --radius (\d+)", err)
                z, rad = int(m[3]), int(m[4])
                self.assertLess(z, 19, km)
                self.assertLessEqual((2 * rad + 1) ** 2, 17 ** 2, km)
                cx, cy = (int(v // 256) for v in geo.ll2px(z, float(m[1]), float(m[2])))
                for ll in (cam, *corners):
                    kx, ky = (int(v // 256) for v in geo.ll2px(z, *ll))
                    self.assertLessEqual(max(abs(kx - cx), abs(ky - cy)), rad, (km, ll))
                self.assertEqual('drop or redo "crop"' in err, bool(crop), km)   # crop is in pixels of the map the refetch replaces

    def test_long_wedge_from_a_camera_inside_does_not_warn(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            self._map(td)
            self.assertEqual(self._build({"camera": [self.LAT0, self.LON0], "heading": 90, "range_m": 2000}, td), "")

    def test_camera_outside_the_crop_warns(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            self._map(td)
            self.assertIn("outside the crop", self._build({"camera": [self.LAT0, self.LON0], "crop": [0, 0, 100, 100]}, td))

    def test_wrap_breaks_at_spaces_and_falls_back_for_cjk(self):
        import evidence
        from geolib.cli import font
        f = font(20, prefer_wide=True)
        text = "Public reference: same tile facade, white bands and chimney"
        lines = evidence._wrap(text, f, 414)
        self.assertGreater(len(lines), 1)
        for ln in lines:
            self.assertTrue(set(ln.split()) <= set(text.split()), ln)                # whole words only, never "white ba|nds"
        ko = "서울특별시중구세종대로한국프레스센터앞횡단보도신호등버스정류장공중전화부스가로수"  # 40 Hangul, no spaces
        lines = evidence._wrap(ko, f, 414)
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(f.getlength(ln) <= 414 for ln in lines))
        self.assertEqual("".join(lines), ko)

    def test_evidence_camera_drawn_over_labels(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            from tiles import Mosaic
            cam = Mosaic(self._map(td)).to_ll(256, 256)
            label = {"at": list(cam), "text": "Long label anchored on the camera position, clamped back over it"}
            self._build({"camera": list(cam), "heading": 240, "labels": [label]}, td, "ev.png")   # PNG: no JPEG colour bleed
            with Image.open(td / "ev.png") as im:
                r, g, b = im.convert("RGB").getpixel((256, 256))
            self.assertGreater(r, 200)
            self.assertLess(g, 90)
            self.assertLess(b, 90)


if __name__ == "__main__":
    unittest.main(verbosity=1)
