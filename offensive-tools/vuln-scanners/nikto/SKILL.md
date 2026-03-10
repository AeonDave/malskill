---
name: nikto
description: "Nikto: open-source web server scanner checking for 6700+ known vulnerabilities, outdated software, misconfigurations, and dangerous CGI/default files. Use when performing quick web server reconnaissance to identify low-hanging fruit, server banners, and default content before deeper manual testing."
license: GPL-2.0
compatibility: "Linux / macOS / Windows (Perl 5). Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.0"
---

# Nikto

Web server vulnerability and misconfiguration scanner.

## Quick Start

```bash
nikto -h http://target.com
nikto -h https://target.com -ssl
nikto -h target.com -p 8443 -o nikto.txt -Format txt
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-h <host>` | Target host/URL |
| `-p <port>` | Port (default 80/443) |
| `-ssl` | Force SSL |
| `-id <user:pass>` | HTTP basic auth |
| `-useproxy <proxy>` | Route through proxy |
| `-Tuning <n>` | Scan tuning bitmask |
| `-o <file>` | Output file |
| `-Format <fmt>` | csv / txt / xml / html |

## Tuning Values

| Value | Meaning |
|-------|---------|
| 1 | Interesting files |
| 2 | Misconfiguration |
| 3 | Info disclosure |
| 4 | XSS injection |
| 8 | Command execution |
| 9 | SQL injection |

## Resources

| File | When to load |
|------|--------------|
| `references/` | Plugin list, auth bypass techniques |
