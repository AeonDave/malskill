---
name: edr-evasion
description: |
  Universal patterns, constraints, and trade-offs for Windows EDR evasion in
  offensive tooling (verified against S1, Defender, CrowdStrike — 2026). Covers
  syscall dispatch (indirect, SSN, NtContinue), stack spoofing (SilentMoonwalk),
  sleep obfuscation (unmap/remap, XOR+NOACCESS), memory strategies (module stomp,
  private RWX, dual-view W^X), ETW/AMSI bypass, HWBP/VEH, PIC execution, API
  resolution, payload encryption, and PE section ratios. Use when implementing,
  reviewing, or hardening evasion in any Windows implant, loader, beacon, BOF, or
  shellcode runner. Activate for: call stack spoofing, sleep encryption, ntdll
  unhooking, direct/indirect syscalls, module stomping, ETW/AMSI bypass,
  Fritter/Donut constraints, AES vs. XOR detection, or deciding which evasion
  features to add vs. cut.
license: MIT
metadata:
  author: kRustyLoader
  version: "2.2"
---

# EDR Evasion — Universal Patterns & Constraints

Field-tested principles for Windows EDR/AV evasion. Verified against S1, Defender, and CrowdStrike (2026). Project-agnostic — applies to any loader, implant, or tool runner targeting Windows 10/11.

---

## 0a. Loader as Primary EDR Signal Source

EDRs do not evaluate a process at a single point in time. They accumulate a weighted signal score across the **entire execution timeline**: syscalls, memory allocation patterns, page permission transitions, ETW events, call stack shapes, IAT content, and in-memory byte patterns. Final verdict is a sum.

The loader runs first. Every decision the loader makes — how memory is allocated, whether VirtualProtect is called, whether ETW is emitting events during decryption, whether known loader bytes are present in any page — contributes to the score **before the payload executes a single instruction**. The payload inherits that accumulated score and works from it, upward.

### Why Donut made every executable malicious

Donut's loader stub is a well-known shellcode with documented byte signatures. Its default allocation pattern is `VirtualAlloc(RWX)`. Its PE-loader code path matches ML models trained on Donut specifically. The result: by the time the beacon's first instruction ran, the process already had 3–4 strong independent signals. The payload behavior was irrelevant — the verdict was reached at loader stage.

### What the loader must guarantee at handoff

The goal of the loader layer is to reach payload execution with the process's accumulated signal score **at or near zero**. Concrete requirements derived from a minimal loader execution order:

| Loader decision | Wrong (signal-generating) | Right (zero-signal) |
|---|---|---|
| Anti-debug/sandbox checks | `NtQueryInformationProcess`, `NtSetInformationThread` | PEB byte reads + KUSER_SHARED_DATA reads only — no kernel events |
| ETW patch method | `VirtualProtect` on ntdll page (permission change event) | `NtWriteVirtualMemory` — kernel COW on SEC_IMAGE, no permission change event |
| ETW patch timing | After startup delay (delay emits ETW events) | **Before** startup delay so no ETW events during sleep masking or decrypt |
| Payload memory | `VirtualAlloc(RWX)` or `VirtualAlloc` then `VirtualProtect(RX)` | Module stomp (`SEC_IMAGE` backing), Ghostly Hollow (dual-view), or Mockingjay (existing RWX section) |
| Loader bytes in memory | Donut stub, reflective loader shellcode with known signatures | PIC Rust `no_std` loader — no recognizable signature; wiped post-decrypt |
| Plaintext payload lifetime | Survives in heap post-exec (EDR periodic scanner finds it) | `write_volatile` zero after decrypt; stage scrub thread cleans post-handoff |
| Key/nonce material | Static bytes in `.rdata` | MBA-obfuscated per-build derivation — no raw key bytes in any section |

### Execution order constraint

The execution order in a minimal loader entry point is not arbitrary — it is a signal ordering constraint:

```
syscall::init()          ← indirect/RecycledGate layer live before ANY NT call
spoof::init()            ← call stack spoofed from first dispatch
anti_debug (passive)     ← PEB read only, zero kernel events
anti_sandbox (passive)   ← GetLastInputInfo + GetTickCount64 + GetForegroundWindow
etw::patch()             ← ETW silenced BEFORE startup delay and decrypt
startup delay            ← NtDelayExecution now runs without ETW-TI telemetry
reassemble + decrypt     ← RW allocation only; no RWX at any point
wipe encrypted buffer    ← plaintext lifetime minimized
etw::restore()           ← ETW restored before handoff
loader::execute()        ← payload placed in backed memory via stomp/hollow/mockingjay
stage_scrub              ← decode workspace zeroed after payload leaves it
```

