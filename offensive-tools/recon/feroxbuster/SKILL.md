---
name: feroxbuster
description: "Fast, recursive web content discovery tool written in Rust. Use when asked to enumerate web directories recursively, find hidden files/endpoints, fuzz a web application, or when a deep recursive scan is needed that gobuster doesn't handle natively."
license: MIT
compatibility: "Linux, Windows, macOS. Install: cargo install feroxbuster or download binary from GitHub releases. Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.1"
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
| `--collect-words` | Collect words from responses for wordlist mutation |
| `--collect-backups` | Also request common backup file extensions |
| `--collect-extensions` | Collect extensions from responses |
| `--resume-from <state>` | Resume from a previous scan state file |
| `--extract-links` | Extract links from HTML and add to queue |
| `--scan-limit <n>` | Max concurrent scans (for recursion) |
| `--time-limit <dur>` | Max time limit (e.g., `10m`) |
| `-A` | Random User-Agent per request |
| `--dont-filter` | Disable auto-filter of wildcard responses |

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

# Link extraction (spider + brute)
feroxbuster -u https://target.com -w common.txt --extract-links

# Smart collect mode (mutate wordlist from response)
feroxbuster -u https://target.com -w common.txt --collect-words --collect-extensions

# Time-boxed scan
feroxbuster -u https://target.com -w big.txt --time-limit 5m

# Resume interrupted scan
feroxbuster --resume-from ferox-target-state.json
```

## Config File (~/.config/feroxbuster/ferox-config.toml)

```toml
# Set defaults to avoid repeating flags
wordlist = "/usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt"
threads = 50
timeout = 10
status_codes = [200, 204, 301, 302, 307, 401, 403]
filter_status = [404]
auto_tune = true
collect_words = true
extract_links = true
user_agent = "Mozilla/5.0 (compatible; feroxbuster)"
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
