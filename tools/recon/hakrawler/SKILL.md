---
name: hakrawler
description: "Fast Go web crawler for discovering URLs, endpoints, and JavaScript files. Use when crawling web applications to build a URL inventory before fuzzing or during OSINT on web infrastructure."
license: MIT
compatibility: "Go; go install github.com/hakluke/hakrawler@latest; Linux/macOS/Windows"
metadata:
  author: AeonDave
  version: "1.0"
---

# Hakrawler

Fast Go web crawler — discover URLs, JS files, forms, and endpoints.

## Quick Start

```bash
go install github.com/hakluke/hakrawler@latest

# Crawl a domain
echo https://target.com | hakrawler

# Depth 3, include subdomains
echo https://target.com | hakrawler -d 3 -subs

# Output as JSON
echo https://target.com | hakrawler -json

# Pipe multiple domains
cat domains.txt | hakrawler -d 2
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-d N` | Depth (default: 1) |
| `-subs` | Include subdomains |
| `-u` | Unique URLs only |
| `-insecure` | Skip TLS verification |
| `-t N` | Threads |
| `-timeout N` | Timeout per request (s) |
| `-H "K:V"` | Custom header |
| `-json` | JSON output |
| `-scope REGEX` | Limit to URL pattern |

## Common Workflows

**Build URL inventory for fuzzing:**
```bash
echo https://target.com | hakrawler -d 3 -u | tee urls.txt
# Feed to ffuf
ffuf -w urls.txt:URL -u URL -mc 200
```

**Discover JS files:**
```bash
echo https://target.com | hakrawler -d 2 | grep "\.js$"
```

**Combine with httpx for live check:**
```bash
cat domains.txt | hakrawler | httpx -silent -mc 200
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Scope filtering and JS analysis tips |
