#!/usr/bin/env python3
"""Scaffold a new skill directory from a learning theme or entry."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from self_improvement_lib import (
    create_skill_from_values,
    infer_values_from_source,
    normalize_resources,
    utc_date_hint,
    validate_skill_name,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a new skill scaffold from a learning theme or entry.",
    )
    parser.add_argument(
        "skill_name",
        nargs="?",
        help="Optional explicit lowercase hyphenated skill name.",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory under which the new skill folder will be created. Default: current directory.",
    )
    parser.add_argument(
        "--learning-id",
        default="LRN-YYYYMMDD-XXX",
        help="Source learning identifier to record in the generated skill.",
    )
    parser.add_argument(
        "--date-hint",
        default=utc_date_hint(),
        help="Extraction date to include in the scaffold. Default: today in UTC.",
    )
    parser.add_argument(
        "--summary",
        default="",
        help="Summary sentence for the generated skill when not loading from a source entry.",
    )
    parser.add_argument(
        "--background",
        default="",
        help="Optional background/problem statement for the generated skill.",
    )
    parser.add_argument(
        "--suggested-action",
        default="",
        help="Optional suggested action used to seed the workflow section.",
    )
    parser.add_argument(
        "--source-file",
        help="Markdown file containing the source learning entry to extract from.",
    )
    parser.add_argument(
        "--entry-id",
        help="Learning entry identifier to extract from the source file.",
    )
    parser.add_argument(
        "--resources",
        default="",
        help="Comma-separated resource directories to create, e.g. references,assets,scripts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the target path and resulting SKILL.md content without creating files.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        if args.source_file and args.entry_id:
            values = infer_values_from_source(
                source_file=Path(args.source_file),
                entry_id=args.entry_id,
                explicit_skill_name=args.skill_name,
            )
        else:
            if not args.skill_name:
                raise ValueError("skill_name is required when no --source-file/--entry-id pair is provided")
            validate_skill_name(args.skill_name)
            summary = (args.summary or "Reusable workflow captured from a validated learning").strip()
            values = {
                "skill_name": args.skill_name,
                "learning_id": args.learning_id,
                "summary": summary,
                "background": (args.background or summary).strip(),
                "suggested_action": (args.suggested_action or "Review the original learning and turn it into repeatable, validated steps.").strip(),
                "date_hint": args.date_hint,
            }

        create_skill_from_values(
            output_root=Path(args.output_dir),
            resources=normalize_resources(args.resources),
            dry_run=args.dry_run,
            **values,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Next: refine the generated skill only if the learning needs more examples, references, or helper scripts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
