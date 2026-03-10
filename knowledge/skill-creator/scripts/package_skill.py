#!/usr/bin/env python3
"""
Skill Packager - Validate and package a skill into a distributable .skill file.

The .skill file is a standard zip archive. The folder structure inside the zip
preserves the skill directory name, so agents can unzip it directly.

Usage:
    package_skill.py <path/to/skill-folder> [output-directory]

Examples:
    package_skill.py ~/skills/my-skill
    package_skill.py ~/skills/my-skill ./dist

Exit codes:
    0  Package created successfully
    1  Validation failed or packaging error
"""

import sys
import zipfile
from pathlib import Path

from quick_validate import validate_skill

# Files and directories to exclude from the package
EXCLUDE_DIRS = {".git", "__pycache__", ".DS_Store", "node_modules", ".venv", "venv"}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db"}


def package_skill(skill_path: str | Path, output_dir: str | Path | None = None) -> Path | None:
    """
    Validate and package a skill directory into a .skill file.

    Returns:
        Path to the created .skill file, or None on failure.
    """
    skill_path = Path(skill_path).resolve()

    if not skill_path.exists():
        print(f"[ERROR] Skill directory not found: {skill_path}")
        return None
    if not skill_path.is_dir():
        print(f"[ERROR] Not a directory: {skill_path}")
        return None

    # Validate first
    print("Validating skill...")
    valid, message = validate_skill(skill_path)

    if not valid:
        print(f"[ERROR] Validation failed: {message}")
        print("        Fix errors before packaging.")
        return None

    if message.startswith("[WARNING]"):
        print(message)
        print("[ERROR] Resolve all TODOs before packaging.")
        return None

    print(f"[OK] {message}")

    # Determine output path
    skill_name = skill_path.name
    if output_dir:
        out = Path(output_dir).resolve()
        out.mkdir(parents=True, exist_ok=True)
    else:
        out = Path.cwd()

    skill_file = out / f"{skill_name}.skill"

    # Build the zip
    print(f"\nPackaging {skill_name}...")
    try:
        with zipfile.ZipFile(skill_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in sorted(skill_path.rglob("*")):
                if not file.is_file():
                    continue
                # Skip excluded directories anywhere in the path
                if any(part in EXCLUDE_DIRS for part in file.parts):
                    continue
                if file.name in EXCLUDE_FILES:
                    continue
                arcname = file.relative_to(skill_path.parent)
                zf.write(file, arcname)
                print(f"  + {arcname}")
    except Exception as exc:
        print(f"[ERROR] Failed to create .skill file: {exc}")
        return None

    print(f"\n[OK] Package created: {skill_file}")
    return skill_file


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    skill_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Packaging: {skill_path}")
    if output_dir:
        print(f"Output:    {output_dir}")
    print()

    result = package_skill(skill_path, output_dir)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
