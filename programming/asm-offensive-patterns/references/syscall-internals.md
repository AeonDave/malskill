# Syscall Internals — Windows NT & Linux x86-64

## Windows NT Syscall ABI

### Calling Convention (kernel side)
- RAX = System Service Number (SSN)
- **R10** = arg1 (NOT RCX — userland moves RCX to R10 before `SYSCALL`)
- RDX = arg2, R8 = arg3, R9 = arg4
- args 5+ on stack at [RSP+0x28], [RSP+0x30], ...
- 0x20 bytes shadow space reserved by caller
- Return value: NTSTATUS in RAX

### Why R10 instead of RCX
The `SYSCALL` instruction saves the return RIP into RCX and RFLAGS into R11.
The kernel ABI therefore uses R10 for argument 1 so RCX is available for the CPU to clobber.
The canonical trampoline:
```nasm
mov  r10, rcx    ; save arg1 from the Win64 usermode calling convention slot
mov  eax, SSN    ; system service number
syscall          ; SYSCALL clobbers RCX <- saved RIP, R11 <- RFLAGS
retn
```

---

## SSN (System Service Number) Stability

SSNs change between major Windows builds (7 / 8.1 / 10 / 11) and sometimes between minor patches.
Never hardcode SSNs — always resolve at runtime.

### Key resolution strategies

---

#### 1. Hell's Gate (2020 — am0nsec + RtlMateusz)

Read SSN directly from the `Zw*` stub's prologue bytes.

```
Clean stub layout:
  +0  4C 8B D1        mov r10, rcx
  +3  B8 XX 00 00 00  mov eax, SSN   <- bytes [3..4] = SSN (little-endian)
  +8  0F 05           syscall
  +10 C3              ret
```

```c
// Read SSN if stub is unhooked
if (stub[0]==0x4C && stub[1]==0x8B && stub[2]==0xD1 && stub[3]==0xB8)
    ssn = *(uint16_t*)(stub + 4);
else
    // hooked — fall through to Halo's Gate or fail
```

**Weakness**: fails immediately if `stub[0] == 0xE9` (JMP hook) or any inline patch.

---

#### 2. Halo's Gate (2021 — Sektor7)

If the target stub is hooked (`E9` at offset 0), scan neighboring `Zw*` stubs in sorted order.
Use the neighbor's SSN ± delta to recover the hooked target's SSN.

```
Algorithm:
  1. Sort all Zw* exports by VirtualAddress (NtXxx are linearly ordered)
  2. Find index of target in sorted list
  3. For delta = 1, 2, ..., MAX_SCAN:
       check [target_va - delta*stub_size] and [target_va + delta*stub_size]
       if bytes match clean pattern [4C 8B D1 B8]: SSN = neighbor_ssn - delta (or + delta)
  4. Guard: stop if delta exceeds available export range
```

**Weakness**: fails when multiple consecutive stubs are hooked.

---

#### 3. Tartarus' Gate (2021 — trickster0)

Extension of Halo's Gate. Handles more hook styles and walks further:

```
Hook detection — check stub[0] and stub[3]:
  stub[0] == 0xE9              -> NEAR JMP (most common, CrowdStrike etc.)
  stub[0] == 0xFF, stub[1]==0x25 -> INDIRECT JMP (FF 25)
  stub[0] == 0xEB              -> SHORT JMP
  stub[0] == 0xCC              -> INT3 (breakpoint hook)
  stub[3] == 0xE9              -> inline patch after mov r10,rcx  (4C 8B D1 E9...)

If hooked, walk ±16 neighbors (instead of ±8) in both directions.
```

**Tooling**: SysWhispers4 (`--resolve tartarus`) implements this with NOP injection between
the prologue instructions to break brittle byte-scan signatures.

---

#### 4. FreshyCalls (2022)

Pure export-sort approach — never reads stub bytes at all.

```python
exports = [(va, name) for (va, name) in ntdll_exports if name.startswith("Zw")]
exports.sort(key=lambda x: x[0])           # sort by VirtualAddress
ssn = {entry.name: idx for idx, entry in enumerate(exports)}
# NtXxx SSN = ZwXxx SSN (same stub number)
```

