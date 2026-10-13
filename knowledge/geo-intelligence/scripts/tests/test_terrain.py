#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy", "tzdata"]
# ///
"""Offline terrain.py fit regressions on synthetic terrain. Run: uv run scripts/tests/test_terrain.py"""
from __future__ import annotations

import contextlib
from datetime import datetime
import io
import json
import math
import os
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import terrain

LAT0, LON0 = 38.0, 106.0
W, H, HROW = 2000, 1125, 600.0


class FakeDEM:
    """Flat plain; a low near range 6 km west that ends 1 km north of the camera; a high far range 20 km west."""

    def __init__(self, *a, **k):
        pass

    def sample(self, lat, lon):
        y = (np.asarray(lat) - LAT0) * 110540
        x = (np.asarray(lon) - LON0) * 111320 * math.cos(math.radians(LAT0))
        crest = 1500 + 500 * np.sin(y / 2500) + 300 * np.cos(y / 1300)
        far = crest * np.exp(-((x + 20000) / 2500) ** 2)
        near = (350 + 120 * np.sin(y / 700)) * np.exp(-((x + 6000) / 400) ** 2) * (y < 1000) * (y > -4000)
        return np.maximum(far, near)


def synth_ridge(path: Path, f35: float, heading: float, two_layer: bool, roll: float = 0.0, photo: Path | None = None) -> None:
    """Project the fake terrain through a pinhole at f35 / heading, write ridge.json with an assumed 26 mm focal.
    roll tilts the frame with fit's convention: row grows by tan(roll)·(x − cx)."""
    f = f35 / 43.2666 * math.hypot(W, H)
    xs = np.arange(40, W - 40, 80, dtype=float)
    az = (heading + np.degrees(np.arctan((xs - W / 2) / f))) % 360
    ang, dist = terrain.cast(FakeDEM(), (LAT0, LON0), 1.6, az, 30000, near=150, n=600)
    tilt = math.tan(math.radians(roll)) * (xs - W / 2)
    rel = np.arctan((xs - W / 2) / f)                                  # horizontal offset of each column from the optical axis
    row = lambda a: HROW - f * np.tan(np.radians(a)) / np.cos(rel)   # true pinhole: the vertical scale shrinks off-axis
    far = row(ang.max(axis=1)) + tilt
    near_ang = ang[:, dist <= 9000].max(axis=1)
    near = row(near_ang) + tilt
    ridge = {"photo": str(photo or ""), "image_size": [W, H], "cx": W / 2, "ridge": [[int(x), int(round(y))] for x, y in zip(xs, far)],
             "flat": None, "hrow": HROW, "f0": 26 / 43.2666 * math.hypot(W, H), "f0_source": "assumed", "f35_equiv": 26.0,
             "near": [], "near_clear": []}
    if two_layer:
        stand = near_ang > 0.3                                       # columns where the near range stands up
        ridge["near"] = [[int(x), int(round(y))] for x, y, s in zip(xs, near, stand) if s]
        clear = xs[~stand & (xs > W / 2)]
        ridge["near_clear"] = [[int(clear.min()), int(clear.max()), float(HROW - f * np.tan(np.radians(0.25)))]]   # one row for the range: on-axis bound
    path.write_text(json.dumps(ridge), encoding="utf-8")


def run_fit(out: Path, *argv: str, dem=FakeDEM) -> tuple[dict, str]:
    """terrain.py fit --out out *argv on a fake DEM: (fit.json, stderr)."""
    err = io.StringIO()
    with patch.object(terrain, "DEM", dem), patch.object(sys, "argv", ["terrain.py", "fit", "--out", str(out), *argv]), \
            contextlib.redirect_stderr(err):
        terrain.main()
    return json.loads(out.read_text(encoding="utf-8")), err.getvalue()


def fit(ridge: Path, out: Path, *extra: str) -> tuple[dict, str]:
    return run_fit(out, "--at", f"{LAT0},{LON0}", "--radius", "0", "--ridge", str(ridge),
                   "--range", "30000", "--min-peak", "2", "--nsamp", "400", *extra)


