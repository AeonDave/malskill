---
name: xsstrike
description: "Auth/lab ref: XSStrike XSS validation; context analysis, DOM checks, crawler, blind callback workflow, WAF-aware evidence."
license: GPL-3.0
compatibility: "Linux / macOS / Windows; Python 3.6+."
metadata:
  author: AeonDave
  version: "1.1"
---

# XSStrike

Context-aware XSS scanner — intelligent payload generation, DOM analysis, WAF evasion.

## Quick Start

```bash
git clone https://github.com/s0md3v/XSStrike
cd XSStrike && pip3 install -r requirements.txt

# Single URL / GET param
python3 xsstrike.py -u "http://target.com/search?q=test"

# POST data
python3 xsstrike.py -u "http://target.com/feedback" --data "comment=test&name=x"

# Crawl full site
python3 xsstrike.py -u "http://target.com" --crawl -l 3 -t 10

# Blind XSS (inject on crawl, callback on trigger)
python3 xsstrike.py -u "http://target.com" --crawl --blind

# WAF bypass fuzzing
python3 xsstrike.py -u "http://target.com?q=test" --fuzzer
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u <url>` | Target URL with injectable parameter |
| `--data <data>` | POST body (default: GET) |
| `--crawl` | Crawl site and test all discovered parameters |
| `-l <depth>` | Crawl depth (default: 2) |
| `--seeds <file>` | Crawl seed URLs from file |
| `--blind` | Blind XSS — inject payloads during crawl (no reflection check) |
| `--fuzzer` | Fuzz WAF filters (slow, with delays) |
| `--dom` | DOM XSS analysis only |
| `--skip-dom` | Skip DOM analysis (faster) |
| `-t <threads>` | Thread count |
| `-d <ms>` | Delay between requests (ms) |
| `--timeout <s>` | Request timeout (seconds) |
| `--encode` | Encode payloads for WAF evasion |
| `--json` | Treat POST data as JSON |
| `--path` | Test path injection |
| `--headers <h>` | Custom headers (separate multiple with `\n`) |
| `--proxy <proxy>` | HTTP/HTTPS proxy (e.g., http://127.0.0.1:8080) |
| `--file-log-level` | File logging verbosity |
| `--log-file <path>` | Save output to log file |

## XSStrike vs Dalfox

| | XSStrike | Dalfox |
|-|----------|--------|
| Speed | Moderate | Fast |
| WAF evasion | Deep encoding engine | Basic detection |
| Context analysis | 4 hand-written parsers | Heuristic |
| DOM XSS | Yes (dedicated analysis) | Limited |
| **Use when** | WAF-protected, complex filters | Large-scope quick scans |

## Common Workflows

```bash
# Authenticated single-param scan
python3 xsstrike.py -u "http://target.com/search?q=test" \
    --headers "Cookie: PHPSESSID=abc123"

# POST JSON API
python3 xsstrike.py -u "http://api.target.com/render" \
    --json --data '{"name":"test","msg":"hello"}'

# Full site crawl with auth
python3 xsstrike.py -u "http://target.com" --crawl -l 3 -t 10 \
    --headers "Cookie: session=abc123\nX-Custom: value"

# Blind XSS across full site
python3 xsstrike.py -u "http://target.com" --crawl --blind \
    --headers "Cookie: session=abc123"

# WAF bypass mode (slow)
python3 xsstrike.py -u "http://target.com?id=1" --fuzzer -d 2

# Through Burp proxy
python3 xsstrike.py -u "http://target.com/search?q=test" \
    --proxy http://127.0.0.1:8080

# Log results
python3 xsstrike.py -u "http://target.com" --crawl \
    --log-file results.txt --file-log-level INFO
```

## Payload Context Detection

XSStrike uses 4 hand-written parsers to detect injection context:

| Context | Detected By | Payload Type |
|---------|------------|--------------|
| HTML tag body | HTML parser | Event handler injection |
| HTML attribute | Attribute parser | Attribute breakout |
| JavaScript string | JS parser | Quote escape + exec |
| URL context | URL parser | URL encoding aware |

## Resources

| File | When to load |
|------|--------------|
| `references/xss-context-bypass.md` | Context-specific payloads, WAF evasion patterns, blind XSS setup, DOM sink list |
