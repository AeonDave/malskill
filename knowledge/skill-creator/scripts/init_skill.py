#!/usr/bin/env python3
"""
Skill Initializer - Scaffold a new skill directory from template.

Usage:
    init_skill.py <skill-name> --path <output-dir> [--resources scripts,references,assets] [--examples]

Examples:
    init_skill.py my-skill --path ~/skills
    init_skill.py my-skill --path ~/skills --resources scripts,references
    init_skill.py my-skill --path ~/skills --resources scripts,references,assets --examples
"""

import argparse
import re
import sys
from pathlib import Path

MAX_NAME_LENGTH = 64
ALLOWED_RESOURCES = {"scripts", "references", "assets"}

SKILL_TEMPLATE = """\
---
name: {skill_name}
description: "[TODO: What this skill does and WHEN to activate it — mention file types, task keywords, activation phrases. Max 1024 chars.]"
---

# {skill_title}

## Overview

[TODO: 1-2 sentences explaining what this skill enables for the agent.]

## Structuring This Skill

[TODO: Choose a structure pattern that fits. Delete this section when done.

**Workflow-based** (sequential processes):
- ## Overview → ## Step 1 → ## Step 2 → ## Troubleshooting

**Task-based** (distinct operations):
- ## Overview → ## Quick Start → ## Task: X → ## Task: Y

**Reference/guidelines** (standards, policies):
- ## Overview → ## Guidelines → ## Specifications

**Capabilities-based** (interrelated features):
- ## Overview → ## Capabilities → ### 1. Feature → ### 2. Feature

Patterns can be mixed. Keep the total under 500 lines — move details to references/.]

## [TODO: First main section]

[TODO: Add content. Include:
- Concrete step-by-step instructions
- Code examples where relevant
- References to scripts and reference files with notes on when to load them]

## Resources

[TODO: List only the resources this skill actually uses. Delete subsections that are not needed.]

### scripts/

[TODO: List each script with a one-line description of what it does and when to run it.]

### references/

[TODO: List each reference file with a one-line description and when the agent should load it.]

### assets/

[TODO: List each asset with a one-line description of how the agent should use it.]
"""

EXAMPLE_SCRIPT = """\
#!/usr/bin/env python3
\"\"\"
Example script for {skill_name}.

Replace this placeholder with actual implementation or delete if not needed.

Agentic ergonomics:
- Output clean success/failure strings to stdout/stderr.
- Never print raw tracebacks — catch exceptions and print a clear message.
- Truncate long outputs (e.g., "Success: First 50 lines shown...").
\"\"\"

import sys


def main():
    # TODO: Implement actual logic here.
    print("Success: example script ran.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Failure: {{exc}}", file=sys.stderr)
        sys.exit(1)
"""

EXAMPLE_REFERENCE = """\
# Reference: {skill_title}

[TODO: Replace with actual reference content or delete this file if not needed.]

## Table of Contents

- [Overview](#overview)
- [Details](#details)

## Overview

Provide a concise summary of this reference document.

## Details

Add detailed documentation here. This file is loaded on demand — it can be long.
Common uses: API specifications, database schemas, workflow guides, company policies.
"""

