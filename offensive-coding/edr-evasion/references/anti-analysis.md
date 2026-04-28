# Anti-Analysis Hardening — Detail

Run ALL checks before any evasion/payload setup — generating signals in a sandbox is equivalent to detection.

## Anti-Debug Checks

| Check | API / Method | Notes |
|-------|-------------|-------|
| IsDebuggerPresent | `PEB.BeingDebugged` byte | Trivially bypassed; still worth including |
| NtQueryInformationProcess | `ProcessDebugPort (7)` → non-zero = debugger | Harder to patch; use via indirect syscall |
| Heap flags | `PEB→ProcessHeap→Flags & 0x40` (HEAP_TAIL_CHECKING_ENABLED) | Set by kernel when debugger attached |
| `NtSetInformationThread(ThreadHideFromDebugger)` | Hides thread from debugger; EXCEPTION_DEBUG_EVENT not delivered | One-way; apply to non-CLR threads only |
| Timing check | `GetTickCount64` / `RDTSC` delta across sleep | Sandbox fast-forwards sleep → delta < expected |
| Hardware breakpoints | Check `ctx.Dr0-Dr7` via `GetThreadContext` — non-zero = debugger | EDRs also set DRs → false positives possible |
| Parent process check | Query PPID via `NtQueryInformationProcess(ProcessBasicInformation)` → compare vs known-good | Unusual parent (e.g. `python.exe`) → sandbox |

## Anti-VM / Anti-Sandbox Checks

| Check | Method | Notes |
|-------|--------|-------|
| CPUID hypervisor bit | `CPUID EAX=1` → ECX bit 31 | VMware/Hyper-V/KVM set this |
| Registry artefacts | `HKLM\SOFTWARE\VMware Inc.`, `VirtualBox Guest Additions` | Simple but effective |
| Process list | `vmtoolsd.exe`, `vboxservice.exe`, `sandboxie.exe`, `wireshark.exe` | Sandbox-typical processes |
| MAC address OUI | `00:0C:29` (VMware), `08:00:27` (VirtualBox) | NIC vendor lookup |
| Disk size | < 60 GB → likely sandbox image | |
| Mouse movement | No movement over 10s → headless sandbox | `GetCursorPos` delta |
| Screen resolution | < 800×600 → headless or minimal sandbox | |
| GetForegroundWindow | null or desktop only → no user logged in | |
| Sleep acceleration | Measure wall-clock delta after `Sleep(5000)` + RDTSC | Most reliable sandbox check |

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
