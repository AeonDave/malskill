---
name: nikto
description: "Nikto: open-source web server scanner checking for 6700+ known vulnerabilities, outdated software, misconfigurations, and dangerous CGI/default files. Use when performing quick web server reconnaissance to identify low-hanging fruit, server banners, default content, and misconfigs before deeper manual testing. Fast, noisy — good for CTF/authorized pentests."
license: GPL-2.0
compatibility: "Linux / macOS / Windows (Perl 5). Pre-installed on Kali. Install: apt install nikto / brew install nikto."
metadata:
  author: AeonDave
  version: "1.1"
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
| `-useproxy <proxy>` | Route through proxy (e.g., `127.0.0.1:8080`) |
| `-Tuning <n>` | Scan tuning bitmask (see below) |
| `-Plugins <list>` | Run specific plugins |
| `-evasion <n>` | IDS evasion technique (see below) |
| `-timeout <n>` | Timeout per request (default 10s) |
| `-pause <n>` | Pause between requests (stealth) |
| `-maxtime <n>` | Max scan time in seconds |
| `-o <file>` | Output file |
| `-Format <fmt>` | csv / txt / xml / html / json |
| `-C all` | Check all CGI dirs |
| `-nossl` | Disable SSL |
| `-no404` | Disable 404 guess detection |
| `-followredirects` | Follow HTTP redirects |
| `-mutate <n>` | Guess additional file names |
| `-update` | Update plugins/databases |

## Tuning Values

Combine with `+` or `-` to include/exclude:

| Value | Meaning |
|-------|---------|
| `0` | File upload |
| `1` | Interesting files / seen in logs |
| `2` | Misconfiguration / default files |
| `3` | Information disclosure |
| `4` | Injection (XSS/Script) |
| `5` | Remote file retrieval — inside web root |
| `6` | Denial of service |
| `7` | Remote file retrieval — server-wide |
| `8` | Command execution / remote shell |
| `9` | SQL injection |
| `a` | Authentication bypass |
| `b` | Software identification |
| `c` | Remote source inclusion |
| `x` | Reverse tuning (exclude selected) |

```bash
# Most useful combo: misconfigs + info disclosure + SQLi + XSS
nikto -h http://target.com -Tuning 234489a

# Aggressive: all checks
nikto -h http://target.com -Tuning 0123456789abc

# Skip DoS (safe for production):
nikto -h http://target.com -Tuning x6
```

## IDS Evasion Techniques

| Value | Technique |
|-------|-----------|
| `1` | Random URI encoding |
| `2` | Directory self-reference (/./) |
| `3` | Premature URL ending |
| `4` | Prepend long random string |
| `5` | Fake parameter |
| `6` | TAB as request spacer |
| `7` | Random case sensitivity |
| `8` | Use Windows directory separator (\) |
| `A` | Use carriage return as spacer |
| `B` | Use binary value 0x0b as spacer |

```bash
nikto -h http://target.com -evasion 1,2,3,7
```

## Common Workflows

```bash
# Quick recon (most useful findings)
nikto -h http://target.com -Tuning 23b

# HTTPS with self-signed cert
nikto -h https://target.com -ssl -nointeractive

# Through Burp proxy (capture for manual review)
nikto -h http://target.com -useproxy http://127.0.0.1:8080

# Scan with basic auth
nikto -h http://target.com -id admin:password

# Scan with custom header (session cookie)
nikto -h http://target.com -C all \
    -H "Cookie: session=abc123"

# Scan multiple hosts from file
nikto -h hosts.txt -o results.csv -Format csv

# Save HTML report
nikto -h http://target.com -o report.html -Format html

# Quiet mode for clean output
nikto -h http://target.com -Display V

# Target non-standard port
nikto -h target.com -p 8080,8443,8888
```

## Display Options

| Value | Output |
|-------|--------|
| `1` | Show redirects |
| `2` | Show cookies received |
| `3` | Show all 200 responses |
| `4` | Show URLs requiring auth |
| `D` | Debug output |
| `E` | Display all HTTP errors |
| `P` | Print progress to STDOUT |
| `V` | Verbose output |

```bash
nikto -h http://target.com -Display 12
```

## Output Parsing

```bash
# Extract only findings (exclude info lines)
nikto -h http://target.com -Format csv | grep -v "^#\|^-" | column -t -s ','

# Combine with httpx for batch scanning
httpx -l hosts.txt -silent | xargs -P5 -I{} nikto -h {} -Tuning 23b -o {}_nikto.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/plugins.md` | Plugin list, authentication bypass techniques, custom checks |
