#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["tzdata"]
# ///
"""Archive workflow checks; all sample sessions live in temporary directories."""

import hashlib
import json
import os
from pathlib import Path
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
        for marker in ("<!-- fill: ranked shortlist with percentages and the cues behind each; region hunch; what would change your mind -->",
                       "<!-- fill: country / region / city, coordinates (WGS84; GCJ-02 too in mainland China), confidence per level, radius and what it rests on -->"):
            report = report.replace(marker, "1. Namibia 80% — yellow edge lines, red sand" if "shortlist" in marker else "Namibia, country level only")
        report = report.replace('<!-- fill: year or year range, season, date, time of day: each with the clue and the file it rests on; "not determinable" with the reason when it is -->',
                                "not determinable: no metadata, no dated imagery checked")
        (folder / "report.md").write_text(report, encoding="utf-8")
        out = self.command("finish", folder, "--country", "Namibia", "--city", "unknown", "--confidence", "medium", "--radius-m", "500")
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
        err = self.command("finish", folder2, "--country", "Atlantis", "--city", "x", "--confidence", "low", success=False)
        self.assertIn("Unknown country", err)
        err = self.command("finish", folder2, "--country", "Namibia", "--city", "x", "--confidence", "low", "--latitude", "-22", success=False)
        self.assertIn("both", err)

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
        final = self.command("finish", folder, "--country", "Slovakia", "--city", "Poprad", "--latitude", "49.1675", "--longitude", "20.0675",
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

    def test_unicode_place_names_fit_filesystem_limits(self):
        pending = self.start()
        folder = Path(pending["folder"])
        (folder / "report.md").write_text("Estimated location.\n", encoding="utf-8")
        final = self.finish(folder, "--country", "中国" * 40, "--region", "广东" * 40, "--city", "清远" * 40)
        self.assertLessEqual(len(Path(final["folder"]).name.encode("utf-8")), 255)
        self.assertTrue(Path(final["report"]).is_file())


if __name__ == "__main__":
    unittest.main()
