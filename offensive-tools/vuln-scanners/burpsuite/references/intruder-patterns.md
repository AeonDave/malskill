# Burp Suite — Intruder Patterns & Repeater Workflows

## Intruder: Attack Configuration

### Payload Position Markers

```
# Mark positions with § in request body:
username=§admin§&password=§password§

# Sniper: one position at a time
# Cluster Bomb: all combos (u×p requests)
# Pitchfork: parallel lists (same index)
```

### Payload Types

| Type | Use Case |
|------|---------|
| Simple list | Wordlist attack |
| Runtime file | Large file, streamed |
| Numbers | Sequential IDs (IDOR) |
| Dates | Date-based parameters |
| Brute Forcer | Charset-based enumeration |
| Character substitution | l33tspeak, case variants |
| Case modification | UPPERCASE, lowercase |
| Null payloads | Repeat same request N times |
| Username generator | Based on name format |
| Bit flipper | Encrypted session manipulation |

### Payload Processing Rules

```
# Transform payloads before sending:
# Add prefix: admin_
# Add suffix: @target.com
# URL encode
# Base64 encode
# Hash (MD5/SHA1/SHA256)
# Match/replace regex

# Example: brute-force with MD5-hashed passwords
# Rule chain: Hash (MD5) → URL encode
```

### Grep Rules for Response Analysis

```
# Grep Match: find specific strings in responses
# "Invalid password" → failed logins
# "Welcome back" → successful login
# "Access denied" → auth check
# "error in your SQL" → SQLi indicator

# Grep Extract: pull values from responses
# Regex: token="([^"]+)"  → extract CSRF tokens, session IDs

# Intruder → Grep - Match → add patterns
# Results column: boolean (found/not found)
# Sort by column to find outliers
```

## Common Intruder Workflows

### IDOR / Horizontal Privilege Escalation

```
# Enumerate object IDs:
GET /api/document/§1§ HTTP/1.1

# Attack type: Sniper
# Payload: Numbers 1-1000
# Grep: your own data (baseline)
# Look for: same/longer response length when ID changed
# Check: grep for other users' data
```

### Password Brute-Force (Login)

```
POST /login HTTP/1.1
username=admin&password=§password§

# Attack: Sniper
# Payload: /usr/share/wordlists/rockyou.txt
# Grep Match: "Invalid" (failed indicator)
# Filter: where match not found = success

# Cluster Bomb for unknown username:
username=§user§&password=§pass§
# Payload 1: users.txt
# Payload 2: 100 common passwords
```

### CSRF Token Extraction and Reuse

```
# Get fresh CSRF token per request:
# Intruder → Options → Extract grep
# Regex: csrf_token" value="([^"]+)"
# Use extracted value as payload in next request
# (Recursive grep — requires Macros for full automation)
```

### OTP / 2FA Brute-Force

```
POST /verify HTTP/1.1
code=§1234§

# Attack: Sniper
# Payload: Numbers (0000-9999) with padding (4 digits)
# Rate limit: set request throttle or use Turbo Intruder for race
```

## Session Handling Rules (Macros)

```
# For apps that require valid CSRF token or session per request:
Project → Options → Sessions → Session Handling Rules
→ Add rule → Run macro
→ Add macro: record the login/token-fetch request
→ Define what to extract (CSRF token, session cookie)
→ Apply to: Intruder / Scanner / Repeater

# Full flow:
1. Record: GET /login → extract csrf_token
2. Record: POST /login (with credentials) → extract session cookie
3. Add rule: run macro before each Intruder request
4. Intruder now has fresh session for each payload
```

## Repeater: Advanced Usage

```
# HTTP/2 requests:
# Repeater → Inspector panel → Request Attributes → Protocol: HTTP/2
# Test for HTTP/2 downgrade attacks, header smuggling

# Request smuggling (TE.CL):
POST / HTTP/1.1
Host: target.com
Transfer-Encoding: chunked
Content-Length: 6

0

# WebSocket messages:
# Proxy → WebSockets History → Send to Repeater
# Modify and replay individual WS frames

# Comparison workflow:
# Two requests side-by-side: Window → New Window or use tabs
# Comparer: right-click → Send to Comparer
```

## Scanner Configuration (Pro)

```
# Fine-tune active scanner:
Dashboard → New Scan → Scan Configuration → New

Audit optimization:
- Select issue types to check
- Set request engine: concurrency, delay, timeout
- "Minimize false positives" vs "Maximize coverage"

# Useful custom configs:
- "XSS only" — minimize noise, confirm injections
- "SQL injection only" — targeted injection test
- "Information disclosure" — check error pages, backups, etc.

# Scan from Proxy History:
- Select interesting requests
- Right-click → Scan
```
