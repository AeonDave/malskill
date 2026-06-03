---
name: john
description: "Auth/lab ref: CPU-based password cracker supporting hundreds of hash formats with wordlist, rules, and incremental modes."
license: MIT
compatibility: "Linux/macOS/Windows."
metadata:
  author: AeonDave
  version: "1.1"
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

**PDF:**
```bash
pdf2john document.pdf > pdf.hash
john pdf.hash --wordlist=rockyou.txt
```

**KeePass database:**
```bash
keepass2john database.kdbx > kp.hash
john kp.hash --wordlist=rockyou.txt
```

**Office documents (docx/xlsx):**
```bash
office2john document.docx > office.hash
john office.hash --wordlist=rockyou.txt
```

**7-Zip:**
```bash
7z2john archive.7z > 7z.hash
john 7z.hash --wordlist=rockyou.txt
```

## Session Management

```bash
# Named session
john hashes.txt --wordlist=rockyou.txt --session=mysession

# Resume
john --restore=mysession

# Check status of running session (send USR1 signal or press 'q')
john --status=mysession
```

## Parallel Cracking

```bash
# Fork N processes (uses all CPU cores)
john hashes.txt --wordlist=rockyou.txt --fork=4
```

## Custom Rules (inline in john.conf)

```ini
[List.Rules:MyRules]
# Append year variants
Az"[0-9][0-9][0-9][0-9]"
# Capitalize first + append !
c Az"!"
# l33t substitutions
sa@ se3 si1 so0
```

```bash
john hashes.txt --wordlist=rockyou.txt --rules=MyRules
```

## Resources

| File | When to load |
|------|--------------|
| `references/formats-and-rules.md` | Supported format names, *2john tool list, rule syntax reference |