def hits_args(d: Path, n: int, params: dict | None = None) -> list[str]:
    """fit arguments over a scan-shaped d/hits.json: n clusters 1.1 km apart going north, each seeing the fake ranges
    (far range 4.3°, below fit's fallback --min-peak 6); params is the scan's params block."""
    synth_ridge(d / "ridge.json", 26.0, 270.0, False)
    clusters = [{"lat": LAT0 + i * 0.01, "lon": LON0, "name": f"c{i}", "h0": 0, "max_ang": 5, "az": 270, "n": 1} for i in range(n)]
    (d / "hits.json").write_text(json.dumps({"params": params or {}, "n_samples": n, "n_hits": n, "n_clusters": n,
                                             "hits": clusters, "clusters": clusters}), encoding="utf-8")
    return ["--hits", str(d / "hits.json"), "--radius", "0", "--ridge", str(d / "ridge.json"), "--range", "30000",
            "--nsamp", "400", "--focal-scales", "1"]


class ShoreDEM(FakeDEM):
    """FakeDEM plus a 30 % slope rising west of the camera: east of it is the lake (flat), the camera stands at the shore."""

    def sample(self, lat, lon):
        x = (np.asarray(lon) - LON0) * 111320 * math.cos(math.radians(LAT0))
        return super().sample(lat, lon) + np.where(x < 0, -0.3 * x, 0.0)


