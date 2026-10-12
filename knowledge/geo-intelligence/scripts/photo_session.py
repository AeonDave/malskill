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
  finish    append the chosen country/region/city to the folder name, record the result
  truth     record the real location later (from the photo's owner, a puzzle answer, a game reveal)
            and score the session: error in km, approximate world-map game score, country/region hit
  scoreboard  accuracy over every scored session: median error, hit rates at 1/25/200/750/2500 km,
            and whether "high/medium/low" confidence actually meant what it claimed
  list      sessions with their status, so an interrupted one can be resumed
"""

from __future__ import annotations

import argparse
from datetime import datetime
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
from geolib.paths import SKILL_DIR, local_config as _local_config  # noqa: E402,F401

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
    if getattr(args, "beside", False):
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
    if getattr(args, "viewer", False):
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


VERIFICATION_MARK = re.compile(r"(^rank\.json$|_rank\.json$|^rank_.*\.json$|_rank_.*\.json$|_views/|^evidence|refsheet|sheet|^match|terrain|pose|^sun|sat_scan|intersect|\.index\.json$|viewer_marks)", re.I)


def count_verification_artifacts(folder: Path) -> int:
    """Files that only a check produces (rank, views, sheet, evidence, terrain, pose, marks): zero means the answer is
    untested. recon's own output (detect sheets, reverse-search sheets) is the first pass, not a check."""
    n = 0
    for p in folder.rglob("*"):
        rel = p.relative_to(folder).as_posix()
        if rel.startswith((".geo-cache/", "original/", "recon")) or not p.is_file():
            continue
        if VERIFICATION_MARK.search(p.name) or VERIFICATION_MARK.search(rel):
            n += 1
    return n


def country_centre(name: str) -> tuple[float, float, float]:
    """Population-weighted centre of a country and a radius (m) covering its populated extent, from assets/data/countries.json."""
    table = json.loads((SKILL_DIR / "assets" / "data" / "countries.json").read_text(encoding="utf-8-sig"))
    key = name.strip().lower()
    for code, row in table.items():
        if code.startswith("_") or not isinstance(row, dict):
            continue
        if key in {str(v).lower() for v in (row.get("name"), row.get("geonames_name"), row.get("iso2"), row.get("iso3"), code) if v}:
            lat, lon = row["center"]
            radius = 100_000.0
            if row.get("bbox"):
                s, w, n, e = row["bbox"]
                dlat = (n - s) / 2 * 111_000
                dlon = (e - w) / 2 * 111_000 * max(math.cos(math.radians(lat)), 0.05)
                radius = max(radius, math.hypot(dlat, dlon))
            return float(lat), float(lon), round(radius)
    raise ValueError(f"Unknown country '{name}' for the coordinate fallback: give --latitude and --longitude.")


def _free_port(preferred: int) -> int:
    """The preferred port when free, else one the OS hands out: parallel sessions must not fight over 8765."""
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
    """Headings of the top ranked views (match.py rank files), as hints for --heading."""
    out = []
    for f in sorted(folder.glob("*rank*.json")):
        if f.name.endswith(".index.json"):
            continue
        try:
            rows = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(rows, list) and rows and isinstance(rows[0], dict) and rows[0].get("heading") is not None:
            out.append(f"{rows[0]['heading']:.0f}° ({f.name})")
    return out


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
<!-- fill: ranked shortlist with percentages and the cues behind each; region hunch; what would change your mind -->

## Evidence
<!-- fill: decisive clues with the files that show them, commands actually run, sources with links -->

## Answer
<!-- fill: country / region / city, coordinates (WGS84; GCJ-02 too in mainland China), confidence per level, radius and what it rests on -->

## Alternatives and how to separate them
<!-- fill if any -->

## Excluded candidates and unresolved clues
<!-- fill if any -->
"""
REQUIRED_SECTIONS = ("## Gut call (before tools)\n<!-- fill:", "## Answer\n<!-- fill:")


def finish(args: argparse.Namespace) -> dict:
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
    radius, heading = args.radius_m, args.heading
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
    if not math.isfinite(lat) or not -90 <= lat <= 90:
        raise ValueError("Latitude must be a finite number from -90 to 90.")
    if not math.isfinite(lon) or not -180 <= lon <= 180:
        raise ValueError("Longitude must be a finite number from -180 to 180.")
    artifacts = count_verification_artifacts(folder)
    if heading is None:
        hints = ranked_headings(folder)
        print("Warning: no --heading, so the map draws no view cone" + (f"; the top ranked views look at {', '.join(hints[:3])}" if hints else "")
              + ". If you know where the camera looked (matched panorama, road bearing when the photo looks along the road, sun), pass --heading.", file=sys.stderr)
    if artifacts == 0:
        print("Warning: this session holds no verification artifact (no rank, sheet, evidence, terrain, pose or mark file): "
              "the answer is an unverified estimate and must say so.", file=sys.stderr)
    names = [slug(value) for value in (country, region, city) if value]
    destination = folder.parent / (timestamp + "__" + "__".join(names))
    if destination != folder and destination.exists():
        raise ValueError("The final archive already exists; no existing session was changed.")
    if destination != folder:
        cwd = Path.cwd()
        if cwd == folder or folder in cwd.parents:
            os.chdir(folder.parent)               # Windows refuses to rename a folder that is this process's cwd
        _rename(folder, destination)
    metadata.update({
        "status": "completed",
        "completed_at": now().isoformat(timespec="microseconds"),
        "folder": str(destination),
        "result": {
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
        },
    })
    body = report.split(FOOTER, 1)[0].rstrip().replace(str(folder), str(destination))
    footer = (
        f"\n\n{FOOTER}\n\n"
        f"Analysis started: {metadata['started_at']} ({TZ_NAME})  \n"
        f"Analysis completed: {metadata['completed_at']}  \n"
        f"Result: {lat:.6f}, {lon:.6f} (WGS84{'' if coordinate_source == 'given' else ', ' + coordinate_source})"
        + (f"; radius {radius:g} m" if radius is not None else "") + (f"; heading {heading:g}°" if heading is not None else "")
        + f"; confidence {confidence}; verification artifacts {artifacts}  \n"
        f"Archive: [{destination.name}](<{destination}>)\n"
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


def gut_call(report: str) -> list[tuple[str, float]]:
    """(country, percent) rows of the '## Gut call (before tools)' section ('1. Portugal 55% — cues'), in the order written."""
    m = re.search(r"^## Gut call \(before tools\)[^\n]*\n(.*?)(?=^## |\Z)", report, re.M | re.S)
    rows = []
    for line in (m.group(1) if m else "").splitlines():
        g = GUT_LINE.match(line)
        if g:
            rows.append((g.group("country").strip(" *_`"), float(g.group("p"))))
    return rows


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from geolib.geomath import haversine_m
    return haversine_m((lat1, lon1), (lat2, lon2)) / 1000


def _same(a: str | None, b: str | None) -> bool | None:
    if not a or not b:
        return None
    return slug(a) == slug(b)


def country_iso2(name: str) -> str | None:
    """ISO2 for a country name, alias, ISO2 or ISO3 (assets/data/countries.json); None when unknown."""
    try:
        table = json.loads((SKILL_DIR / "assets" / "data" / "countries.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    key = name.strip().lower()
    for code, row in table.items():
        if code.startswith("_") or not isinstance(row, dict):
            continue
        if key in {str(v).lower() for v in (row.get("name"), row.get("geonames_name"), row.get("iso2"), row.get("iso3"), code) if v}:
            return row.get("iso2") or code
    return None


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


def truth(args: argparse.Namespace) -> dict:
    _check_coords(args.latitude, args.longitude)
    folder = args.folder.expanduser().resolve(strict=True)
    metadata = json.loads((folder / "session.json").read_text(encoding="utf-8-sig"))
    result = metadata.get("result")
    if not result:
        raise ValueError("Finish the session first (photo_session.py finish), then record the truth.")
    distance = haversine_km(result["latitude"], result["longitude"], args.latitude, args.longitude)
    report_path = folder / "report.md"
    report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    gut = gut_call(report)
    gut_p = next((p for c, p in gut if _same_country(c, args.country)), None) if args.country and gut else None
    record = {
        "latitude": args.latitude, "longitude": args.longitude,
        "country": args.country or None, "region": args.region or None, "city": args.city or None,
        "source": args.source or None, "recorded_at": now().isoformat(timespec="microseconds"),
        "error_km": round(distance, 3),
        "game_score_estimate": int(round(5000 * math.exp(-distance / SCORE_SCALE_KM))),
        "country_hit": _same_country(result.get("country"), args.country),
        "region_hit": _same(result.get("region"), args.region),
        # gut call (written before tools) vs truth: None when the report has no gut rows or no truth country was given
        "gut_country_hit": (gut_p is not None) if (args.country and gut) else None,
        "gut_p_truth": (gut_p if gut_p is not None else 0.0) if (args.country and gut) else None,
    }
    metadata["truth"] = record
    save_json(folder / "session.json", metadata)
    if TRUTH_START in report:
        before, rest = report.split(TRUTH_START, 1)
        report = before.rstrip() + rest.split(TRUTH_END, 1)[-1]
    hit = lambda v: "unknown" if v is None else ("yes" if v else "no")  # noqa: E731
    block = (
        f"\n\n{TRUTH_START}\n\n## Ground truth\n\n"
        f"Actual location: {args.latitude:.6f}, {args.longitude:.6f}"
        + (f" ({', '.join(x for x in (args.city, args.region, args.country) if x)})" if (args.city or args.region or args.country) else "")
        + (f"; source: {args.source}" if args.source else "") + "  \n"
        f"Error: {distance:.2f} km; approximate world-map game score {record['game_score_estimate']}; "
        f"country hit: {hit(record['country_hit'])}; region hit: {hit(record['region_hit'])}; "
        f"gut call: {hit(record['gut_country_hit'])}"
        + (f" ({record['gut_p_truth']:g}% on the true country)" if record["gut_p_truth"] is not None else "")
        + f"; stated confidence: {result.get('confidence')}.\n\n{TRUTH_END}\n"
    )
    if FOOTER in report:
        body, footer = report.split(FOOTER, 1)
        report = body.rstrip() + block + "\n" + FOOTER + footer
    else:
        report = report.rstrip() + block
    report_path.write_text(report, encoding="utf-8")
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
    rows = []
    for folder, m in _sessions(root):
        t, r = m.get("truth"), m.get("result")
        if t and r:
            rows.append({"folder": folder.name, "started_at": m.get("started_at"), "chosen": r.get("city_or_nearest_locality"),
                         "country": r.get("country"), "confidence": r.get("confidence"), "error_km": t["error_km"],
                         "score": t.get("game_score_estimate"), "country_hit": t.get("country_hit"),
                         "gut_country_hit": t.get("gut_country_hit"), "gut_p_truth": t.get("gut_p_truth")})
    errors = [x["error_km"] for x in rows]
    summary = {"root": str(root), "scored_sessions": len(rows),
               "median_error_km": _median(errors),
               "mean_game_score": round(sum(x["score"] or 0 for x in rows) / len(rows)) if rows else None,
               "within_km": {str(k): round(sum(e <= k for e in errors) / len(errors), 3) if errors else None for k in THRESHOLDS_KM},
               "country_hit_rate": (round(sum(1 for x in rows if x["country_hit"]) / len([x for x in rows if x["country_hit"] is not None]), 3)
                                    if any(x["country_hit"] is not None for x in rows) else None),
               "gut_country_hit_rate": (round(sum(1 for x in rows if x["gut_country_hit"]) / len([x for x in rows if x["gut_country_hit"] is not None]), 3)
                                        if any(x["gut_country_hit"] is not None for x in rows) else None)}
    calib = {}
    for tier in ("high", "medium", "low"):
        e = [x["error_km"] for x in rows if x["confidence"] == tier]
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
                 "| share | " + " | ".join(_pct(summary["within_km"][str(k)]) for k in THRESHOLDS_KM) + " |",
                 "", "## Calibration", "", "| Stated confidence | n | median error km | within 25 km | within 200 km |", "|---|---|---|---|---|"]
        for tier, c in calib.items():
            med = "–" if c["median_error_km"] is None else f"{c['median_error_km']:.1f}"
            lines.append(f"| {tier} | {c['n']} | {med} | {_pct(c['within_25km'])} | {_pct(c['within_200km'])} |")
        lines += ["", "## Sessions", "", "| Session | Chosen | Confidence | Error km | Score | Gut % on truth |", "|---|---|---|---|---|---|"]
        for x in sorted(rows, key=lambda x: x["started_at"] or ""):
            gut = "–" if x["gut_p_truth"] is None else f"{x['gut_p_truth']:g}"
            lines.append(f"| {x['folder']} | {x['chosen']}, {x['country']} | {x['confidence']} | {x['error_km']:.1f} | {x['score']} | {gut} |")
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
        r, t = m.get("result") or {}, m.get("truth") or {}
        rows.append({"folder": str(folder), "status": m.get("status"), "started_at": m.get("started_at"),
                     "result": f"{r.get('city_or_nearest_locality')}, {r.get('country')} ({r.get('confidence')})" if r else None,
                     "error_km": t.get("error_km")})
    return {"root": str(root), "count": len(rows), "sessions": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("start", help="Create a new archive and copy the original image.")
    create.add_argument("--image", type=Path, action="append", default=[], help="Source image to copy unchanged; repeat it for several photos of the same scene.")
    create.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Archive root (default: GEOINT_PHOTOS, config.local.json, or ~/geoint-photos).")
    create.add_argument("--beside", action="store_true", help="Create the session folder next to the first --image instead of under --root (scoreboard then needs --root <that folder>).")
    create.add_argument("--viewer", action="store_true", help="Also start viewer.py serve for this session and open it in the browser.")
    create.add_argument("--viewer-port", type=int, default=8765, help="Port for --viewer on 127.0.0.1 (default 8765).")
    create.set_defaults(handler=start)
    complete = subparsers.add_parser("finish", help="Append the location to a session with a saved report.")
    complete.add_argument("folder", type=Path)
    complete.add_argument("--country", required=True)
    complete.add_argument("--region", default="")
    complete.add_argument("--city", required=True, help="City or nearest named locality.")
    complete.add_argument("--latitude", type=float, help="WGS84; omit both coordinates only when nothing below country level is supported (then: country centre, wide radius, confidence low).")
    complete.add_argument("--longitude", type=float)
    complete.add_argument("--confidence", required=True, choices=("high", "medium", "low"))
    complete.add_argument("--radius-m", type=float, help="Error radius of the answer in metres (what the stated precision rests on).")
    complete.add_argument("--heading", type=float, help="Camera heading in degrees (0 = north, 90 = east).")
    complete.set_defaults(handler=finish)
    scored = subparsers.add_parser("truth", help="Record the real location of a finished session and score it.")
    scored.add_argument("folder", type=Path)
    scored.add_argument("--latitude", required=True, type=float)
    scored.add_argument("--longitude", required=True, type=float)
    scored.add_argument("--country", default="")
    scored.add_argument("--region", default="")
    scored.add_argument("--city", default="")
    scored.add_argument("--source", default="", help="Where the truth comes from (owner, puzzle answer, game reveal…).")
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