Each step is positioned so that the EDR-observable event it generates either (a) produces zero telemetry, (b) produces telemetry indistinguishable from a benign process, or (c) is masked by the layer initialized above it in the stack.

**Implication for payload design**: do not open signal surfaces the loader closed. No `VirtualProtect` on ntdll in the beacon if the loader already patched ETW via `NtWriteVirtualMemory`. No `NtQueryInformationProcess` in the payload's anti-debug if the loader's passive checks already covered it. The payload's job is to keep the accumulated score near zero from the handoff point onward — not to rebuild defenses the loader already established.

---

## 0. Evasion Minimalism Principle

**Field-tested**: the strongest evasion configuration is the smallest one. Every evasion feature (VEH, HWBP, indirect syscall, ntdll unhooking, stack spoofing) is itself a detection surface. Feature accumulation produces net negative evasion when each feature generates its own indicator.

A 1,472-line reference beacon (zero VEH, zero DRs, zero unhooking, byte-patch ETW, NtContinue spoof, sleep obfuscation) evades S1/Defender/CS fully. A 6,126-line version with VEH+DR0+DR1+KnownDlls+RecycledGate+build-std is detected.

### Per-mode minimalism

| Mode | Minimal viable evasion | Rationale |
|------|----------------------|-----------|
| **Beacon (module stomp)** | NtContinue spoof + sleep obfuscation + byte-patch ETW | Unbacked needs stack spoof; sleep needs memory encrypt; ETW byte-patch is 1 byte |
| **Tool (backed EXE)** | PEB-resolved direct ntdll stubs + private RWX | Backed .text is legitimate; direct stubs avoid syscall indicators; private RWX is generic |
| **Tool (unbacked)** | indirect_syscall + SilentMoonwalk + E10 HWBP | Unbacked memory needs stack spoof + syscall interception |

### When to add features

Only when: (1) the specific detection is **confirmed active** against your EDR, (2) the feature's detection cost is **measured** lower than the vector it eliminates, (3) the feature can be **`#[cfg]` gated** so it's physically absent from binaries that don't need it.

---

## 1. Syscall Dispatch

### Indirect syscalls

Load SSN into EAX, jump to `syscall; ret` gadget (`0F 05 C3`) inside ntdll. Return address lands in ntdll → legitimate stack walk. Safe in all thread contexts.

### SSN resolution

- **RecycledGate** (preferred): enumerate all `Zw*` exports from EAT, sort by address → index = SSN. Works with all Nt* stubs hooked.
- **Hell's Gate** (fallback): parse Nt* stub prologue for `B8 xx xx 00 00`. Fails when EDR inline-hooks.

### Stack spoofing (NtContinue-based)

Build a CONTEXT with synthetic RSP (fake `BaseThreadInitThunk` → `RtlUserThreadStart` frames) → `NtContinue` → kernel replays context → syscall with fully spoofed stack.

### Hard rules

| Context | Safe dispatch | Unsafe |
|---------|--------------|--------|
| Main thread, no console | `spoofed_syscall`, `masked_syscall`, `indirect_syscall` | — |
| Main thread, console attached | `masked_syscall`, `indirect_syscall` | `spoofed_syscall` (crash) |
| TP worker thread | `tp_spoofed_syscall` (SMW), `indirect_syscall` | `masked_syscall` (RSP corruption), `spoofed_syscall` (crash) |
| Backed EXE (any thread) | PEB-resolved real ntdll stubs | indirect_syscall (generates MORE detection than hooked stubs) |

### Mode-based dispatch profile

Use runtime profile selection instead of one global syscall strategy:

| Profile mode | Primary path | Fallback | Best fit |
|-------------|--------------|----------|----------|
| 1 | `indirect_syscall*` wrappers | direct/clean stub if wrapper unavailable | unbacked beacon/tooling where stack legitimacy is weak |
| 2 | clean `Nt*` function pointers from fresh ntdll mapping | `indirect_syscall*` only for blocked calls | backed EXE where direct stub calls look normal |

Rule: if the binary is disk-backed and has legitimate `.text`, prefer clean/direct `Nt*` calls first. Save indirect spoof-heavy paths for unbacked execution contexts.

### Ghost Hunting (Emerging Kernel Detection)

Some EDR research prototypes correlate kernel handle issuance (pre-NTAPI return) against userland hook telemetry — if a handle exists with no hook observation, HWBP/VEH interception is inferred. Not yet widespread in production S1/CS/Defender (2026); `indirect_syscall` + `tp_spoofed_syscall` remain effective. Monitor threat intel for production rollout.

---

## 1b. SilentMoonwalk — .pdata-coherent Stack Spoofing

