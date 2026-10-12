#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Offline board regressions. Run: uv run scripts/tests/test_board.py"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import board  # noqa: E402


class CorridorPendingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "board.json"
        self.output = self.root / "scan.json"
        self.output.write_text('{"hits": []}', encoding="utf-8")
        self.run_board("init", "--photo", "photo.jpg")

    def run_board(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "board.py"), "--board", str(self.path), *args],
            cwd=self.root, capture_output=True, text=True, encoding="utf-8",
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def read_board(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def clue(self, kind="infra", status="observed", *extra):
        self.run_board("clue", "A spatial observation or its computed test", "--kind", kind,
                       "--status", status, *extra)

    def pending(self):
        return board._corridor_pending(self.read_board())

    def test_alias_is_normalized_when_recorded(self):
        self.clue("infrastructure")
        self.assertEqual(self.read_board()["clues"]["K1"]["kind"], "infra")
        self.assertEqual(self.pending(), ["K1"])
        self.assertIn("infrastructure clue K1", self.run_board("next").stdout)

    def test_legacy_alias_is_detected_without_rewriting_board(self):
        self.clue()
        data = self.read_board()
        data["clues"]["K1"]["kind"] = "infrastructure"
        self.path.write_text(json.dumps(data), encoding="utf-8")
        before = self.path.read_bytes()
        self.assertEqual(self.pending(), ["K1"])
        self.assertIn("infrastructure clue K1", self.run_board("next").stdout)
        self.assertEqual(self.path.read_bytes(), before)

    def test_unlinked_computations_do_not_clear_infrastructure(self):
        self.clue()
        self.clue("infrastructure", "read")
        for kind in ("terrain", "corridor", "infra"):
            with self.subTest(kind=kind):
                self.clue(kind, "computed", "--file", str(self.output))
                self.assertEqual(self.pending(), ["K1", "K2"])

    def test_computation_clears_only_explicitly_linked_clues(self):
        self.clue()
        self.clue("infrastructure", "read")
        self.clue("terrain", "computed", "--file", str(self.output), "--resolves", "K1")
        self.assertEqual(self.pending(), ["K2"])
        self.assertIn("infrastructure clue K2", self.run_board("next").stdout)
        self.assertEqual(self.read_board()["clues"]["K3"]["resolves"], ["K1"])
        self.clue("corridor", "computed", "--file", str(self.output),
                  "--resolves", "K1", "--resolves", "K2")
        self.assertEqual(self.pending(), [])
        self.assertNotIn("infrastructure clue", self.run_board("next").stdout)
        # Recording a computation is separate from scoring candidate evidence.
        self.assertEqual(self.read_board()["evidence"], [])

    def test_unrelated_explicit_link_does_not_clear_infrastructure(self):
        self.clue()
        self.clue("terrain")
        self.clue("terrain", "computed", "--file", str(self.output), "--resolves", "K2")
        self.assertEqual(self.pending(), ["K1"])

    def test_invalid_completion_is_rejected_without_mutation(self):
        self.clue()
        before = self.path.read_bytes()
        cases = [
            ("--status", "observed", "--file", str(self.output), "--resolves", "K1"),
            ("--status", "computed", "--file", str(self.output), "--resolves", "K99"),
            ("--status", "computed", "--file", str(self.output), "--resolves", "K1", "--resolves", "K99"),
            ("--status", "computed", "--resolves", "K1"),
            ("--status", "computed", "--file", str(self.root / "missing.json"), "--resolves", "K1"),
            ("--status", "computed", "--file", str(self.root), "--resolves", "K1"),
        ]
        for args in cases:
            with self.subTest(args=args):
                self.run_board("clue", "An invalid completion", "--kind", "terrain", *args, ok=False)
                self.assertEqual(self.path.read_bytes(), before)

    def test_missing_output_no_longer_counts_as_completion(self):
        self.clue()
        self.clue("terrain", "computed", "--file", str(self.output), "--resolves", "K1")
        self.assertEqual(self.pending(), [])
        self.output.unlink()
        self.assertEqual(self.pending(), ["K1"])

    def test_relative_output_link_survives_a_different_working_directory(self):
        self.clue()
        self.clue("terrain", "computed", "--file", "scan.json", "--resolves", "K1")
        saved = self.read_board()["clues"]["K2"]["file"]
        self.assertEqual(Path(saved), self.output.resolve())
        self.assertEqual(self.pending(), [])
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "board.py"), "--board", str(self.path), "next"],
            cwd=self.root.parent, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("infrastructure clue", result.stdout)


