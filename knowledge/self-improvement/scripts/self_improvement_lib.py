#!/usr/bin/env python3
"""Shared helpers for self-improvement automation scripts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
from typing import Final

DEFAULT_SECTION_TITLE: Final[str] = "Self-Improvement Promotions"
ENTRY_HEADING_RE: Final[re.Pattern[str]] = re.compile(
    r"^## \[(?P<id>[A-Z]+-\d{8}-\d{3})\]\s*(?P<title>.+)$",
    re.MULTILINE,
)
SECTION_NAMES: Final[tuple[str, ...]] = (
    "Summary",
    "Details",
    "Suggested Action",
    "Error",
    "Context",
    "Requested Capability",
    "User Context",
    "Complexity Estimate",
    "Suggested Implementation",
    "Metadata",
    "Resolution",
)
ASSET_FILE_MAP: Final[dict[str, str]] = {
    "LEARNINGS.md": "LEARNINGS.md",
    "ERRORS.md": "ERRORS-template.md",
    "FEATURE_REQUESTS.md": "FEATURE-REQUESTS-template.md",
}
PREFIX_MAP: Final[dict[str, str]] = {
    "learning": "LRN",
    "error": "ERR",
    "feature": "FEAT",
}
TARGET_FILE_MAP: Final[dict[str, str]] = {
    "learning": "LEARNINGS.md",
    "error": "ERRORS.md",
    "feature": "FEATURE_REQUESTS.md",
}
DEFAULT_PRIORITY: Final[dict[str, str]] = {
    "learning": "medium",
    "error": "high",
    "feature": "medium",
}
DEFAULT_AREA: Final[str] = "workflow"
VALID_PRIORITIES: Final[set[str]] = {"low", "medium", "high", "critical"}
VALID_STATUSES: Final[set[str]] = {
    "pending",
    "in_progress",
    "resolved",
    "wont_fix",
    "promoted",
    "promoted_to_skill",
}
VALID_LEARNING_CATEGORIES: Final[set[str]] = {
    "correction",
    "insight",
    "knowledge_gap",
    "best_practice",
}
VALID_AREAS: Final[set[str]] = {
    "workflow",
    "repo-config",
    "docs",
    "tooling",
    "programming",
    "testing",
    "knowledge",
    "research",
    "offensive-tools",
    "bof",
}
VALID_SOURCES: Final[set[str]] = {
    "conversation",
    "user_feedback",
    "error",
    "review",
    "research",
    "simplify-and-harden",
}


def script_root() -> Path:
    return Path(__file__).resolve().parent.parent


def assets_dir() -> Path:
    return script_root() / "assets"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def utc_date_hint() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def resolve_store_dir(store_dir: str | Path | None) -> Path:
    candidate = Path(store_dir or ".learnings")
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    return candidate.resolve()


def ensure_store(store_dir: str | Path | None) -> Path:
    target_dir = resolve_store_dir(store_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    source_dir = assets_dir()
    for output_name, template_name in ASSET_FILE_MAP.items():
        output_path = target_dir / output_name
        if output_path.exists():
            continue
        shutil.copyfile(source_dir / template_name, output_path)
    return target_dir


def _next_sequence(file_path: Path, prefix: str, day_stamp: str) -> int:
    if not file_path.exists():
        return 1
    pattern = re.compile(rf"\[{re.escape(prefix)}-{day_stamp}-(\d{{3}})\]")
    values = [int(match.group(1)) for match in pattern.finditer(file_path.read_text(encoding="utf-8"))]
    return (max(values) + 1) if values else 1


def next_entry_id(file_path: Path, kind: str) -> str:
    prefix = PREFIX_MAP[kind]
    day_stamp = utc_day()
    sequence = _next_sequence(file_path, prefix, day_stamp)
    return f"{prefix}-{day_stamp}-{sequence:03d}"


def append_text(file_path: Path, text: str) -> None:
    existing = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
    with file_path.open("a", encoding="utf-8") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        if existing.strip():
            handle.write("\n")
        handle.write(text.rstrip() + "\n")


def _normalize_multiline(value: str) -> str:
    value = value.strip("\n")
    return value if value else "N/A"


def _metadata_lines(items: list[tuple[str, str | None]]) -> str:
    lines: list[str] = []
    for key, value in items:
        if value is None or value == "":
            continue
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "- Source: conversation"


def format_learning_entry(
    *,
    entry_id: str,
    category: str,
    priority: str,
    area: str,
    summary: str,
    details: str,
    suggested_action: str,
    source: str,
    related_files: str | None,
    tags: str | None,
    see_also: str | None,
    pattern_key: str | None,
    recurrence_count: str | None,
    first_seen: str | None,
    last_seen: str | None,
) -> str:
    metadata = _metadata_lines(
        [
            ("Source", source),
            ("Related Files", related_files),
            ("Tags", tags),
            ("See Also", see_also),
            ("Pattern-Key", pattern_key),
            ("Recurrence-Count", recurrence_count),
            ("First-Seen", first_seen),
            ("Last-Seen", last_seen),
        ]
    )
    return f"""## [{entry_id}] {category}

