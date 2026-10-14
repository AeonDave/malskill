#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["tzdata"]
# ///
"""Archive workflow checks; all sample sessions live in temporary directories."""

from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "photo_session.py"
sys.path.insert(0, str(SCRIPT.parent))
import photo_session  # noqa: E402


class PhotoArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "original photo.jpg"
        self.source.write_bytes(b"archive test fixture; copied without modification")

    def command(self, *args, success=True, env=None):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
        )
        self.assertEqual(result.returncode, 0 if success else 1, result.stderr)
        return json.loads(result.stdout) if success else result.stderr

    def start(self):
        return self.command("start", "--root", self.root / "archives", "--image", self.source)

    def finish(self, folder, *extra, success=True):
        extra = list(extra)
        if "--heading" not in extra:
            extra += ["--heading", "unknown"]
        if "--taken" not in extra:
            extra += ["--taken", "unknown"]
        if "--accept-unverified" not in extra:
            extra += ["--accept-unverified", "operator asked: test fixture, no checks"]
        return self.command(
            "finish", folder, "--country", "Slovakia", "--region", "Prešov",
            "--city", "Poprad", "--latitude", "49.1675", "--longitude", "20.0675",
            "--confidence", "medium", *extra, success=success,
        )

    def test_preserves_original_evidence_timestamp_and_final_links(self):
        first = self.start()
        folder = Path(first["folder"])
        (folder / "report.md").write_text(f"Best estimate. Original: {first['original']}\n", encoding="utf-8")
        (folder / "evidence.jpg").write_bytes(b"evidence fixture")
        final = self.finish(folder)
        renamed = Path(final["folder"])
        self.assertFalse(folder.exists())
        self.assertEqual(first["started_at"], final["started_at"])
        self.assertTrue(renamed.name.endswith("__slovakia__presov__poprad"))
        self.assertEqual(Path(final["original"]).read_bytes(), self.source.read_bytes())
        self.assertEqual((renamed / "evidence.jpg").read_bytes(), b"evidence fixture")
        metadata = json.loads((renamed / "session.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["original"]["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(metadata["original"]["relative_path"], "original/original photo.jpg")   # POSIX form on every OS
        self.assertEqual(metadata["result"]["coordinate_system"], "WGS84")
        report = Path(final["report"]).read_text(encoding="utf-8")
        self.assertIn(str(renamed), report)
        self.assertNotIn(str(folder) + "/original/", report)
        second = self.finish(renamed)
        self.assertEqual(final["folder"], second["folder"])
        self.assertEqual(Path(second["report"]).read_text(encoding="utf-8").count("<!-- geogussr-archive -->"), 1)

    def test_linked_board_output_survives_finish_and_corrected_archive_name(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        output = folder / "nested" / "scan.json"
        output.parent.mkdir()
        output.write_text('{"hits": []}', encoding="utf-8")

        def board_command(*args):
            result = subprocess.run(
                [sys.executable, str(SCRIPT.parent / "board.py"), "--board", str(folder / "board.json"), *args],
                cwd=self.root, capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout

        board_command("clue", "Road geometry", "--kind", "infra", "--status", "observed")
        board_command("clue", "Measured output", "--kind", "terrain", "--status", "computed",
                      "--file", str(output), "--resolves", "K1")
        first = self.finish(folder)
        folder = Path(first["folder"])
        self.assertNotIn("infrastructure clue", board_command("next"))
        corrected = self.finish(folder, "--city", "Corrected")
        folder = Path(corrected["folder"])
        self.assertNotEqual(first["folder"], corrected["folder"])
        self.assertFalse(Path(first["folder"]).exists())
        data = json.loads((folder / "board.json").read_text(encoding="utf-8"))
        self.assertTrue((folder / data["clues"]["K2"]["file"]).is_file())
        self.assertNotIn("infrastructure clue", board_command("next"))
        self.assertTrue((folder / "viewer.html").is_file())

    def test_refinish_keeps_first_close_and_history(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n\n## When\nNot determinable: no dated clue.\n", encoding="utf-8")
        final = self.finish(folder)
        self.finish(Path(final["folder"]), "--heading", "240")
        meta = json.loads((Path(final["folder"]) / "session.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["completed_at"], final["completed_at"])                        # the close time is the first one
        self.assertEqual(meta["result"]["heading"], 240.0)
        self.assertEqual(len(meta["result_history"]), 1)
        self.assertIsNone(meta["result_history"][0]["result"]["heading"])                    # the replaced answer is kept
        self.assertEqual(meta["result"]["when_text"], "Not determinable: no dated clue.")     # the first footer is not part of ## When
        report = Path(final["report"]).read_text(encoding="utf-8")
        self.assertEqual(report.count("<!-- geogussr-archive -->"), 1)
        self.assertIn("Amended:", report)
        self.assertIn("heading 240°", report)

    def test_invalid_coordinates_and_missing_report_preserve_pending_folder(self):
        started = self.start()
        folder = Path(started["folder"])
        self.finish(folder, success=False)
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        for latitude in ("nan", "91", "inf"):
            self.finish(folder, "--latitude", latitude, success=False)
        self.assertTrue(folder.exists())
        self.assertEqual(json.loads((folder / "session.json").read_text(encoding="utf-8"))["status"], "pending")

    def test_existing_archive_is_never_overwritten(self):
        started = self.start()
        folder = Path(started["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        collision = folder.with_name(folder.name + "__slovakia__presov__poprad")
        collision.mkdir()
        (collision / "keep.txt").write_text("Keep this earlier archive.", encoding="utf-8")
        self.finish(folder, success=False)
        self.assertTrue(folder.exists())
        self.assertEqual((collision / "keep.txt").read_text(encoding="utf-8"), "Keep this earlier archive.")

    def test_several_photos_of_one_scene_share_a_session(self):
        second = self.root / "second.jpg"
        second.write_bytes(b"second photo")
        other = self.root / "sub"
        other.mkdir()
        (other / "original photo.jpg").write_bytes(b"same file name, other bytes")
        out = self.command("start", "--root", self.root / "archives", "--image", self.source, "--image", second,
                           "--image", other / "original photo.jpg")
        folder = Path(out["folder"])
        meta = json.loads((folder / "session.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["original"]["relative_path"], "original/original photo.jpg")      # first = reference
        self.assertEqual([r["relative_path"] for r in meta["originals"]],
                         ["original/original photo.jpg", "original/second.jpg", "original/original photo_3.jpg"])
        self.assertEqual(len(out["originals"]), 3)
        for record in meta["originals"]:
            self.assertTrue((folder / record["relative_path"]).is_file())
        self.assertEqual(len({r["sha256"] for r in meta["originals"]}), 3)
        self.assertIn("original/second.jpg", (folder / "report.md").read_text(encoding="utf-8").splitlines()[0])
        single = json.loads((Path(self.start()["folder"]) / "session.json").read_text(encoding="utf-8"))
        self.assertNotIn("originals", single)

    def test_start_creates_the_board_and_recon_feeds_it(self):
        folder = Path(self.start()["folder"])
        board = json.loads((folder / "board.json").read_text(encoding="utf-8"))
        self.assertEqual(board["candidates"], {})
        self.assertEqual(board["photo"], "original/original photo.jpg")
        recon_dir = folder / "recon"
        recon_dir.mkdir()
        (recon_dir / "textgeo.json").write_text(json.dumps({"tool": "textgeo", "signals": [
            {"clue": "Greek script on a sign", "kind": "text", "status": "inferred", "level": "country", "lr": {"Greece": 5, "Cyprus": 2}}]}), encoding="utf-8")
        import recon
        lines = recon.ingest_into_board(recon_dir)
        self.assertEqual(len(lines), 1, lines)
        board = json.loads((folder / "board.json").read_text(encoding="utf-8"))
        self.assertEqual(set(board["candidates"]), {"Greece", "Cyprus"})
        self.assertTrue(board["clues"])
        self.assertEqual(recon.ingest_into_board(self.root / "nowhere"), [])

    def test_finish_without_coordinates_pins_the_country_centre(self):
        folder = Path(self.start()["folder"])
        report = (folder / "report.md").read_text(encoding="utf-8")
        for marker in ("<!-- fill: ranked countries with percentages and the cues behind each; region hunch; what would change your mind; Plan: A. B. C. the most selective fixed features, each → what it can leave → its route (no percentages) -->",
                       "<!-- fill: country / region / city, coordinates (WGS84; GCJ-02 too in mainland China), confidence per level, radius and what it rests on -->"):
            report = report.replace(marker, "1. Namibia 80% — yellow edge lines, red sand" if "ranked" in marker else "Namibia, country level only")
        report = report.replace('<!-- fill: year or year range, season, date, time of day: each with the clue and the file it rests on; "not determinable" with the reason when it is -->',
                                "not determinable: no metadata, no dated imagery checked")
        (folder / "report.md").write_text(report, encoding="utf-8")
        out = self.command("finish", folder, "--country", "Namibia", "--city", "unknown", "--confidence", "medium", "--radius-m", "500", "--heading", "unknown", "--taken", "unknown", "--accept-unverified", "operator asked: stop (test)")
        meta = json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))
        r = meta["result"]
        self.assertTrue(-29 < r["latitude"] < -16 and 11 < r["longitude"] < 26, r)       # inside Namibia
        self.assertEqual(r["confidence"], "low")                                            # forced down
        self.assertGreaterEqual(r["radius_m"], 100000)                                       # never narrower than the country
        self.assertIn("country centre", r["coordinate_source"])
        self.assertEqual(r["verification_artifacts"], 0)
        self.assertIn("country centre", (Path(out["folder"]) / "report.md").read_text(encoding="utf-8"))
        self.assertTrue((Path(out["folder"]) / "viewer.html").is_file())        # offline snapshot beside the photos
        folder2 = Path(self.start()["folder"])
        (folder2 / "report.md").write_text(report, encoding="utf-8")
        err = self.command("finish", folder2, "--country", "Atlantis", "--city", "x", "--confidence", "low", "--heading", "unknown", "--taken", "unknown", "--accept-unverified", "operator asked: stop (test)", success=False)
        self.assertIn("Unknown country", err)
        err = self.command("finish", folder2, "--country", "Namibia", "--city", "x", "--confidence", "low", "--latitude", "-22", "--heading", "unknown", "--taken", "unknown", "--accept-unverified", "operator asked: stop (test)", success=False)
        self.assertIn("both", err)
        r = subprocess.run([sys.executable, str(SCRIPT), "finish", str(folder2), "--country", "Namibia", "--city", "x", "--confidence", "low", "--taken", "unknown"],
                           cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 2)                                                    # argparse: --heading is required
        self.assertIn("--heading", r.stderr)                                                 # the camera direction must be stated, even as unknown
        err = self.command("finish", folder2, "--country", "Namibia", "--city", "x", "--confidence", "low", "--heading", "east", "--taken", "unknown", "--accept-unverified", "operator asked: stop (test)", success=False)
        self.assertIn("degrees", err)

    def test_viewer_port_falls_back_when_taken(self):
        import socket
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen(1)
            taken = busy.getsockname()[1]
            chosen = photo_session._free_port(taken)
            self.assertNotEqual(chosen, taken)
            self.assertGreater(chosen, 0)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free = probe.getsockname()[1]
        self.assertEqual(photo_session._free_port(free), free)

    def test_viewer_is_launched_without_a_console_window(self):
        calls = []
        real = photo_session.subprocess.Popen
        photo_session.subprocess.Popen = lambda cmd, **kw: calls.append((cmd, kw))
        try:
            url = photo_session.launch_viewer(self.root, 0)
        finally:
            photo_session.subprocess.Popen = real
        cmd, kw = calls[0]
        self.assertIn("serve", cmd)
        self.assertEqual(kw["cwd"], str(self.root.parent))                       # never inside the session folder
        if os.name == "nt":
            self.assertTrue(kw["creationflags"] & 0x08000000)                     # CREATE_NO_WINDOW: no black console to close
            self.assertFalse(kw["creationflags"] & 0x00000008)                    # not DETACHED_PROCESS
        else:
            self.assertTrue(kw["start_new_session"])
        self.assertTrue(url.startswith("http://127.0.0.1:"))

    def test_verification_artifacts_ignore_recon_and_count_rank_files(self):
        folder = Path(self.start()["folder"])
        (folder / "recon" / "detect").mkdir(parents=True)
        (folder / "recon" / "detect" / "detect_sheet.jpg").write_bytes(b"x")                 # the first pass is not a check
        self.assertEqual(photo_session.count_verification_artifacts(folder), 0)
        (folder / "rank_123456.json").write_text("[]", encoding="utf-8")
        (folder / "r_rank_views").mkdir()
        (folder / "r_rank_views" / "01.jpg").write_bytes(b"x")
        self.assertEqual(photo_session.count_verification_artifacts(folder), 2)
        self.assertTrue(photo_session._same_country("Italy", "IT"))
        self.assertTrue(photo_session._same_country("Russian Federation", "RU") or photo_session._same_country("Russia", "RUS"))
        self.assertFalse(photo_session._same_country("Italy", "France"))
        self.assertIsNone(photo_session._same_country(None, "IT"))
        pending = self.command("start", "--root", self.root / "archives")                     # no --image: still a board
        self.assertTrue((Path(pending["folder"]) / "board.json").is_file())

    def test_beside_puts_the_session_next_to_the_photo(self):
        out = self.command("start", "--image", self.source, "--beside")
        folder = Path(out["folder"])
        self.assertEqual(folder.parent, self.source.parent)
        self.assertTrue((folder / "original" / self.source.name).is_file())
        self.assertTrue(self.source.is_file())                                             # the photo itself is untouched
        err = self.command("start", "--beside", "--root", self.root / "archives", success=False)
        self.assertIn("--beside needs --image", err)

    def test_taken_is_recorded_and_scored(self):
        self.assertEqual(photo_session.parse_taken("2019")["from"], "2019-01-01")
        self.assertEqual(photo_session.parse_taken("2019")["to"], "2019-12-31")
        self.assertEqual(photo_session.parse_taken("2019-06..2019-09")["to"], "2019-09-30")
        t = photo_session.parse_taken("2019-06-21T14:30")
        self.assertEqual((t["from"], t["to"], t["time"]), ("2019-06-21", "2019-06-21", "14:30"))
        with self.assertRaises(ValueError):
            photo_session.parse_taken("summer 2019")
        with self.assertRaises(ValueError):
            photo_session.parse_taken("2020..2019")
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        out = self.finish(folder, "--taken", "2019-06..2019-09", "--taken-confidence", "medium", "--taken-basis", "leaves full, sun high, 2018 pano lacks the kiosk")
        r = json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual(r["taken"]["from"], "2019-06-01")
        self.assertEqual(r["taken"]["confidence"], "medium")
        self.assertIn("Taken: 2019-06..2019-09", (Path(out["folder"]) / "report.md").read_text(encoding="utf-8"))
        scored = self.command("truth", out["folder"], "--latitude", "49.1675", "--longitude", "20.0675", "--country", "Slovakia", "--taken", "2019-07-14")
        self.assertTrue(scored["truth"]["taken_hit"])
        self.assertEqual(scored["truth"]["taken_error_days"], 0)
        scored = self.command("truth", out["folder"], "--latitude", "49.1675", "--longitude", "20.0675", "--country", "Slovakia", "--taken", "2020-01-10")
        self.assertFalse(scored["truth"]["taken_hit"])
        self.assertEqual(scored["truth"]["taken_error_days"], 102)
        board = self.command("scoreboard", "--root", self.root / "archives")
        self.assertEqual(board["taken_hit_rate"], 0.0)

    def test_open_ranges_when_text_and_heading_hint(self):
        self.assertEqual(photo_session.parse_taken("2015..")["from"], "2015-01-01")
        self.assertGreaterEqual(photo_session.parse_taken("2015..")["to"], "2026-01-01")
        self.assertEqual(photo_session.parse_taken("..2019")["to"], "2019-12-31")
        with self.assertRaises(ValueError):
            photo_session.parse_taken("..")
        folder = Path(self.start()["folder"])
        report = (folder / "report.md").read_text(encoding="utf-8")
        report = report.replace("## When\n<!-- fill: year or year range, season, date, time of day: each with the clue and the file it rests on; \"not determinable\" with the reason when it is -->",
                                "## When\nSeason: spring (full leaf). Year: unknown; top panoramas are from May 2015, so 2015 or later.")
        report = report.replace("## Gut call (before tools)\n<!-- fill:", "## Gut call (before tools)\nSlovakia 60%\n<!--").replace("## Answer\n<!-- fill:", "## Answer\nPoprad\n<!--")
        (folder / "report.md").write_text(report, encoding="utf-8")
        (folder / "m_rank.json").write_text(json.dumps([{"rank": 1, "id": "x", "heading": 120, "inliers": 14, "score_global": 0.2, "wgs": [49.1680, 20.0680]}]), encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPT), "finish", str(folder), "--country", "Slovakia", "--city", "Poprad", "--latitude", "49.1675",
                            "--longitude", "20.0675", "--confidence", "medium", "--heading", "unknown", "--taken", "unknown"],
                           cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("name 2015", r.stderr)                                                  # the report knew a year
        self.assertIn("looks at 120", r.stderr)                                               # the best match nearby had a heading
        self.assertIn("geo.py frame", r.stderr)                                               # and the landmark route is named
        self.assertIn("--anchor", r.stderr)
        out = json.loads(r.stdout)
        res = json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertIsNone(res["heading"])
        self.assertEqual(res["heading_hint"]["heading"], 120.0)
        self.assertIn("2015 or later", res["when_text"])
        footer = (Path(out["folder"]) / "report.md").read_text(encoding="utf-8")
        self.assertIn("suggested, not asserted", footer)
        self.assertIn("Taken: not given (report: Season: spring", footer)

    def test_taken_note_does_not_push_a_reference_date(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n\n## When\nNot determinable; the 2026-03-05 reference panorama does not date the photo.\n",
                                          encoding="utf-8")
        r = self.run_cli("finish", folder, "--country", "Slovakia", "--city", "Poprad", "--latitude", "49.1675", "--longitude", "20.0675",
                         "--confidence", "medium", "--heading", "unknown", "--taken", "unknown", "--accept-unverified", "operator asked: test fixture")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("dates or bounds this photo", r.stderr)                                 # encode a year only when it dates the photo
        self.assertIn("2026", r.stderr)
        res = json.loads((Path(json.loads(r.stdout)["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertIsNone(res["taken"])

    def test_finish_refuses_an_unverified_answer_before_the_clock(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPT), "finish", str(folder), "--country", "Austria", "--city", "Plansee", "--latitude", "47.55",
                            "--longitude", "10.79", "--confidence", "low", "--heading", "unknown", "--taken", "unknown"],
                           cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not an answer yet", r.stderr)
        self.assertIn("terrain.py", r.stderr)
        self.assertIn('--accept-unverified "<reason>" (before 25 min only when the operator stopped or redirected the analysis: '
                      'put "operator asked: …" in the reason', r.stderr)
        self.assertNotIn("budget is gone", r.stderr)                                           # the Quick budget is no exit
        self.assertTrue(folder.is_dir())                                                        # nothing renamed
        (folder / "shore_rank.json").write_text("[]", encoding="utf-8")                          # one check later, it closes
        out = self.command("finish", folder, "--country", "Austria", "--city", "Plansee", "--latitude", "47.55", "--longitude", "10.79",
                           "--confidence", "low", "--heading", "unknown", "--taken", "unknown")
        res = json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual(res["verification_artifacts"], 1)
        self.assertIsNone(res["accepted_unverified"])
        folder2 = Path(self.start()["folder"])
        (folder2 / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        out = self.command("finish", folder2, "--country", "Austria", "--city", "x", "--latitude", "47.55", "--longitude", "10.79",
                           "--confidence", "low", "--heading", "unknown", "--taken", "unknown", "--accept-unverified", "operator asked: stop the run")
        res = json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual(res["accepted_unverified"], "operator asked: stop the run")

    def test_quick_budget_is_not_a_reason_to_close_unverified(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPT), "finish", str(folder), "--country", "Italy", "--city", "unknown", "--latitude", "42.9",
                            "--longitude", "11.9", "--confidence", "low", "--heading", "unknown", "--taken", "unknown",
                            "--accept-unverified", "Quick budget: no GPS, no text, no matching skyline"],
                           cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 1)
        self.assertIn("go Deep", r.stderr)
        self.assertIn('put "operator asked: …" in the reason', r.stderr)
        self.assertTrue(folder.is_dir())
        out = self.command("finish", folder, "--country", "Italy", "--city", "unknown", "--latitude", "42.9", "--longitude", "11.9",
                           "--confidence", "low", "--heading", "unknown", "--taken", "unknown", "--accept-unverified", "operator asked: stop the analysis")
        res = json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual(res["accepted_unverified"], "operator asked: stop the analysis")
        folder3 = Path(self.start()["folder"])
        (folder3 / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        out = self.command("finish", folder3, "--country", "Italy", "--city", "unknown", "--latitude", "42.9", "--longitude", "11.9",
                           "--confidence", "low", "--heading", "unknown", "--taken", "unknown", "--accept-unverified", "operator asked: the answer now")
        res = json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual(res["accepted_unverified"], "operator asked: the answer now")      # the operator outranks the gate

    def test_scene_checks_gate_finish(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        (folder / "recon" / "prior").mkdir(parents=True, exist_ok=True)
        (folder / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"mountains": 0.93, "water": 0.88, "urban": 0.1, "road": 0.2, "text": 0.05, "indoor": 0.02}}), encoding="utf-8")
        (folder / "refsheet_alps.jpg").write_bytes(b"\xff\xd8\xff\xd9")                       # an artifact, but not the skyline
        req = photo_session.required_checks(folder)
        self.assertEqual([c["name"] for c in req], ["skyline"])
        self.assertFalse(req[0]["done"])
        base = ["--country", "Italy", "--city", "x", "--latitude", "46.2", "--longitude", "10.9", "--confidence", "low", "--heading", "unknown", "--taken", "unknown"]
        r = subprocess.run([sys.executable, str(SCRIPT), "finish", str(folder), *base], cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Required check 'skyline'", r.stderr)
        self.assertIn('--skip-check skyline:"<reason>" (before 25 min only when the operator stopped or redirected', r.stderr)
        r = subprocess.run([sys.executable, str(SCRIPT), "finish", str(folder), *base, "--skip-check", "skyline:Quick budget spent"],
                           cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 1)                                                     # the budget is not a reason
        self.assertIn('only for an analysis the operator stopped or redirected: put "operator asked: …" in the reason', r.stderr)
        self.assertIn("Next: run terrain.py ridge → fit", r.stderr)                           # and the work that closes it instead
        (folder / "fit_region.json").write_text(json.dumps({"clusters": [], "cams": [{"total": 1.0}]}), encoding="utf-8")   # fit output: closes
        self.assertTrue(photo_session.required_checks(folder)[0]["done"])
        out = self.command("finish", folder, *base)
        res = json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual(res["checks"][0]["name"], "skyline")
        self.assertTrue(res["checks"][0]["done"])
        self.assertEqual(res["verification_artifacts"], 2)                                      # refsheet + fit
        folder2 = Path(self.start()["folder"])
        (folder2 / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        (folder2 / "recon" / "prior").mkdir(parents=True, exist_ok=True)
        (folder2 / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"mountains": 0.9, "urban": 0.7, "road": 0.8}}), encoding="utf-8")
        self.assertEqual([c["name"] for c in photo_session.required_checks(folder2)], ["skyline", "street"])
        out = self.command("finish", folder2, *base, "--skip-check", "skyline:operator asked: stop the analysis", "--skip-check", "street:operator asked: stop the analysis",
                           "--accept-unverified", "operator asked: stop the analysis")
        res = json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual([c["skipped"] for c in res["checks"]], ["operator asked: stop the analysis"] * 2)
        self.assertEqual(photo_session.checks_for_scene({"indoor": 0.9, "mountains": 0.9}), [])
        self.assertEqual(photo_session.checks_for_scene(None), [])

    def test_an_operator_redirect_closes_a_check_early_and_is_recorded(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        (folder / "recon" / "prior").mkdir(parents=True, exist_ok=True)
        (folder / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"mountains": 0.9}}), encoding="utf-8")
        err = self.finish(folder, "--skip-check", "skyline:redirected to Lago X", success=False)
        self.assertIn('put "operator asked: …" in the reason', err)                           # the wording that closes it, not a ban
        self.assertNotIn("user stopped", err)
        out = self.finish(folder, "--skip-check", "skyline:operator asked: skip the skyline, it is Lago X")
        res = json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual(res["checks"][0]["skipped"], "operator asked: skip the skyline, it is Lago X")
        self.assertIsNone(res["checks"][0]["waived_by"])

    def test_early_exit_takes_the_operator_words_at_the_start(self):
        words = photo_session.OPERATOR_WORDS.match
        for said in ("operator asked: stop", "User said: give me the answer", " operator confirmed: Quick only", "utente ha chiesto: fermati",
                     "operatore ha detto: basta così", "usuario dijo: para", "utilisateur a demandé : arrête", "Benutzer hat gesagt: Schluss",
                     "The operator asked: give me what you have", "L'utente ha chiesto: fermati", "L’utente ha chiesto: fermati",
                     "l'operatore ha detto: basta", "el usuario dijo: para", "operador pidió: para", "l'utilisateur a demandé : arrête",
                     "opérateur a demandé : arrête", "der Benutzer hat gesagt: Schluss", "Nutzer hat gesagt: Schluss",
                     "operator requested: Quick only"):
            self.assertTrue(words(said), said)
        for agent in ("the user would want a quick answer", "operator's 40-minute hard limit", "operator asked for the answer now",
                      "user stopped the run", "users said: stop", "budget gone; operator asked: stop", "the users said: stop",
                      "l'utente vorrebbe: una risposta rapida"):
            self.assertFalse(words(agent), agent)
        base = ["--country", "Italy", "--city", "x", "--latitude", "46.2", "--longitude", "10.9", "--confidence", "low", "--heading", "unknown",
                "--taken", "unknown"]
        form = 'put "operator asked: …" in the reason as its first words'
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        r = self.run_cli("finish", folder, *base, "--accept-unverified", "the user would want a quick answer")
        self.assertEqual(r.returncode, 1)                                                     # the agent's paraphrase is not the operator
        self.assertIn(form, r.stderr)                                                         # the exact form that closes it
        self.assertIn('"utente ha chiesto: …"', r.stderr)
        out = self.command("finish", folder, *base, "--accept-unverified", "operator asked: stop")
        self.assertEqual(json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]["accepted_unverified"],
                         "operator asked: stop")
        folder2 = Path(self.start()["folder"])
        (folder2 / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        (folder2 / "recon" / "prior").mkdir(parents=True, exist_ok=True)
        (folder2 / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"mountains": 0.9}}), encoding="utf-8")
        r = self.run_cli("finish", folder2, *base, "--skip-check", "skyline:the user would want a quick answer",
                         "--accept-unverified", "utente ha chiesto: fermati qui")
        self.assertEqual(r.returncode, 1)
        self.assertIn(form, r.stderr)
        out = self.command("finish", folder2, *base, "--skip-check", "skyline:utente ha chiesto: fermati qui",
                           "--accept-unverified", "utente ha chiesto: fermati qui")             # the operator's own language closes too
        res = json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual((res["checks"][0]["skipped"], res["accepted_unverified"]), ("utente ha chiesto: fermati qui",) * 2)
        folder3 = Path(self.start()["folder"])
        (folder3 / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        out = self.command("finish", folder3, *base, "--accept-unverified", "L'operatore ha chiesto: fermati qui")   # with its article
        self.assertEqual(json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]["accepted_unverified"],
                         "L'operatore ha chiesto: fermati qui")

    def test_accept_unverified_is_recorded_beside_check_files(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        (folder / "shore_rank.json").write_text("[]", encoding="utf-8")                         # a check ran and matched nothing
        r = self.run_cli("finish", folder, "--country", "Austria", "--city", "Reutte", "--latitude", "47.55", "--longitude", "10.79",
                         "--confidence", "low", "--heading", "unknown", "--taken", "unknown", "--accept-unverified", "the sheets matched nothing")
        self.assertEqual(r.returncode, 0, r.stderr)                                           # never refused while a check file exists
        self.assertIn("--accept-unverified recorded (the sheets matched nothing)", r.stderr)
        res = json.loads((Path(json.loads(r.stdout)["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual(res["verification_artifacts"], 1)
        self.assertEqual(res["accepted_unverified"], "the sheets matched nothing")

    def test_supporting_artifacts_count_apart_from_executed_checks(self):
        near, far, jpg = [46.2005, 10.9005], [46.218, 10.9], b"\xff\xd8\xff\xd9"            # ~68 m and ~2 km from 46.2, 10.9

        def fit(bbox=None, cam=(46.2, 10.9)):
            best = {"cam": list(cam), "total": 0.7}
            tie = {"n": 5, "span_m": 400.0, "bearing": 90.0, "delta": 0.03, **({"bbox": bbox} if bbox else {"n": 1, "span_m": 0.0})}
            other = {"cam": [47.0, 11.0], "total": 0.9}
            return {"params": {"grid_m": 100}, "cams": [best, other],
                    "clusters": [{"hit": 0, "rank": 1, "best": best, "tie": tie},
                                 {"hit": 1, "rank": 2, "best": other, "tie": {"n": 3, "bbox": [46.99, 10.99, 47.01, 11.01]}}]}

        def row(wgs, inliers, score):
            return {"rank": 1, "id": "p1", "heading": None, "inliers": inliers, "score_global": score, "wgs": wgs}

        def support(files, at=(46.2, 10.9)):
            return photo_session.supporting_artifacts(self.scene_folder({}, files), at)
        self.assertEqual(support({"fit.json": fit(bbox=[46.199, 10.895, 46.201, 10.905])}), ["fit.json"])   # the pin inside the tie stretch
        self.assertEqual(support({"fit.json": fit(bbox=[46.199, 10.901, 46.201, 10.91])}), ["fit.json"])    # 77 m off it: within one grid step
        self.assertEqual(support({"fit.json": fit(bbox=[46.199, 10.908, 46.201, 10.92])}), [])              # 620 m off it
        self.assertEqual(support({"fit.json": fit(cam=(46.2005, 10.9))}), ["fit.json"])                     # one tied position: the best camera
        self.assertEqual(support({"fit.json": fit(cam=(46.21, 10.9))}), [])
        self.assertEqual(support({"fit.json": fit(bbox=[46.199, 10.895, 46.201, 10.905])}, at=(47.0, 11.0)), [])   # a lower cluster's stretch
        ran = {"far_rank.json": [row(far, 40, 0.6)], "around.jpg": jpg, "around.index.json": [{"id": "abc", "heading": 90.0}],
               "refsheet_alps.jpg": jpg, "ridge.json": {"ridge": [[0, 10]]}}
        self.assertEqual(support(ran), [])                                                    # checks that ran, none placing the answer
        self.assertEqual(support({"a_rank.json": [row(near, 12, 0.2)]}), ["a_rank.json"])
        self.assertEqual(sorted(support({"evidence.jpg": jpg, "pose.json": {"camera_ll": [46.2003, 10.9004]}})), ["evidence.jpg", "pose.json"])
        far_pose = {"pose.json": {"camera_ll": [46.65, 11.35]}}                             # a solve for a candidate 61 km away
        self.assertEqual(support(far_pose), [])
        self.assertEqual(photo_session.pinning_artifacts(self.scene_folder({}, far_pose), (46.2, 10.9)), ["pose.json"])   # the waiver: by content

        def swept(wgs, sim, k=1):
            return {"rank": k, "area_rank": k, "key": f"kakao:p{k}", "provider": "kakao", "id": f"p{k}", "lat": wgs[0], "lon": wgs[1],
                    "score": 2.1, "area_score": 2.4, "sim_full": sim, "best_bearing": 90.0}
        self.assertEqual(support({"sweep/ranked.json": [swept(near, 0.62)]}), ["sweep/ranked.json"])   # sweep.py rank: lat/lon, sim_full
        self.assertEqual(support({"sweep/ranked.json": [swept(near, 0.12)]}), [])                     # near, but weak
        self.assertEqual(support({"sweep/ranked.json": [swept(far, 0.62)]}), [])                      # strong, but 2 km away
        self.assertEqual(support({"sweep/ranked.json": [swept(far, 0.3, k) for k in range(1, 11)] + [swept(near, 0.62, 11)]}), [])  # top 10
        base = ["--country", "Italy", "--city", "x", "--latitude", "46.2", "--longitude", "10.9", "--confidence", "low", "--heading", "unknown",
                "--taken", "unknown"]
        line = ("Warning: no check supports this location: the answer is an unverified estimate. Next: record the match that places it, "
                "evidence.py match.json --out match.jpg --match against the sheet cell or sweep view that shows the place (or terrain.py fit "
                "--at 46.20000,10.90000 --ridge <ridge.json> for a skyline); otherwise say so in the answer, or --accept-unverified \"<reason>\".")
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        (folder / "recon" / "prior").mkdir(parents=True, exist_ok=True)
        (folder / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"road": 0.9}}), encoding="utf-8")
        for rel, body in ran.items():
            (folder / rel).write_bytes(body if isinstance(body, bytes) else json.dumps(body).encode("utf-8"))
        r = self.run_cli("finish", folder, *base)
        self.assertEqual(r.returncode, 0, r.stderr)                                           # no refusal: the line says what the answer is
        self.assertIn(line, r.stderr)
        res = json.loads((Path(json.loads(r.stdout)["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertTrue(res["checks"][0]["done"])                                             # the street check ran
        self.assertGreaterEqual(res["verification_artifacts"], 3)
        self.assertEqual(res["supporting_artifacts"], 0)
        self.assertIsNone(res["accepted_unverified"])
        folder2 = Path(self.start()["folder"])
        (folder2 / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        (folder2 / "near_rank.json").write_text(json.dumps([row(near, 12, 0.2)]), encoding="utf-8")
        r = self.run_cli("finish", folder2, *base)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(line, r.stderr)
        res = json.loads((Path(json.loads(r.stdout)["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual((res["verification_artifacts"], res["supporting_artifacts"]), (1, 1))
        folder3 = Path(self.start()["folder"])
        (folder3 / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        (folder3 / "recon" / "prior").mkdir(parents=True, exist_ok=True)
        (folder3 / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"urban": 0.9, "road": 0.9}}), encoding="utf-8")
        (folder3 / "sweep").mkdir()
        (folder3 / "sweep" / "ranked.json").write_text(json.dumps([swept(near, 0.62), swept(far, 0.4, 2)]), encoding="utf-8")
        r = self.run_cli("finish", folder3, *base[:8], "--confidence", "high", *base[10:])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("no check supports", r.stderr)                                       # the sweep's rank 1 at the answer supports it
        res = json.loads((Path(json.loads(r.stdout)["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual((res["confidence"], res["supporting_artifacts"]), ("high", 1))

    def test_finish_prints_the_stored_result_keys(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        r = self.run_cli("finish", folder, "--country", "South Korea", "--region", "Jeju", "--city", "Jeju City", "--latitude", "33.5131",
                         "--longitude", "126.5263", "--confidence", "low", "--radius-m", "4000", "--heading", "215", "--taken", "2019..",
                         "--accept-unverified", "operator asked: test fixture")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Stored result: country="South Korea", region="Jeju", city_or_nearest_locality="Jeju City", latitude=33.5131, '
                      'longitude=126.5263, radius_m=4000.0, confidence="low", heading=215.0, taken="2019.."\n', r.stderr)

    def test_pinning_artifact_waives_a_scene_check(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        (folder / "recon" / "prior").mkdir(parents=True, exist_ok=True)
        (folder / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"mountains": 0.9}}), encoding="utf-8")
        (folder / "shop_rank.json").write_text(json.dumps([{"rank": 1, "id": "p1", "heading": None, "inliers": 14, "score_global": 0.2,
                                                            "wgs": [46.2005, 10.9005]}]), encoding="utf-8")   # a sign named the shop; match.py pinned it 68 m away
        self.assertEqual(photo_session.pinning_artifacts(folder, (46.2, 10.9)), ["shop_rank.json"])
        self.assertEqual(photo_session.pinning_artifacts(folder), [])                         # a rank file pins only an answer
        out = self.command("finish", folder, "--country", "Italy", "--city", "x", "--latitude", "46.2", "--longitude", "10.9",
                           "--confidence", "medium", "--heading", "unknown", "--taken", "unknown")
        res = json.loads((Path(out["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual(res["checks"][0]["waived_by"], ["shop_rank.json"])
        self.assertFalse(res["checks"][0]["done"])
        folder2 = Path(self.start()["folder"])
        (folder2 / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        (folder2 / "recon" / "prior").mkdir(parents=True, exist_ok=True)
        (folder2 / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"mountains": 0.9}}), encoding="utf-8")
        (folder2 / "refsheet_alps.jpg").write_bytes(b"\xff\xd8\xff\xd9")                     # a reference sheet pins nothing
        r = subprocess.run([sys.executable, str(SCRIPT), "finish", str(folder2), "--country", "Italy", "--city", "x", "--latitude", "46.2",
                            "--longitude", "10.9", "--confidence", "low", "--heading", "unknown", "--taken", "unknown"],
                           cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Required check 'skyline'", r.stderr)

    def scene_folder(self, scene, files):
        """A bare folder with recon's scene tags and the given files (bytes as written, anything else as JSON)."""
        folder = Path(tempfile.mkdtemp(dir=self.root))
        files = {"recon/prior/prior.json": {"scene": scene}, **files}
        for rel, body in files.items():
            (folder / rel).parent.mkdir(parents=True, exist_ok=True)
            (folder / rel).write_bytes(body if isinstance(body, bytes) else json.dumps(body).encode("utf-8"))
        return folder

    def test_rank_file_waives_only_with_a_near_fair_top_view(self):
        near, far = [46.2005, 10.9005], [46.218, 10.9]                                       # ~68 m and ~2 km from 46.2, 10.9

        def row(rank, wgs, inliers, score, **extra):
            return {"rank": rank, "id": f"p{rank}", "heading": None, "inliers": inliers, "score_global": score, "wgs": wgs, **extra}

        def pins(name, rows):
            return photo_session.pinning_artifacts(self.scene_folder({}, {name: rows}), (46.2, 10.9))
        self.assertEqual(pins("a_rank.json", []), [])
        self.assertEqual(pins("a_rank.json", [row(1, far, 40, 0.6)]), [])                    # strong, but 2 km away
        self.assertEqual(pins("a_rank.json", [row(1, near, 3, 0.1)]), [])                    # near, but weak
        self.assertEqual(pins("a_rank.json", [row(1, far, 40, 0.6), row(2, near, 3, 0.1), row(3, near, 12, 0.2)]), ["a_rank.json"])
        self.assertEqual(pins("ranked.json", [row(1, near, None, 0.31)]), ["ranked.json"])     # any name; fair by score alone
        twelve = [row(k, far, 0, 0.1) for k in range(1, 12)] + [row(12, near, 20, 0.5)]
        self.assertEqual(pins("b_rank.json", twelve), [])                                     # no saved views: the first 10 only
        self.assertEqual(pins("b_rank.json", [dict(r, view=f"b_rank_views/{r['rank']:02d}.jpg") for r in twelve]), ["b_rank.json"])
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        (folder / "recon" / "prior").mkdir(parents=True)
        (folder / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"mountains": 0.9}}), encoding="utf-8")
        (folder / "far_rank.json").write_text(json.dumps([row(1, far, 40, 0.6, view="far_rank_views/01_p1.jpg"), row(2, near, 3, 0.1)]),
                                              encoding="utf-8")
        err = self.finish(folder, "--latitude", "46.2", "--longitude", "10.9", success=False)
        self.assertIn("Required check 'skyline'", err)
        self.assertIn("far_rank.json #1", err)                                                # the best view, its distance and scores
        self.assertIn("40 inliers", err)
        self.assertIn("open far_rank_views/01_p1.jpg", err)
        self.assertIn("only if it shows the same fixed structures as the photo, answer there", err)
        self.assertNotIn("--latitude", err)                                                   # the gate is never a coordinate source
        self.assertNotIn("46.218", err)
        self.assertIn("--skip-check skyline:", err)
        (folder / "far_rank.json").write_text(json.dumps([row(1, near, 3, 0.1)]), encoding="utf-8")
        err = self.finish(folder, "--latitude", "46.2", "--longitude", "10.9", success=False)
        self.assertIn("too weak", err)
        self.assertNotIn("answer there", err)                                                 # a weak view is no place to move to

    def test_pins_are_evidence_images_by_name_and_pose_output_by_content(self):
        solve = {"camera_ll": [46.2003, 10.9004], "height": 31.0, "heading": 212.5, "rms_px": 2.1, "points": 4}
        check = {"candA": {"rms_px": 3.0, "delta_chi2": 0.0, "robust_delta_chi2": 0.0, "robust_by": "all_points"},
                 "candB": {"rms_px": 9.0, "delta_chi2": 40.1, "robust_delta_chi2": 12.5, "robust_by": "drop spire"}}
        spec = {"image_size": [1476, 827], "points": [{"name": "spire", "px": [1180, 120], "ll": [46.2, 10.9], "h": 620}],
                "init": {"at": [46.2, 10.9], "height": 30}, "fix": ["hfov"]}
        pinned = {"evidence_1.jpg": b"x", "match.png": b"x", "pose.json": solve, "cam/solution.json": solve, "pose_check.json": check}
        loose = {"pose_spec.json": spec, "spec_pose.json": spec, "candA_pose.json": {}, "candA-pose.png": b"x",
                 "intersect_spec.json": {"a": "SS 12"}, "intersect.json": [{"lat": 46.2, "lon": 10.9, "a": "SS 12", "b": "SP 7"}],
                 "sat_scan_spec.json": {"query": "silo"}, "sat_scan.json": [{"cell": 7, "lat": 46.2, "lon": 10.9, "score": 0.4, "rank": 1}],
                 "proposed.json": [], "purpose_notes.json": [], "match_spec.json": [], "evidence_spec.json": [], "rank_1.json": [], "x_rank.json": []}
        folder = self.scene_folder({}, {**pinned, **loose})
        self.assertEqual(sorted(photo_session.pinning_artifacts(folder)), sorted(pinned))
        self.assertEqual(sorted(photo_session.pinning_artifacts(folder, (46.2, 10.9))), sorted(pinned))

    def test_heading_hint_and_waiver_read_the_same_top_views(self):
        near, far = [46.2005, 10.9005], [46.218, 10.9]
        rows = [{"rank": k, "id": f"p{k}", "heading": 10.0 * k, "inliers": 2, "score_global": 0.1, "wgs": far} for k in (1, 2)]
        rows.append({"rank": 3, "id": "p3", "heading": 250.0, "inliers": 20, "score_global": 0.3, "wgs": near})
        folder = self.scene_folder({"mountains": 0.9}, {"r_rank.json": rows, "original/x_rank.json": [dict(rows[2], heading=90.0, inliers=40)]})
        self.assertEqual(photo_session.pinning_artifacts(folder, (46.2, 10.9)), ["r_rank.json"])
        hint = photo_session.heading_hint(folder, 46.2, 10.9)
        self.assertEqual((hint["heading"], hint["source"], hint["inliers"]), (250.0, "r_rank.json", 20))   # row #3; originals are not walked
        self.assertEqual(photo_session.ranked_headings(folder), ["10° (r_rank.json)"])
        with patch.object(photo_session, "JSON_MAX_BYTES", 10):                              # one size cap for the hint and the waiver
            self.assertIsNone(photo_session.heading_hint(folder, 46.2, 10.9))
            self.assertEqual(photo_session.pinning_artifacts(folder, (46.2, 10.9)), [])

    def test_recon_first_pass_follows_every_recon_json(self):
        steps = {"photo": "original/p.jpg", "steps": {}}
        folder = self.scene_folder({"road": 0.9}, {"recon_2/recon.json": steps, "recon_2/detect/detect_sheet.jpg": b"x",
                                                   "recon_2/intake/rev/yandex_sheet.jpg": b"x", "recon_2/textgeo.json": {"signals": []}})
        self.assertEqual(photo_session.count_verification_artifacts(folder), 0)              # recon --out-dir recon_2: still the first pass
        self.assertFalse(photo_session.required_checks(folder)[0]["done"])
        (folder / "recon_2" / "rank.json").write_text("[]", encoding="utf-8")                   # a check saved beside recon's output counts
        self.assertEqual(photo_session.count_verification_artifacts(folder), 1)
        self.assertTrue(photo_session.required_checks(folder)[0]["done"])
        (folder / "work" / "detect").mkdir(parents=True)
        (folder / "work" / "detect" / "detect_overview.jpg").write_bytes(b"x")                 # standalone detect.py: never a check
        (folder / "notes" / "intake").mkdir(parents=True)
        (folder / "notes" / "recon.json").write_text("{}", encoding="utf-8")                    # not recon's (no steps): nothing excluded
        (folder / "notes" / "intake" / "x_sheet.jpg").write_bytes(b"x")
        self.assertEqual(photo_session.count_verification_artifacts(folder), 2)
        root = self.scene_folder({}, {"recon.json": steps, "intake/edges_sheet.jpg": b"x", "rank_1.json": []})
        self.assertEqual(photo_session.count_verification_artifacts(root), 1)                # recon in the session root: only its outputs go

    def test_scene_checks_recognised_by_content(self):
        sky, street, jpg = {"mountains": 0.9}, {"road": 0.9}, b"\xff\xd8\xff\xd9"

        def done(scene, files):
            return photo_session.required_checks(self.scene_folder(scene, files))[0]["done"]
        fit = {"clusters": [], "cams": [{"total": 0.8}], "partial": True}
        refsheet = {"refsheet.jpg": jpg, "refsheet.index.json": [{"candidate": "Trento", "country": "IT", "cells": [{"id": "p", "heading": 90}]}]}
        tiles = {"cands_sheet.jpg": jpg, "cands_sheet.json": {"zoom": 17, "center": [46.2, 10.9]}}
        gsv = [{"id": "abc", "heading": 90.0, "wgs": [46.2, 10.9]}]
        match_rows = [{"rank": 1, "id": "abc", "wgs": [46.2, 10.9], "inliers": 4, "score_global": 0.1}]
        sweep_rows = [{"rank": 1, "area_rank": 2, "key": "apple:1", "id": "1", "lat": 46.2, "lon": 10.9, "score": 2.1}]
        sat_rows = [{"cell": 7, "lat": 46.2, "lon": 10.9, "score": 0.4, "rank": 1}]
        for files in ({"ridge.json": {"ridge": [[0, 10]]}}, {"hits.json": {"hits": [], "clusters": [{"lat": 46.2, "lon": 10.9}]}}, refsheet,
                      {"refsheet_alps.jpg": jpg}, tiles, {"lake.geojson": fit}, {".geo-cache/fit.json": fit}, {"broken.json": b'{"cams": ['}):
            self.assertFalse(done(sky, files), files)
        self.assertTrue(done(sky, {"fine.json": fit}))                                       # fit output under any name, partial included
        for files in (refsheet, {"refsheet_alps.jpg": jpg}, tiles, {"around.index.json": gsv}, {"sat/ranked.json": sat_rows}):
            self.assertFalse(done(street, files), files)
        baidu = {"cands_sheet.jpg": jpg, "cands_sheet.index.json": [{"id": "09002200121902131010000012345", "heading": 45.0, "pitch": 10, "fov": 80}]}
        for files in ({"around.jpg": jpg, "around.index.json": gsv}, {"r.json": match_rows}, {"out/ranked.json": sweep_rows}, {"evidence.jpg": jpg}, baidu):
            self.assertTrue(done(street, files), files)
        count = photo_session.count_verification_artifacts
        self.assertEqual(count(self.scene_folder(street, {"out/ranked.json": sweep_rows})), 1)
        self.assertGreaterEqual(count(self.scene_folder(street, {"around.jpg": jpg, "around.index.json": gsv})), 1)
        self.assertEqual(count(self.scene_folder(sky, {"fine.json": fit})), 1)
        with patch.object(photo_session, "JSON_MAX_BYTES", 10):
            self.assertFalse(done(sky, {"fine.json": fit}))                                  # too big to parse: skipped
        self.assertIn("sweep.py rank → view", photo_session.CHECKS["street"]["command"])
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        (folder / "recon" / "prior").mkdir(parents=True)
        (folder / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": street}), encoding="utf-8")
        (folder / "evidence.jpg").write_bytes(jpg)
        res = json.loads((Path(self.finish(folder)["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertTrue(res["checks"][0]["done"])                                             # the street check itself, not a waiver
        self.assertIsNone(res["checks"][0]["waived_by"])

    def test_status_line_reads_clock_artifacts_and_checks(self):
        line, jpg = photo_session.status_line, b"\xff\xd8\xff\xd9"
        self.assertEqual(line(self.scene_folder({}, {})), "verification files 0")                       # no session.json, no scene
        self.assertEqual(line(self.scene_folder({"mountains": 0.9}, {"fine.json": {"cams": [{"total": 0.8}]}})),
                         "verification files 1 · skyline done")
        self.assertEqual(line(self.scene_folder({"mountains": 0.9, "road": 0.9}, {"evidence_1.jpg": jpg})),
                         "verification files 1 · skyline waived by evidence_1.jpg | street done")
        self.assertEqual(line(self.scene_folder({}, {"session.json": {"started_at": "yesterday"}})), "verification files 0")
        started = photo_session.now() - timedelta(minutes=12, seconds=20)
        near = [{"rank": 1, "id": "p1", "inliers": 14, "score_global": 0.2, "wgs": [46.2005, 10.9005]}]
        folder = self.scene_folder({"mountains": 0.9}, {"shop_rank.json": near, "session.json": {"started_at": started.isoformat()}})
        self.assertEqual(line(folder), '+12 min · verification files 1 · skyline missing: run terrain.py ridge → fit, or --skip-check skyline:"<reason>"')   # no answer yet: a rank file pins nothing
        (folder / "session.json").write_text(json.dumps({"started_at": started.isoformat(), "completed_at": (started + timedelta(minutes=14)).isoformat(),
                                                         "status": "completed", "result": {"latitude": 46.2, "longitude": 10.9}}), encoding="utf-8")
        self.assertEqual(line(folder), "+14 min · verification files 1 · skyline waived by shop_rank.json")   # the answer is 68 m from its view
        skipped = self.scene_folder({"mountains": 0.9}, {"session.json": {"status": "completed", "result": {
            "latitude": 46.2, "longitude": 10.9, "checks": [{"name": "skyline", "done": False, "skipped": "operator asked: it is Lago X"}]}}})
        self.assertEqual(line(skipped), "verification files 0 · skyline skipped: operator asked: it is Lago X")

    def test_malformed_scene_tags_never_crash_say_or_checks(self):
        for prior in ([], {"scene": [0.9]}, {"scene": "mountains"}, "x", {"scene": None}):
            folder = self.scene_folder({}, {"recon/prior/prior.json": prior})
            self.assertIsNone(photo_session.scene_tags(folder), prior)
            self.assertEqual(photo_session.status_line(folder), "verification files 0", prior)
        folder = self.scene_folder({}, {"recon/prior/prior.json": {"scene": {"mountains": "0.9", "water": None, "urban": "n/a"}}})
        self.assertEqual(photo_session.scene_tags(folder), {"mountains": 0.9, "water": 0.0, "urban": 0.0})
        self.assertEqual(photo_session.status_line(folder),
                         'verification files 0 · skyline missing: run terrain.py ridge → fit, or --skip-check skyline:"<reason>"')
        r = subprocess.run([sys.executable, str(SCRIPT), "checks", str(folder)], cwd=self.root, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout.splitlines()[2], r'^  skyline +MISSING .* → terrain\.py ridge → fit .*, or --skip-check skyline:"<reason>"$')

    def test_checks_prints_the_status_line_first(self):
        folder = Path(self.start()["folder"])
        (folder / "recon" / "prior").mkdir(parents=True)
        (folder / "recon" / "prior" / "prior.json").write_text(json.dumps({"scene": {"mountains": 0.9, "road": 0.9}}), encoding="utf-8")
        (folder / "pose.json").write_text(json.dumps({"camera_ll": [46.2, 10.9], "rms_px": 2.0}), encoding="utf-8")   # pose.py solve output
        r = subprocess.run([sys.executable, str(SCRIPT), "checks", str(folder)], cwd=self.root, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertRegex(lines[0], r"^\+\d+ min · verification files 1 · skyline waived by pose\.json \| street waived by pose\.json$")
        self.assertRegex(lines[2], r"^  skyline +WAIVED .*: by pose\.json$")                  # the body agrees with the header
        self.assertRegex(lines[3], r"^  street +WAIVED .*: by pose\.json$")
        checks = json.loads(r.stdout[r.stdout.index("\n{") + 1:])["checks"]
        self.assertEqual([c.get("waived_by") for c in checks], [["pose.json"], ["pose.json"]])

    def test_new_photos_have_separate_folders_and_missing_bytes_are_explicit(self):
        self.assertNotEqual(self.start()["folder"], self.start()["folder"])
        pending = self.command("start", "--root", self.root / "archives")
        self.assertIsNone(pending["original"])
        self.assertIn("not been saved", (Path(pending["folder"]) / "original" / "source.txt").read_text(encoding="utf-8"))
        self.command("start", "--root", self.root / "missing", "--image", self.root / "no.jpg", success=False)
        self.assertFalse((self.root / "missing").exists())

    def test_truth_scores_session_and_survives_refinish(self):
        started = self.start()
        folder = Path(started["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        self.command("truth", folder, "--latitude", "49.0", "--longitude", "20.0", success=False)  # not finished yet
        final = self.finish(folder)
        renamed = Path(final["folder"])
        scored = self.command("truth", renamed, "--latitude", "49.2", "--longitude", "20.1",
                              "--country", "Slovakia", "--region", "Prešov", "--source", "owner")
        truth = scored["truth"]
        self.assertAlmostEqual(truth["error_km"], 4.53, delta=0.3)
        self.assertTrue(truth["country_hit"])
        self.assertTrue(truth["region_hit"])
        self.assertGreater(truth["game_score_estimate"], 4980)
        report = (renamed / "report.md").read_text(encoding="utf-8")
        self.assertIn("## Ground truth", report)
        # recording the truth again replaces the block; finishing again keeps it once
        self.command("truth", renamed, "--latitude", "48.15", "--longitude", "17.11", "--country", "Slovakia")
        self.finish(renamed)
        report = (renamed / "report.md").read_text(encoding="utf-8")
        self.assertEqual(report.count("## Ground truth"), 1)
        self.assertIn("48.150000, 17.110000", report)
        self.assertEqual(report.count("<!-- geogussr-archive -->"), 1)
        self.assertLess(report.index("## Ground truth"), report.index("<!-- geogussr-archive -->"))
        self.assertLess(report.index("<!-- geogussr-archive -->"), report.index("Amended:"))

    def test_refinish_rescores_the_truth_and_keeps_the_old_metrics(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        poprad = Path(self.finish(folder)["folder"])
        first = self.command("truth", poprad, "--latitude", "49.1675", "--longitude", "20.0675", "--country", "Slovakia", "--source", "owner")["truth"]
        self.assertEqual((first["error_km"], first["game_score_estimate"], first["country_hit"]), (0.0, 5000, True))
        paris = Path(self.command("finish", poprad, "--country", "France", "--city", "Paris", "--latitude", "48.8566", "--longitude", "2.3522",
                                  "--confidence", "high", "--heading", "unknown", "--taken", "unknown",
                                  "--accept-unverified", "operator asked: test fixture, no checks")["folder"])
        meta = json.loads((paris / "session.json").read_text(encoding="utf-8"))
        km = photo_session.haversine_km(48.8566, 2.3522, 49.1675, 20.0675)
        t = meta["truth"]
        self.assertAlmostEqual(t["error_km"], km, delta=0.01)                                  # the metrics describe the current answer
        self.assertLess(t["game_score_estimate"], 2500)
        self.assertEqual((t["country_hit"], t["outcome_hit"], t["false_stop"]), (False, True, False))
        ground = ("outcome", "latitude", "longitude", "country", "region", "city", "source", "recorded_at")
        self.assertEqual({k: t.get(k) for k in ground}, {k: first.get(k) for k in ground})     # the ground truth itself is unchanged
        old = meta["result_history"][0]
        self.assertEqual(old["result"]["city_or_nearest_locality"], "Poprad")
        self.assertEqual({k: old["truth_metrics"][k] for k in ("error_km", "game_score_estimate", "country_hit")},
                         {"error_km": 0.0, "game_score_estimate": 5000, "country_hit": True})  # the replaced answer keeps its own score
        report = (paris / "report.md").read_text(encoding="utf-8")
        self.assertEqual(report.count("## Ground truth"), 1)
        self.assertIn(f"Error: {t['error_km']:.2f} km", report)
        self.assertIn("country hit: no", report)
        self.assertIn("stated confidence: high", report)
        board = self.command("scoreboard", "--root", self.root / "archives")
        row = board["sessions"][0]
        self.assertEqual((row["chosen"], row["confidence"], row["country_hit"], row["score"]), ("Paris", "high", False, t["game_score_estimate"]))
        self.assertAlmostEqual(row["error_km"], km, delta=0.01)
        self.assertEqual((board["by_confidence"]["high"]["n"], board["by_confidence"]["high"]["within_200km"]), (1, 0.0))
        self.assertEqual((board["by_confidence"]["medium"]["n"], board["country_hit_rate"]), (0, 0.0))

    def stale_truth_session(self, **truth) -> Path:
        """The review's fixture: Poprad finished and scored (0 km), then re-finished as Paris by a version that kept the truth's
        metrics as they were and wrote no truth_metrics in result_history."""
        folder = self.root / "archives" / "session"
        folder.mkdir(parents=True)
        state = {"status": "completed", "started_at": "2026-10-13T12:00:00+02:00",
                 "result": {"country": "France", "city_or_nearest_locality": "Paris", "latitude": 48.8566, "longitude": 2.3522, "confidence": "high"},
                 "truth": {"latitude": 49.05, "longitude": 20.30, "country": "Slovakia", "recorded_at": "2026-10-13T12:01:00+02:00",
                           "error_km": 0, "game_score_estimate": 5000, "country_hit": True, **truth},
                 "result_history": [{"replaced_at": "2026-10-13T12:02:00+02:00",
                                     "result": {"country": "Slovakia", "city_or_nearest_locality": "Poprad", "latitude": 49.05,
                                                "longitude": 20.30, "confidence": "medium"}}]}
        (folder / "session.json").write_text(json.dumps(state), encoding="utf-8")
        return folder

    def test_truth_kept_through_an_unrescored_refinish_scores_the_current_answer(self):
        self.stale_truth_session()
        km = photo_session.haversine_km(48.8566, 2.3522, 49.05, 20.30)
        board = self.command("scoreboard", "--root", self.root / "archives")
        row = board["sessions"][0]
        self.assertEqual((row["chosen"], row["confidence"], row["country_hit"]), ("Paris", "high", False))
        self.assertAlmostEqual(row["error_km"], km, delta=0.01)
        self.assertLess(row["score"], 2500)
        self.assertEqual((board["by_confidence"]["high"]["n"], board["by_confidence"]["high"]["within_200km"]), (1, 0.0))
        self.assertAlmostEqual(self.command("list", "--root", self.root / "archives")["sessions"][0]["error_km"], km, delta=0.01)

    def test_truth_metrics_recorded_for_the_current_answer_are_read_as_stored(self):
        # truth recorded after the replacement, or a replacement that kept its own metrics: the stored ones are the current answer's
        folder = self.stale_truth_session(recorded_at="2026-10-13T12:03:00+02:00", error_km=7.0)
        self.assertEqual(self.command("scoreboard", "--root", self.root / "archives")["sessions"][0]["error_km"], 7.0)
        state = json.loads((folder / "session.json").read_text(encoding="utf-8"))
        state["truth"]["recorded_at"] = "2026-10-13T12:01:00+02:00"
        state["result_history"][0]["truth_metrics"] = {"error_km": 0}
        (folder / "session.json").write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual(self.command("list", "--root", self.root / "archives")["sessions"][0]["error_km"], 7.0)

    def test_refinish_with_an_unreadable_truth_names_the_next_action(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        poprad = Path(self.finish(folder)["folder"])
        self.command("truth", poprad, "--latitude", "49.1675", "--longitude", "20.0675", "--country", "Slovakia")
        paris = ("--country", "France", "--city", "Paris", "--latitude", "48.8566", "--longitude", "2.3522", "--confidence", "high",
                 "--heading", "unknown", "--taken", "unknown", "--accept-unverified", "operator asked: test fixture, no checks")
        state = json.loads((poprad / "session.json").read_text(encoding="utf-8"))
        for broken in ({k: v for k, v in state["truth"].items() if k != "latitude"}, {**state["truth"], "latitude": "north"}):
            with self.subTest(truth=broken.get("latitude")):
                (poprad / "session.json").write_text(json.dumps({**state, "truth": broken}), encoding="utf-8")
                err = self.command("finish", poprad, *paris, success=False)
                self.assertNotIn("Traceback", err)
                self.assertIn("truth record cannot be scored", err)
                self.assertIn(f'photo_session.py truth "{poprad}" --latitude', err)                # the exit, with its command
                self.assertEqual(json.loads((poprad / "session.json").read_text(encoding="utf-8"))["result"]["city_or_nearest_locality"], "Poprad")
        self.command("truth", poprad, "--latitude", "49.1675", "--longitude", "20.0675", "--country", "Slovakia")
        self.assertFalse(json.loads((Path(self.command("finish", poprad, *paris)["folder"]) / "session.json").read_text(encoding="utf-8"))
                         ["truth"]["country_hit"])

    def test_scoreboard_and_list(self):
        archives = self.root / "archives"
        for lat, conf in (("49.2", "medium"), ("10.0", "high")):
            folder = Path(self.start()["folder"])
            (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
            final = self.finish(folder, "--confidence", conf)
            self.command("truth", final["folder"], "--latitude", lat, "--longitude", "20.1", "--country", "Slovakia")
        pending = self.start()
        listed = self.command("list", "--root", archives)
        self.assertEqual(listed["count"], 3)
        self.assertEqual(self.command("list", "--root", archives, "--status", "pending")["sessions"][0]["folder"], pending["folder"])
        board = self.command("scoreboard", "--root", archives, "--write")
        self.assertEqual(board["scored_sessions"], 2)
        self.assertEqual(board["within_km"]["25"], 0.5)
        self.assertEqual(board["by_confidence"]["high"]["n"], 1)
        self.assertEqual(board["by_confidence"]["high"]["within_200km"], 0.0)
        self.assertTrue((archives / "scoreboard.md").read_text(encoding="utf-8").startswith("# Geo-intelligence scoreboard"))

    def test_report_skeleton_must_be_filled_before_finish(self):
        folder = Path(self.start()["folder"])
        skeleton = (folder / "report.md").read_text(encoding="utf-8")
        self.assertIn("## Gut call (before tools)", skeleton)
        self.assertIn("Fill these report.md sections", self.finish(folder, success=False))
        filled = skeleton.replace("## Gut call (before tools)\n<!-- fill:", "## Gut call (before tools)\nSlovakia 60% (Tatras)\n<!--")
        (folder / "report.md").write_text(filled, encoding="utf-8")
        self.assertIn("Answer", self.finish(folder, success=False))
        filled = filled.replace("## Answer\n<!-- fill:", "## Answer\nPoprad, medium\n<!--")
        (folder / "report.md").write_text(filled, encoding="utf-8")
        self.assertIn("When", self.finish(folder, success=False))                        # when is an answer too
        (folder / "report.md").write_text(filled.replace("## When\n<!-- fill:", "## When\nSummer 2019, afternoon (shadows)\n<!--"), encoding="utf-8")
        self.assertTrue(self.finish(folder)["folder"].endswith("__slovakia__presov__poprad"))

    def test_timezone_name_is_resolved_never_none(self):
        env = {k: v for k, v in os.environ.items() if k != "GEOINT_TZ"}
        started = self.command("start", "--root", self.root / "archives", "--image", self.source, env=env)
        self.assertTrue(started["timezone"])
        folder = Path(started["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        final = self.command("finish", folder, "--country", "Slovakia", "--city", "Poprad", "--latitude", "49.1675", "--longitude", "20.0675", "--heading", "unknown", "--taken", "unknown", "--accept-unverified", "operator asked: stop (test)",
                             "--confidence", "low", env=env)
        report = Path(final["report"]).read_text(encoding="utf-8")
        self.assertNotIn("(None)", report)
        self.assertIn(f"({started['timezone']})", report)
        named = self.command("start", "--root", self.root / "archives", "--image", self.source, env={**env, "GEOINT_TZ": "Europe/Rome"})
        self.assertEqual(named["timezone"], "Europe/Rome")
        self.assertTrue(named["started_at"].endswith(("+01:00", "+02:00")))

    def test_finish_records_radius_and_heading(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        self.finish(folder, "--radius-m", "0", success=False)
        self.finish(folder, "--heading", "nan", success=False)
        self.assertTrue(folder.exists())
        final = self.finish(folder, "--radius-m", "150", "--heading", "407")
        result = json.loads((Path(final["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual((result["radius_m"], result["heading"]), (150.0, 47.0))
        self.assertIn("radius 150 m; heading 47°; confidence medium", Path(final["report"]).read_text(encoding="utf-8"))
        plain = self.finish(Path(final["folder"]))     # without the flags both stay recorded as unknown
        result = json.loads((Path(plain["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual((result["radius_m"], result["heading"]), (None, None))

    def test_truth_scores_the_gut_call(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("# Report\n\n## Gut call (before tools)\n1. Portugal 55% — calçada, whitewash\n"
                                          "2. **Spain** 25% — similar roofs\nRegion hunch: Alentejo\n\n## Answer\nPoprad\n", encoding="utf-8")
        self.assertEqual(photo_session.gut_call((folder / "report.md").read_text(encoding="utf-8")), [("Portugal", 55.0), ("Spain", 25.0)])
        hunch = ("## Gut call (before tools)\n1. South Korea 99% - Hangul\nRegion hunch: Seoul Goto Mall 45%, Incheon 40%\n"
                 "Plan:\nA. sign 30% visible → a street → step 3\n\n## Answer\n")
        self.assertEqual(photo_session.gut_call(hunch), [("South Korea", 99.0)])     # labelled lines never parse as countries
        renamed = self.finish(folder)["folder"]
        truth = self.command("truth", renamed, "--latitude", "38.9", "--longitude", "-6.3", "--country", "Spain")["truth"]
        self.assertEqual((truth["country_hit"], truth["gut_country_hit"], truth["gut_p_truth"]), (False, True, 25.0))
        self.assertIn("gut call: yes (25% on the true country)", (Path(renamed) / "report.md").read_text(encoding="utf-8"))
        truth = self.command("truth", renamed, "--latitude", "48.0", "--longitude", "2.0", "--country", "France")["truth"]
        self.assertEqual((truth["gut_country_hit"], truth["gut_p_truth"]), (False, 0.0))
        truth = self.command("truth", renamed, "--latitude", "48.0", "--longitude", "2.0")["truth"]   # no truth country: unknown
        self.assertEqual((truth["gut_country_hit"], truth["gut_p_truth"]), (None, None))
        board = self.command("scoreboard", "--root", self.root / "archives", "--write")
        self.assertIsNone(board["gut_country_hit_rate"])
        self.command("truth", renamed, "--latitude", "38.9", "--longitude", "-6.3", "--country", "Spain")
        board = self.command("scoreboard", "--root", self.root / "archives", "--write")
        self.assertEqual(board["gut_country_hit_rate"], 1.0)
        self.assertEqual(board["sessions"][0]["gut_p_truth"], 25.0)
        self.assertIn("| 25 |", (self.root / "archives" / "scoreboard.md").read_text(encoding="utf-8"))

    def test_rename_retries_with_backoff_then_names_the_folder(self):
        attempts, sleeps = [], []
        real_rename = Path.rename

        def flaky(self_, target):
            attempts.append(target)
            if len(attempts) < 3:
                raise PermissionError(5, "Access is denied")
            return real_rename(self_, target)

        src = self.root / "pending"
        src.mkdir()
        with patch.object(Path, "rename", flaky), patch.object(photo_session.time, "sleep", sleeps.append):
            photo_session._rename(src, self.root / "done")
        self.assertTrue((self.root / "done").is_dir())
        self.assertEqual(sleeps, [1.0, 1.25])
        attempts.clear()
        with patch.object(Path, "rename", lambda s_, t: (_ for _ in ()).throw(PermissionError(32, "in use"))), \
                patch.object(photo_session.time, "sleep", sleeps.append), self.assertRaises(OSError) as cm:
            photo_session._rename(self.root / "done", self.root / "again")
        self.assertIn(str(self.root / "done"), str(cm.exception))
        self.assertIn("after 5 attempts", str(cm.exception))
        self.assertEqual(len(sleeps), 2 + 4)
        self.assertTrue(all(1.0 <= t <= 2.0 for t in sleeps))

    @unittest.skipUnless(os.name == "nt", "Windows refuses to rename a folder with an open file inside")
    def test_finish_fails_clearly_while_another_process_holds_a_file(self):
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        with (folder / "report.md").open("rb"):
            err = self.finish(folder, success=False)
        self.assertIn("Could not rename", err)
        self.assertIn(folder.name, err)
        self.assertTrue(folder.exists())
        self.assertEqual(json.loads((folder / "session.json").read_text(encoding="utf-8"))["status"], "pending")
        self.assertTrue(self.finish(folder)["folder"].endswith("__slovakia__presov__poprad"))

    DECLARED = {"declared": True, "term": "trainedAlgorithmicMedia", "composite": False, "source": "XMP-iptcExt:DigitalSourceType"}

    def generated_session(self, declared=None, p_ai=None):
        """A started session with a filled report and, optionally, meta's provenance verdict and the detector's score."""
        folder = Path(self.start()["folder"])
        (folder / "report.md").write_text("Best estimate.\n", encoding="utf-8")
        if declared is not None:
            (folder / "recon" / "meta").mkdir(parents=True, exist_ok=True)
            (folder / "recon" / "meta" / "meta.json").write_text(json.dumps({"digest": {"provenance": {"generated": declared}}, "raw": {}}), encoding="utf-8")
        if p_ai is not None:
            (folder / "recon" / "aidet").mkdir(parents=True, exist_ok=True)
            (folder / "recon" / "aidet" / "aidet.json").write_text(json.dumps({"tool": "aidet.py", "p_ai": p_ai, "threshold": 0.65, "model": "detector@0123abcd"}),
                                                                 encoding="utf-8")
        return folder

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_finish_generated_closes_without_a_place(self):
        folder = self.generated_session(self.DECLARED, p_ai=0.91)
        basis = "IPTC DigitalSourceType trainedAlgorithmicMedia (recon/meta/meta.md)"
        renamed = Path(self.command("finish", folder, "--generated", basis)["folder"])
        self.assertEqual(renamed.name, folder.name + "__generated-image")
        res = json.loads((renamed / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual((res["outcome"], res["latitude"], res["longitude"]), ("generated", None, None))
        self.assertEqual(res["generated"], {"basis": basis, "score": 0.91, "model": "detector@0123abcd", "skipped": None, "override": None})
        self.assertIn("Result: generated image, no real place", (renamed / "report.md").read_text(encoding="utf-8"))
        self.assertTrue((renamed / "viewer.html").is_file())
        listed = {s["folder"]: s["result"] for s in self.command("list", "--root", self.root / "archives")["sessions"]}
        self.assertEqual(listed[str(renamed)], "generated image (no place)")
        folder2 = self.generated_session(self.DECLARED)
        for extra in (["--country", "Slovakia"], ["--heading", "unknown"], ["--confidence", "high"], ["--accept-unverified", "user stopped"],
                      ["--skip-check", "skyline:user stopped"]):
            r = self.run_cli("finish", folder2, "--generated", "trainedAlgorithmicMedia", *extra)
            self.assertEqual(r.returncode, 2, extra)                                          # a usage error, like a missing flag
            self.assertIn(f"drop {extra[0]}", r.stderr)
        r = self.run_cli("finish", folder2, "--country", "Namibia", "--city", "x", "--confidence", "low", "--taken", "unknown")
        self.assertEqual(r.returncode, 2)
        self.assertIn("the following arguments are required: --heading", r.stderr)             # unchanged without --generated
        self.assertIn("--generated BASIS", r.stderr)                                           # and the other exit is named
        self.assertTrue(folder2.is_dir())

    def test_generated_basis_is_evidence_never_a_score(self):
        folder = self.generated_session({"declared": False, "term": None, "composite": True, "source": "XMP"}, p_ai=0.99)
        (folder / "recon" / "intake").mkdir(parents=True)
        (folder / "recon" / "intake" / "gallery.html").write_text("x", encoding="utf-8")         # recon's first pass, not a page the agent saved
        (folder / "verify").mkdir()
        (folder / "verify" / "ai gallery page.html").write_text("prompt: …", encoding="utf-8")
        (folder / "aidet").mkdir()                                                           # aidet.py run by hand outside recon/: still a score
        (folder / "aidet" / "aidet.json").write_text(json.dumps({"tool": "aidet.py", "p_ai": 0.99, "threshold": 0.65}), encoding="utf-8")
        ok = photo_session.generated_basis
        for basis in ("detector 0.99, generated-like", "compositeWithTrainedAlgorithmicMedia", "trainedAlgorithmicMedia", "recon/intake/gallery.html",
                      "recon/aidet/aidet.json", "aidet/aidet.json p_ai 0.99", "aidet.json", "missing_page.html", "verify/ai gallery page.htmlx",
                      "report.md", "", "aidet p_ai 0.99, flagged; users on the forum agree", "looks like an interrupted render",
                      "detector 0.99, no operator input", "model flagged it, the user did not answer", "the detector says: operator asked: generated"):
            self.assertFalse(ok(basis, folder), basis)
        for basis, kind in (("saved page: verify/ai gallery page.html.", "file"), ("ai gallery page.html shows the prompt and the model", "file"),
                            ("operator asked: it is generated", "operator"), ("User said: it is generated", "operator")):
            self.assertEqual(ok(basis, folder), kind, basis)
        declared = self.generated_session(self.DECLARED)
        self.assertEqual(ok("IPTC trainedalgorithmicmedia, the only source type", declared), "declared")   # the declared term, any case
        self.assertFalse(ok("compositeWithTrainedAlgorithmicMedia", declared))                # another term that contains it
        r = self.run_cli("finish", folder, "--generated", "detector 0.99, generated-like")
        self.assertEqual(r.returncode, 1)
        self.assertIn("never a score", r.stderr)
        self.assertIn('"operator asked: …"', r.stderr)
        self.assertTrue(folder.is_dir())

    def test_a_detector_score_alone_never_refuses(self):
        res = json.loads((Path(self.finish(self.generated_session(p_ai=0.99))["folder"]) / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual((res["outcome"], res["latitude"]), ("place", 49.1675))

    def test_operator_real_outranks_the_declared_term(self):
        folder = self.generated_session(self.DECLARED)
        self.command("not-generated", folder, "operator asked: it is real, continue")
        err = self.command("finish", folder, "--generated", "trainedAlgorithmicMedia", success=False)
        self.assertIn("operator asked: it is real, continue", err)                             # what outranks the term, quoted
        self.assertIn('--generated "operator asked: …"', err)                                  # every exit, with its command
        self.assertIn("saved file", err)
        self.assertIn("--country", err)
        self.assertTrue(folder.is_dir())
        renamed = Path(self.command("finish", folder, "--generated", "operator asked: it is generated after all")["folder"])
        res = json.loads((renamed / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual(res["generated"]["override"]["reason"], "operator asked: it is real, continue")

    def test_a_pin_outranks_the_declared_term_in_finish_generated(self):
        folder = self.generated_session(self.DECLARED)
        (folder / "pose.json").write_text(json.dumps({"camera_ll": [49.1675, 20.0675], "heading": 90.0}), encoding="utf-8")
        err = self.command("finish", folder, "--generated", "trainedAlgorithmicMedia", success=False)
        self.assertIn("pose.json", err)                                                        # what outranks the term, named
        self.assertIn("--latitude", err)                                                       # every exit, with its command
        self.assertIn('--generated "operator asked: …"', err)
        self.assertIn("saved file", err)
        self.assertTrue(folder.is_dir())
        (folder / "verify").mkdir()
        (folder / "verify" / "ai gallery page.html").write_text("prompt: …", encoding="utf-8")
        renamed = self.command("finish", folder, "--generated", "saved page: verify/ai gallery page.html")["folder"]
        self.assertEqual(json.loads((Path(renamed) / "session.json").read_text(encoding="utf-8"))["result"]["outcome"], "generated")
        self.command("finish", renamed, "--generated", "operator asked: it is generated")      # the operator's words close too
        ranked = self.generated_session(self.DECLARED)                                         # a ranked view pins the finished place
        (ranked / "x_rank.json").write_text(json.dumps([{"rank": 1, "id": "p1", "heading": 90.0, "inliers": 20, "score_global": 0.3,
                                                         "wgs": [49.1675, 20.0675]}]), encoding="utf-8")
        place = self.finish(ranked)["folder"]
        err = self.command("finish", place, "--generated", "trainedAlgorithmicMedia", success=False)
        self.assertIn("x_rank.json", err)
        self.assertEqual(json.loads((Path(place) / "session.json").read_text(encoding="utf-8"))["result"]["outcome"], "place")

    def test_refinish_switches_outcome_and_keeps_history(self):
        place = self.finish(self.generated_session())
        generated = self.command("finish", place["folder"], "--generated", "operator asked: it is generated")
        meta = json.loads((Path(generated["folder"]) / "session.json").read_text(encoding="utf-8"))
        self.assertEqual((meta["result"]["outcome"], meta["completed_at"]), ("generated", place["completed_at"]))
        self.assertEqual(meta["result_history"][0]["result"]["outcome"], "place")
        back = self.finish(Path(generated["folder"]))
        self.assertEqual(back["folder"], place["folder"])                                      # the folder name follows the answer
        meta = json.loads((Path(back["folder"]) / "session.json").read_text(encoding="utf-8"))
        self.assertEqual((meta["result"]["outcome"], meta["completed_at"]), ("place", place["completed_at"]))
        self.assertEqual([h["result"]["outcome"] for h in meta["result_history"]], ["place", "generated"])
        report = Path(back["report"]).read_text(encoding="utf-8")
        self.assertEqual(report.count("<!-- geogussr-archive -->"), 1)
        self.assertNotIn("generated image, no real place", report)                            # the footer is the current answer's

    def test_finish_generated_records_a_skipped_detector(self):
        folder = self.generated_session()
        (folder / "recon" / "aidet").mkdir(parents=True)
        (folder / "recon" / "aidet" / "aidet.json").write_text(json.dumps({"tool": "aidet.py", "skipped": "timed out after 20s"}), encoding="utf-8")
        renamed = Path(self.command("finish", folder, "--generated", "operator asked: generated")["folder"])
        res = json.loads((renamed / "session.json").read_text(encoding="utf-8"))["result"]
        self.assertEqual((res["generated"]["score"], res["generated"]["skipped"]), (None, "timed out after 20s"))
        self.assertIn("Detector: skipped (timed out after 20s)", (renamed / "report.md").read_text(encoding="utf-8"))

    def test_declared_generation_refuses_a_place_until_pinned_or_overridden(self):
        folder = self.generated_session(self.DECLARED, p_ai=0.2)
        err = self.finish(folder, success=False)
        self.assertIn("trainedAlgorithmicMedia", err)
        self.assertIn("not-generated", err)                                                   # every exit, with its command
        self.assertIn('"operator asked: it is real"', err)
        self.assertIn('--generated "trainedAlgorithmicMedia"', err)
        self.assertIn("pose.py", err)
        self.assertTrue(folder.is_dir())
        for words in ("looks real to me", "users on the forum say it is real", "no operator input, looks real"):
            err = self.command("not-generated", folder, words, success=False)
            self.assertIn('"operator asked: …"', err, words)
        self.assertNotIn("generated_override", json.loads((folder / "session.json").read_text(encoding="utf-8")))
        out = self.command("not-generated", folder, "operator asked: it is real, continue")
        self.assertEqual(out["generated_override"]["reason"], "operator asked: it is real, continue")
        shutil.rmtree(folder / "recon")                                                      # a recon rerun rewrites recon/, never the override
        (folder / "recon" / "meta").mkdir(parents=True)
        (folder / "recon" / "meta" / "meta.json").write_text(json.dumps({"digest": {"provenance": {"generated": self.DECLARED}}}), encoding="utf-8")
        meta = json.loads((Path(self.finish(folder)["folder"]) / "session.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["result"]["outcome"], "place")
        self.assertEqual(meta["generated_override"]["reason"], "operator asked: it is real, continue")
        pinned = self.generated_session(self.DECLARED)
        (pinned / "evidence_1.jpg").write_bytes(b"\xff\xd8\xff\xd9")                         # a real place found outranks a declaration
        r = self.run_cli("finish", pinned, "--country", "Slovakia", "--city", "Poprad", "--latitude", "49.1675", "--longitude", "20.0675",
                         "--confidence", "medium", "--heading", "unknown", "--taken", "unknown")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("the place is pinned by evidence_1.jpg", r.stderr)

    def test_generated_outcomes_are_scored_against_the_truth(self):
        archives = self.root / "archives"
        called = self.command("finish", self.generated_session(), "--generated", "operator asked: the image is generated")["folder"]
        rec = self.command("truth", called, "--latitude", "49.2", "--longitude", "20.1", "--country", "Slovakia")["truth"]
        self.assertEqual((rec["outcome"], rec["error_km"], rec["outcome_hit"], rec["false_stop"]), ("place", None, False, True))
        self.assertIn("false stop", (Path(called) / "report.md").read_text(encoding="utf-8"))
        board = self.command("scoreboard", "--root", archives, "--write")                    # no distance to measure: no TypeError
        self.assertEqual(board["generated"], {"called": 1, "confirmed": 0, "false_stops": 1, "missed": 0})
        self.assertEqual((board["scored_sessions"], board["median_error_km"], board["mean_game_score"]), (1, None, None))
        placed = self.finish(self.generated_session())["folder"]
        rec = self.command("truth", placed, "--generated", "--source", "owner")["truth"]
        self.assertEqual((rec["outcome"], rec["error_km"], rec["outcome_hit"], rec["false_stop"]), ("generated", None, False, False))
        self.assertIn("missed generation", (Path(placed) / "report.md").read_text(encoding="utf-8"))
        confirmed = self.command("finish", self.generated_session(), "--generated", "operator asked: generated")["folder"]
        self.assertTrue(self.command("truth", confirmed, "--generated")["truth"]["outcome_hit"])
        kept = self.finish(self.generated_session())["folder"]
        self.command("truth", kept, "--latitude", "49.2", "--longitude", "20.1")
        board = self.command("scoreboard", "--root", archives, "--write")
        self.assertEqual(board["generated"], {"called": 2, "confirmed": 1, "false_stops": 1, "missed": 1})
        self.assertEqual(board["scored_sessions"], 4)
        self.assertAlmostEqual(board["median_error_km"], 4.53, delta=0.3)                    # the one place answer against a place truth
        self.assertIn("generated image (no place)", (archives / "scoreboard.md").read_text(encoding="utf-8"))
        for extra in (["--generated", "--latitude", "1", "--longitude", "2"], ["--latitude", "1"], []):
            self.assertEqual(self.run_cli("truth", confirmed, *extra).returncode, 2, extra)
        old = ({"latitude": 1.0, "longitude": 2.0}, {"latitude": 1.0, "longitude": 2.0, "error_km": 3.0})   # sessions from before outcomes
        self.assertEqual(photo_session.generated_summary([old]), {"called": 0, "confirmed": 0, "false_stops": 0, "missed": 0})

    def test_refinish_rescores_generated_outcomes(self):
        archives = self.root / "archives"
        meta = lambda f: json.loads((Path(f) / "session.json").read_text(encoding="utf-8"))   # noqa: E731
        placed = self.finish(self.generated_session())["folder"]
        self.command("truth", placed, "--generated", "--source", "owner")                     # a missed generation, until the re-finish
        called = self.command("finish", placed, "--generated", "operator asked: it is generated")["folder"]
        m = meta(called)
        self.assertEqual((m["truth"]["outcome"], m["truth"]["outcome_hit"], m["truth"]["false_stop"]), ("generated", True, False))
        self.assertEqual((m["result_history"][0]["truth_metrics"]["outcome_hit"], m["result_history"][0]["truth_metrics"]["false_stop"]), (False, False))
        report = (Path(called) / "report.md").read_text(encoding="utf-8")
        self.assertIn("generated image confirmed", report)
        self.assertNotIn("missed generation", report)
        self.assertEqual(self.command("scoreboard", "--root", archives)["generated"], {"called": 1, "confirmed": 1, "false_stops": 0, "missed": 0})
        stopped = self.command("finish", self.generated_session(), "--generated", "operator asked: generated")["folder"]
        self.command("truth", stopped, "--latitude", "49.2", "--longitude", "20.1", "--country", "Slovakia")   # a false stop, until the re-finish
        back = self.finish(stopped)["folder"]
        m = meta(back)
        self.assertEqual((m["truth"]["outcome_hit"], m["truth"]["false_stop"], m["truth"]["country_hit"]), (True, False, True))
        self.assertAlmostEqual(m["truth"]["error_km"], 4.53, delta=0.3)
        self.assertEqual((m["result_history"][0]["truth_metrics"]["false_stop"], m["result_history"][0]["truth_metrics"]["error_km"]), (True, None))
        self.assertNotIn("false stop", (Path(back) / "report.md").read_text(encoding="utf-8"))
        board = self.command("scoreboard", "--root", archives)
        self.assertEqual(board["generated"], {"called": 1, "confirmed": 1, "false_stops": 0, "missed": 0})
        self.assertAlmostEqual(board["median_error_km"], 4.53, delta=0.3)

    @unittest.skipUnless(shutil.which("uv"), "bench.py runs through uv: its dependencies are not in this suite's environment")
    def test_bench_sessions_skip_unmeasured_errors(self):
        called = self.command("finish", self.generated_session(), "--generated", "operator asked: generated")["folder"]
        self.command("truth", called, "--latitude", "49.2", "--longitude", "20.1")
        self.command("truth", self.finish(self.generated_session())["folder"], "--latitude", "49.2", "--longitude", "20.1")
        r = subprocess.run(["uv", "run", "-q", str(SCRIPT.parent / "bench.py"), "sessions", "--root", str(self.root / "archives")],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["n"], 1)
        self.assertEqual(out["generated"], {"called": 1, "confirmed": 0, "false_stops": 1, "missed": 0})

    def test_unicode_place_names_fit_filesystem_limits(self):
        pending = self.start()
        folder = Path(pending["folder"])
        (folder / "report.md").write_text("Estimated location.\n", encoding="utf-8")
        final = self.finish(folder, "--country", "中国" * 40, "--region", "广东" * 40, "--city", "清远" * 40)
        self.assertLessEqual(len(Path(final["folder"]).name.encode("utf-8")), 255)
        self.assertTrue(Path(final["report"]).is_file())


if __name__ == "__main__":
    unittest.main()
