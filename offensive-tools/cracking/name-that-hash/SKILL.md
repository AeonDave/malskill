---
name: name-that-hash
description: "Auth/lab ref: hash-identification helper for narrowing candidate algorithms before cracking."
compatibility: "Linux, macOS, Windows; Python 3."
metadata:
  author: AeonDave
  version: "1.0"
---

# Name-That-Hash

Cheap ambiguity reduction before you waste hours cracking the wrong thing.

## When to use Name-That-Hash

Use it when you need to:

- identify likely algorithms for unknown hash strings
- distinguish similar-looking formats before choosing a cracking mode
- generate a short candidate list for `john` or `hashcat`

## Quick Start

```bash
# Identify a single hash
name-that-hash 5f4dcc3b5aa765d61d8327deb882cf99

# Short alias if installed
nth 5f4dcc3b5aa765d61d8327deb882cf99
```

## Practical Workflow

1. Feed the observed hash string to the tool.
2. Review the ranked candidate algorithms.
3. Use surrounding context to prune the list: length, prefix, salt markers, application source.
4. Pass the best candidate into `john` or `hashcat` with an explicit format/mode.

## Practical Notes

- Identification is strongest when you also know the source application or file type.
- Treat output as candidate ranking, not certainty.
- Combine with archive/file-specific extractors such as `zip2john`, `keepass2john`, or PDF tools when the source is known.

## Caveats

- Many formats share the same length and alphabet.
- Salted, truncated, or application-wrapped hashes can confuse generic identification.
- Do not skip context; it is often more valuable than the string alone.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the upstream project docs for current aliases, input modes, and output interpretation.