**Logged**: {utc_timestamp()}
**Priority**: {priority}
**Status**: pending
**Area**: {area}

### Summary
{summary.strip()}

### Details
{_normalize_multiline(details)}

### Suggested Action
{_normalize_multiline(suggested_action)}

### Metadata
{metadata}

---"""


def format_error_entry(
    *,
    entry_id: str,
    name: str,
    priority: str,
    area: str,
    summary: str,
    error_text: str,
    context: str,
    suggested_fix: str,
    reproducible: str,
    related_files: str | None,
    tags: str | None,
    see_also: str | None,
) -> str:
    metadata = _metadata_lines(
        [
            ("Reproducible", reproducible),
            ("Related Files", related_files),
            ("See Also", see_also),
            ("Tags", tags),
        ]
    )
    return f"""## [{entry_id}] {name.strip()}

**Logged**: {utc_timestamp()}
**Priority**: {priority}
**Status**: pending
**Area**: {area}

### Summary
{summary.strip()}

### Error
```text
{_normalize_multiline(error_text)}
```

### Context
{_normalize_multiline(context)}

### Suggested Fix
{_normalize_multiline(suggested_fix)}

### Metadata
{metadata}

---"""


def format_feature_entry(
    *,
    entry_id: str,
    name: str,
    priority: str,
    area: str,
    requested_capability: str,
    user_context: str,
    complexity: str,
    suggested_implementation: str,
    frequency: str,
    related_features: str | None,
    tags: str | None,
) -> str:
    metadata = _metadata_lines(
        [
            ("Frequency", frequency),
            ("Related Features", related_features),
            ("Tags", tags),
        ]
    )
    return f"""## [{entry_id}] {name.strip()}

**Logged**: {utc_timestamp()}
**Priority**: {priority}
**Status**: pending
**Area**: {area}

### Requested Capability
{requested_capability.strip()}

### User Context
{_normalize_multiline(user_context)}

### Complexity Estimate
{complexity}

### Suggested Implementation
{_normalize_multiline(suggested_implementation)}

### Metadata
{metadata}