**Hook resistance**: immune to byte-patching because no stub bytes are ever read.
**Weakness**: requires accurate export enumeration; remapping attacks can skew VA order.

---

#### 5. DWhisper / RecycleGate (ADE — AeonDave)

FreshyCalls + seeded hash at rest + random gadget scan order.

```
SSN resolution (DWhisper):
  1. Enumerate ntdll via PEB walk — GS:[0x60] -> PEB -> Ldr -> InMemoryOrderModuleList
     Zero Win32 API calls; no GetModuleHandle/GetProcAddress IOC
  2. Collect all Zw* exports; apply seeded hash to each name before storing
     All map keys are hashed — no plaintext "NtXxx" strings in memory at rest
  3. Bubble-sort by VirtualAddress; SSN = sorted index

Gadget scan (GetRecyCall):
  1. Enumerate exports again; SHUFFLE list randomly (rand.Shuffle per call)
  2. For each candidate: validate bytes at [VA+18] == 0F 05 C3 (SYSCALL;RET)
  3. Return VA+18 as the indirect syscall gadget
  -> Different export is selected as gadget each run, defeating timing fingerprinting

String obfuscation:
  mNtdll, mNt, mZw are XOR/seeded-hash encrypted constants — decrypted only at calltime
```

---

#### 6. FromDisk / SyscallsFromDisk

Map a **clean copy** of ntdll from disk or `\KnownDlls\ntdll.dll` — bypasses all in-memory hooks.

```c
// Open \KnownDlls\ntdll.dll (the clean, pre-loaded section)
RtlInitUnicodeString(&us, L"\\KnownDlls\\ntdll.dll");
NtOpenSection(&hSection, SECTION_MAP_READ|SECTION_MAP_EXECUTE, &oa);
NtMapViewOfSection(hSection, NtCurrentProcess(), &cleanBase, ...);
// Now parse export table from cleanBase for SSNs using Hell's Gate approach
```

**Detection**: two ntdll mappings visible in memory (one private, one from KnownDlls).
Mitigated by: unmapping the copy after SSN collection.

---

#### 7. SysWhispers Lineage Summary

| Version | SSN method | Invocation | Notes |
|---|---|---|---|
| SW1 | Hardcoded per-OS-build table | Direct SYSCALL | No runtime parsing; brittle across patches |
| SW2 | Export sort (FreshyCalls-style) | Direct SYSCALL | Dynamic SSN; still direct SYSCALL |
| SW3 | Export sort | Indirect JMP + random gadget | "Syswhispers is dead" blog, 2022 |
| SW4 | All methods + FromDisk + RecycledGate + HWBP | Indirect + randomized | Pluggable resolver interface |

---

## `SYSCALL;RET` Gadget Search

Scan ntdll `.text` (or each `Zw*` export stub) for the byte pattern:
```
0F 05    SYSCALL
C3       RET
```

In practice every `ZwXxx` stub in ntdll contains this at a fixed offset:
```
ZwAllocateVirtualMemory:
    4C 8B D1         mov r10, rcx
    B8 18 00 00 00   mov eax, 0x18
    0F 05            syscall        <- gadget at stub+8
    C3               ret
```

For indirect syscall from own code, set `pGadget = &ZwXxx + 8`.

---

## Windows Calling Convention (Win64 Fastcall)

| Register | Arg | Notes |
|---|---|---|
| RCX | 1 | caller-saved |
| RDX | 2 | caller-saved |
| R8  | 3 | caller-saved |
| R9  | 4 | caller-saved |
| RSP+0x28 | 5 | on stack |
| RSP+0x30 | 6 | on stack |
| RAX | return | NTSTATUS |
| RSP+0x00..0x1F | shadow space | callee scratch, must be allocated |
| RBX, RSI, RDI, RBP, R12-R15 | — | callee-saved |

---

## Linux x86-64 Syscall ABI

