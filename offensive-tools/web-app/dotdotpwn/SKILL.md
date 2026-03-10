---
name: dotdotpwn
description: "Directory traversal vulnerability fuzzer for web servers and applications. Use when testing for path traversal and LFI vulnerabilities across HTTP, FTP, and TFTP services."
license: MIT
compatibility: "Perl; Linux/macOS; apt install dotdotpwn; github.com/wireghoul/dotdotpwn"
metadata:
  author: AeonDave
  version: "1.0"
---

# DotDotPwn

Directory traversal fuzzer — test for path traversal across HTTP, FTP, TFTP.

## Quick Start

```bash
apt install dotdotpwn

# HTTP traversal
dotdotpwn -m http -h target.com -x 80

# HTTP with specific URL
dotdotpwn -m http -h target.com -U "http://target.com/page?file=TRAVERSAL"

# FTP
dotdotpwn -m ftp -h target.com -x 21 -u user -p pass
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-m MODULE` | Module: http/http-url/ftp/tftp/payload |
| `-h HOST` | Target host |
| `-x PORT` | Target port |
| `-U URL` | URL with TRAVERSAL placeholder |
| `-u USER` | Username (FTP) |
| `-p PASS` | Password (FTP) |
| `-f FILE` | Target file (e.g., `/etc/passwd`) |
| `-d N` | Traversal depth (default: 6) |
| `-t N` | Time between requests (ms) |
| `-q` | Quiet mode |
| `-s` | Stop on first found |

## Common Workflows

**HTTP-URL traversal with custom path:**
```bash
dotdotpwn -m http-url -h target.com -U "http://target.com/download.php?file=TRAVERSAL" -f /etc/passwd -d 8 -q
```

**Windows target:**
```bash
dotdotpwn -m http -h target.com -f "windows/system32/cmd.exe" -d 6
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Encoding bypass and Windows path notes |
