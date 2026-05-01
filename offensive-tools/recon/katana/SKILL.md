---
name: katana
description: "ProjectDiscovery web crawler for endpoint and JS-endpoint discovery. Handles modern JS-heavy apps via headless browser mode, extracts endpoints from JavaScript files (JSLuice/regex), follows XHR/fetch calls, and integrates with the ProjectDiscovery pipeline (httpx, dnsx, subfinder). Use during active recon to enumerate all reachable endpoints, crawl APIs, extract hidden JS paths, and feed results into parameter discovery or vuln scanning."
license: MIT
compatibility: "Linux/macOS/Windows; Go binary. Targets: HTTP/HTTPS web applications."
metadata:
  author: AeonDave
  version: "1.0"
---

# Katana

ProjectDiscovery web crawler — endpoints, JS paths, XHR calls, and API routes from modern web apps.

## Quick start

```bash
# Single URL crawl
katana -u https://target.com

# Crawl with JS parsing (extract endpoints from JS files)
katana -u https://target.com -jc

# Headless mode (renders JS — required for SPA/React/Angular apps)
katana -u https://target.com -headless

# Output to file
katana -u https://target.com -jc -o endpoints.txt

# Multiple targets from file
katana -list urls.txt -jc -o all_endpoints.txt
```

## Crawling scope

```bash
# Limit to same domain (default behavior — no external crawl)
katana -u https://target.com -jc

# Include subdomains
katana -u https://target.com -jc -cs target.com

# Depth control
katana -u https://target.com -jc -d 5          # max depth 5 (default: 3)

# Concurrency
katana -u https://target.com -jc -c 20 -p 20   # 20 concurrent crawlers, 20 parallelism

# Rate limit (requests per second)
katana -u https://target.com -jc -rl 50
```

## JS endpoint extraction

Katana's JS crawling (`-jc`) uses JSLuice and regex patterns to extract endpoints from JavaScript files. This is the primary value over generic crawlers.

```bash
# JS crawl + XHR/fetch call tracing
katana -u https://target.com -jc -xhr

# Extract all JS file URLs only
katana -u https://target.com -jc | grep "\.js$" > js_files.txt

# Show discovered endpoints from JS (exclude static assets)
katana -u https://target.com -jc | grep -v "\.(png|jpg|gif|svg|ico|woff|css)$"

# Filter for API paths
katana -u https://target.com -jc | grep -E "(/api/|/v[0-9]+/|/graphql|/rest/)"
```

## Headless mode (SPA/React/Angular)

Standard crawler misses dynamically rendered content. Use headless for apps that require JavaScript execution.

```bash
# Headless Chrome/Chromium required
katana -u https://target.com -headless -jc -d 3

# Headless with wait (allow JS to execute before capture)
katana -u https://target.com -headless -jc -nos

# Authenticated crawl — provide session cookie
katana -u https://target.com -headless -H "Cookie: session=<token>" -jc
```

## Authentication and custom headers

```bash
# Bearer token
katana -u https://api.target.com -H "Authorization: Bearer <token>" -jc

# Multiple headers
katana -u https://target.com -H "X-Api-Key: abc123" -H "Accept: application/json" -jc

# POST requests (for apps requiring login state)
katana -u https://target.com -X POST -H "Content-Type: application/json" \
  -body '{"email":"test@test.com","password":"test"}' -jc
```

## Pipeline integration

Katana integrates with the ProjectDiscovery ecosystem:

```bash
# httpx → katana: crawl all live web hosts
httpx -l live_hosts.txt -silent | katana -jc -o all_endpoints.txt

# subfinder → httpx → katana: full passive-to-crawl pipeline
subfinder -d target.com -silent | httpx -silent | katana -jc -o endpoints.txt

# Feed into nuclei for vuln scanning
katana -u https://target.com -jc -o endpoints.txt
nuclei -l endpoints.txt -t exposures/ -t vulnerabilities/
```

## Output and filtering

```bash
# JSON output (structured for parsing)
katana -u https://target.com -jc -jsonl -o katana.jsonl

# Filter by extension (exclude static assets)
katana -u https://target.com -jc -fx js,json

# Filter by response code
katana -u https://target.com -jc -fsc 200,301,302

# Show only unique paths (deduplicate)
katana -u https://target.com -jc | sort -u > unique_endpoints.txt

# Extract parameters from found URLs
katana -u https://target.com -jc | grep "?" | cut -d"?" -f2 | tr "&" "\n" | cut -d"=" -f1 | sort -u
```

## OPSEC notes

- Standard mode: one request per link — low noise but misses JS-rendered content.
- Headless mode: launches a real browser — higher resource use, slightly more detectable.
- Use `-rl` rate limiting on sensitive or production scopes.
- Respect `robots.txt` boundaries unless explicitly authorized to ignore them: `-cr` to crawl despite robots.

## When to use vs. other crawlers

| Scenario | Tool |
|----------|------|
| Modern SPA/React/Angular | `katana -headless` |
| API endpoint extraction from JS | `katana -jc` |
| Fast directory brute-force | `feroxbuster` |
| Historical URL collection | `gau` |
| Fast link extraction from static HTML | `hakrawler` |
