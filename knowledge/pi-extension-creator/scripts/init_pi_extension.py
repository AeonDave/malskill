#!/usr/bin/env python3
"""Copy the basic Pi extension template into a target directory."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


TOKEN = "pi-extension-template"


def package_name(value: str) -> str:
    if not re.fullmatch(r"(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*", value):
        raise argparse.ArgumentTypeError("Use a valid lowercase npm package name.")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Directory to create")
    parser.add_argument("--name", type=package_name, default="my-pi-extension", help="package.json name")
    parser.add_argument("--force", action="store_true", help="overwrite an existing target directory")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    template = skill_dir / "assets" / "templates" / "basic-pi-extension"
    target = args.target.resolve()

    if target.exists():
        if not args.force:
            parser.error(f"target exists: {target}")
        shutil.rmtree(target)

    shutil.copytree(template, target)

    for path in target.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if TOKEN in text:
            path.write_text(text.replace(TOKEN, args.name), encoding="utf-8", newline="\n")

    print(f"Created {args.name} at {target}")
    print("Next: npm install && npm run typecheck && npm test && pi -e .")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