---"""


def entry_file_for_kind(store_dir: Path, kind: str) -> Path:
    return store_dir / TARGET_FILE_MAP[kind]


def find_entry_span(text: str, entry_id: str) -> tuple[int, int]:
    matches = list(ENTRY_HEADING_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.group("id") != entry_id:
            continue
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        return start, end
    raise ValueError(f"Entry not found: {entry_id}")


def get_entry_block(file_path: Path, entry_id: str) -> str:
    text = file_path.read_text(encoding="utf-8")
    start, end = find_entry_span(text, entry_id)
    return text[start:end].strip("\n")


def extract_sections(block: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for index, name in enumerate(SECTION_NAMES):
        pattern = re.compile(rf"^### {re.escape(name)}\n", re.MULTILINE)
        match = pattern.search(block)
        if not match:
            continue
        start = match.end()
        end = len(block)
        for later_name in SECTION_NAMES[index + 1 :]:
            later_pattern = re.compile(rf"^### {re.escape(later_name)}\n", re.MULTILINE)
            later_match = later_pattern.search(block, start)
            if later_match:
                end = later_match.start()
                break
        result[name] = block[start:end].strip()
    return result


def extract_title(block: str) -> str:
    match = ENTRY_HEADING_RE.search(block)
    return match.group("title").strip() if match else "entry"


def extract_field(block: str, field_name: str) -> str | None:
    pattern = re.compile(rf"^\*\*{re.escape(field_name)}\*\*: (.+)$", re.MULTILINE)
    match = pattern.search(block)
    return match.group(1).strip() if match else None


def upsert_status_fields(
    file_path: Path,
    entry_id: str,
    *,
    new_status: str,
    promoted: str | None = None,
    skill_path: str | None = None,
) -> None:
    text = file_path.read_text(encoding="utf-8")
    start, end = find_entry_span(text, entry_id)
    block = text[start:end].strip("\n")
    lines = block.splitlines()
    updated: list[str] = []
    inserted_promoted = False
    inserted_skill_path = False

    for line in lines:
        if line.startswith("**Status**:"):
            updated.append(f"**Status**: {new_status}")
            if promoted:
                updated.append(f"**Promoted**: {promoted}")
                inserted_promoted = True
            if skill_path:
                updated.append(f"**Skill-Path**: {skill_path}")
                inserted_skill_path = True
            continue
        if line.startswith("**Promoted**:"):
            if promoted and not inserted_promoted:
                updated.append(f"**Promoted**: {promoted}")
                inserted_promoted = True
            continue
        if line.startswith("**Skill-Path**:"):
            if skill_path and not inserted_skill_path:
                updated.append(f"**Skill-Path**: {skill_path}")
                inserted_skill_path = True
            continue
        updated.append(line)

    new_block = "\n".join(updated).rstrip() + "\n"
    file_path.write_text(text[:start] + new_block + text[end:].lstrip("\n"), encoding="utf-8")


def append_under_heading(target_file: Path, section_title: str, content: str) -> None:
    if target_file.exists():
        text = target_file.read_text(encoding="utf-8")
    else:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        text = ""

    heading = f"## {section_title}"
    section_re = re.compile(rf"^## {re.escape(section_title)}$", re.MULTILINE)
    clean_content = content.rstrip() + "\n"

    if section_re.search(text):
        matches = list(re.finditer(r"^## .+$", text, re.MULTILINE))
        insert_at = len(text)
        for index, match in enumerate(matches):
            if match.group(0) != heading:
                continue
            insert_at = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            break
        new_text = text[:insert_at].rstrip() + "\n" + clean_content + text[insert_at:]
        target_file.write_text(new_text.rstrip() + "\n", encoding="utf-8")
        return

    prefix = "\n\n" if text.strip() else ""
    target_file.write_text(
        text.rstrip() + f"{prefix}{heading}\n\n{clean_content}" if text.strip() else f"{heading}\n\n{clean_content}",
        encoding="utf-8",
    )


def first_sentence(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    match = re.match(r"(.+?[.!?])(?:\s|$)", cleaned)
    return match.group(1) if match else cleaned


def distilled_rule_from_entry(block: str) -> str:
    sections = extract_sections(block)
    summary = sections.get("Summary") or sections.get("Requested Capability") or extract_title(block)
    action = sections.get("Suggested Action") or sections.get("Suggested Fix") or sections.get("Suggested Implementation")
    if action:
        return f"- {first_sentence(summary)} {first_sentence(action)}".strip()
    return f"- {first_sentence(summary)}".strip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or "new-skill"


def skill_title(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def build_skill_description(summary: str) -> str:
    summary = first_sentence(summary).strip()
    if not summary:
        summary = "Capture a reusable workflow from a verified learning"
    if len(summary) > 160:
        summary = summary[:157].rstrip() + "..."
    return f"{summary}. Use when the same non-obvious problem or workflow appears again."


# ---------------------------------------------------------------------------
# Skill scaffolding helpers (used by extract_skill.py and promote_learning.py)
# ---------------------------------------------------------------------------

NAME_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_skill_name(name: str) -> None:
    if not NAME_RE.fullmatch(name):
        raise ValueError("Skill name must use lowercase letters, digits, and single hyphens only.")


def ensure_safe_target(root: Path, skill_name: str) -> Path:
    root = root.resolve()
    target = (root / skill_name).resolve()
    if root not in target.parents and target != root:
        raise ValueError("Refusing to create a skill outside the requested output directory.")
    return target


def normalize_resources(resources: str) -> list[str]:
    return [part.strip() for part in resources.split(",") if part.strip()]


def infer_values_from_source(
    *,
    source_file: Path,
    entry_id: str,
    explicit_skill_name: str | None,
) -> dict[str, str]:
    block = get_entry_block(source_file, entry_id)
    sections = extract_sections(block)
    summary = (
        sections.get("Summary")
        or sections.get("Requested Capability")
        or f"Reusable workflow derived from {entry_id}"
    ).strip()
    background = (
        sections.get("Details")
        or sections.get("Error")
        or sections.get("User Context")
        or sections.get("Context")
        or summary
    ).strip()
    suggested_action = (
        sections.get("Suggested Action")
        or sections.get("Suggested Fix")
        or sections.get("Suggested Implementation")
        or "Review the original learning and turn it into repeatable, validated steps."
    ).strip()
    skill_name = explicit_skill_name or slugify(summary)
    return {
        "skill_name": skill_name,
        "learning_id": entry_id,
        "summary": summary,
        "background": background,
        "suggested_action": suggested_action,
        "date_hint": utc_date_hint(),
    }


def render_skill_md(
    *,
    skill_name: str,
    learning_id: str,
    summary: str,
    background: str,
    suggested_action: str,
    date_hint: str,
) -> str:
    description = build_skill_description(summary)
    action_sentence = " ".join(suggested_action.split()) or "Apply the reusable fix, then verify the outcome."
    return f"""---
