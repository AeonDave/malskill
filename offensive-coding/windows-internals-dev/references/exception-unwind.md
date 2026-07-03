# Exception Handling and Stack Unwinding Reference

Complete coverage of x64 Windows exception mechanics: SEH / VEH / CEH, UNWIND_INFO format, `RtlLookupFunctionEntry`, `RtlVirtualUnwind`, `KiUserExceptionDispatcher` flow, and how all of this gets reused for offensive call-stack spoofing (SilentMoonwalk / Draugr / CHRYSALIS).

> **See also**: the dedicated [`stack-spoofing`](../../stack-spoofing-dev/SKILL.md) skill covers the **implementation** side of call-stack spoofing (frame-size math with `SAVE_NONVOL` safety filter, `FF 23` gadget scanners with debug instrumentation, per-build empirical gadget inventories, C/Rust/Go trampoline skeletons). This file is the **reference** for the underlying mechanisms; go to `stack-spoofing` when actually building a spoofer.

---

## Why x64 exception handling matters offensively

Windows x64 uses **table-based exception handling**. Unlike x86 (which maintained a per-thread chain of exception frames on the stack), x64 uses `.pdata` descriptors. Every function that touches the stack needs a `RUNTIME_FUNCTION` entry describing its prologue.

This means:
- Anyone can reconstruct a call stack from any `rsp` + `rip` pair by walking `.pdata`
- EDRs capture call stacks on syscalls / other events using `StackWalk64` or equivalent
- If your frame is not described in `.pdata`, the unwinder stops at your frame → "broken" call stack signal
- If you want a **convincing** call stack, you need to make each frame's `rip` correspond to a real function with valid `UNWIND_INFO`, and ensure each frame size matches the unwind data

---

## .pdata — RUNTIME_FUNCTION array

Located at `DataDirectory[3]` (IMAGE_DIRECTORY_ENTRY_EXCEPTION). Contiguous array sorted by `BeginAddress`, binary-searchable.

```c
typedef struct _RUNTIME_FUNCTION {
    DWORD BeginAddress;        // RVA
    DWORD EndAddress;          // RVA (exclusive)
    DWORD UnwindInfoAddress;   // RVA to UNWIND_INFO in .xdata (or continuation entry)
} RUNTIME_FUNCTION;
// sizeof = 12
```

Finding the entry for a given RIP:

```c
PRUNTIME_FUNCTION find_runtime_function(PVOID dll_base, DWORD rip_rva) {
    DWORD pdata_rva  = nt->OptionalHeader.DataDirectory[3].VirtualAddress;
    DWORD pdata_size = nt->OptionalHeader.DataDirectory[3].Size;
    PRUNTIME_FUNCTION table = (PRUNTIME_FUNCTION)((PBYTE)dll_base + pdata_rva);
    DWORD count = pdata_size / sizeof(RUNTIME_FUNCTION);

    // Binary search
    DWORD lo = 0, hi = count;
    while (lo < hi) {
        DWORD mid = (lo + hi) / 2;
        if (rip_rva < table[mid].BeginAddress) {
            hi = mid;
        } else if (rip_rva >= table[mid].EndAddress) {
            lo = mid + 1;
        } else {
            return &table[mid];
        }
    }
    return NULL;
}
```

This is what `RtlLookupFunctionEntry` does internally.

---

## UNWIND_INFO structure

Lives in `.xdata` (or sometimes directly in `.rdata`). Pointed to by `RUNTIME_FUNCTION.UnwindInfoAddress`.

```c
typedef struct _UNWIND_INFO {
    UCHAR Version       : 3;  // Usually 1
    UCHAR Flags         : 5;  // UNW_FLAG_EHANDLER / UHANDLER / CHAININFO
    UCHAR SizeOfProlog;       // Bytes the prologue occupies
    UCHAR CountOfCodes;       // Number of UNWIND_CODE entries
    UCHAR FrameRegister : 4;  // Register used as frame pointer, or 0
    UCHAR FrameOffset   : 4;  // Scaled by 16
    UNWIND_CODE UnwindCode[CountOfCodes];
    // If UNW_FLAG_CHAININFO: followed by another RUNTIME_FUNCTION (parent)
    // If UNW_FLAG_EHANDLER or UNW_FLAG_UHANDLER: followed by handler RVA + language-specific data
    // Array padded to multiple of 4 bytes
} UNWIND_INFO;
```

