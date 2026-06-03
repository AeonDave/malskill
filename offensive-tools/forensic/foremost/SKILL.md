---
name: foremost
description: "Auth/lab ref: file carving from disk images, raw media, and damaged data; headers/footers, recovery workflow, evidence handling."
compatibility: "Linux, macOS, WSL; CLI-focused; works on raw files and images."
metadata:
  author: AeonDave
  version: "1.0"
---

# Foremost

Header-footer carving for the moment when structure is gone but signatures remain.

## When to use Foremost

Use Foremost when you need to:

- recover common file types from a raw image or dump
- triage a large blob quickly before deeper filesystem work
- carve likely loot from partially corrupted or unmounted data

## Quick Start

```bash
# Carve common default types
foremost image.dd -o carve_out

# Restrict to selected types
foremost image.dd -t jpg,png,pdf,zip -o carve_out
```

## Practical Notes

- Start with a narrow type set when you already know what you want; it reduces noise and disk churn.
- Foremost is great for first-pass recovery, but not a substitute for filesystem-aware tools.
- Review output names and offsets carefully; carved files often lose original metadata and paths.

## Caveats

- Header/footer carving can recover fragments, duplicates, or false positives.
- Large images can produce a lot of junk if you carve every supported type.
- Filesystem context, timestamps, and original names usually do not survive.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the local config and man page for file-type signatures and custom carving behavior.
