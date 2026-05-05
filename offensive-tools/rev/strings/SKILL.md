---
name: strings
description: "strings: printable-string extractor for binaries, libraries, firmware blobs, and files of unknown type. Use when you need a fast first pass for URLs, paths, flags, format strings, compiler banners, crypto material, or embedded configuration before deeper reversing."
compatibility: "Linux, macOS, WSL; GNU binutils or BSD variant available on most systems"
metadata:
  author: AeonDave
  version: "1.0"
---

# strings

The fastest first question in reversing is often: what human text escaped alive?

## When to use strings

Use strings when you need to:

- surface URLs, domains, file paths, and command lines quickly
- hunt for flags, prompts, keys, or configuration fragments
- identify a binary's language/runtime from embedded banners
- find likely function names or imported library references in stripped samples

## Quick Start

```bash
# Default printable-string extraction
strings ./sample.bin

# Show offsets in hex
strings -t x ./sample.bin

# Require longer strings to reduce noise
strings -n 8 ./sample.bin
```

## High-Value Workflows

### Focused triage

```bash
strings -a -n 6 ./sample.bin | grep -iE "flag|http|token|password|/bin/|cmd.exe"
strings -a -t x ./sample.bin | grep -i libc
```

### Wide or alternate encodings

```bash
strings -a -e l ./sample.bin
strings -a -e b ./sample.bin
```

### Batch file-origin context

```bash
strings -f -a *.so
```

## Practical Notes

- `-a` is a safer default when you want to scan the whole file, not only data sections.
- Pair offsets from `-t x` with `objdump`, `gdb`, or a GUI disassembler for contextual follow-up.
- Try both regular and wide-string modes on Windows or Android artifacts.

## Caveats

- Missing strings do not imply missing capability; malware and packed binaries hide text all the time.
- `strings` can produce seductive nonsense on compressed or encrypted data.
- Use it as a lead generator, not as final evidence.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the platform `man strings` page for encoding flags and variant-specific behavior.
