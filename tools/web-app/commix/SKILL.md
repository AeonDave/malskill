---
name: commix
description: "Commix: automated OS command injection detection and exploitation tool supporting classic, time-based, and file-based techniques. Use when detecting and exploiting command injection vulnerabilities in web parameters, cookies, or HTTP headers, or escalating from injection to interactive shell access."
license: GPL-3.0
compatibility: "Linux / macOS / Windows. Python 3. Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.0"
---

# Commix

Automated OS command injection detection and exploitation.

## Quick Start

```bash
commix --url="http://target.com/page?ip=127.0.0.1"
commix --url="http://target.com/ping" --data="ip=127.0.0.1"
commix -r request.txt
commix --url="http://target.com/?ip=1" --os-shell
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--url <url>` | Target URL |
| `--data <data>` | POST body |
| `-r <file>` | Burp-format request file |
| `--cookie <c>` | Session cookie |
| `--os-cmd <cmd>` | Run single OS command |
| `--os-shell` | Interactive pseudo shell |
| `--technique <t>` | classic / timebased / tempfile-based / file-based |
| `--level <1-3>` | Fuzz depth |
| `--proxy <proxy>` | HTTP proxy |
| `--batch` | Non-interactive defaults |

## Resources

| File | When to load |
|------|--------------|
| `references/` | Blind injection, file upload via command injection |