**Purpose**: spoof TP worker thread call stacks so every frame has a valid `.pdata` (RUNTIME_FUNCTION) entry. Unwinders (ETW-TI, EDR) verify frame sizes against UNWIND_INFO — mismatched sizes expose synthetic frames.

### Architecture

1. `find_jmp_reg_gadget(ntdll, min_frame)`: scan ntdll .text for `41 FF E4` (jmp r12); validate: no REX prefix, valid .pdata, frame_size >= min_frame, no frame pointer, past prolog
2. `select_chain_frames(ntdll)`: sample .pdata for 1-2 intermediate functions (frame 0x28–0x80, no FP)
3. `init_silentmoonwalk()`: populate SMW_GADGET, SMW_CHAIN[4], override BTIT/RUTS frame sizes from .pdata
4. `build_smw_stack(buf, extra_args)`: [jmp_r12 gadget] → [intermediates] → [BTIT] → [RUTS] → [0]
5. `tp_spoofed_syscall`: SMW_READY → jmp r12 (r12=continuation, r13=saved RSP); fallback → E8a

Flow: `push r12/r13 → lea r12,[continuation] → mov r13,rsp → mov rsp,synth → jmp gadget → syscall;ret → jmp r12 → mov rsp,r13 → pop r13/r12`. Unwinder: Nt(leaf) → gadget → intermediate → BTIT → RUTS → 0.

### Constraints

| Constraint | Detail |
|------------|--------|
| `min_frame >= 0x58` | NtMapViewOfSection has 10 args; 6 stack args, last at [rsp+0x50]. Smaller frame → arg overflow |
| LLVM rbx issue | List rbx in clobbers; LLVM may allocate it across asm block |
| Lock ordering | `E10_LOCK` → `SPOOF_BUF_LOCK` (never reverse). Contention → fallback to `indirect_syscall` |
| Beacon only | Tool_mode (backed EXE) skips SMW entirely (F9) |
| Init timing | After `init_stack_spoof_phase1`, before ntdll unhooking |

---

## 1c. Backed EXE vs Unbacked Memory

| Aspect | Backed EXE (tool_mode) | Unbacked (beacon, module stomp) |
|--------|----------------------|-------------------------------|
| Return address legitimacy | .text is in a known PE on disk → legitimate | Points to private/pagefile memory → suspicious |
| Syscall dispatch | Real ntdll stubs (even hooked) | indirect_syscall + gadgets |
| Stack spoofing | Unnecessary (adds indicators) | Essential (SilentMoonwalk or NtContinue) |
| VEH/HWBP | Counterproductive (detection signal) | Useful for E10 payload interception |
| DR registers | Zero DRs | DR0-DR3 for ETW/AMSI/E10 |

**Key insight**: for backed EXE, each evasion feature generates MORE detection than the attack surface it hides. S1 hooks collect telemetry but don't block; indirect syscall triggers "direct syscall from patched library" indicator.

---

## 2. Memory Allocation Strategies

### Private allocation (`NtAllocateVirtualMemory`)

- `PAGE_EXECUTE_READWRITE` — generic, shared with JIT/CLR. Weaker signal than section RWX.
- Post-exec: zero entire buffer → `NtFreeVirtualMemory`
- Best for: tool mode (one-shot, backed EXE)

### Module stomping

- Load legitimate DLL (xpsservices.dll, diasymreader.dll) → overwrite .text with payload
- Image-backed memory → legitimate in VAD (Virtual Address Descriptor)
- DllMain disable: null EP in LDR_DATA_TABLE_ENTRY (works for beacon; NOT for .NET tools with CLR threads)
- Best for: beacon mode (long-running, unbacked concern)

### Mapped section (dual-view W^X)

- `NtCreateSection(PAGE_EXECUTE_READWRITE)` → RW view + RX view on same physical pages
- W^X: VEH handler redirects writes from RX to RW view transparently
- **Kernel signal**: pagefile-backed section with X+W max_prot is nearly unique to shellcode loaders. Logged by ETW-TI `SectionCreate`.
- Superseded by private RWX for tool_mode (B1). Retained for beacon if module stomp fails.

### Decision matrix

| Scenario | Strategy | Why |
|----------|----------|-----|
| Beacon (primary) | Module stomp | Image-backed, legitimate VAD entry |
| Beacon (fallback) | alloc_rw + nt_protect(RX) | Private, no section kernel signal |
| Tool, backed EXE | Private RWX | Generic JIT pattern, one-shot |
| Tool, unbacked | Mapped section W^X | Need W^X for Fritter self-modification |

---

## 3. VEH W^X — Dual-View Write Interception

