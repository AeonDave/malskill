#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Offline regressions for viewer.py (state building, focus, stages, the local server). Run: uv run scripts/tests/test_viewer.py"""
from __future__ import annotations

import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import viewer  # noqa: E402

PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c636000010000050001"
                    "0d0a2db40000000049454e44ae426082")


def make_session(root: Path, with_board: bool = True) -> Path:
    folder = root / "2026-01-02_03-04-05-000000+0100"
    (folder / "original").mkdir(parents=True)
    (folder / "original" / "photo.png").write_bytes(PNG)
    (folder / "session.json").write_text(json.dumps({
        "schema_version": 1, "timestamp": folder.name, "started_at": "2026-01-02T03:04:05.000000+01:00",
        "status": "pending", "folder": str(folder), "original": {"relative_path": "original/photo.png", "sha256": "x"},
    }), encoding="utf-8")
    (folder / "report.md").write_text("# Geolocation report: photo.png\n\n## Gut call (before tools)\n1. Greece 80% — sign\n\n## Answer\n<!-- fill: x -->\n", encoding="utf-8")
    if with_board:
        (folder / "board.json").write_text(json.dumps({
            "case": folder.name, "photo": "original/photo.png", "created": "2026-01-02T03:10:00", "country": None,
            "candidates": {
                "Greece": {"level": "country", "parent": None, "bbox": None, "scan_bbox": None, "prior": 1.0, "status": "open", "note": ""},
                "Bulgaria": {"level": "country", "parent": None, "bbox": None, "scan_bbox": None, "prior": 1.0, "status": "excluded", "note": ""},
                "Kozani": {"level": "admin1", "parent": "Greece", "bbox": None, "scan_bbox": None, "prior": 1.0, "status": "open", "note": ""},
                "Koilada": {"level": "area", "parent": "Kozani", "bbox": [40.352, 21.92, 40.364, 21.936], "scan_bbox": None, "prior": 1.0, "status": "open", "note": ""},
                "Galani": {"level": "area", "parent": "Kozani", "bbox": None, "scan_bbox": None, "prior": 1.0, "status": "open", "note": ""},
            },
            "clues": {"K1": {"text": "Greek sign", "kind": "text", "status": "read", "file": "sign.png", "source": "", "used": True}},
            "evidence": [{"id": "E1", "clue": "K1", "candidate": "Greece", "lr": 15.0, "why": "script", "file": "", "cmd": ""},
                         {"id": "E2", "clue": "K1", "candidate": "Koilada", "lr": 2.0, "why": "fits", "file": "", "cmd": ""}],
            "falsify": {}, "log": ["03:10 add Greece (country)", "03:11 evidence E1 K1 → Greece ×15"], "updated": "2026-01-02T03:11:00",
        }), encoding="utf-8")
    return folder


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="viewer-"))
        self.folder = make_session(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_focus_prefers_finest_open_candidate_with_geometry(self):
        s = viewer.build_state(self.folder)
        f = s["focus"]
        self.assertEqual(f["level"], "area")
        self.assertEqual(f["name"], "Koilada")            # top share at the frontier (evidence E2) and it has a bbox
        self.assertAlmostEqual(f["lat"], 40.358, places=3)
        self.assertLess(f["radius_km"], 2.0)
        self.assertFalse(f["final"])
        self.assertEqual(s["stage"], "Candidates")

    def test_country_geometry_from_table_and_exclusion(self):
        rows = {r["name"]: r for r in viewer.build_state(self.folder)["candidates"]}
        self.assertEqual(rows["Greece"]["iso2"], "GR")
        self.assertTrue(rows["Greece"]["has_geo"])
        self.assertGreater(rows["Greece"]["radius_km"], 100)
        self.assertTrue(rows["Bulgaria"]["excluded"])
        self.assertEqual(rows["Bulgaria"]["share"], 0.0)
        self.assertFalse(rows["Galani"]["has_geo"])

    def test_scan_bbox_places_a_candidate_too(self):
        b = json.loads((self.folder / "board.json").read_text(encoding="utf-8"))
        b["candidates"]["Galani"]["scan_bbox"] = [40.355, 21.868, 40.363, 21.882]
        (self.folder / "board.json").write_text(json.dumps(b), encoding="utf-8")
        rows = {r["name"]: r for r in viewer.build_state(self.folder)["candidates"]}
        self.assertTrue(rows["Galani"]["has_geo"])
        self.assertAlmostEqual(rows["Galani"]["lon"], 21.875, places=3)

    def test_focus_falls_back_to_ancestor_without_geometry(self):
        b = json.loads((self.folder / "board.json").read_text(encoding="utf-8"))
        b["candidates"]["Koilada"]["bbox"] = None
        (self.folder / "board.json").write_text(json.dumps(b), encoding="utf-8")
        f = viewer.build_state(self.folder)["focus"]
        self.assertEqual(f["name"], "Koilada")
        self.assertEqual(f["placed_by"], "Greece")        # Kozani has no bbox either, Greece has a centre
        self.assertEqual(f["iso2"], "GR")

    def test_final_result_wins_and_stage_done(self):
        meta = json.loads((self.folder / "session.json").read_text(encoding="utf-8"))
        meta.update({"status": "completed", "result": {"country": "Greece", "region": "Kozani", "city_or_nearest_locality": "Koilada",
                                                        "latitude": 40.3581, "longitude": 21.9279, "radius_m": 250, "heading": 215, "confidence": "medium"}})
        (self.folder / "session.json").write_text(json.dumps(meta), encoding="utf-8")
        s = viewer.build_state(self.folder)
        self.assertTrue(s["focus"]["final"])
        self.assertEqual(s["focus"]["name"], "Koilada, Kozani, Greece")
        meta["truth"] = {"latitude": 40.48633, "longitude": 21.13315, "country": "Greece", "city": "Kalochori", "error_km": 68.758}
        (self.folder / "session.json").write_text(json.dumps(meta), encoding="utf-8")
        self.assertEqual(viewer.build_state(self.folder)["truth"]["city"], "Kalochori")
        self.assertEqual(s["focus"]["radius_km"], 0.25)
        self.assertEqual(s["focus"]["heading"], 215)
        self.assertEqual(s["stage"], "Done")

    def test_stages_from_artifacts(self):
        self.assertEqual(viewer.build_state(self.folder)["stage"], "Candidates")
        (self.folder / "koilada_rank.jpg").write_bytes(PNG)
        self.assertEqual(viewer.build_state(self.folder)["stage"], "Pinpoint")
        (self.folder / "verify").mkdir()
        self.assertEqual(viewer.build_state(self.folder)["stage"], "Verify")   # a verify/ folder is the verify step
        (self.folder / "evidence.jpg").write_bytes(PNG)
        self.assertEqual(viewer.build_state(self.folder)["stage"], "Verify")
        other = make_session(self.tmp / "b", with_board=False)
        self.assertEqual(viewer.build_state(other)["stage"], "Gut call")
        (other / "report.md").write_text("# r\n\n## Gut call (before tools)\n<!-- fill: ranked shortlist -->\n", encoding="utf-8")
        self.assertEqual(viewer.build_state(other)["stage"], "Gut call")             # the first stage, even before it is written
        (other / "recon").mkdir()                                                    # recon.py has started, nothing written yet
        self.assertEqual(viewer.build_state(other)["stage"], "Recon")
        (other / "viewer_marks.json").write_text("[]", encoding="utf-8")
        self.assertEqual(viewer.build_state(other)["stage"], "Pinpoint")

    def test_activity_merges_say_board_and_files_newest_first(self):
        (self.folder / "sign.png").write_bytes(PNG)
        old = time.time() - 3600
        os.utime(self.folder / "sign.png", (old, old))
        viewer.main(["say", "Reading the sign", "--session", str(self.folder)])
        s = viewer.build_state(self.folder)
        self.assertEqual(s["now"], "Reading the sign")
        self.assertEqual(s["activity"][0]["source"], "say")
        sources = {e["source"] for e in s["activity"]}
        self.assertEqual(sources, {"say", "board", "file"})
        times = [e["time"] for e in s["activity"]]
        self.assertEqual(times, sorted(times, reverse=True))
        self.assertNotIn("original/photo.png", [e["text"] for e in s["activity"]])   # the original is not an event
        self.assertTrue(any(a["path"] == "original/photo.png" for a in s["artifacts"]))

    def test_several_originals_are_listed_and_are_not_events(self):
        meta = json.loads((self.folder / "session.json").read_text(encoding="utf-8"))
        (self.folder / "original" / "second.png").write_bytes(PNG)
        meta["originals"] = [meta["original"], {"relative_path": "original/second.png", "sha256": "y"}]
        (self.folder / "session.json").write_text(json.dumps(meta), encoding="utf-8")
        s = viewer.build_state(self.folder)
        self.assertEqual([p["name"] for p in s["photos"]], ["photo.png", "second.png"])
        self.assertEqual(s["title"], "photo.png")
        self.assertEqual(s["photo_url"], "/files/original/photo.png")
        self.assertFalse(any(e["source"] == "file" and e["text"].startswith("original/") for e in s["activity"]))

    def test_marks_and_rank_ingestion(self):
        s = str(self.folder)
        self.assertEqual(viewer.main(["mark", "camera", "--lat", "40.4863", "--lon", "21.1331", "--heading", "5", "--fov", "80", "--label", "pano", "--session", s]), 0)
        self.assertEqual(viewer.main(["mark", "line", "--from", "40.4863,21.1331", "--bearing", "90", "--km", "2", "--label", "ridge", "--session", s]), 0)
        self.assertEqual(viewer.main(["mark", "point", "--lat", "40.49", "--lon", "21.14", "--label", "church", "--session", s]), 0)
        (self.folder / "sign.png").write_bytes(PNG)
        self.assertEqual(viewer.main(["mark", "image", str(self.folder / "sign.png"), "--lat", "40.48", "--lon", "21.13", "--heading", "270", "--session", s]), 0)
        with self.assertRaises(SystemExit):
            viewer.main(["mark", "image", str(self.tmp / "elsewhere.png"), "--lat", "1", "--lon", "2", "--session", s])
        views = self.folder / "kalo_rank_views"
        views.mkdir()
        (views / "01_abc_h0.jpg").write_bytes(PNG)
        (self.folder / "rank.json").write_text(json.dumps([{"rank": 1, "id": "plain", "score_global": 0.5, "heading": 90, "wgs": [40.4, 21.1]}]), encoding="utf-8")
        (self.folder / "kalo_rank.json").write_text(json.dumps([
            {"rank": 1, "id": "abc", "score_global": 0.396, "inliers": 6, "heading": 0, "wgs": [40.48633, 21.13315], "view": "kalo_rank_views/01_abc_h0.jpg"},
            {"rank": 2, "id": "def", "score_global": 0.242, "inliers": 28, "heading": 270, "wgs": [40.48631, 21.13355]},
            {"rank": 3, "id": "file-only", "score_global": 0.2, "file": "x.jpg"},
        ]), encoding="utf-8")
        (self.folder / "kalo.index.json").write_text(json.dumps([{"id": "abc", "wgs": [40.4863, 21.1331]}, {"id": "def", "wgs": [40.4864, 21.1335]}, {"id": "bad"}]), encoding="utf-8")
        (self.folder / "kalo").write_text(json.dumps({"ghi": {"wgs": [40.4865, 21.1340], "date": "", "road": ""}}), encoding="utf-8")   # gsv.py area --out kalo
        L = viewer.build_state(self.folder)["layers"]
        self.assertEqual(L["cameras"][0]["fov"], 80)
        self.assertAlmostEqual(L["lines"][0]["to"][1], 21.1331 + 2 / (111.32 * 0.76), places=2)   # 2 km east at this latitude
        self.assertEqual(L["points"][0]["label"], "church")
        self.assertEqual(L["images"][0]["url"], "/files/sign.png")
        self.assertEqual([m["id"] for m in L["matches"]], ["def", "abc", "plain"])                  # inliers first, then score; rank.json counts too
        self.assertEqual(L["matches"][1]["view"], "/files/kalo_rank_views/01_abc_h0.jpg")
        self.assertEqual(len(L["coverage"]), 3)
        self.assertEqual(viewer.main(["mark", "clear", "--kind", "line", "--session", s]), 0)
        self.assertEqual(len(viewer.read_marks(self.folder)), 3)
        self.assertEqual(viewer.main(["mark", "clear", "--session", s]), 0)
        self.assertEqual(viewer.read_marks(self.folder), [])

    def test_analysis_images_are_picked_by_name(self):
        for name in ("ridge_overlay.png", "evidence.jpg", "koilada40_rank.jpg", "sign_zoom.png"):
            (self.folder / name).write_bytes(PNG)
        (self.folder / "koilada40_rank_views").mkdir()
        (self.folder / "koilada40_rank_views" / "01_x_h0.jpg").write_bytes(PNG)                      # shown on the map, not in the gallery
        names = {a["path"] for a in viewer.build_state(self.folder)["analysis_images"]}
        self.assertEqual(names, {"ridge_overlay.png", "evidence.jpg", "koilada40_rank.jpg"})

    def test_gut_call_fills_the_board_until_board_py_is_used(self):
        (self.folder / "board.json").unlink()
        (self.folder / "report.md").write_text(
            "# r\n\n## Gut call (before tools)\n1. Namibia 60% — arid, yellow edge lines, left-hand traffic\n"
            "2. South Africa 30% — similar roads\n3. Botswana 10% — flatter\nRegion hunch: Erongo\n"
            "Would change my mind: a Portuguese sign\n\n## Answer\n<!-- fill: x -->\n", encoding="utf-8")
        s = viewer.build_state(self.folder)
        self.assertEqual(s["candidates_source"], "gut")
        self.assertEqual([c["name"] for c in s["candidates"]], ["Namibia", "South Africa", "Botswana"])
        self.assertAlmostEqual(s["candidates"][0]["share"], 0.6, places=3)
        self.assertEqual(s["candidates"][0]["iso2"], "NA")
        self.assertEqual(s["focus"]["name"], "Namibia")
        self.assertEqual(s["focus"]["label"], "gut call")
        self.assertEqual(s["stage"], "Gut call")
        # an unknown name stays in the list without a position; the board, once used, takes over
        (self.folder / "report.md").write_text("# r\n\n## Gut call (before tools)\n1. Atlantis 100%\n\n## Answer\n<!-- fill: x -->\n", encoding="utf-8")
        s = viewer.build_state(self.folder)
        self.assertFalse(s["candidates"][0]["has_geo"])
        self.assertIsNone(s["focus"])
        make_session(self.tmp / "again")
        self.assertEqual(viewer.build_state(self.tmp / "again" / "2026-01-02_03-04-05-000000+0100")["candidates_source"], "board")

    def test_json_with_bom_is_read(self):
        meta = json.loads((self.folder / "session.json").read_text(encoding="utf-8"))
        meta.update({"status": "completed", "result": {"country": "Greece", "latitude": 40.0, "longitude": 21.0, "confidence": "low"}})
        (self.folder / "session.json").write_bytes(b"\xef\xbb\xbf" + json.dumps(meta, indent=4).encode("utf-8"))   # PowerShell style
        s = viewer.build_state(self.folder)
        self.assertEqual(s["status"], "completed")
        self.assertEqual(s["title"], "photo.png")

    def test_hand_closed_session_stays_in_analysis_mode(self):
        meta = json.loads((self.folder / "session.json").read_text(encoding="utf-8"))
        meta.update({"status": "completed", "result": None, "completion_note": "closed by hand"})
        (self.folder / "session.json").write_text(json.dumps(meta), encoding="utf-8")
        s = viewer.build_state(self.folder)
        self.assertEqual(s["status"], "pending")
        self.assertIn("photo_session.py finish", s["warning"])
        self.assertNotEqual(s["stage"], "Done")

    def test_coherence_note_for_a_bare_finer_candidate(self):
        b = json.loads((self.folder / "board.json").read_text(encoding="utf-8"))
        b["candidates"]["Bulgaria"]["status"] = "open"
        b["candidates"]["Plovdiv"] = {"level": "city", "parent": "Bulgaria", "bbox": None, "scan_bbox": None, "prior": 1.0, "status": "open", "note": ""}
        (self.folder / "board.json").write_text(json.dumps(b), encoding="utf-8")
        s = viewer.build_state(self.folder)
        self.assertTrue(any(n.startswith("Plovdiv sits under Bulgaria without any evidence") for n in s["coherence"]), s["coherence"])

    def test_export_writes_an_offline_snapshot(self):
        (self.folder / "sign.png").write_bytes(PNG)
        viewer.main(["mark", "image", str(self.folder / "sign.png"), "--lat", "40.48", "--lon", "21.13", "--session", str(self.folder)])
        out = viewer.export_html(self.folder)
        self.assertEqual(out, self.folder / "viewer.html")
        html = out.read_text(encoding="utf-8")
        self.assertIn("window.GEO_STATE = {", html)
        self.assertIn("window.GEO_COUNTRIES = {", html)
        self.assertIn("<style>", html)
        state_part = html.split("window.GEO_STATE = ", 1)[1].split("window.GEO_COUNTRIES", 1)[0]
        self.assertNotIn("/files/", state_part)                        # every link relative to the folder
        self.assertIn('"url": "original/photo.png"', state_part)
        self.assertNotIn("</script>", state_part)                       # the JSON can never close the script tag
        self.assertIn("const STATIC = !!window.GEO_STATE", html)
        self.assertIn('"snapshot_at"', html)

    def test_rank_files_are_known_by_content_and_find_session_follows_finish(self):
        (self.folder / "ranked.json").write_text(json.dumps([{"rank": 1, "id": "byname", "score_global": 0.4, "heading": 10, "wgs": [40.5, 21.1]}]), encoding="utf-8")
        (self.folder / "notes.json").write_text(json.dumps({"not": "a rank file"}), encoding="utf-8")
        ids = [m["id"] for m in viewer.build_state(self.folder)["layers"]["matches"]]
        self.assertIn("byname", ids)
        renamed = self.folder.with_name(self.folder.name + "__greece__kastoria__kalochori")
        self.folder.rename(renamed)
        self.assertEqual(viewer.find_session(str(self.folder)), renamed)                      # the folder printed by start still works
        self.assertEqual(viewer.main(["mark", "line", "--from", "-21.99,15.52", "--bearing", "90", "--km", "1", "--session", str(renamed)]), 0)   # negative coordinates
        with self.assertRaises(SystemExit):
            viewer.main(["mark", "camera", "--lat", "1", "--lon", "2", "--session", str(renamed)])   # heading missing
        gone = viewer.build_state(self.tmp / "nowhere")
        self.assertIn("gone", gone["warning"])

    def test_old_sessions_get_when_text_and_heading_hint_from_their_files(self):
        meta = json.loads((self.folder / "session.json").read_text(encoding="utf-8"))
        meta.update({"status": "completed", "result": {"country": "Greece", "latitude": 40.0, "longitude": 21.0, "confidence": "low", "heading": None}})
        (self.folder / "session.json").write_text(json.dumps(meta), encoding="utf-8")
        (self.folder / "report.md").write_text("# r\n\n## Answer\nx\n\n## When\nSpring 2015 or later (panorama dates)\n\n## Z\n", encoding="utf-8")
        (self.folder / "r_rank.json").write_text(json.dumps([{"rank": 1, "id": "a", "heading": 77, "inliers": 12, "score_global": 0.2, "wgs": [40.0005, 21.0005]}]), encoding="utf-8")
        s = viewer.build_state(self.folder)
        self.assertEqual(s["result"]["when_text"], "Spring 2015 or later (panorama dates)")
        self.assertEqual(s["result"]["heading_hint"]["heading"], 77.0)
        self.assertEqual(s["focus"]["heading_hint"], 77.0)

    def test_viewer_url_is_recorded_and_stop_needs_it(self):
        viewer.record_viewer_url(self.folder, "http://127.0.0.1:48770/")
        self.assertEqual(json.loads((self.folder / "session.json").read_text(encoding="utf-8"))["viewer_url"], "http://127.0.0.1:48770/")
        self.assertEqual(viewer.viewer_port(str(self.folder), None), 48770)
        self.assertEqual(viewer.viewer_port(str(self.folder), 99), 99)
        other = make_session(self.tmp / "noport")
        with self.assertRaises(SystemExit):
            viewer.viewer_port(str(other), None)                                     # random ports: no silent default

    def test_skyline_card_comes_from_the_fit_sidecar(self):
        self.assertIsNone(viewer.build_state(self.folder)["skyline"])
        side = {"image": "top_skyline.jpg", "fit": "fit.json", "top": [{"rank": 1, "hit": 62, "name": "Lago di Tovel", "cam": [46.2586, 10.9491],
                "heading": 59.0, "f35": 24.3, "rms_px": 18.0, "total": 0.859, "peaks": [{"name": "Cima X", "dist_m": 3200}]}]}
        (self.folder / "top_skyline.json").write_text(json.dumps(side), encoding="utf-8")
        self.assertIsNone(viewer.build_state(self.folder)["skyline"])                     # no image yet: no card
        (self.folder / "top_skyline.jpg").write_bytes(b"\xff\xd8\xff\xd9")
        s = viewer.build_state(self.folder)
        self.assertEqual(s["skyline"]["image"], "/files/top_skyline.jpg")
        self.assertEqual(s["skyline"]["top"][0]["name"], "Lago di Tovel")
        self.assertNotIn("top_skyline.jpg", [a["path"] for a in s["analysis_images"]])      # the card, not the gallery

    def test_version_changes_with_content(self):
        v1 = viewer.build_state(self.folder)["version"]
        viewer.main(["say", "next step", "--session", str(self.folder)])
        self.assertNotEqual(v1, viewer.build_state(self.folder)["version"])

    def test_follow_rename(self):
        renamed = self.folder.with_name(self.folder.name + "__greece__kozani__koilada")
        self.folder.rename(renamed)
        self.assertEqual(viewer.follow_rename(self.folder), renamed)
        self.assertEqual(viewer.build_state(self.folder)["name"], renamed.name)

    def test_find_session_from_subfolder(self):
        sub = self.folder / "recon" / "intake"
        sub.mkdir(parents=True)
        self.assertEqual(viewer.find_session(str(sub)), self.folder)
        with self.assertRaises(SystemExit):
            viewer.find_session(str(self.tmp))


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="viewer-srv-"))
        cls.folder = make_session(cls.tmp)
        (cls.folder / "sign.png").write_bytes(PNG)
        cls.server = viewer.make_server(cls.folder, 0, "osm")
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def get(self, path, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path, headers=headers or {})
        r = conn.getresponse()
        body = r.read()
        conn.close()
        return r.status, dict(r.getheaders()), body

    def test_page_and_assets(self):
        for path, needle in (("/", b"<canvas id=\"globe\""), ("/app.js", b"/api/state"), ("/style.css", b"--amber"), ("/countries.json", b"\"iso2\"")):
            status, _, body = self.get(path)
            self.assertEqual(status, 200, path)
            self.assertIn(needle, body, path)

    def test_state_and_etag(self):
        status, headers, body = self.get("/api/state")
        self.assertEqual(status, 200)
        s = json.loads(body)
        self.assertEqual(s["tiles"], "osm")
        self.assertEqual(s["focus"]["name"], "Koilada")
        self.assertEqual(s["photo_url"], "/files/original/photo.png")
        status, _, body = self.get("/api/state", {"If-None-Match": headers["ETag"]})
        self.assertEqual(status, 304)
        self.assertEqual(body, b"")

    def test_open_folder_endpoint_is_post_only_and_local(self):
        calls = []
        real = viewer.open_folder
        viewer.open_folder = lambda folder: calls.append(folder)
        try:
            for method, path, expected in (("POST", "/api/open", 204), ("POST", "/api/other", 404), ("GET", "/api/open", 404)):
                conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
                conn.request(method, path)
                r = conn.getresponse()
                r.read()
                conn.close()
                self.assertEqual(r.status, expected, f"{method} {path}")
            self.assertEqual(calls, [self.folder])
        finally:
            viewer.open_folder = real

    def test_folder_can_be_renamed_while_served(self):
        # photo_session.py finish renames the folder while the viewer keeps polling it: no handle may stay open
        folder = make_session(self.tmp / "renaming")
        (folder / "sign.png").write_bytes(PNG)
        server = viewer.make_server(folder, 0, "esri")
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for path in ("/api/state", "/files/sign.png", "/files/report.md", "/api/state"):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                conn.request("GET", path)
                r = conn.getresponse()
                r.read()
                conn.close()
                self.assertEqual(r.status, 200, path)
            renamed = folder.with_name(folder.name + "__greece__kastoria__kalochori")
            folder.rename(renamed)                                    # raises PermissionError on Windows if a handle is open
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/api/state")
            r = conn.getresponse()
            state = json.loads(r.read())
            conn.close()
            self.assertEqual(state["name"], renamed.name)
        finally:
            server.shutdown()
            server.server_close()

    def test_stop_endpoint_shuts_the_server_down(self):
        folder = make_session(self.tmp / "stopping")
        self.assertFalse((folder / "viewer.html").exists())
        server = viewer.make_server(folder, 0, "esri")
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("POST", "/api/stop")
        r = conn.getresponse()
        r.read()
        conn.close()
        self.assertEqual(r.status, 204)
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)   # the page's last poll still gets the final state
        conn.request("GET", "/api/state")
        last = json.loads(conn.getresponse().read())
        conn.close()
        self.assertTrue(last["stopping"])
        self.assertTrue(last["snapshot"].endswith("viewer.html"))
        thread.join(timeout=viewer.STOP_GRACE_S + 6)
        self.assertFalse(thread.is_alive())
        server.server_close()
        self.assertTrue((folder / "viewer.html").is_file())              # Close leaves the page behind as a file

    def test_stop_command_and_idle_watchdog(self):
        folder = make_session(self.tmp / "stopcmd")
        server = viewer.make_server(folder, 0, "esri")
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        other = make_session(self.tmp / "other")
        self.assertEqual(viewer.main(["stop", str(other), "--port", str(port)]), 2)          # another session's viewer: refused
        self.assertTrue(thread.is_alive())
        self.assertEqual(viewer.main(["stop", str(folder), "--port", str(port)]), 0)         # this session's: stopped
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        server.server_close()
        self.assertEqual(viewer.main(["stop", "--port", str(port)]), 1)      # nothing listening any more
        server = viewer.make_server(folder, 0, "esri")
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.assertEqual(viewer.main(["stop", str(other), "--port", str(port), "--force"]), 0)   # --force overrides
        thread.join(timeout=5)
        server.server_close()
        meta = json.loads((folder / "session.json").read_text(encoding="utf-8"))
        meta["viewer_url"] = "http://127.0.0.1:4321/"
        (folder / "session.json").write_text(json.dumps(meta), encoding="utf-8")
        self.assertEqual(viewer.viewer_port(str(folder), None), 4321)
        server = viewer.make_server(folder, 0, "esri")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        viewer.start_watchdog(server, 0.4, tick=0.1)
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())                                   # idle: stopped by itself
        server.server_close()

    def test_foreign_host_and_origin_are_refused(self):
        status, _, _ = self.get("/api/state", {"Host": "evil.example:80"})
        self.assertEqual(status, 403)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/open", headers={"Origin": "http://evil.example"})
        r = conn.getresponse()
        r.read()
        conn.close()
        self.assertEqual(r.status, 403)
        self.assertEqual(self.get("/api/state", {"Host": f"localhost:{self.port}"})[0], 200)

    def test_session_files_and_traversal(self):
        status, headers, body = self.get("/files/sign.png")
        self.assertEqual(status, 200)
        self.assertEqual(body, PNG)
        self.assertTrue(headers["Content-Type"].startswith("image/png"))
        (self.tmp / "outside.txt").write_text("secret", encoding="utf-8")
        self.assertEqual(self.get("/files/../outside.txt")[0], 404)            # nothing above the session folder
        self.assertEqual(self.get("/files/..%2Foutside.txt")[0], 404)
        self.assertEqual(self.get("/files/session.json")[0], 200)             # inside it, everything is readable
        self.assertEqual(self.get("/files/missing.png")[0], 404)
        self.assertEqual(self.get("/" + Path(viewer.__file__).name)[0], 404)   # nothing outside assets/viewer is served
        self.assertEqual(self.get("/data/countries.json")[0], 404)


if __name__ == "__main__":
    unittest.main(verbosity=1)
