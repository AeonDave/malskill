---
name: arjun
description: "Discover hidden HTTP parameters in web endpoints. Use when performing API reconnaissance, fuzzing query/body/header parameters, or finding undocumented inputs in REST/GraphQL endpoints."
license: MIT
compatibility: "Python 3; pip install arjun; Linux/macOS/Windows"
metadata:
  author: AeonDave
  version: "1.0"
---

# Arjun

HTTP parameter discovery — finds hidden GET/POST/JSON/XML parameters in web endpoints.

## Quick Start

```bash
pip install arjun

# Single URL — GET params
arjun -u https://target.com/api/endpoint

# POST body params
arjun -u https://target.com/api/endpoint -m POST

# JSON body
arjun -u https://target.com/api/endpoint -m JSON

# Multiple URLs from file
arjun -i urls.txt -o results.json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u URL` | Target URL |
| `-m GET/POST/JSON/XML` | Request method (default: GET) |
| `-i FILE` | Input file with URLs |
| `-o FILE` | Output results to JSON |
| `-t N` | Threads (default: 5) |
| `-d N` | Request delay (ms) |
| `--headers "K:V"` | Custom headers |
| `--stable` | Avoid flakey endpoints (retry on error) |
| `-q` | Quiet mode |
| `--include` | Always include params in every request |

## Common Workflows

**API recon on authenticated endpoint:**
```bash
arjun -u https://api.target.com/v1/user -m GET --headers "Authorization: Bearer TOKEN"
```

**Fuzz POST form:**
```bash
arjun -u https://target.com/login -m POST
```

**Batch scan from Burp export:**
```bash
cat burp_urls.txt | arjun -i /dev/stdin -o found_params.json
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Extended wordlist and tamper tips |