VEH handler catches `EXCEPTION_ACCESS_VIOLATION` on write to RX view → redirects write to RW view (same physical page). Decodes write instruction at fault RIP, computes RW destination (`fault_addr - RX_BASE + RW_BASE`), performs write, advances RIP, returns `EXCEPTION_CONTINUE_EXECUTION`.

Supported write forms: `MOV [reg], r8/r32/r64`, `MOV [mem], imm8/imm32`, `MOVDQU/MOVQ/MOVUPS [mem], xmm`, `XOR [mem], reg` (read-modify-write via RW view). Full decode table in constraints.md.

XOR: read from RW (has current data) → XOR → write to RW. Never read RX — may have stale cached value.

---

## 3b. ntdll Unhooking via KnownDlls

**Technique**: `NtOpenSection(\KnownDlls\ntdll.dll)` → `NtMapViewOfSection(readonly)` → compare .text → overwrite hooked stubs with clean bytes.

**Status**: code exists but **disabled in all modes**. KnownDlls generates 5+ kernel-logged signals (NtOpenSection + NtMapView + NtProtect(RWX on ntdll .text) + bulk write + NtProtect(restore)). The reference beacon evades without unhooking.

**Constraint**: if ever re-enabled, V6 ordering applies — sandbox/anti-debug checks MUST run before unhooking to avoid generating signals in sandbox.

---

## 3c. Module Stomp Hardening (Astral Projection cherry-pick)

Inspired by Astral Projection UDRL, cherry-picked without VEH/TrapFlag (detection signals).

### AP1 — PEB LDR_DATA_TABLE_ENTRY Patching

`DONT_RESOLVE_DLL_REFERENCES` leaves IOCs: EntryPoint=NULL, `ImageDll`/`LoadNotificationsSent`/`ProcessAttachCalled` flags unset. PE-sieve and DetectCobaltStomp flag these.

Fix: walk PEB `InLoadOrderModuleList` by DllBase, patch:
- `ep_addr` → standalone `RET` gadget (0xC3) in ntdll .text
- `Flags @ offset 0x68 |= 0x4 | 0x8 | 0x40000`

Zero API calls, pure in-process memory write. Beacon + DLL + CPL modes.

### AP2 — Section Handle via Direct NtCreateSection

Astral Projection uses VEH + TrapFlag to intercept LoadLibrary's internal NtCreateSection — generates thousands of EXCEPTION_SINGLE_STEP events (ETW-TI visible). Instead: open the DLL file directly after stomp.