name: {skill_name}
description: \"{description}\"
---

# {skill_title(skill_name)}

{summary}

## When to use

- the same non-obvious problem appears again
- the original learning has been validated and should become reusable guidance
- future sessions would benefit from having the workflow pre-written

## Workflow

1. Review the original learning and remove incident-only detail.
2. Capture the reusable checks, commands, and decision points.
3. Apply this rule: {action_sentence}
4. Validate the resulting workflow in a fresh task before packaging or broad reuse.

## Background

{background}

## Resources

- add `references/`, `assets/`, or `scripts/` only when they clearly improve reuse

## Source

- Learning ID: {learning_id}
- Extraction Date: {date_hint}
"""


def create_skill_from_values(
    *,
    output_root: Path,
    skill_name: str,
    learning_id: str,
    summary: str,
    background: str,
    suggested_action: str,
    date_hint: str,
    resources: list[str] | None = None,
    dry_run: bool,
) -> Path:
    validate_skill_name(skill_name)
    target = ensure_safe_target(output_root, skill_name)
    content = render_skill_md(
        skill_name=skill_name,
        learning_id=learning_id,
        summary=summary,
        background=background,
        suggested_action=suggested_action,
        date_hint=date_hint,
    )

    if dry_run:
        print(f"Target: {target}")
        print()
        print(content)
        if resources:
            print()
            print(f"Resource directories: {', '.join(resources)}")
        return target

    if target.exists():
        raise ValueError(f"target already exists: {target}")

    target.mkdir(parents=True)
    (target / "SKILL.md").write_text(content, encoding="utf-8")
    for resource in resources or []:
        (target / resource).mkdir(parents=True, exist_ok=True)
    print(f"Created skill scaffold at {target}")
    return target
