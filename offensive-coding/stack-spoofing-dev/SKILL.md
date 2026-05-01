---
name: stack-spoofing-dev
description: "Design, implement, and harden x86-64 Windows call-stack spoofing primitives (Draugr, SilentMoonwalk DESYNC with/without Eclipse, NtContinue-based synthetic contexts, thread-pool stack spoof) and reference implementations (YouMayPasser, VulcanRaven, Unwinder, HulkOps). Use when writing or reviewing implants/loaders/BOFs that must hide syscall origins from EDR stack walkers, porting spoofers between C/Rust/Go, choosing between strategies on a specific Windows build (10, 11 22H2/24H2, Server 2022+), tuning frame thresholds against .pdata-parsed gadget inventories, debugging JMP [RBX] / ADD RSP,X gadget failures, or integrating stack spoofing with indirect syscall dispatch or sleep obfuscation. Covers frame math, UNWIND_INFO parsing gotchas, SAVE_NONVOL safety, Eclipse validation, per-strategy ASM trampoline layouts, and strategy selection on modern Windows where classical thresholds no longer hold."
license: MIT
compatibility: "x86-64 Windows 10 1809 through Windows 11 24H2 / Server 2022+. Classical thresholds assume Win10; Win11 22H2+ requires empirical re-tuning (see frame-math reference). ARM64 not covered — unwinder model differs."
metadata:
  author: AeonDave
  version: "1.0"
  category: evasion
  language: c,cpp,rust,go,asm
---

# Stack Spoofing — Windows x64

Produce a spoofed call stack that survives unwinder-based inspection (ETW-TI, EDR stack walkers, `StackWalk64`). Each frame must have a legitimate `.pdata` entry, an unwind description that matches the planted frame size, and a return address that points inside a known module's `.text`.

This skill assumes you already understand `.pdata` / `UNWIND_INFO` at the level described in `windows-internals/references/exception-unwind.md`. It focuses on **implementing** the spoofer, not on teaching the format.

## When to activate

