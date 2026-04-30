---
name: watson
description: "Watson: Windows patch vulnerability analyzer that identifies missing KB patches and maps to known exploitable CVEs. Use when assessing local privilege escalation vectors via kernel exploits, determining patchability before attacking, or prioritizing which unpatched systems are vulnerable to public CVE exploits."
license: BSD-3-Clause
compatibility: "Windows x86/x64. Compiled .NET binary. Run as user (user-mode checks) or admin (full system visibility). No admin required for basic checks."
metadata:
  author: AeonDave
  version: "1.1"
---

# Watson

Windows patch vulnerability scanner — identifies missing KBs and maps to exploitable CVEs.

## Quick Start

```cmd
# Basic patch check
Watson.exe

# Verbose output
Watson.exe -v

# Export to file
Watson.exe > watson_output.txt
```

## Core Functionality

Watson automatically:
1. Detects Windows version & build
2. Enumerates installed patches (KB numbers)
3. Maps missing patches to known CVEs
4. Prioritizes by exploitability & severity
5. Shows if public exploit/PoC is available

## What Watson Checks For

| Category | Examples |
|---|---|
| **Kernel Exploits** | DirtyCOW, Dirty Pipe, OverlayFS (CVE variants) |
| **Privilege Escalation** | ElevatedPotato, PrintNightmare, PetitPotam |
| **Credential Dumping** | LSASS dumping CVEs |
| **Authentication Bypass** | Zero-click admin elevation bugs |
| **Information Disclosure** | Kernel pointer leaks, memory disclosure |

## Output Interpretation

Watson displays:
- **CVE ID** — Official CVE identifier
- **Affected versions** — Which Windows versions are vulnerable
- **Severity** — Critical / High / Medium / Low
- **Exploit availability** — "PoC exists", "Public exploit available", "No known PoC"
- **Status** — "VULNERABLE" if patch missing

Example output:
```
[!] CVE-2016-3309 — Windows Kernel Elevation of Privilege
    Affected: Windows 7 SP1, Windows Server 2008 R2 SP1
    Severity: Critical
    Status: VULNERABLE (KB missing)
    PoC: Available (github.com/abysssol/CVE-2016-3309)
```

## Workflow

### 1. Initial Assessment

```cmd
# Run Watson on target
Watson.exe > patching_status.txt

# Review output for CRITICAL + VULNERABLE
# Identify exploits with public PoC
```

### 2. Prioritize Exploits

Focus on:
- **CRITICAL** + PoC available
- **HIGH** + commonly exploited (PrintNightmare, etc)
- Exploit matches target's running services (e.g., PrintSpooler for PrintNightmare)

### 3. Determine Mitigation Status

```cmd
# Check if services are running
sc query spooler              # Print Spooler
sc query WinRM               # Windows Remote Management
tasklist | findstr service   # Check for running services
```

### 4. Exploit Selection

```cmd
# Example: PrintNightmare (CVE-2021-34527)
# 1. Watson shows "VULNERABLE" + PoC available
# 2. Check if Print Spooler is running
#    → sc query spooler
# 3. If running + vulnerable, exploit

# Example: ElevatedPotato
# 1. Watson shows kernel CVE exploitable
# 2. Compile/obtain ElevatedPotato
# 3. Run → SYSTEM shell
```

## Comparison with WinPEAS

| Tool | Focus |
|---|---|
| **Watson** | Kernel patches + public CVE mapping |
| **WinPEAS** | Configuration misconfigurations (services, SUID, perms) |
| **Together** | Complete privilege escalation surface → patch + misconfig vectors |

Use Watson first (fast, specific), then WinPEAS for broader enumeration.

## Common Vulnerable Patterns

### Old Windows Versions (7, 2008 R2)

```cmd
Watson.exe
# Usually many CRITICAL vulnerabilities
# High likelihood of working PoC
```

### Modern Windows (10, 2019+) Unpatched

```cmd
Watson.exe
# Fewer vulnerabilities, but newer patches often take time to roll out
# Check monthly security updates status
```

### Windows with Disabled Windows Update

```cmd
Watson.exe
# May show many gaps; check last Windows Update date
# Can be indicator of other misconfigurations
```

## Manual Patch Verification

If Watson output is unclear:

```powershell
# Get all installed patches
Get-HotFix | Select HotFixID

# Check specific KB
Get-HotFix | Select HotFixID | Select-String "KB2999226"
# Returns nothing → patch NOT installed → VULNERABLE

# Get Windows version
[System.Environment]::OSVersion.Version
# or
Get-WmiObject -Class Win32_OperatingSystem | Select Caption, BuildNumber
```

## Integration with Other Tools

| Tool | Use |
|---|---|
| **WinPEAS** | Run first for full enum, Watson confirms kernel vulns |
| **Exploit frameworks** | SearchSploit / Metasploit to find working exploits |
| **Custom exploit repos** | GitHub has PoCs for most Watson-identified CVEs |

## Resources

| File | When to load |
|---|---|
| `references/` | Kernel exploit compilation, CVE remediation, safe testing practices |