### Flags

| Flag | Value | Meaning |
|------|-------|---------|
| UNW_FLAG_EHANDLER | 0x01 | C++ exception handler present |
| UNW_FLAG_UHANDLER | 0x02 | Termination handler (__try/__finally) |
| UNW_FLAG_CHAININFO | 0x04 | Chained info — last code entry is parent RUNTIME_FUNCTION |

### UNWIND_CODE structure

```c
typedef union _UNWIND_CODE {
    struct {
        UCHAR CodeOffset;     // Offset within prologue where this operation occurs
        UCHAR UnwindOp  : 4;  // Opcode (UWOP_*)
        UCHAR OpInfo    : 4;  // Operation-specific info (register index, etc.)
    };
    USHORT FrameOffset;       // For multi-slot ops
} UNWIND_CODE;
// sizeof = 2
```

---

## UWOP opcodes — what the prologue did

| Opcode | Value | OpInfo meaning | Slots | What the prologue did |
|--------|-------|----------------|-------|------------------------|
| UWOP_PUSH_NONVOL | 0 | Register index | 1 | `push <reg>` |
| UWOP_ALLOC_LARGE | 1 | Size encoding | 2 or 3 | `sub rsp, <large>` |
| UWOP_ALLOC_SMALL | 2 | (size/8) - 1 | 1 | `sub rsp, <small>` (8..128) |
| UWOP_SET_FPREG | 3 | unused (uses FrameRegister/FrameOffset in header) | 1 | `lea rbp, [rsp + FrameOffset*16]` — **sets frame pointer** |
| UWOP_SAVE_NONVOL | 4 | Register index | 2 | `mov [rsp + offset*8], <reg>` |
| UWOP_SAVE_NONVOL_FAR | 5 | Register index | 3 | Large-offset variant |
| UWOP_EPILOG | 6 | (version 2) | varies | Marks epilog sequence |
| UWOP_SPARE_CODE | 7 | reserved | varies | |
| UWOP_SAVE_XMM128 | 8 | XMM register | 2 | `movdqa [rsp + offset*16], <xmm>` |
| UWOP_SAVE_XMM128_FAR | 9 | XMM register | 3 | Large-offset variant |
| UWOP_PUSH_MACHFRAME | 10 | 0 or 1 | 1 | Trap frame / interrupt (kernel only) |

### UWOP_ALLOC_SMALL decoding

OpInfo stores `(allocation_size / 8) - 1`. Valid range: allocation 8..128 bytes.
- OpInfo=0 → sub rsp, 8
- OpInfo=15 → sub rsp, 128

### UWOP_ALLOC_LARGE decoding

- OpInfo=0: next 1 slot contains `size / 8` (range 136..524280)
- OpInfo=1: next 2 slots contain raw size in bytes (up to 4 GB)

### UWOP_SET_FPREG

The critical opcode for stack spoofing. `FrameRegister` in the UNWIND_INFO header identifies the register used (typically RBP = 5). `FrameOffset` (header field) is the offset within rsp where the frame pointer was set, scaled by 16.

The unwinder, when walking through this frame, sets `UnwindContext->Rsp = FrameRegister - FrameOffset*16`. This is what "terminates" the unwind chain — the next frame's rsp comes from a non-stack register that the unwinder trusts.

### UWOP_PUSH_NONVOL (rbp)

Another critical opcode for spoofing. When the unwinder sees `UWOP_PUSH_NONVOL` with OpInfo=5 (rbp), it does:
- `UnwindContext->Rbp = *(PVOID*)UnwindContext->Rsp`
- `UnwindContext->Rsp += 8`

Combined with a subsequent `UWOP_SET_FPREG`, the unwinder sets `rbp` from a saved value, then pivots rsp based on rbp — which an attacker can plant.

---

## Frame size computation

Total stack allocation for a frame = sum of:
- Every `UWOP_PUSH_NONVOL`: +8 bytes
- Every `UWOP_ALLOC_SMALL`: +(OpInfo+1)*8
- Every `UWOP_ALLOC_LARGE`: +value from extra slot(s)
- Every `UWOP_SAVE_XMM128`: already inside ALLOC — **do not add**

