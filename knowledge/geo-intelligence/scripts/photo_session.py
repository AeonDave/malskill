#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["tzdata"]
# ///
"""Create, finalize and score one timestamped geo-intelligence archive per photograph.

  start     new archive for one photo, or several photos of the same scene (--image repeated); the untouched
            originals are copied with their checksums, the first one is the reference `original`;
            --beside puts the session folder next to the photo instead of under the archive root
            --viewer also opens the live page (viewer.py serve) in the default browser; board.json is created too
  finish    append the chosen country/region/city to the folder name, record the result; --generated BASIS closes a
            generated image with no real place (<timestamp>__generated-image), on evidence only, never on a detector score;
            finish again replaces the answer (the old one goes to result_history with its truth metrics) and rescores a recorded truth
  not-generated  record the operator's "it is real, continue" (session.json generated_override): a place finish is then
            never refused for a declared generation
  truth     record the real location later (from the photo's owner, a puzzle answer, a game reveal), or --generated,
            and score the session: error in km, approximate world-map game score, country/region hit, outcome hit
  scoreboard  accuracy over every scored session: median error, hit rates at 1/25/200/750/2500 km,
            whether "high/medium/low" confidence actually meant what it claimed, and generated calls against the truth
  list      sessions with their status, so an interrupted one can be resumed
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import calendar
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geolib.geomath import haversine_m  # noqa: E402
from geolib.paths import SKILL_DIR, local_config as _local_config  # noqa: E402

_CONFIG = _local_config()
# Archive root: --root, else GEOINT_PHOTOS, else config.local.json "photos_root", else ~/geoint-photos
DEFAULT_ROOT = Path(os.environ.get("GEOINT_PHOTOS") or _CONFIG.get("photos_root") or Path.home() / "geoint-photos").expanduser()
# Time zone of the archive timestamps: GEOINT_TZ, else config.local.json "timezone", else this computer's own
TIMEZONE = os.environ.get("GEOINT_TZ") or _CONFIG.get("timezone")
# Name written to session.json and the report footer: the configured zone, else this computer's zone as the OS names it
TZ_NAME = TIMEZONE or datetime.now().astimezone().tzname() or datetime.now().astimezone().strftime("UTC%z")
UV = os.environ.get("UV") or shutil.which("uv") or "uv"
FOOTER = "<!-- geogussr-archive -->"
TRUTH_START = "<!-- geogussr-truth -->"
TRUTH_END = "<!-- /geogussr-truth -->"
THRESHOLDS_KM = (1, 25, 200, 750, 2500)
SCORE_SCALE_KM = 1492.7  # approximate world-map scoring: 5000 · exp(-d / 1492.7 km)
UNVERIFIED_CLOCK_MIN = 25  # before this elapsed time, an unverified close needs an explicit operator limit
# The operator's words, the one form an early exit (--skip-check, --accept-unverified before the clock) and a verdict on the image
# (finish --generated, not-generated) take: an operator word (an article may precede it), asked/said/confirmed (or the same in the
# operator's language) and a colon, at the start of the reason. Anywhere else ("the user would want…", "users on the forum agree")
# the agent is speaking.
OPERATOR_WORDS = re.compile(r"\s*(?:(?:the|l['’]|el|la|le|der|die)\s*)?"
                            r"(?:operator|operatore|operador|op[ée]rateur|user|utente|usuario|utilisateur|benutzer|nutzer)\s+"
                            r"(?:(?:has|ha|a|hat)\s+)?"
                            r"(?:asked|said|says|confirmed|requested|chiesto|detto|confermato|pidi[oó]|pedido|dijo|dicho|confirm[oó]|confirmado"
                            r"|demand[ée]|dit|confirm[ée]|gesagt|sagte|gebeten|bat|best[äa]tigt)\s*:", re.I)
OPERATOR_FORM = ("put \"operator asked: …\" in the reason as its first words (said or confirmed too, or in the operator's language: "
                 "\"utente ha chiesto: …\", \"usuario dijo: …\")")
# the operator may limit the work (including explicit Quick); an agent-invented time budget is not an early exit
EARLY_EXIT = f"before {UNVERIFIED_CLOCK_MIN} min only when the operator stopped or redirected the analysis: {OPERATOR_FORM}; after it, any stated reason"
SCENE_THRESHOLD = 0.6
# required checks by scene (recon's prior tags the scene): each is done by a file it leaves, known by name here or, for a
# JSON with no telling name, by content (check_hits)
CHECKS = {
    "skyline": {"files": re.compile(r"(^|/)[^/]*(_skyline\.json|_overlay\.(png|jpe?g))$", re.I),
                "command": "terrain.py ridge → fit (--at a candidate, or scan the region's lakes/rivers/roads first: SKILL step 6 mountain and lake/coast/valley rows)"},
    "street": {"files": re.compile(r"(^|/)([^/]*_rank\.json|rank\.json|rank_[^/]*\.json|(match|evidence)[^/]*\.(png|jpe?g))$", re.I),
               "command": "gsv.py sheet / pano.py → match.py rank, sweep.py rank → view, or evidence.py (SKILL step 6 street row; an "
                          "aerial photo or no street-level coverage: evidence.py on the tiles.py map with the camera and heading, --out evidence.jpg)"},
}
# recon.py's own outputs inside its --out-dir: the first pass, never a check
RECON_PARTS = ("intake/", "prior/", "detect/", "meta/", "aidet/", "calib", "textgeo.", "recon.")
RECON_FIRST_PASS = tuple("recon/" + p for p in RECON_PARTS)   # the default recon/ while a run has not written recon.json yet
# images that pin the place by their own geometry, known by name: evidence.py's map with the camera, its --match side by side.
# pose.py output pins by content (_pose_output), a rank file only relative to an answer (_near_fair); spec JSON never pins.
# With a pin, a scene check that was not run is waived, not refused.
PINNING_MARK = re.compile(r"^(evidence|match)[^/]*\.(jpe?g|png)$", re.I)
NEAR_M, FAIR_INLIERS, FAIR_SCORE = 150, 10, 0.25   # a ranked view this near and this good pins the answer and lends its heading
JSON_MAX_BYTES = 8_000_000                          # content checks skip bigger JSON; a 10k-panorama sweep ranking is ~4 MB


def _session_files(folder: Path) -> list[str]:
    """Relative POSIX paths of the session's files, sorted; caches (.geo-cache at any depth) and the originals are not walked."""
    out = []
    for root, dirs, files in os.walk(folder):
        rel = Path(root).relative_to(folder).as_posix()
        dirs[:] = [d for d in dirs if d != ".geo-cache" and not (rel == "." and d == "original")]
        out += [f if rel == "." else f"{rel}/{f}" for f in files]
    return sorted(out)


def _read_json(path: Path):
    """Parsed JSON, or None when unreadable, malformed (a tool may be writing it while the viewer polls) or over JSON_MAX_BYTES."""
    try:
        if path.stat().st_size > JSON_MAX_BYTES:
            return None
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, RecursionError):
        return None


def _recon_first_pass(folder: Path) -> tuple[str, ...]:
    """Path prefixes of recon's first pass: its outputs beside every recon.json it wrote (--out-dir may be any folder, or the
    session root), plus the default recon/ mid-run. Never a whole folder: a check saved beside recon's outputs still counts."""
    prefixes = list(RECON_FIRST_PASS)
    for rel in _session_files(folder):
        if rel.rsplit("/", 1)[-1] != "recon.json":
            continue
        data = _read_json(folder / rel)
        if isinstance(data, dict) and "steps" in data:
            prefixes += [rel[: -len("recon.json")] + p for p in RECON_PARTS]
    return tuple(prefixes)


def _artifact_paths(folder: Path) -> list[str]:
    """Relative POSIX paths of the files a check could have left: recon's first pass and detect.py sheets (standalone runs
    too) are not checks."""
    first_pass = _recon_first_pass(folder)
    return [rel for rel in _session_files(folder) if not rel.startswith(first_pass)
            and not rel.rsplit("/", 1)[-1].lower().startswith(("detect_sheet", "detect_overview"))]


def _first_row(data) -> dict:
    return data[0] if isinstance(data, list) and data and isinstance(data[0], dict) else {}


def _street_ranking(row: dict) -> bool:
    """A street-level ranking row: match.py rank (rank, id, wgs) or sweep.py rank (rank, id, lat/lon). sat_scan.py rows
    (rank, cell, lat/lon) carry no panorama id: a satellite scan is not the street check."""
    return "rank" in row and "id" in row and (bool(row.get("wgs")) or (row.get("lat") is not None and row.get("lon") is not None))


def _pano_index(row: dict) -> bool:
    """A gsv.py / pano.py / baidu_pano.py sheet index row: a panorama id and the heading (bearing) it was rendered at.
    refsheet.py's index (candidate → cells) is a look-alike sheet, not a street comparison."""
    return "id" in row and ("heading" in row or "bearing" in row)


def check_hits(folder: Path, paths: list[str]) -> dict[str, list[str]]:
    """Files among paths that show each scene check ran: by name first (CHECKS), a JSON no name matched by content.
    skyline: terrain.py fit output under any name, partial runs included (a dict with "cams"; scan output has "clusters"
    too, so that key never counts). street: a street-level ranking, or X.index.json of panorama views beside its sheet X.jpg/png."""
    images = {p.lower() for p in paths if p.lower().endswith((".jpg", ".jpeg", ".png"))}
    hits: dict[str, list[str]] = {name: [] for name in CHECKS}
    for rel in paths:
        named = [name for name, spec in CHECKS.items() if spec["files"].search(rel)]
        for name in named:
            hits[name].append(rel)
        if named or not rel.lower().endswith(".json"):          # *.geojson never ends in .json
            continue
        data = _read_json(folder / rel)
        row = _first_row(data)
        stem = rel[: -len(".index.json")].lower() if rel.lower().endswith(".index.json") else None
        if isinstance(data, dict) and "cams" in data:
            hits["skyline"].append(rel)
        elif _street_ranking(row) or (stem and _pano_index(row) and any(stem + ext in images for ext in (".jpg", ".jpeg", ".png"))):
            hits["street"].append(rel)
    return hits