class ShadeTests(unittest.TestCase):
    """FakeDEM: a 350 m range 6 km west of the camera (3.3° above it), a 1500 m range 20 km west (4.3°), flat to the east."""

    def test_shadow_mask_follows_the_sun(self):
        dem = FakeDEM()
        la, lo = np.array([LAT0]), np.array([LON0])
        self.assertTrue(terrain.shadow_mask(dem, la, lo, 270, 2.0, step=50, reach=25000)[0])      # low sun behind the near range
        self.assertFalse(terrain.shadow_mask(dem, la, lo, 270, 10.0, step=50, reach=25000)[0])    # sun above both ranges
        self.assertFalse(terrain.shadow_mask(dem, la, lo, 90, 2.0, step=50, reach=25000)[0])      # east is flat
        self.assertTrue(terrain.shadow_mask(dem, la, lo, 90, -1.0, step=50, reach=25000)[0])      # night
        self.assertTrue(terrain.shadow_mask(dem, la, lo, 270, 2.0, step=50, reach=4000)[0] is np.False_ or
                        not terrain.shadow_mask(dem, la, lo, 270, 2.0, step=50, reach=4000)[0])   # reach shorter than the range: not seen

    def test_building_shadows_and_point_tests(self):
        gj = {"features": [{"type": "Feature", "properties": {"building": "yes", "building:levels": "5"},
                            "geometry": {"type": "Polygon", "coordinates": [[[LON0, LAT0], [LON0 + 0.0003, LAT0], [LON0 + 0.0003, LAT0 + 0.0002], [LON0, LAT0 + 0.0002], [LON0, LAT0]]]}}]}
        sh = terrain.building_shadows(gj, az=180, el=45, default_h=8, level_h=3)                  # sun due south: shadow due north, 15 m long
        self.assertEqual(sh[0]["height_m"], 15.0)
        self.assertAlmostEqual(sh[0]["shadow_m"], 15.0, places=3)
        north = LAT0 + 0.0002 + 10 / 110540                                                      # 10 m north of the north wall: shaded
        self.assertTrue(terrain.in_building_shadow(north, LON0 + 0.00015, sh))
        self.assertFalse(terrain.in_building_shadow(LAT0 + 0.0002 + 25 / 110540, LON0 + 0.00015, sh))   # 25 m north: beyond the shadow
        self.assertFalse(terrain.in_building_shadow(LAT0 - 10 / 110540, LON0 + 0.00015, sh))        # south side: lit
        self.assertEqual(terrain.building_shadows(gj, az=180, el=0, default_h=8, level_h=3), [])

    def test_sweep_finds_the_daylight_window_cut_by_the_western_range(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "sweep.json"
            # winter: the sun sets at ~240°, straight behind the near range (its y-span is -4000..1000 m); in June it sets at ~300° and misses it
            argv = ["terrain.py", "shade", "--at", f"{LAT0},{LON0}", "--date", "2025-12-21", "--tz", "Asia/Shanghai",
                    "--lit", f"{LAT0},{LON0}:camera", "--step", "100", "--reach", "25000", "--minutes", "5", "--json", str(out)]
            with patch.object(terrain, "DEM", FakeDEM), patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                terrain.main()
            spans = json.loads(out.read_text(encoding="utf-8"))["sweep"]["days"][0]["spans"]
            self.assertEqual(len(spans), 1)
            start, end = spans[0]
            self.assertGreater(start, "08:00")              # flat east: lit from sunrise (~08:17 at 38 N, 106 E on Dec 21)
            self.assertLess(start, "08:40")
            self.assertGreater(end, "16:45")                # sunset ~17:39; the near range (3.3° high) cuts the last ~20 minutes
            self.assertLess(end, "17:30")


class SkylineCardTests(unittest.TestCase):
    def test_sheet_writes_the_stacked_card_and_names_visible_peaks(self):
        with tempfile.TemporaryDirectory() as td:
            ridge, out, sheet = Path(td) / "ridge.json", Path(td) / "fit.json", Path(td) / "top.jpg"
            synth_ridge(ridge, 26.0, 270.0, False)
            kx = 111320 * math.cos(math.radians(LAT0))
            peaks = {"type": "FeatureCollection", "features": [
                {"type": "Feature", "properties": {"name": "Far Crest", "natural": "peak", "ele": "1800"},
                 "geometry": {"type": "Point", "coordinates": [LON0 - 20000 / kx, LAT0]}},            # on the far range crest: visible
                {"type": "Feature", "properties": {"name": "Low Knoll", "natural": "peak", "ele": "60"},
                 "geometry": {"type": "Point", "coordinates": [LON0 - 4000 / kx, LAT0]}},             # 4 km west, 60 m: under the near range's skyline
                {"type": "Feature", "properties": {"name": "Behind Me", "natural": "peak", "ele": "900"},
                 "geometry": {"type": "Point", "coordinates": [LON0 + 5000 / kx, LAT0]}}]}            # east: outside the frame
            (Path(td) / "peaks.geojson").write_text(json.dumps(peaks), encoding="utf-8")
            res, err = fit(ridge, out, "--sheet", str(sheet), "--peaks", str(Path(td) / "peaks.geojson"), "--focal-scales", "1")
            card = sheet.with_name("top_skyline.jpg")
            self.assertTrue(card.exists())
            self.assertIn("skyline card", err)
            side = json.loads(card.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(side["top"][0]["rank"], 1)
            self.assertAlmostEqual(side["top"][0]["heading"], 270.0, delta=2.0)
            names = [p["name"] for p in side["top"][0]["peaks"]]
            self.assertIn("Far Crest", names)
            self.assertNotIn("Low Knoll", names)
            self.assertNotIn("Behind Me", names)
            from PIL import Image
            with Image.open(card) as im:
                self.assertLessEqual(im.width, 1000)
            with Image.open(sheet) as im:
                self.assertLessEqual(im.width, 360)                                           # one record: one tile, no empty columns
            self.assertIn("peakfinder_url", side["top"][0])
            self.assertIn("--peaks " + shlex.quote(str(Path(td) / "peaks.geojson")), err)   # the printed view command labels them too


class BudgetTests(unittest.TestCase):
    def test_fit_stops_at_the_budget_with_a_partial_ranking(self):
        with tempfile.TemporaryDirectory() as td:
            res, err = run_fit(Path(td) / "fit.json", *hits_args(Path(td), 6), "--min-peak", "2", "--budget-min", "0.000001")
            self.assertTrue(res["partial"])
            self.assertEqual(res["status"], "budget")
            self.assertEqual(res["n_clusters"], 1)                                   # the first cluster is always scored
            self.assertEqual(len(res["unscored_clusters"]), 5)
            self.assertIn("--select", err)
            self.assertIn("PARTIAL", err)


class KillDEM(FakeDEM):
    """Dies when fit loads the third cluster (LAT0 + 0.02), as a killed process would."""

    def __init__(self, center, *a, **k):
        if abs(center[0] - (LAT0 + 0.02)) < 1e-9:
            raise RuntimeError("killed")


class CheckpointTests(unittest.TestCase):
    def killed_run(self, d: Path) -> tuple[dict, str]:
        out, err = d / "fit.json", io.StringIO()
        argv = ["terrain.py", "fit", "--out", str(out), *hits_args(d, 6), "--min-peak", "2"]
        with patch.object(terrain, "DEM", KillDEM), patch.object(sys, "argv", argv), contextlib.redirect_stderr(err), \
                self.assertRaises(RuntimeError):
            terrain.main()
        self.assertEqual(list(d.glob("*.part")), [])
        return json.loads(out.read_text(encoding="utf-8")), err.getvalue()

    def test_a_killed_fit_leaves_the_scored_clusters_and_the_rest_to_select(self):
        with tempfile.TemporaryDirectory() as td, patch.object(terrain, "CHECKPOINT_S", 0.0):
            res, err = self.killed_run(Path(td))
        self.assertEqual(res["status"], "running")
        self.assertEqual(res["pid"], os.getpid())                              # running + a pid that is gone = a dead run
        self.assertIsNotNone(datetime.fromisoformat(res["updated_at"]).tzinfo)
        self.assertTrue(res["partial"])
        self.assertEqual(res["n_clusters"], 2)
        self.assertEqual([x["hit"] for x in res["clusters"] if x["best"]], [0, 1])
        self.assertEqual(res["unscored_clusters"], [2, 3, 4, 5])
        self.assertIn("(saved 2/6; if killed: --select 2,3,4,5 with a new --out)", err)

    def test_checkpoints_are_throttled(self):
        with tempfile.TemporaryDirectory() as td:                               # default 30 s: the second cluster is not written
            res, err = self.killed_run(Path(td))
        self.assertEqual(res["n_clusters"], 1)
        self.assertEqual(res["unscored_clusters"], [1, 2, 3, 4, 5])
        self.assertIn("cluster 2/6 hit1 c1", err)
        self.assertIn("(saved 1/6; if killed: --select 1,2,3,4,5 with a new --out)", err)

    def test_an_unbudgeted_run_ends_done(self):
        with tempfile.TemporaryDirectory() as td:
            res, err = run_fit(Path(td) / "fit.json", *hits_args(Path(td), 3), "--min-peak", "2", "--budget-min", "0")
            self.assertEqual(list(Path(td).glob("*.part")), [])
        self.assertEqual(res["status"], "done")
        self.assertFalse(res["partial"])
        self.assertEqual(res["unscored_clusters"], [])
        self.assertEqual(res["n_clusters"], 3)
        self.assertIn("(saved 3/3)", err)

    def test_a_failed_checkpoint_is_skipped_and_the_final_write_lands(self):
        real, calls = terrain.os.replace, []

        def locked(src, dst):                                                   # a reader holds fit.json through every checkpoint
            calls.append(dst)
            if json.loads(Path(src).read_text(encoding="utf-8"))["status"] == "running":
                raise PermissionError(13, "in use", str(dst))
            real(src, dst)

        with tempfile.TemporaryDirectory() as td, patch.object(terrain, "CHECKPOINT_S", 0.0), patch.object(terrain.os, "replace", locked), \
                patch.object(terrain, "REPLACE_WAIT_S", 0.0):
            res, err = run_fit(Path(td) / "fit.json", *hits_args(Path(td), 3), "--min-peak", "2")
            self.assertEqual(list(Path(td).glob("*.part")), [])
        self.assertEqual(len(calls), 3 * terrain.REPLACE_TRIES + 1)              # each checkpoint retried, then skipped
        self.assertEqual(res["status"], "done")
        self.assertEqual(res["n_clusters"], 3)
        self.assertIn("not saved yet: PermissionError", err)

    def test_a_short_hold_is_waited_out(self):
        real, calls = terrain.os.replace, []

        def held(src, dst):                                                     # a viewer poll reads fit.json for a moment
            calls.append(dst)
            if len(calls) <= 2:
                raise PermissionError(13, "in use", str(dst))
            real(src, dst)

        with tempfile.TemporaryDirectory() as td, patch.object(terrain, "CHECKPOINT_S", 0.0), patch.object(terrain.os, "replace", held), \
                patch.object(terrain, "REPLACE_WAIT_S", 0.0):
            res, err = run_fit(Path(td) / "fit.json", *hits_args(Path(td), 2), "--min-peak", "2")
        self.assertEqual(len(calls), 2 + 3)                                     # two refused tries, then 2 checkpoints and the final write
        self.assertIn("(saved 1/2;", err)
        self.assertNotIn("not saved yet", err)
        self.assertEqual(res["status"], "done")

    def test_a_final_write_that_stays_locked_leaves_the_ranking_and_the_move_command(self):
        def locked(src, dst):                                                   # a reader never lets go of fit.json
            raise PermissionError(13, "in use", str(dst))

        with tempfile.TemporaryDirectory() as td, patch.object(terrain, "CHECKPOINT_S", 0.0), patch.object(terrain.os, "replace", locked), \
                patch.object(terrain, "REPLACE_WAIT_S", 0.0):
            out, err = Path(td) / "fit.json", io.StringIO()
            argv = ["terrain.py", "fit", "--out", str(out), *hits_args(Path(td), 2), "--min-peak", "2"]
            with patch.object(terrain, "DEM", FakeDEM), patch.object(sys, "argv", argv), contextlib.redirect_stderr(err):
                terrain.main()                                                  # no traceback after the whole scoring run
            parts = list(Path(td).glob("fit.json.*.part"))
            self.assertEqual(len(parts), 1)
            res = json.loads(parts[0].read_text(encoding="utf-8"))
            self.assertFalse(out.exists())
        err = err.getvalue()
        self.assertEqual((res["status"], res["n_clusters"]), ("done", 2))       # the full ranking survives in the .part
        self.assertIn(f"Move-Item -Force -LiteralPath '{parts[0]}' -Destination '{out}'", err)
        self.assertIn(f"mv -f {shlex.quote(str(parts[0]))} {shlex.quote(str(out))}", err)
        self.assertIn("PeakFinder, same camera for the eyes", err)              # the report after the write still prints

    def test_a_long_select_list_is_named_never_truncated(self):              # a pasted "…" would break --select
        self.assertEqual(terrain._select_list([3, 4], "fit.json"), "3,4 with a new --out")
        self.assertEqual(terrain._select_list(list(range(21)), "fit.json"), "<the 21 unscored_clusters in fit.json> with a new --out")


class MinPeakTests(unittest.TestCase):
    def test_fit_inherits_the_scan_min_peak(self):
        with tempfile.TemporaryDirectory() as td:
            res, _ = run_fit(Path(td) / "fit.json", *hits_args(Path(td), 1, {"min_peak_deg": 2}))
        self.assertEqual(res["params"]["min_peak_deg"], 2)
        self.assertEqual(res["n_cams"], 1)                                          # the 4.3° far range passes 2°, not the fallback 6°

    def test_without_scan_params_the_fallback_is_6(self):
        with tempfile.TemporaryDirectory() as td:
            res, _ = run_fit(Path(td) / "fit.json", *hits_args(Path(td), 1))
        self.assertEqual(res["params"]["min_peak_deg"], 6)
        self.assertEqual(res["n_skipped"]["no_peak"], 1)

    def test_a_stricter_explicit_value_names_both_and_the_exit(self):
        with tempfile.TemporaryDirectory() as td:
            res, err = run_fit(Path(td) / "fit.json", *hits_args(Path(td), 1, {"min_peak_deg": 2}), "--min-peak", "6")
        self.assertEqual(res["params"]["min_peak_deg"], 6)
        line = next(x for x in err.splitlines() if "stricter" in x)
        self.assertIn("--min-peak 6°", line)
        self.assertIn("scan's 2°", line)
        self.assertIn("rerun without --min-peak", line)


class ViewCommandTests(unittest.TestCase):
    def test_fit_prints_a_view_overlay_command_that_reproduces_the_fit(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            photo = d / "photo.jpg"
            Image.new("RGB", (W, H), (120, 120, 120)).save(photo)
            synth_ridge(d / "ridge.json", 26.0, 270.0, False, photo=photo)
            res, err = fit(d / "ridge.json", d / "fit.json", "--focal-scales", "1")
            line = next(x for x in err.splitlines() if "terrain.py view " in x)
            argv = shlex.split(line[line.index("terrain.py view "):])
            opt = lambda k: argv[argv.index(k) + 1]
            best = res["cams"][0]
            pitch = float(opt("--pitch"))
            self.assertGreater(pitch, 0)                          # horizon row 600 below the frame middle 562.5: looking up
            self.assertAlmostEqual(pitch, best["cc"] + math.degrees(math.atan((HROW - H / 2) / best["f"])), delta=0.006)
            self.assertAlmostEqual(float(opt("--hfov")), 2 * math.degrees(math.atan(W / 2 / best["f"])), delta=0.05)
            self.assertEqual(float(opt("--heading")), best["H"])
            self.assertEqual(Path(opt("--photo")), photo)
            self.assertEqual(Path(opt("--out")), d / "view_best.jpg")
            self.assertIn("--overlay", argv)
            # run it as printed: at the centre column view's red skyline lands on the photo ridge fit matched
            with patch.object(terrain, "DEM", FakeDEM), patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                terrain.main()
            with Image.open(d / "view_best_overlay.jpg") as im:
                col = np.asarray(im.convert("RGB"), dtype=int)[:, W // 2]
            red = np.flatnonzero((col[:, 0] > 200) & (col[:, 1] < 100) & (col[:, 2] < 100))
            ridge_y = dict(map(tuple, json.loads((d / "ridge.json").read_text(encoding="utf-8"))["ridge"]))[W // 2]
            self.assertGreater(red.size, 0)
            self.assertAlmostEqual(float(red.mean()), ridge_y, delta=3)


class TieTests(unittest.TestCase):
    def test_tie_extent_measures_the_stretch_along_the_sight_line(self):
        cams = [{"hit": 0, "cam": [LAT0, LON0 + i * 100 / (111320 * math.cos(math.radians(LAT0)))], "total": 0.30 + 0.005 * i} for i in range(5)]
        cams.append({"hit": 0, "cam": [LAT0 + 0.01, LON0], "total": 0.9})                           # far and bad: not a tie
        t = terrain.tie_extent(cams, 0.30, 0.03)
        self.assertEqual(t["n"], 5)
        self.assertAlmostEqual(t["span_m"], 400.0, delta=2.0)
        self.assertAlmostEqual(t["bearing"], 90.0, delta=1.0)                                        # east-west stretch
        self.assertEqual(terrain.tie_extent(cams[:1], 0.30, 0.03)["n"], 1)
        self.assertIsNone(terrain.tie_extent([], 0.30, 0.03))
        url = terrain.peakfinder_url(46.26, 10.95, 59.4, 67.0, 1180.0)
        self.assertEqual(url, "https://www.peakfinder.com/?lat=46.26000&lng=10.95000&azi=59&fov=67&ele=1180")


class CamLevelTests(unittest.TestCase):
    def test_cam_level_keeps_shore_positions_and_drops_the_slope(self):
        with tempfile.TemporaryDirectory() as td:
            ridge, out = Path(td) / "ridge.json", Path(td) / "fit.json"
            synth_ridge(ridge, 26.0, 270.0, False)
            common = ["--radius", "300", "--grid", "100", "--cam-flat", "10000", "--focal-scales", "1"]
            argv = ["terrain.py", "fit", "--at", f"{LAT0},{LON0}", "--ridge", str(ridge), "--out", str(out),
                    "--range", "30000", "--min-peak", "2", "--nsamp", "400", *common]
            with patch.object(terrain, "DEM", ShoreDEM), patch.object(sys, "argv", argv), contextlib.redirect_stderr(io.StringIO()):
                terrain.main()
            free = json.loads(out.read_text(encoding="utf-8"))
            argv += ["--cam-level", "5"]
            with patch.object(terrain, "DEM", ShoreDEM), patch.object(sys, "argv", argv), contextlib.redirect_stderr(io.StringIO()):
                terrain.main()
            level = json.loads(out.read_text(encoding="utf-8"))
            self.assertGreater(level["n_skipped"]["off_level"], 0)                      # slope positions dropped
            self.assertEqual(free["n_skipped"]["off_level"], 0)
            self.assertLess(level["n_cams"], free["n_cams"])
            self.assertEqual(level["params"]["cam_level_m"], 5)
            self.assertGreater(level["n_cams"], 0)                                      # the lake side still scores
            err = io.StringIO()                                                          # the shore run keeps most positions: no warning
            with patch.object(terrain, "DEM", ShoreDEM), patch.object(sys, "argv", argv), contextlib.redirect_stderr(err):
                terrain.main()
            self.assertLess(level["n_skipped"]["off_level"], level["n_cams"])
            self.assertNotIn("rerun with a larger --cam-level", err.getvalue())
            above = list(argv)                                                           # level taken 200 m up the slope (60 m above the
            above[above.index("--at") + 1] = f"{LAT0},{LON0 - 200 / (111320 * math.cos(math.radians(LAT0)))}"   # flat side): most positions go
            err = io.StringIO()
            with patch.object(terrain, "DEM", ShoreDEM), patch.object(sys, "argv", above), contextlib.redirect_stderr(err):
                terrain.main()
            tight = json.loads(out.read_text(encoding="utf-8"))
            self.assertGreaterEqual(tight["n_skipped"]["off_level"], tight["n_cams"])
            self.assertIn("rerun with a larger --cam-level", err.getvalue())


class FocalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_assumed_focal_searches_wide_and_finds_telephoto(self):
        synth_ridge(self.d / "r.json", 60, 270, two_layer=False)
        res, _ = fit(self.d / "r.json", self.d / "f.json")
        best = res["cams"][0]
        self.assertGreater(len(res["params"]["f35_ladder"]), 10)
        self.assertLess(abs(math.log(best["f35"] / 60)), math.log(1.2))
        self.assertLess(abs((best["H"] - 270 + 180) % 360 - 180), 1.0)
        self.assertIsNone(res["focal_edge"])

    def test_main_camera_only_hits_long_edge_and_warns(self):
        synth_ridge(self.d / "r.json", 60, 270, two_layer=False)
        res, err = fit(self.d / "r.json", self.d / "f.json", "--focal-scales", "0.9,1,1.12")
        self.assertEqual(res["focal_edge"]["top1"], "long")
        self.assertIn("--f35-range", err)

    def test_widened_range_clears_the_edge(self):
        synth_ridge(self.d / "r.json", 60, 270, two_layer=False)
        res, _ = fit(self.d / "r.json", self.d / "f.json", "--f35-range", "20:40")
        self.assertEqual(res["focal_edge"]["top1"], "long")
        res, _ = fit(self.d / "r.json", self.d / "f.json", "--f35-range", "24:80")
        self.assertIsNone(res["focal_edge"])

    def test_two_layer_scores_near_points(self):
        synth_ridge(self.d / "r.json", 60, 270, two_layer=True)
        ridge = json.loads((self.d / "r.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(ridge["near"]), 3)
        res, _ = fit(self.d / "r.json", self.d / "f.json")
        best = res["cams"][0]
        self.assertIn("D1", best)
        self.assertLess(best["rms_near_px"], 6)
        self.assertLess(abs((best["H"] - 270 + 180) % 360 - 180), 1.0)

    def test_perp_line_restricts_heading(self):
        synth_ridge(self.d / "r.json", 60, 270, two_layer=False)
        line = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {},
                "geometry": {"type": "LineString", "coordinates": [[LON0 + 0.003, LAT0 - 0.02], [LON0 + 0.003, LAT0 + 0.02]]}}]}
        (self.d / "l.geojson").write_text(json.dumps(line), encoding="utf-8")
        res, _ = fit(self.d / "r.json", self.d / "f.json", "--perp-line", str(self.d / "l.geojson"), "--perp-tol", "10")
        self.assertLess(abs((res["cams"][0]["H"] - 270 + 180) % 360 - 180), 10.5)
        self.assertEqual(res["cams"][0]["line_brg"], 0.0)

    def _lines(self, parts):
        p = self.d / "l.geojson"
        p.write_text(json.dumps({"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": c}} for c in parts]}), encoding="utf-8")
        return str(p)

    def test_perp_line_distance_ignores_vertex_density(self):
        synth_ridge(self.d / "r.json", 60, 270, two_layer=False)
        lon = LON0 + 0.0005
        a, _ = fit(self.d / "r.json", self.d / "a.json", "--perp-line", self._lines([[[lon, LAT0 - 0.002], [lon, LAT0 + 0.04]]]))
        b, _ = fit(self.d / "r.json", self.d / "b.json", "--perp-line", self._lines([[[lon, LAT0 - 0.002], [lon, LAT0], [lon, LAT0 + 0.04]]]))
        self.assertEqual(a["n_cams"], 1)
        self.assertEqual(b["n_cams"], 1)

    def test_perp_line_picks_nearest_segment_not_nearest_midpoint(self):
        synth_ridge(self.d / "r.json", 60, 270, two_layer=False)
        lon = LON0 + 0.0005
        p = self._lines([[[lon, LAT0 - 0.0001], [lon, LAT0 + 0.005]], [[LON0 - 0.002, LAT0 + 0.001], [LON0 + 0.002, LAT0 + 0.001]]])
        res, _ = fit(self.d / "r.json", self.d / "f.json", "--perp-line", p, "--perp-tol", "10")
        self.assertEqual(res["cams"][0]["line_brg"], 0.0)

    def test_near_dist_within_sight_line_start_is_dropped_not_crash(self):
        synth_ridge(self.d / "r.json", 60, 270, two_layer=True)
        res, err = fit(self.d / "r.json", self.d / "f.json", "--near", "4000")
        self.assertEqual(res["n_cams"], 1)
        self.assertIn("dropped", err)
        with self.assertRaises(SystemExit):
            fit(self.d / "r.json", self.d / "f.json", "--near", "4000", "--near-dist", "3000")

    def test_every_rung_recovers_heading(self):
        for f35 in (13, 20, 26, 40, 90, 135):
            with self.subTest(f35=f35):
                synth_ridge(self.d / "r.json", f35, 270, two_layer=False)
                res, _ = fit(self.d / "r.json", self.d / "f.json")
                self.assertLess(abs((res["cams"][0]["H"] - 270 + 180) % 360 - 180), 2)


class RidgeTests(unittest.TestCase):
    def test_points_and_near_layer_written(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "p.jpg"
            Image.new("RGB", (400, 300), (120, 160, 200)).save(p)
            out = Path(t) / "r.json"
            with patch.object(sys, "argv", ["terrain.py", "ridge", str(p), "--points", "10,100;200,90;390,110",
                                            "--near", "10,140;100,150;180,160", "--near-clear", "250:390@170", "--out", str(out)]), \
                    contextlib.redirect_stdout(io.StringIO()):
                terrain.main()
            r = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(r["ridge_source"], "points")
            self.assertEqual(r["ridge"], [[10, 100], [200, 90], [390, 110]])
            self.assertEqual(len(r["near"]), 3)
            self.assertEqual(r["near_clear"], [[250, 390, 170.0]])


class RollTests(unittest.TestCase):
    def test_roll_solved_lowers_rms_and_is_recovered(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            synth_ridge(d / "r.json", 60, 270, two_layer=False, roll=0.8)
            flat, _ = fit(d / "r.json", d / "a.json", "--roll-max", "0")
            tilted, _ = fit(d / "r.json", d / "b.json", "--roll-max", "1")
            self.assertEqual(flat["cams"][0]["roll"], 0.0)
            self.assertLess(tilted["cams"][0]["rms_px"], flat["cams"][0]["rms_px"])
            self.assertAlmostEqual(tilted["cams"][0]["roll"], 0.8, delta=0.3)
            self.assertLess(abs((tilted["cams"][0]["H"] - 270 + 180) % 360 - 180), 1.0)


class PlaneDEM:
    """100 m plain rising 10 % toward the east."""

    def __init__(self, *a, **k):
        pass

    def sample(self, lat, lon):
        x = (np.asarray(lon, dtype=float) - LON0) * 111320 * math.cos(math.radians(LAT0))
        return 100 + 0.10 * x + 0 * np.asarray(lat, dtype=float)


class SlopeTests(unittest.TestCase):
    def cli(self, *argv) -> str:
        out = io.StringIO()
        with patch.object(terrain, "DEM", PlaneDEM), patch.object(sys, "argv", ["terrain.py", *argv]), contextlib.redirect_stdout(out):
            terrain.main()
        return out.getvalue()

    def points(self, d: Path) -> Path:
        p = d / "c.json"
        p.write_text(json.dumps({"a": [LAT0, LON0], "b": {"lat": LAT0 + 0.001, "lon": LON0}, "c": {"wgs": [LAT0, LON0 + 0.001]}}), encoding="utf-8")
        return p

    def test_slope_sign_follows_bearing(self):
        with tempfile.TemporaryDirectory() as t:
            p, out = self.points(Path(t)), Path(t) / "s.json"
            self.cli("slope", "--points", str(p), "--bearing", "90", "--span", "40", "--out", str(out))
            rows = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual([r["name"] for r in rows], ["a", "b", "c"])
            for r in rows:
                self.assertAlmostEqual(r["slope_pct"], 10.0, delta=0.2)
                self.assertAlmostEqual(r["fwd_m"] - r["back_m"], 4.0, delta=0.1)
            self.cli("slope", "--points", str(p), "--bearing", "270", "--span", "40", "--out", str(out))
            self.assertAlmostEqual(json.loads(out.read_text(encoding="utf-8"))[0]["slope_pct"], -10.0, delta=0.2)
            txt = self.cli("slope", "--points", str(p), "--bearing", "0", "--span", "40")
            self.assertIn("rises toward 0°", txt)
            self.assertAlmostEqual(float(txt.strip().splitlines()[1].split()[-1]), 0.0, delta=0.05)

    def test_elev_single_and_batch(self):
        self.assertEqual(self.cli("elev", "--at", f"{LAT0},{LON0}").strip(), "100 m")
        with tempfile.TemporaryDirectory() as t:
            p, out = self.points(Path(t)), Path(t) / "e.json"
            txt = self.cli("elev", "--points", str(p), "--out", str(out))
            rows = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual([r["name"] for r in rows], ["a", "b", "c"])
            self.assertAlmostEqual(rows[2]["elev_m"], 100 + 0.10 * 0.001 * 111320 * math.cos(math.radians(LAT0)), delta=0.2)
            self.assertIn("c\t", txt)
        with self.assertRaises(SystemExit):
            self.cli("elev")


if __name__ == "__main__":
    unittest.main()
