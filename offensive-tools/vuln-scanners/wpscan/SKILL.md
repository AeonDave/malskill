---
name: wpscan
description: "Auth/lab ref: WordPress vulnerability and enumeration scanner."
license: WPScan License (free non-commercial)
compatibility: "Linux / macOS / Windows; Ruby 2.5+."
metadata:
  author: AeonDave
  version: "1.1"
---

# WPScan

WordPress vulnerability and enumeration scanner.

## Quick Start

```bash
wpscan --url https://target.com
wpscan --url https://target.com --enumerate u,p,t --api-token <TOKEN>
wpscan --url https://target.com -U admin -P /usr/share/wordlists/rockyou.txt
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--url <url>` | Target WordPress URL |
| `--enumerate <items>` | u=users, p=plugins, t=themes, vp=vuln plugins, vt=vuln themes, ap=all plugins, at=all themes, tt=timthumbs, cb=config backups, dbe=db exports, m=media ids |
| `--api-token <token>` | WPScan API token (required for CVE data) |
| `--plugins-detection` | `aggressive` / `passive` / `mixed` |
| `--themes-detection` | `aggressive` / `passive` / `mixed` |
| `-U <user>` | Username (or file) for brute-force |
| `-P <wordlist>` | Password wordlist |
| `--password-attack` | `xmlrpc` / `xmlrpc-multicall` / `wp-login` |
| `--usernames <list>` | Usernames to brute-force (comma-sep or file) |
| `--proxy <proxy>` | HTTP proxy (e.g., `http://127.0.0.1:8080`) |
| `--cookie <str>` | Cookie for authenticated scans |
| `--headers <str>` | Custom HTTP headers |
| `--http-auth <u:p>` | HTTP basic auth |
| `-o <file>` | Output file |
| `--format <fmt>` | cli / json / cli-no-colour |
| `--throttle <ms>` | Milliseconds between requests |
| `--request-timeout <n>` | Timeout per request |
| `--connect-timeout <n>` | Connection timeout |
| `--max-threads <n>` | Max concurrent threads (default 5) |
| `--wp-content-dir <dir>` | Override wp-content dir if non-standard |
| `--wp-plugins-dir <dir>` | Override plugins dir |
| `--disable-tls-checks` | Skip SSL verification |
| `--ignore-main-redirect` | Don't follow main domain redirect |
| `--force` | Proceed even if target isn't WordPress |
| `--update` | Update WPScan database |
| `-v` / `--verbose` | Verbose output |
| `--stealthy` | Passive detection only + random UA |

## Enumeration Targets

```bash
# Users only (fastest, high value)
wpscan --url https://target.com --enumerate u

# Vulnerable plugins only (most impactful)
wpscan --url https://target.com --enumerate vp --api-token $TOKEN

# Full aggressive enum
wpscan --url https://target.com \
    --enumerate ap,at,u,tt,cb,dbe \
    --plugins-detection aggressive \
    --api-token $TOKEN

# Config backups (wp-config.php.bak, wp-config.php~, etc.)
wpscan --url https://target.com --enumerate cb

# Database exports
wpscan --url https://target.com --enumerate dbe
```

## Password Attacks

```bash
# Brute-force via wp-login.php (slower, stealthier)
wpscan --url https://target.com \
    --usernames admin \
    --passwords /usr/share/wordlists/rockyou.txt \
    --password-attack wp-login

# XML-RPC multicall (faster, bypasses rate limiting)
wpscan --url https://target.com \
    --usernames admin \
    --passwords /usr/share/wordlists/rockyou.txt \
    --password-attack xmlrpc-multicall

# Enumerate users first, then attack
wpscan --url https://target.com --enumerate u --api-token $TOKEN -o users.json --format json
cat users.json | jq -r '.users[].username' > found_users.txt
wpscan --url https://target.com -U found_users.txt -P passwords.txt
```

## Authenticated Scanning

```bash
# With session cookie (login via browser first)
wpscan --url https://target.com \
    --cookie "wordpress_logged_in_xxx=admin%7C..."

# With admin credentials (finds more plugins/themes)
wpscan --url https://target.com \
    --enumerate ap \
    --username admin --password 'AdminPass123!' \
    --plugins-detection aggressive
```

## Common Findings

| Finding | Impact |
|---------|--------|
| Outdated plugins with CVEs | RCE / LFI / SQLi |
| User enumeration via author archive | Enables password attacks |
| xmlrpc.php enabled | Brute-force amplification (multicall = 500 tries/request) |
| readme.html / license.txt | WordPress version disclosure |
| Timthumb vulnerability | Remote code execution |
| Debug log exposed (`/wp-content/debug.log`) | Info disclosure, credentials |
| Config backup (`wp-config.php.bak`) | Database credentials |
| DB export in web root | Full database dump |
| Registration open | Account creation → plugin exploit |

## Common Workflows

```bash
# Quick recon pass
wpscan --url https://target.com --enumerate u,vp,vt \
    --api-token $TOKEN -o wp_scan.json --format json

# Parse JSON output for CVEs
cat wp_scan.json | jq '.plugins | to_entries[] | {plugin: .key, vulns: .value.vulnerabilities}'

# Stealthy scan (minimize fingerprint)
wpscan --url https://target.com --stealthy --enumerate u \
    --throttle 2000

# Through proxy for manual review
wpscan --url https://target.com --proxy http://127.0.0.1:8080 \
    --disable-tls-checks --enumerate u,vp --api-token $TOKEN
```

## Key Attack Paths

```
1. Enumerate users → brute-force weak passwords → admin access → RCE via theme editor
2. Find vulnerable plugin (CVE) → exploit SQLi/LFI/RCE directly
3. xmlrpc.php enabled → multicall brute-force (bypass account lockout)
4. Config backup found → extract DB creds → wp_users table → crack password hashes
5. Registration enabled + vulnerable plugin → account takeover chain
```

## Resources

| File | When to load |
|------|--------------|
| `references/wordpress-testing.md` | XML-RPC abuse, REST API enum, auth bypass, manual exploitation |
