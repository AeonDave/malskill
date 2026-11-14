---
name: uac-evasion-dev
description: "UAC bypass implementation for loaders and agents: auto-elevate mechanics, registry/class-COM/auto-elevate-binary bypass families, BOF integrations, prompt-free medium→high integrity escalation, and UAC→admin→SYSTEM chaining. Use when implementing or reviewing an in-tool UAC bypass — not for choosing a privesc vector (post-exploit-technique)."
license: MIT
compatibility: "Windows 10 19041+ / Windows 11 24H2-25H2 x64. Method validity is build-specific: verify per target build before shipping."
metadata:
  author: AeonDave
  version: "1.0"
---

# UAC Evasion Development

Implement prompt-free medium→high integrity escalation **inside a loader/agent**, not as a separate exploit step. Scope: the medium→high jump. Token-level privilege escalation to SYSTEM (Potato family) is the privesc catalog in `post-exploit-technique/references/windows-privesc.md`; the chain orchestration that stitches UAC→admin→SYSTEM is covered here.

## When to activate

- Implementing a UAC bypass inside a loader, agent, or BOF
- Reviewing a bypass for OPSEC (cleanup, artifacts, telemetry)
- Chaining medium→high→SYSTEM in one process tree
- Deciding whether a bypass is worth it vs asking the user for elevation

## UAC mechanics that gate every bypass

- Elevation policy: `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System` — `ConsentPromptBehaviorAdmin` (`0` = silent elevate, `2` = prompt on secure desktop [default], `5` = consent for non-Windows binaries only) and `EnableLUA`. Enumerate before choosing a method — `0` means no bypass is needed.
- **Auto-elevate requirements** for a binary to self-elevate without prompt: `autoElevate="true"` in its manifest, signed by the Windows publisher, launched from a trusted path. Every bypass family abuses one leg of this triad.
- **COM auto-elevation**: CLSIDs whose `LocalizedString`/`Elevation` registry values point into system32 elevate on CoCreateInstance from medium integrity — the class-based family (`CMSTPLUA`, `ICMLuaUtil`, …).
- High-integrity processes only check the first two legs for *their own* children — once you are high, spawning elevated children is free.

## Bypass families (implementation-oriented)

