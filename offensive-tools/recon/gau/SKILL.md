---
name: gau
description: "Passive URL mining tool that fetches known URLs from Wayback Machine, Common Crawl, URLScan, and OTX. Use when asked to discover historical URLs, find old endpoints, mine parameters, or gather URLs passively without touching the target."
license: MIT
compatibility: "Linux, Windows, macOS. Install: go install github.com/lc/gau/v2/cmd/gau@latest or download binary from GitHub releases."
metadata:
  author: AeonDave
  version: "1.1"
---

# gau (getallurls)

Passive URL mining from Wayback Machine, Common Crawl, URLScan.io, and AlienVault OTX — no requests to target.

## Quick Start

```bash
# Fetch all known URLs for a domain
gau target.com

# With subdomains
gau --subs target.com

# Pipe into other tools
echo target.com | gau | httpx -silent
```

## Core Flags

| Flag | Description |
|------|-------------|
| `--subs` | Include subdomains |
| `--providers <list>` | Sources: `wayback,commoncrawl,urlscan,otx` |
| `--blacklist <ext>` | Exclude extensions (e.g., `png,jpg,gif,css,woff`) |
| `--fc <codes>` | Filter by status codes (from URLScan data) |
| `--ft <types>` | Filter by content type |
| `--mc <codes>` | Match status codes |
| `--threads <n>` | Concurrent threads |
| `--retries <n>` | Retry count |
| `--timeout <n>` | Timeout per request |
| `--verbose` | Verbose output |
| `--json` | JSON output (includes status, content-type, length) |
| `-o <file>` | Output file |
| `--config <file>` | Config file path |

## Common Workflows

```bash
# All URLs for domain + subs, skip media files
gau --subs --blacklist png,jpg,gif,svg,ico,css,woff,woff2,ttf target.com

# Specific providers only
gau --providers wayback,urlscan target.com

# JSON output for analysis
gau --json target.com > urls.json

# Filter parameters (find injectable endpoints)
gau target.com | grep "?"

# Unique parameters across all URLs
gau target.com | grep "?" | \
  sed 's/=.*/=/' | sort -u

# Old endpoints → check if still alive
gau target.com | httpx -silent -mc 200

# Mine API endpoints
gau target.com | grep -E "(/api/|/v[0-9]+/)" | sort -u

# Find backup/config files (historical)
gau target.com | grep -E "\.(bak|old|conf|cfg|env|log|sql|tar|zip|gz)$"

# Feed to nuclei for historical endpoint scan
gau target.com | httpx -silent | nuclei -tags exposure,misconfig -severity medium,high
```

## Parameter Mining

```bash
# Extract all parameter names
gau target.com | grep "?" | \
  python3 -c "
import sys, urllib.parse
params = set()
for url in sys.stdin:
  parsed = urllib.parse.urlparse(url.strip())
  for k in urllib.parse.parse_qs(parsed.query).keys():
    params.add(k)
print('\n'.join(sorted(params)))
" > params.txt

# Feed to ffuf for parameter fuzzing
ffuf -u "https://target.com/page?FUZZ=test" -w params.txt -ac
```

## Config File (~/.gau.toml)

```toml
providers = ["wayback", "commoncrawl", "urlscan", "otx"]
threads = 1
verbose = false
retries = 3
timeout = 45
blacklist = ["png", "jpg", "gif", "svg", "ico", "css", "woff", "woff2"]
```

## Resources

| File | When to load |
|------|--------------|
| `references/sources.md` | Provider details, URL parsing patterns, combination with other tools |
