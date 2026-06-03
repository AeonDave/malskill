---
name: upx
description: "Auth/lab ref: executable packer and unpacker for PE, ELF, Mach-O, and several embedded formats."
compatibility: "Linux, Windows, macOS; standalone binary; supports many executable formats."
metadata:
  author: AeonDave
  version: "1.0"
---

# UPX

Practical executable packing. In reversing, it is usually the wrapper you remove before the real work begins.

## When to use UPX

Use UPX when you need to:

- detect and unpack standard UPX-packed malware or challenge binaries
- inspect packing status and compression metadata quickly
- repack a controlled binary for transport or lab exercises

## Quick Start

```bash
# Inspect packing info
upx -l sample.bin

# Unpack in place
upx -d sample.bin

# Write unpacked output elsewhere
upx -d sample.bin -o sample.unpacked
```

## High-Value Workflows

### Unpack before analysis

```bash
upx -d sample.bin
file sample.bin
strings -n 8 sample.bin
```

### Controlled repack for lab artifacts

```bash
upx -9 tool.bin
upx --best --lzma tool.bin
```

## Practical Notes

- Always hash before and after unpacking so later evidence chains stay clean.
- After unpacking, re-run `file`, `readelf`, `objdump`, and `strings` because the sample's surface changes dramatically.
- If `upx -d` fails, the target may be modified, corrupted, or only UPX-like.

## Caveats

- Not every packed sample is unpackable with stock UPX.
- Repacking changes file hashes and may trigger different runtime behavior in security tooling.
- UPX support varies by target format and version; read the tool's error messages carefully.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the official UPX docs for supported formats, compression modes, and troubleshooting.
