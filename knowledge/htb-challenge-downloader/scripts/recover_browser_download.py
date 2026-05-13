#!/usr/bin/env python3
"""# requires: standard-library only

Recover a recent Chromium-family browser download and copy it into an output directory.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recover a recent Chromium-family download into an output directory."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the recovered file should be copied.",
    )
    parser.add_argument(
        "--match",
        help="Case-insensitive substring matched against filename, source URL, or tab URL.",
    )
    parser.add_argument(
        "--history-db",
        help="Override the Chromium History database path.",
    )
    parser.add_argument(
        "--since-minutes",
        type=int,
        default=120,
        help="Only consider downloads newer than this many minutes.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Maximum number of recent download records to inspect.",
    )
    return parser.parse_args()


def _history_candidates() -> list[Path]:
    home = Path.home()
    return [
        home / "snap/chromium/common/chromium/Default/History",
        home / ".config/chromium/Default/History",
        home / ".config/google-chrome/Default/History",
        home / ".config/BraveSoftware/Brave-Browser/Default/History",
    ]


def _resolve_history_db(override: str | None) -> Path:
    if override:
        path = Path(override).expanduser()
        if path.is_file():
            return path
        raise FileNotFoundError(f"History DB not found: {path}")

    for candidate in _history_candidates():
        if candidate.is_file():
            return candidate

    raise FileNotFoundError("No Chromium-family History DB found")


def _copy_history_db(history_db: Path) -> Path:
    with tempfile.NamedTemporaryFile(prefix="browser-history-", suffix=".db", delete=False) as handle:
        temp_path = Path(handle.name)
    shutil.copy2(history_db, temp_path)
    return temp_path


def _query_records(history_copy: Path, limit: int) -> list[tuple[int, str, str, str, str]]:
    conn = sqlite3.connect(history_copy)
    try:
        cur = conn.cursor()
        rows = list(
            cur.execute(
                """
                SELECT
                    d.start_time,
                    COALESCE(d.target_path, ''),
                    COALESCE(d.current_path, ''),
                    COALESCE(d.tab_url, ''),
                    COALESCE(u.url, '')
                FROM downloads AS d
                LEFT JOIN downloads_url_chains AS u
                    ON u.id = d.id AND u.chain_index = 0
                ORDER BY d.start_time DESC
                LIMIT ?
                """,
                (limit,),
            )
        )
    finally:
        conn.close()
    return rows


def _chromium_time_to_unix(raw_value: int) -> float:
    return raw_value / 1_000_000 - 11_644_473_600


def _record_matches(row: tuple[int, str, str, str, str], needle: str | None, cutoff: float) -> bool:
    started_raw, target_path, current_path, tab_url, source_url = row
    if _chromium_time_to_unix(started_raw) < cutoff:
        return False
    if not needle:
        return True
    haystack = "\n".join([target_path, current_path, tab_url, source_url]).lower()
    return needle in haystack


def _candidate_paths(row: tuple[int, str, str, str, str]) -> list[Path]:
    _, target_path, current_path, _, _ = row
    candidates: list[Path] = []

    for raw_path in (target_path, current_path):
        if raw_path:
            candidates.append(Path(raw_path).expanduser())

    basenames = {path.name for path in candidates if path.name}
    fallback_dirs = [
        Path.home() / "Downloads",
        Path.home() / ".local/share/Trash/files",
    ]
    for basename in basenames:
        for directory in fallback_dirs:
            candidates.append(directory / basename)

    deduped: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            deduped.append(path)
    return deduped


def _copy_first_existing(row: tuple[int, str, str, str, str], output_dir: Path) -> tuple[Path, Path] | None:
    for candidate in _candidate_paths(row):
        if candidate.is_file():
            destination = output_dir / candidate.name
            shutil.copy2(candidate, destination)
            return candidate, destination
    return None


def main() -> int:
    args = _parse_args()
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        history_db = _resolve_history_db(args.history_db)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    history_copy = _copy_history_db(history_db)
    try:
        rows = _query_records(history_copy, args.limit)
    finally:
        history_copy.unlink(missing_ok=True)

    cutoff = time.time() - args.since_minutes * 60
    needle = args.match.lower() if args.match else None

    matching_rows = [row for row in rows if _record_matches(row, needle, cutoff)]
    for row in matching_rows:
        copied = _copy_first_existing(row, output_dir)
        if copied is not None:
            source_path, destination_path = copied
            _, target_path, current_path, tab_url, source_url = row
            print(f"RECOVERED {destination_path}")
            print(f"SOURCE_FILE {source_path}")
            print(f"TARGET_PATH {target_path}")
            print(f"CURRENT_PATH {current_path}")
            print(f"TAB_URL {tab_url}")
            print(f"SOURCE_URL {source_url}")
            return 0

    print("ERROR: No matching download file could be recovered", file=sys.stderr)
    for row in matching_rows[:5]:
        _, target_path, current_path, tab_url, source_url = row
        print(
            "SEEN " + " | ".join([target_path or "-", current_path or "-", tab_url or "-", source_url or "-"]),
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())