- Implementing or reviewing Draugr / SilentMoonwalk / NtContinue / YouMayPasser / VulcanRaven / Unwinder spoofers in C, C++, Rust, Go, or Plan9 ASM
- Choosing between spoof strategies for a specific Windows build or thread context (main, TP worker, alertable, console-attached)
- Debugging `spoof_init: FAIL jmp_rbx` or unwinder-reported frame-size mismatches
- Adjusting `MinJmpRbxFrameSize` / `MinAddRspX` thresholds after `.pdata` inventory changes across Windows builds
- Integrating a spoofer with an indirect syscall dispatcher (RecycleGate / Hell's / FreshyCalls)
- Hardening a pre-existing spoofer against modern EDR correlation (Eclipse, SAVE_NONVOL safety, backed-vs-unbacked caller)
- Porting a spoofer between languages without breaking the ASM/context-struct contract

If the question is "what does UNWIND_INFO look like" → wrong skill, read `windows-internals/references/exception-unwind.md`. If the question is "how do I make `NtWriteVirtualMemory` appear to come from `RtlUserThreadStart`" → right skill.

---

## The three strategies, side by side

| Property | **Draugr** | **SilentMoonwalk DESYNC** | **NtContinue (context-replay)** |
|---|---|---|---|
| Frames planted | 3 | 4 | 0 (kernel replays `CONTEXT`) |
| Gadgets required | 1× `JMP [RBX]` | 1× `JMP [RBX]` + 1× `ADD RSP,X;RET` | none (only a `syscall;ret`) |
| UNWIND_INFO frames needed | 2 (`BaseThreadInitThunk`, `RtlUserThreadStart`) | 2 (`UWOP_SET_FPREG` + `UWOP_PUSH_NONVOL rbp`) | 2 synthetic retaddrs planted in target `CONTEXT.Rsp` |
| Eclipse-validated? | No | Optional (cascade: wininet → user32 → kernelbase) | N/A |
| Callstack walker sees | `syscall;ret → JMP [RBX] → BaseThreadInitThunk → RtlUserThreadStart → 0` | `syscall;ret → AddRspX → JmpRbx → SecondFrame(rbp) → FirstFrame(setfpreg) → 0` | `syscall;ret → BaseThreadInitThunk → RtlUserThreadStart → 0` |
| Safe on TP worker threads | No (root RSP wrong) | Yes | Yes |
| Safe with console attached | Yes | Yes | No (NtContinue races console I/O) |
| Go runtime friendly | Yes (uses pre-allocated heap buffer as fake RSP) | Yes | Risky (CONTEXT replay confuses goroutine scheduler) |
| Complexity (LOC) | ~300 + ASM | ~600 + ASM | ~150 + ASM |

**Default choice**: Draugr if you control the thread (main thread of an EXE, or explicit `CreateThread` with known root). SilentMoonwalk if you run on thread pool workers or need `.pdata`-coherent frames all the way down.

---

## Notable implementations and variants

The strategies above are conceptual; below are the public PoCs/implementations you will encounter in the wild. Each is a concrete realization (or precursor) of one of the three strategies, with its own quirks.

### YouMayPasser (Waldo-irc) — return-address-only minimalist baseline

64-bit weaponization of Gargoyle that extends Namaszo's original Return Address Spoofing PoC. Targets Cobalt Strike beacons. Spoofs only the **immediate** return address of the calling function — not a full multi-frame chain — so it is the cheapest stack-masquerading primitive.

- **Strategy mapping**: precursor / strict subset of Draugr (1 frame, 1 gadget).
- **When to pick**: BOF or short-lived primitive where one syscall's caller-frame must be hidden and a full Draugr chain is overkill.
- **Caveat**: hardcoded gadget offsets per Windows build — you must re-tune per build, exactly as Win11 22H2+ measurements above warn for any `JMP [RBX]` consumer. Walks the same gadget cliffs as Draugr.

### VulcanRaven — template-based stack mimicry with VEH cleanup

Spoofs the call stack by **mirroring** a real captured stack from telemetry (SysMon ProcessAccess on lsass), shipping with three example profiles selected via `--wmi`, `--rpc`, `--svchost`. Each profile is a captured frame chain of a legitimate Windows service path; the spoofer reproduces it byte-for-byte before issuing `NtOpenProcess`.

- **Strategy mapping**: orthogonal to Draugr/SilentMoonwalk — instead of computing a generic plausible chain, it copies a specific real one. Fewer correlation surface marks because the chain came from real telemetry.
- **VEH twist**: registers a vectored exception handler before resuming the spoofed thread; on access violation it redirects to `RtlExitUserThread` so the thread terminates cleanly rather than crashing the host. Adopt this pattern any time you mutate `CONTEXT.Rsp` and cannot guarantee the planted chain unwinds correctly.
- **When to pick**: targeted credential-access flows where you want the call chain to *match* a known-good svchost/RPC/WMI invocation rather than merely *look generic*.
- **Limit**: the captured chain ages — re-collect SysMon templates after major Windows feature updates or you start mimicking a chain that no longer exists in production.

### Unwinder (Kudaes) — Rust weaponization of SilentMoonwalk

Rust crate (`unwinder` on crates.io) implementing full SilentMoonwalk DESYNC with stable, idiomatic Rust ergonomics. Supports calling arbitrary functions or indirect syscalls with **up to 11 parameters**, retrieves return values, and the spoof can be **chained any number of times without growing the call stack** (frames are recycled per call).

- **Strategy mapping**: SilentMoonwalk DESYNC (4 frames, JMP[RBX] + ADD RSP,X), Rust-native.
- **When to pick**: Rust implants where you want SilentMoonwalk without rolling your own `global_asm!` trampoline. Treat it as the canonical Rust answer to the lang-c-rust-go reference's SilentMoonwalk slot.
- **Caveat**: still subject to all the Win11 22H2+ gadget-population limits. Cascade module ordering is internal to the crate — read its source before assuming `wininet → user32 → kernelbase` is wired the way you want.

### HulkOps — tutorial reference, not a tool

GitBook write-up walking through both **return address spoofing** and **x64 call stack spoofing** at code level: synthetic stack frames with proper unwinding, locating `RUNTIME_FUNCTION` in `.pdata`, parsing `UNWIND_CODE` to compute frame sizes, and the assembly `Spoof` function that pushes a sentinel `0` to terminate unwinding.

- **Use as**: pedagogical reference for engineers new to the technique. Especially good for understanding **why** the math in `references/frame-math.md` looks the way it does. Not a drop-in implementation.

---

## Decision tree

```
Implant runs on...
│
├── Main thread of a dedicated loader EXE?
│   └── Draugr (simplest, fewest gadgets, zero Eclipse concerns)
│
├── Thread pool worker (TpWorkCallback, timer, TP_IO)?
│   └── SilentMoonwalk DESYNC — only strategy with .pdata-coherent frames
│                               beyond BaseThreadInitThunk/RtlUserThreadStart
│
├── Beacon in a module-stomped host (rundll32, legitimate PE)?
│   └── SilentMoonwalk DESYNC or NtContinue — Draugr's assumption
│       "this thread was started by RtlUserThreadStart" does not hold
│
├── Single one-shot syscall with console attached?
│   └── Indirect syscall only (skip spoofing) — NtContinue races console
│
└── Need template-based mimicry of a real process's stack (e.g. svchost/RPC/WMI)?
    └── VulcanRaven — synthetic stack mirroring a captured SysMon profile, VEH-based cleanup
```

---

## Frame math — the numbers you actually need

These are the non-negotiable sizing rules. Full derivation in `references/frame-math.md`.

### Minimum frame sizes for `JMP [RBX]` gadget

The trampoline frame must hold the shadow area (0x20) plus all stack args of the syscall you are spoofing. For NT syscalls:

| Syscall arg count | Stack args (after RCX/RDX/R8/R9) | Shadow + stack args | Minimum frame |
|---|---|---|---|
| ≤ 4 | 0 | 0x20 | 0x28 |
| 5 | 1 | 0x28 | 0x30 |
| 11 (NtCreateThreadEx) | 7 | 0x58 | 0x60 |
| 18 (max practical) | 14 | 0x90 | 0x98 |

Classical Draugr literature uses `0xD8` as a "safe for everything" floor. **This is wrong on Windows 11 22H2+**: kernelbase.dll has had its `FF 23` gadget population drastically reduced and often exposes no gadget with frame ≥ `0xD8`. Use the real minimum for your specific syscall.

**Rule**: compute `shadow (0x20) + args_on_stack * 8 + padding (0x08)` and use that as your `min_frame`. For the common `NtCreateThreadEx(11)` path, `0x60` is correct.

### Windows 11 22H2+ field measurements (kernelbase.dll)

| Metric | Value |
|---|---|
| Total `FF 23` in kernelbase `.text` | ~14 |
| Max `.pdata`-validated frame size | `0x70` |
| CALL-preceded candidates (Eclipse) | 0 |
| Candidates rejected by SAVE_NONVOL filter | ~8 (of 14) |
| Candidates passing `frame ≥ 0x60` | ~1 |

**Implication**: hardcoded `0xD8` breaks. Eclipse from kernelbase alone is infeasible. Cascade `wininet → user32 → kernelbase` is the correct strategy; or accept the lower threshold and drop Eclipse.

### Minimum `ADD RSP,X;RET` (SilentMoonwalk only)

`X` must be **larger than** the `JMP [RBX]` trampoline's frame size, so arg slots placed at `[SP+0x28..SP+0x90]` within the `AddRspX` frame never collide with the `JmpRbxGadget` word written at `[SP + 8 + X]`.

Rule: `min_x = max(jmp_rbx_frame_size, MIN_FLOOR)` where `MIN_FLOOR = 0x60` on Win11 22H2+ (was `0xB0` on Win10).

### UNWIND_INFO safety filters

Reject any candidate where `calc_frame_size` returns **0**. Causes:
- No `.pdata` entry (leaf function)
- `UWOP_SAVE_NONVOL` / `UWOP_SAVE_NONVOL_FAR` with `save_offset >= total_alloc` → writes past frame → stack corruption when used as spoof frame
- `UWOP_SAVE_XMM128` present — spoof does not preserve XMM regs; executing the real unwinder on this function causes a #UD when unwinding saved XMM

See `references/frame-math.md` for the full `calc_frame_size` algorithm including chained unwind info (`UNW_FLAG_CHAININFO`) handling.

---

## Gadget scanner — non-negotiable rules

1. Scan `.text` of the target module only. Never scan `.rdata`; byte sequence `FF 23` occurs in data.
2. Match `byte[i] == 0xFF && byte[i+1] == 0x23` for `JMP [RBX]`. This is a 2-byte opcode with no REX prefix.
3. For each hit, compute `frame_size` via `.pdata` binary search. Reject if 0.
4. If Eclipse required: check `byte[gadget - 5] == 0xE8` (CALL rel32). Do **not** check `0x41 FF D_` or other CALL variants — callsite validation in Eclipse papers specifically relies on the 5-byte `E8` displacement CALL.
5. Deterministic selection: pick the **largest** `frame_size` that passes filters. Random selection makes failure modes unreproducible.
6. Emit diagnostic counters on failure (`FF23_total`, `fs_zero`, `below_min`, `eclipse_fail`, `best_belowmin_fs/addr`). Without these, kernelbase-has-no-gadgets failures look identical to bad-threshold failures.

Full scanner pseudocode + instrumentation patterns in `references/frame-math.md`.

---

## Trampoline contract (all languages)

Every spoofer expresses the same contract between a high-level caller and a small ASM trampoline:

```
Caller (C / Rust / Go):
  1. Resolve: module bases, function retaddrs, gadget(s), frame sizes
  2. Populate a fixed-layout SpoofContext struct
  3. Pre-allocate a spoofing buffer (heap-safe; see below)
  4. Call ASM trampoline: (ssn, syscall_ret_addr, &ctx, args...)

ASM trampoline:
  1. Save callee-saved (RBX, RBP, R12–R15, XMM6–15 if used)
  2. Anchor the real RSP in a non-volatile reg (R12 is canonical)
  3. Switch SP to the pre-allocated buffer (top-aligned to 16)
  4. Plant synthetic frames bottom-up (sentinel 0 → outermost → innermost)
  5. Load SSN into EAX, set MOV R10, RCX (syscall ABI)
  6. JMP/CALL into syscall;ret gadget (never embed bare `syscall` — leaves your .text as source)
  7. After return: restore SP from R12, pop callee-saved, RET
```

**Buffer rule**: never allocate the fake stack in a local variable of the ASM trampoline's frame. You are about to rewrite RSP; any local temporaries die. Pre-allocate a heap buffer (or a stable static) in the high-level caller, pass in `bufPin + fakeStackTop`, and use R12 to anchor the *real* RSP for fixup.

### Why the buffer matters in Go

Go's runtime grows goroutine stacks dynamically. A large `SUB SP, imm` inside the trampoline can overflow `stack.lo`, or worse, produce a valid stack that the GC scanner then tries to walk — finding planted return addresses, treating them as Go frames, and crashing with "runtime: unreachable". The pre-allocated heap buffer sidesteps both issues:

```go
// Pre-allocate once at Init; pin through GC via unsafe.Pointer arg
total := 8 + f2 + f1 + trampoline + 256
total = (total + 15) &^ 15
buf := make([]byte, total)
bufPin := unsafe.Pointer(&buf[0])
fakeStackTop := (uintptr(bufPin) + uintptr(len(buf))) &^ 15
```

Pass `bufPin` as an explicit arg so the GC keeps it alive for the syscall duration.

### Why the buffer matters in Rust / C

- **Rust**: `#[naked]` / `global_asm!` with local `sub rsp, imm` blows through canaries and `-Z stack-check` instrumentation. Use a `Box<[u8; N]>` allocated in the caller and passed via `rdi`/`rsi`.
- **C (mingw-w64)**: `__attribute__((naked))` + inline AT&T asm; use a file-scope `static __thread uint8_t buf[N]` (TLS-backed) or a heap buffer allocated once in `spoof_init`. `alloca` is unsafe here — it uses `_chkstk` which generates CFG indirect calls.

---

## The five implementation rules

These apply across C, C++, Rust, Go, and raw ASM.

**R1. Resolve frame sizes at runtime**. Hardcoding `BaseThreadInitThunk+0x14` and `RtlUserThreadStart+0x21` is fine (those offsets are stable since Win10 1809); hardcoding `Frame1Size = 0x30` is not (it changed between 20H1 and 22H2). Always parse `.pdata`.

**R2. Cascade gadget search across modules**. Never commit to a single module. Order: `wininet → user32 → kernelbase → ntdll` (for SM); `kernelbase → ntdll` (for Draugr). Emit a log line on each fallback so you know which module won at runtime.

**R3. Instrument the scanner in debug builds**. Zero-match failures are ambiguous without counters. See the debug pattern in `references/frame-math.md` §Scanner Instrumentation.

**R4. Invalidate the spoof context on init failure**. Do not leave partial state; downstream callers must be able to check a single `SPOOF_READY` flag and fall back to unspoofed dispatch. Never "partially succeed".

**R5. Strip the spoofer from release builds when you do not need it**. A 500-line SilentMoonwalk with 4 frames and cascade logic is a strong detection target by itself — string constants, control-flow patterns, and `.pdata` scans are all observable. If the binary can run backed-on-disk in a legitimate PE, skip the spoof. See the minimalism principle in `edr-evasion`.

---

## Languages — what changes

### C / C++ (mingw-w64 or MSVC)

- `__attribute__((naked))` function with AT&T inline asm (GNU) or `.code` block (MASM with MSVC)
- Context struct: `#pragma pack(push, 8)` → fixed field order; offsets referenced in asm as `0(%rdi)`, `8(%rdi)`, …
- Prefer mingw-w64 over MSVC for spoofers: no `_chkstk` injection on large stack frames, predictable codegen
- Link with `-nostdlib -fno-ident -fno-asynchronous-unwind-tables` so your own `.pdata` does not confuse investigators reversing your loader

See [references/lang-c-rust-go.md](references/lang-c-rust-go.md#c) for a ready-to-compile Draugr trampoline in mingw-w64 AT&T syntax.

### Rust

- `#[naked]` (stable as of Rust 1.88) or `global_asm!` for the trampoline
- `#[repr(C)]` on the context struct — never `#[repr(Rust)]`
- `no_std + no_main` for implant builds; link with `-C link-args=/NODEFAULTLIB`
- **Caveat**: LLVM aggressively allocates RBX across inline asm blocks. Always list `rbx` in clobbers, or use `options(noreturn)` + a tail call to the next phase.

See [references/lang-c-rust-go.md](references/lang-c-rust-go.md#rust).

### Go

- Plan 9 ASM syntax (`.s` files), one per architecture. See `draugr_spoof_x64.s` template in the reference file.
- Frame size `$0-N` — always `$0` (no local frame). `N` = size of args passed from Go (sum of typed-arg sizes rounded to 8).
- **`BYTE $0x90` NOP scattered between instructions**: not decorative. Plan 9 ASM's go assembler reorders "optimizable" sequences; the NOPs are padding to keep the assembler from merging or eliminating instructions that look redundant to it but are necessary for the spoof.
- Never touch `g` (`GS:0x30` on Windows) in the trampoline. The Go runtime's thread-local lookup needs it intact for goroutine scheduling on return.

See [references/lang-c-rust-go.md](references/lang-c-rust-go.md#go).

---

## Integration with indirect syscall dispatchers

A stack spoofer does not resolve SSNs or find `syscall;ret` gadgets — that is the `indirect-syscall` skill's job. The integration point is a small interface:

```
spoof_trampoline(ssn: u16, syscall_ret_addr: *const u8, ctx: *const SpoofContext, args...) -> NTSTATUS
```

Where the caller resolves `(ssn, syscall_ret_addr)` via RecycleGate / Hell's / FreshyCalls, and the spoof trampoline dispatches the actual `syscall;ret` through the spoofed stack. Loading one skill does not require the other, but production loaders combine both. The layering is:

```
high-level wrapper
  └─ indirect_syscall.execute(ssn, gadget_addr, args…)
       └─ if (spoof_ctx != 0 && spoof_dispatch != NULL):
              spoof_dispatch(ssn, gadget_addr, spoof_ctx, args…)   ← spoof trampoline
          else:
              direct_indirect_syscall(ssn, gadget_addr, args…)     ← plain trampoline
```

See `indirect-syscall/SKILL.md` for the SSN side of this interface.

---

## Diagnostic workflow (when init fails)

The failure diagnosis sequence, from most common to least:

1. **`FF23_total == 0`** → target module has been stripped of gadgets (Win11 24H2 kernel32.dll). Add another module to the cascade.
2. **`fs_zero` dominates** → SAVE_NONVOL filter is rejecting the scanner's inventory. Verify `UWOP_SAVE_NONVOL` handling: `max_save_offset >= total_alloc` is the rejection criterion; off-by-one here eats half the population.
3. **`below_min` dominates, `best_belowmin_fs == 0x70`** → threshold too high. Compute actual required frame for your syscall's arg count; lower `MIN_JMP_RBX` accordingly.
4. **`eclipse_fail == FF23_total`** → no `E8` byte at `gadget - 5`. On Win11 22H2+ this is expected for kernelbase. Cascade through `wininet` / `user32` first, then drop Eclipse for kernelbase last-resort.
5. **Init succeeds but runtime crash** → buffer too small. Recompute: `8 + frame2 + frame1 + trampoline_frame + args*8 + 0x100 padding`, align to 16.
6. **Unwinder sees "broken" stack** → frame sizes mismatch between your plant and the real UNWIND_INFO. Re-read `.pdata` for the retaddr, not the function entry.

Full diagnostic script + instrumentation pattern in `references/frame-math.md` §Diagnosing Init Failures.

---

## Resources

- [references/frame-math.md](references/frame-math.md) — `calc_frame_size` algorithm, SAVE_NONVOL safety filter, gadget scanner with instrumentation, Win11 22H2+ empirical inventory, diagnosing init failures
- [references/lang-c-rust-go.md](references/lang-c-rust-go.md) — Per-language trampoline patterns (mingw-w64 AT&T asm, Rust `global_asm!`, Go Plan 9), context-struct layout rules, buffer-management patterns, interop caveats

### External references

- Eden / Draugr — original C++ implementation, `NtDallas` author
- SilentMoonwalk — Klezvirus et al., public repo (github.com/klezVirus/SilentMoonwalk)
- YouMayPasser — Waldo-irc, 64-bit Gargoyle / Return-Address-Spoofing extension (precursor of Draugr; built on Namaszo's PoC)
- VulcanRaven — synthetic stack mimicry with SysMon-captured wmi/rpc/svchost profiles + VEH cleanup; targets `NtOpenProcess` on lsass
- Unwinder — Kudaes, Rust port/weaponization of SilentMoonwalk (github.com/Kudaes/Unwinder; `unwinder` on crates.io)
- HulkOps — GitBook tutorial: x64 Return Address Spoofing and x64 Call Stack Spoofing (hulkops.gitbook.io/blog/red-team)
- Eclipse bypass — Arash Parsa (waldo-irc), Call Stack Masquerading research
- WithSecure Labs — "Spoofing Call Stacks To Confuse EDRs" (CallStackSpoofer PoC)
- Microsoft x64 unwind docs — `learn.microsoft.com/en-us/cpp/build/exception-handling-x64`
- Geoff Chappell — CALL-site reverse on `RtlUserThreadStart` / `BaseThreadInitThunk`
