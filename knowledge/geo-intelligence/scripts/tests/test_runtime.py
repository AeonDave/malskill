#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy", "streetlevel", "torch"]
#
# [tool.uv.sources]
# torch = { index = "pytorch-cpu" }
#
# [[tool.uv.index]]
# name = "pytorch-cpu"
# url = "https://download.pytorch.org/whl/cpu"
# explicit = true
# ///
"""Offline runtime regressions. Run: uv run scripts/tests/test_runtime.py"""
from __future__ import annotations

import contextlib
import http.server
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import re
import math
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import types
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geolib import net as _net
from geolib import browser as _browser
from geolib import pano as _pano   # import-time side effect under test: bounds requests' default timeout
from geolib import accel
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

    def test_baidu_sheet_always_writes_its_index(self):
        rows = [{"id": "09002200121902131010000012345", "heading": 45.0, "pitch": 10, "fov": 80}]
        with tempfile.TemporaryDirectory() as d:
            spec, out = Path(d) / "spec.json", Path(d) / "cands_sheet.jpg"
            spec.write_text(json.dumps(rows), encoding="utf-8")
            argv = ["baidu_pano.py", "sheet", "--spec", str(spec), "--out", str(out)]
            with patch.object(baidu_pano, "cells", return_value=[Image.new("RGB", (8, 8))]),                     patch.object(baidu_pano, "sheet") as draw, patch.object(sys, "argv", argv), patch("sys.stdout", new=io.StringIO()):
                baidu_pano.main()
            self.assertEqual(draw.call_count, 1)                                          # one page from a spec
            # the street check knows a panorama sheet by the index beside it
            self.assertEqual(json.loads(out.with_suffix(".index.json").read_text(encoding="utf-8")), rows)

    def test_all_poi_sources_forward_proxy(self):
        with patch.object(poi, "_curl", return_value='{}') as fetch:
            poi.search_so("school", None, 2, "direct")
            self.assertEqual(fetch.call_args.kwargs["proxy"], "direct")
            poi.search_sug("school", "http://chosen:8080")
            self.assertEqual(fetch.call_args.kwargs["proxy"], "http://chosen:8080")
        with patch.object(poi, "_curl", return_value='[]') as fetch:
            poi.search_osm("school", None, 2, "http://chosen:8080", "us")
            self.assertEqual(fetch.call_args.kwargs["proxy"], "http://chosen:8080")

    @staticmethod
    def searched(cmd: list[str]) -> list[str]:
        """The image arguments of a revimg.py command line."""
        i = next(k for k, part in enumerate(cmd) if str(part).endswith("revimg.py"))
        return cmd[i + 1:cmd.index("--out-dir")]

    @staticmethod
    def run_intake(root: Path, *extra: str, guess: str = "", failed_engine: str | None = None) -> tuple[Path, list[list[str]]]:
        """intake.main() on a white 100x100 photo: the small local helpers run for real (they write the files intake reads);
        revimg is a recorder that writes one result JSON per image and engine, labelled `guess`. Returns the photo and the
        revimg commands."""
        import intake
        photo = root / "photo.jpg"
        Image.new("RGB", (100, 100), "white").save(photo)
        commands = []
        original = intake._run

        def local_or_search(cmd, **kwargs):
            if not any(str(part).endswith("revimg.py") for part in cmd):
                return original([sys.executable, *cmd[2:]], **kwargs)
            commands.append(cmd)
            rev_dir, engine = Path(cmd[cmd.index("--out-dir") + 1]), cmd[cmd.index("--engines") + 1]
            if engine == failed_engine:
                return 1, "", "engine unavailable"
            for img in NetworkTests.searched(cmd):
                (rev_dir / f"{Path(img).stem}_{engine}.json").write_text(json.dumps({"guess": [guess] if guess else []}),
                                                                         encoding="utf-8")
            return 0, "", ""
        argv = ["intake.py", str(photo), "--out-dir", str(root / "intake"), "--no-ocr", *extra]
        with patch.object(intake, "_run", side_effect=local_or_search), patch.object(sys, "argv", argv), \
                patch("sys.stdout", new=io.StringIO()):
            intake.main()
        return photo, commands

    def test_intake_forwards_route_to_both_engines(self):
        with tempfile.TemporaryDirectory() as folder:
            photo, commands = self.run_intake(Path(folder), "--max-variants", "1", "--proxy", "direct")
            self.assertEqual(len(commands), 2)
            for cmd in commands:
                self.assertEqual(cmd[cmd.index("--proxy") + 1], "direct")
                self.assertEqual(self.searched(cmd)[0], str(photo))                 # without --box the original goes first
            self.assertEqual({cmd[cmd.index("--engines") + 1] for cmd in commands}, {"baidu", "yandex"})

    def test_intake_box_searches_only_crops(self):
        # recon already searched the full frame on both engines: a --box rerun searches the crop's variants only
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            photo, commands = self.run_intake(root, "--box", "10,10,60,60", "--max-variants", "2")
            self.assertEqual(len(commands), 2)
            for cmd in commands:
                self.assertNotIn(str(photo), cmd)
                images = self.searched(cmd)
                self.assertEqual(len(images), 2)
                self.assertTrue(all(Path(p).name.startswith("box1_") for p in images), images)
            self.assertFalse((root / "intake" / "edges").exists())
            self.assertEqual(list((root / "intake" / "variants").glob("full_*")), [])
            md = (root / "intake" / "intake.md").read_text(encoding="utf-8")
            self.assertIn("Only the --box crops were searched here (recon or a run without --box searched the full frame); "
                          "compare each crop's sheet with the crop.", md)
            self.assertNotIn("Look at the original image's sheet first", md)
            self.assertNotIn("Edge crops", md)
            self.assertIn("- Place-name labels: none", md)

    def test_intake_two_boxes_both_searched(self):
        # --box is repeatable: the variant slots go round-robin across boxes, each box's crop first
        with tempfile.TemporaryDirectory() as folder:
            _, commands = self.run_intake(Path(folder), "--box", "10,10,60,60", "--box", "40,40,90,90", "--max-variants", "2")
            self.assertEqual(len(commands), 2)
            for cmd in commands:
                self.assertEqual([Path(p).name for p in self.searched(cmd)], ["box1_crop.jpg", "box2_crop.jpg"])

    def test_intake_rerun_reports_only_this_calls_searches(self):
        # a --box rerun in the folder of a full run: the full run's results stay on disk as evidence, but the new report
        # holds only the crop's results and votes
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "intake"
            self.run_intake(Path(folder), "--max-variants", "1", guess="图中可能是：上海")
            self.assertEqual(json.loads((out / "intake.json").read_text(encoding="utf-8"))["votes"]["city"],
                             {"上海": ["baidu", "yandex"]})
            self.run_intake(Path(folder), "--box", "10,10,60,60", "--max-variants", "1", guess="图中可能是：石板路")
            report = json.loads((out / "intake.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted((e["variant"], e["engine"]) for e in report["rev"]),
                             [("box1_crop", "baidu"), ("box1_crop", "yandex")])
            self.assertEqual(report["votes"], {"city": {}, "place": {"石板路": ["baidu/box1_crop", "yandex/box1_crop"]}})
            self.assertNotIn("上海", (out / "intake.md").read_text(encoding="utf-8"))
            self.assertTrue((out / "rev" / "photo_baidu.json").is_file())

    def test_intake_full_rerun_uses_current_variants_after_a_crop(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.run_intake(root, "--box", "10,10,60,60", "--max-variants", "2")
            photo, commands = self.run_intake(root, "--max-variants", "2")
            for cmd in commands:
                images = self.searched(cmd)
                self.assertEqual(images[0], str(photo))
                self.assertEqual(len(images), 3)
                self.assertTrue(all(Path(p).name.startswith("full_") for p in images[1:]), images)
            self.assertTrue((root / "intake/variants/box1_crop.jpg").is_file())

    def test_intake_failed_crop_does_not_search_an_earlier_crop(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.run_intake(root, "--box", "10,10,60,60", "--max-variants", "1", guess="Tokyo")
            previous = (root / "intake/variants/box1_crop.jpg").read_bytes()
            _, commands = self.run_intake(root, "--box", "not-a-box", "--max-variants", "1")
            data = json.loads((root / "intake/intake.json").read_text(encoding="utf-8"))
            self.assertEqual(commands, [])
            self.assertTrue(data["status"]["variants"].startswith("failed:"))
            self.assertEqual(data["rev"], [])
            self.assertEqual(data["votes"], {"city": {}, "place": {}})
            self.assertEqual(data["status"]["rev-baidu"], "not run: no crop variants prepared")
            self.assertEqual((root / "intake/variants/box1_crop.jpg").read_bytes(), previous)

    def test_intake_same_crop_rerun_drops_a_failed_engines_old_result(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.run_intake(root, "--box", "10,10,60,60", "--max-variants", "1", guess="Tokyo")
            self.run_intake(root, "--box", "10,10,60,60", "--max-variants", "1", guess="Berlin", failed_engine="baidu")
            data = json.loads((root / "intake/intake.json").read_text(encoding="utf-8"))
            self.assertEqual([(e["variant"], e["engine"]) for e in data["rev"]], [("box1_crop", "yandex")])
            self.assertEqual(data["votes"]["city"], {"Berlin": ["yandex"]})
            self.assertTrue(data["status"]["rev-baidu"].startswith("failed:"))

    def test_place_labels_are_not_presented_as_places(self):
        # _classify files any label containing 路/山/湖/寺/园/城… under "place": Baidu's 石板路 (stone paving) is a scene word,
        # so neither report may turn it into a geocoding command
        import recon
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.run_intake(root, "--max-variants", "0", guess="图中可能是：石板路")
            md = (root / "intake" / "intake.md").read_text(encoding="utf-8")
            self.assertIn("conflicting place labels don't cancel city votes", md)
            self.assertIn("- Label **石板路** (scene/object word or place name): 2 times (baidu/photo, yandex/photo); if it is a "
                          "proper name → `poi.py \"石板路\" --city <city> --region <cc>`, list every same-name place, then verify", md)
            self.assertNotIn("Specific place", md)
            summary = recon.summary(Path("photo.jpg"), root, {}, 1.0, True)
            self.assertIn("- Labels that may name a place (often a scene or object word): 石板路 (2) → `poi.py \"<name>\"` "
                          "(or web search) only for a proper name, then verify", summary)
            self.assertNotIn("Specific places named", summary)
            self.assertNotIn('poi.py "石板路"', summary)


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


class RevimgQueryTests(unittest.IsolatedAsyncioTestCase):
    QUERY = "부산 등대 & 東京/タワー #1"

    def test_query_urls_encode_non_latin_queries_for_every_engine(self):
        hosts = {"bing": ("www.bing.com", "q"), "baiduimg": ("image.baidu.com", "word"), "sogouimg": ("pic.sogou.com", "query"),
                 "naverimg": ("search.naver.com", "query"), "daumimg": ("search.daum.net", "q"),
                 "yahoojpimg": ("search.yahoo.co.jp", "p"), "yandeximg": ("yandex.com", "text"),
                 "bingimg": ("www.bing.com", "q"), "googleimg": ("www.google.com", "q")}
        self.assertEqual(set(revimg.TEXT_URL), set(hosts))
        for engine, (host, param) in hosts.items():
            with self.subTest(engine=engine):
                url = revimg.query_url(engine, self.QUERY)
                parts = urlparse(url)
                self.assertEqual((parts.scheme, parts.netloc), ("https", host))
                self.assertIn("%EB%B6%80%EC%82%B0", url)                           # UTF-8 percent-encoded Hangul
                self.assertFalse(re.search(r"[^\x21-\x7e]", url))                 # no raw space or non-ASCII left
                self.assertEqual(parse_qs(parts.query)[param], [self.QUERY])       # '&', '/', '#' stay inside the query
                self.assertFalse(parts.fragment)

    def test_country_picks_local_engines_and_explicit_list_wins(self):
        for country, engines in [("KR", ["naverimg", "daumimg"]), ("kr", ["naverimg", "daumimg"]),
                                 ("JP", ["yahoojpimg", "yandeximg", "googleimg"]), ("CN", ["baiduimg", "sogouimg"]),
                                 ("RU", ["yandeximg", "googleimg"]), ("BY", ["yandeximg", "googleimg"]),
                                 ("KZ", ["yandeximg", "googleimg"]), ("IT", ["bingimg", "yandeximg"]),
                                 ("ZZ", ["bingimg", "yandeximg"]), (None, ["bingimg", "yandeximg"])]:
            with self.subTest(country=country):
                self.assertEqual(revimg.pick_text_engines(country, None), engines)
        self.assertEqual(revimg.pick_text_engines("KR", "bing,googleimg,nope"), ["bing", "googleimg"])

    def test_search_md_engine_table_matches_the_code(self):
        text = (Path(revimg.__file__).resolve().parents[1] / "references" / "search.md").read_text(encoding="utf-8")
        rows = re.findall(r"^\| ([A-Z]{2}(?:, [A-Z]{2})*|any other, none) \| ([^|]+) \|", text, re.M)
        table = {}
        for countries, engines in rows:
            for c in countries.split(", "):
                table[c] = tuple(re.findall(r"`(\w+)`", engines))
        self.assertEqual([table.pop(k, None) for k in ("any other", "none")], [revimg.DEFAULT_ENGINES] * 2)
        self.assertEqual(table, revimg.COUNTRY_ENGINES)

    def test_cli_passes_country_engines_and_rejects_a_country_name(self):
        def cli(*argv):
            with patch.object(sys, "argv", ["revimg.py", "--query", self.QUERY, "--out-dir", "q", *argv]), \
                    patch.object(revimg, "run", return_value=[]) as run, contextlib.redirect_stdout(io.StringIO()):
                revimg.main()
            return run.call_args.args[5]
        self.assertEqual(cli("--country", "kr"), ["naverimg", "daumimg"])
        self.assertEqual(cli(), ["bingimg", "yandeximg"])
        self.assertEqual(cli("--country", "KR", "--text-engines", "bingimg"), ["bingimg"])
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cli("--country", "Korea")

    def test_only_long_queries_get_the_short_query_hint(self):
        def hint(*queries):
            argv = ["revimg.py", "--out-dir", "q", "--country", "KR"] + [a for q in queries for a in ("--query", q)]
            err = io.StringIO()
            with patch.object(sys, "argv", argv), patch.object(revimg, "run", return_value=[]),                     contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                revimg.main()
            return err.getvalue()
        self.assertIn("more than 3 words", hint("부산 해안 산책로 돌담 등대 야경", "부산 등대 빨간 철제 난간 밤"))
        self.assertNotIn("more than 3 words", hint("부산 등대", "부산 등대 빨간 철제 난간 밤"))

    def test_blocked_pages_are_recognised_and_result_pages_are_not(self):
        google = ("https://www.google.com/sorry/index?continue=https://www.google.com/search%3Fq%3Dx%26udm%3D2",
                  "About this page\nOur systems have detected unusual traffic from your computer network. This page checks to see if it's really you sending the requests, and not a robot.")
        yahoo = ("https://search.yahoo.co.jp/image/search?p=x",
                 "お知らせ\n2022年4月6日 (水) よりYahoo! JAPANは欧州経済領域（EEA）およびイギリスからご利用いただけなくなりました")
        for url, text in [google, yahoo, ("https://consent.google.com/ml?continue=https://www.google.com/search", "Before you continue to Google"),
                          ("https://yandex.com/showcaptcha?cc=1&mt=C43A", ""), ("https://image.baidu.com/search/index?word=x", "百度安全验证")]:
            with self.subTest(url=url):
                self.assertTrue(revimg._blocked(url, text))
        self.assertIn("EEA", revimg._blocked(*yahoo))
        naver = ("https://search.naver.com/search.naver?where=image&query=captcha%20consent.",
                 "NAVER\n이미지\ncaptcha 이미지검색 결과\n부산 등대 포토뉴스")
        self.assertIsNone(revimg._blocked(*naver))

    async def test_links_keep_posts_on_engine_hosts_and_drop_its_navigation(self):
        naver = [{"t": "내 블로그", "h": "https://blog.naver.com/MyBlog.naver"}, {"t": "가입한 카페", "h": "https://section.cafe.naver.com/"},
                 {"t": "도움말새 창 열림", "h": "https://help.naver.com/alias/search/word/word_35.naver"},
                 {"t": "부산 등대 기록 네이버 블로그", "h": "https://blog.naver.com/someone/223099420934"},
                 {"t": "등대 보존 포토뉴스", "h": "http://www.example-news.co.kr/news/articleView.html?idxno=1"}]
        daum = [{"t": "티스토리", "h": "https://www.tistory.com/?nil_profile=mini"}, {"t": "백과사전", "h": "https://100.daum.net/"},
                {"t": "&quot;등대&quot; 복원", "h": "https://v.daum.net/v/20220224121049494"},
                {"t": "등대 카페 후기", "h": "https://cafe.daum.net/club/MirA/827"}]
        for engine, links, kept in [("naverimg", naver, ["https://blog.naver.com/someone/223099420934", "http://www.example-news.co.kr/news/articleView.html?idxno=1"]),
                                    ("daumimg", daum, ["https://v.daum.net/v/20220224121049494", "https://cafe.daum.net/club/MirA/827"])]:
            with self.subTest(engine=engine):
                page = SimpleNamespace(url="https://results", evaluate=AsyncMock(side_effect=["NAVER", links]))
                res = await revimg._collect(page, engine)
                self.assertEqual([ln["url"] for ln in res["links"]], kept)
        self.assertEqual(res["links"][0]["title"], '"등대" 복원')

    async def test_grid_screenshots_take_a_second_slice_only_when_the_page_loaded_one(self):
        for height, names in [(2327, ["q01_daumimg.png"]), (7177, ["q01_daumimg.png", "q01_daumimg_2.png"])]:
            with self.subTest(height=height):
                page = SimpleNamespace(evaluate=AsyncMock(side_effect=lambda js: height if "scrollHeight" in js else None),
                                       wait_for_timeout=AsyncMock(), screenshot=AsyncMock())
                paths = await revimg._grid_shots(page, Path("q") / "q01_daumimg.png")
                self.assertEqual([Path(p).name for p in paths], names)
                self.assertEqual([c.kwargs["clip"]["y"] for c in page.screenshot.await_args_list], [0, revimg.SLICE][:len(names)])

    async def test_bing_no_results_page_is_an_error_not_an_empty_success(self):
        class Page:
            def __init__(self, engine, items):
                self.url = revimg.query_url(engine, "부산 등대")
                self.items, self.shots, self.closed = items, [], False
                self.goto, self.wait_for_timeout = AsyncMock(), AsyncMock()
                self.wait_for_selector = AsyncMock(side_effect=TimeoutError("li.b_algo"))

            async def evaluate(self, js):
                if "innerText.slice(0, 400)" in js:          # the block check's head
                    return ("Rewards AllAI ModeImages SafeSearch: Moderate There are no results for 부산 등대 Check your spelling"
                            if "images" in self.url else "跳至内容 全部 图片 没有与此相关的结果: 부산 등대 检查拼写或尝试其他关键字")
                return "#b_results" in js                    # Bing web's results container is there on its empty page

            async def query_selector(self, sel):
                return object() if sel in self.items else None

            def get_by_role(self, role, name):
                return SimpleNamespace(count=AsyncMock(return_value=0))

            async def screenshot(self, **kw):
                self.shots.append(kw)

            async def close(self):
                self.closed = True

        for engine in ("bingimg", "bing"):
            with self.subTest(engine=engine):
                page = Page(engine, items=())
                res = await revimg._text(SimpleNamespace(new_page=AsyncMock(return_value=page)), engine, "부산 등대", Path("q01.png"))
                self.assertIn("no results", res["error"])
                self.assertIn(engine, res["error"])
                self.assertNotIn("blocked", res)                                    # the next query still asks this engine
                self.assertNotIn("links", res)
                self.assertEqual(len(page.shots), 1)
                self.assertTrue(page.closed)

    async def test_each_query_starts_without_the_screenshots_of_an_earlier_call(self):
        browser = SimpleNamespace(new_context=AsyncMock(), close=AsyncMock())
        manager = AsyncMock()
        manager.__aenter__.return_value = object()
        fake = SimpleNamespace(async_playwright=lambda: manager)

        async def text(ctx, engine, query, shot):
            if engine == "daumimg":
                raise TimeoutError("page.goto: Timeout 60000ms exceeded")
            shot.write_bytes(b"new")                                                # one slice only
            return {"error": "a CAPTCHA", "blocked": True} if engine == "googleimg" else {"url": "u", "guess": [], "links": []}
        with tempfile.TemporaryDirectory() as folder, patch.dict(sys.modules, {"playwright.async_api": fake}),                 patch.object(revimg, "launch_browser", AsyncMock(return_value=(browser, "test"))), patch.object(revimg, "_text", text):
            out = Path(folder)
            for eng in ("naverimg", "googleimg", "daumimg"):
                for name in (f"q01_{eng}.png", f"q01_{eng}_2.png"):
                    (out / name).write_bytes(b"old query")
            results = await revimg.run([], [], out, "direct", ["new query"], ["naverimg", "googleimg", "daumimg"])
            left = sorted(p.name for p in out.glob("*.png"))
            olds = [p.name for p in out.glob("*.png") if p.read_bytes() == b"old query"]
        self.assertEqual(left, ["q01_googleimg.png", "q01_naverimg.png"])
        self.assertEqual(olds, [])
        failed = next(r for r in results if r["engine"] == "daumimg")
        self.assertIn("Timeout", failed["error"])
        self.assertNotIn("screenshot", failed)                                      # nothing was captured this call
        self.assertTrue(all("screenshot" in r for r in results if r["engine"] != "daumimg"))

    async def test_blocked_engine_is_not_retried_and_each_engine_gets_its_locale(self):
        browser = SimpleNamespace(new_context=AsyncMock(), close=AsyncMock())
        manager = AsyncMock()
        manager.__aenter__.return_value = object()
        fake = SimpleNamespace(async_playwright=lambda: manager)
        calls = []

        async def text(ctx, engine, query, shot):
            calls.append(engine)
            return {"error": "a CAPTCHA", "blocked": True} if engine == "googleimg" else {"url": "u", "guess": [], "links": []}
        with tempfile.TemporaryDirectory() as folder, patch.dict(sys.modules, {"playwright.async_api": fake}), \
                patch.object(revimg, "launch_browser", AsyncMock(return_value=(browser, "test"))), patch.object(revimg, "_text", text):
            results = await revimg.run([], [], Path(folder), "direct", ["one", "two"], ["googleimg", "naverimg"])
            self.assertEqual(calls, ["googleimg", "naverimg", "naverimg"])
            skipped = json.loads((Path(folder) / "q02_googleimg.json").read_text(encoding="utf-8"))
        self.assertIn("not retried", skipped["error"])
        self.assertNotIn("screenshot", skipped)                                    # nothing was captured
        self.assertEqual(len(results), 4)
        self.assertEqual([c.kwargs["locale"] for c in browser.new_context.await_args_list], ["en-US", "ko-KR"])


class DoctorTests(unittest.TestCase):
    def test_probe_distinguishes_transport_failure_and_service_block(self):
        for returncode, stdout, status in [(0, "200", "PASS"), (0, "429", "WARN"), (7, "000", "FAIL")]:
            with self.subTest(status=status), patch.object(doctor.subprocess, "run", return_value=SimpleNamespace(returncode=returncode, stdout=stdout)):
                row = doctor.probe(("service", "https://example.invalid"), "direct")
                self.assertEqual(row["status"], status)

    def test_local_checks_do_not_probe_network_or_print_proxy_credentials(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(doctor, "browser_check", AsyncMock(return_value=doctor.check("browser", "PASS", "ready"))), patch.object(doctor, "probe") as probe, patch.dict(os.environ, {"GEO_PROXY": "http://user:secret@localhost:8080"}),                 patch.object(doctor.accel, "detected", return_value=None):
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
        err = io.StringIO()
        with patch.object(sys, "stderr", err):
            data, calls, cached = self.run_with(lambda ep, q: ({"elements": []}, "") if ep == osm.ENDPOINTS[0] else (None, "503"))
        self.assertEqual(data["elements"], [])
        self.assertEqual(cached, [])
        self.assertEqual(len(calls), len(osm.ENDPOINTS))           # one round, no retry sleeps
        self.assertIn("Rerun once at most", err.getvalue())           # a terminal exit, not an open rerun loop
        self.assertIn('"not found in OSM (unconfirmed)" and move on', err.getvalue())

    def test_zero_area_count_needs_a_second_mirror(self):
        ql = '[out:json][timeout:120];(area["name"="青海省"];)->.a;.a out count;'
        data, _, _ = self.run_with(lambda ep, q: (count(0) if ep == osm.ENDPOINTS[0] else count(1), ""), ql)
        self.assertEqual(data["elements"][0]["tags"]["total"], "1")

    def test_bbox_and_around_empties_need_a_second_mirror(self):
        # a stale mirror answered a mall's --bbox query with elements: [] and the empty reply was cached for the whole run
        for ql in ('[out:json][timeout:180];nwr["shop"="mall"](33.509,126.520,33.517,126.530);out geom tags;',
                   '[out:json][timeout:60];nwr["amenity"="place_of_worship"](around:500,33.5132,126.5247);out center tags;'):
            data, calls, cached = self.run_with(lambda ep, q: ({"elements": []} if ep == osm.ENDPOINTS[0] else {"elements": [LINE]}, ""), ql)
            self.assertEqual(data["elements"], [LINE])
            self.assertEqual(calls, osm.ENDPOINTS[:2])
            self.assertEqual(len(cached), 1)
            _, calls, cached = self.run_with(lambda ep, q: ({"elements": []}, ""), ql)
            self.assertEqual(len(calls), 2)                                    # confirmed empty: cached
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


class GsvRenderTests(unittest.TestCase):
    """A failed `gsv.py render` wrote a grey 'render failed' JPEG and exited 0, so it looked like a valid view."""

    def test_failed_render_exits_nonzero_and_writes_nothing(self):
        pid = "CIHM0ogKEICAgIDE89qY1QE"
        for err in (RuntimeError(f"panorama {pid} not found"), ModuleNotFoundError("No module named 'streetlevel'")):
            with tempfile.TemporaryDirectory() as d:
                out = Path(d) / "v.jpg"
                argv = ["gsv.py", "render", pid, "--heading", "90", "--out", str(out), "--cache", d]
                with patch.object(gsv.SL, "equirect", side_effect=err), patch.object(sys, "argv", argv), patch.dict(os.environ), \
                        patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit) as cm:
                    gsv.main()
                self.assertIsInstance(cm.exception.code, str)                  # a message, so a non-zero exit
                self.assertIn(pid, cm.exception.code)
                self.assertFalse(out.exists())


class MatchRenderFailureTests(unittest.TestCase):
    """match.py kept a renderer's grey 'render failed' cells (info["failed"]) as candidates and wrote them into the ranking,
    so a ranking of an outage counted as the street check."""

    @staticmethod
    def rank(folder: Path, ids: list[str]) -> tuple[Path, str]:
        import numpy as np
        import match

        class Embedder:                     # no model download: every image gets the same unit vector
            def __init__(self, method):
                pass

            def embed(self, ims, multi=False, batch=32):
                return np.full((len(ims), 4 if multi else 1, 8), 8 ** -0.5, np.float32)

        def view(pid, *a, **k):
            if pid.startswith("bad"):
                raise RuntimeError("blocked")
            return Image.new("RGB", (640, 480), "green")
        items, query, out = folder / "items.json", folder / "q.jpg", folder / "r.json"
        items.write_text(json.dumps([{"id": i, "heading": 0.0, "wgs": [33.5, 126.5]} for i in ids]), encoding="utf-8")
        Image.new("RGB", (64, 48), "green").save(query)
        argv = ["match.py", "--cache", str(folder / "cache"), "rank", "--query", str(query), "--items", str(items),
                "--render", "gsv", "--refine", "none", "--out", str(out)]
        with patch.object(gsv, "view", side_effect=view), patch.object(match, "Embedder", Embedder), patch.object(sys, "argv", argv), \
                patch.object(match, "handoff"), \
                patch.dict(os.environ), patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()) as err:
            match.main()
        return out, err.getvalue()

    def test_all_failed_renders_write_no_ranking(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as cm:
                self.rank(Path(d), ["bad1", "bad2"])
            self.assertIsInstance(cm.exception.code, str)                      # a message, so a non-zero exit
            self.assertIn("every one of the 2 candidates failed to render (RuntimeError: blocked)", cm.exception.code)
            self.assertIn("`sources_check.py --only gsv`", cm.exception.code)              # the engine name selects its probes there
            import sources_check
            self.assertLessEqual({"gsv-coverage", "gsv-metadata"}, {p.key for p in sources_check.select(sources_check.build_registry(), "gsv")})
            self.assertFalse((Path(d) / "r.json").exists())
            self.assertFalse((Path(d) / "r_views").exists())

    def test_failed_renders_are_dropped_from_the_ranking(self):
        with tempfile.TemporaryDirectory() as d:
            out, err = self.rank(Path(d), ["good1", "bad1", "good2"])
            self.assertEqual(sorted(r["id"] for r in json.loads(out.read_text(encoding="utf-8"))), ["good1", "good2"])
            self.assertEqual(len(list((Path(d) / "r_views").iterdir())), 2)
            self.assertIn("1/3 candidates failed to render (first: RuntimeError: blocked), dropped", err)


class NaverTypeTests(unittest.TestCase):
    """Naver recaptures carry dtl_type 14, a PanoramaType streetlevel 0.12.12 does not know: every lookup that met one raised
    ValueError, so `pano.py list` and `coverage` showed no Naver panorama where Naver has them."""

    def test_unknown_type_in_the_timeline_keeps_the_panorama_listed(self):
        import importlib
        import pano as pano_cli
        naver = _pano._sl("naver")
        api = importlib.import_module("streetlevel.naver.api")
        lat, lon = 33.5132, 126.5247
        nearby = {"features": [{"geometry": {"coordinates": [lon, lat]}, "properties": {
            "id": "NOW", "camera_angle": [0, 90, 0], "photodate": "2025-05-01 10:00:00", "description": "", "title": "",
            "camera_altitude": 1200, "type": "3"}}]}
        around = {"panoramas": {"street": [{"id": "NEXT", "latitude": lat, "longitude": lon + 1e-4, "altitude": 12, "dtl_type": "14"}]}}
        timeline = {"timeline": {"panoramas": [["NOW", lon, lat, "3", "2025-05-01 10:00:00.0"],
                                               ["OLD", lon, lat, "14", "2019-08-01 10:00:00.0"]]}}
        with patch.object(api, "find_panorama", return_value=nearby), patch.object(api, "get_neighbors", return_value=around), \
                patch.object(api, "get_historical", return_value=timeline), patch.object(pano_cli.time, "sleep"):
            rows = pano_cli._point_lookup("naver", pano_cli.bbox_around(lat, lon, 30), 100, 10)
            found = naver.find_panorama(lat, lon)
        self.assertEqual([r["id"] for r in rows], ["NOW"])
        self.assertEqual([(h.id, h.date.year, h.panorama_type.name) for h in found.historical], [("OLD", 2019, "CAR")])
        self.assertEqual(found.neighbors.street[0].panorama_type.name, "CAR")


class PanoCacheRaceTests(unittest.TestCase):
    """`pano.py sheet` renders the bearings of one panorama on 6 threads: each downloaded it again and later threads read a
    half-written JPEG ('image file is truncated'), leaving grey cells that could hide the matching view."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)
        self.image = Image.linear_gradient("L").convert("RGB").resize((512, 256))

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def staggered(fn, n=6, gap=0.03):
        with ThreadPoolExecutor(n) as ex:
            futs = []
            for _ in range(n):
                futs.append(ex.submit(fn))
                time.sleep(gap)
            return [f.result(timeout=20) for f in futs]

    def fake_google(self, calls):
        def find(pid):
            calls.append(pid)
            time.sleep(0.2)
            return SimpleNamespace(id=pid, heading=0.5)
        return SimpleNamespace(find_panorama_by_id=find, get_panorama=lambda p, zoom: self.image)

    def test_one_download_per_panorama(self):
        made = []

        def make():
            made.append(1)
            time.sleep(0.2)
            return self.image
        with patch.object(_pano, "CACHE", self.cache):
            arrays = self.staggered(lambda: _pano._cached_equirect("naver:P1:1:cube", make))
        self.assertEqual(len(made), 1)
        self.assertTrue(all(a.shape == (256, 512, 3) for a in arrays))
        found = []
        with patch.object(gsv.SL, "streetview", return_value=self.fake_google(found)):
            views = self.staggered(lambda: gsv.SL.equirect("G1", self.cache / "google", 3))
        self.assertEqual(found, ["G1"])
        self.assertTrue(all(eq.shape == (256, 512, 3) and abs(h - math.degrees(0.5)) < 1e-9 for eq, h in views))
        self.assertEqual([p.name for p in self.cache.rglob("*.part")], [])

    def test_reader_never_opens_a_half_written_panorama(self):
        orig = Image.Image.save

        def slow_save(im, fp, format=None, **params):
            buf = io.BytesIO()
            orig(im, buf, format or "JPEG", **params)
            data = buf.getvalue()
            with open(fp, "wb") as fh:
                fh.write(data[:len(data) // 2])
                fh.flush()
                time.sleep(0.3)
                fh.write(data[len(data) // 2:])

        def reader(folder, done, seen, errors):
            while True:                     # another process: it reads whatever *.jpg exists, outside this process's locks
                last = done.is_set()
                for q in folder.rglob("*.jpg"):
                    try:
                        with Image.open(q) as im:
                            im.load()
                        seen.append(q.name)
                    except OSError as e:
                        errors.append(f"{q.name}: {e}")
                if last:
                    return
                time.sleep(0.005)

        for name, write in (("sl", lambda: _pano._cached_equirect("kakao:P2:1", lambda: self.image)),
                            ("google", lambda: gsv.SL.equirect("G2", self.cache / "google", 3))):
            (self.cache / name).mkdir(parents=True, exist_ok=True)
            done, seen, errors = threading.Event(), [], []
            t = threading.Thread(target=reader, args=(self.cache / name, done, seen, errors))
            t.start()
            try:
                with patch.object(Image.Image, "save", slow_save), patch.object(_pano, "CACHE", self.cache), \
                        patch.object(gsv.SL, "streetview", return_value=self.fake_google([])):
                    write()
            finally:
                done.set()
                t.join(10)
            self.assertEqual(errors, [], name)
            self.assertTrue(seen, name)


@unittest.skipUnless(shutil.which("curl"), "curl required")
class PanoUrlPublicationTests(unittest.TestCase):
    """A URL prefetch must publish complete images without exposing curl's open output to another reader."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)
        buf = io.BytesIO()
        Image.effect_noise((1024, 512), 80).convert("RGB").save(buf, "JPEG", quality=95)
        self.body = buf.getvalue()

    def tearDown(self):
        self.tmp.cleanup()

    @contextlib.contextmanager
    def server(self, respond):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(handler):
                handler.send_response(200)
                handler.send_header("Content-Length", str(len(self.body)))
                handler.end_headers()
                respond(handler)

            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)

    def test_prefetch_never_exposes_partial_file_to_reader(self):
        sent, release = threading.Event(), threading.Event()
        requests = []

        def respond(handler):
            requests.append(handler.path)
            if len(requests) == 1:
                handler.wfile.write(self.body[:len(self.body) // 2])
                handler.wfile.flush()
                sent.set()
                release.wait(8)
                handler.wfile.write(self.body[len(self.body) // 2:])
            else:
                handler.wfile.write(self.body)

        with self.server(respond) as base, patch.object(_pano, "CACHE", self.cache), \
                patch.dict(os.environ, {"GEO_PROXY": "direct"}):
            url = base + "/same.jpg"
            with ThreadPoolExecutor(1) as ex:
                future = ex.submit(_pano.fetch_many, [url], proxy="direct", timeout=10)
                try:
                    self.assertTrue(sent.wait(4), "curl did not request the first image")
                    # Wait until curl has flushed its output: before the fix this is the final JPEG, afterwards a .part.
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline:
                        if any(p.stat().st_size >= len(self.body) // 4 for p in self.cache.rglob("*") if p.is_file()):
                            break
                        time.sleep(0.01)
                    im = _pano._open(url)
                    self.assertEqual(im.size, (1024, 512))
                finally:
                    release.set()
                self.assertIn(url, future.result(timeout=12))
            self.assertEqual(_pano.read_image(_pano._cache_path(url)).size, (1024, 512))
            self.assertEqual(list(self.cache.rglob("*.part")), [])

    def test_failed_download_does_not_hide_a_successful_peer(self):
        def respond(handler):
            body = self.body if handler.path == "/good.jpg" else self.body[:len(self.body) // 2]
            handler.wfile.write(body)
            handler.wfile.flush()
            handler.close_connection = True          # a short body with a full Content-Length: curl exits 18

        with self.server(respond) as base, patch.object(_pano, "CACHE", self.cache):
            good, cut = base + "/good.jpg", base + "/cut.jpg"
            got = _pano.fetch_many([good, cut], parallel=2, timeout=3, proxy="direct")
            self.assertEqual(set(got), {good})
            self.assertEqual(_pano.read_image(got[good]).size, (1024, 512))
            self.assertFalse(_pano._cache_path(cut).exists())
            self.assertEqual(list(self.cache.rglob("*.part")), [])
            self.assertEqual(list(self.cache.rglob("*.curl")), [])

    def test_distinct_downloads_stay_parallel(self):
        active, peak = [0], [0]
        guard = threading.Lock()

        def respond(handler):
            with guard:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            try:
                time.sleep(0.1)
                handler.wfile.write(self.body)
            finally:
                with guard:
                    active[0] -= 1

        with self.server(respond) as base, patch.object(_pano, "CACHE", self.cache):
            urls = [base + f"/{i}.jpg" for i in range(4)]
            got = _pano.fetch_many(urls, parallel=4, timeout=3, proxy="direct")
            self.assertEqual(set(got), set(urls))
            self.assertGreaterEqual(peak[0], 2)

    def test_timeout_never_publishes_an_unfinished_image(self):
        def respond(handler):
            handler.wfile.write(self.body[:len(self.body) // 2])
            handler.wfile.flush()
            time.sleep(0.2)                         # curl's deadline expires before the declared body is complete
            handler.close_connection = True

        with self.server(respond) as base, patch.object(_pano, "CACHE", self.cache):
            url = base + "/timeout.jpg"
            self.assertEqual(_pano.fetch_many([url], timeout=0.05, proxy="direct"), {})
            self.assertFalse(_pano._cache_path(url).exists())
            self.assertEqual(list(self.cache.rglob("*.part")), [])
            self.assertEqual(list(self.cache.rglob("*.curl")), [])


class PanoCacheHealTests(unittest.TestCase):
    """A panorama JPEG or sidecar left broken in the cache (a killed process, a full disk, a writer from before the atomic
    writes) failed every later read and was never downloaded again."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)
        self.image = Image.linear_gradient("L").convert("RGB").resize((512, 256))
        self.calls, self.offline = [], False

    def tearDown(self):
        self.tmp.cleanup()

    def fetch(self, what):
        self.calls.append(what)
        if self.offline:
            raise RuntimeError("offline")

    def sl(self):
        """The streetlevel cache of Kakao, Naver and the others: one JPEG per panorama."""
        with patch.object(_pano, "CACHE", self.cache):
            return _pano._cached_equirect("kakao:P1:1", lambda: self.fetch("make") or self.image)

    def google(self):
        """The Google cache: a JPEG and a JSON sidecar with the heading."""
        sv = SimpleNamespace(find_panorama_by_id=lambda pid: self.fetch("find") or SimpleNamespace(id=pid, heading=0.5),
                             get_panorama=lambda p, zoom: self.image)
        with patch.object(gsv.SL, "streetview", return_value=sv):
            eq, heading = gsv.SL.equirect("G1", self.cache / "google", 3)
        self.assertAlmostEqual(heading, math.degrees(0.5))
        return eq

    def url(self):
        """The download cache of the manifest kinds that name a URL (equirect, cube-strip, photo, cube faces)."""
        import numpy as np

        def fetch(u):                       # as fetch_many: a cached file that is not empty is not downloaded again
            path = _pano._cache_path(u)
            if not (path.exists() and path.stat().st_size):
                self.fetch("download")
                path.parent.mkdir(parents=True, exist_ok=True)
                self.image.save(path, "JPEG")
            return path
        with patch.object(_pano, "CACHE", self.cache), patch.object(_pano, "fetch", fetch):
            return np.asarray(_pano._open("https://example.org/pano/1.jpg"))

    def cases(self):
        return (("sl", self.sl, lambda: next((self.cache / "sl").glob("*.jpg"))),
                ("google", self.google, lambda: self.cache / "google" / "G1_z3.jpg"),
                ("url", self.url, lambda: next((self.cache / "url").rglob("*.jpg"))))

    @staticmethod
    def truncate(p: Path) -> None:
        data = p.read_bytes()
        p.write_bytes(data[:len(data) // 2])

    def test_valid_cache_is_read_without_a_rebuild(self):
        for name, read, _ in self.cases():
            with self.subTest(cache=name):
                self.calls.clear()
                self.assertEqual(read().shape, (256, 512, 3))
                self.assertEqual(read().shape, (256, 512, 3))
                self.assertEqual(len(self.calls), 1)

    def test_truncated_jpeg_is_rebuilt_once(self):
        for name, read, jpg in self.cases():
            with self.subTest(cache=name):
                self.calls.clear()
                read()
                self.truncate(jpg())
                self.assertEqual(read().shape, (256, 512, 3))
                read()
                self.assertEqual(len(self.calls), 2)                            # one rebuild, then the healed file is read

    def test_corrupt_sidecar_is_rebuilt_once(self):
        self.google()
        (self.cache / "google" / "G1_z3.json").write_text('{"head', encoding="utf-8")
        self.assertEqual(self.google().shape, (256, 512, 3))
        self.google()
        self.assertEqual(self.calls, ["find", "find"])

    def test_failed_rebuild_raises_after_one_attempt(self):
        for name, read, jpg in self.cases():
            with self.subTest(cache=name):
                self.calls.clear()
                self.offline = False
                read()
                broken = jpg()
                self.truncate(broken)
                self.offline = True
                with self.assertRaisesRegex(RuntimeError, "offline"):
                    read()
                self.assertEqual(len(self.calls), 2)
                self.assertFalse(broken.exists())                               # the next run downloads it

    @unittest.skipUnless(shutil.which("curl"), "curl required")
    def test_threads_downloading_distinct_urls_each_get_their_own_image(self):
        # fetch_many wrote one curl config per process: threads downloading or healing different URLs at once (pano.py sheet,
        # sweep.py index) overwrote and deleted each other's config, so most cells failed with "download failed"
        import numpy as np
        shades = {f"/pano/{i}.jpg": 10 + i * 20 for i in range(12)}
        bodies = {}
        for path, v in shades.items():
            buf = io.BytesIO()
            Image.new("RGB", (64, 32), (v, v, v)).save(buf, "JPEG")
            bodies[path] = buf.getvalue()

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                body = bodies.get(self.path)
                time.sleep(0.05)                              # requests overlap, as on a real provider
                self.send_response(200 if body else 404)
                self.send_header("Content-Length", str(len(body or b"")))
                self.end_headers()
                self.wfile.write(body or b"")

            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        urls = {f"http://127.0.0.1:{server.server_port}{path}": v for path, v in shades.items()}

        def shade(u):
            try:
                return int(np.asarray(_pano._open(u))[16, 32, 0])
            except Exception as e:  # noqa: BLE001  (every failure is reported, not only the first)
                return f"{type(e).__name__}: {e}"
        try:
            with patch.object(_pano, "CACHE", self.cache), patch.dict(os.environ, {"GEO_PROXY": "direct"}):
                for state in ("missing", "truncated"):
                    with self.subTest(cache=state), ThreadPoolExecutor(6) as ex:
                        got = dict(zip(urls, ex.map(shade, urls)))
                        self.assertEqual({u: g if isinstance(g, str) or abs(g - v) > 3 else v for u, g in got.items()}, urls)
                    for u in urls:
                        self.truncate(_pano._cache_path(u))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_corrupt_apple_sidecar_is_rebuilt(self):
        # Look Around keeps its heading in a JSON sidecar beside the JPEG
        import hashlib
        stem = self.cache / "sl" / hashlib.sha1(b"apple:A1:7:4").hexdigest()
        jpg, meta = stem.with_suffix(".jpg"), stem.with_suffix(".json")
        jpg.parent.mkdir(parents=True)
        self.image.save(jpg, "JPEG")
        meta.write_text(json.dumps({"heading_rad": math.radians(-30)}), encoding="utf-8")
        la = SimpleNamespace(get_coverage_tile_by_latlon=lambda lat, lon: self.fetch("tile"))
        entry, spec = {"lat": 48.85, "lon": 2.35, "heading": 10.0}, {"pano": "A1", "build": 7, "zoom": 4}
        with patch.object(_pano, "CACHE", self.cache), patch.object(_pano, "_sl", lambda s: la), \
                patch.dict(sys.modules, {"pillow_heif": SimpleNamespace(register_heif_opener=lambda: None)}):
            eq, center = _pano._apple_equirect(entry, spec)
            self.assertEqual((eq.shape, round(center, 6), self.calls), ((256, 512, 3), 210.0, []))
            meta.write_text('{"heading', encoding="utf-8")
            self.offline = True
            with self.assertRaisesRegex(RuntimeError, "offline"):
                _pano._apple_equirect(entry, spec)
        self.assertEqual(self.calls, ["tile"])
        self.assertFalse(jpg.exists() or meta.exists())


class DeviceTests(unittest.TestCase):
    """geolib.cli.device: a script's --device, else GEOINT_DEVICE, else cuda → xpu → mps → cpu; one picker for every model script."""

    @staticmethod
    def torch(cuda=False, mps=False, xpu=False):
        t = types.ModuleType("torch")
        t.device = lambda name: f"torch.device({name})"
        t.cuda = SimpleNamespace(is_available=lambda: cuda)
        t.xpu = SimpleNamespace(is_available=lambda: xpu)
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
            for key in ("GEOINT_DEVICE", "GEOINT_GPU_CHILD"):
                if key not in env:
                    os.environ.pop(key, None)
            return cli.device(**kw)

    def test_env_cpu_wins_over_available_gpus(self):
        self.assertEqual(self.pick({"GEOINT_DEVICE": "cpu"}, self.torch(cuda=True, mps=True), directml="dml:0"), "torch.device(cpu)")

    def test_invalid_env_is_a_one_line_error(self):
        with self.assertRaises(SystemExit) as cm:
            self.pick({"GEOINT_DEVICE": "tpu"}, self.torch())
        self.assertIn("GEOINT_DEVICE='tpu'", str(cm.exception))
        self.assertEqual(len(str(cm.exception).splitlines()), 1)

    def test_auto_order_cuda_xpu_mps_cpu_never_directml(self):
        self.assertEqual(self.pick({}, self.torch(cuda=True, xpu=True, mps=True), directml="dml:0"), "torch.device(cuda)")
        self.assertEqual(self.pick({}, self.torch(xpu=True, mps=True), directml="dml:0"), "torch.device(xpu)")
        self.assertEqual(self.pick({}, self.torch(mps=True), directml="dml:0"), "torch.device(mps)")
        self.assertEqual(self.pick({}, self.torch(), directml="dml:0"), "torch.device(cpu)")    # DirectML installed, never picked

    def test_directml_request_points_to_the_gpu_environment(self):
        for env, kw in (({"GEOINT_DEVICE": "directml"}, {}), ({}, {"want": "directml"})):
            with self.subTest(env=env, kw=kw), self.assertRaises(SystemExit) as cm:
                self.pick(env, self.torch(cuda=True), directml="dml:0", **kw)
            self.assertIn(accel.GPU_CMD, str(cm.exception))
            self.assertEqual(len(str(cm.exception).splitlines()), 1)

    def test_cuda_cpu_only_models_fall_back_to_cpu(self):
        # calib.py (GeoCalib, float64 linear algebra): GEOINT_DEVICE=cpu|cuda honoured, mps/xpu → cpu with a note
        for want in ("mps", "xpu"):
            with self.subTest(want=want), patch("sys.stderr", new=io.StringIO()) as err:
                self.assertEqual(self.pick({"GEOINT_DEVICE": want}, self.torch(mps=True, xpu=True), allow_mps=False), "torch.device(cpu)")
            self.assertIn("using cpu", err.getvalue())
        self.assertEqual(self.pick({"GEOINT_DEVICE": "cuda"}, self.torch(cuda=True), allow_mps=False), "torch.device(cuda)")
        self.assertEqual(self.pick({}, self.torch(mps=True, xpu=True), directml="dml:0", allow_mps=False), "torch.device(cpu)")

    def test_gpu_child_exits_75_instead_of_running_on_the_cpu(self):
        # the GPU builds' own CPU path is far slower than the default environment's CPU torch: the parent reruns there
        child = {"GEOINT_GPU_CHILD": "1"}
        self.assertEqual(self.pick(child, self.torch(cuda=True)), "torch.device(cuda)")
        for env in (child, {**child, "GEOINT_DEVICE": "cpu"}):
            with self.subTest(env=env), self.assertRaises(SystemExit) as cm:
                self.pick(env, self.torch())
            self.assertEqual(cm.exception.code, 75)
        self.assertEqual(self.pick({}, self.torch()), "torch.device(cpu)")                  # outside the child: cpu as before

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


AMD = {"vendor": "amd", "name": "AMD Radeon RX 6900 XT", "arch": "gfx1030"}
AMD_INDEX = "https://stable.repo.amd.com/rocm/whl-next/"


class GpuCacheCase(unittest.TestCase):
    """A temporary GEOINT_CACHE (the GPU environment lives in <cache>/gpu), outside any GPU run."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        env = patch.dict(os.environ, {"GEOINT_CACHE": str(self.dir), "UV": "uv-bin"})
        env.start()
        self.addCleanup(env.stop)
        for key in ("GEOINT_DEVICE", "GEOINT_GPU_CHILD"):
            os.environ.pop(key, None)
        self.gpu = self.dir / "gpu"
        self.script = str(Path(__file__).resolve().parents[1] / "prior.py")

    def profile(self, python_exists: bool = True, env: dict | None = None) -> Path:
        py = self.gpu / "venv" / "python.exe"
        py.parent.mkdir(parents=True, exist_ok=True)
        if python_exists:
            py.write_bytes(b"")
        (self.gpu / "profile.json").write_text(json.dumps({"backend": "rocm", "python": str(py), "uv_args": ["--index", AMD_INDEX],
                                                          "torch": "2.14.0+rocm10.1.0", "env": env or {},
                                                          "created": "2026-10-13T12:00:00"}), encoding="utf-8")
        return py

    def detected(self, gpu):
        self.gpu.mkdir(parents=True, exist_ok=True)
        (self.gpu / "detected.json").write_text(json.dumps({"gpu": gpu}), encoding="utf-8")


@contextlib.contextmanager
def no_process():
    """Fails the test if the hand-off starts any process: a sync, a GPU run or a hardware detection."""
    with patch.object(accel.subprocess, "run", side_effect=AssertionError("subprocess.run")), \
            patch.object(accel.subprocess, "Popen", side_effect=AssertionError("subprocess.Popen")), \
            patch.object(accel, "detect_gpu", side_effect=AssertionError("detect_gpu")):
        yield


class AccelTests(GpuCacheCase):
    """geolib.accel: the model scripts rerun themselves in the GPU environment doctor.py --gpu builds; without it nothing changes."""

    def handoff(self, argv=("photo.jpg", "--out-dir", "prior")) -> str:
        err = io.StringIO()
        with patch.object(sys, "argv", [self.script, *argv]), patch("sys.stderr", new=err):
            accel.handoff(self.script)
        return err.getvalue()

    def test_without_a_profile_or_gpu_nothing_runs_and_nothing_prints(self):
        self.detected(None)
        with no_process():
            self.assertEqual(self.handoff(), "")

    def test_cpu_request_and_the_gpu_run_itself_return_at_once(self):
        self.profile()
        for env in ({"GEOINT_DEVICE": "cpu"}, {"GEOINT_DEVICE": " CPU "}, {"GEOINT_GPU_CHILD": "1"}):
            with self.subTest(env=env), patch.dict(os.environ, env), no_process():
                self.assertEqual(self.handoff(), "")

    def test_script_device_flag_is_read_as_cli_device_reads_it(self):
        # the script's --device unless auto, else GEOINT_DEVICE: a CPU request never syncs or starts the GPU run
        self.profile()
        for env, argv in (({}, ("photo.jpg", "--device", "cpu")), ({}, ("photo.jpg", "--device=CPU")),
                          ({"GEOINT_DEVICE": "cpu"}, ("photo.jpg", "--device", "auto"))):
            with self.subTest(env=env, argv=argv), patch.dict(os.environ, env), no_process():
                self.assertEqual(self.handoff(argv), "")
        stop = SimpleNamespace(returncode=1, stdout="", stderr="stop")
        with patch.dict(os.environ, {"GEOINT_DEVICE": "cpu"}), patch.object(accel.subprocess, "run", return_value=stop) as run:
            self.handoff(("photo.jpg", "--device", "cuda"))
        run.assert_called_once()                                                      # --device cuda outranks GEOINT_DEVICE=cpu

    def test_missing_gpu_python_is_one_line_and_runs_here(self):
        self.profile(python_exists=False)
        with no_process():
            out = self.handoff()
        self.assertEqual(len(out.strip().splitlines()), 1)
        self.assertIn("doctor.py --gpu", out)

    def test_already_in_the_gpu_python_returns(self):
        py = self.profile()
        with patch.object(sys, "executable", str(py)), no_process():
            self.assertEqual(self.handoff(), "")
        twin = self.dir / "cpu-venv-python.exe"
        os.link(py, twin)                                   # POSIX venv pythons all link to one base interpreter: not "in it"
        with patch.object(sys, "executable", str(twin)), \
                patch.object(accel.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="stop")) as run:
            self.handoff()
        run.assert_called_once()

    def test_profile_syncs_the_script_then_reruns_it_with_the_same_argv(self):
        py = self.profile()
        child = SimpleNamespace(wait=lambda: 3, kill=lambda: None, send_signal=lambda s: None)
        with patch.object(accel.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="", stderr="")) as run, \
                patch.object(accel.subprocess, "Popen", return_value=child) as popen, self.assertRaises(SystemExit) as cm:
            self.handoff()
        self.assertEqual(cm.exception.code, 3)                                        # the GPU run's exit code
        child.wait = lambda: -2                                                       # POSIX: killed by SIGINT
        with patch.object(accel.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="", stderr="")), \
                patch.object(accel.subprocess, "Popen", return_value=child), self.assertRaises(SystemExit) as cm:
            self.handoff()
        self.assertEqual(cm.exception.code, 130)                                      # what a shell reports for the direct run
        self.assertEqual(run.call_args.args[0], ["uv-bin", "pip", "install", "-q", "--python", str(py), "--index", AMD_INDEX,
                                                 "-c", str(self.gpu / "constraints.txt"), "-r", self.script])
        self.assertEqual(popen.call_args.args[0], [str(py), self.script, "photo.jpg", "--out-dir", "prior"])
        self.assertEqual(popen.call_args.kwargs["env"]["GEOINT_GPU_CHILD"], "1")

    def test_gpu_run_stays_on_the_device_the_smoke_test_chose(self):
        self.profile(env={"HIP_VISIBLE_DEVICES": "1"})                               # a Radeon listed after the Ryzen iGPU
        child = SimpleNamespace(wait=lambda: 0, kill=lambda: None, send_signal=lambda s: None)
        for env, want in (({}, "1"), ({"HIP_VISIBLE_DEVICES": "0"}, "0")):           # the operator's own setting wins
            with self.subTest(env=env), patch.dict(os.environ, env), \
                    patch.object(accel.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="", stderr="")), \
                    patch.object(accel.subprocess, "Popen", return_value=child) as popen, self.assertRaises(SystemExit):
                self.handoff()
            self.assertEqual(popen.call_args.kwargs["env"]["HIP_VISIBLE_DEVICES"], want)

    def test_failed_sync_is_one_line_and_runs_here(self):
        self.profile()
        fail = SimpleNamespace(returncode=1, stdout="", stderr="\n  × No solution found when resolving dependencies:\n  ╰─▶ Because torch==9 …\n")
        with patch.object(accel.subprocess, "run", return_value=fail), \
                patch.object(accel.subprocess, "Popen", side_effect=AssertionError("GPU run after a failed sync")):
            out = self.handoff()
        self.assertEqual(len(out.strip().splitlines()), 1)
        for part in ("No solution found", "doctor.py --gpu", "CPU"):
            self.assertIn(part, out)
        os.environ.pop("UV")
        with patch.object(accel.shutil, "which", return_value=None), \
                patch.object(accel.subprocess, "Popen", side_effect=AssertionError("GPU run without uv")):
            out = self.handoff()
        self.assertEqual(len(out.strip().splitlines()), 1)
        self.assertIn("uv", out)

    def test_gpu_run_without_a_device_returns_to_the_cpu(self):
        self.profile()
        child = SimpleNamespace(wait=lambda: accel.NO_DEVICE, kill=lambda: None, send_signal=lambda s: None)
        with patch.object(accel.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="", stderr="")), \
                patch.object(accel.subprocess, "Popen", return_value=child):
            out = self.handoff()                                                      # returns: this process runs on the CPU
        self.assertEqual(accel.NO_DEVICE, 75)
        self.assertEqual(len(out.strip().splitlines()), 1)
        self.assertIn("CPU", out)

    def test_found_gpu_without_a_profile_prints_the_build_command_once_per_run(self):
        with patch.object(accel, "detect_gpu", return_value=AMD) as det, patch.object(sys, "platform", "win32"):
            first, second = self.handoff(), self.handoff()
            self.assertEqual(det.call_count, 1)                                       # cached in <cache>/gpu/detected.json
            # one command string everywhere (doctor's Next hints): no absolute path to break on a space in the skill path
            line = ("GPU AMD Radeon RX 6900 XT found: `uv run scripts/doctor.py --gpu` builds its environment once "
                    "(~1 GB download, ~4 GB on disk); this run uses the CPU")
            self.assertEqual(first.splitlines(), [line])
            self.assertEqual(second.splitlines(), [line])
            (self.gpu / "failed.txt").write_text("smoke test: no GPU device", encoding="utf-8")
            self.assertEqual(self.handoff(), "")                                      # a failed build silences it; doctor shows why

    @unittest.skipIf(os.name == "nt", "Windows: taskkill /T and the console's Ctrl+C reach the GPU run directly")
    def test_sigterm_reaches_the_gpu_run(self):
        import signal
        sent, before = [], signal.getsignal(signal.SIGTERM)

        def wait():
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)                    # recon's timeout stops the parent
            return -signal.SIGTERM

        child = SimpleNamespace(wait=wait, kill=lambda: None, send_signal=sent.append)
        with patch.object(accel.subprocess, "Popen", return_value=child):
            self.assertEqual(accel._run_child(["py"], {}), -signal.SIGTERM)
        self.assertEqual(sent, [signal.SIGTERM])
        self.assertEqual(signal.getsignal(signal.SIGTERM), before)

    def test_ctrl_c_waits_for_the_gpu_run_to_clean_up(self):
        # the console's Ctrl+C reaches the GPU run too: killing it would skip its own cleanup (temp files, partial index)
        import signal
        killed, before = [], signal.getsignal(signal.SIGINT)

        def wait():
            signal.raise_signal(signal.SIGINT)
            return -signal.SIGINT                                                     # the child's own exit after its cleanup

        child = SimpleNamespace(wait=wait, kill=lambda: killed.append(True), send_signal=lambda s: None)
        with patch.object(accel.subprocess, "Popen", return_value=child):
            try:
                rc = accel._run_child(["py"], {})
            except KeyboardInterrupt:
                rc = "KeyboardInterrupt"
        self.assertEqual((rc, killed), (-signal.SIGINT, []))
        self.assertEqual(signal.getsignal(signal.SIGINT), before)

    def test_gpu_plan_per_platform(self):
        nv_new = {"vendor": "nvidia", "name": "NVIDIA GeForce RTX 4090", "driver": "580.65.06"}
        nv_old = {**nv_new, "driver": "566.36"}
        arc = {"vendor": "intel", "name": "Intel(R) Arc(TM) A770 Graphics"}
        for platform, gpu in (("win32", None), ("linux", None), ("darwin", None), ("linux", nv_new), ("win32", {**AMD, "arch": None})):
            with self.subTest(platform=platform, gpu=gpu):
                self.assertIsNone(accel.gpu_plan(platform, gpu))                       # Linux PyPI torch is CUDA 13: driver 580+ uses it
        for platform, gpu in (("win32", nv_new), ("win32", nv_old), ("linux", nv_old)):
            plan = accel.gpu_plan(platform, gpu)
            self.assertEqual((plan["backend"], plan["args"], plan["extra"], plan["pre"], plan["env"]),
                             ("cuda", ["--torch-backend=auto"], "", [], {}))
        win = accel.gpu_plan("win32", AMD)
        self.assertEqual((win["backend"], win["args"], win["extra"], win["pre"], win["env"]),
                         ("rocm", ["--index", AMD_INDEX], "[device-gfx1030]", ["--prerelease", "allow"], {}))
        self.assertEqual(win["gb"], 1)
        lin = accel.gpu_plan("linux", AMD)
        self.assertEqual((lin["backend"], lin["args"], lin["extra"], lin["env"]),
                         ("rocm", ["--torch-backend=auto"], "", {"UV_AMD_GPU_ARCHITECTURE": "gfx1030"}))
        xpu = accel.gpu_plan("win32", arc)
        self.assertEqual((xpu["backend"], xpu["args"]), ("xpu", ["--torch-backend=xpu"]))
        # download and installed GB of the torch stack (wheel sizes and their unpacked contents, cp312, torch 2.14)
        plans = (win, lin, xpu, accel.gpu_plan("linux", arc), accel.gpu_plan("win32", nv_old), accel.gpu_plan("linux", nv_old))
        self.assertEqual([(p["gb"], p["disk"]) for p in plans], [(1, 4), (7, 16), (1.5, 4), (2.5, 7), (2.5, 4), (4, 7)])
        self.assertEqual(accel.size_note(win), "~1 GB download, ~4 GB on disk")

    @staticmethod
    def tools(outputs):
        """The detection tools' stdout by command name; a missing name is a missing tool."""
        return patch.object(accel, "_run", side_effect=lambda cmd, timeout=20: outputs.get(cmd[0], ""))

    @staticmethod
    def clinfo(*devices):
        """clinfo as the AMD Windows driver prints it, one block per (board name, compute units, gfx target)."""
        head = ("Number of platforms:\t\t\t\t 1\n  Platform Name:\t\t\t\t AMD Accelerated Parallel Processing\n\n\n"
                f"  Platform Name:\t\t\t\t AMD Accelerated Parallel Processing\nNumber of devices:\t\t\t\t {len(devices)}\n")
        return head + "".join(f"  Device Type:\t\t\t\t\t CL_DEVICE_TYPE_GPU\n  Vendor ID:\t\t\t\t\t 1002h\n  Board name:\t\t\t\t\t {board}\n"
                              f"  Max compute units:\t\t\t\t {units}\n    Max work items[0]:\t\t\t\t 1024\n"
                              f"  Platform ID:\t\t\t\t\t 00007FF963FC1000\n  Name:\t\t\t\t\t\t {arch}\n"
                              "  Vendor:\t\t\t\t\t Advanced Micro Devices, Inc.\n" for board, units, arch in devices)

    def test_detect_reads_nvidia_smi_wmi_clinfo_rocm_and_kfd(self):
        with self.tools({"nvidia-smi": "NVIDIA GeForce RTX 4090, 580.88\n"}):
            self.assertEqual(accel.detect_gpu("win32"), {"vendor": "nvidia", "name": "NVIDIA GeForce RTX 4090", "driver": "580.88"})
        wmi = json.dumps([{"Name": "Meta Virtual Monitor", "PNPDeviceID": "ROOT\\DISPLAY\\0000"},
                          {"Name": "AMD Radeon RX 6900 XT", "PNPDeviceID": "PCI\\VEN_1002&DEV_73BF&SUBSYS_232C1458&REV_C0\\6&2D888E3C&0&00000019"}])
        clinfo = self.clinfo(("AMD Radeon RX 6900 XT", 40, "gfx1030"))
        with self.tools({"powershell": wmi, "clinfo": clinfo}):
            self.assertEqual(accel.detect_gpu("win32"), AMD)
        with self.tools({"powershell": wmi}):
            self.assertEqual(accel.detect_gpu("win32"), {**AMD, "arch": None})            # no clinfo: no gfx target, no plan
        arc = json.dumps({"Name": "Intel(R) Arc(TM) A770 Graphics", "PNPDeviceID": "PCI\\VEN_8086&DEV_56A0"})   # one adapter: an object
        with self.tools({"powershell": arc}):
            self.assertEqual(accel.detect_gpu("win32"), {"vendor": "intel", "name": "Intel(R) Arc(TM) A770 Graphics"})
        with self.tools({"powershell": json.dumps({"Name": "Intel(R) UHD Graphics 620", "PNPDeviceID": "PCI\\VEN_8086&DEV_5917"})}):
            self.assertIsNone(accel.detect_gpu("win32"))                                  # integrated graphics: no torch build
        with self.tools({"rocm_agent_enumerator": "gfx000\ngfx1100\n"}):
            self.assertEqual(accel.detect_gpu("linux"), {"vendor": "amd", "name": "AMD gfx1100", "arch": "gfx1100"})
        nodes = self.dir / "nodes"
        for node, version in (("0", 0), ("1", 90010)):
            (nodes / node).mkdir(parents=True)
            (nodes / node / "properties").write_text(f"cpu_cores_count 16\ngfx_target_version {version}\n", encoding="utf-8")
        with self.tools({}), patch.object(accel, "KFD_NODES", nodes):
            self.assertEqual(accel.detect_gpu("linux"), {"vendor": "amd", "name": "AMD gfx90a", "arch": "gfx90a"})
        with self.tools({}), patch.object(accel, "KFD_NODES", self.dir / "none"):
            self.assertIsNone(accel.detect_gpu("linux"))
            self.assertIsNone(accel.detect_gpu("darwin"))
        self.assertEqual(accel.kfd_arch("gfx_target_version 100300\n"), "gfx1030")

    def test_detect_picks_the_amd_gpu_with_the_most_compute_units(self):
        # a Ryzen iGPU next to a Radeon: name and gfx target both of the Radeon, whatever order WMI and clinfo list them in
        igpu = {"Name": "AMD Radeon(TM) Graphics", "PNPDeviceID": "PCI\\VEN_1002&DEV_164E&SUBSYS_88771043&REV_C9\\4&1A0B5A1F&0&0041"}
        dgpu = {"Name": "AMD Radeon RX 7900 XTX", "PNPDeviceID": "PCI\\VEN_1002&DEV_744C&SUBSYS_471E1849&REV_C8\\6&2D888E3C&0&00000019"}
        devices = [("AMD Radeon(TM) Graphics", 1, "gfx1036"), ("AMD Radeon RX 7900 XTX", 48, "gfx1100")]
        for cards in ([igpu, dgpu], [dgpu, igpu]):
            for listed in (devices, devices[::-1]):
                with self.subTest(wmi=cards[0]["Name"], clinfo=listed[0][0]), \
                        self.tools({"powershell": json.dumps(cards), "clinfo": self.clinfo(*listed)}):
                    self.assertEqual(accel.detect_gpu("win32"), {"vendor": "amd", "name": "AMD Radeon RX 7900 XTX", "arch": "gfx1100"})

    def test_torchvision_pairs_with_torch_minor_plus_15(self):
        self.assertEqual(accel.torchvision_spec("2.14.0+rocm10.1.0", "[device-gfx1030]"), "torchvision[device-gfx1030]>=0.29.0a0,<0.30")
        self.assertEqual(accel.torchvision_spec("2.9.1+cu126"), "torchvision>=0.24.0a0,<0.25")

    def test_model_scripts_hand_off_first_and_cpu_scripts_never(self):
        import ast
        scripts = Path(__file__).resolve().parents[1]
        for name in ("prior.py", "detect.py", "match.py", "sweep.py", "sat_scan.py"):
            tree = ast.parse((scripts / name).read_text(encoding="utf-8"))
            main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
            self.assertEqual(ast.unparse(main.body[0]), "handoff(__file__)", name)
        for name in ("calib.py", "aidet.py"):                                             # no GPU gain / ONNX on the CPU
            self.assertNotIn("handoff", (scripts / name).read_text(encoding="utf-8"), name)


class GpuDoctorTests(GpuCacheCase):
    """doctor.py: the GPU row of the report and `--gpu [remove]`."""

    def test_gpu_row_is_info_with_hardware_state_and_command(self):
        def row(gpu, platform="win32"):
            r = doctor.gpu_row(gpu, platform)
            self.assertEqual((r["name"], r["status"]), ("GPU", "INFO"))
            return r

        self.assertIn("No NVIDIA, AMD or Intel Arc GPU found", row(None)["detail"])
        self.assertIn("mps", row(None, "darwin")["detail"])
        nv = row({"vendor": "nvidia", "name": "NVIDIA GeForce RTX 4090", "driver": "580.65.06"}, "linux")
        self.assertIn("default environment", nv["detail"])
        self.assertEqual(nv["fix"], "")
        self.assertIn("clinfo", row({**AMD, "arch": None})["detail"])
        r = row(AMD)
        for part in ("AMD Radeon RX 6900 XT", "gfx1030", "CPU"):
            self.assertIn(part, r["detail"])
        self.assertEqual(r["fix"], "uv run scripts/doctor.py --gpu (~1 GB download, ~4 GB on disk, once)")
        self.gpu.mkdir(parents=True)
        (self.gpu / "failed.txt").write_text("smoke test: no GPU device", encoding="utf-8")
        r = row(AMD)
        self.assertIn("smoke test: no GPU device", r["detail"])
        self.assertIn("doctor.py --gpu", r["fix"])
        py = self.profile()
        r = row(AMD)
        for part in ("rocm", "torch 2.14.0+rocm10.1.0", "smoke test passed", "2026-10-13"):
            self.assertIn(part, r["detail"])
        self.assertEqual(r["fix"], "")
        py.unlink()
        self.assertIn("doctor.py --gpu", row(AMD)["fix"])

    def build(self, gpu, platform, smoke_rc=0, versions=("2.14.0+rocm10.1.0", "0.29.0a0+rocm10.1.0"), index=0):
        calls, out = [], io.StringIO()

        def run(cmd, **kw):
            calls.append([str(c) for c in cmd])
            if cmd[1:2] == ["-c"]:                                                        # the smoke test, in the GPU python
                ok = json.dumps({"device": "AMD Radeon RX 6900 XT", "index": index, "torch": versions[0], "matmul": 2e-7, "conv": 4e-7})
                return SimpleNamespace(returncode=smoke_rc, stdout=ok if smoke_rc == 0 else "",
                                       stderr="" if smoke_rc == 0 else "Traceback …\nRuntimeError: no GPU device visible to torch\n")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        version = dict(zip(("torch", "torchvision"), versions))
        with patch.object(doctor.accel, "detected", return_value=gpu), patch.object(sys, "platform", platform), \
                patch.object(doctor.subprocess, "run", side_effect=run), \
                patch.object(doctor, "_version", side_effect=lambda py, package: version[package]), \
                patch("sys.stdout", new=out), patch("sys.stderr", new=out):
            rc = doctor.gpu_build()
        return rc, calls, out.getvalue()

    def test_gpu_build_pins_the_pair_smoke_tests_then_writes_the_profile(self):
        rc, calls, out = self.build(AMD, "win32")
        self.assertEqual(rc, 0, out)
        venv = self.gpu / "venv"
        py = str(doctor.accel.venv_python(venv))
        cons = str(self.gpu / "constraints.txt")
        self.assertEqual(calls[0], ["uv-bin", "venv", "--clear", "--managed-python", "--python", "3.12", str(venv)])   # survives a system Python upgrade
        self.assertEqual(calls[1], ["uv-bin", "pip", "install", "--python", py, "--index", AMD_INDEX, "torch[device-gfx1030]", "numpy", "pillow"])
        self.assertEqual(calls[2], ["uv-bin", "pip", "install", "--python", py, "--index", AMD_INDEX, "--prerelease", "allow",
                                    "-c", cons, "torchvision[device-gfx1030]>=0.29.0a0,<0.30"])
        self.assertEqual(calls[3][:2], [py, "-c"])
        self.assertEqual(Path(cons).read_text(encoding="utf-8"), "torch==2.14.0+rocm10.1.0\ntorchvision==0.29.0a0+rocm10.1.0\n")
        prof = json.loads((self.gpu / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual({k: prof[k] for k in ("backend", "python", "uv_args", "torch", "env")},
                         {"backend": "rocm", "python": py, "uv_args": ["--index", AMD_INDEX], "torch": "2.14.0+rocm10.1.0",
                          "env": {"MIOPEN_LOG_LEVEL": "3"}})                               # MIOpen's per-run warnings stay out of the output
        self.assertTrue(prof["created"])
        self.assertIn("(~1 GB download, ~4 GB on disk, once)", out)
        nv = {"vendor": "nvidia", "name": "NVIDIA GeForce RTX 4090", "driver": "580.88"}
        rc, calls, out = self.build(nv, "win32", versions=("2.14.1+cu130", "0.29.1+cu130"))
        self.assertEqual(rc, 0, out)
        self.assertEqual(calls[1][5:], ["--torch-backend=auto", "torch", "numpy", "pillow"])
        prof = json.loads((self.gpu / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(prof["uv_args"], ["--torch-backend=cu130"])                      # the backend uv chose, fixed for every re-sync

    def test_gpu_build_keeps_the_gpu_runs_on_the_smoke_tested_device(self):
        # the smoke test picks the GPU with the most compute units; a later index (the Radeon after a Ryzen iGPU) is
        # recorded so the GPU runs see only that device
        nv = {"vendor": "nvidia", "name": "NVIDIA GeForce RTX 4090", "driver": "580.88"}
        for gpu, versions, env in ((AMD, ("2.14.0+rocm10.1.0", "0.29.0a0+rocm10.1.0"), {"MIOPEN_LOG_LEVEL": "3", "HIP_VISIBLE_DEVICES": "1"}),
                                   (nv, ("2.14.1+cu130", "0.29.1+cu130"), {"CUDA_VISIBLE_DEVICES": "1"})):
            with self.subTest(gpu=gpu["name"]):
                rc, calls, out = self.build(gpu, "win32", versions=versions, index=1)
                self.assertEqual(rc, 0, out)
                self.assertEqual(json.loads((self.gpu / "profile.json").read_text(encoding="utf-8"))["env"], env)

    def test_failed_smoke_test_writes_no_profile(self):
        self.profile()                                                                    # an earlier environment
        rc, calls, out = self.build(AMD, "win32", smoke_rc=1)
        self.assertEqual(rc, 1)
        self.assertFalse((self.gpu / "profile.json").exists())
        self.assertIn("no GPU device visible to torch", (self.gpu / "failed.txt").read_text(encoding="utf-8"))
        self.assertIn("CPU", out)

    def test_nothing_to_build_runs_nothing(self):
        for gpu, platform, text in ((None, "win32", "No NVIDIA, AMD or Intel Arc GPU found"), (None, "darwin", "mps"),
                                    ({"vendor": "nvidia", "name": "RTX", "driver": "580.65.06"}, "linux", "default environment")):
            with self.subTest(platform=platform):
                rc, calls, out = self.build(gpu, platform)
                self.assertEqual((rc, calls), (0, []))
                self.assertIn(text, out)
                self.assertFalse((self.gpu / "profile.json").exists())

    def test_gpu_remove_deletes_the_environment(self):
        self.profile()
        with patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(doctor.gpu_remove(), 0)
        self.assertFalse(self.gpu.exists())


class GeoCLIPGalleryTests(unittest.TestCase):
    def test_gallery_encoded_once_gives_the_per_crop_probabilities(self):
        import numpy as np
        import torch
        import prior
        F = torch.nn.functional
        torch.manual_seed(0)
        calls = []

        class ImageEncoder(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.lin = torch.nn.Linear(12, 16)

            @staticmethod
            def preprocess_image(im):
                return torch.tensor(np.asarray(im.resize((2, 2)), dtype=np.float32).reshape(1, 12) / 255)

            def forward(self, x):
                return self.lin(x)

        class LocationEncoder(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.lin = torch.nn.Linear(2, 16)

            def forward(self, gps):
                calls.append(len(gps))
                return torch.sin(self.lin(gps / 90))

        class GeoCLIP(torch.nn.Module):
            """GeoCLIP 1.2's forward: the per-crop reference path."""
            def __init__(self):
                super().__init__()
                self.image_encoder, self.location_encoder = ImageEncoder(), LocationEncoder()
                self.logit_scale = torch.nn.Parameter(torch.tensor(3.0))
                self.gps_gallery = torch.rand(64, 2) * torch.tensor([180.0, 360.0]) - torch.tensor([90.0, 180.0])

            def forward(self, image, location):
                image_features = F.normalize(self.image_encoder(image), dim=1)
                location_features = F.normalize(self.location_encoder(location), dim=1)
                return self.logit_scale.exp() * (image_features @ location_features.t())

        model = GeoCLIP().eval()
        crops = [Image.new("RGB", (8, 8), c) for c in ((200, 30, 30), (30, 200, 30), (30, 30, 200), (120, 120, 120))]
        with torch.no_grad():
            ref = sum(model(model.image_encoder.preprocess_image(c), model.gps_gallery).softmax(dim=-1)[0] for c in crops) / len(crops)
        top = torch.topk(ref, 10)
        gm = prior.GeoCLIPModel.__new__(prior.GeoCLIPModel)
        gm.torch, gm.model, gm.dev = torch, model, "cpu"
        calls.clear()
        gps, probs = gm.points(crops, 10)
        self.assertEqual(calls, [64])                                                     # the gallery is encoded once, not per crop
        np.testing.assert_allclose(probs, top.values.numpy(), rtol=0, atol=1e-6)
        np.testing.assert_array_equal(gps, model.gps_gallery.index_select(0, top.indices).numpy())


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


class PanoHistoricalMetadataTests(unittest.TestCase):
    """A discovered capture can be downloadable even when its ID lookup returns None."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        cache = patch.object(_pano, "CACHE", self.root / "cache")
        cache.start()
        self.addCleanup(cache.stop)

    @staticmethod
    def entry(service="kakao", image_path=None):
        spec = {"kind": "streetlevel", "service": service, "pano": "101", "zoom": 0, "center": 210.0}
        if image_path is not None:
            spec["image_path"] = image_path
        return {"provider": service, "id": "101", "lat": 37.5, "lon": 127.0, "heading": 30.0, "high": spec}

    def test_discovery_manifest_retains_download_metadata_at_both_levels(self):
        import pano
        captured = SimpleNamespace(id=101, lat=37.5, lon=127.0, heading=math.radians(30),
                                   date="2015-06-01", image_path="/2015/06/capture/unique")
        fake = SimpleNamespace(find_panoramas=lambda *a, **k: [captured])
        with patch.object(pano.P, "_sl", return_value=fake), patch.object(pano.time, "sleep"):
            rows = pano._point_lookup("kakao", (37.499, 126.999, 37.501, 127.001), 300, 0)
        manifest = self.root / "history.jsonl"
        _pano.write_manifest(manifest, rows)
        restored = _pano.read_manifest(manifest)[0]
        for level in ("low", "high"):
            self.assertEqual(restored[level]["image_path"], captured.image_path)
            self.assertEqual(restored[level]["center"], 210.0)

    def test_preserved_history_renders_without_an_id_lookup(self):
        fetched = []

        def get(p, zoom):
            fetched.append((p.id, p.image_path, zoom))
            return Image.new("RGB", (32, 16), "red")

        fake = SimpleNamespace(KakaoPanorama=SimpleNamespace, get_panorama=get,
                               find_panorama_by_id=lambda pid: self.fail("historical ID must not be looked up again"))
        row = self.entry(image_path="/2015/06/capture/unique")
        with patch.object(_pano, "_sl", return_value=fake):
            view = _pano.load(json.loads(json.dumps(row)), "high")
            self.assertEqual(view.heading, 210.0)
            self.assertEqual(view.render(210, 0, 60, 40, 20).size, (40, 20))
        self.assertEqual(fetched, [(101, "/2015/06/capture/unique", 0)])

    def test_missing_history_metadata_is_not_called_a_missing_panorama(self):
        fake = SimpleNamespace(find_panorama_by_id=lambda pid: None,
                               get_panorama=lambda *a, **k: self.fail("cannot download from None"))
        with patch.object(_pano, "_sl", return_value=fake), self.assertRaisesRegex(RuntimeError, "metadata") as error:
            _pano.load(self.entry(), "high")
        self.assertIn("image_path", str(error.exception))
        self.assertIn("histor", str(error.exception).lower())
        self.assertNotIn("does not exist", str(error.exception))

    def test_legacy_current_lookup_and_other_provider_path_are_unchanged(self):
        for service, path in (("kakao", None), ("mapy", "/not/a/kakao/path")):
            with self.subTest(service=service):
                calls = []
                found = object()
                fake = SimpleNamespace(find_panorama_by_id=lambda pid: calls.append(pid) or found,
                                       get_panorama=lambda p, zoom: self.assertIs(p, found) or Image.new("RGB", (32, 16)))
                with patch.object(_pano, "_sl", return_value=fake):
                    _pano.load(self.entry(service, path), "high")
                self.assertEqual(calls, [101])


class PanoSheetAndKakaoTests(unittest.TestCase):
    """Street-level sheets: pano.py list/sheet selection by capture period, sheets whose cells failed (pano, gsv, baidu),
    and the Kakao render centre."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def rows(*specs: tuple[str, str, float]) -> list[dict]:
        """Kakao manifest rows (id, date, metres north of 33.5,126.5)."""
        return [{"provider": "kakao", "id": i, "lat": 33.5 + m / 110540.0, "lon": 126.5, "heading": 0.0, "date": d,
                 "high": {"kind": "streetlevel", "service": "kakao", "pano": i, "zoom": 2, "center": 180.0}} for i, d, m in specs]

    @staticmethod
    def pano_main(*argv: str) -> tuple[str, str]:
        import pano
        with patch.object(sys, "argv", ["pano.py", *argv]), patch.dict(os.environ), patch("sys.stdout", new=io.StringIO()) as out, \
                patch("sys.stderr", new=io.StringIO()) as err:
            pano.main()
        return out.getvalue(), err.getvalue()

    @staticmethod
    def view():
        return SimpleNamespace(render=lambda *a: Image.new("RGB", (480, 320)))

    def test_kakao_center_is_opposite_the_travel_angle(self):
        # Kakao's `angle` is the travel direction and the stitched image's middle column looks back: checked against the Kakao
        # Roadview compass and OSM landmarks on pano 1206769250 (Jeju, angle 219.9) and 1198500660 (Seoul, angle 270.5)
        import pano
        p = SimpleNamespace(id=1206769250, lat=33.5156457665871, lon=126.529766754107, heading=math.radians(219.9), date=None)
        fake = SimpleNamespace(find_panoramas=lambda *a, **k: [p])
        with patch.object(pano.P, "_sl", lambda s: fake), patch.object(pano.time, "sleep"):
            rows = pano._point_lookup("kakao", (33.5150, 126.5290, 33.5162, 126.5305), 200, 5)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["heading"], 219.9, places=1)            # the travel axis `sheet --along` faces
        self.assertAlmostEqual(rows[0]["low"]["center"], 39.9, places=1)
        self.assertAlmostEqual(rows[0]["high"]["center"], 39.9, places=1)

    def test_kakao_legacy_manifest_center_is_corrected(self):
        import numpy as np
        fake = SimpleNamespace(find_panorama_by_id=lambda pid: object(), get_panorama=lambda p, zoom: None)

        def centre(service: str, heading: float, center: float | None) -> float:
            spec = {"kind": "streetlevel", "service": service, "pano": "1206769250", "zoom": 1}
            if center is not None:
                spec["center"] = center
            with patch.object(_pano, "_sl", lambda s: fake), \
                    patch.object(_pano, "_cached_equirect", lambda tag, make: np.zeros((4, 8, 3), np.float32)):
                return _pano.load({"provider": service, "id": "1206769250", "heading": heading, "high": spec}, "high").heading % 360
        for center in (219.9, 39.9, None):      # a manifest listed before the fix (centre = angle), one listed after, none
            self.assertAlmostEqual(centre("kakao", 219.9, center), 39.9, places=6, msg=center)
        self.assertEqual(centre("mapy", 120.0, 0.0), 0.0)                       # other providers keep their own centre

    def test_list_date_filter_runs_before_thin(self):
        import pano
        new, old = self.rows(("new", "2026-03", 0), ("old", "2008-10", 5))
        for listed, period, kept in (([new, old], "2008", "old"), ([old, new], "2026", "new")):
            out = self.dir / f"m{period}.jsonl"
            with patch.dict(pano.LISTERS, {"kakao": lambda bb, spacing, limit, **_: list(listed)}):
                self.pano_main("list", "--provider", "kakao", "--bbox", "33.49,126.49,33.51,126.51", "--thin", "20", "--date", period,
                               "--out", str(out))
            self.assertEqual([r["id"] for r in pano.P.read_manifest(out)], [kept])

    def test_list_limit_caps_the_manifest(self):
        # --limit went to the point-lookup listers, which ignore it: a Kakao list with --limit 1 wrote both panoramas
        import pano
        found = [SimpleNamespace(id=i, lat=33.5, lon=126.5, heading=0.0, date=None) for i in (1, 2)]
        fake = SimpleNamespace(find_panoramas=lambda *a, **k: list(found))
        for limit, n in (("1", 1), ("0", 2)):                                # 0 = no limit
            out = self.dir / f"l{limit}.jsonl"
            with patch.object(pano.P, "_sl", lambda s: fake), patch.object(pano.time, "sleep"):
                self.pano_main("list", "--provider", "kakao", "--bbox", "33.4999,126.4999,33.5001,126.5001", "--limit", limit,
                               "--out", str(out))
            self.assertEqual(len(pano.P.read_manifest(out)), n, limit)

    def test_list_near_limit_keeps_the_nearest(self):
        # the lister's grid order starts at the south-west corner: --near --limit 2 kept two edge panoramas, not the one at the point
        import pano
        listed = self.rows(("edge0", "2026-03", -343), ("edge1", "2026-03", 245), ("edge2", "2026-03", -300), ("edge3", "2026-03", 330),
                           ("centre", "2026-03", 0))
        for extra, kept in (((), ["centre", "edge1"]), (("--thin", "100"), ["centre", "edge1"])):
            out = self.dir / "near.jsonl"
            with patch.dict(pano.LISTERS, {"kakao": lambda bb, spacing, limit, **_: list(listed)}):
                self.pano_main("list", "--provider", "kakao", "--near", "33.5,126.5", "--radius", "400", "--spacing", "60", "--limit", "2",
                               *extra, "--out", str(out))
            self.assertEqual([r["id"] for r in pano.P.read_manifest(out)], kept, extra)

    def test_list_limit_stops_the_lister_only_when_no_filter_follows(self):
        # kartaview stops walking its grid at the limit; with --date, --near or --thin after it, that cut would come before the filter
        import pano
        calls = []

        def http_json(url, data=None, **k):
            calls.append(data)
            n = len(calls)
            return {"currentPageItems": [{"id": f"{n}-{i}", "lat": data["lat"], "lng": data["lng"], "heading": 0, "shot_date": "2024-05-01",
                                          "th_name": "a/b.jpg", "name": "a/b.jpg", "sequence_id": 1, "sequence_index": i}
                                         for i in range(25)]}
        bbox = "45.00,7.00,45.05,7.07"
        whole = len(pano.grid(tuple(float(v) for v in bbox.split(",")), 700))
        for extra, requests in (((), 1), (("--date", "2024"), whole), (("--thin", "5"), whole),
                                (("--near", "45.025,7.035", "--radius", "2000"), None)):
            calls.clear()
            out = self.dir / "k.jsonl"
            area = () if "--near" in extra else ("--bbox", bbox)
            with patch.object(pano, "http_json", http_json):
                self.pano_main("list", "--provider", "kartaview", *area, "--limit", "20", *extra, "--out", str(out))
            self.assertEqual(len(pano.P.read_manifest(out)), 20, extra)
            if requests:
                self.assertEqual(len(calls), requests, extra)
            else:
                self.assertGreater(len(calls), 1, extra)

    def test_sheet_date_filter_names_available_periods(self):
        import pano
        rows = self.rows(("a", "2008-10-29", 0), ("b", "2008-10-29", 10), ("c", "2008-10-29", 25))
        out = self.dir / "s.jpg"
        argv = ("sheet", "--manifest", "x.jsonl", "--near", "33.5,126.5", "--radius", "50", "--date", "2026", "--bearings", "0",
                "--out", str(out))
        with patch.object(pano.P, "read_manifest", return_value=rows), self.assertRaises(SystemExit) as cm:
            self.pano_main(*argv)
        self.assertIn("no 2026 capture in the selection (available: 2008-10)", str(cm.exception))
        self.assertFalse(out.exists())
        self.assertFalse(out.with_suffix(".index.json").exists())
        rows += self.rows(("d", "2026-03-05", 15))
        with patch.object(pano.P, "read_manifest", return_value=rows), patch.object(pano.P, "load", return_value=self.view()):
            self.pano_main(*argv)
        self.assertEqual([r["id"] for r in json.loads(out.with_suffix(".index.json").read_text(encoding="utf-8"))], ["d"])

    def test_pano_sheet_all_failed_writes_nothing(self):
        import pano
        out = self.dir / "s.jpg"
        with patch.object(pano.P, "read_manifest", return_value=self.rows(("a", "2026-03", 0), ("b", "2026-03", 10))), \
                patch.object(pano.P, "load", side_effect=RuntimeError("boom")), self.assertRaises(SystemExit) as cm:
            self.pano_main("sheet", "--manifest", "x.jsonl", "--ids", "a,b", "--bearings", "0", "--out", str(out))
        self.assertIn("every one of the 2 cells failed (RuntimeError: boom): no sheet written", str(cm.exception))
        self.assertFalse(out.exists())
        self.assertFalse(out.with_suffix(".index.json").exists())

    def test_pano_sheet_partial_failure_is_reported(self):
        import pano
        out = self.dir / "s.jpg"

        def load(entry, level):                  # by id, not by call order: the cells render on parallel threads
            if entry["id"] == "b":
                raise RuntimeError("boom")
            return self.view()
        with patch.object(pano.P, "read_manifest", return_value=self.rows(("a", "2026-03", 0), ("b", "2026-03", 10))), \
                patch.object(pano.P, "load", side_effect=load):
            _, err = self.pano_main("sheet", "--manifest", "x.jsonl", "--ids", "a,b", "--bearings", "0", "--out", str(out))
        self.assertTrue(out.exists())
        self.assertEqual(len(json.loads(out.with_suffix(".index.json").read_text(encoding="utf-8"))), 2)
        self.assertIn("1/2 cells failed (first: RuntimeError: boom); grey cells are not views", err)

    def test_gsv_sheet_all_failed_writes_nothing(self):
        out = self.dir / "s.jpg"
        blocked = patch.object(gsv.SL, "equirect", side_effect=RuntimeError("blocked"))
        with blocked, patch.dict(os.environ), patch("sys.stderr", new=io.StringIO()) as err:
            ims = gsv.cells([{"id": "x", "heading": 0}], None, self.dir)
        self.assertEqual([im.info.get("failed") for im in ims], ["RuntimeError: blocked"])
        self.assertIn("gsv render failed for x", err.getvalue())
        argv = ["gsv.py", "sheet", "--ids", "x", "--heading", "0", "--out", str(out), "--cache", str(self.dir)]
        with blocked, patch.object(gsv.SL, "metadata", return_value={}), patch.object(sys, "argv", argv), patch.dict(os.environ), \
                patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit) as cm:
            gsv.main()
        self.assertIn("every one of the 1 cells failed (RuntimeError: blocked): no sheet written", str(cm.exception))
        self.assertFalse(out.exists())
        self.assertFalse(out.with_suffix(".index.json").exists())
        pts, idx = self.dir / "pts.json", self.dir / "t.index.json"
        pts.write_text(json.dumps({"church": [51.44, 5.47]}), encoding="utf-8")
        argv = ["gsv.py", "targets", "--points", str(pts), "--out", str(idx), "--sheet", str(out), "--cache", str(self.dir)]
        with blocked, patch.object(gsv, "panos_around", return_value=[("x", 51.4402, 5.4702, 25.0)]), patch.object(sys, "argv", argv), \
                patch.dict(os.environ), patch("sys.stdout", new=io.StringIO()) as so, patch("sys.stderr", new=io.StringIO()) as se:
            gsv.main()                                                       # the exit code of targets is unchanged
        self.assertIn("every one of the 1 sheet cells failed (RuntimeError: blocked): no sheet written; the index stays the "
                      "candidate list for match.py", se.getvalue())
        self.assertNotIn(str(out), so.getvalue())
        self.assertFalse(out.exists())
        self.assertEqual(len(json.loads(idx.read_text(encoding="utf-8"))), 1)

    def test_sheet_run_with_a_failed_page_writes_every_page(self):
        # all-failed is decided over the whole run: a grey page beside real views on another page is still written,
        # so the sheet at --out sits beside its index and counts as the street check
        import photo_session
        buf = io.BytesIO()
        Image.new("RGB", (64, 48), "green").save(buf, "JPEG")

        def gsv_view(pid, *a, **k):
            if pid != "good":
                raise RuntimeError("blocked")
            return Image.new("RGB", (640, 480), "green")

        def baidu_get(url, *a, **k):
            if "panoid=good&" not in url:
                raise RuntimeError("Request failed (curl exit 22)")
            return buf.getvalue()
        bad = [{"id": f"bad{k}", "heading": 0.0, "pitch": 10, "fov": 80} for k in range(12)]
        good = {"id": "good", "heading": 0.0, "pitch": 10, "fov": 80}
        spec = self.dir / "spec.json"
        spec.write_text(json.dumps([bad[0], good]), encoding="utf-8")
        runs = {"gsv": (gsv, patch.object(gsv, "view", side_effect=gsv_view),
                        ["sheet", "--ids", "bad0,good", "--heading", "0", "--limit", "1"]),
                "baidu sheet": (baidu_pano, patch.object(baidu_pano, "_get", side_effect=baidu_get),
                                ["sheet", "--spec", str(spec), "--limit", "1"]),
                "baidu sample": (baidu_pano, patch.object(baidu_pano, "_get", side_effect=baidu_get),
                                 ["sample", "--bbox", "22.5,113.9,22.6,114.1"])}     # 12 cells per page: 12 failed, then one view
        for name, (mod, fetch, argv) in runs.items():
            with self.subTest(run=name):
                folder = self.dir / name.replace(" ", "_")
                folder.mkdir()
                out = folder / "s.jpg"
                cmd = [f"{mod.__name__}.py", "--cache", str(folder / "cache"), *argv, "--out", str(out)]
                with fetch, patch.object(gsv.SL, "metadata", return_value={}), patch.object(baidu_pano, "sample", return_value=bad + [good]),                         patch.object(sys, "argv", cmd), patch.dict(os.environ), patch("sys.stdout", new=io.StringIO()) as so,                         patch("sys.stderr", new=io.StringIO()) as se:
                    mod.main()
                for page in (out, folder / "s_2.jpg"):
                    self.assertTrue(page.exists(), page)
                    self.assertIn(str(page), so.getvalue())
                self.assertRegex(se.getvalue(), r"(1/2|12/13) cells failed")
                files = sorted(p.name for p in folder.iterdir() if p.is_file())
                self.assertEqual(photo_session.check_hits(folder, files)["street"], ["s.index.json"])

    def test_baidu_sheet_all_failed_exits(self):
        pid = "09002200121902131010000012345"
        rows = [{"id": pid, "heading": 45.0, "pitch": 10, "fov": 80}]
        spec, out, cache = self.dir / "spec.json", self.dir / "s.jpg", self.dir / "cache"
        spec.write_text(json.dumps(rows), encoding="utf-8")
        sheet = ["sheet", "--spec", str(spec), "--out", str(out)]
        sample = ["sample", "--bbox", "22.5,113.9,22.6,114.1", "--n", "1", "--out", str(out)]
        for argv, reply in ((sheet, RuntimeError("Request failed (curl exit 22)")), (sheet, b"<html>busy</html>"),
                            (sample, RuntimeError("Request failed (curl exit 28)"))):
            get = (patch.object(baidu_pano, "_get", side_effect=reply) if isinstance(reply, Exception)
                   else patch.object(baidu_pano, "_get", return_value=reply))      # refused, or a reply that is no image
            with self.subTest(cmd=argv[0], reply=reply):
                with get, patch.object(baidu_pano, "sample", return_value=list(rows)), \
                        patch.object(sys, "argv", ["baidu_pano.py", "--cache", str(cache), *argv]), \
                        patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()) as err, \
                        self.assertRaises(SystemExit) as cm:
                    baidu_pano.main()
                self.assertIn("every one of the 1 cells failed", str(cm.exception))
                self.assertIn(f"baidu render failed for {pid}", err.getvalue())
                self.assertFalse(out.exists())
                self.assertFalse(out.with_suffix(".index.json").exists())
                self.assertEqual(list(cache.glob("*")), [])                   # a failed view is never cached


class LongToolProgressTests(unittest.TestCase):
    """Long tools printed nothing: a Kakao listing ran minutes without a line and a killed one lost every row, sweep indexing
    spoke every 256 panoramas (~10 min at 2.4 s each), a killed Overpass find left no line, match.py rank cut the candidates
    without saying how to narrow them."""

    BBOX = "33.50,126.50,33.503,126.503"         # 9 grid points at 100 m

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        osm._blocked_until.clear()

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def kakao(kill_at=None):
        """One panorama at every asked point; asking kill_at raises KeyboardInterrupt (the run is killed there)."""
        def find_panoramas(lat, lon, **k):
            if kill_at and (lat, lon) == kill_at:
                raise KeyboardInterrupt
            return [SimpleNamespace(id=f"{lat:.6f},{lon:.6f}", lat=lat, lon=lon, heading=0.0, date=None)]
        return SimpleNamespace(find_panoramas=find_panoramas)

    def test_point_lookup_announces_its_size_then_rate_and_eta(self):
        import pano
        bb = tuple(float(v) for v in self.BBOX.split(","))
        n = len(pano.grid(bb, 100))
        with patch.object(pano.P, "_sl", lambda s: self.kakao()), patch.object(pano.time, "sleep"), patch.object(pano, "PROGRESS_S", 0), \
                patch("sys.stderr", new=io.StringIO()) as err:
            rows = pano._point_lookup("kakao", bb, 100, 0)
        lines = err.getvalue().splitlines()
        self.assertEqual(len(rows), n)
        self.assertRegex(lines[0], rf"^kakao: {n} lookups at 100 m spacing, ~\d+ s at ~[\d.]+ lookups/s")
        self.assertTrue(any(re.search(rf"^kakao: \d+/{n} lookups, \d+ panoramas, [\d.]+ lookups/s, ~\d+ s left", ln) for ln in lines[1:]),
                        lines)

    def test_killed_listing_keeps_the_rows_found_and_a_finished_one_writes_them_all(self):
        import pano
        pts = pano.grid(tuple(float(v) for v in self.BBOX.split(",")), 100)
        out, side = self.dir / "m.jsonl", self.dir / "m.jsonl.partial.jsonl"
        old = PanoSheetAndKakaoTests.rows(("old", "2020-01-01", 0))
        pano.P.write_manifest(out, old)                                        # a complete earlier listing
        argv = ("list", "--provider", "kakao", "--bbox", self.BBOX, "--spacing", "100", "--out", str(out))
        with patch.object(pano.P, "_sl", lambda s: self.kakao(kill_at=pts[3])), patch.object(pano.time, "sleep"), \
                self.assertRaises(KeyboardInterrupt):
            PanoSheetAndKakaoTests.pano_main(*argv)
        self.assertEqual(pano.P.read_manifest(out), old)                       # never a partial area under the manifest's name
        self.assertEqual([r["id"] for r in pano.P.read_manifest(side)], [f"{la:.6f},{lo:.6f}" for la, lo in pts[:3]])
        with patch.object(pano.P, "_sl", lambda s: self.kakao()), patch.object(pano.time, "sleep"), open(out, encoding="utf-8"):
            _, err = PanoSheetAndKakaoTests.pano_main(*argv, "--limit", "5")  # a reader holding --out open never blocks the write
        self.assertIn(f"rows go to {side} as they arrive", err.splitlines()[0])
        self.assertEqual(len(pano.P.read_manifest(out)), 5)                    # the complete run replaces the earlier manifest
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["m.jsonl"])

    def test_lookup_cap_names_the_time_and_what_fits(self):
        import pano
        bb = pano.bbox_around(33.5, 126.53, 3000)
        with patch.object(pano.P, "_sl", lambda s: self.kakao()), self.assertRaises(SystemExit) as cm:
            pano._point_lookup("kakao", bb, 40, 0)
        msg = str(cm.exception)
        self.assertIn(f"{len(pano.grid(bb, 40))} lookups at 40 m spacing", msg)
        self.assertRegex(msg, r"~\d+(\.\d)? (min|h)")
        spacing = float(re.search(r"--spacing (\d+)", msg).group(1))
        self.assertLessEqual(len(pano.grid(bb, spacing)), pano.LOOKUP_CAP)
        self.assertGreater(len(pano.grid(bb, spacing - 5)), pano.LOOKUP_CAP)  # about the finest that fits, not just any coarse one
        radius = float(re.search(r"--radius (\d+)", msg).group(1))
        self.assertLessEqual(len(pano.grid(pano.bbox_around(33.5, 126.53, radius), 40)), pano.LOOKUP_CAP)

    def test_list_date_that_keeps_nothing_names_undated_rows_and_periods(self):
        import pano
        listed = PanoSheetAndKakaoTests.rows(("a", "2008-10-29", 0), ("b", "2026-03-05", 10), ("c", "", 20))
        with patch.dict(pano.LISTERS, {"kakao": lambda bb, spacing, limit, **_: list(listed)}):
            _, err = PanoSheetAndKakaoTests.pano_main("list", "--provider", "kakao", "--bbox", "33.49,126.49,33.51,126.51", "--date", "2018",
                                                      "--out", str(self.dir / "d.jsonl"))
        self.assertIn("--date 2018 kept 0 of 3 panoramas (1 undated; periods here: 2008-10, 2026-03)", err)

    def test_sweep_index_reports_its_rate_early_and_during_a_batch(self):
        import numpy as np
        import sweep
        rows = [{"provider": "x", "id": str(i), "lat": 33.5, "lon": 126.5, "heading": 0.0, "low": {"kind": "photo"}} for i in range(40)]
        view = SimpleNamespace(bearings=lambda n: [0.0, 180.0], render=lambda *a: Image.new("RGB", (8, 8)))
        megaloc = types.ModuleType("geolib.megaloc")          # no torch here: the embedder is faked
        megaloc.Embedder = lambda: SimpleNamespace(embed=lambda ims: np.zeros((len(ims), 8448), np.float32))
        for every, name in ((30, "a"), (0, "b")):
            args = SimpleNamespace(manifest=["town.jsonl"], name=name, views=2, hfov=65, pitch=3, workers=2, parallel=2)
            with patch.object(sweep, "ROOT", self.dir), patch.object(sweep.P, "read_manifest", return_value=rows), \
                    patch.object(sweep.P, "load", return_value=view), patch.dict(sys.modules, {"geolib.megaloc": megaloc}), \
                    patch.object(sweep, "PROGRESS_S", every), patch("sys.stdout", new=io.StringIO()) as out:
                sweep.cmd_index(args)
            lines = out.getvalue().splitlines()
            first = r"^  16/40 panoramas, 32 views, \d+s, [\d.]+ s/panorama, ~[\d.]+ min left"
            if every:
                self.assertRegex(lines[1], first)                               # the first line comes after 16 panoramas
            else:
                self.assertTrue(any(re.match(first, ln) for ln in lines), lines)
            mid = [ln for ln in lines if re.match(r"^  (1[7-9]|[23]\d)/40 panoramas", ln)]
            self.assertTrue(mid if every == 0 else not mid, lines)              # time-based lines inside a batch
            self.assertTrue(lines[-1].startswith("done: 40 panoramas, 80 views"), lines)

    def overpass(self, post, ql="[out:json][timeout:60];node(1);out;"):
        """osm.run against fake mirrors; its stderr lines land in self.lines even when the run is killed."""
        err = io.StringIO()
        try:
            with patch.object(osm, "_post", side_effect=post), patch.object(osm.time, "sleep"), \
                    patch.dict(os.environ, {"GEO_OVERPASS_URL": ""}), patch("sys.stderr", new=err):
                osm.run(ql, None, self.dir, timeout=60)
        finally:
            self.lines = err.getvalue().splitlines()

    def test_every_overpass_attempt_leaves_a_line(self):
        hosts = [ep.split("/")[2] for ep in osm.ENDPOINTS]
        self.overpass(lambda ep, q, proxy, timeout: (None, "HTTP 504: server too busy") if ep == osm.ENDPOINTS[0]
                      else ({"elements": [LINE]}, ""))
        self.assertRegex(self.lines[0], rf"^Overpass {re.escape(hosts[0])}: asking \(gives up after 90 s, 0 s elapsed\)")
        self.assertRegex(self.lines[1], rf"^Overpass {re.escape(hosts[1])}: asking \(gives up after 90 s, \d+ s elapsed\)")

        def killed(ep, q, proxy, timeout):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.overpass(killed, "[out:json][timeout:60];node(2);out;")
        self.assertIn(hosts[0], self.lines[-1])                                # the mirror in flight when the run was killed

    def match_args(self, **kw):
        base = dict(cache=str(self.dir), images=None, items=None, spread_headings=None, panos=None, max_candidates=400, toward=None,
                    within=None, render="gsv", proxy=None, headings=None, spread=None, offset=0, pitch=10, fov=80)
        return SimpleNamespace(**{**base, **kw})

    def test_match_cap_is_announced_before_rendering_and_scoring(self):
        import match
        items = self.dir / "t.index.json"
        items.write_text(json.dumps([{"id": f"p{i}", "heading": 0.0, "wgs": [33.5 + i * 1e-4, 126.5]} for i in range(5)]), encoding="utf-8")
        for within, ids, order in (("33.5004,126.5,1000", ["p4", "p3"], "nearest to the --within centre first"),
                                   (None, ["p0", "p1"], "the first 2 in file order")):
            seen = {}
            err = io.StringIO()

            def render(its, engine, proxy, cache):
                seen.update(notice=err.getvalue(), ids=[it["id"] for it in its])
                return [Image.new("RGB", (8, 8)) for _ in its]
            with patch.object(match, "_render_items", side_effect=render), patch("sys.stderr", new=err):
                match._load_candidates(self.match_args(items=str(items), max_candidates=2, within=within))
            self.assertEqual(seen["ids"], ids)
            for part in ("5 candidates, above --max-candidates 2: scoring 2", order, "3 not scored", "--within lat,lon,m",
                         "--spread-headings", "split the set"):
                self.assertIn(part, seen["notice"])
        with patch.object(match, "_render_items", side_effect=AssertionError("rendered outside --within")), \
                self.assertRaises(SystemExit) as cm:
            match._load_candidates(self.match_args(items=str(items), within="40.0,10.0,100"))
        self.assertIn("no candidates left", str(cm.exception))                    # --within filters --items too
        bare = self.dir / "baidu.index.json"                                       # baidu_pano.py sheet --ids: no positions
        bare.write_text(json.dumps([{"id": "0900", "heading": 90.0, "pitch": 0, "fov": 60}]), encoding="utf-8")
        with patch.object(match, "_render_items", side_effect=AssertionError("rendered without positions")), \
                self.assertRaises(SystemExit) as cm:
            match._load_candidates(self.match_args(items=str(bare), within="31.23,121.47,5000", render="baidu"))
        self.assertIn(f"{bare} has no positions", str(cm.exception))
        self.assertIn("drop --within", str(cm.exception))
        self.assertNotIn("widen", str(cm.exception))                              # widening can never help

    def test_match_without_a_source_names_the_three_with_examples(self):
        import match
        with self.assertRaises(SystemExit) as cm:
            match._load_candidates(self.match_args(within="33.5,126.5,300"))
        for example in ("--images cands/", "--items targets.index.json --render gsv", "--panos panos.json --headings 0,90,180,270"):
            self.assertIn(example, str(cm.exception))


if __name__ == "__main__":
    unittest.main()
