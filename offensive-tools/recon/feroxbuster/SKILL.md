---
name: feroxbuster
description: "Fast, recursive web content discovery tool written in Rust. Use when asked to enumerate web directories recursively, find hidden files/endpoints, fuzz a web application, or when a deep recursive scan is needed that gobuster doesn't handle natively."
license: MIT
compatibility: "Linux, Windows, macOS. Install: cargo install feroxbuster or download binary from GitHub releases. Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.0"
---

# Feroxbuster

Recursive, fast content discovery — handles JavaScript-rendered apps and auto-recurses into found dirs.

## Quick Start

```bash
# Basic scan
feroxbuster -u http://example.com -w /usr/share/wordlists/dirb/common.txt

# With extensions
feroxbuster -u http://example.com -w common.txt -x php,html,txt

# No recursion (flat scan)
feroxbuster -u http://example.com -w common.txt --no-recursion
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-u <url>` | Target URL |
| `-w <wordlist>` | Wordlist (use `-` to read stdin) |
| `-x <ext>` | File extensions comma-separated |
| `-t <n>` | Threads (default 50) |
| `-d <n>` | Recursion depth (default 4, 0 = unlimited) |
| `--no-recursion` | Disable recursion |
| `-s <codes>` | Status codes to match (default `200,204,301,302,307,308,401,403,405`) |
| `-C <codes>` | Filter/exclude status codes |
| `-S <size>` | Filter by response size |
| `-W <words>` | Filter by word count |
| `-L <lines>` | Filter by line count |
| `-H <header>` | Custom HTTP header |
| `-b <cookie>` | Cookie value |
| `-k` | Disable TLS verification |
| `-r` | Follow redirects |
| `--proxy <url>` | HTTP/SOCKS5 proxy |
| `-o <file>` | Output file |
| `-q` | Quiet (no progress bar) |
| `--json` | JSON output |
| `--auto-tune` | Automatically slow down on errors |
| `--smart-auto-tune` | Only slow on 429/503 |

## Filtering Examples

```bash
# Filter out 404 and 302
feroxbuster -u http://target.com -w common.txt -C 404,302

# Filter by response size (hide 0-byte responses)
feroxbuster -u http://target.com -w common.txt -S 0

# Show only 200 responses
feroxbuster -u http://target.com -w common.txt -s 200
```

## Common Workflows

```bash
# Recursive scan with extensions, output to file
feroxbuster -u https://target.com -w raft-medium.txt -x php,bak,conf -o results.txt

# API endpoint discovery (JSON-focused)
feroxbuster -u https://api.target.com -w api-endpoints.txt -x json -H "Accept: application/json"

# Authenticated scan
feroxbuster -u https://target.com -w common.txt -H "Authorization: Bearer TOKEN"

# Behind proxy (Burp)
feroxbuster -u http://target.com -w common.txt --proxy http://127.0.0.1:8080 -k

# Fast aggressive scan
feroxbuster -u http://target.com -w big.txt -t 100 --no-recursion -d 1

# Scan multiple URLs from file
feroxbuster --stdin -w common.txt < urls.txt
```

## Interactive Controls

While running, press:
- `Enter` — display current state
- `s` — stop a specific URL scan
- `q` / `Ctrl+C` — quit

## Resources

| File | When to load |
|------|--------------|
| `references/filters.md` | Detailed filter flag combinations, size/word/line-based noise reduction |
