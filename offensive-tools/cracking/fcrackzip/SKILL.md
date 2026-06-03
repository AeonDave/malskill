---
name: fcrackzip
description: "Auth/lab ref: ZIP password-cracking utility for dictionary and brute-force testing. For you need a focused CLI workflow against password-protected ZIP archives before escalating to heavier cracking stacks."
compatibility: "Linux, macOS, WSL; package-manager friendly; ZIP archives only."
metadata:
  author: AeonDave
  version: "1.0"
---

# fcrackzip

Specialist ZIP password cracking with less ceremony than the bigger frameworks.

## When to use fcrackzip

Use fcrackzip when you need to:

- test a ZIP archive against a wordlist quickly
- brute-force a narrow password space for ZIP only
- verify whether a known candidate password opens the archive

## Quick Start

```bash
# Dictionary attack and verify extraction
fcrackzip -D -p rockyou.txt -u archive.zip

# Brute-force simple character sets
fcrackzip -b -c 1aA -l 1-8 -u archive.zip
```

## Practical Notes

- `-u` verifies the password against unzip logic instead of only reporting a guess.
- Start with a dictionary attack unless you have strong evidence the keyspace is tiny.
- If the archive source is known, build targeted masks before going full brute force.

## Caveats

- ZIP-only specialization is its strength and its boundary.
- Brute force becomes painful fast; switch to better-targeted tooling when entropy rises.
- Some workflows are better served by `john` or `hashcat` once you extract the relevant hash material.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the local man page for charset syntax and mode details.
