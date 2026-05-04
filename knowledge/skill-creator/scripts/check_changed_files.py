#!/usr/bin/env python3
"""Safe changed-file hygiene checks for AgentSkills repositories.

Checks changed text files for a final newline and delegates tracked whitespace
checks to `git diff --check` without passing a large path list through the shell.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
from collections.abc import Iterable


def git_z(args: list[str]) -> list[str]:
    output = subprocess.check_output(args)
    return [os.fsdecode(item) for item in output.split(b"\0") if item]


def changed_paths(include_untracked: bool) -> list[str]:
    paths = git_z(["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", "-z"])
    if include_untracked:
        paths.extend(git_z(["git", "ls-files", "--others", "--exclude-standard", "-z"]))
    return list(dict.fromkeys(paths))


def is_probably_binary(path: pathlib.Path, sample_size: int = 8192) -> bool:
    try:
        with path.open("rb") as handle:
            return b"\0" in handle.read(sample_size)
    except OSError:
        return False


def files_missing_final_newline(paths: Iterable[str]) -> list[str]:
    missing: list[str] = []
    for raw_path in paths:
        path = pathlib.Path(raw_path)
        if not path.is_file() or is_probably_binary(path):
            continue

        try:
            with path.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                if size == 0:
                    continue
                handle.seek(-1, os.SEEK_END)
                if handle.read(1) != b"\n":
                    missing.append(raw_path)
        except OSError as exc:
            print(f"WARN {raw_path}: {exc}", file=sys.stderr)
    return missing


def run_diff_check(include_staged: bool) -> int:
    commands = [["git", "diff", "--check"]]
    if include_staged:
        commands.append(["git", "diff", "--cached", "--check"])

    for command in commands:
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check changed text files for final newlines and git diff whitespace errors."
    )
    parser.add_argument(
        "--no-untracked",
        action="store_true",
        help="Do not include untracked files in the final-newline check.",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Also run git diff --cached --check for staged changes.",
    )
    parser.add_argument(
        "--newline-only",
        action="store_true",
        help="Skip git diff --check and only check final newlines.",
    )
    args = parser.parse_args()

    paths = changed_paths(include_untracked=not args.no_untracked)
    missing = files_missing_final_newline(paths)
    if missing:
        for path in missing:
            print(f"NO_NEWLINE {path}")
        return 1
    print("newline_check_ok")

    if not args.newline_only:
        diff_status = run_diff_check(include_staged=args.staged)
        if diff_status != 0:
            return diff_status
        print("diff_check_ok")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
