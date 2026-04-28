---
name: indirect-syscall
description: "Design, implement, and harden Windows x64 indirect syscall dispatchers: SSN resolution (Hell's Gate, Halo's Gate, Tartarus' Gate, FreshyCalls, Recycled Gate, RecycledGate/DWhisper), direct vs indirect dispatch, `syscall;ret` gadget discovery, layered syscall interception, and composition with stack spoofing. Use when writing or reviewing implants/loaders/BOFs that dispatch NT APIs without touching hooked ntdll stubs, porting dispatchers between C/Rust/Go, diagnosing SSN-drift failures across Windows builds, selecting between resolution strategies under specific EDR hook patterns, integrating with call-stack spoof trampolines, or building multi-arg (6+) syscall wrappers. Covers ntdll stub byte layout, PEB-walk-based module/export resolution, name obfuscation, gadget scanning, the RCX→R10 convention, WoW64 considerations, and strategy trade-offs against modern inline / IAT / nirvana hooks."
license: MIT
compatibility: "x86-64 Windows 10 1809 through Windows 11 24H2 / Server 2022+. ARM64 uses `svc #0` with SSN in `x8` — structurally similar but register conventions differ; treat this skill as x64-only."
metadata:
  author: AeonDave
  version: "1.0"
  category: evasion
  language: c,cpp,rust,go,asm
---

# Indirect Syscall Dispatch — Windows x64

Invoke an NT API by executing the `syscall` instruction from inside an unmodified module (ntdll), without calling the hooked Nt* / Zw* stub prologue. The result: a call stack that ends in `ntdll!<some Nt function>+0x12` instead of `yourloader!your_trampoline`, and no inline-hook byte-pattern detection on your dispatch path.

This skill is the dispatch companion to `stack-spoofing`. It assumes you understand ntdll stub layout and the syscall ABI at the level of `windows-internals/references/syscalls.md`. It focuses on **implementing** the dispatcher correctly.

## When to activate

- Implementing or reviewing indirect syscall dispatchers in C / C++ / Rust / Go
- Selecting between Hell's / Halo's / Tartarus' / FreshyCalls / RecycledGate on a specific EDR hook pattern
- Debugging SSN drift after a Patch Tuesday (`STATUS_INVALID_PARAMETER` from an NT API that used to work)
- Diagnosing `syscall;ret` gadget discovery failures on stripped ntdll builds
- Composing an indirect dispatcher with a stack spoof trampoline (Draugr / SilentMoonwalk)
- Writing a multi-arg wrapper (`NtCreateThreadEx` has 11, `NtQuerySystemInformationEx` has 6)
- Porting a dispatcher between languages — preserving the SSN-table and gadget-cache contracts

If the question is "what does `mov r10, rcx` mean" → wrong skill, read `windows-internals/references/syscalls.md`. If the question is "how do I build a dispatcher that still works when ntdll is inline-hooked at offset 0" → right skill.

---

## The five SSN resolution strategies

| Strategy | Works when stub byte 0 is hooked | Works against IAT hook only | SSN accuracy | Runtime cost |
|---|---|---|---|---|
| **Hell's Gate** | No | Yes | Exact | Low (one stub read) |
| **Halo's Gate** | Yes (±N neighbor walk) | Yes | Exact if neighbor unhooked | Low (walk up to 32 neighbors) |
| **Tartarus' Gate** | Yes (multi-pattern match incl. `jmp` hooks) | Yes | Exact | Medium |
| **FreshyCalls** | Yes (sorts stub addresses, derives SSN from order) | Yes | Exact if no shuffle | Medium (sort entire Zw* list) |
| **Recycled Gate / DWhisper** | Yes (sorts Zw* exports by address, index = SSN) | Yes | Exact, hook-immune | High (O(n log n) at init, O(1) lookup after) |

**Default choice on modern Windows (build ≥ 19041)**: **Recycled Gate / DWhisper**. It is hook-immune by design (never reads stub bytes), runs once at init with O(n log n) cost, and lookup is O(1) after. The other strategies retain educational value but none offer a production advantage.

### Why the "read the stub" strategies lose on modern EDRs

