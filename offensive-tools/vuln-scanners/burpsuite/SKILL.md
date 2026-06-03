---
name: burpsuite
description: "Auth/lab ref: Burp Suite: integrated web application security testing platform with proxy, scanner, intruder, and repeater."
license: Commercial (Pro) / Free (Community)
compatibility: "Windows / macOS / Linux; Java 11+."
metadata:
  author: AeonDave
  version: "1.1"
---

# Burp Suite

Web application security testing platform.

## Quick Start

```bash
burpsuite
# Set browser proxy: 127.0.0.1:8080
# Install CA cert: browse to http://burp → CA Certificate (or Proxy → Options → Import/Export CA)
# Firefox: FoxyProxy extension for quick toggle
```

## Core Tools

| Tool | Use |
|------|-----|
| **Proxy** | Intercept / modify HTTP/S traffic |
| **Repeater** | Replay and modify single requests |
| **Intruder** | Automated fuzzing / brute-force |
| **Scanner** | Active/passive vuln detection (Pro) |
| **Decoder** | Encode/decode URL, Base64, hex, HTML |
| **Comparer** | Diff two HTTP responses or requests |
| **Extender** | Load BApp plugins |
| **Logger** | Full HTTP traffic log (Pro) |

## Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | Send to Repeater |
| `Ctrl+I` | Send to Intruder |
| `Ctrl+D` | Send to Decoder |
| `Ctrl+F` | Forward intercepted request |
| `Ctrl+Z` | Drop request |
| `Ctrl+S` | Save item |
| `Ctrl+A` | Select all |

## Proxy: Key Settings

```
Proxy → Options:
- Intercept Client Requests: check "URL is in target scope"
- Match and Replace: inject headers, modify values without intercepting every request

Proxy → HTTP History:
- Filter: show only in-scope, exclude images/CSS/JS
- Ctrl+F: search across all history (regex supported)
- Right-click → Add to scope / Send to Intruder/Repeater/Scanner
```

### Match and Replace rules

```
# Proxy → Options → Match and Replace
# Add rule:
Type: Request header
Match: ^
Replace: X-Forwarded-For: 127.0.0.1

# Type: Response body
# Match: You must be logged in
# Replace: Welcome admin
# (useful for bypassing client-side auth checks)

# Type: Request header, Replace: Authorization: Bearer <stolen_token>
# Auto-injects auth on every request
```

## Scope Configuration

```
Target → Scope → Include in scope:
Protocol: https
Host: ^target\.com$  # regex supported
Path: ^/api/

# "Use Advanced Scope Control" for regex rules
# Project → Options → Out-of-scope URLs: Drop → avoids noise
```

## Intruder Attack Types

| Type | Use Case |
|------|----------|
| Sniper | One payload set, one position at a time |
| Battering Ram | Same payload in all positions simultaneously |
| Pitchfork | One payload per position, parallel lists |
| Cluster Bomb | All combinations (cartesian product) |

```
# Brute-force login:
POST /login → Intruder → Cluster Bomb
§username§ → payload list: users.txt
§password§ → payload list: passwords.txt

# Grep Match: "Invalid credentials" → failed
# Grep Match: "Welcome" → success
# Sort by length to find successful responses
```

## Repeater Workflows

```
# Manual SQLi test:
GET /item?id=1 → Repeater
Modify: id=1'       → check for error
        id=1 AND 1=1 → check for normal response
        id=1 AND 1=2 → check for different response

# IDOR test:
GET /api/user/123 → Repeater
Change 123 → 124, 125 (other users)
Check response for data leakage

# HTTP Request Smuggling (Pro/manual):
Change Connection: keep-alive
Add Transfer-Encoding: chunked
Craft ambiguous body
```

## Common Workflows

### Auth bypass (parameter tampering)
1. Intercept login request
2. Observe response → session cookie/token
3. Forward → capture admin endpoint request
4. Replay with modified role/flag parameters

### Session token analysis
```
Sequencer → Token Location: Cookie/Header
Start Live Capture → 10,000+ samples
Analyze → check entropy (should be >100 bits effective entropy)
```

### Active Scanner (Pro)

```
# Right-click target in Proxy History → Scan
# Or: Dashboard → New Scan → URL → select scan type
# Audit checks: SQL injection, XSS, XXE, SSRF, path traversal, etc.

# Scan configuration:
# Built-in: "Audit coverage - maximum" vs "Audit checks - critical issues only"
# Custom: reduce noise, set concurrency, timeout
```

### Bambda (Java lambda filters, Burp 2023+)

```javascript
// Filter History to show only 4xx with JSON body:
return requestResponse.response().statusCode() >= 400
    && requestResponse.response().statusCode() < 500
    && requestResponse.response().hasHeader("Content-Type", "application/json");

// Find requests with Authorization header:
return requestResponse.request().hasHeader("Authorization");

// Find responses containing "password" (case-insensitive):
return requestResponse.response().bodyToString().toLowerCase().contains("password");
```

## Extensions (BApp Store)

```
# Install: Extender → BApp Store
```

| Extension | Purpose |
|-----------|---------|
| **Autorize** | Detect IDOR / broken access control automatically |
| **JWT Editor** | Decode/modify/forge JWT tokens |
| **Turbo Intruder** | High-speed fuzzing (Python, async) |
| **Active Scan++** | Additional active scan checks |
| **Param Miner** | Discover hidden/unlinked parameters |
| **403 Bypasser** | Auto-test auth bypass techniques |
| **Logger++** | Advanced traffic logging |
| **JS Miner** | Extract endpoints from JS files |
| **Upload Scanner** | Test file upload for dangerous types |
| **Hackvertor** | Multi-step encoding/decoding |

### Turbo Intruder example

```python
# High-speed race condition test:
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=30,
                           requestsPerConnection=100,
                           pipeline=True)
    for i in range(30):
        engine.queue(target.req, str(i))

def handleResponse(req, interesting):
    if '200' in req.status:
        table.add(req)
```

## Resources

| File | When to load |
|------|--------------|
| `references/bapp-extensions.md` | Plugin selection, Autorize/JWT/ParamMiner config |
| `references/intruder-patterns.md` | Attack type selection, payload processing, grep rules |