```c
ULONG calc_frame_size(PUNWIND_INFO info) {
    ULONG frame = 0;
    ULONG i = 0;
    while (i < info->CountOfCodes) {
        UNWIND_CODE c = info->UnwindCode[i];
        switch (c.UnwindOp) {
            case UWOP_PUSH_NONVOL:
                frame += 8;
                i += 1;
                break;
            case UWOP_ALLOC_SMALL:
                frame += (c.OpInfo + 1) * 8;
                i += 1;
                break;
            case UWOP_ALLOC_LARGE:
                if (c.OpInfo == 0) {
                    frame += info->UnwindCode[i+1].FrameOffset * 8;
                    i += 2;
                } else {
                    ULONG raw = *(PULONG)&info->UnwindCode[i+1];
                    frame += raw;
                    i += 3;
                }
                break;
            case UWOP_SET_FPREG:
            case UWOP_SAVE_NONVOL:
                i += (c.UnwindOp == UWOP_SAVE_NONVOL ? 2 : 1);
                break;
            case UWOP_SAVE_XMM128:
                i += 2;
                break;
            case UWOP_SAVE_NONVOL_FAR:
            case UWOP_SAVE_XMM128_FAR:
                i += 3;
                break;
            default:
                i += 1;  // unknown → skip, log
                break;
        }
    }
    // +8 for return address the call pushed
    return frame + 8;
}
```

### Chained unwind info

If `UNW_FLAG_CHAININFO` is set, after the code array there is another `RUNTIME_FUNCTION` (12 bytes) pointing to the parent function. Useful for functions split into non-contiguous regions. When computing frame sizes for chain, recurse into parent.

---

## Exception dispatch flow (user mode)

### KiUserExceptionDispatcher

When the kernel detects an exception (fault, INT3, STATUS_GUARD_PAGE_VIOLATION, etc.) targeting user mode, it:
1. Saves user-mode context into an `EXCEPTION_RECORD` and `CONTEXT`
2. Pushes both onto the target thread's user-mode stack
3. Sets thread RIP to `ntdll!KiUserExceptionDispatcher`
4. Returns to user mode

`KiUserExceptionDispatcher` in ntdll:
1. Calls `RtlDispatchException(&ExceptionRecord, &Context)`
2. If it returns TRUE → `NtContinue(&Context, FALSE)` — continue execution with modified context
3. If it returns FALSE → `NtRaiseException(&ExceptionRecord, &Context, FALSE)` — re-raise

### RtlDispatchException

1. Walk VEH chain (registered by `RtlAddVectoredExceptionHandler`). Each handler can return:
   - `EXCEPTION_CONTINUE_SEARCH` → next handler
   - `EXCEPTION_CONTINUE_EXECUTION` → restart instruction at (possibly modified) context
2. If no VEH handled: walk SEH frames via `.pdata`:
   - Start at current `Rip`, find `RUNTIME_FUNCTION`
   - If `UNW_FLAG_EHANDLER` set, call the handler
   - Otherwise `RtlVirtualUnwind` to parent frame, repeat

### RtlVirtualUnwind

Given current `Rip`, `Rsp`, and the function's `UNWIND_INFO`:
1. Parses `UNWIND_CODE[]` in order (these describe prologue operations backward-applicable)
2. Reverses each operation: `UWOP_PUSH_NONVOL` → `pop reg` (set reg from stack, rsp+=8)
3. After the full code array, `Rsp` now points to the saved return address → pops it into `Rip`
4. Returns the handler function pointer (if any) and new frame state

The unwinder state after one call: `Rsp` points to caller's local frame, `Rip` is caller's PC. Repeating gives you the full call chain.

---

## SEH: __try / __except / __finally

MSVC `__try/__except` and `__try/__finally` compile to functions with `UNW_FLAG_EHANDLER` / `UNW_FLAG_UHANDLER`. Handler RVA is in the extra bytes after the `UNWIND_CODE` array. Language-specific data (scope table) describes the filter expressions and mapping from IP ranges to handler labels.

### C++ exceptions

C++ exceptions are thrown via `RaiseException` with code `0xE06D7363` ("msc" in ASCII) and a specific `EXCEPTION_RECORD` layout containing pointer to the thrown object and its type descriptor. Unwinding matches catch handlers against type, invokes destructors in the unwind path.

---

## VEH — Vectored Exception Handling

