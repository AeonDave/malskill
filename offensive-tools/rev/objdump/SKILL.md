---
name: objdump
description: "Auth/lab ref: binutils inspection and disassembly tool for ELF and many other object formats."
compatibility: "Linux, macOS, WSL; part of GNU binutils; strongest on ELF workflows."
metadata:
  author: AeonDave
  version: "1.0"
---

# objdump

Quick static inspection and disassembly without firing up a full GUI. Tiny hammer, surprisingly sharp.

## When to use objdump

Use objdump when you need to:

- disassemble code sections quickly from a shell
- inspect headers, sections, relocations, or symbol tables
- dump raw bytes from a section like `.rodata` or `.text`
- compare compiler output or verify what a packer/stub changed

## Quick Start

```bash
# Disassemble executable sections
objdump -d ./chall

# Disassemble all sections, not just code-marked ones
objdump -D ./chall

# Intel syntax on x86/x86-64
objdump -d -Mintel ./chall
```

## High-Value Workflows

### Code and symbols

```bash
objdump -d -Mintel ./chall
objdump -t ./chall
objdump -T ./chall
objdump -x ./chall
```

### Dump interesting data sections

```bash
objdump -s -j .rodata ./chall
objdump -s -j .data ./chall
```

### Mixed source plus assembly for local builds

```bash
objdump -S -Mintel ./chall
```

## Practical Notes

- Prefer `readelf` when you need canonical ELF metadata rather than a friendlier summary.
- `-D` is useful for hand-marked shellcode regions or strange packer output where section flags lie.
- Pair `objdump -s -j .rodata` with `strings` when looking for nearby format strings, keys, or banners.

## Caveats

- objdump is a disassembler, not a decompiler.
- Linear disassembly can mislead on embedded data or obfuscated control flow.
- For stripped or heavily optimized code, combine with `gdb`, `strings`, and `readelf` instead of trusting a single view.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the GNU binutils manual for architecture-specific `-M` options and file-format nuances.