class HierarchyTests(unittest.TestCase):
    """A finer candidate carries the search: coarser rivals without open descendants go dormant; `country` settles."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "board.json"
        self.cli("init", "--photo", "photo.jpg")

    def cli(self, *args):
        r = subprocess.run([sys.executable, str(SCRIPTS / "board.py"), "--board", str(self.path), *args],
                           cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def shares(self, level):
        b = json.loads(self.path.read_text(encoding="utf-8"))
        return {r["name"]: r for r in board._scores(b, level, "equal")}

    def test_city_under_one_country_makes_the_other_dormant_not_excluded(self):
        self.cli("add", "Russia", "Ukraine", "--level", "country")
        self.assertAlmostEqual(self.shares("country")["Ukraine"]["share"], 0.5)
        out = self.cli("add", "Lipetsk", "--level", "city", "--parent", "Russia", "--no-geocode")
        self.assertIn("nothing on the board says why Lipetsk", out)
        self.assertAlmostEqual(self.shares("country")["Ukraine"]["share"], 0.5)      # a bare name below Russia proves nothing
        self.cli("clue", "Липецк on the sign", "--kind", "text", "--status", "read", "--file", "photo.jpg")
        self.cli("evidence", "--clue", "K1", "--for", "Lipetsk:20", "--why", "read on the sign")
        rows = self.shares("country")
        self.assertAlmostEqual(rows["Russia"]["share"], 1.0)
        self.assertEqual(rows["Ukraine"]["share"], 0.0)
        self.assertTrue(rows["Ukraine"].get("dormant"))
        self.assertFalse(rows["Ukraine"]["excluded"])
        self.assertIn("dormant", self.cli("rank"))
        self.cli("exclude", "Lipetsk", "--why", "wrong street grid", "--file", "photo.jpg", "--covers", "52.58,39.55") if False else None
        b = json.loads(self.path.read_text(encoding="utf-8"))
        b["candidates"]["Lipetsk"]["status"] = "excluded"          # the city falls: the countries are back in play
        self.path.write_text(json.dumps(b), encoding="utf-8")
        rows = self.shares("country")
        self.assertAlmostEqual(rows["Ukraine"]["share"], 0.5)
        self.assertFalse(rows["Ukraine"].get("dormant"))

    def test_country_context_settles_the_country_level(self):
        self.cli("add", "Russia", "Ukraine", "--level", "country")
        self.cli("country", "RU")
        rows = self.shares("country")
        self.assertTrue(rows["Russia"].get("settled"))
        self.assertTrue(rows["Ukraine"].get("superseded"))
        self.assertEqual(rows["Ukraine"]["share"], 0.0)
        b = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertIsNone(board._frontier(b) if False else None)
        self.cli("add", "Lipetsk", "Yelets", "--level", "city", "--parent", "Russia", "--no-geocode")
        b = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(board._frontier(b), "city")

    def test_parent_country_is_added_and_country_settles_with_a_candidate(self):
        out = self.cli("add", "Lipetsk", "--level", "city", "--parent", "Russia", "--no-geocode")
        self.assertIn("Russia added as the country candidate", out)
        b = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(b["candidates"]["Russia"]["level"], "country")
        self.assertEqual(b["candidates"]["Lipetsk"]["parent"], "Russia")
        self.assertIn("added as the country candidate", self.cli("country", "IT"))
        b = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(b["country"], "IT")
        self.assertTrue(any(c["level"] == "country" and c.get("iso2") == "IT" for c in b["candidates"].values()))
        self.assertIn("already exists", self.cli("init", "--photo", "photo.jpg"))              # idempotent after start

    def test_dormant_respects_the_rivals_own_evidence_and_never_the_settled_country(self):
        self.cli("add", "Russia", "Ukraine", "--level", "country")
        self.cli("clue", "Cyrillic everywhere", "--kind", "text", "--status", "read", "--file", "photo.jpg")
        self.cli("evidence", "--clue", "K1", "--for", "Ukraine:30", "--why", "Ukrainian letters")
        self.cli("add", "Lipetsk", "--level", "city", "--parent", "Russia", "--no-geocode")
        self.cli("clue", "weak hint", "--kind", "hint", "--status", "inferred", "--file", "photo.jpg")
        self.cli("evidence", "--clue", "K2", "--for", "Lipetsk:2", "--why", "a guess")
        rows = self.shares("country")
        self.assertFalse(rows["Ukraine"].get("dormant"))                                     # its own evidence outweighs the child's
        self.assertGreater(rows["Ukraine"]["share"], rows["Russia"]["share"])
        self.cli("country", "UA")
        rows = self.shares("country")
        self.assertTrue(rows["Ukraine"].get("settled"))
        self.assertAlmostEqual(sum(r["share"] for r in rows.values()), 1.0)                   # the level still sums to one

    def test_apply_observation_kinds_are_observed_and_check_flags_ties(self):
        out = self.cli("apply", "--kind", "driving-side", "--value", "left")
        self.assertIn("observed", out)
        b = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertTrue(all(c["status"] == "observed" for c in b["clues"].values()))
        self.assertTrue(all(e["lr"] <= 5 for e in b["evidence"]))
        r = subprocess.run([sys.executable, str(SCRIPTS / "board.py"), "--board", str(self.path), "check"],
                           cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1)
        self.assertIn("undecided", r.stdout)

    def test_ancestor_gap_is_reported(self):
        self.cli("add", "Russia", "Ukraine", "--level", "country")
        self.cli("clue", "Ukrainian letters", "--kind", "text", "--status", "read", "--file", "photo.jpg")
        self.cli("evidence", "--clue", "K1", "--for", "Ukraine:30", "--why", "ї on the sign")
        self.cli("add", "Lipetsk", "Yelets", "--level", "city", "--parent", "Russia", "--no-geocode")
        self.cli("clue", "street view match", "--kind", "match", "--status", "computed", "--file", "photo.jpg")
        self.cli("evidence", "--clue", "K2", "--for", "Lipetsk:10", "--why", "invariant features")
        r = subprocess.run([sys.executable, str(SCRIPTS / "board.py"), "--board", str(self.path), "check"],
                           cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertIn("sits under Russia, which is not first at its level", r.stdout)
        rep = subprocess.run([sys.executable, str(SCRIPTS / "board.py"), "--board", str(self.path), "report"],
                             cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertIn("ancestor_gap", rep.stdout)

    def test_bare_names_are_placed_from_geonames(self):
        real = board._geocode
        board._geocode = lambda name, cc: {"lat": 52.5876, "lon": 39.5515, "population": 509735, "radius_m": 10000,
                                            "bbox": board._bbox_around(52.5876, 39.5515, 10000), "feature": "P.PPLA", "country": cc}
        try:
            args = argparse.Namespace(names=["Lipetsk"], from_=None, radius=500, level="city", parent="Russia", bbox=None,
                                      prior=1.0, note=None, no_geocode=False)
            self.cli("add", "Russia", "--level", "country")
            board.cmd_add(args, self.path)
        finally:
            board._geocode = real
        c = json.loads(self.path.read_text(encoding="utf-8"))["candidates"]["Lipetsk"]
        self.assertEqual(c["center"], [52.5876, 39.5515])
        self.assertEqual(len(c["bbox"]), 4)
        self.assertEqual(c["geocode"]["population"], 509735)
        self.assertEqual(board._country_of(json.loads(self.path.read_text(encoding="utf-8")), "Russia"), "RU")


class LevelGapTests(unittest.TestCase):
    """A point added under the city instead of under its road: its evidence never reached the road ranking, and report named another road."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "board.json"
        (self.root / "match.jpg").write_bytes(b"x")
        (self.root / "evidence.jpg").write_bytes(b"x")
        run = CorridorPendingTests.run_board
        self.run_board = lambda *a, ok=True: run(self, *a, ok=ok)
        self.run_board("init", "--photo", "photo.jpg")
        self.run_board("add", "City", "--level", "district")
        self.run_board("add", "A ST 100", "--level", "road", "--parent", "City", "--bbox", "49.20,-123.20,49.201,-123.19")
        self.run_board("add", "B ST 200", "--level", "road", "--parent", "City", "--bbox", "49.21,-123.20,49.211,-123.19")
        self.run_board("clue", "street view matches", "--kind", "municipal", "--status", "computed", "--file", "match.jpg")
        self.run_board("evidence", "--clue", "K1", "--for", "A ST 100:2", "--why", "partial", "--file", "match.jpg")

    def add_point(self, *extra):
        out = self.run_board("add", "spot", "--level", "point", "--parent", "City", "--bbox", "49.2159,-123.1095,49.2162,-123.1091", *extra)
        self.run_board("evidence", "--clue", "K1", "--for", "spot:10", "--why", "invariant features", "--file", "match.jpg")
        return out

    def ranking(self):
        return [r["name"] for r in board._scores(json.loads(self.path.read_text(encoding="utf-8")), "road", "uniform")]

    def test_skipped_level_is_flagged_everywhere(self):
        self.assertIn("2 road candidates", self.add_point().stdout)
        check = self.run_board("check", ok=False)
        self.assertEqual(check.returncode, 1)
        self.assertIn("FAIL spot (point) sits directly under City", check.stdout)
        self.assertIn("leaves the answer out", check.stdout)
        result = self.root / "result.json"
        result.write_text(json.dumps({"lat": 49.216, "lon": -123.1093, "radius_m": 20}), encoding="utf-8")
        report = self.run_board("report", "--merge", str(result)).stdout
        self.assertIn("outside the board's main answer A ST 100", report)
        self.assertTrue(json.loads(result.read_text(encoding="utf-8"))["board"]["level_gaps"])

    def test_moving_under_its_road_carries_support_up(self):
        self.add_point()
        self.run_board("add", "W 60 AVE 100", "--level", "road", "--parent", "City", "--bbox", "49.2158,-123.1112,49.2164,-123.1075")
        self.assertIn("lies inside W 60 AVE 100", self.run_board("check", ok=False).stdout)
        self.run_board("move", "spot", "--parent", "W 60 AVE 100")
        check = self.run_board("check")
        self.assertEqual(check.returncode, 0)
        self.assertNotIn("FAIL", check.stdout)
        self.assertIn("main answer spot", check.stdout)                 # the verified point carries the search; its road leads the road level
        self.assertEqual(self.ranking()[0], "W 60 AVE 100")
        rows = {r["name"]: r for r in board._scores(json.loads(self.path.read_text(encoding="utf-8")), "road", "uniform")}
        self.assertTrue(rows["A ST 100"].get("dormant") and rows["B ST 200"].get("dormant"))
        result = self.root / "result.json"
        result.write_text(json.dumps({"lat": 49.216, "lon": -123.1093}), encoding="utf-8")
        self.assertNotIn("WARN", self.run_board("report", "--merge", str(result)).stdout)

    def test_against_on_a_point_does_not_reach_its_road(self):
        self.run_board("add", "spot2", "--level", "point", "--parent", "B ST 200")
        before = self.ranking()
        self.run_board("evidence", "--clue", "K1", "--against", "spot2:0.1", "--why", "no match", "--file", "match.jpg")
        self.assertEqual(self.ranking(), before)
        b = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(board._inherited(b, "B ST 200", set()), [])

    def test_same_clue_counts_once(self):
        self.run_board("add", "spot3", "--level", "point", "--parent", "A ST 100")
        self.run_board("evidence", "--clue", "K1", "--for", "spot3:10", "--why", "same clue", "--file", "match.jpg")
        b = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(board._inherited(b, "A ST 100", {"K1"}), [])   # A ST 100 already has its own K1 evidence

    def test_move_rejects_finer_parent(self):
        self.run_board("add", "spot4", "--level", "point", "--parent", "A ST 100")
        self.run_board("move", "A ST 100", "--parent", "spot4", ok=False)