Registered via `RtlAddVectoredExceptionHandler` (also exposed as `AddVectoredExceptionHandler`). Runs **before** any SEH frame. Useful for:

- Global logging / crash reporting
- Anti-debug traps (`RaiseException` then handle in VEH)
- HWSyscall: set DR0 on a syscall instruction, register VEH, modify CONTEXT when fired

### VEH handler signature

```c
LONG NTAPI VehHandler(PEXCEPTION_POINTERS Pointers) {
    PEXCEPTION_RECORD er = Pointers->ExceptionRecord;
    PCONTEXT ctx         = Pointers->ContextRecord;

    if (er->ExceptionCode == STATUS_SINGLE_STEP) {
        // Hardware breakpoint fired
        ctx->Rax = my_ssn;
        ctx->Rip += <distance past hook>;
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

AddVectoredExceptionHandler(1 /* FirstHandler */, VehHandler);
```

### VEH pitfall

The VEH chain is stored in ntdll's data. EDRs can enumerate it and flag suspicious handlers. `RtlAddVectoredExceptionHandler` itself may be hooked. Registering via direct list manipulation requires access to `ntdll!LdrpVectorHandlerList`.

---

## Call-stack spoofing — SilentMoonwalk / DESYNC

### Goal

When an EDR captures the call stack at the moment of a sensitive syscall (e.g., via kernel-side stack-walk in ETW-TI), the stack appears to show a chain of legitimate ntdll/kernel32/msvcrt frames, with no trace of the attacker's module.

### The DESYNC trick

"Desync" refers to **diverging the execution path from the unwind metadata path**. Execution actually goes: attacker code → syscall. But the **unwind metadata** (driven by plant values on rsp) tells the unwinder: "this frame is inside RtlUserThreadStart; its caller is KernelBase!BaseThreadInitThunk; etc." — pointing at legitimate functions whose UNWIND_INFO happily validates the frame sizes.

### Required ingredients

1. **A `jmp [rbx]` gadget** (one register indirect jump) inside a legit module's `.text`. Used to enter the chain from attacker code after setting `rbx`.
2. **`add rsp, <X>; ret` gadget** where X matches a chosen frame size exactly. Used to pivot past planted values.
3. **A function with `UWOP_SET_FPREG` opcode in its prologue** — acts as a **terminator frame**. The unwinder, upon seeing SET_FPREG, sets rsp from a frame-register value we control.
4. **A function with `UWOP_PUSH_NONVOL(rbp)` in its prologue** (and no SET_FPREG) — used as the **second frame** that saves the fake rbp we plant.
5. **SSN + `syscall;ret` gadget** — standard indirect syscall dispatch.

### Building the context

A typical `DesyncContext` carries:

```c
struct DesyncContext {
    uintptr_t add_rsp_x_gadget;   // "add rsp, X; ret" gadget address
    uintptr_t add_rsp_x_value;    // X (must match second_frame_size)
    uintptr_t jmp_rbx_gadget;     // "jmp qword ptr [rbx]" gadget address
    uintptr_t first_frame_ret;    // Address inside SET_FPREG function, after call
    uintptr_t second_frame_ret;   // Address inside PUSH_NONVOL(rbp) function
    uintptr_t first_frame_size;   // Computed from UNWIND_INFO
    uintptr_t second_frame_size;
    uintptr_t jmp_rbx_frame_size; // Frame size of jmp_rbx_gadget's containing function
    uintptr_t rbp_plant_offset;   // Where to plant fake rbp inside second frame
};
```

### Gadget discovery routines

Scan each trusted module's `.text` for raw bytes:

- **`jmp [rbx]`** — `FF 23` (two bytes). Use a preceding `call` byte pattern to reduce false positives ("Eclipse" check: preceded by a call).
- **`add rsp, X; ret`** with short encoding: `48 83 C4 XX C3` (X is 8-bit immediate).
- **`add rsp, X; ret`** with long encoding: `48 81 C4 XX XX XX XX C3` (X is 32-bit).
- **POP gadgets**: `58 C3` (pop rax; ret), `5B C3` (pop rbx; ret), `59 C3` (pop rcx; ret), `5A C3` (pop rdx; ret), `41 58 C3` (pop r8; ret), ...
- **Standalone `ret`**: `C3` at a valid function boundary.

### Scanning .pdata for SET_FPREG functions

