---
name: windows-internals-dev
description: "Auth/lab dev: Windows internals; PEB/TEB, PE/COFF, syscalls, unwinding, memory/heap, tokens, kernel objects, ETW/AMSI telemetry."
license: MIT
compatibility: "Windows 10 1809 through Windows 11 24H2, x86-64 and ARM64; Kernel structures referenced from Windows 11 22H2/24H2 public debug symbols."
metadata:
  author: AeonDave
  version: "1.0"
---

# windows-internals

Foundational Windows internals for programmatic work: writing implants and loaders, reversing your own binaries, building EDR/AV tooling, or understanding what the kernel actually does under a Win32 call. This is **structural and mechanical** knowledge — if you need tool usage, look in `offensive-tools/`; if you need language-specific patterns, look in `*-patterns` skills.

**What this skill gives you**: the offsets, structures, data flows, and invariants you need to touch Windows at the NTAPI/undocumented/kernel-struct level without guessing. Every claim here is either stable across the supported build range or explicitly flagged as version-dependent.

**Rule of thumb**: if your code uses any Win32 API that is documented, this skill is not needed. If you are walking a PEB pointer, parsing UNWIND_INFO, resolving SSNs, spoofing a call stack, patching ETW-TI, or touching a kernel object directly — start here.

---

## When to activate

- Writing an implant, loader, or BOF that cannot use traditional imports
- Building indirect syscall dispatch (Hell's / Halo's / Tartarus / Recycled Gate)
- Reversing your own release binary to verify ASM stubs land correctly
- Implementing call-stack spoofing (SilentMoonwalk / Draugr / CHRYSALIS)
- Patching AMSI, ETW, or ETW-TI in userland; understanding what kernel telemetry remains
- Writing a kernel driver that registers process/thread/image/registry callbacks
- Designing around mitigations: CFG, XFG, CET shadow stack, HVCI, Credential Guard
- Reasoning about detection surface when designing an offensive technique

If the question is "what function do I call" — wrong skill. If the question is "what does the OS actually do when I call this, and what can I touch directly instead" — right skill.

---

## Map of the territory

Everything below is a pointer into a reference file. Load only what you need.

| Domain | File | Covers |
|--------|------|--------|
| **Process/thread state blocks** | `references/peb-teb.md` | PEB, TEB, LDR data, InMemoryOrderModuleList, ApiSetMap, module walking, hash-based resolution |
| **PE / COFF** | `references/pe-format.md` | DOS/NT headers, sections, exports (incl. forwarded), imports, relocations, TLS callbacks, .pdata, COFF object files |
| **Syscalls** | `references/syscalls.md` | Syscall ABI (x64/ARM64), SSN resolution strategies, direct/indirect dispatch, gate variants, stub layout |
| **Exception handling** | `references/exception-unwind.md` | SEH, VEH, UNWIND_INFO, RtlLookupFunctionEntry, RtlVirtualUnwind, KiUserExceptionDispatcher, call-stack spoofing frames |
| **Memory** | `references/memory-management.md` | Virtual memory (NtAllocate/Protect/Write/Read), sections, VADs, NT heap vs Segment heap, LFH |
| **Threads / APCs** | `references/threads-apcs.md` | Thread creation, suspension, CONTEXT struct, user/kernel/Special APCs, thread hijacking primitives |
| **Tokens / privileges** | `references/tokens-privileges.md` | TOKEN struct, privileges, integrity levels, impersonation vs primary, DuplicateTokenEx semantics |
| **Kernel objects** | `references/kernel-objects.md` | EPROCESS, ETHREAD, KPCR/KPRCB, handle table, object manager namespace, kernel callbacks |
| **Mitigation surface** | `references/evasion-surface.md` | ETW/ETW-TI, AMSI, CFG/XFG/CET, VBS/HVCI/CG, userland hook detection/unhooking |

---

## Quick-reference: x86-64 Windows ABI

Non-negotiable invariants. Violating any of these causes silent corruption that surfaces later.

| Invariant | Rule |
|---|---|
| Stack alignment | `rsp % 16 == 0` at every `call` site |
| Shadow space | 32 bytes reserved by caller before every `call` (`sub rsp, 0x28` min with alignment) |
| Integer args (1–4) | `rcx`, `rdx`, `r8`, `r9` |
| Integer args (5+) | Stack, caller-allocated |
| Float args (1–4) | `xmm0`–`xmm3` |
| Integer return | `rax` |
| Callee-saved (int) | `rbx`, `rbp`, `rsi`, `rdi`, `r12`–`r15` |
| Callee-saved (xmm) | `xmm6`–`xmm15` |
| Syscall number | `rax` (user-mode SSN before `syscall`) |
| Syscall arg 4 | `r10` — kernel clobbers `rcx`, so userland stub must `mov r10, rcx` |
| TEB | `gs:[0x30]` |
| PEB | `gs:[0x60]` (or `[[gs:0x30] + 0x60]`) |

