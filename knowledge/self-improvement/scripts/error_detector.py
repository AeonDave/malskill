#!/usr/bin/env python3
"""Detect likely command failures from tool output and emit a short reminder."""

from __future__ import annotations

import argparse
import os
import sys

ERROR_PATTERNS = (
    "error:",
    "failed",
    "command not found",
    "no such file",
    "permission denied",
    "fatal:",
    "exception",
    "traceback",
    "modulenotfounderror",
    "syntaxerror",
    "typeerror",
    "exit code",
    "non-zero",
)

REMINDER = """<error-detected>
A command failure likely occurred. Log it to .learnings/ERRORS.md if it was non-obvious,
required investigation, or could recur in a future session.
</error-detected>"""


def read_input_text(cli_text: str | None) -> str:
    if cli_text:
        return cli_text

    env_candidates = [
        "CLAUDE_TOOL_OUTPUT",
        "COPILOT_TOOL_OUTPUT",
        "TOOL_OUTPUT",
    ]
    for name in env_candidates:
        value = os.environ.get(name)
        if value:
            return value

    if not sys.stdin.isatty():
        return sys.stdin.read()

    return ""


def likely_error(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in ERROR_PATTERNS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect likely failures in tool output and emit a reminder.",
    )
    parser.add_argument(
        "--text",
        help="Explicit text to inspect instead of environment variables or stdin.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    text = read_input_text(args.text)
    if text and likely_error(text):
        print(REMINDER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
