---
name: zsteg
description: "zsteg: PNG and BMP steganography analyzer for bit-plane, color-channel, and payload extraction. Use when hunting LSB-style hidden data in images, especially after basic metadata and strings checks show nothing useful."
compatibility: "Linux, macOS, WSL; Ruby gem; strongest on PNG and BMP"
metadata:
  author: AeonDave
  version: "1.0"
---

# zsteg

Bit-plane spelunking for images that are too quiet on the surface.

## When to use zsteg

Use zsteg when you need to:

- scan PNG/BMP files for common LSB and channel-hiding tricks
- enumerate embedded payload candidates quickly
- extract a promising payload for deeper analysis

## Quick Start

```bash
# Automatic scan
zsteg -a image.png

# Default inspection
zsteg image.png
```

## High-Value Workflows

### Extract a specific candidate

```bash
zsteg -E "b1,r,lsb,xy" image.png > payload.bin
```

### Broad PNG/BMP triage

1. Run `zsteg -a`.
2. Review human-readable hits first.
3. Extract promising payloads with `-E`.
4. Feed extracted bytes into `file`, `strings`, `foremost`, or archive tools.

## Practical Notes

- zsteg shines on PNG/BMP artifacts; JPEG-focused suspects usually belong to other workflows.
- Not every hit is meaningful; short text fragments and compressed junk both show up.
- Pair with `steghide`, `stegseek`, and normal image triage rather than betting everything on one pass.

## Caveats

- False positives are common on busy or large images.
- The interesting payload may need decompression or decoding after extraction.
- Channel/bit-order choice matters; extraction without context can mislead.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the upstream README for extractor spec syntax and advanced scan flags.
