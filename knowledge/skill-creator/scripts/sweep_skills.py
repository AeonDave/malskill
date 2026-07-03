#!/usr/bin/env python3
"""Sweep a category dir (or single skill dir) for hygiene issues.

Complements quick_validate.py (frontmatter/description) and
check_changed_files.py (final newline + git-diff whitespace).

Checks per markdown file under the target root:
  - broken relative .md links
  - placeholder markers (TODO / FIXME / XXX / TBD / WIP)
  - CTF-idiom leakage in non-CTF contexts (root.txt / user.txt / HTB{ /
    HackTheBox / TryHackMe) — off by default; enable with --ctf-check
  - workstation-path leakage (C:\\Users\\<user>, /home/<user>, /Users/<user>)
  - file size distribution (smallest/largest N)

Usage:
  python sweep_skills.py <path>
  python sweep_skills.py offensive-techniques --ctf-check --top 5

Exit codes:
  0 = clean or informational-only
  1 = broken links or workstation paths found
  2 = argument error
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Iterable

# Placeholder markers we treat as unresolved gaps.
_PLACEHOLDER_RE = re.compile(r"\b(TODO|FIXME|XXX|TBD|WIP)\b")

# Markdown relative-link matcher. Skips fenced anchors / non-.md targets.
_MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#]+?\.md)(#[^)]*)?\)")

# CTF-idiom markers. Legitimate in offensive-ctf/, wrong elsewhere.
_CTF_PATTERNS = [
    r"\broot\.txt\b",
    r"\buser\.txt\b",
    r"HTB\{",
    r"HackTheBox",
    r"TryHackMe",
]

# Real workstation-path patterns. Avoids the classic false positives
# (port-forward syntax like R:1080, protocol tags like U:47808, CVSS
# vectors like V:N, register names). Requires a username after the
# home-dir prefix and a word boundary.
_WORKSTATION_PATH_RE = re.compile(
    r"[A-Za-z]:[/\\]Users[/\\]\w+"
    r"|/home/[a-z][a-z0-9_-]{2,}(?![a-z0-9_-])"
    r"|/Users/[A-Z][a-z0-9_-]{2,}(?![a-z0-9_-])"
)

# Well-known non-workstation paths. Match the FULL hit (case-insensitive)
# against this set to filter false positives before reporting.
_WORKSTATION_PATH_ALLOWLIST = {
    # HP JetDirect / PJL default user account
    "/home/default",
    # Windows built-in profiles
    r"c:\users\public",
    r"c:\users\default",
    r"c:\users\all users",
    r"c:\users\administrator",
    r"c:\users\defaultuser0",
    # Common example accounts in security literature
    r"c:\users\user",
}


def _iter_md(root: pathlib.Path) -> Iterable[pathlib.Path]:
    if root.is_file() and root.suffix == ".md":
        yield root
        return
    for md in sorted(root.rglob("*.md")):
        yield md


def _rel(p: pathlib.Path) -> str:
    try:
        return str(p.relative_to(pathlib.Path.cwd()))
    except ValueError:
        return str(p)


def sweep(root: pathlib.Path, *, ctf_check: bool, top: int) -> int:
    broken: list[tuple[str, str]] = []
    placeholders: list[tuple[str, str, int]] = []
    ctf_hits: list[tuple[str, str]] = []
    ws_paths: list[tuple[str, str]] = []
    sizes: dict[str, int] = {}

    for md in _iter_md(root):
        try:
            txt = md.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            print(f"read_error {md}: {e}", file=sys.stderr)
            continue
        rel = _rel(md)
        sizes[rel] = len(txt)

        for m in _MD_LINK_RE.finditer(txt):
            link = m.group(1)
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            target = (md.parent / link).resolve()
            if not target.exists():
                broken.append((rel, link))

        for m in _PLACEHOLDER_RE.finditer(txt):
            line_no = txt.count("\n", 0, m.start()) + 1
            placeholders.append((rel, m.group(0), line_no))

        if ctf_check:
            seen: set[str] = set()
            for pat in _CTF_PATTERNS:
                if re.search(pat, txt) and pat not in seen:
                    seen.add(pat)
                    ctf_hits.append((rel, pat))

        for m in _WORKSTATION_PATH_RE.finditer(txt):
            hit = m.group(0)
            if hit.lower().replace("/", "\\") in _WORKSTATION_PATH_ALLOWLIST or hit.lower() in _WORKSTATION_PATH_ALLOWLIST:
                continue
            ws_paths.append((rel, hit))

    print(f"scanned {len(sizes)} markdown file(s) under {_rel(root)}")

    print(f"\nbroken_md_links = {len(broken)}")
    for rel, link in broken:
        print(f"  {rel} -> {link}")

    print(f"\nplaceholder_markers = {len(placeholders)}")
    for rel, tag, line_no in placeholders:
        print(f"  {rel}:{line_no} :: {tag}")

    if ctf_check:
        print(f"\nctf_idiom_hits = {len(ctf_hits)}")
        for rel, pat in ctf_hits:
            print(f"  {rel} :: {pat}")

    print(f"\nworkstation_paths = {len(ws_paths)}")
    for rel, hit in ws_paths:
        print(f"  {rel} :: {hit}")

    if sizes:
        ranked = sorted(sizes.items(), key=lambda kv: kv[1])
        print(f"\nsize distribution (chars):")
        print(f"  smallest {min(top, len(ranked))}:")
        for rel, size in ranked[:top]:
            print(f"    {size:7d}  {rel}")
        if len(ranked) > top:
            print(f"  largest {min(top, len(ranked))}:")
            for rel, size in ranked[-top:]:
                print(f"    {size:7d}  {rel}")

    # workstation_paths findings often need human triage (well-known
    # example paths, PDB strings in malware writeups, etc.), so they do
    # not fail the exit code — only broken links do.
    return 1 if broken else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="skill dir, category dir, or single .md file")
    parser.add_argument(
        "--ctf-check",
        action="store_true",
        help="report CTF-idiom leakage (use for non-CTF trees)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="how many smallest/largest files to list (default 10)",
    )
    args = parser.parse_args(argv)

    root = pathlib.Path(args.path)
    if not root.exists():
        print(f"path not found: {root}", file=sys.stderr)
        return 2
    return sweep(root, ctf_check=args.ctf_check, top=args.top)


if __name__ == "__main__":
    sys.exit(main())