```c
for each RUNTIME_FUNCTION in .pdata:
    parse UNWIND_INFO
    for each UNWIND_CODE:
        if opcode == UWOP_SET_FPREG:
            record this function as terminator candidate
            frame_size = calc_frame_size(info)
            break
```

### Scanning for PUSH_NONVOL(rbp) functions without SET_FPREG

Similar scan, but require `UWOP_PUSH_NONVOL` with `OpInfo == 5` (rbp) and **no** `UWOP_SET_FPREG` in the same function. This function must not overwrite the saved rbp before the syscall path runs.

### Execution layout

At execution time, with rsp pointing somewhere in the thread's real stack:

```
rsp + 0x00   : return addr pointing to "add rsp, X; ret" gadget
rsp + 0x08   : filler / args area (X bytes worth) — sized so "add rsp, X; ret" lands at:
rsp + 0x10   : return addr pointing to first_frame_ret (inside SET_FPREG function)
rsp + 0x18..N: frame of that SET_FPREG function (filled with whatever, unwinder doesn't read most)
rsp + 0x??   : planted rbp value (referenced by FrameOffset in SET_FPREG header)
rsp + 0x??   : return addr pointing to second_frame_ret (inside PUSH_NONVOL(rbp) function)
rsp + 0x??   : frame of that function
rsp + 0x??   : saved rbp planted such that PUSH_NONVOL(rbp) unwinder step restores it
rsp + 0x??   : return addr pointing to top of real call chain (RtlUserThreadStart etc.)
```

Build the chain, `jmp` into the syscall;ret gadget (after moving SSN into rax). The syscall executes. Kernel captures call stack. Walks starting at `syscall;ret` address in ntdll → finds legit pdata entry, unwinds → reaches `add rsp, X; ret` → unwinds that (finds its pdata) → reaches SET_FPREG function → frame reset → PUSH_NONVOL(rbp) function → unwind → reaches original `RtlUserThreadStart`. Clean.

### Why the syscall `jmp` and not `call`?

A real `call` would push a return address from attacker memory onto the stack, which would then appear as a stack frame before the legit chain — **exposing** the attacker module. `jmp` lets the attacker plant the **correct** return address (pointing into a legit function) before entering the chain.

### Cleanup after syscall

After the syscall;ret returns, we need to get control back to attacker code while still presenting a clean stack (or at least not a detectably corrupted one). Typical approach: store real rsp at entry in a known register (e.g., `r12`, saved and restored), restore it via a short ASM epilogue.

### CHRYSALIS — Memory Bouncing context

Extends DESYNC with sleep obfuscation: before sleeping, encrypt .text (MBA-XOR), flip to RW, delay, XOR back, flip to RX. All driven by a `ChrysalisContext` struct containing:
- DesyncContext (for the syscalls inside the bounce sequence)
- Gadget addresses (hidden by obfuscation during sleep)
- .text base/size region descriptors
- Sleep API SSN+address pairs
- Runtime state for suspended threads

---

## SafeSEH / GS / CFG interaction with unwinding

- **GS cookie** — stack canary. Does not affect unwinding (canary is checked in epilogue, after unwind codes).
- **SafeSEH** — x86 only; lists valid SEH handlers in `LoadConfig`. On x64, all handlers are validated by being reachable via `.pdata`.
- **CFG (Control Flow Guard)** — checks indirect call targets. Call to a `jmp [rbx]` gadget **requires** the gadget address to be in the CFG valid target bitmap. If CFG is enabled on the calling module, the gadget target must be pre-registered via `SetProcessValidCallTargets` (kernelbase).
- **CET shadow stack** — tracks all return addresses in a separate shadow stack. On `ret`, HW compares real return address with shadow. Planted return addresses **will not match** shadow stack → `#CP` exception. Call-stack spoofing on CET-enabled targets requires either disabling CET on the thread (impossible without kernel) or avoiding `ret` in favor of `jmp` chains.

CET enforcement is per-process, triggered by `SET_PROCESS_MITIGATION_POLICY`. Most commodity applications have it disabled; EDR agents and browsers increasingly enable it.

---

## Detection surface for call-stack spoofing

