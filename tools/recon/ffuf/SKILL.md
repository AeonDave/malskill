---
name: ffuf
description: "Fast web fuzzer for directory/file discovery, parameter fuzzing, virtual host discovery, and POST data fuzzing. Use when asked to fuzz web endpoints, discover hidden parameters, enumerate directories, test for injection points, or perform any HTTP-level wordlist-based fuzzing."
license: MIT
compatibility: "Linux, Windows, macOS. Install: go install github.com/ffuf/ffuf/v2@latest or download binary from GitHub releases. Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.0"
---

# ffuf

Go-based web fuzzer — FUZZ keyword can be placed anywhere in a request (URL, headers, body, hostname).

## Quick Start

```bash
# Directory fuzzing
ffuf -u http://example.com/FUZZ -w /usr/share/wordlists/dirb/common.txt

# With file extension
ffuf -u http://example.com/FUZZ -w common.txt -e .php,.html,.txt

# Subdomain/vhost fuzzing
ffuf -u http://FUZZ.example.com -w subdomains.txt -H "Host: FUZZ.example.com"
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-u <url>` | Target URL (use `FUZZ` as placeholder) |
| `-w <wordlist>` | Wordlist path (`:KEYWORD` for named payloads) |
| `-e <ext>` | Append extensions to each word |
| `-t <n>` | Threads (default 40) |
| `-rate <n>` | Max requests per second |
| `-H <header>` | Custom header |
| `-X <method>` | HTTP method (default GET) |
| `-d <data>` | POST data body |
| `-b <cookies>` | Cookie string |
| `-r` | Follow redirects |
| `-k` | Skip TLS verification |
| `-x <proxy>` | Proxy URL |
| `-o <file>` | Output file |
| `-of <format>` | Output format: `json`, `html`, `csv`, `md`, `all` |
| `-v` | Verbose (show redirects) |
| `-s` | Silent mode |
| `-p <delay>` | Delay between requests (e.g., `0.1` or `0.1-0.5`) |

## Filtering & Matching

| Flag | Description |
|------|-------------|
| `-mc <codes>` | Match HTTP status codes (default `200,204,301,302,307,401,403,405`) |
| `-ml <n>` | Match by response lines |
| `-mw <n>` | Match by word count |
| `-ms <size>` | Match by response size |
| `-mr <regex>` | Match by regex in body |
| `-fc <codes>` | Filter (exclude) status codes |
| `-fl <n>` | Filter by lines |
| `-fw <n>` | Filter by words |
| `-fs <n>` | Filter by size |
| `-fr <regex>` | Filter by regex |

## Multiple FUZZ Positions

```bash
# Two wordlists: W1 + W2
ffuf -u http://target.com/W1/W2 -w list1.txt:W1 -w list2.txt:W2

# Cluster bomb (all combinations)
ffuf -u http://target.com/W1?param=W2 -w list1.txt:W1 -w list2.txt:W2 -mode clusterbomb

# Pitchfork (paired positions)
ffuf -u http://target.com/W1?user=W2 -w paths.txt:W1 -w users.txt:W2 -mode pitchfork
```

## Common Workflows

```bash
# Standard dir fuzz with noise filtering
ffuf -u https://target.com/FUZZ -w raft-medium.txt -fc 404 -o dirs.json -of json

# POST login brute-force
ffuf -u https://target.com/login -X POST -d "user=admin&pass=FUZZ" -w passwords.txt -fc 401

# Parameter discovery (GET)
ffuf -u "https://target.com/page?FUZZ=test" -w params.txt -fw 42

# Vhost discovery
ffuf -u http://target.com -H "Host: FUZZ.target.com" -w vhosts.txt -fw 42

# API endpoint fuzzing with auth
ffuf -u https://api.target.com/v1/FUZZ -w api-words.txt -H "Authorization: Bearer TOKEN" -mc 200,201,204
```

## Resources

| File | When to load |
|------|--------------|
| `references/filters.md` | All filter/matcher flags, noise reduction strategies, multi-FUZZ patterns |
