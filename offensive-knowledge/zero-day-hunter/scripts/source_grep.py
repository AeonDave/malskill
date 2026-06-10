#!/usr/bin/env python3
"""Lightweight code-search helper for zero-day review.

Uses ripgrep when available and falls back to a Python file walker.
Outputs concise, analyst-friendly matches.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_GLOBS = [
    "*.c", "*.h", "*.cc", "*.cpp", "*.cxx", "*.hpp", "*.hxx",
    "*.go", "*.rs", "*.py", "*.java", "*.js", "*.ts", "*.php", "*.cs",
]


def iter_candidate_files(root: Path) -> list[Path]:
    suffixes = {
        ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hxx",
        ".go", ".rs", ".py", ".java", ".js", ".ts", ".php", ".cs",
    }
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in suffixes:
            continue
        files.append(path)
    return files


def run_rg(root: Path, pattern: str, literal: bool, limit: int) -> str:
    rg_path = shutil.which("rg")
    if not rg_path:
        return ""

    cmd = [rg_path, "--no-heading", "-n", "-S"]
    if literal:
        cmd.append("--fixed-strings")
    for item in DEFAULT_GLOBS:
        cmd.extend(["-g", item])
    cmd.append(pattern)

    try:
        proc = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return ""

    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return "\n".join(lines[:limit])


def run_python_fallback(root: Path, pattern: str, literal: bool, limit: int) -> str:
    matcher = None if literal else re.compile(pattern, re.IGNORECASE)
    rows: list[str] = []

    for file_path in iter_candidate_files(root):
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            haystack = line if literal else line
            matched = pattern in haystack if literal else bool(matcher.search(haystack))
            if not matched:
                continue
            rel = file_path.relative_to(root)
            rows.append(f"{rel}:{line_no}:{line}")
            if len(rows) >= limit:
                return "\n".join(rows)

    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search source files for review evidence.")
    parser.add_argument("root", help="Repository or source root")
    parser.add_argument("pattern", help="Literal text or regex to search")
    parser.add_argument("--regex", action="store_true", help="Treat pattern as a regex")
    parser.add_argument("--limit", type=int, default=30, help="Maximum number of lines to print")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"Failure: root directory not found: {root}", file=sys.stderr)
        return 1

    literal = not args.regex
    output = run_rg(root, args.pattern, literal, args.limit)
    if not output:
        output = run_python_fallback(root, args.pattern, literal, args.limit)

    if not output:
        print("No matches found.")
        return 0

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
