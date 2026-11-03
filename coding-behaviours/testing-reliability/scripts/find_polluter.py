#!/usr/bin/env python3
"""Find the test that creates unwanted filesystem state.

Usage example:
  python find_polluter.py --watch .tmp-state --tests "tests/**/*_test.py" --command "pytest {test}"

The test command is an argv template, parsed using POSIX quoting before
{test} is substituted. Use forward slashes in Windows paths in the template.
Shell operators are unsupported; cleanup-command is an explicit shell command.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run tests one at a time and report the first test that creates watched paths."
    )
    parser.add_argument("--watch", action="append", required=True, help="Path that must not appear after a test run. Can be repeated.")
    parser.add_argument("--tests", required=True, help="Glob for test files, for example tests/**/*.py.")
    parser.add_argument("--command", required=True, help="Argv template using POSIX quoting; {test} inserts the test path (or it is appended). Use forward slashes in Windows template paths; no shell operators.")
    parser.add_argument("--cwd", default=".", help="Working directory. Default: current directory.")
    parser.add_argument("--cleanup-command", help="Optional shell command run before each test to remove expected pollution.")
    parser.add_argument("--stop-on-fail", action="store_true", help="Stop if a test command exits non-zero before pollution appears.")
    return parser.parse_args()


def parse_command(template: str) -> list[str]:
    lexer = shlex.shlex(template, posix=True, punctuation_chars="|&;<>()")
    lexer.whitespace_split = True
    lexer.commenters = ""
    parts = list(lexer)
    if not parts or any(part and all(char in "|&;<>()" for char in part) for part in parts):
        raise ValueError("command must be a nonempty argv template without shell operators")
    return parts


def render_command(template: list[str], test_path: Path) -> list[str]:
    result = [part.replace("{test}", str(test_path)) for part in template]
    if not any("{test}" in part for part in template):
        result.append(str(test_path))
    return result


def run_command(command: list[str] | str, cwd: Path, *, shell: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        shell=shell,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def existing_paths(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def main() -> int:
    args = parse_args()
    cwd = Path(args.cwd).resolve()
    if not cwd.is_dir():
        print(f"ERROR: working directory does not exist: {cwd}")
        return 2

    try:
        template = parse_command(args.command)
    except ValueError as exc:
        print(f"ERROR: invalid test command: {exc}")
        return 2

    tests = sorted(path for path in cwd.glob(args.tests) if path.is_file())
    if not tests:
        print(f"ERROR: no test files matched: {args.tests}")
        return 2

    watch_paths = [Path(path) if Path(path).is_absolute() else cwd / path for path in args.watch]

    print(f"Watching {len(watch_paths)} path(s):")
    for path in watch_paths:
        print(f"  - {path}")
    print(f"Testing {len(tests)} file(s) matched by: {args.tests}")

    failed = False
    for index, test in enumerate(tests, start=1):
        if args.cleanup_command:
            cleanup = run_command(args.cleanup_command, cwd, shell=True)
            if cleanup.returncode != 0:
                print(f"ERROR: cleanup command failed before {test.relative_to(cwd)}")
                print(cleanup.stdout)
                return cleanup.returncode or 2

        preexisting = existing_paths(watch_paths)
        if preexisting:
            print("ERROR: watched path exists before test run; clean baseline required.")
            for path in preexisting:
                print(f"  - {path}")
            return 2

        rel_test = test.relative_to(cwd)
        command = render_command(template, rel_test)
        print(f"[{index}/{len(tests)}] {rel_test}")
        try:
            result = run_command(command, cwd)
        except OSError as exc:
            print(f"ERROR: could not start test command: {exc}")
            return 2

        polluted = existing_paths(watch_paths)
        if polluted:
            print("\nFOUND POLLUTER")
            print(f"Test: {rel_test}")
            print(f"Command argv: {command!r}")
            print(f"Exit code: {result.returncode}")
            print("Created watched path(s):")
            for path in polluted:
                print(f"  - {path}")
            if result.stdout:
                print("\nTest output:")
                print(result.stdout)
            return 1

        if result.returncode != 0:
            failed = True
            print(f"ERROR: test failed before pollution appeared: {rel_test} (exit {result.returncode})")
            if result.stdout:
                print(result.stdout)
            if args.stop_on_fail:
                return result.returncode

    if failed:
        print("\nInconclusive: no polluter found, but one or more tests failed.")
        return 2

    print("\nNo polluter found. Watched paths stayed absent after all test files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