---

## Quick-reference: ARM64 Windows ABI

| Invariant | Rule |
|---|---|
| Stack alignment | `sp % 16 == 0` (hardware enforced at PSTATE transitions) |
| Integer args (1–8) | `x0`–`x7` |
| Float args (1–8) | `d0`–`d7` |
| Integer return | `x0` |
| Callee-saved (int) | `x19`–`x28`, `x29` (fp), `x30` (lr) |
| Callee-saved (vec) | `d8`–`d15` |
| Syscall number | `x8` |
| Syscall instruction | `svc #0` |
| TEB | `x18` (platform register, reserved by Windows) |
| PEB | `[x18 + 0x60]` |

ARM64EC (x64 emulation compatible) uses a modified register mapping — x0..x15 map to rcx,rdx,r8,r9 etc. If writing ARM64EC ASM, consult the Microsoft ARM64EC ABI doc, not this table.

---

## Common structure offsets (x64, Windows 10–11)

These are the 12 offsets you will look up most often. Full layouts in `references/peb-teb.md`.

| Structure | Field | Offset | Notes |
|---|---|---|---|
| TEB | ProcessEnvironmentBlock | 0x60 | PEB pointer |
| TEB | ThreadLocalStoragePointer | 0x58 | TLS slot array |
| TEB | LastErrorValue | 0x68 | GetLastError storage |
| PEB | BeingDebugged | 0x02 | 1 byte |
| PEB | ImageBaseAddress | 0x10 | Main .exe base |
| PEB | Ldr | 0x18 | PEB_LDR_DATA pointer |
| PEB | ProcessParameters | 0x20 | RTL_USER_PROCESS_PARAMETERS |
| PEB | ApiSetMap | 0x68 | API_SET_NAMESPACE pointer |
| PEB_LDR_DATA | InLoadOrderModuleList | 0x10 | Head of load order list |
| PEB_LDR_DATA | InMemoryOrderModuleList | 0x20 | Head of memory order list |
| LDR_DATA_TABLE_ENTRY | DllBase | 0x30 | Module base address |
| LDR_DATA_TABLE_ENTRY | BaseDllName | 0x58 | UNICODE_STRING |

> When walking `InMemoryOrderModuleList`, the `Flink` you dereference points **into** `InMemoryOrderLinks` (offset 0x10) of the next entry, not its base. Subtract 0x10 to get the entry pointer.

---

## The 10 things you will do over and over

1. **Get a module base without LoadLibrary** — walk PEB → Ldr → InMemoryOrderModuleList, hash `BaseDllName`, compare. See `peb-teb.md` §Module Walk.
2. **Resolve an export by hash** — parse target module's PE headers → `DataDirectory[0]` → iterate AddressOfNames / AddressOfOrdinals / AddressOfFunctions. See `pe-format.md` §Export Walk.
3. **Resolve an SSN** — Hell's Gate reads the function stub at the resolved Nt* address and extracts the immediate after `mov eax, imm32`. Halo's / Tartarus Gate fall back when the stub is hooked. Recycled Gate enumerates all `Zw*` exports and sorts by RVA to derive SSN from index. See `syscalls.md`.
4. **Find a `syscall; ret` gadget** — scan any Nt* stub body for the byte sequence `0F 05 C3`. Used by Recycled Gate / indirect syscall paths to route all syscalls through ntdll. See `syscalls.md` §Indirect Dispatch.
5. **Parse UNWIND_INFO for a function** — binary-search `.pdata` (`DataDirectory[3]`) for a `RUNTIME_FUNCTION` whose `[BeginAddress, EndAddress)` contains your RIP. Walk `UnwindCodes[]` to derive frame size and saved registers. See `exception-unwind.md`.
6. **Build a spoofed call stack** — find two chained unwind frames (`UWOP_SET_FPREG` terminator + `UWOP_PUSH_NONVOL(rbp)` second frame), plant fake return addresses on the real RSP matching those unwinders, then `jmp` into the target. The unwinder validates; the scanner walks the frame list and sees legitimate module addresses. See `exception-unwind.md` §Call-stack Spoofing.
7. **Open a token, check elevation, impersonate** — `NtOpenProcessToken` → `NtQueryInformationToken(TokenElevation)` / `TokenUser` → `NtDuplicateToken(SecurityImpersonation)` → `NtSetInformationThread(ThreadImpersonationToken)`. See `tokens-privileges.md`.
8. **Inject into another process** — allocate remote memory (`NtAllocateVirtualMemory` or section + `NtMapViewOfSection`), write payload, create thread (`NtCreateThreadEx`) or queue APC (`NtQueueApcThread[Ex2]`). See `threads-apcs.md`.
9. **Patch AMSI / ETW in-process** — locate `AmsiScanBuffer` (amsi.dll) or `EtwEventWrite` / `NtTraceEvent` (ntdll.dll), flip page protection RW, write a 1-byte `ret` or `mov eax, 0x80070057; ret` prologue, restore protection. See `evasion-surface.md`.
10. **Walk the PSP callback list (kernel)** — kernel shellcode iterates `PspCreateProcessNotifyRoutine` (array of 64 `EX_CALLBACK_ROUTINE_BLOCK` pointers with low-bit tagging) and nulls entries belonging to EDR drivers. See `kernel-objects.md` §Kernel Callbacks.

