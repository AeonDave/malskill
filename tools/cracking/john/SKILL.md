---
name: john
description: "CPU-based password cracker supporting hundreds of hash formats with wordlist, rules, and incremental modes. Use when cracking hashes offline with CPU resources, applying mangling rules, or when GPUs are unavailable."
license: MIT
compatibility: "Linux/macOS/Windows; apt install john or build from source (Openwall)"
metadata:
  author: AeonDave
  version: "1.0"
---

# John the Ripper

CPU password cracker — hundreds of hash formats, wordlist + rules + incremental.

## Quick Start

```bash
# Auto-detect format and crack
john hashes.txt --wordlist=/usr/share/wordlists/rockyou.txt

# Show cracked passwords
john hashes.txt --show

# Single crack mode (fast, username-based)
john hashes.txt --single

# Incremental (brute-force)
john hashes.txt --incremental
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--wordlist=FILE` | Dictionary attack |
| `--rules[=RULE]` | Apply mangling rules |
| `--format=TYPE` | Force hash format |
| `--single` | Single crack (username hints) |
| `--incremental` | Brute-force |
| `--show` | Display cracked passwords |
| `--pot=FILE` | Custom pot file |
| `--fork=N` | Parallel processes |
| `--list=formats` | List all formats |

## Common Workflows

**NTLM with rules:**
```bash
john ntlm.txt --format=NT --wordlist=rockyou.txt --rules=best64
```

**SSH private key:**
```bash
ssh2john id_rsa > id_rsa.hash
john id_rsa.hash --wordlist=rockyou.txt
```

**Zip archive:**
```bash
zip2john archive.zip > zip.hash
john zip.hash --wordlist=rockyou.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Rule syntax and format list |
