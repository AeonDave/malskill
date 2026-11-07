# Research and Weaponization Methodology

Load when you need a **new** bypass (catalogued methods dead on your target build), or when porting a published PoC into loader-grade tooling. This is the loop: find → evaluate → port → qualify → own it.

## 1) Discovery — where new bypasses come from

Every UAC bypass abuses one leg of the auto-elevate triad (`autoElevate` manifest + Windows signature + trusted path). Hunt systematically instead of waiting for catalogs:

### Auto-elevate binary hunting
```powershell
# Every autoElevate binary on the box — the raw hunting list
Get-ChildItem C:\Windows\System32, C:\Windows\SysWOW64 -Filter *.exe |
  ForEach-Object { (Get-Item $_.FullName).VersionInfo | ? { $_.CompanyName -match "Microsoft" } }
# Then check each manifest for autoElevate=true (mt.exe / or parse XML resource #24)
```
For each hit, ask: does it load a DLL/registry value/COM object that a user can influence? That's the bypass. Documented examples of the hunt paying off: `eudcedit.exe` (Private Character Editor, 2025 writeup), `SystemReset.exe` (Server 2019 DLL hijack), the whole fodhelper/eventvwr family.

### COM auto-elevation CLSID hunting
```powershell
# Classes whose LocalizedString points into system32 + Elevation flag = auto-elevating COM
Get-ChildItem "HKLM:\SOFTWARE\Classes\CLSID" -Recurse -ErrorAction SilentlyContinue |
  Where-Object { $_.GetValue("LocalizedString") -like "*system32*" }
# Then check for the Elevation subkey (Enabled=1) — CoCreateInstance from medium
# integrity succeeds and the class's privileged methods run high
```

### Scheduled task + WNF trigger tracing
Auto-elevated `taskhostw`-style tasks (`\UnifiedConsent\UnifiedConsentSyncTask` = UACME #83) load DLLs from redirected paths when a state fires. Hunt: enumerate auto-elevate scheduled tasks, trace which DLL they resolve, find the state/registry trigger (`logman`, WNF tracing, ETW registry provider) that wakes them. The trigger is often the unpublished part — UACME gives you the method, the trigger mechanics you extract yourself (see "making it your own" below).

### Source landscape (where to watch)

| Source | What it gives you | Cadence |
|---|---|---|
| [UACME](https://github.com/hfiref0x/UACME) | Canonical numbered catalog + per-method sources; actively maintained (MSVS 2026 config); Issues are gold — method validity debates live there (e.g. method 34 reported patched but re-confirmed working on 24H2) | watch releases + issues |
| [Elastic Security Labs UAC piece](https://www.elastic.co/security-labs/threat-command/exploring-windows-uac-bypasses-techniques-and-detection-strategies) | The primitives + detection model — write your bypass against what they describe | read once, re-check on rule updates |
| BOF collections: [BofAllTheThings](https://github.com/N7WEra/BofAllTheThings), awesome-bof | BOF-shaped implementations ready to port | watch |
| Researcher blogs (MDSEC, SpecterOps, offsec.rokibulroni, g3tsyst3m) + DEF CON/BlackHat slides | New primitives and class discoveries | periodic |
| HackTricks UAC page | Fast per-build method index | quick reference |
| GitHub topics `uac-bypass`, `bypassuac` | Fresh PoCs, derivative implementations | watch |
| MITRE [T1548.002](https://attack.mitre.org/techniques/T1548/002/) | Taxonomy anchor for reporting | static |

## 2) Evaluate a candidate before porting

- **Which leg does it abuse?** (manifest autoElevate / COM class / task side-load) — determines how it dies when Microsoft tightens that leg.
- **What does it write?** File drops and HKCU writes are the cleanup ledger; fewer artifacts = longer life.
- **What signals it in flight?** Map the ETW/Sysmon events (registry write → auto-elevate spawn → DLL load) against the Elastic/Fibratus detection model. If the correlation is generic, expect short life; if the trigger is obscure (WNF state), expect longer.
- **Build validity**: check UACME issues + your own test matrix. Catalog age ≠ validity — method 34 was reported patched and re-confirmed working on 24H2.

## 3) Making it your own (PoC → production)

1. **Re-derive, don't paste**: reproduce the PoC's primitive from your own harness first (your registry writes, your trigger, your payload). You inherit the understanding, not the signature.
2. **Strip the tell**: published PoCs ship obvious constants (fixed temp paths, fixed DLL names, console windows). Parameterize paths, derive names from a per-build seed, windowless execution.
3. **Embed the cleanup ledger** (see `implementation-patterns.md`) — every artifact enumerated with owner and trigger. PoCs never clean up; production must.
4. **Add the failure contract**: bounded wait on a completion signal, single retry at most, loud failure attribution (policy vs method-dead vs trigger-failed).
5. **Shape for your loader**: BOF form (agent owns the channel), or in-loader form with the chain arbiter (UAC step and SYSTEM step in separate processes — see `implementation-patterns.md`).
6. **Kill the classic telemetry**: no `cmd.exe` intermediate (DCOM/trusted-path shape), windowless, no `Start-Process powershell` chains.

## 4) Qualification loop (per build, per release)

```text
for build in [19041, 22000, 22621, 26100, 26200, target]:
    1. Snapshot VM per build
    2. Run the bypass → assert high-integrity payload callback received
    3. Capture telemetry: Sysmon (registry/file/process), ETW-TI, Defender sample
    4. Verify cleanup ledger (every artifact re-checked)
    5. Record: method ID, build, result, telemetry deltas — regression table
on Windows feature update: re-run the matrix; retire dead methods loudly
```

Keep the matrix results in the project (not the skill): a bypass without a recorded qualification date is a liability. When a method dies, mark it in your table immediately — stale methods shipped on new builds are the loudest alerts.

## 5) Anti-patterns of research

- Trusting blog claims without live re-test (methods get patched the week they're published).
- Releasing a port with the PoC's exact strings/paths — you ship someone else's signature.
- Skipping the cleanup ledger because "the elevated process will overwrite it anyway".
- Treating UACMe validity as current: the catalog documents *history*; your matrix documents *now*.