---

## Syscall dispatch decision tree

```
Need to invoke an Nt* function without touching ntdll's hooked stub?
│
├── Can ntdll.dll be walked? (99% yes — ntdll is first LDR entry)
│   │
│   ├── YES → Use PEB walk to resolve Nt* address
│   │         │
│   │         ├── Stub unhooked? → Hell's Gate (read SSN from stub at +4)
│   │         │
│   │         └── Stub hooked?   → Halo's/Tartarus Gate (walk neighbors ±1)
│   │                              OR Recycled Gate (sort Zw* exports by RVA)
│   │
│   └── NO (unusual — stripped PEB or sandbox) → Hard-coded SSN table
│                                                 (brittle, version-specific)
│
├── Executing the syscall:
│   │
│   ├── Direct   → Emit `syscall` instruction in your own .text
│   │              • Callstack has your module → red flag
│   │
│   ├── Indirect → Emit `call <syscall;ret gadget inside ntdll>`
│   │              • Callstack shows ntdll frame → clean
│   │              • Requires gadget discovery pass
│   │
│   └── Desync   → Build spoofed 3-frame call stack, `jmp` into gadget
│                  • Callstack shows chain of legit frames
│                  • Full UNWIND_INFO math required
│
└── 6+ args? → 5th arg onwards goes on stack after shadow space
                 Stubs vary: see syscalls.md §Multi-arg variants
```

---

## Architectural lifecycles you must understand

### DLL load (`LdrLoadDll`)

1. Canonicalize name, check if in `KnownDlls` (section object namespace under `\KnownDlls`)
2. If present → `NtOpenSection` on the pre-mapped section, `NtMapViewOfSection` into process
3. If absent → resolve via search path, `NtOpenFile` → `NtCreateSection(SEC_IMAGE)` → `NtMapViewOfSection`
4. Process imports recursively (depth-first — causes loader lock cascades)
5. Walk `IMAGE_TLS_DIRECTORY.AddressOfCallBacks` array, call each with `DLL_PROCESS_ATTACH`
6. Call `DllMain` with `DLL_PROCESS_ATTACH`
7. Insert into LDR lists, notify registered load image callbacks (`PsSetLoadImageNotifyRoutine` fires now)

**Pitfall**: TLS callbacks from a DLL loaded via `LoadLibrary` are **not** invoked for already-running threads, only for threads created after. They are invoked for the current thread on `DLL_PROCESS_ATTACH`. Statically-linked DLLs' TLS callbacks are fired for all existing threads at process init.

### Thread creation (`NtCreateThreadEx`)

1. Kernel allocates ETHREAD, creates TEB in process VA space
2. Initial context populated from caller params (start address, parameter, stack info)
3. If `THREAD_CREATE_FLAGS_CREATE_SUSPENDED` set → thread placed in waiting state
4. Otherwise queued for execution
5. First user-mode code on thread is `LdrInitializeThunk` (unless `THREAD_CREATE_FLAGS_SKIP_THREAD_ATTACH`) — runs DLL TLS callbacks, `DllMain(DLL_THREAD_ATTACH)` for every loaded DLL, then jumps to start address