Hell's Gate reads byte `+4` of the Nt* stub expecting `B8 <ssn:4>`. Modern inline hooks replace the stub with `E9 <jmp>` at byte 0, making byte `+4` garbage. Halo's/Tartarus walk to neighbor stubs hoping they are unhooked — this fails on EDRs that hook *all* Nt* stubs (Defender for Endpoint on Server 2022 does this by default). FreshyCalls sorts stub addresses — fine in theory, but the sort order assumption breaks on Kaspersky-style hooks that relocate stubs.

RecycledGate sidesteps all of this: it enumerates ntdll's **export table** (a read-only data structure in `.edata`, not modified by stub hooks), extracts only `Zw*` exports, sorts them by address, and derives SSN from position in the sorted list. This is a structural property of how Windows ntdll is built, not of what the stubs look like.

---

## The dispatch side — indirect vs direct

**Direct syscall**: your own code emits `syscall` — call stack shows your module as source. Trivially flagged.

**Indirect syscall**: your code calls `syscall;ret` gadget **inside ntdll**. From inside a CALL, the callstack at syscall time is:

```
ntdll!NtSomeCleanStub+0x12    (syscall;ret gadget from another Nt* stub)
  ← your trampoline
    ← your high-level caller
```

From an EDR's perspective: "syscall from ntdll" is normal. "syscall from nonstandard address" is anomalous.

**Where is the gadget?** Every non-hooked Nt* stub ends with `0F 05 C3` (`syscall; ret`). Pick any clean Nt* stub + 18 bytes = `syscall;ret` gadget address. RecycledGate's `GetRecyCall` enumerates Nt/Zw exports, validates the 3-byte pattern at `func_addr + 18`, and returns the address of the `syscall` instruction.

**Gotcha**: if the target Nt* stub is itself hooked, the 3-byte pattern at `+18` is gone. Scan all Nt/Zw exports, not just one — collect all unhooked `syscall;ret` sites and pick one at random (resilience) or by policy (prefer gadgets from different stubs per call, to vary your callstack signature).

---

## Decision matrix

```
Target EDR profile:
│
├── No hook on ntdll (EDR disabled, or using only ETW-TI kernel-side)
│   └── Direct syscall from a CALL inside ntdll is fine. Use RecycledGate
│       for consistency; SSNs resolve correctly from unhooked stubs.
│
├── IAT hook only (legacy AV, Defender early builds)
│   └── Hell's Gate works. But use RecycledGate anyway — future-proof.
│
├── Inline hook at stub byte 0 (modern Defender, SentinelOne, CrowdStrike)
│   └── Hell's fails. Use RecycledGate or Tartarus'. Halo's if you need
│       minimal code size (~40 LOC including neighbor walk).
│
├── Inline hook + kernel callback mirror (Defender for Endpoint, Server 2022)
│   └── Indirect syscall alone does NOT evade — callback fires regardless.
│       Combine with: SilentMoonwalk DESYNC stack spoof + sleep obfuscation.
│
└── Nirvana instrumentation callback (research-grade / some HIDS)
    └── Every syscall trap is intercepted kernel-side regardless of userland
        technique. Indirect dispatch is irrelevant here; use process-hollow
        or module-stomp and get out of the user-mode game.
```

---

## RecycledGate / DWhisper — the canonical algorithm

### Init

```
1. PEB walk → find ntdll base (second entry in InMemoryOrderModuleList)
2. Parse PE headers → locate export directory
3. Iterate ExportDirectory.AddressOfNames
4. Filter: keep only names starting with "Zw"
5. Build list of (name_hash, export_rva)
6. Sort list by export_rva ascending
7. For each entry at index i: SSN[hash] = i
```

**Why Zw, not Nt?** Zw* and Nt* exports are aliases in ntdll (same function). Iterating Zw* guarantees one entry per syscall (no duplicates from the renames), and the Zw prefix is stable across builds.

**Why sort by RVA?** Microsoft builds ntdll with stub addresses monotonically assigned per-SSN at link time. The sorted-by-address order reconstructs the SSN table. Verified stable from Windows 7 through Windows 11 24H2.