def scene_tags(folder: Path) -> dict | None:
    """recon's zero-shot scene tags (recon/prior/prior.json → scene) as numbers; None when the prior did not run or the file holds
    no tag table (a hand edit, another tool's JSON): a bad tag file never breaks say, checks or finish. Read without the content
    checks' size cap, which is for check files, not recon's own small output."""
    try:
        data = json.loads((folder / "recon" / "prior" / "prior.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, RecursionError):
        return None
    scene = data.get("scene") if isinstance(data, dict) else None
    if not isinstance(scene, dict) or not scene:
        return None
    return {str(k): _num(v) for k, v in scene.items()}


def checks_for_scene(scene: dict | None) -> list[dict]:
    """Which checks the scene requires: mountains, or water without a city → skyline; a city or a road → street. Indoor → none."""
    if not scene or scene.get("indoor", 0) >= SCENE_THRESHOLD:
        return []
    out = []
    m, w, u, r = (scene.get(k, 0) for k in ("mountains", "water", "urban", "road"))
    if m >= SCENE_THRESHOLD or (w >= SCENE_THRESHOLD and u < 0.5):
        out.append({"name": "skyline", "why": f"mountains {m:.0%}, water {w:.0%}", "command": CHECKS["skyline"]["command"]})
    if u >= SCENE_THRESHOLD or r >= SCENE_THRESHOLD:
        out.append({"name": "street", "why": f"urban {u:.0%}, road {r:.0%}", "command": CHECKS["street"]["command"]})
    return out


def required_checks(folder: Path) -> list[dict]:
    """The scene's required checks with their status: done when the session holds a file of that check (check_hits)."""
    req = checks_for_scene(scene_tags(folder))
    if not req:
        return []
    hits = check_hits(folder, _artifact_paths(folder))
    for c in req:
        c["done"] = bool(hits[c["name"]])
        c["files"] = hits[c["name"]][:6]
    return req


def _num(value) -> float:
    """An inlier count or score as a number; None, missing or malformed → 0."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _latlon(wgs) -> tuple[float, float] | None:
    try:
        return float(wgs[0]), float(wgs[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None


def _near_fair(lat: float, lon: float, wgs, inliers, score) -> float | None:
    """Metres from the answer to a ranked view within NEAR_M that is at least a fair match (≥FAIR_INLIERS inliers or global
    score ≥FAIR_SCORE), else None: the one test behind the rank waiver and the heading hint."""
    at = _latlon(wgs)
    if at is None:
        return None
    d_m = haversine_m((lat, lon), at)
    return d_m if d_m <= NEAR_M and (_num(inliers) >= FAIR_INLIERS or _num(score) >= FAIR_SCORE) else None


def _top_rows(data) -> list[dict]:
    """The top views of a match.py rank file, known by its rows (rank and wgs) under any name: the rows match.py saved a view
    image for, else the first 10; [] for any other JSON."""
    rows = [r for r in data if isinstance(r, dict) and "rank" in r] if isinstance(data, list) else []
    return [r for r in ([r for r in rows if r.get("view")] or rows[:10]) if _latlon(r.get("wgs"))]


def _rank_top_views(folder: Path) -> list[tuple[str, dict]]:
    """(file, row) for the top views of every rank file among the session's check files: the one reader behind the waiver's
    shortfall message and the heading hints, over the same walk and size cap as the waiver itself."""
    return [(rel, r) for rel in _artifact_paths(folder) if rel.lower().endswith(".json") for r in _top_rows(_read_json(folder / rel))]


def _pose_output(data) -> bool:
    """pose.py output: solve's camera solution (camera_ll) or check's candidate table (robust_delta_chi2 per candidate);
    its input spec (image_size, points, init) is neither."""
    if not isinstance(data, dict) or not data:
        return False
    return _latlon(data.get("camera_ll")) is not None or all(isinstance(v, dict) and "robust_delta_chi2" in v for v in data.values())


def pinning_artifacts(folder: Path, answer: tuple[float, float] | None = None) -> list[str]:
    """Session files whose geometry pins the place: an evidence/match image (PINNING_MARK), a pose.py output (_pose_output), and,
    given the answer, a rank file whose top views include a near, fair one (_near_fair). Without an answer a rank file pins nothing."""
    pins = []
    for rel in _artifact_paths(folder):
        if "_views/" in rel:                     # match.py's saved views illustrate their rank file; alone they pin nothing
            continue
        if PINNING_MARK.search(rel.rsplit("/", 1)[-1]):
            pins.append(rel)
        elif rel.lower().endswith(".json"):
            data = _read_json(folder / rel)
            if _pose_output(data) or (answer and any(_near_fair(*answer, r["wgs"], r.get("inliers"), r.get("score_global")) is not None
                                                     for r in _top_rows(data))):
                pins.append(rel)
    return pins


def _fit_supports(data, answer: tuple[float, float]) -> bool:
    """A terrain.py fit output whose leading cluster puts the camera at the answer: the pin within one grid step (params.grid_m,
    else NEAR_M) of that cluster's near-tie stretch (tie.bbox), or of its best camera when nothing ties."""
    if not isinstance(data, dict) or "cams" not in data:
        return False
    lead = next((c for c in data.get("clusters") or [] if isinstance(c, dict) and isinstance(c.get("best"), dict)), None)
    if lead is None:
        return False
    tie = lead.get("tie") if isinstance(lead.get("tie"), dict) else {}
    cam = _latlon(lead["best"].get("cam"))
    try:
        s, w, n, e = (float(v) for v in (tie.get("bbox") or (cam + cam if cam else None)))
    except (TypeError, ValueError):
        return False
    params = data.get("params") if isinstance(data.get("params"), dict) else {}
    lat, lon = answer
    return haversine_m(answer, (min(max(lat, s), n), min(max(lon, w), e))) <= (_num(params.get("grid_m")) or NEAR_M)


def _sweep_supports(data, answer: tuple[float, float]) -> bool:
    """A sweep.py ranking whose first 10 rows hold a near, fair one (_near_fair on lat/lon, sim_full as the global score)."""
    rows = data[:10] if isinstance(data, list) else []
    return any(isinstance(r, dict) and "sim_full" in r and _near_fair(*answer, (r.get("lat"), r.get("lon")), None, r["sim_full"]) is not None
               for r in rows)


def supporting_artifacts(folder: Path, answer: tuple[float, float]) -> list[str]:
    """Session files that support the answer's location: the pins at the answer (pinning_artifacts; a pose.py solve only with its
    camera within NEAR_M), a sweep.py ranking with a near, fair top row (_sweep_supports) and a fit output whose near-tie stretch
    holds the pin (_fit_supports). A check that ran and placed nothing at the answer is executed, not support."""
    pins, out = set(pinning_artifacts(folder, answer)), []
    for rel in _artifact_paths(folder):
        data = _read_json(folder / rel) if rel.lower().endswith(".json") else None
        cam = _latlon(data.get("camera_ll")) if isinstance(data, dict) else None
        if (rel in pins and (cam is None or haversine_m(answer, cam) <= NEAR_M)) or _sweep_supports(data, answer) \
                or _fit_supports(data, answer):
            out.append(rel)
    return out


def _rank_shortfall(folder: Path, lat: float, lon: float, check: str) -> str:
    """Why the session's rank files did not waive a check (the strongest top view: which, how far, how good) and the exits; empty
    without rank files. Never the view's coordinates: a fair match far from the answer is a lead to look at, not an answer to paste."""
    views = _rank_top_views(folder)
    if not views:
        return ""
    rel, row = max(views, key=lambda v: (_num(v[1].get("inliers")), _num(v[1].get("score_global"))))
    inliers, score = _num(row.get("inliers")), _num(row.get("score_global"))
    head = (f"Rank files do not pin this answer: the strongest top view, {rel} #{row.get('rank')}, is "
            f"{haversine_m((lat, lon), _latlon(row['wgs'])):.0f} m away with {inliers:g} inliers and score {score:.2f}")
    skip = f"--skip-check {check}:\"<reason>\""
    if inliers >= FAIR_INLIERS or score >= FAIR_SCORE:
        view = f"open {(Path(rel).parent / str(row['view'])).as_posix()}" if row.get("view") else "open that view"
        return (head + f" (a waiver needs ≤{NEAR_M} m). Next: {view} beside the photo; only if it shows the same fixed structures as "
                f"the photo, answer there (its row's wgs in {rel}); otherwise run the check, or {skip}.")
    return (head + f": too weak to pin the place (a waiver needs ≥{FAIR_INLIERS} inliers or score ≥{FAIR_SCORE} within {NEAR_M} m). "
            f"Run the check, or {skip}.")


def _checks_with_waiver(folder: Path, answer: tuple[float, float] | None = None) -> list[dict]:
    """required_checks with finish's waiver, the one place it is decided: waived_by on each missing check while pinning_artifacts
    pins the place. answer: the position rank files are tested against; None → the finished result's position (before finish
    there is none, so a rank file pins nothing yet). A finished session also shows the skips finish recorded."""
    checks = required_checks(folder)
    if all(c["done"] for c in checks):
        return checks
    meta = _read_json(folder / "session.json")
    result = meta.get("result") if isinstance(meta, dict) else None
    result = result if isinstance(result, dict) else {}
    if answer is None:
        answer = _latlon((result.get("latitude"), result.get("longitude")))
    pinned = pinning_artifacts(folder, answer)
    recorded = result.get("checks") if isinstance(result.get("checks"), list) else []
    skipped = {c.get("name"): c.get("skipped") for c in recorded if isinstance(c, dict)}
    for c in checks:
        if c["done"]:
            continue
        if skipped.get(c["name"]):
            c["skipped"] = skipped[c["name"]]
        elif pinned:
            c["waived_by"] = pinned[:4]
    return checks


def _check_state(c: dict) -> str:
    """One required check in the status line; a missing one names its next command and the exit, so no step reads as a dead end."""
    if c["done"]:
        return f"{c['name']} done"
    if c.get("skipped"):
        return f"{c['name']} skipped: {c['skipped']}"
    if c.get("waived_by"):
        return f"{c['name']} waived by {c['waived_by'][0]}"
    return f"{c['name']} missing: run {c['command'].split(' (', 1)[0]}, or --skip-check {c['name']}:\"<reason>\""


def status_line(folder: Path) -> str:
    """The session in one line of values, printed after every `viewer.py say` and atop `checks`: minutes since start (to the
    finish once finished), the verification file count, each required check (_check_state). No gate: the gates stay in finish."""
    meta = _read_json(folder / "session.json")
    meta = meta if isinstance(meta, dict) else {}
    parts = []
    try:
        start = datetime.fromisoformat(meta["started_at"])
        end = datetime.fromisoformat(meta["completed_at"]) if meta.get("completed_at") else now()
        parts.append(f"+{max(0, int((end - start).total_seconds() // 60))} min")   # floored: never shows finish's clock passed early
    except (KeyError, TypeError, ValueError):                                          # no session.json, or a hand-edited time
        pass
    parts.append(f"verification files {count_verification_artifacts(folder)}")
    checks = _checks_with_waiver(folder)
    if checks:
        parts.append(" | ".join(_check_state(c) for c in checks))
    return " · ".join(parts)


def cmd_checks(args: argparse.Namespace) -> dict:
    folder = Path(args.folder)
    scene = scene_tags(folder)
    req = _checks_with_waiver(folder)
    print(status_line(folder))
    print("Scene: " + (", ".join(f"{k} {v:.0%}" for k, v in sorted(scene.items(), key=lambda kv: -kv[1])) if scene else "no tags (recon's prior did not run)"))
    if not req:
        print("Required checks: none from the scene (finish still needs one verification artifact).")
    for c in req:
        state, detail = (("DONE", f": {', '.join(c['files'])}") if c["done"] else ("SKIPPED", f": {c['skipped']}") if c.get("skipped")
                         else ("WAIVED", f": by {', '.join(c['waived_by'])}") if c.get("waived_by")
                         else ("MISSING", f" → {c['command']}, or --skip-check {c['name']}:\"<reason>\""))
        print(f"  {c['name']:<8} {state:<7} ({c['why']}){detail}")
    return {"scene": scene, "checks": req}


def now() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE)) if TIMEZONE else datetime.now().astimezone()


def slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    cleaned = re.sub(r"[^\w]+", "-", normalized, flags=re.UNICODE).replace("_", "-").strip("-")
    # Limit bytes, since filesystem component limits also apply to Unicode names.
    return cleaned.encode("utf-8")[:64].decode("utf-8", errors="ignore").rstrip("-") or "unnamed"


def save_json(path: Path, data: dict) -> None:
    pending = path.with_suffix(".json.tmp")
    pending.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pending.replace(path)


def describe(folder: Path, metadata: dict) -> dict:
    return {
        "folder": str(folder),
        "started_at": metadata["started_at"],
        "completed_at": metadata.get("completed_at"),
        "timezone": TZ_NAME,
        "report": str(folder / "report.md"),
        "original": str(folder / metadata["original"]["relative_path"]) if metadata.get("original") else None,
        "originals": [str(folder / r["relative_path"]) for r in metadata.get("originals", [])],
        "status": metadata["status"],
    }


def start(args: argparse.Namespace) -> dict:
    images = [p.expanduser().resolve(strict=True) for p in (args.image or [])]
    for image in images:
        if not image.is_file():
            raise ValueError(f"{image} is not a regular file.")
    if args.beside:
        if not images:
            raise ValueError("--beside needs --image: the session is created in the folder of the first photo.")
        root = images[0].parent                   # the work lands next to the photo, not in the shared archive
    else:
        root = args.root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    while True:
        started = now()
        timestamp = started.strftime("%Y-%m-%d_%H-%M-%S-%f%z")
        folder = root / timestamp
        try:
            folder.mkdir()
            break
        except FileExistsError:
            continue
    original_dir = folder / "original"
    original_dir.mkdir()
    metadata = {
        "schema_version": 1,
        "timestamp": timestamp,
        "started_at": started.isoformat(timespec="microseconds"),
        "timezone": TZ_NAME,
        "status": "pending",
        "folder": str(folder),
        "original": None,
    }
    if images:
        records = []
        for image in images:
            target = original_dir / image.name
            if target.exists():   # two sources sharing a file name
                target = original_dir / f"{target.stem}_{len(records) + 1}{target.suffix}"
            shutil.copy2(image, target)
            checksum = hashlib.sha256()
            with target.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    checksum.update(chunk)
            records.append({
                "source_path": str(image),
                "relative_path": target.relative_to(folder).as_posix(),  # portable across OS (report.md heading, session.json)
                "sha256": checksum.hexdigest(),
            })
        metadata["original"] = records[0]          # the reference photo every single-photo tool and the report refer to
        if len(records) > 1:
            metadata["originals"] = records
    else:
        (original_dir / "source.txt").write_text(
            "The original image bytes have not been saved. Record the attachment's source here; "
            "save the actual original when accessible.\n", encoding="utf-8"
        )
    save_json(folder / "session.json", metadata)
    name = ", ".join(r["relative_path"] for r in metadata.get("originals") or ([metadata["original"]] if metadata.get("original") else [])) or "original (not saved)"
    (folder / "report.md").write_text(REPORT_SKELETON.format(name=name), encoding="utf-8")
    init_board(folder, metadata)
    out = describe(folder, metadata)
    if args.viewer:
        out["viewer"] = metadata["viewer_url"] = launch_viewer(folder, args.viewer_port)
        save_json(folder / "session.json", metadata)        # viewer.py stop finds the port here
    return out


def init_board(folder: Path, metadata: dict) -> None:
    """board.json from the first minute: candidates, clues and evidence have one home even when board.py init is forgotten."""
    photo = (metadata.get("original") or {}).get("relative_path") or ""
    cmd = [UV, "run", "-q", str(Path(__file__).resolve().parent / "board.py"), "init", "--case", metadata["timestamp"],
           "--photo", photo or "original/source.txt"]
    try:
        subprocess.run(cmd, cwd=str(folder), check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"Warning: board.json not created ({exc}); run board.py init in the session folder.", file=sys.stderr)


VERIFICATION_MARK = re.compile(r"(^rank\.json$|_rank\.json$|^rank_.*\.json$|_rank_.*\.json$|_views/|^evidence|refsheet|sheet|^match|terrain|pose|^sun|sat_scan|intersect|\.index\.json$|viewer_marks|^fit[^/]*\.json$|_fit[^/]*\.json$|ridge[^/]*\.json$|_skyline\.json$|_overlay\.(png|jpe?g)$|^shade[^/]*\.(png|json)$)", re.I)


def count_verification_artifacts(folder: Path) -> int:
    """Files that only a check produces (rank, views, sheet, evidence, terrain, pose, marks by name; a fit output, a street-level
    ranking or a panorama sheet index by content): zero means the answer is untested. recon's first pass is not a check."""
    paths = _artifact_paths(folder)
    by_content = {rel for files in check_hits(folder, paths).values() for rel in files}
    return sum(1 for rel in paths if rel in by_content or VERIFICATION_MARK.search(rel.rsplit("/", 1)[-1]) or VERIFICATION_MARK.search(rel))


SESSION_RECORDS = {"session.json", "report.md", "board.json", "activity.log", "viewer_marks.json", "viewer.html"}   # bookkeeping, never evidence
GENERATED_LABEL = "generated image (no place)"                     # a generated outcome in list and the scoreboard


def outcome(record: dict | None) -> str:
    """'generated' or 'place' for a finished result or a truth record; a record without `outcome` is a place."""
    return "generated" if isinstance(record, dict) and record.get("outcome") == "generated" else "place"


def declared_generation(folder: Path) -> dict | None:
    """meta.py's provenance verdict (recon/meta/meta.json, provenance.generated) when the file declares generated content, else
    None. A composite* term (a real photo with AI edits) declares nothing."""
    data = _read_json(folder / "recon" / "meta" / "meta.json")
    digest = data.get("digest", data) if isinstance(data, dict) else None
    prov = digest.get("provenance") if isinstance(digest, dict) else None
    gen = prov.get("generated") if isinstance(prov, dict) else None
    return gen if isinstance(gen, dict) and gen.get("declared") is True else None


def detector(folder: Path) -> dict | None:
    """recon/aidet/aidet.json as model status: {p_ai, threshold, model, flagged} when the detector ran, {skipped} when it did not,
    None when absent or unreadable. Shown and recorded, never a gate: models rank, evidence decides."""
    data = _read_json(folder / "recon" / "aidet" / "aidet.json")
    if not isinstance(data, dict):
        return None
    if data.get("skipped"):
        return {"skipped": str(data["skipped"])}
    try:
        p_ai, threshold = float(data["p_ai"]), float(data["threshold"])
    except (KeyError, TypeError, ValueError):
        return None
    return {"p_ai": p_ai, "threshold": threshold, "model": data.get("model"), "flagged": p_ai >= threshold}


def _names(text: str, name: str) -> bool:
    """text names `name` as a whole token, case-insensitive: never inside a longer word, file name or term."""
    return re.search(r"(?<![\w.-])" + re.escape(name) + r"(?![\w-]|\.\w)", text, re.I) is not None


def _score_record(path: Path) -> bool:
    """An aidet.py record (a score or its skip), known by content wherever --out-dir put it."""
    data = _read_json(path) if path.suffix.lower() == ".json" else None
    return isinstance(data, dict) and data.get("tool") == "aidet.py"


