#!/usr/bin/env python3
"""Copy the basic Pi extension template into a target directory."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


TOKEN = "pi-extension-template"


def is_link(path: Path) -> bool:
    """Detect symlinks and Windows junctions, including dangling links."""
    junction_check = getattr(path, "is_junction", None)
    return path.is_symlink() or (junction_check is not None and junction_check())


def copy_template(template: Path, target: Path, package: str, *, force: bool) -> None:
    """Create or update only template paths, preserving unrelated files."""
    if is_link(template) or not template.is_dir():
        raise ValueError("template must be a real directory")
    if is_link(target):
        raise ValueError("target must not be a symlink")
    if target == target.anchor or target == Path(target.anchor):
        raise ValueError("refusing to use a filesystem root as target")
    try:
        target.relative_to(template)
        inside_template = True
    except ValueError:
        inside_template = False
    try:
        template.relative_to(target)
        target_contains_template = True
    except ValueError:
        target_contains_template = False
    if inside_template or target_contains_template:
        raise ValueError("target must not contain or be contained by the skill template")
    if target.exists() and not target.is_dir():
        raise ValueError(f"target is not a directory: {target}")
    if target.exists() and not force:
        raise FileExistsError(f"target exists: {target}")

    source_paths = list(template.rglob("*"))
    if any(is_link(path) for path in source_paths):
        raise ValueError("template must not contain symlink or junction entries")
    files = [path for path in source_paths if path.is_file()]
    destinations = [(path, target / path.relative_to(template)) for path in files]
    for _, destination in destinations:
        relative_parts = destination.relative_to(target).parts
        cursor = target
        for component in relative_parts[:-1]:
            cursor /= component
            if is_link(cursor):
                raise ValueError(f"refusing to traverse linked directory: {cursor}")
            if cursor.exists() and not cursor.is_dir():
                raise ValueError(f"refusing to traverse non-directory: {cursor}")
        if is_link(destination) or (destination.exists() and not destination.is_file()):
            raise ValueError(f"refusing to overwrite non-regular file: {destination}")

    target.mkdir(parents=True, exist_ok=True)
    for source, destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text(encoding="utf-8")
        destination.write_text(text.replace(TOKEN, package), encoding="utf-8", newline="\n")


def package_name(value: str) -> str:
    if not re.fullmatch(r"(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*", value):
        raise argparse.ArgumentTypeError("Use a valid lowercase npm package name.")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Directory to create")
    parser.add_argument("--name", type=package_name, default="my-pi-extension", help="package.json name")
    parser.add_argument("--force", action="store_true", help="overwrite template files in an existing target directory")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    template = skill_dir / "assets" / "templates" / "basic-pi-extension"
    target_arg = args.target.absolute()
    if is_link(target_arg):
        parser.error("target must not be a symlink")
    for ancestor in target_arg.parents:
        if is_link(ancestor):
            parser.error("target must not pass through a symlinked directory")
    target = target_arg.resolve()

    try:
        copy_template(template, target, args.name, force=args.force)
    except (FileExistsError, ValueError) as exc:
        parser.error(str(exc))

    print(f"Created {args.name} at {target}")
    print("Next: npm install && npm run typecheck && npm test && pi -e .")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
