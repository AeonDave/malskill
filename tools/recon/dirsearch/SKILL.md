---
name: dirsearch
description: "Web path scanning and directory brute-forcing with recursive scanning and multi-extension support. Use when enumerating web server content, finding hidden endpoints, and discovering backup or config files."
license: MIT
compatibility: "Python 3; pip install dirsearch; Linux/macOS/Windows; github.com/maurosoria/dirsearch"
metadata:
  author: AeonDave
  version: "1.0"
---

# Dirsearch

Web directory and file brute-forcer with recursion, extensions, and proxy support.

## Quick Start

```bash
pip install dirsearch

# Basic scan
dirsearch -u https://target.com

# With extensions
dirsearch -u https://target.com -e php,asp,aspx,bak,txt

# Recursive
dirsearch -u https://target.com -r

# Output to file
dirsearch -u https://target.com -o results.txt
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u URL` | Target URL |
| `-e EXT` | Extensions (comma-separated) |
| `-w FILE` | Custom wordlist |
| `-r` | Recursive scanning |
| `-R N` | Max recursion depth |
| `-t N` | Threads (default: 25) |
| `-x CODES` | Exclude status codes |
| `--proxy URL` | HTTP proxy |
| `-o FILE` | Output file |
| `--format FORMAT` | plain/json/xml/md |

## Common Workflows

**PHP app scan with backups:**
```bash
dirsearch -u https://target.com -e php,bak,old,txt,zip -r -t 30
```

**Exclude 404s and noise:**
```bash
dirsearch -u https://target.com -x 404,403,301
```

**API path discovery:**
```bash
dirsearch -u https://api.target.com -w /usr/share/seclists/Discovery/Web-Content/api/api-endpoints.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Wordlist selection and recursion tuning |
