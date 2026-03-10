---
name: httpx
description: "Fast HTTP probing tool for bulk URL processing, status codes, title extraction, tech detection, and web fingerprinting. Use when asked to probe a list of hosts/URLs for live web servers, find HTTP services, check status codes, extract page titles, or fingerprint web technologies."
license: MIT
compatibility: "Linux, Windows, macOS. Install: go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest or download binary. Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.0"
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
| `-status-code` | Show HTTP status code |
| `-title` | Extract page title |
| `-tech-detect` | Detect technologies (Wappalyzer) |
| `-web-server` | Show web server header |
| `-content-type` | Show Content-Type header |
| `-ip` | Resolve and show IP |
| `-cname` | Show CNAME |
| `-location` | Show redirect location |
| `-content-length` | Show response size |
| `-hash <algo>` | Hash response body (md5,sha1,sha256) |
| `-favicon` | Extract favicon hash (Shodan mmh3) |
| `-follow-redirects` | Follow HTTP redirects |
| `-threads <n>` | Concurrent threads (default 50) |
| `-rate-limit <n>` | Requests per second |
| `-timeout <n>` | Timeout in seconds (default 5) |
| `-retries <n>` | Retry count |
| `-H <header>` | Custom header |
| `-proxy <url>` | HTTP/SOCKS5 proxy |
| `-o <file>` | Output file |
| `-json` | JSON output |
| `-csv` | CSV output |
| `-ports <p>` | Probe specific ports (e.g., `80,443,8080`) |
| `-tls-probe` | Probe for TLS |
| `-http2` | Enable HTTP/2 |
| `-screenshot` | Take screenshots (requires chromium) |

## Common Workflows

```bash
# Full recon pipeline: subfinder -> httpx
subfinder -d target.com -silent | httpx -status-code -title -tech-detect -o live.txt

# Probe list with all metadata
httpx -l hosts.txt -status-code -title -tech-detect -web-server -ip -o full.json -json

# Find admin/login panels
httpx -l hosts.txt -title -silent | grep -iE "admin|login|portal|dashboard"

# Port-specific probing
httpx -l hosts.txt -ports 80,443,8080,8443,3000,8888 -status-code -silent

# Favicon hash (for Shodan pivot)
httpx -u https://target.com -favicon

# Screenshot all live hosts
httpx -l hosts.txt -screenshot -output screenshots/
```

## Resources

| File | When to load |
|------|--------------|
| `references/output-fields.md` | All output field flags, JSON schema, and filter options |
