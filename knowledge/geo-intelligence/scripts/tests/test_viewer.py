#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Offline regressions for viewer.py (state building, focus, stages, the local server). Run: uv run scripts/tests/test_viewer.py"""
from __future__ import annotations

import contextlib
from datetime import datetime, timedelta
import http.client
import io
import json
import os
import shutil
import subprocess
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

    def test_truth_shown_is_the_current_answers_after_a_refinish(self):
        def session(*args) -> Path:
            r = subprocess.run([sys.executable, str(SCRIPTS / "photo_session.py"), *map(str, args)], cwd=self.tmp, capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 0, r.stderr)
            return Path(json.loads(r.stdout)["folder"])
        (self.folder / "report.md").write_text("# Report\n\n## Gut call (before tools)\n1. Slovakia 80% — sign\n\n## Answer\nPoprad\n\n"
                                               "## When\nNot determinable.\n", encoding="utf-8")
        flags = ["--heading", "unknown", "--taken", "unknown", "--accept-unverified", "operator asked: test fixture"]
        poprad = session("finish", self.folder, "--country", "Slovakia", "--city", "Poprad", "--latitude", "49.1675", "--longitude", "20.0675",
                         "--confidence", "medium", *flags)
        session("truth", poprad, "--latitude", "49.1675", "--longitude", "20.0675", "--country", "Slovakia")
        self.assertEqual(viewer.build_state(poprad)["truth"]["error_km"], 0.0)
        paris = session("finish", poprad, "--country", "France", "--city", "Paris", "--latitude", "48.8566", "--longitude", "2.3522",
                        "--confidence", "high", *flags)
        s = viewer.build_state(paris)
        self.assertEqual(s["result"]["city_or_nearest_locality"], "Paris")
        self.assertAlmostEqual(s["truth"]["error_km"], 1289.5, delta=1.0)                     # the page's distance is Paris's, not Poprad's
        self.assertFalse(s["truth"]["country_hit"])
        self.assertEqual((s["truth"]["latitude"], s["truth"]["longitude"]), (49.1675, 20.0675))

    def test_answer_card_says_unverified_estimate_when_no_check_supports_the_place(self):
        (self.folder / "report.md").write_text("# Report\n\n## Gut call (before tools)\n1. Greece 80% — sign\n\n## Answer\nKoilada\n\n"
                                               "## When\nNot determinable.\n", encoding="utf-8")
        (self.folder / "far_rank.json").write_text(json.dumps([{"rank": 1, "id": "p1", "inliers": 40, "score_global": 0.6, "wgs": [40.5, 21.9]}]),
                                                   encoding="utf-8")                          # a check that ran, 16 km from the answer
        r = subprocess.run([sys.executable, str(SCRIPTS / "photo_session.py"), "finish", str(self.folder), "--country", "Greece", "--city", "Koilada",
                            "--latitude", "40.358", "--longitude", "21.928", "--confidence", "low", "--heading", "unknown", "--taken", "unknown"],
                           cwd=self.tmp, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stderr)
        result = viewer.build_state(Path(json.loads(r.stdout)["folder"]))["result"]
        self.assertEqual((result["verification_artifacts"], result["supporting_artifacts"]), (1, 0))
        page = (SCRIPTS.parent / "assets" / "viewer" / "app.js").read_text(encoding="utf-8")
        rule = 'if (r.supporting_artifacts === 0 || r.accepted_unverified) bits.push("unverified estimate");'
        self.assertTrue(rule in page, "the answer card no longer labels an unsupported answer")

    def test_truth_kept_through_an_unrescored_refinish_shows_the_current_answers_score(self):
        # re-finished after its truth by a version that did not rescore: the stored metrics scored the replaced answer (Poprad, 0 km)
        state = json.loads((self.folder / "session.json").read_text(encoding="utf-8"))
        truth = {"latitude": 49.05, "longitude": 20.30, "country": "Slovakia", "recorded_at": "2026-10-13T12:01:00+02:00",
                 "error_km": 0, "game_score_estimate": 5000, "country_hit": True}
        state.update(status="completed", truth=truth,
                     result={"country": "France", "city_or_nearest_locality": "Paris", "latitude": 48.8566, "longitude": 2.3522, "confidence": "high"},
                     result_history=[{"replaced_at": "2026-10-13T12:02:00+02:00", "result": {"country": "Slovakia", "latitude": 49.05, "longitude": 20.30}}])
        (self.folder / "session.json").write_text(json.dumps(state), encoding="utf-8")
        shown = viewer.build_state(self.folder)["truth"]
        self.assertAlmostEqual(shown["error_km"], viewer._ps.haversine_km(48.8566, 2.3522, 49.05, 20.30), delta=0.01)
        self.assertFalse(shown["country_hit"])
        del truth["latitude"]                                                                  # unscorable: no stale figures either
        (self.folder / "session.json").write_text(json.dumps({**state, "truth": truth}), encoding="utf-8")
        shown = viewer.build_state(self.folder)["truth"]
        self.assertEqual((shown.get("error_km"), shown.get("country_hit"), shown["country"]), (None, None, "Slovakia"))

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

    def say(self, text: str) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(viewer.main(["say", text, "--session", str(self.folder)]), 0)
        return out.getvalue().strip()

    def test_say_prints_the_status_line(self):
        meta = json.loads((self.folder / "session.json").read_text(encoding="utf-8"))
        meta["started_at"] = (datetime.now().astimezone() - timedelta(minutes=12, seconds=20)).isoformat()
        (self.folder / "session.json").write_text(json.dumps(meta), encoding="utf-8")
        (self.folder / "a_rank.json").write_text("[]", encoding="utf-8")
        self.assertEqual(self.say("Ranking panoramas"), "said · +12 min · verification files 1")
        (self.folder / "recon" / "prior").mkdir(parents=True)
        (self.folder / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"mountains": 0.9}}), encoding="utf-8")
        self.assertEqual(self.say("Tracing the ridge"),
                         'said · +12 min · verification files 1 · skyline missing: run terrain.py ridge → fit, or --skip-check skyline:"<reason>"')
        (self.folder / "recon" / "prior" / "prior.json").write_text("[]", encoding="utf-8")       # a hand-edited tag file: no traceback
        self.assertEqual(self.say("Reading the sign"), "said · +12 min · verification files 1")
        self.assertIn('"text": "Tracing the ridge"', (self.folder / "activity.log").read_text(encoding="utf-8"))   # recorded, then reported

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
        (self.folder / "town.index.json").write_text(json.dumps([
            {"cell": 0, "provider": "mapillary", "id": "m1", "lat": 40.4866, "lon": 21.1342, "bearing": 10.0},
            {"cell": 1, "provider": "google", "id": "g1", "lat": "bad", "lon": 21.1}]), encoding="utf-8")        # pano.py list rows: lat/lon keys
        (self.folder / "apple.json").write_text(json.dumps({"a1": {"provider": "apple", "id": "a1", "lat": 40.4867, "lon": 21.1343, "heading": 33.4,
                                                                  "low": {"kind": "equirect", "url": "https://x.example/a1.jpg"}}}), encoding="utf-8")
        L = viewer.build_state(self.folder)["layers"]
        cov = {c["id"]: c for c in L["coverage"]}
        self.assertEqual(set(cov), {"abc", "def", "ghi", "m1", "a1"})                         # wgs rows, lat/lon rows, dict and list forms; no coordinates → dropped
        self.assertEqual(cov["a1"]["url"], "https://x.example/a1.jpg")
        self.assertEqual((cov["a1"]["provider"], cov["a1"]["heading"]), ("apple", 33.4))
        self.assertEqual(cov["m1"]["list"], "town.index.json")
        self.assertIsNone(cov["ghi"]["url"])
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

    def test_required_checks_reach_the_page(self):
        self.assertEqual(viewer.build_state(self.folder)["checks"], [])
        (self.folder / "recon" / "prior").mkdir(parents=True, exist_ok=True)
        (self.folder / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"mountains": 0.9, "urban": 0.1}}), encoding="utf-8")
        ck = viewer.build_state(self.folder)["checks"]
        self.assertEqual((ck[0]["name"], ck[0]["done"]), ("skyline", False))
        (self.folder / "fit_x.json").write_text(json.dumps({"clusters": [], "cams": [{"total": 1.0}]}), encoding="utf-8")
        self.assertTrue(viewer.build_state(self.folder)["checks"][0]["done"])
        (self.folder / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"road": 0.9}}), encoding="utf-8")
        (self.folder / "pose.json").write_text(json.dumps({"camera_ll": [40.0, 21.0], "rms_px": 2.0}), encoding="utf-8")
        ck = viewer.build_state(self.folder)["checks"]
        self.assertEqual((ck[0]["name"], ck[0]["done"], ck[0]["waived_by"]), ("street", False, ["pose.json"]))
        self.assertIn("street waived by pose.json", viewer._ps.status_line(self.folder))   # the page and `say` agree

    def write_meta(self, **changes):
        meta = json.loads((self.folder / "session.json").read_text(encoding="utf-8"))
        meta.update(changes)
        (self.folder / "session.json").write_text(json.dumps(meta), encoding="utf-8")

    def test_generated_outcome_is_done_and_detector_status_is_shown(self):
        (self.folder / "recon" / "aidet").mkdir(parents=True)
        aidet = self.folder / "recon" / "aidet" / "aidet.json"
        aidet.write_text(json.dumps({"tool": "aidet.py", "p_ai": 0.91, "threshold": 0.65, "model": "m@0123abcd"}), encoding="utf-8")
        s = viewer.build_state(self.folder)
        self.assertEqual(s["aidet"], {"p_ai": 0.91, "threshold": 0.65, "model": "m@0123abcd", "flagged": True})   # the Now card's muted line
        self.assertIsNone(s["generated_override"])
        self.write_meta(generated_override={"reason": "operator asked: it is real", "at": "2026-01-02T03:20:00+01:00"})
        self.assertEqual(viewer.build_state(self.folder)["generated_override"]["reason"], "operator asked: it is real")
        aidet.write_text(json.dumps({"tool": "aidet.py", "skipped": "timeout after 20 s"}), encoding="utf-8")
        self.assertEqual(viewer.build_state(self.folder)["aidet"], {"skipped": "timeout after 20 s"})
        self.write_meta(status="completed", result={"outcome": "generated", "latitude": None, "longitude": None, "generated": {
            "basis": "operator asked: generated", "score": 0.91, "model": "m@0123abcd", "override": None}})
        s = viewer.build_state(self.folder)
        self.assertEqual((s["status"], s["stage"], s["warning"]), ("completed", "Done", None))   # not demoted as a hand-closed session
        self.assertIsNone(s["focus"])                                                         # no place to turn the globe to
        html = viewer.export_html(self.folder).read_text(encoding="utf-8")
        self.assertIn('"outcome": "generated"', html)
        self.assertIn("Generated image: no real place", html)                                 # the page script carries the card's wording
        self.assertIn("a ranking, not a verdict", html)
        self.assertIn("Detector skipped (", html)                                             # a recorded skip, not "not run"

    def test_camera_mark_after_finish_points_to_refinish(self):
        def mark() -> str:
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(viewer.main(["mark", "camera", "--lat", "40.4863", "--lon", "21.1331", "--heading", "240", "--session", str(self.folder)]), 0)
            return err.getvalue()
        answer = {"outcome": "place", "latitude": 40.4863, "longitude": 21.1331, "heading": None}
        self.write_meta(status="completed", result=answer)
        self.assertIn("--heading 240", mark())                                               # the cone is not the answer: re-finish
        self.write_meta(result={**answer, "heading": 250.0})
        self.assertNotIn("Note:", mark())                                                    # inside the cone's field of view
        self.write_meta(result={"outcome": "generated", "latitude": None, "longitude": None})
        self.assertNotIn("Note:", mark())                                                    # no place, no heading to amend
        self.write_meta(status="pending", result=None)
        self.assertNotIn("Note:", mark())

    def test_area_marks_draw_outlines_corridors_and_levels(self):
        feats = [
            {"type": "Feature", "id": "way/1", "properties": {"name": "Central Underground Mall", "shop": "mall", "level": "-1", "layer": "-1"},
             "geometry": {"type": "LineString", "coordinates": [[126.52, 33.51], [126.53, 33.51], [126.53, 33.52], [126.52, 33.51]]}},   # closed way written as a line
            {"type": "Feature", "id": "way/2", "properties": {"highway": "corridor", "indoor": "corridor", "level": "0;1"},
             "geometry": {"type": "LineString", "coordinates": [[126.521, 33.511], [126.525, 33.512]]}},
            {"type": "Feature", "id": "way/3", "properties": {"building": "hospital", "name": "General Hospital", "addr:street": "x"},
             "geometry": {"type": "Polygon", "coordinates": [[[126.5, 33.5], [126.51, 33.5], [126.51, 33.51], [126.5, 33.5]]]}},
            {"type": "Feature", "id": "relation/4", "properties": {"indoor": "room", "level": "1", "ref": "101"},
             "geometry": {"type": "MultiPolygon", "coordinates": [[[[126.522, 33.512], [126.523, 33.512], [126.523, 33.513], [126.522, 33.512]]]]}},
            {"type": "Feature", "id": "relation/5", "properties": {"highway": "footway", "layer": "-1"},
             "geometry": {"type": "MultiLineString", "coordinates": [[[126.4, 33.4], [126.41, 33.4]], [[126.41, 33.4], [126.41, 33.41]]]}},
            {"type": "Feature", "id": "node/6", "properties": {"entrance": "yes"}, "geometry": {"type": "Point", "coordinates": [126.52, 33.51]}},
        ]
        path = self.tmp / "venue.geojson"                                                     # any osm.py geom output, inside the session or not
        path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(viewer.main(["mark", "area", str(path), "--label", "venue", "--session", str(self.folder)]), 0)
        self.assertIn("5 features", out.getvalue())
        self.assertIn("skipped 1 (Point)", out.getvalue())
        L = viewer.build_state(self.folder)["layers"]
        self.assertEqual(L["levels"], [-1, 0, 1])                                             # one chip per level, sorted numerically
        area = L["areas"][0]
        self.assertEqual((area["label"], area["dropped"]), ("venue", 0))
        f = {x["id"]: x for x in area["features"]}
        mall = f["way/1"]
        self.assertEqual((len(mall["rings"]), mall["lines"], mall["levels"], mall["dashed"]), (1, [], [-1], True))
        self.assertAlmostEqual(mall["lat"], 33.51333, places=4)                               # the label sits at the ring centroid
        self.assertAlmostEqual(mall["lon"], 126.52667, places=4)
        self.assertEqual(mall["tags"]["name"], "Central Underground Mall")
        corridor = f["way/2"]
        self.assertEqual((corridor["rings"], len(corridor["lines"]), corridor["levels"], corridor["dashed"]), ([], 1, [0, 1], False))
        self.assertEqual((corridor["tags"]["highway"], corridor["tags"]["indoor"]), ("corridor", "corridor"))
        self.assertEqual((f["way/3"]["levels"], f["way/3"]["dashed"]), ([], False))           # the footprint: no level, shown on every chip
        self.assertNotIn("addr:street", f["way/3"]["tags"])
        self.assertEqual((f["relation/4"]["levels"], f["relation/4"]["tags"]["ref"]), ([1], "101"))
        self.assertEqual((len(f["relation/5"]["lines"]), f["relation/5"]["levels"], f["relation/5"]["dashed"]), (2, [], True))   # layer -1: underground
        many = self.tmp / "many.geojson"
        many.write_text(json.dumps({"type": "FeatureCollection", "features": [feats[2]] * 520}), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            viewer.main(["mark", "area", str(many), "--level", "-2", "--session", str(self.folder)])
        self.assertIn("dropped 20", out.getvalue())                                           # the cap is logged, never silent
        capped = viewer.read_marks(self.folder)[-1]
        self.assertEqual((len(capped["features"]), capped["dropped"]), (500, 20))
        self.assertEqual((capped["features"][0]["levels"], capped["features"][0]["dashed"]), ([-2], True))   # --level for features without one
        self.assertEqual(viewer.build_state(self.folder)["layers"]["levels"], [-2, -1, 0, 1])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            viewer.main(["mark", "list", "--session", str(self.folder)])
        self.assertLess(len(out.getvalue()), 2000)                                            # list summarises an area, never dumps it
        self.assertIn("Central Underground Mall", viewer.export_html(self.folder).read_text(encoding="utf-8"))   # the offline page draws it too
        for bad in (self.tmp / "missing.geojson", self.tmp / "points.geojson"):
            if bad.name == "points.geojson":
                bad.write_text(json.dumps({"type": "FeatureCollection", "features": [feats[5]]}), encoding="utf-8")
            with self.assertRaises(SystemExit):
                viewer.main(["mark", "area", str(bad), "--session", str(self.folder)])
        self.assertEqual(viewer.main(["mark", "clear", "--kind", "area", "--session", str(self.folder)]), 0)
        self.assertEqual(viewer.build_state(self.folder)["layers"]["areas"], [])

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
