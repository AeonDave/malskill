#!/usr/bin/env python3
"""Write structured entries to the self-improvement learning store."""

from __future__ import annotations

import argparse

from self_improvement_lib import (
    DEFAULT_AREA,
    DEFAULT_PRIORITY,
    VALID_AREAS,
    VALID_LEARNING_CATEGORIES,
    VALID_PRIORITIES,
    VALID_SOURCES,
    append_text,
    ensure_store,
    entry_file_for_kind,
    format_error_entry,
    format_feature_entry,
    format_learning_entry,
    next_entry_id,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append a structured learning entry.")
    parser.add_argument("--kind", choices=("learning", "error", "feature"), required=True)
    parser.add_argument("--store-dir", default=".learnings")
    parser.add_argument("--summary", help="Summary line for learning or error entries.")
    parser.add_argument("--category", default="insight", help="Learning category.")
    parser.add_argument("--name", help="Short name for error or feature entries.")
    parser.add_argument("--priority", help="Priority level.")
    parser.add_argument("--area", default=DEFAULT_AREA)
    parser.add_argument("--source", default="conversation")
    parser.add_argument("--details", default="")
    parser.add_argument("--suggested-action", default="")
    parser.add_argument("--related-files", default="")
    parser.add_argument("--tags", default="")
    parser.add_argument("--see-also", default="")
    parser.add_argument("--pattern-key", default="")
    parser.add_argument("--recurrence-count", default="")
    parser.add_argument("--first-seen", default="")
    parser.add_argument("--last-seen", default="")
    parser.add_argument("--error-text", default="")
    parser.add_argument("--context", default="")
    parser.add_argument("--suggested-fix", default="")
    parser.add_argument("--reproducible", default="unknown")
    parser.add_argument("--requested-capability", default="")
    parser.add_argument("--user-context", default="")
    parser.add_argument("--complexity", default="medium")
    parser.add_argument("--suggested-implementation", default="")
    parser.add_argument("--frequency", default="first_time")
    parser.add_argument("--related-features", default="")
    return parser


def require_non_empty(value: str | None, label: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError(f"{label} is required")
    return cleaned


def main() -> int:
    args = build_parser().parse_args()
    priority = args.priority or DEFAULT_PRIORITY[args.kind]
    if priority not in VALID_PRIORITIES:
        raise SystemExit(f"Invalid priority: {priority}")
    if args.area not in VALID_AREAS:
        raise SystemExit(f"Invalid area: {args.area}")

    store_dir = ensure_store(args.store_dir)
    target_file = entry_file_for_kind(store_dir, args.kind)
    entry_id = next_entry_id(target_file, args.kind)

    if args.kind == "learning":
        if args.category not in VALID_LEARNING_CATEGORIES:
            raise SystemExit(f"Invalid learning category: {args.category}")
        if args.source not in VALID_SOURCES:
            raise SystemExit(f"Invalid source: {args.source}")
        entry = format_learning_entry(
            entry_id=entry_id,
            category=args.category,
            priority=priority,
            area=args.area,
            summary=require_non_empty(args.summary, "--summary"),
            details=args.details,
            suggested_action=args.suggested_action,
            source=args.source,
            related_files=args.related_files,
            tags=args.tags,
            see_also=args.see_also,
            pattern_key=args.pattern_key,
            recurrence_count=args.recurrence_count,
            first_seen=args.first_seen,
            last_seen=args.last_seen,
        )
    elif args.kind == "error":
        entry = format_error_entry(
            entry_id=entry_id,
            name=require_non_empty(args.name, "--name"),
            priority=priority,
            area=args.area,
            summary=require_non_empty(args.summary, "--summary"),
            error_text=require_non_empty(args.error_text, "--error-text"),
            context=args.context,
            suggested_fix=args.suggested_fix,
            reproducible=args.reproducible,
            related_files=args.related_files,
            tags=args.tags,
            see_also=args.see_also,
        )
    else:
        entry = format_feature_entry(
            entry_id=entry_id,
            name=require_non_empty(args.name, "--name"),
            priority=priority,
            area=args.area,
            requested_capability=require_non_empty(args.requested_capability, "--requested-capability"),
            user_context=args.user_context,
            complexity=args.complexity,
            suggested_implementation=args.suggested_implementation,
            frequency=args.frequency,
            related_features=args.related_features,
            tags=args.tags,
        )

    append_text(target_file, entry)
    print(f"Appended {args.kind} entry {entry_id} to {target_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
