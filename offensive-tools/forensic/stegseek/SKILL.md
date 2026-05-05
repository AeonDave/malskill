---
name: stegseek
description: "Stegseek: high-speed wordlist attacker for steghide-protected files. Use when you suspect a JPEG/BMP/WAV/AU artifact contains steghide data but extraction is blocked by a passphrase."
compatibility: "Linux primary; optimized for steghide-compatible files"
metadata:
  author: AeonDave
  version: "1.0"
---

# Stegseek

The fast lane for steghide passphrase guessing.

## When to use Stegseek

Use Stegseek when you need to:

- attack a suspected steghide carrier with a wordlist
- recover the passphrase or extract the hidden payload quickly
- validate whether a JPEG/BMP/WAV/AU file is worth deeper stego effort

## Quick Start

```bash
# Try a wordlist against a carrier
stegseek image.jpg rockyou.txt
```

## Practical Workflow

1. Confirm the file is plausibly steghide-related.
2. Run Stegseek with a good candidate wordlist.
3. If a passphrase is found, verify extraction and inspect the recovered payload.
4. If nothing lands, revisit assumptions about format and stego family.

## Practical Notes

- This tool is purpose-built for steghide scenarios, so use it there first.
- Pair with `steghide info` or prior challenge hints before assuming the wordlist is the problem.
- Recovery speed is its selling point; let it answer the obvious question early.

## Caveats

- Not every image with hidden data is a steghide target.
- A strong passphrase still wins.
- Success only gets you the payload; you still need to analyze what comes out.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the upstream project docs for extraction behavior, output handling, and troubleshooting.
