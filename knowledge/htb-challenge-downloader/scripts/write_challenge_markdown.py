#!/usr/bin/env python3
"""# requires: standard-library only

Write a deterministic HTB challenge markdown file from JSON metadata.
Read JSON from --input or stdin and write markdown to --output.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write readme.md from HTB challenge metadata JSON."
    )
    parser.add_argument(
        "--input",
        help="Path to a JSON metadata file. If omitted, JSON is read from stdin.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output markdown file.",
    )
    return parser.parse_args()


def _load_metadata(input_path: str | None) -> dict[str, Any]:
    if input_path:
        raw = Path(input_path).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        raise ValueError("No JSON input provided")

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Top-level JSON value must be an object")

    return data


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_downloads(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [_string(item) for item in value if _string(item)]
    text = _string(value)
    return [text] if text else []


def _normalize_spawn(value: Any) -> str:
    if value is None:
        return "not attempted"
    if isinstance(value, dict):
        status = _string(value.get("status")) or "unknown"
        details = _string(value.get("details"))
        return f"{status} ({details})" if details else status
    return _string(value) or "not attempted"


def _normalize_string_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [_string(item) for item in value if _string(item)]
    text = _string(value)
    return [text] if text else []


def _render_markdown(data: dict[str, Any]) -> str:
    name = _string(data.get("title")) or _string(data.get("name")) or "Unnamed Challenge"
    category = _string(data.get("category")) or _string(data.get("family")) or "unknown"
    description = _string(data.get("description")) or "No description captured."
    source_url = _string(data.get("source_url"))
    challenge_url = _string(data.get("challenge_url"))
    points = _string(data.get("points"))
    notes = _string(data.get("notes"))
    retrieved_at = _string(data.get("retrieved_at")) or datetime.now(
        timezone.utc
    ).isoformat()
    downloads = _normalize_downloads(data.get("downloads"))
    ip_ports = _normalize_string_list(data.get("ip_ports") or data.get("endpoints"))
    spawn_status = _normalize_spawn(data.get("spawn"))

    lines = [f"# {name}", ""]
    lines.append(f"- Category: {category}")
    if points:
        lines.append(f"- Points: {points}")
    if source_url:
        lines.append(f"- Source URL: {source_url}")
    if challenge_url:
        lines.append(f"- Challenge URL: {challenge_url}")
    lines.append(f"- Retrieved At: {retrieved_at}")
    lines.append(f"- Spawn Status: {spawn_status}")
    lines.append(f"- Downloads: {json.dumps(downloads)}")
    lines.append(f"- IP:Ports: {json.dumps(ip_ports)}")

    lines.extend(["", "## Description", "", description, ""])

    if notes:
        lines.extend(["## Notes", "", notes, ""])

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = _parse_args()

    try:
        data = _load_metadata(args.input)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_render_markdown(data), encoding="utf-8")
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"WROTE {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())