def generated_basis(basis: str, folder: Path) -> str | None:
    """What BASIS rests on as evidence of generation, strongest first: 'operator' (OPERATOR_WORDS at the start), 'file' (a session
    file the agent saved, the AI-gallery page or the sheet confirming the duplicate, named by path or file name) or 'declared'
    (the term meta declares); None for anything else. recon's first pass, the originals, the session's records and aidet.py
    records are no such file: a detector score is never evidence."""
    basis = basis.strip()
    if not basis:
        return None
    if OPERATOR_WORDS.match(basis):
        return "operator"
    text = basis.replace("\\", "/")
    named = [rel for rel in _artifact_paths(folder) if rel not in SESSION_RECORDS and (_names(text, rel) or _names(text, rel.rsplit("/", 1)[-1]))]
    if any(not _score_record(folder / rel) for rel in named):
        return "file"
    declared = declared_generation(folder)
    return "declared" if declared and declared.get("term") and _names(basis, str(declared["term"])) else None


def generated_summary(pairs: list[tuple[dict, dict]]) -> dict:
    """Generated calls against the truth over (result, truth) pairs: called, confirmed, false stops (called, the truth is a real
    place) and missed generations (a place answered, the truth is generated)."""
    out = {"called": 0, "confirmed": 0, "false_stops": 0, "missed": 0}
    for result, real in pairs:
        said, truth_is = outcome(result), outcome(real)
        if said == "generated":
            out["called"] += 1
            out["confirmed" if truth_is == "generated" else "false_stops"] += 1
        elif truth_is == "generated":
            out["missed"] += 1
    return out


def _country_row(name: str) -> tuple[str, dict] | None:
    """(table key, row) of assets/data/countries.json for a country name, GeoNames name, ISO2 or ISO3 (case-insensitive); None when unknown."""
    table = json.loads((SKILL_DIR / "assets" / "data" / "countries.json").read_text(encoding="utf-8-sig"))
    key = name.strip().lower()
    for code, row in table.items():
        if code.startswith("_") or not isinstance(row, dict):
            continue
        if key in {str(v).lower() for v in (row.get("name"), row.get("geonames_name"), row.get("iso2"), row.get("iso3"), code) if v}:
            return code, row
    return None


def country_centre(name: str) -> tuple[float, float, float]:
    """Population-weighted centre of a country and a radius (m) covering its populated extent, from assets/data/countries.json."""
    hit = _country_row(name)
    if not hit:
        raise ValueError(f"Unknown country '{name}' for the coordinate fallback: give --latitude and --longitude.")
    row = hit[1]
    lat, lon = row["center"]
    radius = 100_000.0
    if row.get("bbox"):
        s, w, n, e = row["bbox"]
        dlat = (n - s) / 2 * 111_000
        dlon = (e - w) / 2 * 111_000 * max(math.cos(math.radians(lat)), 0.05)
        radius = max(radius, math.hypot(dlat, dlon))
    return float(lat), float(lon), round(radius)


def _free_port(preferred: int) -> int:
    """A port the viewer can bind: the requested one when free, else one the OS hands out (0 = random, the default)."""
    import socket
    for cand in (preferred, 0):
        try:
            with socket.socket() as s:
                s.bind(("127.0.0.1", cand))
                return s.getsockname()[1]
        except OSError:
            continue
    return preferred


def snapshot(folder: Path) -> Path | None:
    """viewer.html beside the photos: the live page as one offline file (viewer.export_html); never fatal."""
    try:
        import viewer  # local module, stdlib only
        return viewer.export_html(folder)
    except Exception as exc:  # noqa: BLE001  (a snapshot must never block finish or truth)
        print(f"Warning: viewer.html not written ({exc}); run viewer.py export <folder>.", file=sys.stderr)
        return None


def ranked_headings(folder: Path) -> list[str]:
    """Heading of each rank file's first top view that has one, as hints for --heading."""
    first: dict[str, dict] = {}
    for rel, r in _rank_top_views(folder):
        if r.get("heading") is not None:
            first.setdefault(rel, r)
    return [f"{_num(r['heading']):.0f}° ({rel})" for rel, r in first.items()]


def heading_hint(folder: Path, lat: float, lon: float) -> dict | None:
    """When no heading was given: among the top views the waiver reads (_rank_top_views), the best near, fair one with a heading."""
    best = None
    for rel, r in _rank_top_views(folder):
        d_m = _near_fair(lat, lon, r["wgs"], r.get("inliers"), r.get("score_global")) if r.get("heading") is not None else None
        if d_m is None:
            continue
        key = (_num(r.get("inliers")), _num(r.get("score_global")))
        if best is None or key > best[0]:
            best = (key, {"heading": round(_num(r["heading"]) % 360, 1), "source": rel, "inliers": r.get("inliers") or 0,
                          "score": round(key[1], 3), "distance_m": round(d_m)})
    return best[1] if best else None


def when_text(report: str) -> str | None:
    """The `## When` section of report.md as one line (the model's own dating), without the placeholder or finish's footer."""
    m = re.search(r"^## When[^\n]*\n(.*?)(?=^## |\Z)", report.split(FOOTER, 1)[0], re.M | re.S)
    if not m:
        return None
    body = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S)
    text = " ".join(body.split())
    return text[:300] or None


def launch_viewer(folder: Path, port: int) -> str:
    """Start viewer.py serve for this session as a detached process that opens the default browser; returns the URL."""
    port = _free_port(port)
    cmd = [UV, "run", str(Path(__file__).resolve().parent / "viewer.py"), "serve", str(folder), "--open", "--port", str(port)]
    kwargs: dict = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "cwd": str(folder.parent)}  # not inside the folder: finish renames it (Windows refuses while a cwd is inside)
    if os.name == "nt":
        # CREATE_NO_WINDOW, not DETACHED_PROCESS: a detached uv has no console, so the python it spawns opens a new
        # (black) console window, and closing that window kills the viewer. A hidden console is inherited silently.
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)
    return f"http://127.0.0.1:{port}/"


REPORT_SKELETON = """# Geolocation report: {name}

## Gut call (before tools)
<!-- fill: ranked countries with percentages and the cues behind each; region hunch; what would change your mind; Plan: A. B. C. the most selective fixed features, each → what it can leave → its route (no percentages) -->

## Evidence
<!-- fill: decisive clues with the files that show them, commands actually run, sources with links -->

## Answer
<!-- fill: country / region / city, coordinates (WGS84; GCJ-02 too in mainland China), confidence per level, radius and what it rests on -->

## When
<!-- fill: year or year range, season, date, time of day: each with the clue and the file it rests on; "not determinable" with the reason when it is -->

## Alternatives and how to separate them
<!-- fill if any -->

## Excluded candidates and unresolved clues
<!-- fill if any -->
"""
REQUIRED_SECTIONS = ("## Gut call (before tools)\n<!-- fill:", "## Answer\n<!-- fill:", "## When\n<!-- fill:")