| Family | Mechanism | Notes |
|---|---|---|
| **Registry hijack of auto-elevate binary** | Overwrite a per-user value that an auto-elevate binary executes (e.g. `fodhelper`/`ComputerDefaults` progid class → your command) | Classic family; well-known, heavily detected by 2026 rules — use only as baseline |
| **Class-COM elevation** | `CoCreateInstance` an auto-elevating COM class from medium integrity, call its privileged method | BOF-friendly (see below); no file drop if the class method takes your payload as argument |
| **Auto-elevate binary side-load** | Plant a DLL/registry redirect that an auto-elevate binary or scheduled task loads from a user-writable location | The UnifiedConsent method (UACME #83) lives here |
| **Scheduled-task DLL side-load** | Auto-elevated `taskhostw.exe` task side-loads a DLL whose path you redirect per-user | UnifiedConsent (`\UnifiedConsent\UnifiedConsentSyncTask` → `unifiedconsent.dll`) — valid since 19041, catalogued as [UACME #83](https://github.com/hfiref0x/UACME) |
| **Event Viewer deserialization** | `eventvwr.exe` auto-elevate + MMC snap-in deserialization | Public BOF: [Octoberfest7/EventViewerUAC_BOF](https://github.com/Octoberfest7/EventViewerUAC_BOF) |
| **Trusted-path via DCOM** | Invoke the target binary through DCOM so no `cmd.exe` command line is logged | Public BOF: [netero1010/TrustedPath-UACBypass-BOF](https://github.com/netero1010/TrustedPath-UACBypass-BOF) |

Method freshness: the canonical catalog is [UACME](https://github.com/hfiref0x/UACME) (methods numbered, per-build validity in its `Sources/`); community BOF collections ([BofAllTheThings](https://github.com/N7WEra/BofAllTheThings), awesome-bof) track BOF implementations. Cobalt Strike 4.12 (Nov 2025) added a built-in `bypassuac` — treat its signature footprint as public knowledge when you roll your own. Verify every method against your **specific target build**: method validity is build-specific and degrades with each Windows update.

## Implementation requirements (loader-grade)

- **No console window**: launch the auto-elevate binary/windowless (CREATE_NO_WINDOW, window class abuse) — a visible consent flash defeats the purpose.
- **Payload delivery to the elevated context**: prefer methods where the elevated side reads your payload from a path you control (registry value, planted DLL, COM method argument). Avoid dropping a second EXE.
- **Cleanup is part of the bypass**: restore every registry value and delete every planted file *after* the elevated payload starts but while you still own the medium-integrity process. A bypass that leaves `\UnifiedConsent` or planted DLLs behind is forensic gold.
- **Failure path**: if the elevated side does not signal success (event/object/pipe), fail loudly enough to avoid silent loops — re-running a side-load bypass in a loop is a detection multiplier.
- **BOF shape**: a UAC bypass as BOF keeps the agent process as the medium-integrity owner; the elevated payload should call back via the agent's normal channel, not open a second C2 session.

## UAC → admin → SYSTEM chain

Once high integrity, SYSTEM requires a token-level vector (SeImpersonate potato family — catalog in `post-exploit-technique/references/windows-privesc.md`) or a direct kernel path. Chaining design points (field-reported, project evidence: AshuraLoader `chain.rs`):

- One EXE can own the whole chain: bootstrap UAC → spawn admin child (injector) → deliver into a SYSTEM process. Ambiguity between "UAC failed" and "SYSTEM delivery failed" is the failure mode to design away: use a single ownership arbiter (first process to observe a known state wins; on ambiguity, abort — never double-fallback).
- **RushPotato** (project-invented, field-reported, not public): COM secure-binding escalation to SYSTEM — activates a service COM class, wraps IStorage in-memory, OBJREF moniker with attacker display name, `CoGetInstanceFromIStorage`, impersonates per-callback accepting only `S-1-5-18` at `SecurityImpersonation`. Qualified on Win11 26300 (C+Rust). It sits in the potato family of SYSTEM vectors, not UAC.
- **OXID/RPC dispatch hook** (project-verified mechanics, runtime **not** qualified on 26300 — RPCSS behavior changed; GodPotato-class tools failed on the same build): hook the dispatch entry of `RPC_SERVER_INTERFACE` in combase.dll, serve the OBJREF via a named pipe, `FSCTL_PIPE_IMPERSONATE`, `CreateProcessWithTokenW`. Do not ship this path without re-qualification on the target build.
- Keep the UAC step and the SYSTEM step in **separate processes**: a crash in the SYSTEM vector must not take the medium-integrity bootstrap down.

## Detection landscape (what you are writing against)

- Primary detection surface is **behavioral correlation**: medium-integrity process spawning/writing what an auto-elevate binary will consume, then consent.exe never appearing while a high-integrity child appears ([Elastic: Exploring Windows UAC Bypasses](https://www.elastic.co/security-labs/threat-command/exploring-windows-uac-bypasses-techniques-and-detection-strategies)).
- Registry write to `HKCU\...\Classes` progid keys or `Volatile Environment` immediately followed by an auto-elevate binary launch is the generic signature of the registry family — the scheduled-task side-load family (UnifiedConsent) instead shows a planted DLL path + taskhostw load.
- Cleanup reduces artifacts but not the in-flight correlation: the elevated-side action (DLL load in taskhostw, COM method call) is what defenders alert on. Design the elevated step to look like the task's normal work.

## Quick review checklist

- [ ] UAC policy enumerated first (`ConsentPromptBehaviorAdmin == 0` → skip the bypass)
- [ ] Method validity confirmed on the exact target build (UACME catalog + live test)
- [ ] Zero file drops outside user-writable paths; every planted artifact has a cleanup owner
- [ ] Elevated side signals success/failure back; no blind retry loops
- [ ] Chain: UAC step and SYSTEM step in separate processes; single ownership arbiter
- [ ] BOF variant keeps the agent as channel owner; no second C2 session
- [ ] Cleanup verified by re-reading every touched registry key/file path after completion

## Resources

- [references/implementation-patterns.md](references/implementation-patterns.md) — load when implementing: UnifiedConsent step-by-step (UACME #83), chain orchestration pattern, cleanup ledger, BOF integration skeleton
- [references/research-and-weaponization.md](references/research-and-weaponization.md) — load when catalogued methods are dead on your build or you need a new one: discovery loops (autoElevate manifest hunting, COM CLSID hunting, task/WNF trigger tracing), source landscape, PoC→production porting checklist, per-build qualification matrix
- `post-exploit-technique/references/windows-privesc.md` — privilege/SYSTEM escalation catalog (potato family); load for the high→SYSTEM half of the chain
