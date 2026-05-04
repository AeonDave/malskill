#!/usr/bin/env python3
"""Find the test that creates unwanted filesystem state.

Usage example:
  python find_polluter.py --watch .tmp-state --tests "tests/**/*_test.py" --command "pytest {test}"
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
    parser.add_argument("--command", required=True, help="Test command. Use {test} where the test path should be inserted.")
    parser.add_argument("--cwd", default=".", help="Working directory. Default: current directory.")
    parser.add_argument("--cleanup-command", help="Optional command run before each test to remove expected pollution.")
    parser.add_argument("--stop-on-fail", action="store_true", help="Stop if a test command exits non-zero before pollution appears.")
    return parser.parse_args()


def render_command(template: str, test_path: Path) -> str:
    test_text = str(test_path)
    if "{test}" in template:
        return template.replace("{test}", shlex.quote(test_text))
    return f"{template} {shlex.quote(test_text)}"


def run_command(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        shell=True,
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

    tests = sorted(path for path in cwd.glob(args.tests) if path.is_file())
    if not tests:
        print(f"ERROR: no test files matched: {args.tests}")
        return 2

    watch_paths = [Path(path) if Path(path).is_absolute() else cwd / path for path in args.watch]

    print(f"Watching {len(watch_paths)} path(s):")
    for path in watch_paths:
        print(f"  - {path}")
    print(f"Testing {len(tests)} file(s) matched by: {args.tests}")

    for index, test in enumerate(tests, start=1):
        if args.cleanup_command:
            cleanup = run_command(args.cleanup_command, cwd)
            if cleanup.returncode != 0:
                print(f"ERROR: cleanup command failed before {test.relative_to(cwd)}")
                print(cleanup.stdout[-4000:])
                return cleanup.returncode or 2

        preexisting = existing_paths(watch_paths)
        if preexisting:
            print("ERROR: watched path exists before test run; clean baseline required.")
            for path in preexisting:
                print(f"  - {path}")
            return 2

        rel_test = test.relative_to(cwd)
        command = render_command(args.command, rel_test)
        print(f"[{index}/{len(tests)}] {rel_test}")
        result = run_command(command, cwd)

        polluted = existing_paths(watch_paths)
        if polluted:
            print("\nFOUND POLLUTER")
            print(f"Test: {rel_test}")
            print(f"Command: {command}")
            print(f"Exit code: {result.returncode}")
            print("Created watched path(s):")
            for path in polluted:
                print(f"  - {path}")
            if result.stdout:
                print("\nLast output lines:")
                print(result.stdout[-4000:])
            return 1

        if args.stop_on_fail and result.returncode != 0:
            print(f"ERROR: test failed before pollution appeared: {rel_test}")
            print(result.stdout[-4000:])
            return result.returncode

    print("\nNo polluter found. Watched paths stayed absent after all test files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
