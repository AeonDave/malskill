#!/usr/bin/env python3
"""Promote a learning entry into project guidance or a new skill."""

from __future__ import annotations

import argparse
from pathlib import Path

from self_improvement_lib import (
    DEFAULT_SECTION_TITLE,
    append_under_heading,
    create_skill_from_values,
    distilled_rule_from_entry,
    get_entry_block,
    infer_values_from_source,
    upsert_status_fields,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Promote a learning into durable guidance or a new skill.")
    parser.add_argument("--source-file", required=True, help="Markdown file containing the source learning entry.")
    parser.add_argument("--entry-id", required=True, help="Learning entry identifier to promote.")
    parser.add_argument("--target", choices=("file", "skill"), required=True)
    parser.add_argument("--target-file", help="Target Markdown file when promoting into instructions or memory.")
    parser.add_argument("--target-label", help="Label recorded in the source entry, defaults to the target file name.")
    parser.add_argument("--section", default=DEFAULT_SECTION_TITLE, help="Heading under which promoted rules are appended.")
    parser.add_argument("--rule", help="Distilled rule to append to the target file.")
    parser.add_argument("--rule-file", help="File containing the distilled rule text.")
    parser.add_argument("--skill-name", help="Explicit skill name for skill promotion.")
    parser.add_argument("--skills-root", default="knowledge", help="Directory under which a new skill should be created.")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def read_rule_text(args: argparse.Namespace, block: str) -> str:
    if args.rule:
        return args.rule.strip()
    if args.rule_file:
        return Path(args.rule_file).read_text(encoding="utf-8").strip()
    return distilled_rule_from_entry(block)


def promote_to_file(args: argparse.Namespace, source_file: Path, block: str) -> int:
    if not args.target_file:
        raise SystemExit("--target-file is required when --target file is used")
    rule_text = read_rule_text(args, block)
    target_file = Path(args.target_file)
    label = args.target_label or target_file.name

    if args.dry_run:
        print(f"Would append this rule to {target_file} under section '{args.section}':")
        print(rule_text)
        print(f"Would mark {args.entry_id} as promoted to {label}")
        return 0

    append_under_heading(target_file, args.section, rule_text)
    upsert_status_fields(source_file, args.entry_id, new_status="promoted", promoted=label)
    print(f"Promoted {args.entry_id} to {target_file}")
    return 0


def promote_to_skill(args: argparse.Namespace, source_file: Path) -> int:
    values = infer_values_from_source(source_file=source_file, entry_id=args.entry_id, explicit_skill_name=args.skill_name)
    target_path = Path(args.skills_root) / values["skill_name"]

    if args.dry_run:
        print(f"Would create skill at {target_path}")
        print(f"Would mark {args.entry_id} as promoted_to_skill")
        return 0

    created_path = create_skill_from_values(output_root=Path(args.skills_root), dry_run=False, **values)
    upsert_status_fields(
        source_file,
        args.entry_id,
        new_status="promoted_to_skill",
        skill_path=str(created_path).replace("\\", "/"),
    )
    print(f"Promoted {args.entry_id} into new skill at {created_path}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    source_file = Path(args.source_file)
    block = get_entry_block(source_file, args.entry_id)

    if args.target == "file":
        return promote_to_file(args, source_file, block)
    return promote_to_skill(args, source_file)


if __name__ == "__main__":
    raise SystemExit(main())
