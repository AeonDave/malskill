#!/usr/bin/env python3
"""
validate_all.py — Run quick_validate on every skill directory in the repo.

A skill directory is any folder that directly contains a SKILL.md file.
Searches from the repo root (two levels above this script by default) or
from an explicit root path passed as an argument.

Usage:
    python knowledge/skill-creator/scripts/validate_all.py [<repo-root>] [--exclude <dir> ...]

    --exclude <dir>   Exclude any skill path whose components include <dir>.
                      Can be repeated. Defaults to excluding '.import'.

Examples:
    python knowledge/skill-creator/scripts/validate_all.py
    python knowledge/skill-creator/scripts/validate_all.py . --exclude .import --exclude vendor

Exit codes:
    0  All skills valid (warnings allowed)
    1  One or more skills failed validation
"""

import sys
from pathlib import Path

# Allow running from any working directory
_SCRIPTS_DIR = Path(__file__).resolve().parent
_DEFAULT_ROOT = _SCRIPTS_DIR.parent.parent.parent  # scripts/ -> skill-creator/ -> knowledge/ -> repo root

sys.path.insert(0, str(_SCRIPTS_DIR))
from quick_validate import validate_skill  # noqa: E402


def find_skill_dirs(root: Path, excludes: set[str]) -> list[Path]:
    """Return all directories that contain a SKILL.md, sorted by path.
    Excludes skill paths whose relative path contains any of the exclude names as a component.
    """
    results = []
    for p in root.rglob("SKILL.md"):
        if not p.is_file():
            continue
        skill_dir = p.parent
        rel_parts = set(skill_dir.relative_to(root).parts)
        if rel_parts & excludes:
            continue
        results.append(skill_dir)
    return sorted(results)


def _parse_args() -> tuple[Path, set[str]]:
    args = sys.argv[1:]
    repo_root = _DEFAULT_ROOT
    excludes: set[str] = {".import"}  # default

    i = 0
    positional_consumed = False
    while i < len(args):
        if args[i] == "--exclude":
            i += 1
            if i < len(args):
                excludes.add(args[i])
        elif not positional_consumed and not args[i].startswith("--"):
            repo_root = Path(args[i]).resolve()
            positional_consumed = True
        i += 1

    return repo_root, excludes


def main() -> None:
    repo_root, excludes = _parse_args()

    if not repo_root.is_dir():
        print(f"ERROR: repo root not found: {repo_root}", file=sys.stderr)
        sys.exit(1)

    skill_dirs = find_skill_dirs(repo_root, excludes)
    if not skill_dirs:
        print("No skill directories found.", file=sys.stderr)
        sys.exit(1)

    passed = 0
    warned = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    for skill_dir in skill_dirs:
        rel = skill_dir.relative_to(repo_root)
        valid, message = validate_skill(skill_dir)
        if not valid:
            print(f"  FAIL  {rel}: {message}")
            failed += 1
            failures.append((str(rel), message))
        elif message.startswith("[WARNING]"):
            print(f"  WARN  {rel}: {message}")
            warned += 1
            passed += 1
        else:
            print(f"  OK    {rel}")
            passed += 1

    total = passed + failed
    print(f"\nTOTAL={total}  PASSED={passed}  WARNED={warned}  FAILED={failed}")

    if failures:
        print("\nFailed skills:")
        for rel, msg in failures:
            print(f"  {rel}: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