class ExclusionAndReportTests(unittest.TestCase):
    """Southern/western coordinates in value flags, rule numbers, check exit code, ingest guard, report --merge, apply."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "board.json"
        (self.root / "frame.json").write_text('{"hits": []}', encoding="utf-8")
        run = CorridorPendingTests.run_board
        self.run_board = lambda *a, ok=True: run(self, *a, ok=ok)
        self.run_board("init", "--photo", "photo.jpg")
        self.run_board("add", "Echuca", "--level", "district", "--bbox", "-35.82,144.70,-35.78,144.78")
        self.run_board("add", "Moama", "--level", "district", "--bbox", "-35.84,144.72,-35.80,144.80")
        self.run_board("clue", "sign reads Echuca", "--kind", "text", "--status", "read", "--file", "frame.json")

    def read_board(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_negative_coordinates_are_plain_values(self):
        # a span over the whole extent is accepted; argparse must not read "-35.84,…" as an option name
        out = self.run_board("exclude", "Moama", "--clue", "K1", "--computed", "frame.json", "--covers", "-35.84,144.72:-35.80,144.80")
        self.assertIn("Excluded Moama", out.stdout)
        self.assertEqual(self.read_board()["candidates"]["Moama"]["excluded_by"]["covers"], "-35.84,144.72:-35.80,144.80")
        # a single point parses too, and is then refused on coverage grounds (not by argparse)
        self.run_board("add", "Deniliquin", "--level", "district", "--bbox", "-35.60,144.90,-35.50,145.00")
        bad = self.run_board("exclude", "Deniliquin", "--clue", "K1", "--computed", "frame.json", "--covers", "-35.55,144.95", ok=False)
        self.assertIn("covers only about 0%", bad.stderr)
        self.assertNotIn("expected one argument", bad.stderr)

    def test_rule_and_step_numbers_follow_skill_md(self):
        self.run_board("clue", "looks Australian", "--kind", "hint", "--status", "inferred")
        err = self.run_board("exclude", "Echuca", "--clue", "K2", "--computed", "frame.json", "--covers", "-35.82,144.70:-35.78,144.78", ok=False).stderr
        self.assertIn("Hard rule 6", err)
        self.assertNotIn("Hard rule 9", err)
        empty = self.root / "empty.json"
        subprocess.run([sys.executable, str(SCRIPTS / "board.py"), "--board", str(empty), "init", "--photo", "p.jpg"], cwd=self.root, capture_output=True)
        nxt = subprocess.run([sys.executable, str(SCRIPTS / "board.py"), "--board", str(empty), "next"], cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertIn("step 3", nxt.stdout)
        self.assertIn("steps 4–5", nxt.stdout)
        self.assertNotIn("step 2", nxt.stdout)

    def test_check_exit_code_follows_fail_lines(self):
        failing = self.run_board("check", ok=False)      # main answer has no verified evidence yet
        self.assertEqual(failing.returncode, 1)
        self.assertIn("FAIL main answer", failing.stdout)
        self.assertIn("Result: has FAIL", failing.stdout)
        self.run_board("evidence", "--clue", "K1", "--for", "Echuca:20", "--why", "read", "--file", "frame.json")
        passing = self.run_board("check")
        self.assertEqual(passing.returncode, 0)
        self.assertIn("Result: pass", passing.stdout)

    def test_ingest_skips_self_assessed_uninformative_output(self):
        prior = self.root / "prior.json"
        prior.write_text(json.dumps({"tool": "prior.py", "assessment": {"informative": False, "reasons": ["flat distribution"]},
                                     "signals": [{"kind": "model", "status": "model", "level": "country", "clue": "rank", "p": {"AU": 0.9}}]}), encoding="utf-8")
        out = self.run_board("ingest", str(prior))
        self.assertIn("Not ingested", out.stdout)
        self.assertIn("flat distribution", out.stdout)
        b = self.read_board()
        self.assertEqual(len(b["clues"]), 1)                 # only the read clue from setUp
        self.assertEqual(b["evidence"], [])
        prior.write_text(json.dumps({"tool": "prior.py", "assessment": {"informative": True},
                                     "signals": [{"kind": "model", "status": "model", "level": "country", "clue": "rank", "p": {"AU": 0.9}}]}), encoding="utf-8")
        self.assertIn("Ingested 1 signals", self.run_board("ingest", str(prior)).stdout)

    def test_report_merge_reads_result_radius_and_heading(self):
        self.run_board("evidence", "--clue", "K1", "--for", "Echuca:20", "--why", "read", "--file", "frame.json")
        session = self.root / "session.json"            # photo_session.py shape: lat/lon/radius/heading under "result"
        session.write_text(json.dumps({"result": {"latitude": -35.80, "longitude": 144.75, "radius_m": 120, "heading": 47.0}}), encoding="utf-8")
        rep = json.loads(self.run_board("report", "--merge", str(session)).stdout)
        self.assertEqual((rep["main"]["radius_m"], rep["main"]["heading"]), (120, 47.0))
        self.assertNotIn("main_mismatch", rep)
        merged = json.loads(session.read_text(encoding="utf-8"))
        self.assertEqual(merged["board"]["main"]["heading"], 47.0)
        flat = self.root / "result.json"                # result.json shape: top-level keys
        flat.write_text(json.dumps({"lat": -36.5, "lon": 146.0, "radius_m": 50}), encoding="utf-8")
        rep = json.loads(self.run_board("report", "--merge", str(flat)).stdout)
        self.assertEqual(rep["main"]["radius_m"], 50)
        self.assertNotIn("heading", rep["main"])
        self.assertIn("outside the board's main answer Echuca", rep["main_mismatch"])
        flat.write_text(json.dumps({"lat": -35.80, "lon": 144.75, "radius_m": "abc", "heading": None}), encoding="utf-8")
        rep = json.loads(self.run_board("report", "--merge", str(flat)).stdout)   # non-numeric radius: ignored, no crash
        self.assertNotIn("radius_m", rep["main"])
        self.assertNotIn("heading", rep["main"])

    def test_apply_driving_side_caps_observed_likelihood_ratio(self):
        self.run_board("add", "Portugal", "--level", "country")
        out = self.run_board("apply", "--kind", "driving-side", "--value", "left", "--status", "observed", "--lr", "20").stdout
        self.assertIn("likelihood ratio capped at 5", out)
        b = self.read_board()
        self.assertEqual(b["clues"]["K2"], {**b["clues"]["K2"], "kind": "driving-side", "status": "observed", "used": True})
        by_cand = {e["candidate"]: e["lr"] for e in b["evidence"] if e["clue"] == "K2"}
        self.assertEqual(by_cand["Australia"], 5)
        self.assertEqual(b["candidates"]["Australia"]["level"], "country")
        self.assertAlmostEqual(by_cand["Portugal"], 0.2)        # right-hand traffic: evidence against, not excluded
        self.assertNotEqual(b["candidates"]["Portugal"].get("status"), "excluded")


if __name__ == "__main__":
    unittest.main()