1. `peb_get_full_dll_name(h_mod)` → PEB FullDllName
2. Prepend `\??\` → NT path on stack buffer (no heap)
3. `NtOpenFile(GENERIC_READ | SYNCHRONIZE)` → file_handle
4. `NtCreateSection(SECTION_ALL_ACCESS, SEC_IMAGE)` → section_handle (via `indirect_syscall7`)
5. `NtClose(file_handle)` — section holds its own reference
6. Pre-allocate backup buffer (BEACON_SIZE bytes, RW private)

One-time init. Beacon EXE only. If any step fails → globals stay 0 → AP3 falls back to legacy.

### AP3 — Sleep Unmap/Remap Cycle

Replaces XOR + PAGE_NOACCESS with full DLL view unmap during sleep:

1. Copy beacon to backup buffer → XOR-encrypt
2. `NtUnmapViewOfSection(-1, h_mod)` — removes DLL view, PEB entry stays intact
3. `NtMapViewOfSection(section, -1, &h_mod, SEC_IMAGE)` — maps fresh clean DLL
4. `NtDelayExecution` (spoofed) — scanner sees original unmodified DLL
5. `NtUnmapViewOfSection(-1, mapped_base)` → `NtMapViewOfSection` — remap backing
6. Decrypt backup → `NtProtect(RW)` → stomp .text → `NtProtect(RX)`

Eliminates: SharedOriginal IOC, modified-.text detection, PAGE_NOACCESS anomaly.

**ASLR**: after remap, check `actual_base == expected`. If shifted, update `BEACON_MEM` and `STOMP_MODULE_BASE` globals. **Fallback**: unmap fails → decrypt backup, zero it, fall through to legacy XOR+NOACCESS.

---

## 4. Sleep Obfuscation

### Pattern (beacon mode — legacy / fallback)

1. XOR-encrypt payload in RW view with per-sleep random key
2. `NtProtectVirtualMemory(RX region, PAGE_NOACCESS)` — EDR memory scanner sees no executable code
3. Sleep via NtDelayExecution (or hooked Sleep if safe)
4. `NtProtectVirtualMemory(RX region, PAGE_EXECUTE_READ)` — restore
5. XOR-decrypt payload via RW view

Used when: AP3 section handle unavailable (DLL/CPL/XLL modes, or `init_stomp_section` failed), or AP3 unmap step failed (graceful fallback).

### EDR-hooked Sleep detection

Before installing sleep hook trampoline, check first 14 bytes of `kernel32!Sleep` for known hook signatures:
- `E9 xx xx xx xx` (JMP rel32 — EDR detour)
- `FF 25 xx xx xx xx` (JMP [rip+disp] — indirect jump)
- `48 B8 xx xx xx xx xx xx FF E0` (MOV RAX, imm64; JMP RAX)

If any detected: **skip trampoline**, use `NtDelayExecution` directly. Trampoline copies Sleep's first bytes including the hook → crash/loop.

### Constraints

- Thread safety: sleep obfuscation must run only on main thread (XOR key + protection changes are not thread-safe)
- `spoofed_syscall` for NtProtect calls (beacon) — `indirect_syscall6` exposes loader .text

### BOF-safe sleep masking policy

Sleep masking is not universally safe in embedded BOF host contexts. Apply this gate:

1. If running in BOF/hosted thread context with unknown scheduler semantics, skip trampoline-based sleep hooks.
2. If `Sleep` prologue is already detoured/hooked, skip custom trampoline and use `NtDelayExecution` path.
3. Keep masking lifecycle wrapper-owned (startup/loader window), not payload-owned long runtime.

This avoids recursive hook loops, host thread corruption, and unstable callback timing in BOF containers.

---

## 5. ETW/AMSI Bypass

### ETW bypass methods

| Method | Mechanism | Status |
|--------|-----------|--------|
| **Byte-patch** (beacon) | `NtWriteVirtualMemory(-1,self)` via indirect syscall writes `33 C0 C3` to `NtTraceEvent` + `EtwEventWrite`; immediate restore | Active only if restore happens before long-running handoff |
| **HWBP DR0** | Breakpoint on EtwEventWrite, VEH sets EAX=0 + skips | Disabled all modes (B4/F7) |
| **Selective DR0** (F6) | RF flag bypass for non-CLR callers | Failed — S1 detects CLR ETW gap regardless |
| **No bypass** (tool_mode) | All ETW flows normally | Active — one-shot tools finish before EDR processes telemetry |

### AMSI bypass methods

| Method | Mechanism | Status |
|--------|-----------|--------|
| **HWBP DR1** | Breakpoint on AmsiScanBuffer | Disabled in tool_mode (F9) |
| **Byte-patch fallback** | Write `B8 57 00 07 80 C3` to AmsiScanBuffer (return E_INVALIDARG) | Fallback when HWBP fails |
| **No bypass** (tool_mode) | AMSI runs normally | Active — S1 AMSI provider doesn't flag one-shot execution |

### Key constraint

S1 detects BOTH total and selective (CLR-only) DR0 suppression. Safe byte-patching is a different pattern: avoid `VirtualProtect` entirely, patch via `NtWriteVirtualMemory` on self, and restore original bytes before `execute_shellcode`/beacon handoff so the integrity check never sees a dirty `ntdll .text`.

---

## 5b. HWBP Propagation to CLR Threads

**Problem**: HWBP DRs set only on TP worker thread. CLR spawns its own threads (JIT, GC, finalizer) with no DR protection.

**Solution**: hook `NtCreateThreadEx` — after creation, `SetThreadContext` to copy DR0-DR3 to each new thread before resume.

- **DR2 cycling** (preferred): intercept via E10 HWBP; VEH re-issues syscall + calls `set_hwbp_on_thread`. Zero byte modification.
- **Inline hook** (superseded/F5): 12-byte `MOV RAX; JMP RAX` on NtCreateThreadEx stub — detectable by S1 integrity checks.

| Constraint | Detail |
|------------|--------|
| Callee-saved registers | All `indirect_syscall` stubs must push/pop r12/r13/r14. Missing → silent CLR state corruption |
| AMSI lazy re-resolve | Must NOT be inside hook body (CS SharpBlock signature, 60%→90%) — resolve on TP worker instead |
| S1 integrity | ntdll .text compared vs KnownDlls at ~100-500ms intervals; any byte mod detected. HWBP is the only safe path |

---

## 5c. Payload Syscall Interception (E10)

> **Applicability**: unbacked memory only. For backed EXE: counterproductive (see §1c).

Payload Nt* calls expose unbacked return addresses in kernel stack walks. HWBP DR2/DR3 intercept them and re-issue via `tp_spoofed_syscall` with .pdata-coherent stack.

- **DR3 (fixed)**: NtReadVirtualMemory (highest frequency)
- **DR2 (cycling)**: round-robins across NtOpenProcess, NtQuerySystemInformation, NtDuplicateObject
- **VEH handler**: check `DR6.B2/B3` → acquire E10_LOCK → extract args → `tp_spoofed_syscall` → set ctx.rax → simulate ret → cycle DR2
- **Contention fallback**: lock held → `indirect_syscall` (no block; spoof is lost)
- **Lock ordering**: `E10_LOCK` → `SPOOF_BUF_LOCK` (never reverse)

**Known limitation**: kernel-mode observer sees payload return address in EXCEPTION_CONTEXT at [RSP] — captured before VEH runs. No usermode fix.

---

## 5d. int3 Breakpoint Patching (E11)

**Status**: **disabled** (V2). S1 ntdll integrity checks detect modified bytes deterministically. E10 HWBP is net better (zero byte modification). Key: `CONTEXT.Rip` = int3 addr itself (x64 differs from Linux ptrace: no +1).

---

## 6. PIC Execution Constraints

| Constraint | Detail |
|------------|--------|
| Fritter `-g 0` self-modifies | Patches import stubs in-place at runtime. RX-only → ACCESS_VIOLATION → stack overflow. RWX required |
| Fritter `-g 1` conflicts with HWBP VEH | Both use VEH; `-g 1` guard pages interfere |
| Donut `-g 1` same conflict | Same VEH collision |
| CLR hosting via COM fails with Costura.Fody | `TypeInitializationException` in `<Module>.cctor` |
| `.NET -r v4.0.30319` required for Fritter | Without explicit runtime version, CLR 2.0 may load |

---

## 6b. Indirect Execution via Callbacks

Avoids `CreateThread(RWX_addr)` — EDR flags thread start addresses in RWX/private memory. Callback-based patterns fire shellcode from within a legitimate DLL:

| API | Fires from | Notes |
|-----|------------|-------|
| `timeSetEvent(period, 0, shellcode, 0, TIME_CALLBACK_FUNCTION)` | `winmm.dll` | Async; 100ms delay typical |
| `CreateThreadpoolWait(callback, shellcode, NULL)` + `SetThreadpoolWait` | `ntdll.dll` TP | Fires when wait object signaled |
| `QueueUserAPC(shellcode, thread, 0)` + alertable wait | target thread | Thread must enter alertable state |
| `EnumWindows(shellcode, 0)` | `user32.dll` | Synchronous, blocks caller |

**Constraint**: callback thread is TP worker context — use `indirect_syscall` only, not `spoofed_syscall` or `masked_syscall`. See `references/constraints.md` → Indirect / Callback-based Execution.

---

## 7. Post-Execution Cleanup

### Tool mode (private RWX, current)

```
1. Clear all DRs on TP worker — SetThreadContext(DR7=0)
2. Remove VEH handler — RtlRemoveVectoredExceptionHandler
3. Zero entire RWX buffer — write_bytes(base, 0, size)
4. NtFreeVirtualMemory(base)
```

### Stage scrub lifecycle (pre-handoff + post-decrypt)

Treat staging buffers as disposable evidence:

1. After payload materialization, wipe source encoded blob/buffer immediately.
2. After handoff is confirmed, wipe temporary decode/decompress workspace.
3. Keep only the minimal live execution region; scrub and free all setup artifacts.

This reduces post-exec memory forensics recovery of original encrypted/plaintext stages.

### Beacon mode (dual-view section)

```
1. Clear all DRs
2. Remove VEH handler
3. Clear W^X globals (zero VEH_WX_*)
4. Zero entire RW view — no NtProtect needed
5. NtUnmapViewOfSection(rw_view)
6. NtUnmapViewOfSection(rx_view)
7. Close section handle
```

**Order rationale**: DRs before VEH removal (HWBP fire without handler → unhandled exception). Stomp before free/unmap (zero memory while accessible). If payload calls `ExitProcess` (common with .NET), cleanup never executes — kernel releases everything on termination.

---

## 8. API Resolution Without IAT

### PEB walk

`GS:[0x60]` → PEB → `Ldr` → `InLoadOrderModuleList`. Hash each module's `BaseDllName` (UTF-16, case-insensitive DJB2). Match → `DllBase`. Then parse PE Export Directory → hash each export name (ASCII DJB2) → match → address. Reject forwarded exports (address inside export dir range).

### Robustness constraints (field-tested)

- **No SizeOfImage bounds check**: on some builds, kernel32's EAT arrays reside at RVAs beyond SizeOfImage. Memory IS mapped — don't reject.
- **`read_unaligned` mandatory**: PE structures make no alignment guarantees. Raw `*(ptr as *const u32)` panics on misaligned addresses.
- **Fallback chain**: kernel32 → kernelbase for LoadLibraryA, GetThreadContext, SetThreadContext, etc.

---

## 9. String Obfuscation

Compile-time XOR macro (`obfcstr!()`) over byte arrays — decode on stack at runtime. Never leave API names, DLL paths, or registry keys as string literals. Runtime string building for paths: construct `ntdll.dll` char-by-char or from segments.

---

## 10. Payload Encryption Strategy

### Current: zlib + splitmix64 PRNG + Custom Base64

**Pipeline**: `raw → signature obfuscation → zlib deflate(9) → splitmix64 XOR keystream → custom Base64 → ENC_SC`

- **zlib (miniz_oxide)**: whitelisted by most AV. Compresses ~40-50%.
- **splitmix64 PRNG**: non-repeating keystream from 64-bit seed. Zero algorithmic fingerprint. Seed stored split+masked across `SC_SEED_FRAG[8]` / `SC_SEED_MASK[8]`.
- **Custom Base64**: alphabet `A-Za-z0-9_.`. Entropy 8.0 → ~6.0 bits/byte. Resembles PE symbol/identifier tables. No YARA signatures.
- **Section**: `#[link_section = ".data1"]` — isolates payload from .rdata. NEVER `.rsrc` (malforms DataDirectory[2]).