EXAMPLE_ASSET = """\
# Placeholder Asset

Replace this with an actual asset file (template, image, data file, boilerplate, etc.)
or delete this file if not needed.

Assets are NOT loaded into the agent's context — they are files the agent copies or
uses in its output.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_name(raw: str) -> str:
    """Normalize arbitrary input to a valid hyphen-case skill name."""
    normalized = raw.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized


def title_case(name: str) -> str:
    """Convert hyphen-case to Title Case."""
    return " ".join(word.capitalize() for word in name.split("-"))


def parse_resources(raw: str) -> list[str]:
    """Parse and validate the --resources argument."""
    if not raw:
        return []
    items = [item.strip() for item in raw.split(",") if item.strip()]
    invalid = sorted({i for i in items if i not in ALLOWED_RESOURCES})
    if invalid:
        allowed = ", ".join(sorted(ALLOWED_RESOURCES))
        print(f"[ERROR] Unknown resource type(s): {', '.join(invalid)}")
        print(f"        Allowed: {allowed}")
        sys.exit(1)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result = []
    for i in items:
        if i not in seen:
            seen.add(i)
            result.append(i)
    return result


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def init_skill(
    skill_name: str,
    base_path: str,
    resources: list[str],
    include_examples: bool,
) -> Path | None:
    skill_dir = Path(base_path).resolve() / skill_name

    if skill_dir.exists():
        print(f"[ERROR] Directory already exists: {skill_dir}")
        return None

    skill_title = title_case(skill_name)

    try:
        skill_dir.mkdir(parents=True)
        print(f"[OK] Created: {skill_dir}")
    except Exception as exc:
        print(f"[ERROR] Cannot create directory: {exc}")
        return None

    # SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        SKILL_TEMPLATE.format(skill_name=skill_name, skill_title=skill_title),
        encoding="utf-8",
    )
    print("[OK] Created SKILL.md")

    # Resource directories
    for resource in resources:
        resource_dir = skill_dir / resource
        resource_dir.mkdir()
        if not include_examples:
            print(f"[OK] Created {resource}/")
            continue

        if resource == "scripts":
            script = resource_dir / "example.py"
            script.write_text(
                EXAMPLE_SCRIPT.format(skill_name=skill_name), encoding="utf-8"
            )
            script.chmod(0o755)
            print("[OK] Created scripts/example.py")

        elif resource == "references":
            ref = resource_dir / "reference.md"
            ref.write_text(
                EXAMPLE_REFERENCE.format(skill_title=skill_title), encoding="utf-8"
            )
            print("[OK] Created references/reference.md")

        elif resource == "assets":
            asset = resource_dir / "example_asset.txt"
            asset.write_text(EXAMPLE_ASSET, encoding="utf-8")
            print("[OK] Created assets/example_asset.txt")

    # Next steps
    print(f"\n[OK] Skill '{skill_name}' initialized at {skill_dir}")
    print("\nNext steps:")
    print("  1. Edit SKILL.md — fill in all TODO items, especially description")
    if resources and include_examples:
        print("  2. Customize or delete the example files in resource directories")
    elif resources:
        print("  2. Add files to the resource directories as needed")
    else:
        print("  2. Add scripts/, references/, assets/ directories only if needed")
    print("  3. Run quick_validate.py to check the skill before packaging")

    return skill_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold a new Agent Skill directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("skill_name", help="Skill name (normalized to hyphen-case)")
    parser.add_argument("--path", required=True, help="Output directory")
    parser.add_argument(
        "--resources",
        default="",
        metavar="scripts,references,assets",
        help="Resource directories to create (comma-separated subset)",
    )
    parser.add_argument(
        "--examples",
        action="store_true",
        help="Populate resource directories with placeholder example files",
    )
    args = parser.parse_args()

    raw = args.skill_name
    name = normalize_name(raw)

    if not name:
        print("[ERROR] Skill name must contain at least one letter or digit.")
        sys.exit(1)
    if len(name) > MAX_NAME_LENGTH:
        print(
            f"[ERROR] Name '{name}' is {len(name)} chars — max is {MAX_NAME_LENGTH}."
        )
        sys.exit(1)
    if name != raw:
        print(f"[NOTE] Normalized '{raw}' → '{name}'")

    resources = parse_resources(args.resources)

    if args.examples and not resources:
        print("[ERROR] --examples requires --resources to be specified.")
        sys.exit(1)

    print(f"Initializing skill: {name}")
    print(f"  Location:  {args.path}")
    print(f"  Resources: {', '.join(resources) if resources else 'none (add as needed)'}")
    if args.examples:
        print("  Examples:  enabled")
    print()

    result = init_skill(name, args.path, resources, args.examples)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
