#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "tzdata"]
# ///
"""Offline checks for the consolidated toolkit: geolib paths, helpers and data tables, region packs, plate-code levels,
meta.py without exiftool, poi.py map subcommands, the sources_check registry.
Run from anywhere: uv run scripts/tests/test_toolkit.py"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from geolib import paths  # noqa: E402


def _stdout(fn, *a, **k) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*a, **k)
    return buf.getvalue()


class PathsAndDataTests(unittest.TestCase):
    def test_data_dir_is_assets_data(self):
        self.assertEqual(paths.DATA_DIR, SCRIPTS.parent / "assets" / "data")
        self.assertTrue(paths.DATA_DIR.is_dir())
        self.assertEqual(paths.SKILL_DIR, SCRIPTS.parent)

    def test_every_table_loads_with_meta(self):
        files = sorted(paths.DATA_DIR.glob("*.json"))
        self.assertEqual({f.stem for f in files}, {"ai_hosts", "calling_codes", "countries", "country_names", "driving_side", "plate_codes",
                                                   "streetview_coverage", "territories", "text_signals"})
        for f in files:
            with self.subTest(table=f.name):
                d = json.loads(f.read_text(encoding="utf-8"))
                self.assertIn("_meta", d)

    def test_index_lists_every_table(self):
        index = (paths.DATA_DIR / "index.md").read_text(encoding="utf-8")
        for f in [*paths.DATA_DIR.glob("*.json"), *paths.DATA_DIR.glob("regions/*/data/*.json")]:
            self.assertIn(f"`{f.relative_to(paths.DATA_DIR).as_posix()}`", index)
        self.assertEqual(list(paths.DATA_DIR.rglob("README.md")), [])

    def test_packs_hold_data_only(self):
        for d in (paths.DATA_DIR / "regions").iterdir():
            names = {f.relative_to(d).as_posix() for f in d.rglob("*") if f.is_file()}
            self.assertTrue(names <= {"region.json", "tests.json"} | {n for n in names if n.startswith("data/") and n.endswith(".json")}, names)
            m = json.loads((d / "region.json").read_text(encoding="utf-8"))
            self.assertNotIn("maintainers", m)

    def test_cache_dir_honours_env_and_creates(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"GEOINT_CACHE": d}):
            p = paths.cache_dir("unit", "x")
            self.assertEqual(p, Path(d) / "unit" / "x")
            self.assertTrue(p.is_dir())

    @unittest.skipUnless(os.name == "nt", "Windows-only default")
    def test_windows_default_without_dot_cache(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as lad:
            env = {k: v for k, v in os.environ.items() if k != "GEOINT_CACHE"}
            env["LOCALAPPDATA"] = lad
            with patch.dict(os.environ, env, clear=True), patch.object(Path, "home", return_value=Path(home)):
                self.assertEqual(paths.cache_root(), Path(lad) / "geoint")

    def test_driving_side_curated_rows(self):
        d = json.loads((paths.DATA_DIR / "driving_side.json").read_text(encoding="utf-8"))
        rows = {k: v for k, v in d.items() if k != "_meta"}
        self.assertEqual(d["_meta"]["count"], len(rows))
        self.assertIn("license", d["_meta"])
        self.assertGreaterEqual(sum(1 for v in rows.values() if v.get("curated")), 40)
        self.assertEqual(rows["China"]["side"], "right")
        self.assertEqual(rows["Hong Kong"]["side"], "left")
        self.assertEqual(rows["Macau"]["side"], "left")
        self.assertEqual(rows["United Kingdom"]["side"], "left")
        self.assertTrue(rows["China"].get("curated"))

    def test_refresh_keeps_curated_rows(self):
        import refresh
        parsed = {"China": {"side": "left", "switched": "", "note": "scrape error"}, "Peru": {"side": "right", "switched": "", "note": ""}}
        kept = refresh.keep_curated(paths.DATA_DIR / "driving_side.json", parsed)
        self.assertEqual(kept["China"]["side"], "right")
        self.assertTrue(kept["China"]["curated"])
        self.assertIn("United Kingdom and overseas territories", kept)


class PlateTests(unittest.TestCase):
    def test_china_prefix_is_city_level(self):
        import regions
        m = regions.lookup("plate", "粤B·12345", "cn")["matches"]
        self.assertEqual([(x["admin1"], x.get("admin2")) for x in m], [("广东省", "深圳市")])
        self.assertEqual(regions.lookup("plate", "粤X", "cn")["matches"][0].get("district"), "顺德区")
        self.assertEqual(regions.lookup("plate", "粤", "cn")["matches"][0]["admin1"], "广东省")       # bare province character
        b = regions.lookup("plate", "京B", "cn")["matches"][0]
        self.assertEqual((b["admin1"], b.get("admin2"), b["note"]), ("北京市", None, "出租车"))      # a vehicle class, not a place
        self.assertTrue(regions.lookup("plate", "渝C", "cn")["matches"][0].get("unverified"))

    def test_plate_code_levels_and_country(self):
        import clues
        it = clues.lookup_plate_code("PA", "IT")
        self.assertEqual(it["searched"], ["IT"])
        self.assertEqual((it["matches"][0]["country_code"], it["matches"][0]["admin2"]), ("IT", "Palermo"))
        ch = clues.lookup_plate_code("BE", "Switzerland")["matches"][0]
        self.assertEqual((ch["admin1"], ch.get("admin2")), ("Bern", None))                       # cantons are first-level
        de = clues.lookup_plate_code("ABG", "DE")["matches"][0]
        self.assertEqual((de["admin1"], de["admin2"]), ("Thüringen", "Landkreis Altenburger Land"))
        gb = clues.lookup_plate_code("51", "GB")["matches"]
        self.assertTrue(any("dates the registration" in m["note"] and not m.get("admin1") for m in gb))
        self.assertEqual(clues.lookup_plate_code("PA", "Narnia")["status"], "unsupported")
        many = clues.lookup_plate_code("BA")
        self.assertGreaterEqual(len({m["country_code"] for m in many["matches"]}), 4)
        self.assertIn("several countries", many["note"])

    def test_coverage_kind(self):
        import clues
        r = clues.lookup_coverage("streetview")
        iso = {m["country_code"] for m in r["matches"]}
        self.assertIn("KE", iso)
        self.assertNotIn("MA", iso)


class MetaFallbackTests(unittest.TestCase):
    def make_photo(self, folder: Path) -> Path:
        from PIL import Image
        ex = Image.Exif()
        ex[0x010F], ex[0x0110] = "TestMake", "TestModel"
        sub = ex.get_ifd(0x8769)
        sub[0x9003], sub[0x9011], sub[0x920A], sub[0xA405] = "2024:07:12 10:15:30", "+01:00", 4.25, 26
        gps = ex.get_ifd(0x8825)
        gps.update({1: "N", 2: (38.0, 42.0, 36.0), 3: "W", 4: (9.0, 7.0, 48.0), 5: b"\x00", 6: 42.5,
                    7: (9.0, 15.0, 30.0), 16: "T", 17: 123.5, 29: "2024:07:12"})
        thumb = io.BytesIO()
        Image.new("RGB", (160, 90), (200, 30, 30)).save(thumb, "JPEG")          # 16:9 preview of a 4:3 photo
        xmp = (b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF><rdf:Description photoshop:City="Lisboa" '
               b'drone-dji:GimbalYawDegree="-12.5"/></rdf:RDF></x:xmpmeta>')
        f = folder / "PXL_20240712_101530123.jpg"
        Image.new("RGB", (400, 300), (90, 140, 90)).save(f, "JPEG", exif=ex.tobytes() + thumb.getvalue(), xmp=xmp)
        return f

    def test_digest_without_exiftool(self):
        import meta
        with tempfile.TemporaryDirectory() as d, patch.object(meta.shutil, "which", return_value=None):
            f = self.make_photo(Path(d))
            dg, previews, raw = meta.analyse(f, Path(d) / "out", no_previews=False, quiet=True)
        self.assertTrue(dg["backend"].startswith("pillow"))
        self.assertIn("need exiftool", dg["notice"])
        self.assertAlmostEqual(dg["gps"]["lat"], 38.71, places=4)
        self.assertAlmostEqual(dg["gps"]["lon"], -9.13, places=4)
        self.assertEqual(dg["gps"]["image_direction_deg"], 123.5)
        self.assertEqual(dg["gps"]["altitude_m"], 42.5)
        self.assertEqual(dg["gps"]["dji_gimbal_yaw_deg"], -12.5)
        self.assertEqual(dg["time"]["utc_offset"], "+01:00")
        self.assertEqual(dg["time"]["GPSDateTime"], "2024:07:12 09:15:30Z")
        self.assertIn("PT", dg["time"]["countries_with_this_offset_on_that_date"])
        self.assertEqual(dg["optics"]["focal_35mm"], 26.0)
        self.assertEqual(dg["optics"]["focal_mm"], 4.25)
        self.assertEqual(len(dg["optics"]["fov_4x3_long_short_deg"]), 2)
        self.assertEqual(dg["location_text"].get("XMP-photoshop:City"), "Lisboa")
        self.assertEqual(dg["camera"]["Make"], "TestMake")
        self.assertTrue(dg["has_exif"])
        self.assertTrue(any("cropped" in p.get("note", "") for p in previews))      # APP1 thumbnail, no exiftool
        self.assertIn("Notice: exiftool not found", meta.to_md(dg, previews))

    def test_json_mode_one_line_per_photo(self):
        import meta
        with tempfile.TemporaryDirectory() as d, patch.object(meta.shutil, "which", return_value=None):
            f = self.make_photo(Path(d))
            with patch.object(sys, "argv", ["meta.py", str(f), str(f), "--json"]):
                out = _stdout(meta.main)
        lines = [json.loads(x) for x in out.strip().splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["file"], f.name)
        self.assertNotIn("gcj02", lines[0]["gps"])                            # Lisbon is outside China

    def test_china_point_gets_gcj02(self):
        import meta
        dg = meta.digest(Path(__file__), {"GPS:GPSLatitude": 39.9087, "GPS:GPSLongitude": 116.3975})
        lat, lon = dg["gps"]["gcj02"]
        self.assertNotAlmostEqual(lat, 39.9087, places=4)
        self.assertLess(abs(lat - 39.9087) + abs(lon - 116.3975), 0.02)

    def test_xmp_and_iso6709_parsers(self):
        import meta
        self.assertAlmostEqual(meta._xmp_coord("38,42.6N"), 38.71)
        self.assertAlmostEqual(meta._xmp_coord("9,7,48W"), -9.13)
        tags = meta._xmp_tags(b'<x:xmpmeta><exif:GPSLatitude>38,42.6N</exif:GPSLatitude></x:xmpmeta>')
        self.assertAlmostEqual(tags["XMP-exif:GPSLatitude"], 38.71)
        with tempfile.TemporaryDirectory() as d:
            v = Path(d) / "clip.mp4"
            v.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64 + b"\xa9xyz\x00\x12\x15\xc7+38.7100-009.1300/" + b"\x00" * 64)
            raw = meta.pillow_fallback(v)
            dg = meta.digest(v, raw)
        self.assertEqual(raw["QuickTime:GPSCoordinates"], "+38.7100 -009.1300")
        self.assertAlmostEqual(dg["gps"]["lon"], -9.13)


class PoiMapTests(unittest.TestCase):
    ELEMENTS = {"elements": [
        {"type": "node", "id": 1, "lat": 48.8590, "lon": 2.2950,
         "tags": {"name": "Cafe Far", "amenity": "cafe", "opening_hours": "Mo-Su 08:00-20:00", "phone": "+33 1 00"}},
        {"type": "way", "id": 2, "center": {"lat": 48.8585, "lon": 2.2946},
         "tags": {"name": "Boulangerie", "shop": "bakery", "cuisine": "french", "website": "https://example.org",
                  "addr:housenumber": "5", "addr:street": "Rue X", "addr:city": "Paris"}},
    ]}

    def setUp(self):
        import poi
        self.poi = poi

    def test_category_table(self):
        self.assertGreaterEqual(len(self.poi.CATEGORY_TAGS), 44)
        self.assertEqual(self.poi.category_tags("bakery")[0], [("shop", "bakery"), ("amenity", "bakery")])
        self.assertEqual(self.poi.category_tags("church"), ([("amenity", "place_of_worship")], "christian"))
        self.assertEqual(self.poi.category_tags("shop=car_repair"), ([("shop", "car_repair")], None))
        with self.assertRaises(ValueError):
            self.poi.category_tags("not-a-category")
        ql = self.poi.overpass_ql([("shop", "bakery"), ("amenity", "bakery")], None, "around:500,48.85,2.29")
        self.assertIn('nwr["shop"="bakery"](around:500,48.85,2.29);', ql)
        self.assertIn('nwr["amenity"="bakery"](around:500,48.85,2.29);', ql)
        self.assertTrue(ql.endswith("out center tags;"))               # no server-side cut: nearest N chosen after sorting

    def test_nearby_output_shape_and_order(self):
        seen = []
        with tempfile.TemporaryDirectory() as d, \
                patch.object(self.poi, "_overpass", side_effect=lambda ql, proxy, cache: seen.append(ql) or self.ELEMENTS):
            out = _stdout(self.poi.main, ["nearby", "48.8584,2.2945", "--category", "cafe", "--category", "bakery",
                                          "--limit", "5", "--out", str(Path(d) / "pts.json")])
            pts = json.loads((Path(d) / "pts.json").read_text(encoding="utf-8"))
        res = json.loads(out)
        self.assertEqual(len(seen), 2)
        self.assertEqual(res["count"], 2)                                         # deduplicated across categories
        first = res["results"][0]
        self.assertEqual(first["name"], "Boulangerie")                            # nearest first
        for key in ("name", "address", "lat", "lon", "distance_m", "maps_url", "cuisine", "website"):
            self.assertIn(key, first)
        self.assertEqual(first["address"], "5, Rue X, Paris")
        self.assertIn("hours", res["results"][1])
        self.assertIn("phone", res["results"][1])
        self.assertEqual(list(pts.values())[0], [48.8585, 2.2946])

    def test_legacy_search_cli_still_works(self):
        with patch.object(self.poi, "search_osm", return_value=[{"src": "osm", "name": "Eiffel Tower", "city": "", "area": "",
                                                                  "address": "Paris", "type": "man_made/tower", "wgs": [48.8583, 2.2945]}]) as so:
            out = _stdout(self.poi.main, ["Eiffel Tower", "--sources", "osm", "--country", "fr"])
        self.assertEqual(so.call_args.args[0], "Eiffel Tower")
        self.assertIn("1 candidates with coordinates", out)

    def test_no_result_hint_searches_the_address_on_the_country_engines(self):
        for argv, country in [(["上海市 不存在花园", "--sources", "osm"], "CN"), (["Nowhere Street 99", "--sources", "osm", "--country", "fr"], "FR")]:
            with self.subTest(country=country), patch.object(self.poi, "search_osm", return_value=[]):
                out = _stdout(self.poi.main, argv)
            self.assertIn(f'revimg.py --query "<address>" --country {country}', out)

    def test_routes_use_mode_specific_servers_and_skip_geocoding_points(self):
        urls = []
        fake = {"code": "Ok", "routes": [{"distance": 4000.0, "duration": 3000.0, "legs": []}]}
        with patch.object(self.poi, "_get_json", side_effect=lambda url, proxy, timeout=25: urls.append(url) or fake), \
                patch.object(self.poi, "nominatim") as nom:
            walk = json.loads(_stdout(self.poi.main, ["distance", "45.764,4.836", "--to", "45.771,4.880", "--mode", "walking"]))
            _stdout(self.poi.main, ["distance", "45.764,4.836", "--to", "45.771,4.880"])
        nom.assert_not_called()
        self.assertIn("routing.openstreetmap.de/routed-foot/route/v1/driving/4.836,45.764;4.88,45.771", urls[0])
        self.assertIn("routing.openstreetmap.de/routed-car/route/v1/driving/", urls[1])
        self.assertEqual(walk["distance_km"], 4.0)
        self.assertIn("straight_line_km", walk)
        self.assertNotIn("warning", walk)

    def test_route_falls_back_to_demo_server_with_a_warning(self):
        fake = {"code": "Ok", "routes": [{"distance": 4000.0, "duration": 300.0, "legs": []}]}

        def get(url, proxy, timeout=25):
            if "routing.openstreetmap.de" in url:
                raise RuntimeError("down")
            return fake
        with patch.object(self.poi, "_get_json", side_effect=get), contextlib.redirect_stderr(io.StringIO()):
            res = json.loads(_stdout(self.poi.main, ["distance", "45.764,4.836", "--to", "45.771,4.880", "--mode", "walking"]))
        self.assertIn("router.project-osrm.org", res["source"])
        self.assertIn("car route", res["warning"])

    def test_nominatim_is_spaced_one_second(self):
        sleeps = []
        with patch.object(self.poi, "_get_json", return_value=[]), patch.object(self.poi.time, "sleep", side_effect=sleeps.append):
            self.poi._last_nominatim = 0.0
            self.poi.nominatim("search", {"q": "a"}, None)
            self.poi.nominatim("search", {"q": "b"}, None)
        self.assertEqual(len(sleeps), 1)
        self.assertGreater(sleeps[0], 0.5)

    def test_timezone_offset_from_seconds(self):
        fake = {"timeZone": "Europe/Paris", "currentLocalTime": "2026-10-12T01:00:00", "currentUtcOffset": {"seconds": 7200}}
        with patch.object(self.poi, "_get_json", return_value=fake), patch.object(self.poi, "_offline_zone", return_value=None):
            res = json.loads(_stdout(self.poi.main, ["timezone", "48.85,2.29"]))
        self.assertEqual((res["timezone"], res["utc_offset"]), ("Europe/Paris", "+02:00"))

    def test_timezone_falls_back_to_longitude(self):
        with patch.object(self.poi, "_get_json", side_effect=RuntimeError("down")), \
                patch.object(self.poi, "_offline_zone", return_value=None), contextlib.redirect_stderr(io.StringIO()):
            res = json.loads(_stdout(self.poi.main, ["timezone", "48.85", "2.29"]))
        self.assertEqual(res["utc_offset"], "+00:00")
        self.assertIn("longitude approximation", res["source"])


class GeolibHelperTests(unittest.TestCase):
    def test_geomath_matches_geo(self):
        import geo
        from geolib import geomath
        self.assertAlmostEqual(geo.distance((48.8584, 2.2945), (45.764, 4.8357)), geomath.haversine_m((48.8584, 2.2945), (45.764, 4.8357)))
        self.assertAlmostEqual(geomath.haversine_m((48.8584, 2.2945), (45.764, 4.8357)) / 1000, 393.8, delta=0.5)
        self.assertAlmostEqual(geomath.bearing((0, 0), (1, 0)), 0.0)
        self.assertEqual(geomath.tile_xy(40.7580, -73.9855), (38598, 49258))
        lat, lon = geomath.dest((45.0, 7.0), 90, 1000)
        self.assertAlmostEqual(geomath.haversine_m((45.0, 7.0), (lat, lon)), 1000, delta=0.5)

    def test_neg_coords_and_font(self):
        from geolib import cli
        self.assertEqual(cli.neg_coords(["-1.45,-48.5", "-3", "x"]), [" -1.45,-48.5", "-3", "x"])
        # every lat,lon-led value shape: --covers spans, --ring specs and geo.py --sight lat,lon@bearing
        self.assertEqual(cli.neg_coords(["-35.81,144.74:-36,145", "-33.87,151.21:50:500:50:30", "-33.87,151.21@45"]),
                         [" -35.81,144.74:-36,145", " -33.87,151.21:50:500:50:30", " -33.87,151.21@45"])
        for text in ("Rua Augusta", "广东省", "서울", ""):
            self.assertTrue(hasattr(cli.font(14, text), "getbbox"))

    def test_contact_sheet_layout(self):
        from PIL import Image
        from geolib import cli
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "s.jpg"
            cli.contact_sheet([(Image.new("RGB", (64, 48), "red"), "a"), (Image.new("RGB", (48, 64), "blue"), "b")], out, cols=3, tw=120, th=90)
            with Image.open(out) as im:
                self.assertEqual(im.size, (360, 90))

    def test_coverage_module_is_stdlib_only(self):
        import ast
        src = (SCRIPTS / "geolib" / "coverage.py").read_text(encoding="utf-8")
        mods = {a.name.split(".")[0] for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Import) for a in n.names}
        self.assertFalse(mods & {"numpy", "PIL", "streetlevel", "requests"})


class SourcesRegistryTests(unittest.TestCase):
    def setUp(self):
        import sources_check
        self.sc = sources_check
        self.reg = sources_check.build_registry()

    def test_registry_integrity(self):
        keys = [p.key for p in self.reg]
        self.assertEqual(len(keys), len(set(keys)))
        for p in self.reg:
            with self.subTest(probe=p.key):
                self.assertTrue(p.url.startswith(("https://", "http://")))
                self.assertTrue(p.expect.strip())
                self.assertTrue(callable(p.check))
                for s in p.scripts.split(","):
                    self.assertTrue(s == "-" or (SCRIPTS / s).exists(), s)
        for needed in ("nominatim-search", "nominatim-reverse", "overpass", "google-sat", "google-hybrid", "esri", "esri-wayback",
                       "bing-aerial", "eox-s2", "gibs", "terrarium", "open-meteo", "geonames-info", "geonames-cities500", "nsi",
                       "baidu-pano", "so-search", "poi-osm", "gsv-coverage", "gsv-metadata", "gsv-targets", "apple-lookaround", "bing-streetside",
                       "yandex-pano", "mapy-pano", "kartaview", "panoramax", "mapillary", "socrata", "commons",
                       "yandex-images", "baidu-images", "osrm-driving", "hf-streetclip", "hf-megaloc", "hf-owlv2"):
            self.assertIn(needed, keys)
        mirrors = [p for p in self.reg if p.key.startswith("overpass-")]
        with patch.dict(os.environ, {"GEO_OVERPASS_URL": ""}):
            import osm
            self.assertEqual(len(mirrors), len(osm.endpoints()))
        self.assertTrue(all(p.optional for p in mirrors))

    def test_runner_statuses_and_selection(self):
        def boom(ctx):
            raise self.sc.Fail("wrong answer")

        def skip(ctx):
            raise self.sc.Skip("no token")
        ctx = self.sc.Ctx(None, 5)
        mk = lambda key, fn, **kw: self.sc.Probe(key, key, "poi.py", "https://example.org", "x", fn, **kw)  # noqa: E731
        rows = [self.sc.run_probe(mk("a", lambda c: "fine"), ctx, False), self.sc.run_probe(mk("b", boom), ctx, False),
                self.sc.run_probe(mk("c", skip), ctx, False), self.sc.run_probe(mk("d", lambda c: "x", group="models"), ctx, True)]
        self.assertEqual([r["status"] for r in rows], ["PASS", "FAIL", "SKIP", "SKIP"])
        self.assertIn("wrong answer", self.sc.table(rows))
        self.assertEqual({p.key for p in self.sc.select(self.reg, "nominatim")},
                         {"nominatim-search", "nominatim-reverse", "poi-osm"})


class GeometrySunBenchTests(unittest.TestCase):
    """sun.py dish names / half-day label / tz / --out note, geo.py fov --aspect and intersect errors, frame --anchor heading, imgprep plateau peaks,
    opendata group, bench satscan and match --dry-run (bench runs through uv: its deps are not in this suite's env)."""

    def _main(self, mod, argv: list[str]) -> tuple[str, str]:
        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", argv), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            mod.main()
        return out.getvalue(), err.getvalue()

    def _bench(self, *args: str):
        import subprocess
        return subprocess.run(["uv", "run", "-q", str(SCRIPTS / "bench.py"), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_dish_names_list_and_elev_band(self):
        import sun
        self.assertEqual(sun._sat("HotBird"), 13.0)
        self.assertEqual(sun._sat("chinasat-9"), 92.2)
        self.assertEqual(sun._sat("-5"), -5.0)
        with self.assertRaises(sun.argparse.ArgumentTypeError):
            sun._sat("bogus")
        out, _ = self._main(sun, ["sun.py", "dish", "--list"])
        self.assertEqual(len(out.strip().splitlines()), len(sun.SATELLITES))
        out, _ = self._main(sun, ["sun.py", "dish", "--at", "45.46,9.19", "--sat", "hotbird"])
        self.assertIn("13°E (hotbird): azimuth 174.7°, elevation angle 37.5°", out)
        out, _ = self._main(sun, ["sun.py", "dish", "--lat", "31.2", "--sat", "92.2", "--azimuth", "215"])
        self.assertIn("longitude range 108.9° ~ 115.6°", out)
        out, _ = self._main(sun, ["sun.py", "dish", "--lat", "31.2", "--sat", "92.2", "--azimuth", "215", "--elev", "45"])
        self.assertIn("longitude range 111.6° ~ 115.6°", out)
        with tempfile.TemporaryDirectory() as t:
            pts = Path(t) / "band.json"
            out, _ = self._main(sun, ["sun.py", "dish", "--sat", "hotbird", "--azimuth", "174.7", "--elev", "37.5", "--az-tol", "1", "--el-tol", "1",
                                      "--points", str(pts)])
            band = list(json.loads(pts.read_text(encoding="utf-8")).values())
            self.assertIn("latitude", out)
            self.assertTrue(any(abs(la - 45.5) <= 0.5 and abs(lo - 9.0) <= 1.0 for la, lo in band), band[:5])   # Milan lies in the band

    def test_sun_half_day_label_tz_error_and_out_note(self):
        import sun
        from datetime import datetime, timezone
        paris, sydney = 2.35, 151.21
        self.assertTrue(sun._before_solar_noon(paris, datetime(2024, 7, 1, 10, 0, tzinfo=timezone.utc)))      # 12:00 CEST
        self.assertFalse(sun._before_solar_noon(paris, datetime(2024, 7, 1, 13, 20, tzinfo=timezone.utc)))    # 15:20 CEST
        self.assertTrue(sun._before_solar_noon(sydney, datetime(2024, 6, 30, 0, 10, tzinfo=timezone.utc)))    # 10:10 AEST
        self.assertFalse(sun._before_solar_noon(sydney, datetime(2024, 7, 1, 3, 40, tzinfo=timezone.utc)))    # 13:40 AEST
        with self.assertRaises(SystemExit) as cm:
            sun._zone("Europe/Pariss")
        self.assertIn("Unknown time zone", str(cm.exception))
        with tempfile.TemporaryDirectory() as t:
            img = Path(t) / "band.jpg"
            out, err = self._main(sun, ["sun.py", "locate", "--time", "2024-06-01T12:00", "--tz", "Europe/Paris", "--elev", "60",
                                        "--bbox", "48,2,49,3", "--step", "0.5", "--out", str(img)])
            self.assertIn("--out needs --mosaic", err)
            self.assertFalse(img.exists())
            self.assertIn("matched_points", out)

    def test_fov_aspect_and_intersect_error_exit(self):
        import geo
        out, _ = self._main(geo, ["geo.py", "fov", "26"])
        self.assertTrue(out.startswith("4:3 long_side=67.3deg short_side=53.1deg"), out)
        out, _ = self._main(geo, ["geo.py", "fov", "26", "--aspect", "3:2"])
        self.assertTrue(out.startswith("3:2 long_side=69.4deg short_side=49.6deg"), out)
        out, _ = self._main(geo, ["geo.py", "fov", "26", "--aspect", "16:9"])
        self.assertTrue(out.startswith("16:9 long_side=71.9deg short_side=44.4deg"), out)
        with self.assertRaises(SystemExit) as cm:
            self._main(geo, ["geo.py", "fov", "26", "--aspect", "wide"])
        self.assertEqual(cm.exception.code, 2)
        for argv in (["--sight1", "48.85,2.29", "--sight2", "48.86,2.33@300"], ["--align1", "48.85,2.29", "--sight2", "48.86,2.33@300"],
                     ["--sight1", "48.85,2.29@abc", "--sight2", "48.86,2.33@300"]):
            err = io.StringIO()
            with self.assertRaises(SystemExit) as cm, contextlib.redirect_stderr(err), patch.object(sys, "argv", ["geo.py", "intersect", *argv]):
                geo.main()
            self.assertEqual(cm.exception.code, 2)
            self.assertEqual(len(err.getvalue().strip().splitlines()), 1, err.getvalue())
            self.assertIn("malformed --", err.getvalue())

    def test_frame_anchor_gives_heading(self):
        import geo
        # landmark due east of the camera; f = (W/2)/tan(hfov/2), heading = bearing - atan((px - W/2)/f)
        anchor = ["--anchor", "A:0,0.01:px=750", "--width", "1000"]
        out, _ = self._main(geo, ["geo.py", "frame", "--at", "0,0", "--anchor", "A:0,0.01:px=500", "--width", "1000", "--hfov", "60"])
        self.assertIn("heading 90.0°", out)                                    # centred landmark: heading is its bearing
        out, _ = self._main(geo, ["geo.py", "frame", "--at", "0,0", *anchor, "--hfov", "90"])
        self.assertIn("heading 63.43°", out)                                   # 90 - atan(250/500)
        out, _ = self._main(geo, ["geo.py", "frame", "--at", "0,0", "--at", "0.0002,0", *anchor, "--hfov", "60:90"])
        self.assertEqual(out.count("heading is between"), 2, out)              # one heading range per --at
        self.assertIn("as field of view goes 60.0°→90.0°, heading is between 73.9°→63.43°", out)   # 90 - atan(250/866)
        self.assertIn("heading is between 75.04°→64.58°", out)                 # 22 m north: the bearing to the landmark moves

    def test_bearings_far_is_the_footprint_radius_from_the_pin(self):
        import geo
        pin = (33.5132, 126.5247)
        # a 160 m x 100 m venue outline round the pin: a closed way (LineString) and a relation's outer ring (MultiLineString)
        ring = [geo.dest(geo.dest(pin, 0, dy), 90, dx) for dx, dy in ((-60, -40), (100, -40), (100, 60), (-60, 60), (-60, -40))]
        line = [[lon, lat] for lat, lon in ring]
        gj = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"name": "Way"}, "geometry": {"type": "LineString", "coordinates": line}},
            {"type": "Feature", "properties": {"name": "Relation"}, "geometry": {"type": "MultiLineString", "coordinates": [line[:3], line[2:]]}}]}
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "venue.geojson"
            path.write_text(json.dumps(gj), encoding="utf-8")
            out, _ = self._main(geo, ["geo.py", "bearings", "--at", f"{pin[0]},{pin[1]}", "--geojson", str(path)])
        lines = out.splitlines()
        self.assertEqual(lines[1].split(), ["brg", "span", "dist", "far", "h/lvl", "name/kind"])
        rows = {cols[-1]: cols for cols in (ln.split() for ln in lines[2:] if ln.strip())}
        self.assertEqual(sorted(rows), ["Relation", "Way"], out)
        for cols in rows.values():
            self.assertEqual((int(cols[2]), int(cols[3])), (72, 117), out)    # nearest vertex (-60, -40), farthest (100, 60)

    def test_mark_and_sheet_labels_draw_non_latin_glyphs(self):
        import tiles
        from geolib.cli import font
        from PIL import Image, ImageDraw

        def drawn(text):
            im = Image.new("L", (80, 24))
            ImageDraw.Draw(im).text((2, 2), text, fill=255, font=font(14, text))
            return im.tobytes()
        ll = [33.5132, 126.5247]
        with tempfile.TemporaryDirectory() as t:
            base = Path(t) / "m.png"
            Image.new("RGB", (512, 512)).save(base)
            x, y = tiles.geo.ll2px(17, *ll)
            base.with_suffix(".json").write_text(json.dumps({"zoom": 17, "origin_tile": [int(x // 256) - 1, int(y // 256) - 1]}), encoding="utf-8")
            for a, b in (("제주", "서울"), ("東京", "大阪"), ("ไทย", "ลาว")):
                with self.subTest(a):
                    if drawn(a) == drawn(b):
                        self.skipTest(f"no font with {a!r} glyphs on this machine")
                    ims = []
                    for lab in (a, b):
                        tiles.mark(base, {lab: ll}, Path(t) / "out.png", True)
                        ims.append(Image.open(Path(t) / "out.png").tobytes())
                    self.assertTrue(ims[0] != ims[1], f"{a} and {b} drew the same boxes")
                    pages = []
                    with patch.object(tiles, "cell_image", lambda *a, **k: Image.new("RGB", (128, 128))):
                        for i, lab in enumerate((a, b)):
                            tiles.sheet({lab: ll}, 17, 128, 1, Path(t) / f"s{i}.png", "google", None, Path(t))
                            pages.append(Image.open(Path(t) / f"s{i}.png").tobytes())
                    self.assertTrue(pages[0] != pages[1], f"{a} and {b} drew the same boxes on the sheet")

    def test_peaks_report_plateau_centre(self):
        import imgprep
        d = [0.0] * 40
        for i in range(10, 15):
            d[i] = 50.0                      # 5 px wide flat-top pier: its centre column, not the right edge
        d[30] = 40.0
        self.assertEqual(imgprep._peaks(d, 5, 10), [(12, 50.0), (30, 40.0)])
        self.assertEqual(imgprep._peaks(d, 5, 45), [(12, 50.0)])

    def test_opendata_group_cells(self):
        import opendata
        pts = {f"a{i}": [40.73 + i * 1e-5, -73.99] for i in range(4)}
        pts.update({f"b{i}": [40.74, -73.98 + i * 1e-5] for i in range(2)})
        pts["c"] = {"lat": 40.70, "lon": -74.0}
        g = opendata.group_points(pts, 80, 3)
        self.assertEqual(list(g), ["g1 x4"])
        self.assertAlmostEqual(g["g1 x4"][0], 40.730015, places=5)
        self.assertEqual(list(opendata.group_points(pts, 80, 2)), ["g1 x4", "g2 x2"])
        self.assertEqual(opendata.group_points(pts, 80, 5), {})

    def test_bench_satscan_and_match_dry_run(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            cells, k = [], 0
            for r in range(10):                  # 10×10 grid, 100 m pitch near 48.86° N, ranked in reading order
                for c in range(10):
                    k += 1
                    cells.append({"cell": f"r{r:02d}c{c:02d}", "lat": 48.86 + r * 0.0009, "lon": 2.30 + c * 0.00137, "score": 1 - k / 100, "rank": k})
            truth = {"rank3": [cells[2]["lat"] + 0.0001, cells[2]["lon"]], "rank25": [cells[24]["lat"], cells[24]["lon"] + 0.0002], "far": [49.0, 3.0]}
            (d / "cells.json").write_text(json.dumps(cells), encoding="utf-8")
            (d / "truth.json").write_text(json.dumps(truth), encoding="utf-8")
            r = self._bench("satscan", "--cells", str(d / "cells.json"), "--truth", str(d / "truth.json"), "--out", str(d / "m.json"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("recall@20 1/3, recall@30 2/3, recall@100 2/3; median rank 14.0; unmatched 1", r.stdout)
            m = json.loads((d / "m.json").read_text(encoding="utf-8"))
            self.assertEqual([p["rank"] for p in m["per_point"]], [3, 25, None])
            self.assertAlmostEqual(m["match_m"], 75, delta=2)
            panos = {"A": {"wgs": [48.86, 2.30]}, "B": {"wgs": [48.8601, 2.30]}, "C": {"wgs": [48.8602, 2.3001]}, "D": {"wgs": [48.9, 2.4]}}
            (d / "panos.json").write_text(json.dumps(panos), encoding="utf-8")
            r = self._bench("match", "--panos", str(d / "panos.json"), "--radius", "50", "--n", "8", "--dry-run")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("3 planned cases of 3 eligible sites", r.stdout)
            self.assertEqual(r.stdout.count("candidates within 50 m"), 3)


if __name__ == "__main__":
    unittest.main(verbosity=1)