def parse_taken(text: str) -> dict:
    """`2019` | `2019-06` | `2019-06-21` | `2019-06-21T14:30` | ranges `A..B` (each side any precision) -> {from, to, time}."""
    s = text.strip()
    time_part = None

    def bound(part: str, end: bool) -> date:
        nonlocal time_part
        m = re.fullmatch(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?(?:T(\d{2}:\d{2}))?", part.strip())
        if not m:
            raise ValueError(f"--taken {text!r}: use YYYY, YYYY-MM, YYYY-MM-DD, optionally THH:MM, or a range A..B")
        y, mo, d, t = m.groups()
        if t:
            time_part = t
        y_i = int(y)
        if d:
            return date(y_i, int(mo), int(d))
        if mo:
            return date(y_i, int(mo), calendar.monthrange(y_i, int(mo))[1] if end else 1)
        return date(y_i, 12, 31) if end else date(y_i, 1, 1)

    if ".." in s:
        a, b = s.split("..", 1)
        if not a.strip() and not b.strip():
            raise ValueError(f"--taken {text!r}: an open range needs one side (2015.. or ..2019)")
        frm = bound(a, False) if a.strip() else date(1900, 1, 1)
        to = bound(b, True) if b.strip() else date.today()
    else:
        frm, to = bound(s, False), bound(s, True)
    if to < frm:
        raise ValueError(f"--taken {text!r}: the range end is before its start")
    return {"text": s, "from": frm.isoformat(), "to": to.isoformat(), "time": time_part}


STORED_KEYS = ("country", "region", "city_or_nearest_locality", "latitude", "longitude", "radius_m", "confidence", "heading", "taken")   # echoed by finish


def finish(args: argparse.Namespace) -> dict:
    if args.generated is None:
        if (args.latitude is None) != (args.longitude is None):
            raise ValueError("Give both --latitude and --longitude, or neither (then the country centre is used, confidence low).")
        if not args.country.strip() or not args.city.strip():
            raise ValueError("Country and city/nearest locality must be nonempty.")
    folder = args.folder.expanduser().resolve(strict=True)
    metadata = json.loads((folder / "session.json").read_text(encoding="utf-8-sig"))
    report = (folder / "report.md").read_text(encoding="utf-8")
    if not report.strip():
        raise ValueError("Save a nonempty report.md before finalizing the session.")
    unfilled = [s.split("\n")[0].lstrip("# ") for s in REQUIRED_SECTIONS if s in report]
    if unfilled:
        raise ValueError(f"Fill these report.md sections before finalizing: {', '.join(unfilled)}.")
    # The timestamp is a single safe path component, never a caller-provided path.
    timestamp = metadata["timestamp"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-\d{6}[+-]\d{4}", timestamp):
        raise ValueError("Invalid timestamp in session.json.")
    if args.generated is not None:
        return _close(folder, metadata, report, timestamp, ["generated-image"], *_generated_result(args.generated, folder, metadata))
    radius = args.radius_m
    heading_arg = str(args.heading).strip() if args.heading is not None else ""
    if heading_arg.lower() in ("", "unknown", "none", "-"):
        heading = None
    else:
        try:
            heading = float(heading_arg)
        except ValueError as exc:
            raise ValueError("--heading takes degrees (0 = north, 90 = east) or the word unknown.") from exc
    if radius is not None and not (math.isfinite(radius) and radius > 0):
        raise ValueError("--radius-m must be a positive number of metres.")
    if heading is not None:
        if not math.isfinite(heading):
            raise ValueError("--heading must be a finite compass bearing in degrees.")
        heading = round(heading % 360, 1)
    country, region, city = args.country.strip(), args.region.strip(), args.city.strip()
    lat, lon, confidence, coordinate_source = args.latitude, args.longitude, args.confidence, "given"
    if lat is None:                                   # the only honest closing without coordinates: the country centre, wide, low
        lat, lon, floor_m = country_centre(country)
        radius = max(radius or 0.0, floor_m)
        confidence = "low"
        coordinate_source = "country centre: no coordinates were given, unverified"
        print(f"Warning: no coordinates given; pinned the centre of {country} ({lat:.4f}, {lon:.4f}) with a {radius / 1000:.0f} km radius, "
              f"confidence low. A road-snapped point inside the settled area would have been better.", file=sys.stderr)
    _check_coords(lat, lon)
    _declared_generation_gate(folder, metadata, (lat, lon))
    artifacts = count_verification_artifacts(folder)
    taken = None
    taken_arg = (args.taken or "").strip()
    when_line = when_text(report)
    if taken_arg and taken_arg.lower() not in ("unknown", "none", "-"):
        taken = {**parse_taken(taken_arg), "confidence": args.taken_confidence or "low", "basis": (args.taken_basis or "").strip() or None}
    else:
        dated = when_line or ""
        try:                                            # a poster that reads "NOVEMBRE 2025" is a clue on the board, not only a line in the report
            clues = json.loads((folder / "board.json").read_text(encoding="utf-8-sig")).get("clues", {})
            dated += " " + " ".join(str(c.get("text", "")) for c in clues.values())
        except (OSError, ValueError):
            pass
        years = sorted(set(re.findall(r"\b(19\d\d|20\d\d)\b", dated)))
        print("Note: --taken unknown" + (f", yet the report or the board's clues name {', '.join(years)}: if one dates or bounds this photo (a dated sign "
              f"in it, a change against dated imagery, an earliest copy), encode it (`--taken {years[0]}..` from {years[0]} on, `--taken {years[0]}` "
              f"that year, `--taken {years[0]}-MM` a month, `..{years[-1]}` before); the date of a reference image, page or file alone is not the "
              "photo's date" if years else ": the answer still says why the date could not be determined")
              + ".", file=sys.stderr)
    hint = None
    if heading is None:
        hint = heading_hint(folder, lat, lon)
        hints = ranked_headings(folder)
        print("Warning: --heading unknown, so the map draws no firm view cone"
              + (f"; the best ranked view {hint['distance_m']} m from the answer looks at {hint['heading']:.0f}° ({hint['inliers']} inliers, {hint['source']}): pass --heading {hint['heading']:.0f} if that view is the shot" if hint
                 else (f"; the top ranked views look at {', '.join(hints[:3])}" if hints else ""))
              + ". A landmark identified in the frame (`geo.py frame --at <answer lat,lon> --anchor <name>:<lat,lon>:px=<its pixel column> --width "
              "<photo width> --hfov 45:70` prints the heading at each field of view), a Street View frame that shows the scene, the road bearing "
              "when the photo looks along the road, or sun.py compass give the heading.", file=sys.stderr)
    # the scene's required checks: a mountain or lake photo closes only with a skyline file, a street photo with a panorama/match file
    try:
        elapsed_min = (now() - datetime.fromisoformat(metadata["started_at"])).total_seconds() / 60
    except (KeyError, ValueError, TypeError):
        elapsed_min = UNVERIFIED_CLOCK_MIN
    skips = {}
    for s in args.skip_check or []:
        name, _, why = s.partition(":")
        skips[name.strip()] = why.strip()
    checks = _checks_with_waiver(folder, (lat, lon))
    for c in checks:
        if c["done"]:
            continue
        why = skips.get(c["name"])
        if not why and c.get("waived_by"):                         # strong data is a shortcut: the place is pinned by another geometry
            print(f"Note: required check '{c['name']}' not run; waived because the place is pinned by {', '.join(c['waived_by'][:3])}. "
                  f"Say in the answer that the {c['name']} check was not done.", file=sys.stderr)
            continue
        if not why:
            shortfall = _rank_shortfall(folder, lat, lon, c["name"])
            raise ValueError(
                f"Required check '{c['name']}' not done ({c['why']}, recon's scene tags). Next: run {c['command']}; it leaves a file this "
                f"check recognises. To close without it: --skip-check {c['name']}:\"<reason>\" ({EARLY_EXIT})."
                + (f"\n{shortfall}" if shortfall else ""))
        c.pop("waived_by", None)                                   # an explicit skip closes it, recorded with its reason
        if elapsed_min < UNVERIFIED_CLOCK_MIN and not OPERATOR_WORDS.match(why):
            raise ValueError(
                f"--skip-check {c['name']} before {UNVERIFIED_CLOCK_MIN} min is only for an analysis the operator stopped or redirected: "
                f"{OPERATOR_FORM}; '{why[:60]}' is not that. Next: run {c['command']}; from minute "
                f"{UNVERIFIED_CLOCK_MIN} (now {elapsed_min:.0f}) any stated reason closes it.")
        c["skipped"] = why
        print(f"Warning: required check '{c['name']}' skipped ({why}): the answer must say the {c['name']} check was not done.", file=sys.stderr)
    supporting = len(supporting_artifacts(folder, (lat, lon)))
    reason = (args.accept_unverified or "").strip()
    accepted_unverified = None
    if artifacts == 0:
        if reason and elapsed_min < UNVERIFIED_CLOCK_MIN and not OPERATOR_WORDS.match(reason):
            raise ValueError(
                f"--accept-unverified before {UNVERIFIED_CLOCK_MIN} min is only for an analysis the operator stopped or redirected: "
                f"{OPERATOR_FORM}. '{reason[:60]}' is not that: elapsed Quick time alone is never a reason to close unverified. "
                f"Next: go Deep with your plan's next line or the scene's required check (SKILL.md step 1, step 6) and finish when it "
                f"leaves a file; from minute {UNVERIFIED_CLOCK_MIN} (now {elapsed_min:.0f}) any stated reason closes it.")
        if not reason and elapsed_min < UNVERIFIED_CLOCK_MIN:
            raise ValueError(
                f"No verification artifact after {elapsed_min:.0f} min: this is not an answer yet. Next: run your plan's line A or B, "
                f"or a step 6 check (SKILL.md step 6: mountains, or a lake/coast with a skyline → osm.py geom + terrain.py scan/ridge/fit; "
                f"a road, railway or power line → osm.py + terrain.py scan; a facility → osm.py find + sat_scan.py; a street → gsv.py "
                f"sheet + match.py rank; a venue → evidence.py --match against a reference photo; look-alike countries → refsheet.py), "
                f"or go Deep. Close without one: --accept-unverified \"<reason>\" ({EARLY_EXIT}).")
        accepted_unverified = reason or f"clock: {elapsed_min:.0f} min without a verification artifact"
        print(f"Warning: no verification artifact ({accepted_unverified}): the answer is an unverified estimate and must say so.", file=sys.stderr)
    elif reason:                                                   # the agent's own verdict on its checks: never dropped, never refused
        accepted_unverified = reason
        print(f"Note: --accept-unverified recorded ({reason}) beside {artifacts} verification files: the answer is an unverified "
              f"estimate and must say so.", file=sys.stderr)
    elif supporting == 0:
        print("Warning: no check supports this location: the answer is an unverified estimate. Next: record the match that places it, "
              "evidence.py match.json --out match.jpg --match against the sheet cell or sweep view that shows the place (or terrain.py fit "
              f"--at {lat:.5f},{lon:.5f} --ridge <ridge.json> for a skyline); otherwise say so in the answer, or --accept-unverified "
              "\"<reason>\".", file=sys.stderr)
    result = {
        "outcome": "place",
        "country": country,
        "region": region or None,
        "city_or_nearest_locality": city,
        "latitude": lat,
        "longitude": lon,
        "coordinate_system": "WGS84",
        "coordinate_source": coordinate_source,
        "radius_m": radius,
        "heading": heading,
        "confidence": confidence,
        "verification_artifacts": artifacts,
        "supporting_artifacts": supporting,
        "accepted_unverified": accepted_unverified,
        "checks": [{k: c.get(k) for k in ("name", "why", "done", "files", "skipped", "waived_by")} for c in checks],
        "taken": taken,
        "when_text": when_line,
        "heading_hint": hint,
    }
    lines = (
        f"Result: {lat:.6f}, {lon:.6f} (WGS84{'' if coordinate_source == 'given' else ', ' + coordinate_source})"
        + (f"; radius {radius:g} m" if radius is not None else "") + (f"; heading {heading:g}°" if heading is not None else "")
        + f"; confidence {confidence}; verification artifacts {artifacts} ({supporting} supporting the location)  \n"
        + (f"Taken: {taken['text']}" + (f" {taken['time']}" if taken.get("time") else "") + f" ({taken['confidence']}"
           + (f"; {taken['basis']}" if taken.get("basis") else "") + ")  \n" if taken else f"Taken: not given{' (report: ' + when_line + ')' if when_line else ''}  \n")
        + (f"Heading: unknown; the best ranked view nearby looks at {hint['heading']:.0f}° ({hint['source']}, suggested, not asserted)  \n" if hint else "")
    )
    closed = _close(folder, metadata, report, timestamp, [slug(value) for value in (country, region, city) if value], result, lines)
    print("Stored result: " + ", ".join(f"{k}={json.dumps(taken['text'] if k == 'taken' and taken else result[k], ensure_ascii=False)}"
                                        for k in STORED_KEYS), file=sys.stderr)
    return closed


def _declared_generation_gate(folder: Path, metadata: dict, answer: tuple[float, float]) -> None:
    """A place answer for a file that declares generated content: refused only while nothing pins a real place and the operator
    has not said it is real (not-generated); with either, a note. A detector score never enters here."""
    declared = declared_generation(folder)
    if not declared:
        return
    term = declared.get("term") or "generated content"
    what = f"recon/meta declares generated content ({term})"
    override = metadata.get("generated_override")
    if isinstance(override, dict) and override.get("reason"):
        print(f"Note: {what}; the operator said it is real ({override['reason']}): say both in the answer.", file=sys.stderr)
        return
    pins = pinning_artifacts(folder, answer)
    if pins:
        print(f"Note: {what}, but the place is pinned by {', '.join(pins[:3])}: a real place found outranks a declaration; say both in "
              f"the answer.", file=sys.stderr)
        return
    raise ValueError(
        f"{what} and nothing in the session pins a real place. Exits: the operator says it is real → photo_session.py not-generated "
        f"\"{folder}\" \"operator asked: it is real\", then finish again; the declaration stands → photo_session.py finish \"{folder}\" "
        f"--generated \"{term}\"; or pin the place (an evidence.py or match image, a pose.py solution, or a near fair ranked view at this "
        f"answer): a real place found outranks a declaration.")


def _generated_result(basis: str, folder: Path, metadata: dict) -> tuple[dict, str]:
    """finish --generated: the result and its footer line. BASIS must be evidence (generated_basis); the detector's score is
    recorded beside it, never decides it. The operator's earlier "it is real" and a pinned place (pinning_artifacts, a ranked view
    tested against the finished answer as the status line does) each outrank the declared term alone: then only new operator words
    or a saved file close as generated."""
    basis = basis.strip()
    kind = generated_basis(basis, folder)
    if not kind:
        declared = declared_generation(folder)
        raise ValueError(
            "--generated needs evidence of generation, never a score: the term meta declares ("
            + (f"here: {declared['term']}" if declared and declared.get("term") else "none declared in recon/meta/meta.md")
            + "), a session file you saved that shows it (the AI-gallery page with its prompt, model or 'Generated with AI' label, or "
            "the contact sheet confirming the duplicate by fixed features; name its path), or the operator's words (\"operator asked: …\"). "
            f"'{basis[:80]}' is none of these. Next: keep geolocating (a detector score ranks, it never decides), or save that evidence "
            "and name the file.")
    override = metadata.get("generated_override")
    if kind == "declared" and isinstance(override, dict) and override.get("reason"):
        raise ValueError(
            f"The operator said it is real ({override['reason']}): that outranks the declared term. Exits: the operator now says it is "
            f"generated → photo_session.py finish \"{folder}\" --generated \"operator asked: …\"; a saved file that shows the generation "
            "(the AI-gallery page with its prompt or model, the sheet confirming the duplicate) → --generated naming that file; otherwise "
            "finish with the place (--country, --city, --latitude/--longitude…), which the declaration no longer refuses.")
    if kind == "declared":
        prev = metadata.get("result") if isinstance(metadata.get("result"), dict) else {}
        pins = pinning_artifacts(folder, _latlon((prev.get("latitude"), prev.get("longitude"))))
        if pins:
            raise ValueError(
                f"The place is pinned by {', '.join(pins[:3])}: a real place found outranks the declared term. Exits: finish with the place "
                f"it pins (--country, --city, --latitude/--longitude…), which the declaration does not refuse; the operator says it is "
                f"generated → photo_session.py finish \"{folder}\" --generated \"operator asked: …\"; a saved file that shows the generation "
                "(the AI-gallery page with its prompt or model, the sheet confirming the duplicate) → --generated naming that file.")
    score = detector(folder) or {}
    result = {"outcome": "generated", "latitude": None, "longitude": None,
              "generated": {"basis": basis, "score": score.get("p_ai"), "model": score.get("model"), "skipped": score.get("skipped"),
                            "override": override}}
    line = (f"Result: generated image, no real place; basis: {basis}  \n"
            + (f"Detector: {score['p_ai']:.2f} ({score.get('model') or 'model'}), a ranking, not the basis  \n" if score.get("p_ai") is not None
               else f"Detector: skipped ({score['skipped']})  \n" if score.get("skipped") else "Detector: not run  \n")
            + (f"Operator had said real: {override.get('reason')}  \n" if isinstance(override, dict) else ""))
    return result, line


def _close(folder: Path, metadata: dict, report: str, timestamp: str, names: list[str], result: dict, lines: str) -> dict:
    """Rename <timestamp> to <timestamp>__<names>, record the result, append the report footer (lines: the result's own) and
    write the offline page."""
    destination = folder.parent / (timestamp + "__" + "__".join(names))
    if destination != folder and destination.exists():
        raise ValueError("The final archive already exists; no existing session was changed.")
    # finish again on a closed session is the correction path: the first close time stays, the replaced answer goes to result_history,
    # a recorded truth is rescored against the new answer (here, before the rename: a malformed truth record changes nothing)
    prior = metadata.get("result") if metadata.get("status") == "completed" else None
    real = current_truth(folder, metadata) if prior and isinstance(metadata.get("truth"), dict) else None
    body = report.split(FOOTER, 1)[0].rstrip()
    try:
        rescored = score_truth(result, real, body) if real else None
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"session.json's truth record cannot be scored ({type(exc).__name__}: {exc}): record it again with photo_session.py "
                         f"truth \"{folder}\" --latitude … --longitude … [--country …] (or --generated for a generated image), then finish "
                         "again") from exc
    if destination != folder:
        cwd = Path.cwd()
        if cwd == folder or folder in cwd.parents:
            os.chdir(folder.parent)               # Windows refuses to rename a folder that is this process's cwd
        _rename(folder, destination)
    stamp = now().isoformat(timespec="microseconds")
    metadata.update({"status": "completed", "completed_at": metadata.get("completed_at") if prior and metadata.get("completed_at") else stamp,
                     "folder": str(destination), "result": result})
    body = body.replace(str(folder), str(destination))
    if prior:
        replaced = {"replaced_at": stamp, "result": prior}
        if rescored is not None:      # truth metrics always describe the current answer: the replaced one keeps its own
            replaced["truth_metrics"] = {k: real[k] for k in TRUTH_METRICS if k in real}
            metadata["truth"] = {**{k: v for k, v in real.items() if k not in TRUTH_METRICS}, **rescored}
            body = _with_truth_block(body, truth_block(result, metadata["truth"])).rstrip()
        metadata.setdefault("result_history", []).append(replaced)
    footer = (
        f"\n\n{FOOTER}\n\n"
        f"Analysis started: {metadata['started_at']} ({TZ_NAME})  \n"
        f"Analysis completed: {metadata['completed_at']}  \n"
        + (f"Amended: {stamp} (previous result kept in session.json result_history)  \n" if prior else "")
        + lines
        + f"Archive: [{destination.name}](<{destination}>)\n"
    )
    (destination / "report.md").write_text(body + footer, encoding="utf-8")
    save_json(destination / "session.json", metadata)
    snapshot(destination)
    return describe(destination, metadata)


def _rename(src: Path, dst: Path, attempts: int = 5) -> None:
    """Windows refuses to rename a folder while any file in it is open (WinError 5/32: an image viewer, an editor, a terminal's
    cwd, an indexer). Such holds are usually short: retry with a 1-2 s back-off, then fail naming the folder."""
    for i in range(attempts):
        try:
            src.rename(dst)
            return
        except PermissionError as exc:
            if i == attempts - 1:
                raise OSError(f"Could not rename {src} to {dst.name} after {attempts} attempts: another process holds a file in that "
                              f"folder open ({exc.strerror or exc}). Close it (image viewer, editor, terminal in that folder) and run finish again.") from exc
            time.sleep(1.0 + 0.25 * i)


GUT_LINE = re.compile(r"^\s*(?:\d+[.)]\s*|[-*]\s+)?(?P<country>.+?)\s*[:,]?\s+(?P<p>\d+(?:\.\d+)?)\s*%")
GUT_END = re.compile(r"^\s*(?:[-*]\s+)?[*_]*\s*(?:region hunch|would change|plan)\b", re.I)   # ranked rows end at the first labelled line


def gut_call(report: str) -> list[tuple[str, float]]:
    """(country, percent) rows of the '## Gut call (before tools)' section ('1. Portugal 55% — cues'), in the order written."""
    m = re.search(r"^## Gut call \(before tools\)[^\n]*\n(.*?)(?=^## |\Z)", report, re.M | re.S)
    rows = []
    for line in (m.group(1) if m else "").splitlines():
        if GUT_END.match(line):                     # region hunch, would-change, plan lines may carry percentages: never countries
            break
        g = GUT_LINE.match(line)
        if g:
            rows.append((g.group("country").strip(" *_`"), float(g.group("p"))))
    return rows


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return haversine_m((lat1, lon1), (lat2, lon2)) / 1000


def _same(a: str | None, b: str | None) -> bool | None:
    if not a or not b:
        return None
    return slug(a) == slug(b)


def country_iso2(name: str) -> str | None:
    """ISO2 for a country name, alias, ISO2 or ISO3 (assets/data/countries.json); None when unknown."""
    try:
        hit = _country_row(name)
    except (OSError, ValueError):
        return None
    return (hit[1].get("iso2") or hit[0]) if hit else None


def _same_country(a: str | None, b: str | None) -> bool | None:
    """Country names, aliases and codes compared as ISO2 ('Italy', 'IT', 'ITA' are one country); slug equality as fallback."""
    if not a or not b:
        return None
    ca, cb = country_iso2(a), country_iso2(b)
    if ca and cb:
        return ca == cb
    return slug(a) == slug(b)


def _check_coords(lat: float, lon: float) -> None:
    if not math.isfinite(lat) or not -90 <= lat <= 90:
        raise ValueError("Latitude must be a finite number from -90 to 90.")
    if not math.isfinite(lon) or not -180 <= lon <= 180:
        raise ValueError("Longitude must be a finite number from -180 to 180.")


TRUTH_METRICS = ("error_km", "game_score_estimate", "outcome_hit", "false_stop", "country_hit", "region_hit", "gut_country_hit",
                 "gut_p_truth", "taken_hit", "taken_error_days", "taken_span_days")   # a truth record's score of the current answer


def score_truth(result: dict, real: dict, report: str) -> dict:
    """The TRUTH_METRICS of a finished result against a truth record's ground-truth fields (outcome, latitude, longitude, country,
    region, taken): the one scoring code behind truth and a re-finish of a scored session. report: report.md, for the gut call."""
    said, truth_is = outcome(result), outcome(real)
    # a distance exists only between two places: a generated answer or a generated truth has none
    distance = haversine_km(result["latitude"], result["longitude"], real["latitude"], real["longitude"]) if said == truth_is == "place" else None
    country = real.get("country")
    gut = gut_call(report)
    gut_p = next((p for c, p in gut if _same_country(c, country)), None) if country and gut else None
    metrics = {
        "error_km": round(distance, 3) if distance is not None else None,
        "game_score_estimate": int(round(5000 * math.exp(-distance / SCORE_SCALE_KM))) if distance is not None else None,
        "outcome_hit": said == truth_is,
        "false_stop": said == "generated" and truth_is == "place",      # the run stopped on a real photo; the reverse is a missed generation
        "country_hit": _same_country(result.get("country"), country),
        "region_hit": _same(result.get("region"), real.get("region")),
        # gut call (written before tools) vs truth: None when the report has no gut rows or no truth country was given
        "gut_country_hit": (gut_p is not None) if (country and gut) else None,
        "gut_p_truth": (gut_p if gut_p is not None else 0.0) if (country and gut) else None,
    }
    if real.get("taken"):
        truth_taken, answered = parse_taken(real["taken"]), result.get("taken")
        if answered:
            lo, hi = date.fromisoformat(answered["from"]), date.fromisoformat(answered["to"])
            t_lo, t_hi = date.fromisoformat(truth_taken["from"]), date.fromisoformat(truth_taken["to"])
            inside = t_hi >= lo and t_lo <= hi
            gap = 0 if inside else min(abs((t_lo - hi).days), abs((lo - t_hi).days))
            metrics.update(taken_hit=inside, taken_error_days=gap, taken_span_days=(hi - lo).days + 1)
        else:
            metrics.update(taken_hit=None, taken_error_days=None)
    return metrics


def current_truth(folder: Path, metadata: dict) -> dict | None:
    """session.json's truth record with TRUTH_METRICS that score the current result. A session re-finished after its truth by a
    version that did not rescore still holds the replaced answer's metrics (the last result_history entry, replaced after the truth
    was recorded, has no truth_metrics): those are rescored here; a record that cannot be scored loses them rather than show them."""
    real, result, history = metadata.get("truth"), metadata.get("result"), metadata.get("result_history") or []
    last = history[-1] if history and isinstance(history[-1], dict) else None
    if not (isinstance(real, dict) and isinstance(result, dict) and last) or "truth_metrics" in last:
        return real
    try:
        if datetime.fromisoformat(real["recorded_at"]) > datetime.fromisoformat(last["replaced_at"]):
            return real
    except (KeyError, TypeError, ValueError):
        pass                                          # no comparable times: a rescore is right either way
    ground = {k: v for k, v in real.items() if k not in TRUTH_METRICS}
    report = folder / "report.md"
    try:
        return {**ground, **score_truth(result, real, report.read_text(encoding="utf-8") if report.exists() else "")}
    except (KeyError, TypeError, ValueError):
        return ground


def truth_block(result: dict, record: dict) -> str:
    """report.md's '## Ground truth' block: the truth record and its score of result, the current answer."""
    said, real = outcome(result), outcome(record)
    hit = lambda v: "unknown" if v is None else ("yes" if v else "no")  # noqa: E731
    parts = ([f"Error: {record['error_km']:.2f} km; approximate world-map game score {record['game_score_estimate']}"]
             if record.get("error_km") is not None else [])
    if "generated" in (said, real):
        parts.append("outcome: " + ("generated image confirmed" if said == real else "false stop: answered a generated image, the photo shows a real place"
                                    if said == "generated" else "missed generation: answered a place, the image is generated"))
    if real == "place":
        parts.append(f"country hit: {hit(record['country_hit'])}; region hit: {hit(record['region_hit'])}")
    if record.get("taken"):
        parts.append(f"taken: {record['taken']} → {'inside the answered range' if record.get('taken_hit') else ('no range answered' if record.get('taken_hit') is None else str(record.get('taken_error_days')) + ' days off')}")
    if real == "place":
        parts.append(f"gut call: {hit(record['gut_country_hit'])}" + (f" ({record['gut_p_truth']:g}% on the true country)" if record["gut_p_truth"] is not None else ""))
    if said == "place":
        parts.append(f"stated confidence: {result.get('confidence')}")
    names = [x for x in (record.get("city"), record.get("region"), record.get("country")) if x]
    where = ("Actual: generated image, no real place" if real == "generated" else f"Actual location: {record['latitude']:.6f}, {record['longitude']:.6f}"
             + (f" ({', '.join(names)})" if names else ""))
    return (f"\n\n{TRUTH_START}\n\n## Ground truth\n\n" + where + (f"; source: {record['source']}" if record.get("source") else "") + "  \n"
            + "; ".join(parts) + f".\n\n{TRUTH_END}\n")


def _with_truth_block(report: str, block: str) -> str:
    """report.md with its ground-truth block replaced by block, kept above finish's footer."""
    if TRUTH_START in report:
        before, rest = report.split(TRUTH_START, 1)
        report = before.rstrip() + rest.split(TRUTH_END, 1)[-1]
    if FOOTER in report:
        body, footer = report.split(FOOTER, 1)
        return body.rstrip() + block + "\n" + FOOTER + footer
    return report.rstrip() + block


def truth(args: argparse.Namespace) -> dict:
    real = "generated" if args.generated else "place"
    if real == "place":
        _check_coords(args.latitude, args.longitude)
    folder = args.folder.expanduser().resolve(strict=True)
    metadata = json.loads((folder / "session.json").read_text(encoding="utf-8-sig"))
    result = metadata.get("result")
    if not result:
        raise ValueError("Finish the session first (photo_session.py finish), then record the truth.")
    report_path = folder / "report.md"
    report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    record = {
        "outcome": real,
        "latitude": args.latitude, "longitude": args.longitude,
        "country": args.country or None, "region": args.region or None, "city": args.city or None,
        "source": args.source or None, "recorded_at": now().isoformat(timespec="microseconds"),
    }
    if args.taken:
        record["taken"] = parse_taken(args.taken)["text"]
    record.update(score_truth(result, record, report))
    metadata["truth"] = record
    save_json(folder / "session.json", metadata)
    report_path.write_text(_with_truth_block(report, truth_block(result, record)), encoding="utf-8")
    snapshot(folder)                                   # viewer.html now shows the truth too
    return {**describe(folder, metadata), "truth": record}


def _sessions(root: Path) -> list[tuple[Path, dict]]:
    out = []
    if not root.exists():
        return out
    for d in sorted(root.iterdir()):
        f = d / "session.json"
        if d.is_dir() and f.exists():
            try:
                out.append((d, json.loads(f.read_text(encoding="utf-8-sig"))))
            except (OSError, json.JSONDecodeError):
                continue
    return out


def _pct(v: float | None) -> str:
    return "–" if v is None else f"{v:.0%}"


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    v = sorted(values)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def scoreboard(args: argparse.Namespace) -> dict:
    root = args.root.expanduser().resolve()
    rows, pairs = [], []
    for folder, m in _sessions(root):
        t, r = current_truth(folder, m), m.get("result")
        if t and r:
            pairs.append((r, t))
            rows.append({"folder": folder.name, "started_at": m.get("started_at"), "chosen": r.get("city_or_nearest_locality"),
                         "country": r.get("country"), "outcome": outcome(r), "truth_outcome": outcome(t), "confidence": r.get("confidence"),
                         "error_km": t.get("error_km"), "score": t.get("game_score_estimate"), "country_hit": t.get("country_hit"),
                         "taken_hit": t.get("taken_hit"), "gut_country_hit": t.get("gut_country_hit"), "gut_p_truth": t.get("gut_p_truth")})
    measured = [x for x in rows if x["error_km"] is not None]          # a generated answer or truth has no distance
    errors = [x["error_km"] for x in measured]
    summary = {"root": str(root), "scored_sessions": len(rows),
               "median_error_km": _median(errors),
               "mean_game_score": round(sum(x["score"] or 0 for x in measured) / len(measured)) if measured else None,
               "within_km": {str(k): round(sum(e <= k for e in errors) / len(errors), 3) if errors else None for k in THRESHOLDS_KM},
               "country_hit_rate": (round(sum(1 for x in rows if x["country_hit"]) / len([x for x in rows if x["country_hit"] is not None]), 3)
                                    if any(x["country_hit"] is not None for x in rows) else None),
               "taken_hit_rate": (round(sum(1 for x in rows if x.get("taken_hit")) / len([x for x in rows if x.get("taken_hit") is not None]), 3)
                                  if any(x.get("taken_hit") is not None for x in rows) else None),
               "gut_country_hit_rate": (round(sum(1 for x in rows if x["gut_country_hit"]) / len([x for x in rows if x["gut_country_hit"] is not None]), 3)
                                        if any(x["gut_country_hit"] is not None for x in rows) else None),
               "generated": generated_summary(pairs)}
    calib = {}
    for tier in ("high", "medium", "low"):
        e = [x["error_km"] for x in measured if x["confidence"] == tier]
        calib[tier] = {"n": len(e), "median_error_km": _median(e),
                       "within_25km": round(sum(v <= 25 for v in e) / len(e), 3) if e else None,
                       "within_200km": round(sum(v <= 200 for v in e) / len(e), 3) if e else None}
    summary["by_confidence"] = calib
    summary["sessions"] = rows
    if args.write:
        lines = ["# Geo-intelligence scoreboard", "", f"Scored sessions: {len(rows)}. Median error: "
                 f"{summary['median_error_km'] if summary['median_error_km'] is not None else '–'} km. "
                 f"Mean approximate game score: {summary['mean_game_score'] if summary['mean_game_score'] is not None else '–'}.", "",
                 "| Within | " + " | ".join(f"{k} km" for k in THRESHOLDS_KM) + " |", "|---|" + "---|" * len(THRESHOLDS_KM),
                 "| share | " + " | ".join(_pct(summary["within_km"][str(k)]) for k in THRESHOLDS_KM) + " |"]
        g = summary["generated"]
        if g["called"] or g["missed"]:
            lines += ["", f"Generated image calls: {g['called']} (confirmed {g['confirmed']}, false stops {g['false_stops']}); "
                          f"missed generations: {g['missed']}. Distance figures leave these sessions out."]
        lines += ["", "## Calibration", "", "| Stated confidence | n | median error km | within 25 km | within 200 km |", "|---|---|---|---|---|"]
        for tier, c in calib.items():
            med = "–" if c["median_error_km"] is None else f"{c['median_error_km']:.1f}"
            lines.append(f"| {tier} | {c['n']} | {med} | {_pct(c['within_25km'])} | {_pct(c['within_200km'])} |")
        lines += ["", "## Sessions", "", "| Session | Chosen | Confidence | Error km | Score | Gut % on truth |", "|---|---|---|---|---|---|"]
        for x in sorted(rows, key=lambda x: x["started_at"] or ""):
            gut = "–" if x["gut_p_truth"] is None else f"{x['gut_p_truth']:g}"
            chosen = GENERATED_LABEL if x["outcome"] == "generated" else f"{x['chosen']}, {x['country']}"
            error = "–" if x["error_km"] is None else f"{x['error_km']:.1f}"
            lines.append(f"| {x['folder']} | {chosen} | {x['confidence'] or '–'} | {error} | {x['score'] if x['score'] is not None else '–'} | {gut} |")
        (root / "scoreboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        save_json(root / "scoreboard.json", summary)
        summary["written"] = str(root / "scoreboard.md")
    return summary


def list_sessions(args: argparse.Namespace) -> dict:
    root = args.root.expanduser().resolve()
    rows = []
    for folder, m in _sessions(root):
        if args.status and m.get("status") != args.status:
            continue
        r, t = m.get("result") or {}, current_truth(folder, m) or {}
        rows.append({"folder": str(folder), "status": m.get("status"), "started_at": m.get("started_at"),
                     "result": (GENERATED_LABEL if outcome(r) == "generated" else f"{r.get('city_or_nearest_locality')}, {r.get('country')} ({r.get('confidence')})")
                     if r else None,
                     "error_km": t.get("error_km")})
    return {"root": str(root), "count": len(rows), "sessions": rows}


def not_generated(args: argparse.Namespace) -> dict:
    """The operator's "it is real, continue", kept in session.json (outside recon/, so a recon rerun never erases it)."""
    reason = args.reason.strip()
    if not OPERATOR_WORDS.match(reason):
        raise ValueError(f"not-generated records the operator's word only: {OPERATOR_FORM} ('{reason[:60]}' is not that). "
                         "Next: without the operator's word keep geolocating; a detector score never stops the analysis, and a declared "
                         "generation yields to a pinned place (evidence or match image, pose.py solution) or closes with finish --generated.")
    folder = args.folder.expanduser().resolve(strict=True)
    metadata = json.loads((folder / "session.json").read_text(encoding="utf-8-sig"))
    metadata["generated_override"] = {"reason": reason, "at": now().isoformat(timespec="seconds")}
    save_json(folder / "session.json", metadata)
    return {**describe(folder, metadata), "generated_override": metadata["generated_override"]}


FINISH_PLACE = ("country", "region", "city", "latitude", "longitude", "confidence", "radius_m", "heading", "taken", "taken_confidence", "taken_basis")


def _given(args: argparse.Namespace, names: tuple[str, ...]) -> list[str]:
    return [f"--{n.replace('_', '-')}" for n in names if getattr(args, n) not in (None, "")]


def _finish_usage(args: argparse.Namespace) -> str | None:
    """finish's flag rules argparse cannot state: the place flags are required without --generated and never mix with it."""
    if args.generated is not None:
        mixed = _given(args, FINISH_PLACE + ("skip_check", "accept_unverified"))
        return f"--generated closes with no real place: drop {', '.join(mixed)}; to answer a place, drop --generated instead" if mixed else None
    missing = [f"--{n}" for n in ("country", "city", "confidence", "heading", "taken") if getattr(args, n) is None]
    return ("the following arguments are required: " + ", ".join(missing) + " (or --generated BASIS for a generated image with no real place)"
            if missing else None)


def _truth_usage(args: argparse.Namespace) -> str | None:
    """truth takes a place (--latitude and --longitude) or --generated, never both."""
    if args.generated:
        mixed = _given(args, ("latitude", "longitude", "country", "region", "city", "taken"))
        return f"--generated is the truth for an image with no real place: drop {', '.join(mixed)}; for a place truth, drop --generated instead" if mixed else None
    missing = [f"--{n}" for n in ("latitude", "longitude") if getattr(args, n) is None]
    return ("the following arguments are required: " + ", ".join(missing) + " (or --generated when the image shows no real place)"
            if missing else None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("start", help="Create a new archive and copy the original image.")
    create.add_argument("--image", type=Path, action="append", default=[], help="Source image to copy unchanged; repeat it for several photos of the same scene.")
    create.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Archive root (default: GEOINT_PHOTOS, config.local.json, or ~/geoint-photos).")
    create.add_argument("--beside", action="store_true", help="Create the session folder next to the first --image instead of under --root (scoreboard then needs --root <that folder>).")
    create.add_argument("--viewer", action="store_true", help="Also start viewer.py serve for this session and open it in the browser.")
    create.add_argument("--viewer-port", type=int, default=0, help="Port for --viewer on 127.0.0.1 (default: a random free one; the URL is printed and stored in session.json).")
    create.set_defaults(handler=start)
    complete = subparsers.add_parser("finish", help="Append the location to a session with a saved report, or close a generated image (--generated).")
    complete.add_argument("folder", type=Path)
    complete.add_argument("--country", help="Required unless --generated.")
    complete.add_argument("--region", default="")
    complete.add_argument("--city", help="City or nearest named locality; required unless --generated.")
    complete.add_argument("--latitude", type=float, help="WGS84; omit both coordinates only when nothing below country level is supported (then: country centre, wide radius, confidence low).")
    complete.add_argument("--longitude", type=float)
    complete.add_argument("--confidence", choices=("high", "medium", "low"), help="Required unless --generated.")
    complete.add_argument("--radius-m", type=float, help="Error radius of the answer in metres (what the stated precision rests on).")
    complete.add_argument("--heading", help="Camera heading in degrees (0 = north, 90 = east), or the word unknown: say which; required unless --generated.")
    complete.add_argument("--taken", help="When the photo was taken: YYYY, YYYY-MM, YYYY-MM-DD[THH:MM], a range A..B (e.g. 2019-06..2019-09), or the word unknown: say which; required unless --generated.")
    complete.add_argument("--taken-confidence", choices=("high", "medium", "low"), help="Confidence of --taken (default low).")
    complete.add_argument("--taken-basis", help="What --taken rests on, one line (metadata, dated imagery bracket, sun, event…).")
    complete.add_argument("--skip-check", action="append", metavar="NAME:REASON", help=f"Close although a scene-required check (skyline, street) has no file; repeatable, recorded in the result. Allowed {EARLY_EXIT}.")
    complete.add_argument("--accept-unverified", metavar="REASON", help=f"The answer is an unverified estimate; the reason is recorded (result.accepted_unverified). With no verification artifact it is the only close, allowed {EARLY_EXIT}.")
    complete.add_argument("--generated", metavar="BASIS", help="Close as a generated image with no real place, without any place flag. BASIS is evidence, never a detector score: "
                          "the DigitalSourceType term meta declares (not while a file pins a real place), a saved session file that shows it (the AI-gallery page, "
                          "the sheet confirming the duplicate), "
                          "or the operator's words starting the basis (\"operator asked: …\").")
    complete.set_defaults(handler=finish)
    not_gen = subparsers.add_parser("not-generated", help="Record the operator's \"it is real, continue\" (session.json generated_override): a declared generation then never refuses a place finish.")
    not_gen.add_argument("folder", type=Path)
    not_gen.add_argument("reason", help="The operator's words, starting \"operator asked:\", e.g. \"operator asked: it is real, continue\".")
    not_gen.set_defaults(handler=not_generated)
    chk = subparsers.add_parser("checks", help="Print the status line, then the scene's required checks (from recon's scene tags): done, waived by a pinning file, or missing with the command that does it.")
    chk.add_argument("folder", type=Path)
    chk.set_defaults(handler=cmd_checks)

    scored = subparsers.add_parser("truth", help="Record the real location of a finished session (or --generated) and score it.")
    scored.add_argument("folder", type=Path)
    scored.add_argument("--latitude", type=float, help="Required unless --generated.")
    scored.add_argument("--longitude", type=float, help="Required unless --generated.")
    scored.add_argument("--generated", action="store_true", help="The image is generated and shows no real place (no coordinates).")
    scored.add_argument("--country", default="")
    scored.add_argument("--region", default="")
    scored.add_argument("--city", default="")
    scored.add_argument("--source", default="", help="Where the truth comes from (owner, puzzle answer, game reveal…).")
    scored.add_argument("--taken", help="True capture date/time: YYYY-MM-DD[THH:MM] (or a coarser YYYY / YYYY-MM when that is all that is known).")
    scored.set_defaults(handler=truth)
    board = subparsers.add_parser("scoreboard", help="Accuracy and calibration over all scored sessions.")
    board.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    board.add_argument("--write", action="store_true", help="Also write scoreboard.md and scoreboard.json in the root.")
    board.set_defaults(handler=scoreboard)
    listing = subparsers.add_parser("list", help="List sessions (resume pending ones).")
    listing.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    listing.add_argument("--status", choices=("pending", "completed"))
    listing.set_defaults(handler=list_sessions)
    args = parser.parse_args()
    usage = {"finish": (complete, _finish_usage), "truth": (scored, _truth_usage)}.get(args.command)
    problem = usage[1](args) if usage else None
    if problem:
        usage[0].error(problem)                   # exit 2 with the usage line, as argparse's own required-argument check
    try:
        output = args.handler(args)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")   # non-ASCII place names on Windows consoles and pipes
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
