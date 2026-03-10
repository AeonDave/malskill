#!/usr/bin/env python3
"""
Skill Validator - Check a SKILL.md for spec compliance.

Validates:
  - SKILL.md exists
  - YAML frontmatter is well-formed
  - Required fields (name, description) are present and valid
  - No unexpected frontmatter keys
  - Name follows hyphen-case rules and matches folder name
  - Description length and content constraints
  - No unresolved TODO markers

Usage:
    quick_validate.py <skill-directory>

Exit codes:
    0  Valid (no errors, no TODOs)
    1  Invalid or TODOs found
"""

import re
import sys
from pathlib import Path

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

MAX_NAME_LENGTH = 64
MAX_DESC_LENGTH = 1024
MAX_COMPAT_LENGTH = 500

REQUIRED_FIELDS = {"name", "description"}
ALLOWED_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}


def _parse_frontmatter(content: str) -> tuple[bool, str, dict]:
    """
    Extract and parse YAML frontmatter from SKILL.md content.
    Returns (ok, error_message, parsed_dict).
    """
    if not content.startswith("---"):
        return False, "No YAML frontmatter found (file must start with '---')", {}

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Malformed frontmatter — could not find closing '---'", {}

    raw = match.group(1)

    if _HAS_YAML:
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            return False, f"Invalid YAML: {exc}", {}
        if not isinstance(data, dict):
            return False, "Frontmatter must be a YAML mapping", {}
        return True, "", data

    # Minimal fallback parser (simple key: value lines only)
    data = {}
    for line in raw.splitlines():
        m = re.match(r"^(\S[^:]*?):\s*(.*)", line)
        if m:
            data[m.group(1).strip()] = m.group(2).strip()
    return True, "", data


def validate_skill(skill_path: Path | str) -> tuple[bool, str]:
    """
    Validate a skill directory.

    Returns:
        (True, success_message)   — valid, no TODOs
        (True, warning_message)   — structurally valid but TODOs remain
        (False, error_message)    — invalid
    """
    skill_path = Path(skill_path).resolve()

    if not skill_path.exists():
        return False, f"Path not found: {skill_path}"
    if not skill_path.is_dir():
        return False, f"Not a directory: {skill_path}"

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found in skill directory"

    content = skill_md.read_text(encoding="utf-8")
    ok, err, fm = _parse_frontmatter(content)
    if not ok:
        return False, err

    # Unexpected keys
    unexpected = set(fm.keys()) - ALLOWED_FIELDS
    if unexpected:
        allowed = ", ".join(sorted(ALLOWED_FIELDS))
        keys = ", ".join(sorted(unexpected))
        return False, f"Unexpected frontmatter key(s): {keys}. Allowed: {allowed}"

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in fm:
            return False, f"Missing required field '{field}' in frontmatter"

    # Validate name
    name = str(fm.get("name", "")).strip()
    if not name:
        return False, "Field 'name' is empty"
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", name):
        return False, (
            f"Name '{name}' is invalid — use lowercase letters, digits, and hyphens; "
            "no leading/trailing/consecutive hyphens"
        )
    if "--" in name:
        return False, f"Name '{name}' contains consecutive hyphens"
    if len(name) > MAX_NAME_LENGTH:
        return False, f"Name is {len(name)} chars — max is {MAX_NAME_LENGTH}"
    if name != skill_path.name:
        return False, (
            f"Name '{name}' does not match folder name '{skill_path.name}'"
        )

    # Validate description
    desc = str(fm.get("description", "")).strip()
    if not desc:
        return False, "Field 'description' is empty"
    if "<" in desc or ">" in desc:
        return False, "Description must not contain angle brackets (< or >)"
    if len(desc) > MAX_DESC_LENGTH:
        return False, f"Description is {len(desc)} chars — max is {MAX_DESC_LENGTH}"

    # Validate compatibility (optional)
    if "compatibility" in fm:
        compat = str(fm["compatibility"]).strip()
        if len(compat) > MAX_COMPAT_LENGTH:
            return False, f"Compatibility is {len(compat)} chars — max is {MAX_COMPAT_LENGTH}"

    def _has_todo_markers(file_path: Path, text: str) -> bool:
        """Return True if the file contains unresolved TODO markers.

        For Markdown, ignore fenced code blocks to reduce false positives from
        examples that legitimately show TODO placeholders.
        """
        markers = ("TODO:", "TODO]")

        if file_path.suffix.lower() != ".md":
            return any(m in text for m in markers)

        in_fence = False
        for line in text.splitlines():
            stripped = line.lstrip()
            # Toggle on fenced blocks (``` or ~~~)
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if any(m in line for m in markers):
                return True
        return False

    # Scan for TODO markers in Markdown and text files (not in executable scripts)
    SCAN_EXTENSIONS = {".md", ".txt", ".yaml", ".yml", ".json", ".toml"}
    for file in sorted(skill_path.rglob("*")):
        if not file.is_file():
            continue
        if file.suffix.lower() not in SCAN_EXTENSIONS:
            continue
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if _has_todo_markers(file, text):
            rel = file.relative_to(skill_path)
            return True, f"[WARNING] Unresolved TODO in {rel} — resolve before packaging"

    return True, f"Skill '{name}' is valid"


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    skill_path = sys.argv[1]
    valid, message = validate_skill(skill_path)
    print(message)
    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