### Why NOT AES

AES is fingerprinted **algorithmically** even without static S-box: GF(2^8) `0x1b` polynomial, ShiftRows byte permutation, MixColumns structure, 14-round key expansion. Replacing zlib+XOR with AES raised VT 4→8/71.

### E12 per-page lazy decryption

Decrypt streaming into RW view → XOR re-encrypt per page → NtProtect(PAGE_NOACCESS) on RX → VEH decrypts on access. Eliminates cleartext heap buffer. **Constraint**: sliding window eviction incompatible with Fritter W^X writes — disable eviction. Tool_mode: bypassed entirely (S3, direct copy — no VEH faults).

### CrowdStrike regressions (confirmed patterns — do not reintroduce)

1. **PE header stomp**: `map → execute → zero first 0x1000` = CS shellcode loader signature (60%→90%)
2. **AMSI propagation in NtCreateThreadEx hook**: PEB walk + resolve AmsiScanBuffer + SetThreadContext inside hook body = CS SharpBlock signature (60%→90%)
3. **Removing `panic_abort`**: reintroduces Rust unwinding strings (`attempt to divide by zero`, `library/core/src/...`). Always use `build-std = ["std", "panic_abort"]` + `panic = "immediate-abort"`.

---

## 11. PE Section Structure

### Section ratio rule

