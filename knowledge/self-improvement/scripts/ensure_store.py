#!/usr/bin/env python3
"""Create the .learnings store and copy starter templates when missing."""

from __future__ import annotations

import argparse

from self_improvement_lib import ensure_store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ensure the self-improvement learning store exists.")
    parser.add_argument(
        "--store-dir",
        default=".learnings",
        help="Learning store directory to create or update. Default: .learnings",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target_dir = ensure_store(args.store_dir)
    print(f"Ensured learning store at {target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