**Name hashing**: SSNs are stored by hash, not by plaintext name. Use a seeded hash (FNV-1a with a random seed at compile time, or SHA-256 truncated to 64 bits) so the resulting table in your binary does not contain readable strings like `"NtAllocateVirtualMemory"`. The seed is a compile-time constant; regenerate per build for per-sample uniqueness.

### Lookup

```
hash = seeded_hash("NtAllocateVirtualMemory")
ssn = SSN_TABLE[hash]     // O(1) hashmap
gadget = find_syscall_ret_gadget()  // cached at init
return (ssn, gadget)
```

---

## The dispatcher's contract

```
execute(ssn: u16, syscall_gadget: *const u8, args...) -> NTSTATUS
```

ASM trampoline minimum:

```asm
; RCX = ssn, RDX = gadget, R8/R9/[stack] = args...
; ABI-compliant Win64 entry: SSN in RCX, gadget in RDX, args shifted right by 2
mov  eax, ecx          ; SSN → EAX
mov  r11, rdx          ; gadget → R11
mov  rcx, r8           ; arg1 → RCX
mov  rdx, r9           ; arg2 → RDX
mov  r8,  [rsp+0x28]   ; arg3
mov  r9,  [rsp+0x30]   ; arg4
; args 5+: copy from [rsp+0x38..] to [rsp+0x28..] (shift-left by 0x10)
mov  r10, rcx          ; syscall ABI: kernel clobbers RCX, reads R10
call r11               ; CALL syscall;ret gadget
ret
```

**Frame layout gotcha**: your caller passes `ssn` and `gadget` as the first two args, which consumes RCX/RDX. The actual NT API args shift by two. Every arg-shuffling ASM trampoline has to compensate; the canonical approach is the one above.

**Shadow space**: the gadget is a legitimate Win64 function target, so you **must** reserve 0x20 bytes of shadow space before the CALL. Omitting this causes `STATUS_ACCESS_VIOLATION` inside the kernel's syscall handler on some builds (kernel's unwinder expects shadow).

---

## Composition with stack spoofing

The spoofer gets `(ssn, gadget, args)` after the dispatcher has resolved SSN. The interface:

```
// plain indirect dispatch
nt_status_t indirect_execute(u16 ssn, void *gadget, ...args...);

// spoofed indirect dispatch
nt_status_t spoofed_execute(u16 ssn, void *gadget, SpoofContext *ctx, ...args...);

// composed
if (ctx != NULL)
    return spoofed_execute(ssn, gadget, ctx, args);
else
    return indirect_execute(ssn, gadget, args);
```

The spoofer does not care how SSN was resolved. The dispatcher does not care how the callstack was spoofed. Keep the two modules separate; compose at the top level.

See `stack-spoofing/SKILL.md` for the spoofer side.

---

## Layered syscall interception

Some implants need to intercept specific NT APIs before they reach the gate (e.g., detect `NtSuspendThread` calls on `GetCurrentThread()` and abort). The pattern:

```go
type LayeredSyscall struct {
    Syscall  // embedded; unoverridden calls delegate
}

// Override a specific syscall
func (s *LayeredSyscall) NtSuspendThread(h Handle) NTSTATUS {
    if h == currentThreadHandle() {
        return STATUS_INVALID_HANDLE  // pre-hook
    }
    return s.Syscall.NtSuspendThread(h)  // fall through
}
```

Use for:
- Blocking self-suspension primitives
- Logging a subset of NT calls during red team operations
- Replacing a specific NT API with a safer or stealthier variant

The Go idiom above uses struct embedding. In Rust: composition with trait delegation (manually implement the `Syscall` trait, forwarding each method except the ones you intercept). In C: function pointer table, with the wrapper calling the next layer unless it has its own override.

---

## The six implementation rules

**R1. Resolve SSN at runtime, never hardcode.** Hardcoded SSNs break on the first Patch Tuesday. RecycledGate init is O(n log n), runs once, caches everything. There is no reason to hardcode.

**R2. Use a seeded hash for the SSN table keys.** Plaintext `"NtAllocateVirtualMemory"` in `.rdata` is trivially grepable by forensics. Hash keys with a compile-time-constant seed so the table contents do not leak API names. Common pattern: `FNV-1a` over `(seed || api_name_lowercased)`.

