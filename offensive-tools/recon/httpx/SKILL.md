---
name: httpx
description: "Auth/lab ref: Fast HTTP probing tool for bulk URL processing, status codes, title extraction, tech detection, and web fingerprinting."
license: MIT
compatibility: "Linux, Windows, macOS."
metadata:
  author: AeonDave
  version: "1.1"
---

# httpx

Fast HTTP toolkit from ProjectDiscovery — probe and fingerprint web servers at scale.

## Quick Start

```bash
# Probe a list of hosts
cat hosts.txt | httpx

# Probe with status + title
httpx -l hosts.txt -status-code -title

# Silent (URLs only for live hosts)
cat subs.txt | httpx -silent
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-l <file>` | Input file with hosts |
| `-u <url>` | Single target |
| `-silent` | Print live URLs only |
| `-status-code`, `-sc` | Show HTTP status code |
| `-title` | Extract page title |
| `-tech-detect`, `-td` | Detect technologies (Wappalyzer) |
| `-web-server`, `-server` | Show web server header |
| `-content-type`, `-ct` | Show Content-Type header |
| `-ip` | Resolve and show IP |
| `-cname` | Show CNAME |
| `-location` | Show redirect location |
| `-content-length`, `-cl` | Show response size |
| `-hash <algo>` | Hash response body (md5,sha1,sha256) |
| `-favicon` | Extract favicon hash (Shodan mmh3) |
| `-follow-redirects`, `-fr` | Follow HTTP redirects |
| `-threads <n>`, `-t <n>` | Concurrent threads (default 50) |
| `-rate-limit <n>`, `-rl <n>` | Requests per second |
| `-timeout <n>` | Timeout in seconds (default 5) |
| `-retries <n>` | Retry count |
| `-H <header>` | Custom header |
| `-proxy <url>` | HTTP/SOCKS5 proxy |
| `-o <file>` | Output file |
| `-json`, `-j` | JSONL output |
| `-csv` | CSV output |
| `-ports <p>` | Probe specific ports (e.g., `80,443,8080`) |
| `-path <path-or-file>` | Probe specific path(s) on each host |
| `-no-fallback`, `-nf` | Probe both HTTP and HTTPS instead of fallback behavior |
| `-no-fallback-scheme`, `-nfs` | Do not auto-switch schemes |
| `-store-response`, `-sr` | Store request/response artifacts |
| `-store-response-dir`, `-srd <dir>` | Directory for stored artifacts |
| `-tls-impersonate`, `-tlsi` | Experimental TLS impersonation |
| `-tls-probe` | Probe for TLS |
| `-http2` | Enable HTTP/2 |
| `-screenshot` | Take screenshots (requires chromium) |

## Common Workflows

```bash
# Full recon pipeline: subfinder -> httpx
subfinder -d target.com -silent | httpx -status-code -title -tech-detect -o live.txt

# Probe list with all metadata
httpx -l hosts.txt -status-code -title -tech-detect -web-server -ip -o full.json -json

# Agent-safe JSONL baseline with explicit throughput
httpx -l hosts.txt -sc -title -server -td -fr -timeout 10 -retries 1 -rl 50 -t 25 -silent -j -o httpx.jsonl

# Probe known paths and store responses for downstream route/JS parsing
httpx -l hosts.txt -path /,/login,/admin -sc -title -sr -srd recon/httpx_store -silent -j -o httpx_paths.jsonl

# Find admin/login panels
httpx -l hosts.txt -title -silent | grep -iE "admin|login|portal|dashboard"

# Port-specific probing
httpx -l hosts.txt -ports 80,443,8080,8443,3000,8888 -status-code -silent

# Probe both schemes from host-only input
httpx -l hosts.txt -nf -sc -title -silent

# Favicon hash (for Shodan pivot)
httpx -u https://target.com -favicon

# Screenshot all live hosts
httpx -l hosts.txt -screenshot -output screenshots/
```

## Filter Results

```bash
# Only 200s
httpx -l hosts.txt -silent -mc 200

# Exclude CDN/redirect noise
httpx -l hosts.txt -silent -fc 301,302 -filter-string "cloudflare"

# Match by response body content
httpx -l hosts.txt -match-string "password" -silent

# Match by response size
httpx -l hosts.txt -ms 1024 -silent
```

## Resources

| File | When to load |
|------|--------------|
| `references/output-fields.md` | All output field flags, JSON schema, match/filter options, pipeline patterns |
