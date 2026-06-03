---
name: readelf
description: "Auth/lab ref: ELF metadata inspection utility for headers, sections, program headers, symbols, notes, relocations, and dynamic entries."
compatibility: "Linux, macOS, WSL; part of GNU binutils; ELF-only by design."
metadata:
  author: AeonDave
  version: "1.0"
---

# readelf

Authoritative ELF structure inspection. When in doubt, trust the headers.

## When to use readelf

Use readelf when you need to:

- verify ELF type, entry point, and architecture
- inspect sections, segments, dynamic libraries, or relocations
- confirm PIE, interpreter path, and symbol visibility details
- understand what the loader sees before patching or exploiting

## Quick Start

```bash
# ELF header
readelf -h ./chall

# Program headers and interpreter
readelf -l ./chall

# Dynamic section
readelf -d ./chall
```

## High-Value Workflows

### Sections, symbols, and relocations

```bash
readelf -S ./chall
readelf -Ws ./chall
readelf -r ./chall
```

### Notes, build IDs, and hardening clues

```bash
readelf -n ./chall
readelf -l ./chall
```

### Shared-library dependencies

```bash
readelf -d ./chall | grep NEEDED
readelf -d ./chall | grep -E "RPATH|RUNPATH|SONAME"
```

## Practical Notes

- Use `readelf -l` to confirm the PT_INTERP path before touching `patchelf`.
- `readelf -d` is the fastest way to answer libc and loader dependency questions.
- `readelf -Ws` helps explain why `objdump` or a debugger did or did not recover symbols.

## Caveats

- `readelf` shows structure, not runtime values after relocation.
- It is ELF-only; use `objdump` or platform-native tooling for PE/Mach-O.
- For exploitability triage, combine with `checksec` and runtime observation.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the GNU binutils documentation for less common flags like versioning, unwind info, and debug-section inspection.