**R3. Cache the `syscall;ret` gadget at init.** Rescanning per-call wastes ~1ms on a typical ntdll; at high call rates this matters. More importantly: a scanner running at every dispatch is a behavioral pattern EDRs can detect. Scan once, cache the address, invalidate on suspected hook drift (rare).

**R4. Validate the gadget before caching.** If the stub you picked is itself hooked, `+18` no longer reads `0F 05 C3`. Validate with a 3-byte compare and fall through to the next export. `GetRecyCall` in RecycledGate does this; reimplementations often skip it and then fail mysteriously on specific Defender builds.

**R5. Handle 6+ arg syscalls correctly.** The trampoline's arg-shift-by-2 logic must extend through `[rsp+0x28..0x38..0x40..]`. Most published PoCs handle only 4 args (RCX/RDX/R8/R9) and silently break on `NtCreateThreadEx(11 args)`. Test with `NtQuerySystemInformationEx` (6 args) or `NtCreateThreadEx` (11) before trusting.

**R6. Emit minimal strings in release.** `"ntdll.dll"`, `"Zw"`, `"Nt"` can all be obfuscated via compile-time XOR or a custom `Xr/Xh` macro. The `RecycledGate` reference codebase uses `obfuscation.Xr(obfuscation.Mr, mNtdll)` where `mNtdll` is a hex-encoded ciphertext. A loader binary that `strings` reveals no NT API names is substantially harder to triage.

---

## Languages — what changes

### C / C++ (mingw-w64)

- Flat asm file (`.s`) called from C is cleanest. Inline asm in C is tolerable for a single trampoline; becomes fragile for 4+ argcount variants.
- Emit 4 variants: `indirect_syscall4`, `_6`, `_11`, `_18` for different arg counts. Compilers optimize stack shuffling better when the size is fixed.
- Link without CRT: `-nostdlib -fno-ident -Wl,-e,<your_entry>`.

### Rust

- `global_asm!` for the trampoline; call via `extern "win64"`.
- SSN table: `phf::Map` with compile-time-constant seeded hashes.
- Zero-alloc dispatch path: return `NTSTATUS` by value, no `Result` / heap. Call sites handle status checking.
- Avoid `std` entirely in the implant; the dispatcher is `no_std + no_main`.

### Go

- Plan 9 ASM trampoline (`asm_x64.s`). Function signature:
  ```go
  //go:nosplit
  //go:noescape
  func reCycall(ssn uint16, gadget uintptr, args ...uintptr) (errcode uint32)
  ```
- `//go:nosplit` is mandatory: prevents the Go runtime from inserting a stack-growth check that would corrupt the trampoline's register state.
- `//go:noescape` lets the compiler keep args in registers/on stack instead of boxing.
- Set `LastError` to 0 via `TEB[gs:30h][68h]` at trampoline entry if the NT status relies on no prior error leaking.

Full code sketches per language in [references/lang-c-rust-go.md](references/lang-c-rust-go.md).

---

## Resources

- [references/lang-c-rust-go.md](references/lang-c-rust-go.md) — Per-language dispatcher skeletons: C (mingw-w64 AT&T .s), Rust (`global_asm!`), Go (Plan 9), plus SSN table init patterns and obfuscation hooks
- [references/strategies.md](references/strategies.md) — In-depth on each SSN resolution strategy, detection footprint per strategy, migration between strategies, hook-pattern reverse engineering

### External references

- Hell's Gate — @smelly__vx, @am0nsec (2020) — github.com/am0nsec/HellsGate
- Halo's Gate — Sektor7 (2020) — blog.sektor7.net/#!res/2021/halosgate.md
- Tartarus' Gate — @trickster0 (2021) — github.com/trickster0/TartarusGate
- FreshyCalls — @crummie5 (2021) — github.com/crummie5/FreshyCalls
- RecycledGate — @thefLink — github.com/thefLink/RecycledGate
- `SysWhispers3` — @klezVirus — github.com/klezVirus/SysWhispers3
- NtDoc syscall cross-reference — `ntdoc.m417z.com`
- Peter Ferrie, *"Inside Windows"* series — Virus Bulletin
