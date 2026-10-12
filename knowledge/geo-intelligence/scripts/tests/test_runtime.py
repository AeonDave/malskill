#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy", "streetlevel"]
# ///
"""Offline runtime regressions. Run: uv run scripts/tests/test_runtime.py"""
from __future__ import annotations

import asyncio
import http.server
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import re
import math
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import types
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geolib import net as _net
from geolib import browser as _browser
from geolib import pano as _pano   # import-time side effect under test: bounds requests' default timeout
import baidu_pano
import doctor
from geolib import coverage as cov
import gsv
import osm
import poi
import revimg


class NetworkTests(unittest.TestCase):
    def test_route_precedence(self):
        with patch.dict(os.environ, {"GEO_PROXY": "http://localhost:8123"}, clear=True):
            self.assertEqual(_net.resolve_proxy(), "http://localhost:8123")
            self.assertEqual(_net.resolve_proxy("http://localhost:8234"), "http://localhost:8234")
            self.assertIsNone(_net.resolve_proxy("direct"))
            self.assertIsNone(_net.resolve_proxy(""))
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://localhost:9999"}, clear=True):
            self.assertIsNone(_net.resolve_proxy())

    @unittest.skipUnless(shutil.which("curl"), "curl required")
    def test_curl_reaches_direct_and_explicit_proxy_despite_ambient_settings(self):
        paths = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                paths.append(self.path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with patch.dict(os.environ, {"HTTP_PROXY": "http://127.0.0.1:1", "http_proxy": "http://127.0.0.1:1",
                                         "ALL_PROXY": "http://127.0.0.1:1", "NO_PROXY": "*", "GEO_PROXY": "http://127.0.0.1:1"}):
                self.assertEqual(_net.fetch_bytes(base + "/direct", "direct"), b"ok")
                self.assertEqual(_net.fetch_bytes("http://example.invalid/proxied", base), b"ok")
            self.assertEqual(paths, ["/direct", "http://example.invalid/proxied"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_model_route_overrides_ambient_variables(self):
        with patch.dict(os.environ, {"GEO_PROXY": "http://chosen:8080", "https_proxy": "http://old:8080", "NO_PROXY": "*"}, clear=True):
            _net.model_proxy_env()
            self.assertEqual(os.environ["HTTPS_PROXY"], "http://chosen:8080")
            if os.name == "nt":
                # Windows environ keys are case-insensitive: the stale lowercase entry is the overwritten upper one.
                self.assertEqual(os.environ["https_proxy"], "http://chosen:8080")
            else:
                self.assertNotIn("https_proxy", os.environ)
            self.assertNotIn("NO_PROXY", os.environ)
            _net.model_proxy_env("direct")
            self.assertNotIn("HTTPS_PROXY", os.environ)
            self.assertEqual(os.environ["NO_PROXY"], "*")

    def test_baidu_near_forwards_proxy(self):
        with patch.object(baidu_pano, "fetch_bytes", return_value=b'{"content":null}') as fetch:
            self.assertIsNone(baidu_pano.near(35, 110, proxy="http://chosen:8080"))
            self.assertEqual(fetch.call_args.args[1], "http://chosen:8080")

    def test_all_poi_sources_forward_proxy(self):
        with patch.object(poi, "_curl", return_value='{}') as fetch:
            poi.search_so("school", None, 2, "direct")
            self.assertEqual(fetch.call_args.kwargs["proxy"], "direct")
            poi.search_sug("school", "http://chosen:8080")
            self.assertEqual(fetch.call_args.kwargs["proxy"], "http://chosen:8080")
        with patch.object(poi, "_curl", return_value='[]') as fetch:
            poi.search_osm("school", None, 2, "http://chosen:8080", "us")
            self.assertEqual(fetch.call_args.kwargs["proxy"], "http://chosen:8080")

    def test_intake_forwards_route_to_both_engines(self):
        import intake
        from PIL import Image
        commands = []
        def run(cmd, **kwargs):
            commands.append(cmd)
            return 0, "", ""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            photo = root / "photo.jpg"
            Image.new("RGB", (100, 100), "white").save(photo)
            # Preparation writes files used by intake; run the actual small local helpers.
            original = intake._run
            def local_or_search(cmd, **kwargs):
                if any(str(part).endswith("revimg.py") for part in cmd):
                    return run(cmd, **kwargs)
                return original([sys.executable, *cmd[2:]], **kwargs)
            with patch.object(intake, "_run", side_effect=local_or_search), patch.object(sys, "argv", ["intake.py", str(photo), "--out-dir", str(root / "out"), "--no-ocr", "--max-variants", "1", "--proxy", "direct"]):
                intake.main()
            self.assertEqual(len(commands), 2)
            for cmd in commands:
                self.assertEqual(cmd[cmd.index("--proxy") + 1], "direct")
            self.assertEqual({cmd[cmd.index("--engines") + 1] for cmd in commands}, {"baidu", "yandex"})


class BrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_chromium_fallback_uses_same_route(self):
        browser = object()
        launch = AsyncMock(side_effect=[RuntimeError("Chrome absent"), browser])
        p = SimpleNamespace(chromium=SimpleNamespace(launch=launch))
        actual, label = await _browser.launch_browser(p, "socks5h://localhost:8123")
        self.assertIs(actual, browser)
        self.assertEqual(label, "Playwright Chromium")
        for call in launch.call_args_list:
            self.assertEqual(call.kwargs["proxy"]["server"], "socks5://localhost:8123")
        self.assertEqual(launch.call_args_list[0].kwargs["channel"], "chrome")
        self.assertNotIn("channel", launch.call_args_list[1].kwargs)

    async def test_explicit_direct_overrides_saved_browser_proxy(self):
        launch = AsyncMock(return_value=object())
        p = SimpleNamespace(chromium=SimpleNamespace(launch=launch))
        with patch.dict(os.environ, {"GEO_PROXY": "http://old:8080"}):
            await _browser.launch_browser(p, "direct")
        self.assertNotIn("proxy", launch.call_args.kwargs)
        self.assertIn("--no-proxy-server", launch.call_args.kwargs["args"])

    async def test_both_browsers_missing_gives_install_fix(self):
        p = SimpleNamespace(chromium=SimpleNamespace(launch=AsyncMock(side_effect=RuntimeError("missing"))))
        with self.assertRaisesRegex(RuntimeError, "uvx playwright install chromium"):
            await _browser.launch_browser(p, "direct")

    async def test_reverse_search_all_engines_get_selected_route(self):
        browser = SimpleNamespace(new_context=AsyncMock(), close=AsyncMock())
        manager = AsyncMock()
        manager.__aenter__.return_value = object()
        # Avoid requiring Playwright in this offline test's environment.
        fake = SimpleNamespace(async_playwright=lambda: manager)
        with tempfile.TemporaryDirectory() as folder, patch.dict(sys.modules, {"playwright.async_api": fake}), patch.object(revimg, "launch_browser", AsyncMock(return_value=(browser, "test"))) as launch, patch.object(revimg, "_text", AsyncMock(return_value={"links": []})), patch.object(revimg, "_baidu", AsyncMock(return_value={"links": []})) as baidu, patch.object(revimg, "_yandex", AsyncMock(return_value={"links": []})):
            await revimg.run([Path("photo.jpg")], ["baidu", "yandex"], Path(folder), "direct", ["school"], ["bing"])
            self.assertEqual(launch.await_count, 3)
            self.assertTrue(all(call.args[1] == "direct" for call in launch.await_args_list))
            self.assertEqual(baidu.await_args.args[-1], "direct")


class DoctorTests(unittest.TestCase):
    def test_probe_distinguishes_transport_failure_and_service_block(self):
        for returncode, stdout, status in [(0, "200", "PASS"), (0, "429", "WARN"), (7, "000", "FAIL")]:
            with self.subTest(status=status), patch.object(doctor.subprocess, "run", return_value=SimpleNamespace(returncode=returncode, stdout=stdout)):
                row = doctor.probe(("service", "https://example.invalid"), "direct")
                self.assertEqual(row["status"], status)

    def test_local_checks_do_not_probe_network_or_print_proxy_credentials(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(doctor, "browser_check", AsyncMock(return_value=doctor.check("browser", "PASS", "ready"))), patch.object(doctor, "probe") as probe, patch.dict(os.environ, {"GEO_PROXY": "http://user:secret@localhost:8080"}):
            report = doctor.diagnose(False, None)
            probe.assert_not_called()
            self.assertTrue(report["ok"])
            self.assertNotIn("secret", json.dumps(report, ensure_ascii=False))
            self.assertEqual(report["connection"], "configured proxy")


QH = '[out:json][timeout:180];(area["name"="青海省"];area["name:zh"="青海省"];area["name:zh-Hans"="青海省"];)->.searchArea;nwr["power"="line"](area.searchArea);out geom tags;'
LINE = {"type": "way", "id": 1, "geometry": [{"lat": 37.7, "lon": 95.3}, {"lat": 37.8, "lon": 95.4}], "tags": {"power": "line"}}


def count(n):
    return {"elements": [{"type": "count", "tags": {"total": str(n)}}]}


class OverpassMirrorTests(unittest.TestCase):
    """One mirror answered a whole-province --area query with a clean empty result while others had thousands of lines; it got cached."""

    def setUp(self):
        osm._blocked_until.clear()          # 429/406 back-off state is per process

    def run_with(self, replies, ql=QH):
        calls = []

        def post(ep, q, proxy, timeout):
            calls.append(ep)
            return replies(ep, q)

        with tempfile.TemporaryDirectory() as d, patch.object(osm, "_post", side_effect=post), patch.object(osm.time, "sleep"), \
                patch.dict(os.environ, {"GEO_OVERPASS_URL": ""}):
            data = osm.run(ql, None, Path(d))
            cached = list(Path(d).glob("*.json"))
        return data, calls, cached

    def test_empty_from_one_mirror_is_checked_on_another(self):
        data, calls, cached = self.run_with(lambda ep, q: ({"elements": []} if ep == osm.ENDPOINTS[0] else {"elements": [LINE]}, ""))
        self.assertEqual(len(data["elements"]), 1)
        self.assertEqual(calls, osm.ENDPOINTS[:2])
        self.assertEqual(len(cached), 1)

    def test_empty_confirmed_by_two_mirrors_is_cached(self):
        data, calls, cached = self.run_with(lambda ep, q: ({"elements": []}, ""))
        self.assertEqual(data["elements"], [])
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(cached), 1)

    def test_unconfirmed_empty_is_returned_but_not_cached(self):
        data, calls, cached = self.run_with(lambda ep, q: ({"elements": []}, "") if ep == osm.ENDPOINTS[0] else (None, "503"))
        self.assertEqual(data["elements"], [])
        self.assertEqual(cached, [])
        self.assertEqual(len(calls), len(osm.ENDPOINTS))           # one round, no retry sleeps

    def test_zero_area_count_needs_a_second_mirror(self):
        ql = '[out:json][timeout:120];(area["name"="青海省"];)->.a;.a out count;'
        data, _, _ = self.run_with(lambda ep, q: (count(0) if ep == osm.ENDPOINTS[0] else count(1), ""), ql)
        self.assertEqual(data["elements"][0]["tags"]["total"], "1")

    def test_bbox_empty_is_trusted(self):
        ql = '[out:json][timeout:180];nwr["power"="line"](37.6,95.2,37.8,95.4);out geom tags;'
        _, calls, cached = self.run_with(lambda ep, q: ({"elements": []}, ""), ql)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(cached), 1)

    def test_failure_names_every_mirror(self):
        replies = {osm.ENDPOINTS[0]: (None, "HTTP 406: Not Acceptable"), osm.ENDPOINTS[1]: (None, "HTTP 500: Internal Server Error"),
                   osm.ENDPOINTS[2]: (None, "HTTP 504: server too busy")}
        with self.assertRaises(SystemExit) as cm:
            self.run_with(lambda ep, q: replies[ep])
        for code in ("406", "500", "504"):
            self.assertIn(code, str(cm.exception))

    def test_error_remark_not_cached(self):
        def replies(ep, q):
            if ep == osm.ENDPOINTS[0]:
                return {"elements": [], "remark": "runtime error: Query timed out"}, ""
            return {"elements": [LINE]}, ""
        data, _, cached = self.run_with(replies)
        self.assertEqual(len(data["elements"]), 1)
        self.assertEqual(len(cached), 1)


    def test_rate_limited_mirror_is_backed_off_and_env_mirror_goes_first(self):
        calls = []

        def post(ep, q, proxy, timeout):
            calls.append(ep)
            return (None, "HTTP 429: Too Many Requests") if ep == osm.ENDPOINTS[0] else ({"elements": [LINE]}, "")
        with tempfile.TemporaryDirectory() as d, patch.object(osm, "_post", side_effect=post), patch.object(osm.time, "sleep"), \
                patch.dict(os.environ, {"GEO_OVERPASS_URL": ""}):
            osm.run('[out:json];node(1);out;', None, Path(d))
            osm.run('[out:json];node(2);out;', None, Path(d))
        self.assertEqual(calls.count(osm.ENDPOINTS[0]), 1)          # not asked again inside the back-off window
        with patch.dict(os.environ, {"GEO_OVERPASS_URL": "https://mine.example/api/interpreter, " + osm.ENDPOINTS[0]}):
            eps = osm.endpoints()
        self.assertEqual(eps[0], "https://mine.example/api/interpreter")
        self.assertEqual(len(eps), len(osm.ENDPOINTS) + 1)


def _coverage(panos: list[tuple[str, float, float]]) -> str:
    """A coverage tile reply in the layout photometa/ac/v1 returns; no panoramas gives the empty-tile layout."""
    if not panos:
        return ")]}'\n" + json.dumps([None, None, [["ChA0YTkw", [None, None, [None, None, 40.0, -40.0]]]]])
    rows = [[[[2, pid], None, [[None, None, la, lo], [19.2, None, 63.4], [45.9, 0.27, 1.5]]], [27, 113]] for pid, la, lo in panos]
    return ")]}'\n" + json.dumps([None, [None, rows]])


class CoverageTests(unittest.TestCase):
    PID = "77-Z-M-G0QlSNisjusa5DA"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def world(self, panos):
        """_curl stand-in serving each z17 tile only the panoramas inside it; records requested tiles."""
        asked = []

        def curl(url, proxy, out=None, data=None):
            x, y = map(int, re.search(r"!1i(\d+)!2i(\d+)", url).groups())
            asked.append((x, y))
            inside = [(pid, la, lo) for pid, la, lo in panos
                      if tuple(int(v // 256) for v in gsv.geo.ll2px(17, la, lo)) == (x, y)]
            return _coverage(inside).encode()
        return curl, asked

    def test_empty_tile_vs_failed_lookup(self):
        with patch.object(cov, "_curl", return_value=_coverage([]).encode()):
            self.assertEqual(gsv.tile_panos(1, 1, None, self.cache), [])
        with patch.object(cov, "_curl", return_value=_coverage([(self.PID, 51.44, 5.47)]).encode()):
            self.assertEqual(gsv.tile_panos(2, 2, None, self.cache), [(self.PID, 51.44, 5.47)])
        for bad in ("<html>429 Too Many Requests</html>", "", ")]}'\n<html>429 Too Many Requests</html>",
                    ")]}'\n[3,\"Invalid request\"]", ")]}'\n{\"error\": 1}"):
            with patch.object(cov, "_curl", return_value=bad.encode()), self.assertRaises(gsv.ServiceError):
                gsv.tile_panos(3, 3, None, self.cache)

    def test_failed_reply_is_not_cached(self):
        bad = ")]}'\n<html>429 Too Many Requests</html>"
        with patch.object(cov, "_curl", return_value=bad.encode()), self.assertRaises(gsv.ServiceError):
            gsv.tile_panos(5, 5, None, self.cache)
        self.assertEqual([f.name for f in self.cache.iterdir()], [])
        good = _coverage([(self.PID, 51.44, 5.47)]).encode()
        with patch.object(cov, "_curl", return_value=good) as m:
            self.assertEqual(len(gsv.tile_panos(5, 5, None, self.cache)), 1)
            self.assertEqual(m.call_count, 1)  # retried, not served from cache
            self.assertEqual(len(gsv.tile_panos(5, 5, None, self.cache)), 1)
            self.assertEqual(m.call_count, 1)  # a valid reply is cached
        # an error reply left in the cache by an older version is fetched again
        (self.cache / "cov17_6_6.txt").write_text(bad, encoding="utf-8")
        with patch.object(cov, "_curl", return_value=good) as m:
            self.assertEqual(len(gsv.tile_panos(6, 6, None, self.cache)), 1)
            self.assertEqual(m.call_count, 1)

    def test_disappearing_coverage_cache_is_refetched(self):
        cached = self.cache / "cov17_7_7.txt"
        cached.write_text(")]}'\n<html>429 Too Many Requests</html>", encoding="utf-8")
        read_text = Path.read_text

        def read(path, *args, **kwargs):
            if path == cached:
                path.unlink()  # another worker removed a stale entry before this read
            return read_text(path, *args, **kwargs)

        good = _coverage([(self.PID, 51.44, 5.47)]).encode()
        with patch.object(Path, "read_text", read), patch.object(cov, "_curl", return_value=good) as fetch:
            self.assertEqual(gsv.tile_panos(7, 7, None, self.cache), [(self.PID, 51.44, 5.47)])
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(gsv._coverage_rows(cached.read_text(encoding="utf-8")), gsv._coverage_rows(good.decode()))

    def test_shared_coverage_tile_uses_one_fetch(self):
        for stale in (False, True):
            with self.subTest(stale=stale):
                cached = self.cache / "cov17_8_8.txt"
                if stale:
                    cached.write_text(")]}'\n<html>429 Too Many Requests</html>", encoding="utf-8")
                fetching, release, started = threading.Event(), threading.Event(), threading.Event()
                good = _coverage([(self.PID, 51.44, 5.47)]).encode()

                def curl(*args, **kwargs):
                    fetching.set()
                    if not release.wait(5):
                        raise RuntimeError("test did not release coverage request")
                    return good

                def second():
                    started.set()
                    return gsv.tile_panos(8, 8, None, self.cache)

                with patch.object(cov, "_curl", side_effect=curl) as fetch, ThreadPoolExecutor(2) as ex:
                    first = ex.submit(gsv.tile_panos, 8, 8, None, self.cache)
                    try:
                        self.assertTrue(fetching.wait(5))
                        other = ex.submit(second)
                        self.assertTrue(started.wait(5))
                        with self.assertRaises(TimeoutError):
                            other.result(timeout=0.1)
                    finally:
                        release.set()
                    expected = [(self.PID, 51.44, 5.47)]
                    self.assertEqual(first.result(timeout=5), expected)
                    self.assertEqual(other.result(timeout=5), expected)
                    self.assertEqual(fetch.call_count, 1)
                cached.unlink()

    def test_targets_reports_failed_lookups(self):
        pts = self.cache / "pts.json"
        pts.write_text(json.dumps({"church": [51.44, 5.47]}), encoding="utf-8")
        out = self.cache / "t.index.json"
        argv = ["gsv.py", "targets", "--points", str(pts), "--out", str(out), "--cache", str(self.cache / "c")]
        with patch.object(cov, "_curl", return_value=b"<html>429 Too Many Requests</html>"), \
                patch.dict(os.environ, {}), patch.object(sys, "argv", argv), patch("sys.stdout", new=io.StringIO()) as stdout, \
                patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit) as e:
            gsv.main()
        self.assertIn("lookup failed", str(e.exception.code))
        self.assertIn("0 targets without a panorama", stdout.getvalue())
        self.assertIn("1 lookups failed", stdout.getvalue())

    def _edge_target(self, lat):
        """A target 1 px inside the eastern edge of its z17 tile."""
        x, y = gsv.geo.ll2px(17, lat, 5.0)
        tx = int(x // 256)
        tlat, tlon = gsv.geo.px2ll(17, (tx + 1) * 256 - 1, y)
        return tx, tlat, tlon

    def _east(self, lat, lon, metres):
        return lon + math.degrees(metres / (gsv.geo._R * math.cos(math.radians(lat))))

    def test_radius_wider_than_one_tile(self):
        tx, lat, lon = self._edge_target(51.5)
        plon = self._east(lat, lon, 250)
        self.assertEqual(int(gsv.geo.ll2px(17, lat, plon)[0] // 256), tx + 2)  # outside the old 3x3 block
        curl, asked = self.world([(self.PID, lat, plon)])
        with patch.object(cov, "_curl", side_effect=curl):
            got = gsv.panos_around(lat, lon, 12, 300, 2, 15, None, self.cache)
        self.assertEqual([g[0] for g in got], [self.PID])
        self.assertAlmostEqual(got[0][3], 250, delta=1)
        self.assertIn(tx + 2, {a[0] for a in asked})
        with patch.object(cov, "_curl", side_effect=curl):  # the exact distance filter still applies
            self.assertEqual(gsv.panos_around(lat, lon, 12, 200, 2, 15, None, self.cache), [])

    def test_high_latitude_default_radius(self):
        tx, lat, lon = self._edge_target(78.2)
        plon = self._east(lat, lon, 69)
        self.assertEqual(int(gsv.geo.ll2px(17, lat, plon)[0] // 256), tx + 2)
        curl, _ = self.world([(self.PID, lat, plon)])
        with patch.object(cov, "_curl", side_effect=curl):
            got = gsv.panos_around(lat, lon, 12, 70, 2, 15, None, self.cache)
        self.assertEqual([g[0] for g in got], [self.PID])

    def test_tile_range_stays_small(self):
        self.assertLessEqual(len(gsv.tiles_around(51.5, 5.0, 70)), 4)  # a 70 m radius spans at most 2x2 tiles of ~190 m
        tiles = gsv.tiles_around(0.0, 179.9999, 300)  # wraps across the antimeridian
        self.assertTrue(all(0 <= x < 2 ** 17 for x, _ in tiles))
        self.assertIn(0, {x for x, _ in tiles})

class StreetViewNearTests(unittest.TestCase):
    """gsv.near on the coverage engine: an empty tile is "no panorama", an unreadable reply is a failed lookup."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"GEOINT_CACHE": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_empty_coverage_is_none_and_failure_raises(self):
        with patch.object(cov, "_curl", return_value=_coverage([]).encode()):
            self.assertIsNone(gsv.near(49.2161, -123.1093, 50, "direct"))
        for i, bad in enumerate(("<html>blocked</html>", "", ")]}'\n[3,\"Invalid request\"]"), 1):
            with patch.object(cov, "_curl", return_value=bad.encode()), self.assertRaises(gsv.ServiceError):
                gsv.near(49.2161 + i * 0.3, -123.1093, 50, "direct")   # fresh tiles: valid replies are cached

    def test_found_panorama_gets_metadata(self):
        pid = "Z4kP7jsHKunVOqfsg_khyw"
        meta = {"id": pid, "wgs": [49.21598, -123.10927], "date": "2024-05", "country_code": "CA"}
        with patch.object(cov, "_curl", return_value=_coverage([(pid, 49.21598, -123.10927)]).encode()), \
                patch.object(gsv.SL, "metadata", return_value=dict(meta)):
            res = gsv.near(49.2161, -123.1093, 50, "direct")
        self.assertEqual(res["id"], pid)
        self.assertEqual(res["date"], "2024-05")
        self.assertLess(res["distance_m"], 50)


class DeviceTests(unittest.TestCase):
    """geolib.cli.device: a script's --device, else GEOINT_DEVICE, else cuda → mps → DirectML → cpu; one picker for every model script."""

    @staticmethod
    def torch(cuda=False, mps=False):
        t = types.ModuleType("torch")
        t.device = lambda name: f"torch.device({name})"
        t.cuda = SimpleNamespace(is_available=lambda: cuda)
        t.backends = SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps))
        return t

    def pick(self, env, torch, directml=None, **kw):
        """directml: None = torch_directml not installed, else the object its device() returns."""
        from geolib import cli
        dml = None
        if directml is not None:
            dml = types.ModuleType("torch_directml")
            dml.device = lambda: directml
        with patch.dict(sys.modules, {"torch": torch, "torch_directml": dml}), patch.dict(os.environ, env):
            if "GEOINT_DEVICE" not in env:
                os.environ.pop("GEOINT_DEVICE", None)
            return cli.device(**kw)

    def test_env_cpu_wins_over_available_gpus(self):
        self.assertEqual(self.pick({"GEOINT_DEVICE": "cpu"}, self.torch(cuda=True, mps=True), directml="dml:0"), "torch.device(cpu)")

    def test_invalid_env_is_a_one_line_error(self):
        with self.assertRaises(SystemExit) as cm:
            self.pick({"GEOINT_DEVICE": "tpu"}, self.torch())
        self.assertIn("GEOINT_DEVICE='tpu'", str(cm.exception))
        self.assertEqual(len(str(cm.exception).splitlines()), 1)

    def test_auto_order_cuda_mps_directml_cpu(self):
        self.assertEqual(self.pick({}, self.torch(cuda=True, mps=True), directml="dml:0"), "torch.device(cuda)")
        self.assertEqual(self.pick({}, self.torch(mps=True), directml="dml:0"), "torch.device(mps)")
        self.assertEqual(self.pick({}, self.torch(), directml="dml:0"), "dml:0")
        self.assertEqual(self.pick({}, self.torch()), "torch.device(cpu)")

    def test_directml_requested_explicitly(self):
        self.assertEqual(self.pick({"GEOINT_DEVICE": "directml"}, self.torch(cuda=True), directml="dml:0"), "dml:0")
        with self.assertRaises(SystemExit) as cm:
            self.pick({"GEOINT_DEVICE": "directml"}, self.torch(cuda=True))
        self.assertIn("torch_directml", str(cm.exception))

    def test_cuda_cpu_only_models_fall_back_to_cpu(self):
        # calib.py (GeoCalib, float64 linear algebra): GEOINT_DEVICE=cpu|cuda honoured, mps/directml → cpu with a note
        with patch("sys.stderr", new=io.StringIO()) as err:
            self.assertEqual(self.pick({"GEOINT_DEVICE": "mps"}, self.torch(mps=True), allow_mps=False), "torch.device(cpu)")
        self.assertIn("using cpu", err.getvalue())
        self.assertEqual(self.pick({"GEOINT_DEVICE": "cuda"}, self.torch(cuda=True), allow_mps=False), "torch.device(cuda)")
        self.assertEqual(self.pick({}, self.torch(mps=True), directml="dml:0", allow_mps=False), "torch.device(cpu)")

    def test_script_flag_beats_env_and_auto_defers_to_env(self):
        self.assertEqual(self.pick({"GEOINT_DEVICE": "cpu"}, self.torch(cuda=True), want="cuda"), "torch.device(cuda)")
        self.assertEqual(self.pick({"GEOINT_DEVICE": "cpu"}, self.torch(cuda=True), want="auto"), "torch.device(cpu)")

    def test_every_model_script_uses_the_shared_picker(self):
        scripts = Path(__file__).resolve().parents[1]
        for name in ("prior.py", "detect.py", "calib.py", "sat_scan.py", "match.py"):
            self.assertIn("from geolib.cli import device", (scripts / name).read_text(encoding="utf-8"), name)
        megaloc = (scripts / "geolib" / "megaloc.py").read_text(encoding="utf-8")
        self.assertIn("from .cli import device as _pick", megaloc)
        self.assertNotIn("torch.backends.mps.is_available() else", megaloc)   # the old private order (mps before cuda)


class PanoTimeoutTests(unittest.TestCase):
    def test_requests_without_timeout_get_the_default(self):
        import requests
        self.assertTrue(getattr(requests.Session.request, "_geoint_timeout", False))   # importing geolib.pano bound the real one
        seen = []

        def fake(self_, method, url, *args, **kw):
            seen.append(kw.get("timeout"))
            return "ok"

        with patch.object(requests.Session, "request", fake):
            self.assertTrue(_pano.bound_requests_timeout())
            self.assertTrue(_pano.bound_requests_timeout())                 # idempotent: one wrapper
            requests.Session().request("GET", "http://example.invalid/")
            requests.Session().request("GET", "http://example.invalid/", timeout=5)   # explicit timeouts win
            requests.get("http://example.invalid/")                           # module-level API goes through Session.request
        self.assertEqual(seen, [_pano.HTTP_TIMEOUT_S, 5, _pano.HTTP_TIMEOUT_S])
        self.assertEqual(_pano.HTTP_TIMEOUT_S, 60)


class GazetteerNameTests(unittest.TestCase):
    """An English or romanised name finds the local relation (name, name:en, int_name, official_name); coarsest admin_level first."""
    PARENT = {"type": "relation", "id": 3464353, "tags": {"name": "深圳市", "name:en": "Shenzhen", "admin_level": "5", "boundary": "administrative"},
              "bounds": {"minlat": 22.44, "minlon": 113.75, "maxlat": 22.87, "maxlon": 114.63}}
    VILLAGE = {"type": "relation", "id": 99, "tags": {"name": "深圳村", "name:en": "Shenzhen", "admin_level": "8", "boundary": "administrative"},
               "bounds": {"minlat": 22.50, "minlon": 113.90, "maxlat": 22.51, "maxlon": 113.91}}

    def fake_run(self, queries):
        def run(ql, proxy, cache):
            queries.append(ql)
            if f'rel({self.PARENT["id"]});map_to_area' in ql:          # children listing inside the parent
                kids = [{"type": "relation", "id": 10 + i, "tags": {"name": n, "admin_level": "6", "boundary": "administrative"},
                         "bounds": {"minlat": 22.5 + i * 0.1, "minlon": 113.8, "maxlat": 22.6 + i * 0.1, "maxlon": 114.5}}
                        for i, n in enumerate(("南山区", "福田区", "罗湖区"))]
                return {"elements": kids}
            return {"elements": [self.VILLAGE, self.PARENT]}
        return run

    def test_english_name_resolves_to_the_local_relation(self):
        import gazetteer
        queries = []
        with patch.object(gazetteer.osm, "run", side_effect=self.fake_run(queries)), patch("sys.stderr", new=io.StringIO()) as err:
            rows = gazetteer.find_relation("Shenzhen", None, Path("unused"))
            parent, kids = gazetteer.children("Shenzhen", None, Path("unused"), None, None)
        for tag in ("name", "name:en", "int_name", "official_name"):
            self.assertIn(f'rel["{tag}"="Shenzhen"]["boundary"="administrative"];', queries[0])
        self.assertEqual([r["name"] for r in rows], ["深圳市", "深圳村"])       # admin_level 5 before 8
        self.assertEqual(parent["name"], "深圳市")
        self.assertEqual([k["name"] for k in kids], ["南山区", "福田区", "罗湖区"])
        self.assertIn('"Shenzhen" → OSM relation 深圳市, admin_level 5', err.getvalue())
        with patch.object(gazetteer.osm, "run", side_effect=self.fake_run(queries)):
            gazetteer.find_relation("Nanshan", None, Path("unused"), within="Shenzhen", level=6)
        self.assertIn('rel["name:en"="Shenzhen"]["boundary"="administrative"];', queries[-1])
        self.assertIn(");map_to_area->.p;", queries[-1])
        self.assertIn('rel(area.p)["int_name"="Nanshan"]["boundary"="administrative"]["admin_level"="6"];', queries[-1])


if __name__ == "__main__":
    unittest.main()
