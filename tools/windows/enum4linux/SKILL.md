---
name: enum4linux
description: "SMB and Windows/Samba enumeration tool that extracts users, shares, groups, OS info, and password policies via null sessions or with credentials. Use when asked to enumerate a Windows host or Samba share, find users via SMB, extract domain info, or check for null session access."
license: GPL-2.0
compatibility: "Linux. Install: apt install enum4linux or use enum4linux-ng (Python rewrite). Pre-installed on Kali/Parrot."
metadata:
  author: AeonDave
  version: "1.0"
---

# enum4linux

SMB enumeration tool — extracts users, shares, groups, and domain info from Windows/Samba hosts.

## Quick Start

```bash
# Full enumeration (null session)
enum4linux -a 192.168.1.10

# With credentials
enum4linux -a -u admin -p password 192.168.1.10

# Modern rewrite (enum4linux-ng recommended)
enum4linux-ng -A 192.168.1.10
```

## Flags (Classic)

| Flag | Description |
|------|-------------|
| `-a` | All: runs `-U -S -G -P -r -o -n -i` |
| `-U` | User list via RPC |
| `-M` | Machine list |
| `-S` | Share enumeration |
| `-P` | Password policy |
| `-G` | Group enumeration |
| `-r` | User list via RID cycling |
| `-R <range>` | RID range (default `500-550,1000-1050`) |
| `-u <user>` | Username for auth |
| `-p <pass>` | Password for auth |
| `-d` | Debug mode |
| `-v` | Verbose |
| `-o` | Get OS information |
| `-i` | Printer info |
| `-n` | Nmblookup info |

## enum4linux-ng Flags (Recommended)

| Flag | Description |
|------|-------------|
| `-A` | All checks |
| `-u <user>` | Username |
| `-p <pass>` | Password |
| `-oJ <file>` | JSON output |
| `-oY <file>` | YAML output |
| `-t <n>` | Timeout |
| `--no-color` | Disable color output |

## Common Workflows

```bash
# Full null session enum (no creds)
enum4linux -a 10.10.10.100

# Authenticated full enum
enum4linux -a -u "DOMAIN\user" -p "password" 10.10.10.100

# RID cycling for user enumeration
enum4linux -r -R 500-2000 10.10.10.100

# Modern approach with JSON output
enum4linux-ng -A 10.10.10.100 -oJ output.json

# Share enumeration only
enum4linux -S 10.10.10.100

# Password policy extraction
enum4linux -P 10.10.10.100
```

## Key Info Extracted

- Domain/workgroup name and OS version
- User accounts (via RPC and RID brute-force)
- Shares (writable/readable)
- Group memberships
- Password policy (lockout threshold, complexity)
- Printer and session info

## Resources

| File | When to load |
|------|--------------|
| `references/smb-enumeration.md` | SMB enumeration techniques, smbclient commands, null session exploitation |
