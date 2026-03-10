---
name: xsstrike
description: "XSStrike: advanced XSS detection suite with context-aware payload generation, DOM XSS analysis, site crawler, and WAF-bypass fuzzer. Use when testing for reflected, stored, or DOM-based XSS, identifying injection contexts, or generating payloads tailored to bypass specific filters."
license: GPL-3.0
compatibility: "Linux / macOS / Windows. Python 3.6+. pip install -r requirements.txt."
metadata:
  author: AeonDave
  version: "1.0"
---

# XSStrike

Context-aware XSS detection and payload generation.

## Quick Start

```bash
python xsstrike.py -u "http://target.com/search?q=test"
python xsstrike.py -u "http://target.com" --crawl
python xsstrike.py -u "http://target.com/feedback" --blind
python xsstrike.py -u "http://target.com/?q=test" --fuzzer
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u <url>` | Target URL with parameter |
| `--crawl` | Crawl and test all discovered links |
| `--blind` | Blind XSS mode (no reflection check) |
| `--fuzzer` | Fuzz with payload list |
| `-l <level>` | Crawl depth |
| `--data <post>` | POST data |
| `-p <param>` | Test specific parameter only |
| `--headers <h>` | Custom headers |
| `--proxy <proxy>` | Route through proxy |

## Resources

| File | When to load |
|------|--------------|
| `references/` | DOM XSS testing, WAF bypass techniques |