ML classifiers use section size ratios. `.text` must be larger than any single data section (code-dominant). Data-dominant = packer signature.

| opt-level | .text | .data1 (payload) | ratio | Risk |
|-----------|-------|---------|-------|------|
| 0 | 2,222K | 1,151K | 1.93:1 | OK |
| 1 | 876K | 1,151K | 0.76:1 | HIGH |
| 2+ | ~400K | 1,151K | 0.35:1 | CRITICAL |

**Rule**: never change opt-level without verifying resulting section ratios.

### Section name constraints

| Section | DataDirectory auto-link | Safe for raw data? |
|---------|------------------------|-------------------|
| `.rsrc` | DD[2] Resource — expects IMAGE_RESOURCE_DIRECTORY | **NO** — malformation |
| `.data1` | None | **YES** — standard linker overflow name |
| `.edata` / `.idata` / `.reloc` / `.debug` | Various | No — auto-linked |

---

## 13. Process Injection Patterns

Full detail: [`references/process-injection.md`](references/process-injection.md).

**Avoid classic CRT** (`OpenProcess → VirtualAllocEx → WriteProcessMemory → CreateRemoteThread`) — fully hooked.

**Early Bird APC**: `CreateProcess(CREATE_SUSPENDED)` → alloc RW → write → protect RX → `QueueUserAPC` → `ResumeThread`. Fires before EDR DLL loads. Variant — **Early Cryo Bird**: freeze via `NtSetInformationJobObject(JOBOBJECT_FREEZE_INFORMATION)` to avoid `CREATE_SUSPENDED` indicator.

**Thread hijacking**: `SuspendThread` → `GetThreadContext` → set `ctx.Rip` → `SetThreadContext` → `ResumeThread`. Use indirect syscalls (`NtGetContextThread`/`NtSetContextThread`). **Waiting Thread Hijacking** variant: target thread already in `NtDelayExecution` — no `SuspendThread` needed.

