# Anti-Analysis Hardening — Detail

Windows-side detail. Linux anti-debug / anti-sandbox tradecraft (PTRACE_TRACEME, `/proc/self/status`, static musl, seccomp probe, KVM/CPUID detection) is in [`linux-edr-evasion.md`](linux-edr-evasion.md) §6.

Run ALL checks before any evasion/payload setup — generating signals in a sandbox is equivalent to detection.

Primary doctrine: **near-zero IOC by design**. Every passive read-only check generates zero telemetry. Every invasive check (syscalls, DR mutation, thread info queries) generates at least one observable event. The goal is a check layer that is indistinguishable from a normal process at the kernel event level.

Single-signal hard blocks create false positives and generate unnecessary signals. Aggregate weak passive indicators into a score instead.

## Anti-Debug Checks

| Check | API / Method | Notes |
|-------|-------------|-------|
| `PEB.BeingDebugged` | Read PEB byte only — no syscall, no kernel event | Cheapest possible baseline signal |
| Parent process sanity | PPID / parent image allowlist checks | Unusual parent (e.g. automation runner) raises score |
| Debugger process/window heuristics | Process list + window/title patterns | Keep as weak signal, not hard block |
| Timing drift | `GetTickCount64` / `RDTSC` delta across sleep | Sandbox fast-forward remains high-value passive signal |
| Heap flag anomalies | `PEB→ProcessHeap→Flags` sanity checks | Supplemental only; platform-dependent |

### Optional invasive checks (secondary tier — off by default)

Each of these generates at least one kernel-level observable event. Use only when the operational target profile explicitly justifies the IOC cost:

- `NtQueryInformationProcess(ProcessDebugPort)` — kernel call, logged by ETW-TI
- `NtSetInformationThread(ThreadHideFromDebugger)` — one-way, kernel state change, detectable; never use on CLR-managed threads
- DR register read/write (`GetThreadContext` / `SetThreadContext`) — kernel round-trip; EDRs themselves set DRs → false-positive risk is high

Default: disabled. Enable explicitly when secondary validation is needed and the added signal cost is acceptable.

## Anti-VM / Anti-Sandbox Checks

| Check | Method | Notes |
|-------|--------|-------|
| Sleep acceleration | RDTSC delta across `Sleep(5000)` — pure usermode, zero syscall | Most reliable signal; generates no IOC |
| Low-resource profile | Core count / RAM / uptime below realistic target baseline | Stronger when combined, weak alone |
| Process heuristics | Common sandbox/analysis process names | Weight as weak-to-medium signal |
| User-interaction heuristics | Mouse/foreground activity over time | Avoid short single-sample decisions |
| Hostname/username patterns | Lab/default naming conventions | Good additive signal |

### Optional VM artefact checks (secondary tier)

- CPUID hypervisor bit
- VMware/VirtualBox registry artefacts
- MAC OUI vendor checks

Do not hard-fail solely on these artefacts; many legitimate enterprise endpoints are virtualized.

## Scoring Example Policy

- Assign low weights to each passive signal.
- Trigger anti-analysis path only after multiple independent indicators exceed threshold.
- Never exit or self-delete on one indicator; prefer degraded execution path.

## IAT Hygiene

Remove suspicious API imports by:

1. **PEB walk + API hashing** (§8 SKILL.md) — zero IAT entries for `VirtualAlloc`, `CreateThread`, etc.
2. **Fake dead-code imports** — benign imports (`MessageBoxA`, `RegOpenKeyA`) that never execute create noise. Use `#[cfg(false)]` / `if false {}` to guarantee no execution.
3. **Delay imports via LoadLibrary/GetProcAddress** — IAT shows only `kernel32.dll` loader stubs.

Combined with §9 string obfuscation → zero readable API strings + zero suspicious IAT.

## Entropy Management

ML-based AV classifies encrypted/packed binaries by Shannon entropy. Target: **< 7.2 bits/byte** per section.

| Technique | Entropy impact |
|-----------|---------------|
| Custom Base64 with symbol-like alphabet (§10 SKILL.md) | 8.0 → ~6.0 bits/byte |
| `zlib deflate` before encryption | Final Base64 output is lower entropy |
| Embed English dictionary as `.data` | Lowers whole-binary average ~0.5 bit/byte |
| Strip debug symbols (`-s -w` / `strip`) | Smaller .text → better code/data ratio |
| Avoid AES ciphertext in `.rdata` | AES output ~8.0 entropy → YARA/entropy flag |
| `#[link_section = ".data1"]` for payload | Isolates high-entropy section; per-section scoring |
| RC4 vs AES | RC4 has no GF(2^8) polynomial fingerprint; splitmix64 XOR preferred (zero algorithmic footprint) |

Measure entropy with `pe-sieve`, `sigcheck -e`, or a Python script after each pipeline change.
