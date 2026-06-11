#!/usr/bin/env python3
"""Create the standard case directory structure for malware analysis.

Usage:
    python create_case.py [case-name]

Creates: ./case-name/ with numbered evidence directories and empty
AGENTS.md + REPORT.md files.
"""

import sys
from pathlib import Path

DIRS = [
    "00-intake",
    "01-triage",
    "02-strings",
    "03-static",
    "04-decoding",
    "05-config",
    "06-extracted",
    "07-stages",
    "08-yara",
    "09-reports",
    "10-iocs",
    "11-notes",
]

AGENTS_TEMPLATE = """# Case: {name}

## Current Summary

[To be filled during analysis]

## Sample Inventory

| # | Filename | SHA256 | Type | Source |
|---|----------|--------|------|--------|
| 1 | | | | intake |

## Environment And Tooling

- Platform:
- Available tools:
- Missing tools:

## Timeline

- [ ] Intake and hashing
- [ ] String extraction
- [ ] Metadata and structure
- [ ] Reverse engineering
- [ ] Entropy analysis
- [ ] Config / IOC extraction
- [ ] Family attribution
- [ ] Report

## Confirmed Findings

## Decoders And Algorithms

## Family Attribution

## Evidence Index

## Open Questions

## Next Actions
"""

REPORT_TEMPLATE = """# Malware Analysis Report: {name}

## Case Summary

## Sample Inventory

| Filename | MD5 | SHA1 | SHA256 | Type | Role |
|----------|-----|------|--------|------|------|

## Execution / Compromise Chain

## Indicators of Compromise

### URLs

### Domains

### IP Addresses

### File Hashes

## Obfuscation / Protection

## Persistence

## Decoding / Decryption Logic

## Family Assessment

## Confidence and Limitations
"""


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "case"
    root = Path(name)

    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
        print(f"  [OK] {root / d}")

    (root / "AGENTS.md").write_text(AGENTS_TEMPLATE.format(name=name))
    (root / "REPORT.md").write_text(REPORT_TEMPLATE.format(name=name))
    print(f"  [OK] {root / 'AGENTS.md'}")
    print(f"  [OK] {root / 'REPORT.md'}")
    print(f"\nCase directory created: {root.resolve()}")


if __name__ == "__main__":
    main()