- Kernel-side stack walk at syscall detects only frame-validity issues — if all frames are valid, clean
- User-mode hooks that capture stack via `CaptureStackBackTrace` → same unwinder path, same result (clean)
- **ETW-TI callstack events** (kernel provider, Win10 20H1+) capture stack. Elastic / Defender correlate with memory region characteristics
- **Unbacked memory in call stack** — if any frame's RIP falls in a page without a file backing, flagged. Planted frames point into real modules → no unbacked frame
- **Pattern match on gadgets** — the addresses of known gadgets (SilentMoonwalk reference gadgets in ntdll) are known. Defenders can hash frequently-used gadget combinations. Use fresh gadget discovery per-process to vary
- **Abnormal frame sequence** — e.g., a frame inside `memcpy` calling `NtAllocateVirtualMemory` is suspicious even if structurally valid. Frame sequence heuristics are the strongest ML-side detection

---

## Relevant APIs for reading/walking unwind data

| Function | Purpose |
|---|---|
| `RtlLookupFunctionEntry(Rip, &ImageBase, &HistoryTable)` | Find RUNTIME_FUNCTION for RIP; caches in HistoryTable |
| `RtlVirtualUnwind(UnwindType, ImageBase, Rip, FunctionEntry, Context, ...)` | Simulate one step of unwinding |
| `RtlCaptureContext(&Ctx)` | Snapshot current CONTEXT (useful for starting an unwind from current frame) |
| `RtlUnwindEx(...)` | Active unwind — actually modifies thread state |
| `RtlAddFunctionTable(RuntimeFnTable, EntryCount, BaseAddress)` | Register runtime-generated code with unwinder (for JITs, etc.) |
| `RtlDeleteFunctionTable` | Unregister |
| `RtlInstallFunctionTableCallback` | Dynamic .pdata lookup callback |
| `RtlAddGrowableFunctionTable` | Modern version; allows function table to grow |

Offensive use of `RtlAddFunctionTable`: register fake UNWIND_INFO for attacker-allocated RX memory so that stack walks through shellcode unwind cleanly → "backed" frames even though memory is unbacked.

---

## Appendix — Win11 22H2+ empirical gadget inventory

Measured on Windows 11 Build 22631.3880, retail un-patched. Gadget counts (`FF 23` = `JMP [RBX]` byte sequence inside a function body, preceded by an `E8` CALL within the same .pdata entry for Eclipse-style chaining) for the modules commonly used as stack-spoof sources:

| Module | Total `FF 23` | Max frame size passing `SAVE_NONVOL` safety | Eclipse candidates (CALL-preceded) |
|---|---|---|---|
| ntdll.dll | 6 | `0x40` | 0 |
| kernelbase.dll | 14 | `0x70` | 0 |
| kernel32.dll | 2 | 0 | 0 |
| user32.dll | 12 | `0x58` | 4 |
| wininet.dll | 34 | `0x98` | 18 |

**Implication for the classical `min_frame == 0xD8` threshold** used by older Draugr/SM references: on Win11 22H2+ kernelbase alone, **no gadget satisfies it**. Common failure mode when porting an older PoC: init returns "no gadget found", zero syscalls dispatched, silent fallthrough.

**Practical minimums** (shadow `0x20` + N stack args × 8 + alignment `0x08`):

| Syscall arg count | Minimum frame size needed |
|---|---|
| 4 (register-only) | `0x28` |
| 6 | `0x38` |
| 8 | `0x48` |
| 11 (`NtCreateThreadEx`) | `0x60` |
| 18 | `0x98` |

For most dispatcher needs, lowering the threshold to `0x60` unlocks the 14 kernelbase gadgets. For Eclipse cascade (CALL-preceded gadgets), wininet is the only module with meaningful supply on recent builds; plan for a one-time `LoadLibraryW` at init if your host process does not already import it.

### The `SAVE_NONVOL` safety filter

A gadget whose parent function has `UWOP_SAVE_NONVOL` at offset ≥ frame size will clobber the caller's shadow/arg region when its prologue executes. Symptom: 5th syscall arg overwritten → `STATUS_PARTIAL_COPY` from `NtReadVirtualMemory`, `STATUS_INVALID_PARAMETER` from larger APIs. On Win11 22H2+ kernelbase, ~8 of 14 `FF 23` sites fail this filter and must be rejected at discovery time.

Full treatment of the filter, the scanner with debug instrumentation, and per-build inventories: see [`stack-spoofing/references/frame-math.md`](../../stack-spoofing-dev/references/frame-math.md).