**Offensive note**: `SKIP_THREAD_ATTACH` skips the entire LdrInit chain — useful for shellcode threads where you do not want `DLL_THREAD_ATTACH` to fire across every loaded DLL (which can alert hooks or crash if a DLL's DllMain mismatches).

### Exception dispatch (user-mode)

1. Hardware or software raises → kernel transfers to `KiUserExceptionDispatcher` in ntdll
2. `RtlDispatchException` walks the function table starting at faulting RIP
3. For each frame: `RtlLookupFunctionEntry` → `RtlVirtualUnwind` → check for registered handler
4. Handler decides: `ExceptionContinueSearch` / `ContinueExecution`
5. If unhandled → `UnhandledExceptionFilter` → VEH chain → process terminate via `NtTerminateProcess`

**Offensive use**: VEH registration (`RtlAddVectoredExceptionHandler`) is a pre-SEH hook, runs before stack-based handlers. Common abuse: register VEH, trigger a fault, have VEH set `ContextRecord->Rip` to shellcode, return `ExceptionContinueExecution`. Leaves minimal forensic trace compared to thread creation.

---

## Detection surface to reason about

When you apply any technique, the following signals are potentially visible. This is a high-level map; details in `evasion-surface.md`.

| Signal | Who sees it | What triggers it |
|---|---|---|
| Userland hooks | EDR in-process agent | Calling `Nt*` via ntdll stub |
| ETW (userland) | EDR agent or `Microsoft-Windows-*` consumers | `EtwEventWrite` inside ntdll/kernel32 wrappers |
| ETW-TI (kernel) | PPL service consuming kernel events | Memory writes to remote processes, SUSPEND/RESUME, APC queue, etc. |
| AMSI | Registered AMSI providers (Defender) | Script content scanned by `AmsiScanBuffer` |
| Kernel callbacks | EDR driver | Process/thread/image/registry create, handle open |
| Minifilter | EDR filesystem driver | File open/read/write/create |
| Handle open audit | Kernel | Any `NtOpen*` on protected process (LSASS, etc.) |
| CFG violation | Process | Indirect call to non-valid target |
| Shadow stack mismatch | CET-enabled process | `ret` address mismatches shadow stack top |

**Important reality**: modern advanced EDRs (Defender for Endpoint, Elastic, CrowdStrike recent builds) rely primarily on kernel callbacks and ETW-TI. Userland unhooking by itself does nothing against them. Plan your technique accordingly — see `evasion-surface.md` §EDR Architecture.

---

## Pitfalls and invariants

**PEB walk invariants**
- First entry after list head in `InLoadOrderModuleList` is the main executable
- First entry in `InMemoryOrderModuleList` is ntdll.dll (loader init guarantees this)
- `BaseDllName` is a `UNICODE_STRING` (16 bytes: Length, MaximumLength, Buffer). Length is in **bytes**, not chars
- Module name comparisons must be case-insensitive (use lowercase for both operands of hash)

**PE parsing invariants**
- Validate `e_magic == 0x5A4D` ("MZ") and `e_lfanew > 0 && e_lfanew < PE_file_size`
- Validate `NT_Signature == 0x00004550` ("PE\0\0")
- On 64-bit PE, `OptionalHeader.Magic == 0x20B`; export directory RVA at `OptionalHeader + 0x70` (DataDirectory[0].VirtualAddress lives at offset 0x88 of OptionalHeader on x64, or offset 0x78 of IMAGE_NT_HEADERS64 if counting from NT base)
- Forwarded exports: if an export RVA is **within** `DataDirectory[0]` range, it is a forwarder string `"dll.function"` — recursively resolve

**Manual mapping / reflective DLL invariants**
- The OS loader normally runs TLS callbacks and calls the PE `AddressOfEntryPoint`, which is usually CRT startup before user `DllMain`.
- A custom reflective loader may define a different contract: exported `DllMain` can be a minimal shellcode attach gate, followed by an explicit reflective start export. Do not replace that with `AddressOfEntryPoint` just because it resembles the OS loader; verify the payload's `reserved` semantics and runtime markers first.
- For Rust cdylibs, distinguish loader lifecycle bugs from runtime-library boundary bugs. If profile decode, session encode, and DNS resolve already work, a crash in `TcpStream::connect_timeout` is more likely a socket/runtime primitive issue than an earlier PE entrypoint issue.
- Generated shellcode arrays are build artifacts. After changing a reflective loader, regenerate and rebuild the final wrapper before testing; source edits alone do not change the payload under test.

**Syscall invariants**
- On x64, before `syscall`: `r10 = rcx`. Kernel clobbers `rcx` with return address
- Wow64 processes have a 32→64 transition through `wow64cpu!CpupReturnFromSimulatedCode`; direct `syscall` from 32-bit code does **not** work — must go through the transition
- SSN drift between builds: hard-coded SSNs break on the first Patch Tuesday. Always resolve at runtime
- On ARM64: `svc #0` is the instruction; SSN goes in `x8` (not `w8`), args in `x0`–`x7`, then stack

**Unwind invariants**
- `UNWIND_INFO.CountOfCodes` is rounded up to even; iterate in pairs
- `UWOP_ALLOC_SMALL`: size encoded as `OpInfo * 8 + 8` (range 8..128)
- `UWOP_ALLOC_LARGE`: size in following 2 or 4 bytes; `OpInfo == 0` → 2-byte scaled by 8, `OpInfo == 1` → 4-byte raw
- Chained unwind info (`UNW_FLAG_CHAININFO`): last code entry is `RUNTIME_FUNCTION` of parent, not a code — follow it
- Functions without `.pdata` (leaf functions with no prologue) cannot be unwound — useless as spoof frames

**Token invariants**
- `NtOpenProcessToken(NtCurrentProcess(), TOKEN_QUERY, ...)` always succeeds — you own your own token
- `NtOpenProcessToken` on another process requires at minimum `PROCESS_QUERY_LIMITED_INFORMATION` on the process handle and `TOKEN_DUPLICATE` for impersonation
- Primary tokens cannot be assigned to threads — must `DuplicateTokenEx` with `TokenImpersonation` first, or use `CreateProcessWithTokenW` for new process
- Impersonation token integrity cannot exceed thread's primary token integrity without `SeImpersonatePrivilege`

**Memory invariants**
- `NtProtectVirtualMemory` rounds up to page granularity — querying the old protection returns the protection of the **first** page in the range
- `NtAllocateVirtualMemory` with `MEM_COMMIT` over an already-committed region succeeds (idempotent commit) and preserves contents; over a reserved-but-not-committed region zero-fills
- Writing to a `PAGE_NOACCESS` guard page raises `STATUS_GUARD_PAGE_VIOLATION` once, then converts to normal access — useful for trap-then-continue primitives

---

## Resources

### Companion skills

- [`stack-spoofing`](../stack-spoofing/SKILL.md) — Building call-stack spoof trampolines (Draugr / SilentMoonwalk / CHRYSALIS): frame-size math with `SAVE_NONVOL` safety filter, `FF 23` gadget scanner with debug instrumentation, Win11 22H2+ empirical gadget inventory, C/Rust/Go trampoline skeletons.
- [`indirect-syscall`](../indirect-syscall/SKILL.md) — Building indirect syscall dispatchers: SSN resolution (Hell's / Halo's / Tartarus / RecycledGate / DWhisper), `syscall;ret` gadget discovery with caching, name obfuscation, per-language dispatcher implementations with arg-count variants.

Use those skills when writing code; use this one for the underlying structures and invariants.

### Reference files in this skill

- `references/peb-teb.md` — PEB, TEB, LDR data, ApiSetMap, module walking, hash-based resolution
- `references/pe-format.md` — DOS/NT headers, sections, exports, imports, TLS callbacks, .pdata, COFF objects
- `references/syscalls.md` — Syscall ABI, SSN resolution (Hell's/Halo's/Tartarus/Recycled/HWSyscall), direct/indirect dispatch
- `references/exception-unwind.md` — SEH/VEH, UNWIND_INFO, RtlVirtualUnwind, KiUserExceptionDispatcher, call-stack spoofing
- `references/memory-management.md` — Virtual memory, sections, VADs, NT heap / Segment heap / LFH
- `references/threads-apcs.md` — Thread creation, CONTEXT, user/kernel/Special APCs, thread hijacking
- `references/tokens-privileges.md` — TOKEN struct, privileges, integrity levels, impersonation
- `references/kernel-objects.md` — EPROCESS, ETHREAD, KPCR/KPRCB, handle table, object manager, kernel callbacks
- `references/evasion-surface.md` — ETW/ETW-TI, AMSI, CFG/XFG/CET, VBS/HVCI/CG, hook detection/unhooking
- Start with the narrowest subsystem reference that matches the current primitive; expand only when the chain crosses subsystems.