| Register | Role |
|---|---|
| RAX | syscall number |
| RDI | arg1 |
| RSI | arg2 |
| RDX | arg3 |
| R10 | arg4 (NOT RCX — same clobber reason as Windows) |
| R8  | arg5 |
| R9  | arg6 |
| RAX | return value; [-4095, -1] = errno negated |
| RCX, R11 | clobbered by SYSCALL (saved RIP and RFLAGS) |

Never use RCX/R11 to pass arguments — they are unconditionally clobbered.

---

## Go Plan9 ASM Notes for Syscall Stubs

Plan9 ASM used in `_x64.s` / `_amd64.s` Go files:

```
TEXT ·funcName(SB),NOSPLIT,$0-40
```
- `NOSPLIT` — no stack-growth prologue (required for raw ASM stubs to avoid frame intrusion)
- `$0-40` — 0 bytes local frame, 40 bytes argument size
- Arguments accessed via `NAME+OFFSET(FP)` (e.g., `callid+0(FP)`, `arg1+8(FP)`)
- `MOVQ` = 64-bit move, `MOVL` = 32-bit
- `BYTE $0x90` = NOP (for obfuscation padding)
- GS register: `MOVQ (TLS), CX` to access goroutine struct; `16(CX)` = m (OS thread), used by `runtime.SetLastError`

### Caveats
- Do not call Go functions from NOSPLIT stubs without careful stack accounting
- Using `CALL` inside a NOSPLIT stub requires the callee to also be NOSPLIT
- Frame size `$0-N` where N is total argument bytes including return value slot

---

## Invocation Techniques

