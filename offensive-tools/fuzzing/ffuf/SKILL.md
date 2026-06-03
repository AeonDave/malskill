---
name: ffuf
description: "Auth/lab ref: High-speed HTTP fuzzing engine for endpoint discovery and input mutation on web/API targets."
license: MIT
compatibility: "Linux, Windows, macOS."
metadata:
  author: AeonDave
  version: "1.2"
---

# ffuf

Go-based web fuzzer — FUZZ keyword can be placed anywhere in a request (URL, headers, body, hostname).

Use `ffuf` when you need fast, iterative fuzz campaigns and deterministic filtering; use crawlers (`hakrawler`, etc.) only for passive discovery.

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
| `-timeout <n>` | HTTP timeout in seconds |
| `-ignore-body` | Skip response body download when only status/size matters |
| `-noninteractive` | Disable interactive console mode for scripts and agents |
| `-v` | Verbose (show redirects) |
| `-s` | Silent mode |
| `-p <delay>` | Delay between requests (e.g., `0.1` or `0.1-0.5`) |
| `-recursion` | Enable recursive fuzzing |
| `-recursion-depth <n>` | Max recursion depth |
| `-recursion-strategy default\|greedy` | Strategy for recursion |
| `-ac` | Auto-calibrate filter (detect and filter noise) |
| `-ach` | Auto-calibrate per host |
| `-maxtime <n>` | Max run time in seconds |
| `-ic` | Ignore wordlist comments |
| `-c` | Colorize output |

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
# Standard dir fuzz with auto-calibration (best noise filter)
ffuf -u https://target.com/FUZZ -w raft-medium.txt -ac -o dirs.json -of json

# POST login brute-force
ffuf -u https://target.com/login -X POST -d "user=admin&pass=FUZZ" -w passwords.txt -fc 401

# Parameter discovery (GET)
ffuf -u "https://target.com/page?FUZZ=test" -w params.txt -fw 42

# Vhost discovery
ffuf -u http://target.com -H "Host: FUZZ.target.com" -w vhosts.txt -fw 42

# API endpoint fuzzing with auth
ffuf -u https://api.target.com/v1/FUZZ -w api-words.txt -H "Authorization: Bearer TOKEN" -mc 200,201,204

# Recursive dir fuzz
ffuf -u https://target.com/FUZZ -w common.txt -recursion -recursion-depth 3 -ac

# Header fuzzing (find supported methods/auth headers)
ffuf -u https://target.com/api/resource -w methods.txt -X FUZZ -mc 200,201,405

# JSON POST body fuzzing
ffuf -u https://api.target.com/v1/users -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"FUZZ","password":"test"}' \
  -w usernames.txt -mc 200
```

## Operator Playbook (Recommended)

1. Start with `-ac`, `-noninteractive`, and explicit output (`-o <file> -of json`) to reduce baseline noise and keep automation deterministic.
2. Lock stable match/filter logic (`-mc` + one of `-fs/-fw/-fl`) before deep recursion.
3. Run endpoint discovery first, then parameter/header/body fuzzing on confirmed routes.
4. Only then enable recursion (`-recursion`) to avoid exploding false positives.
5. In agent or CI runs, always include `-noninteractive`; if ffuf drops into interactive mode, stop it and rerun with this flag.

### Fast baseline profile

```bash
ffuf -u https://target/FUZZ -w raft-medium-words.txt -ac -fc 404 -t 40 -rate 100 -timeout 10 -noninteractive -o ffuf-baseline.json -of json
```

### Parameter-name fuzzing profile

```bash
ffuf -u "https://target/api/resource?FUZZ=1" -w params.txt -ac -mc all -fs 0
```

### Replay to proxy for manual confirmation

```bash
ffuf -u https://target/FUZZ -w words.txt -ac -replay-proxy http://127.0.0.1:8080
```

## Resources

| File | When to load |
|------|--------------|
| `references/filters.md` | All filter/matcher flags, noise reduction strategies, multi-FUZZ patterns |
