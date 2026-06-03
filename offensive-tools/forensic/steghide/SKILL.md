---
name: steghide
description: "Auth/lab ref: steghide JPEG/BMP/WAV/AU hidden-data workflows; embed/extract tests, passphrase handling, challenge evidence."
compatibility: "Linux, macOS, WSL; package-manager friendly; classic steghide-supported formats."
metadata:
  author: AeonDave
  version: "1.0"
---

# steghide

Classic hidden-payload tooling for media files that look innocent until they absolutely do not.

## When to use steghide

Use steghide when you need to:

- check supported cover files for hidden payloads
- extract content with or without a candidate passphrase
- embed a test payload into a supported media file in a lab workflow

## Quick Start

```bash
# Inspect carrier info
steghide info image.jpg

# Extract hidden payload
steghide extract -sf image.jpg

# Embed data into a cover file
steghide embed -cf cover.jpg -ef secret.txt
```

## Practical Notes

- `info` is a good first move before guessing wildly.
- Pair with `stegseek` when the artifact is likely a steghide file protected by a weak passphrase.
- Keep original carrier hashes if the artifact matters for evidence or writeups.

## Caveats

- Format support is narrower than generic stego folklore suggests.
- Extraction success may still depend on the correct passphrase.
- Unsupported or visually suspicious files may belong to a different stego family entirely.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the local man page for embedding parameters, compression, and encryption options.
