#!/usr/bin/env python3
"""
validate_all.py — Run quick_validate on every skill directory in the repo.

A skill directory is any folder that directly contains a SKILL.md file.
Searches from the repo root (the parent of the scripts directory by default) or
from an explicit root path passed as an argument.

Usage:
    python scripts/validate_all.py [<repo-root>] [--exclude <dir> ...]
    python scripts/validate_all.py --skill-dir <path> [--skill-dir <path> ...]

    --exclude <dir>     Exclude any skill path whose components include <dir>.
                        Can be repeated. Defaults to excluding '.import'.
    --skill-dir <path>  Validate an explicit skill directory instead of
                        discovering under a root. Can be repeated. When any
                        --skill-dir is given, discovery and --exclude are
                        skipped and any positional root is ignored.

Examples:
    python scripts/validate_all.py
    python scripts/validate_all.py . --exclude .import --exclude vendor
    python scripts/validate_all.py \
        --skill-dir coding/rust-patterns --skill-dir coding/golang-patterns

Exit codes:
    0  All skills valid (warnings allowed)
    1  One or more skills failed validation
"""

import argparse
import sys
from pathlib import Path

# Allow running from any working directory
_SCRIPTS_DIR = Path(__file__).resolve().parent
_DEFAULT_ROOT = _SCRIPTS_DIR.parent

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


def _parse_args(argv: list[str] | None = None) -> tuple[Path, set[str], list[Path]]:
    parser = argparse.ArgumentParser(description="Validate skill directories in a repository.")
    parser.add_argument(
        "repo_root",
        nargs="?",
        type=Path,
        default=_DEFAULT_ROOT,
        help="repository root to scan (defaults to the parent of scripts/)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="DIR",
        help="exclude skill paths containing DIR (repeatable; defaults to .import)",
    )
    parser.add_argument(
        "--skill-dir",
        action="append",
        default=[],
        type=Path,
        metavar="PATH",
        help="validate an explicit skill directory instead of discovery (repeatable)",
    )
    args = parser.parse_args(argv)
    excludes = {".import"} | set(args.exclude or [])
    return args.repo_root.resolve(), excludes, [path.resolve() for path in args.skill_dir]


def main(argv: list[str] | None = None) -> int:
    repo_root, excludes, explicit_skill_dirs = _parse_args(argv)

    if explicit_skill_dirs:
        # Preserve caller-supplied order but drop duplicates.
        seen: set[Path] = set()
        skill_dirs: list[Path] = []
        for d in explicit_skill_dirs:
            if d in seen:
                continue
            seen.add(d)
            skill_dirs.append(d)
        # Anchor relative paths against the current working directory when possible;
        # this keeps output readable regardless of caller CWD.
        display_anchor = Path.cwd()
    else:
        if not repo_root.is_dir():
            print(f"ERROR: repo root not found: {repo_root}", file=sys.stderr)
            return 1
        skill_dirs = find_skill_dirs(repo_root, excludes)
        display_anchor = repo_root

    if not skill_dirs:
        print("No skill directories found.", file=sys.stderr)
        return 1

    passed = 0
    warned = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    for skill_dir in skill_dirs:
        try:
            rel = skill_dir.relative_to(display_anchor)
        except ValueError:
            rel = skill_dir
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
        return 1


if __name__ == "__main__":
    sys.exit(main())