**PPID spoofing**: `STARTUPINFOEX` + `UpdateProcThreadAttribute(PROC_THREAD_ATTRIBUTE_PARENT_PROCESS)` → child appears spawned from trusted parent. EDR kernel callback detects PID mismatch — mitigate with token impersonation of spoofed parent.

---

## 14. Anti-Analysis Hardening

Full detail: [`references/anti-analysis.md`](references/anti-analysis.md).

**Ordering rule**: run ALL anti-analysis checks before any evasion setup. Generating ETW events (NtOpenSection, NtProtect) in a sandbox increases detection even without EDR.

**Design principle — near-zero IOC**: passive checks are not a stylistic preference; they are a deliberate zero-IOC constraint. Every read-only check adds zero telemetry. Every invasive call (NtQueryInformationProcess, DR mutation, ThreadHideFromDebugger, CPUID ring-trip) generates at least one observable event. The target is a check layer that produces no indicators that distinguish the implant from a normal process.

**Passive anti-debug baseline**: `PEB.BeingDebugged` (PEB read, no syscall), parent-process sanity (PPID from PEB), sleep/timing drift (RDTSC), debugger process/window heuristics. No `NtQueryInformationProcess`, no `NtSetInformationThread`, no DR read/write in default mode.

**Passive anti-sandbox baseline**: sleep acceleration (RDTSC — most reliable, zero syscall), low-core/low-RAM heuristic, hostname/username patterns, common analysis process names. CPUID, registry probes, and MAC OUI checks are optional secondary tier — avoid by default.

**Decision rule**: score multiple weak passive signals; never hard-fail on a single artefact; prefer silent degraded execution over self-termination.

**IAT hygiene**: PEB walk (§8) removes suspicious IAT entries; fake dead-code imports add benign noise; delay-load via `LoadLibrary`/`GetProcAddress`. Combined with §9 string obfuscation → zero readable API strings.

**Entropy target**: < 7.2 bits/byte per section. Custom Base64 (§10) already achieves 8.0→6.0. Embedding dictionary data and stripping debug info lower further. RC4 lacks AES's GF polynomial fingerprint but splitmix64 XOR remains preferred (zero algorithmic footprint).

---

## 12. BYOVD — Kernel-Level EDR Kill (Reference Only)

BYOVD loads a signed-but-vulnerable kernel driver → Ring 0 → remove EDR callbacks or terminate EDR processes. As of March 2026: 54 active tools targeting 35+ drivers (RTCore64.sys, rwdrv.sys, NSecKrnl.sys); used by RansomHub, BlackByte, Scattered Spider, Qilin/Warlock.

**Orthogonality**: §1–§11 operate entirely in usermode. BYOVD removes the EDR; §1–§11 evade it. Combining both in one implant is operationally noisy and unnecessary.

**Detection surface**: `NtLoadDriver` + driver from TEMP/user-writable path + immediate security-process termination.

**Blue team mitigations**: HVCI, WDAC driver allowlist, Sysmon EID 6, Microsoft vulnerable driver blocklist.

> Do not bundle BYOVD with a usermode-evasion implant — the kernel signal is louder than any benefit from usermode stealth.

---

## S1 Field-Tested Failures

Seven disproven assumptions and a full indicator audit table: see [`references/field-notes.md`](references/field-notes.md).

**Key lesson**: evasion maximalism is self-defeating. A 1,472-line beacon (zero VEH/HWBP/unhooking) evades S1/CS/Defender fully. A 6,126-line version (all features) is detected. Every added feature introduced 1–3 real indicators.

**Confirmed reductions**: B1 (private RWX), F7 (disable ETW DR0), F9 ph3-5 (eliminate syscall/VEH/HWBP stubs).

**Non-reductions**: F6 (selective ETW), F2 (4→11 HWBP targets), F9 ph1-2 (call site gating only).

Remaining irreducible: "Malicious shellcode execution" (private RWX + PEB walk + dynamic API).

---

## Resources

| File | When to load |
|------|-------------|
| [`references/constraints.md`](references/constraints.md) | Hard constraints with failure modes and crash causes. Load when debugging a crash or unexpected detection. |
| [`references/field-notes.md`](references/field-notes.md) | S1/CS/Defender field-tested failures and indicator audit. Load when deciding to add or remove an evasion feature. |
| [`references/etw-patching.md`](references/etw-patching.md) | Detailed ETW byte-patch pattern: why `NtWriteVirtualMemory` on self differs from `VirtualProtect`, required restore window, and patch payload details. |
| [`references/process-injection.md`](references/process-injection.md) | Full Early Bird APC / Thread Hijacking / PPID Spoofing details and decision matrix. |
| [`references/anti-analysis.md`](references/anti-analysis.md) | Full anti-debug, anti-VM, IAT hygiene, and entropy management tables. |