Invocation modes are **orthogonal** to SSN resolution. Any resolver (Hell's Gate, FreshyCalls, DWhisper) can be combined with any invocation mode below.

---

### Direct Syscall

The `SYSCALL` instruction executes inside the malware's own image (`.text` section or dynamically allocated RWX stub).

```nasm
; Full stub lives in malware .text
NtAllocateVirtualMemory_stub:
    mov  r10, rcx      ; copy arg1 (Win64 fastcall)
    mov  eax, SSN      ; resolved system call number
    syscall            ; RIP here points into malware image
    ret
```

**Detection**: kernel records originating RIP in ETW event at syscall entry.
IOC: `SYSCALL` from address outside ntdll's mapped `.text` range.
Caught by ETW+call-stack inspection, CrowdStrike Falcon, MDE (as of ~2022+).

---

### Indirect Syscall

Stub sets up registers then JMPs into ntdll's own `SYSCALL;RET` gadget.
The CPU executes `SYSCALL` at an ntdll address — kernel records RIP inside ntdll.

```nasm
; Only the preamble lives in malware; SYSCALL executes in ntdll
NtAllocateVirtualMemory_stub:
    mov  r10, rcx                    ; arg1
    mov  eax, SSN                    ; system call number
    jmp  QWORD PTR [gadget_ptr]      ; -> ntdll stub+0x12 = SYSCALL;RET
```

Ntdll ZwXxx stub layout (full, including KUSER_SHARED_DATA guard):
```
+0x00  4C 8B D1        mov  r10, rcx
+0x03  B8 xx 00 00 00  mov  eax, SSN
+0x08  F6 04 25 ...    test byte ptr [7FFE0308h], 1   <- KUSER_SHARED_DATA
+0x10  75 03           jne  +0x15
+0x12  0F 05           syscall     <- indirect syscall targets here
+0x14  C3              ret
+0x15  CD 2E           int  2Eh    <- INT 2E fallback (32-bit compat)
+0x17  C3              ret
```

Gadget at `+0x12` — after the 18-byte preamble.  
`GetRecyCall()` (ADE/RecycleGate) returns a random `+0x12` gadget each call.

**Detection**: `SYSCALL` executes in ntdll, but the return address below it points into malware.
Stack-based ETW detectors flag the missing legitimate `kernelbase!/kernel32!` frames.

---

### Vectored Syscall (VEH + HWBP)

Hardware breakpoints + VEH intercept execution at the `SYSCALL` opcode inside ntdll.
No JMP instruction from malware. No inline ASM stubs. Call stack is built naturally by the ntdll call.

```
Execution flow:
1. AddVectoredExceptionHandler — register VEH handler
2. Set Dr0 = VA of SYSCALL opcode (+0x12) in target ntdll Zw* stub
   Set Dr7 bit 0 (G0/L0) = 1 to enable the breakpoint
3. Call the target ntdll function normally (function pointer or IAT)
4. EDR hook in ntdll fires first (if any), sees clean call path — may bypass
5. CPU hits Dr0 -> raises EXCEPTION_SINGLE_STEP before kernel transition
6. VEH handler fires:
   a. ContextRecord->Rax = desired SSN
   b. ContextRecord->R10 = original arg1 (saved from Rcx on entry)
   c. ContextRecord->Rip points at SYSCALL — resumes there on CONTINUE
   d. Disable Dr0 (Dr7 bit 0 = 0) to prevent re-triggering on next call
   e. return EXCEPTION_CONTINUE_EXECUTION
7. SYSCALL executes at ntdll address — RIP fully legitimate
```

**Detection surface**:
- `AddVectoredExceptionHandler` / `AddVectoredContinueHandler` API call
- Dr0–Dr3 modified in user mode (observable via ETW KernelTraceControl, PsSetContextThreadNotifyRoutine)
- Recurring `EXCEPTION_SINGLE_STEP` exceptions per syscall (behavioral pattern)

**Variants**:
- **RedOps / plain VEH**: no HWBP — generates a null-deref exception, sets EAX/R10/RIP in handler
- **LayeredSyscall (WKL 2024)**: HWBP at both `SYSCALL` (+0x12) and `RET` (+0x14) opcodes inside ntdll; constructs synthetic call stack by driving Windows APIs (kernel32, kernelbase) — no manual stack frame building
- **Hit-And-Run**: "call stack theft" — borrows an in-flight legitimate ntdll call's live stack frame; SYSCALL appears to originate from within a real Windows API call path
- **VEH Squared**: nested VEH to avoid calling `SetThreadContext` (avoids that hook surface); inner VEH sets debug registers via CONTEXT only

---

### LayeredSyscall (ADE — middleware decorator)

ADE `layeredSyscall` package wraps any `_interface.Syscall` and provides transparent per-call interception.  
This is **not** a new dispatch mechanism — it is a decorator that forwards to whatever gate is underneath.

```go
// Wrap the default RecycleGate-backed indirectSyscall with an intercept layer
ev := evasion.New(layeredSyscall.New(indirectSyscall.New()))

// Or swap in a different Callgate:
ev := evasion.New(layeredSyscall.New(indirectSyscall.NewWithGate(myGate)))

// To intercept a specific syscall, add a method with matching Syscall interface signature:
func (s *LayeredSyscall) S23( /* NtCreateThreadEx args */ ...) (uint32, error) {
    // pre-call hook: logging, argument patching, context prep
    result, err := s.Syscall.S23(...)  // delegate to inner (IndirectSyscall / RecycleGate)
    // post-call hook: error inspection, cleanup, telemetry
    return result, err
}
// All Sxx methods NOT defined here pass through to inner unchanged.
```

Full stack:
```
Evasion (high-level API, spoof context)
  -> LayeredSyscall (per-call intercept; transparent passthrough)
    -> IndirectSyscall (typed wrappers S1..S43; owns Callgate)
      -> Callgate / RecycleGate (SSN resolver + gadget dispatch)
        -> ntdll SYSCALL gadget (executed at ntdll+0x12)
```

`Callgate` interface (`_interface.Callgate`):
- `Resolve(apiHash) -> (ssn, gadgetAddr, err)` — SSN + ntdll gadget pointer
- `Execute(ssn, gadgetAddr, args...)` — dispatch through gate's trampoline
- `SetCtx(uintptr)` / `HasCtx() bool` / `GetCtx() uintptr` — spoof context lifecycle
