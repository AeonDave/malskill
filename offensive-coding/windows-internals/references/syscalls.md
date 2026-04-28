# Syscalls Reference

Complete coverage of Windows syscall mechanics: ABI, SSN resolution strategies (Hell's / Halo's / Tartarus / Recycled / HWSyscall), direct vs indirect dispatch, stub layout, multi-arg variants, and WoW64 considerations.

---

## Syscall ABI — x86-64

### The three states of a syscall

```
[User mode]                    [Transition]                 [Kernel mode]
ntdll!Nt*Stub                  syscall instruction          KiSystemCall64
───────────────                ───────────────              ──────────────
mov r10, rcx      \                                         pushes CS, SS
mov eax, <SSN>     \            SSN in eax                  pops PFN, swaps CR3 (KPTI)
test byte ...       >─────────> r10 = arg0                  indexes SSDT[eax]
jnz syscall_path   /            RCX will be clobbered       invokes Nt<Handler>
syscall           /             with return address
ret
```

### Register conventions at the `syscall` boundary

**User → Kernel**:
- `rax` = System Service Number (SSN) — dense index 0..N into `nt!KiServiceTable`
- `r10` = arg 1 (was rcx in user convention; kernel reads r10 because syscall clobbers rcx)
- `rdx` = arg 2
- `r8`  = arg 3
- `r9`  = arg 4
- Args 5+ on stack, at `[rsp + 0x28]` onwards (after 32-byte shadow space + 8-byte return addr slot)
- `r11` = saved RFLAGS (syscall instruction semantics)

**Kernel → User return**:
- `rax` = NTSTATUS
- All other registers preserved per Win64 calling convention (except possibly `r11`, which `sysret` restores)

### Minimal syscall stub (what ntdll!NtAllocateVirtualMemory looks like)

```asm
; Windows 10 1809+ default stub layout (non-hooked)
; Example: NtAllocateVirtualMemory on Windows 11 24H2 (SSN drifts; illustrative)
NtAllocateVirtualMemory:
    mov     r10, rcx              ; 4C 8B D1
    mov     eax, 0x18             ; B8 18 00 00 00        ← SSN is here, at offset 4
    test    byte ptr [0x7FFE0308], 1  ; 67 F6 04 25 08 03 FE 7F 01
    jne     short do_wow64_path    ; 75 03
    syscall                        ; 0F 05
    ret                            ; C3
do_wow64_path:
    int     0x2E                   ; CD 2E    (legacy path)
    ret                            ; C3
```

**The SSN is always the 32-bit immediate at byte offset 4** of the stub (for a non-hooked ntdll on supported Windows builds). This is the Hell's Gate invariant.

---

## ARM64 syscall ABI

```
[User mode ARM64]                      [Transition]
ntdll!Nt*Stub                          svc instruction
─────────────────                      ─────────────────
mov     x8, <SSN>                      x8 holds SSN
svc     #0                              enters EL1
ret
```

- `x8` = SSN
- `x0`–`x7` = args 1–8
- Return in `x0`
- `svc #0` instruction traps to EL1; kernel dispatches via arm64 service table

No `mov r10, rcx`-equivalent trick is needed — ARM64 calling convention already puts args in x0..x7. No `wow64` check gate (ARM64EC has its own emulation bridge).

---

## SSN resolution strategies

The SSN is not stable across Windows builds. Patch Tuesday routinely shuffles them. Every modern implant resolves at runtime.

> **See also**: the dedicated [`indirect-syscall`](../../indirect-syscall/SKILL.md) skill covers the **implementation** side of each strategy (complete C/Rust/Go trampolines, SSN-table init with obfuscated hashes, gadget caching, 6+ arg variants). This section is the **reference** for how each strategy works; go to `indirect-syscall` when actually writing dispatcher code.

### Strategy 1 — Hell's Gate

**Assumption**: the stub you find in ntdll is **not hooked**.

Procedure:
1. PEB walk → locate ntdll.dll base
2. Export walk (or hash-indexed lookup) → address of target Nt* function
3. Read `stub[4]` as `uint32_t` → SSN

```c
typedef NTSTATUS (*pfn_t)(...);
uint8_t* stub = (uint8_t*)resolve_export("ntdll.dll", hash_NtAllocateVirtualMemory);

// Hell's Gate check: "mov eax, imm32" starts with 0xB8
if (stub[0] == 0x4C && stub[1] == 0x8B && stub[2] == 0xD1 &&  // mov r10, rcx
    stub[3] == 0xB8) {                                         // mov eax, imm32
    uint32_t ssn = *(uint32_t*)(stub + 4);
    return ssn;
}
// Stub is hooked — fall back to Halo's / Tartarus / Recycled
```

### Strategy 2 — Halo's Gate

**Fallback** when the stub starts with `jmp` or `call` (EDR hook). Walk neighboring stubs ±N and reconstruct SSN by arithmetic.

Invariant: SSNs are **assigned by sorted RVA order** of the Zw* exports. `NtAllocateVirtualMemory` and its neighbors differ by exactly 1 in SSN. So if your target is hooked but its neighbor 0x20 bytes away (next stub) is clean, read the neighbor's SSN and subtract/add 1.

Procedure:
1. If `stub[0] == 0xE9` (JMP) or `stub[0] == 0xE8` (CALL) → hooked
2. Walk forward: `stub + 0x20` is the next function (stubs are uniform length in unhooked ntdll). Check if its Hell's Gate byte pattern is clean. If yes → `ssn = neighbor_ssn - 1`.
3. Walk backward: `stub - 0x20`. If clean → `ssn = neighbor_ssn + 1`.
4. Continue ±N steps until a clean stub found.

### Strategy 3 — Tartarus Gate

Extends Halo's to handle EDRs that hook **deeper** in the stub (e.g., overwriting byte 3 with 0xE9 jmp after the `mov r10, rcx` bytes remain intact). Detects hook by checking byte at various offsets, not just offset 0.

### Strategy 4 — Recycled Gate (DWhisper / recycled)

**Does not read SSNs from stubs at all**. Instead:

1. Walk ntdll export table, filter all `Zw*` exports (mirror of `Nt*` in userland).
2. Collect `(name, RVA)` tuples.
3. Sort by RVA ascending.
4. The index in the sorted array **is** the SSN.

```
Zw exports sorted by RVA:
 [0] ZwAcceptConnectPort        RVA 0x0001A000 → SSN 0
 [1] ZwAccessCheck              RVA 0x0001A020 → SSN 1
 [2] ZwAccessCheckAndAuditAlarm RVA 0x0001A040 → SSN 2
 ...
 [88] ZwAllocateVirtualMemory   RVA 0x0001B100 → SSN 88 (0x18)
 ...
```

This works because the kernel's SSDT (`nt!KiServiceTable`) is populated in the same order the `Zw*` exports are laid out at ntdll link time. The ordering is a link-layout artifact, **not** a guaranteed alphabetical sort — it happens to correlate with alphabetical order of internal names on most builds, but the invariant you rely on is *sorted-by-RVA matches SSN*, not *alphabetical-by-name matches SSN*.

**Advantage**: completely immune to stub hooks. Never reads stub bytes. The name→SSN table can be built once at process init.

**Tradeoff**: no single-function resolution; must enumerate all Zw exports.

### Strategy 5 — HWSyscall / hardware breakpoints

Use hardware debug registers (DR0–DR3) to set an execution breakpoint on the `syscall` instruction inside the legitimate ntdll stub. Call the Nt function normally; when execution hits the breakpoint, your VEH handler:
1. Reads current SSN from RAX (`ExceptionRecord->ContextRecord->Rax`)
2. Modifies context to jump past hooks
3. Optionally modifies any register / returns alternative SSN
4. Resumes

Advantage: the syscall actually executes from ntdll — call stack looks native. EDRs that only hook prologue bytes are bypassed; they never see the modified behavior.

Drawback: DR0–DR3 are **per-thread**, visible in `NtGetContextThread`, and ETW-TI fires on DR modifications starting in recent Windows 11 builds.

---

## Direct vs Indirect syscall dispatch

Once you have the SSN, how do you actually execute the syscall?

### Direct syscall

Emit the `syscall` instruction in **your own code section**.

```asm
; Your module's .text section
MyDirectSyscall:
    mov     r10, rcx           ; Windows kernel expects r10
    mov     eax, <SSN>         ; filled in at runtime or compile time
    syscall
    ret
```

Call stack at the moment of the syscall:
```
Return address → your_module.text+XXX
RIP           → your_module.text+YYY (the `syscall` instruction)
```

**Detection signal**: the `syscall` instruction executes from a non-ntdll module. `call stack` examination (at `KiSystemCall64` or via ETW-TI call-stack capture) shows a userland frame outside ntdll. This is a high-fidelity IOC.

### Indirect syscall

Find a `syscall; ret` byte sequence (`0F 05 C3`) inside ntdll and `call` it, passing the SSN in `rax`.

```asm
; SSN in eax, r11 = address of `0F 05 C3` gadget inside ntdll
MyIndirectSyscall:
    mov     r10, rcx
    mov     eax, <SSN>
    call    r11                ; call the gadget directly (do NOT deref)
    ret
```

Where is `0F 05 C3`? Inside every unhooked `Nt*` stub, at **offset `0x12` (18 decimal)** from the stub start — after `mov r10, rcx` (3) + `mov eax, imm32` (5) + `test byte [0x7FFE0308], 1` (8) + `jne short` (2) = 18 bytes of prologue. In a non-hooked ntdll every Nt stub ends with these three bytes; pick any one that validates (stub may be hooked → pattern at +0x12 no longer matches, try next export).

Call stack at the moment of the syscall (stub-relative offsets):
```
Return address in RCX (clobbered by syscall) → ntdll!Nt*Stub + 0x14  (the ret after syscall)
RIP at trap                                  → ntdll!Nt*Stub + 0x12  (the syscall instruction)
```

**Detection signal reduced**: stack now looks like a legitimate ntdll syscall — but a careful examiner sees the return address below that points into your module's code. ETW-TI kernel-side call stack still captures this.

### Desync / spoofed-stack syscall

See `references/exception-unwind.md` §Call-stack Spoofing. Summary:

1. Resolve gadgets: `jmp [rbx]`, `add rsp, X; ret`, a function with `UWOP_SET_FPREG` (terminator frame), a function with `UWOP_PUSH_NONVOL(rbp)` (second frame), a syscall;ret gadget
2. Compute each function's frame size from UNWIND_INFO
3. Build ROP chain on real RSP that satisfies the unwinder: frame sizes match, return addresses point into real library `.text`
4. `jmp` into the chain

Call stack captured during syscall:
```
ntdll!Nt*Stub + 0x0E
legit_function_A + offset    ← terminator frame (SET_FPREG)
legit_function_B + offset    ← push_nonvol(rbp) frame
legit_function_C + offset    ← optionally more chain frames
ntdll!RtlUserThreadStart     ← original thread start
```

The unwinder validates each frame's PC against `.pdata` and walks happily. The scanner cannot tell this is fake without deep instrumentation.

---

## Finding syscall;ret gadgets

### Simple scan (Recycled Gate approach)

```c
uint8_t* ntdll = get_ntdll_base();
size_t   size  = get_image_size(ntdll);

for (size_t i = 0; i + 3 < size; i++) {
    if (ntdll[i]   == 0x0F &&
        ntdll[i+1] == 0x05 &&
        ntdll[i+2] == 0xC3) {
        return ntdll + i;  // first match works for most Nt* stubs
    }
}
```

### Export-bound scan (more precise)

The syscall;ret sequence exists inside the body of every `Nt*` export, at `stub_addr + 18`. Enumerate exports, add 18 to each Zw address, confirm bytes. Validates you are inside a legitimate function body, not a random byte match.

### Hook-aware scan

If EDR hooks overwrite byte 4 (the SSN) but not the tail (syscall;ret at offset 18), your gadget still works — you resolve the SSN via Recycled Gate (from clean export order) and use the hooked stub's own syscall;ret as the gadget. The EDR's JMP hook is bypassed entirely because you never execute the hooked bytes.

---

## Multi-argument syscalls

Nt* functions with 5+ arguments pass the extras on stack. ABI:
- Args 1–4: rcx, rdx, r8, r9
- Arg 5: `[rsp + 0x28]`
- Arg 6: `[rsp + 0x30]`
- etc.

Shadow space (32 bytes from rsp+0x00 to rsp+0x20) is reserved but **not** populated — kernel writes scratch there. Slot at `[rsp + 0x20]` is the return address slot.

### Example: NtCreateThreadEx (11 arguments)

```asm
NtCreateThreadEx_stub:
    ; Args 1-4 already in rcx, rdx, r8, r9 from caller
    ; Caller has allocated stack for args 5-11 at [rsp+0x28..0x58]
    mov     r10, rcx
    mov     eax, <SSN_NtCreateThreadEx>
    syscall
    ret
```

Caller side (in Rust/C/Go), allocate stack for 11 args as if calling any other function:

```c
// Pseudo-C
NTSTATUS s = (*NtCreateThreadEx_wrap)(
    &hThread,           // arg 1  → rcx
    THREAD_ALL_ACCESS,  // arg 2  → rdx
    NULL,               // arg 3  → r8
    hProcess,           // arg 4  → r9
    start,              // arg 5  → [rsp+0x28]
    parameter,          // arg 6  → [rsp+0x30]
    0,                  // arg 7
    0,                  // arg 8  (stack zero bits)
    0,                  // arg 9  (stack commit)
    0,                  // arg 10 (stack reserve)
    NULL                // arg 11 (attribute list)
);
```

The wrap function is a thin ASM stub that moves r10 and jumps into the syscall. Each syscall with a different arity needs its own wrap (or one variadic wrap with a max arg count).

---

## WoW64 considerations

A 32-bit (WoW64) process runs under a 64-bit kernel. The direct `syscall` instruction from 32-bit code does **not** reach the 64-bit kernel — it would be interpreted as legacy 32-bit `sysenter` semantics.

The WoW64 process transitions to 64-bit mode via `wow64cpu!CpupReturnFromSimulatedCode`, which switches CS segment, performs the syscall, then switches back.

**Offensive technique — Heaven's Gate**: manually perform the CS switch with a far jmp / retf to code segment 0x33, execute 64-bit code, return via far jmp back to 0x23. Allows 32-bit malware to issue 64-bit syscalls directly.

```asm
; x86 code, inside a WoW64 process
push    0x33                  ; 64-bit code segment selector
push    offset sixty_four_land
retf                           ; far return → enters 64-bit mode

sixty_four_land:
    ; Now running as 64-bit code, can use RCX, RDX, etc.
    ; Can execute syscall directly
    db 0x48                    ; REX.W prefix for mov rax
    mov eax, <SSN>
    syscall
    ; Return to 32-bit
    db 0x48
    db 0xCB                    ; far ret with REX.W
```

This is an old technique, heavily signatured. Modern sandboxes / EDRs detect the CS=0x33 transition.

---

## ETW-TI syscall surveillance

Kernel-mode ETW-TI ("Microsoft-Windows-Threat-Intelligence" provider) emits events for specific syscalls regardless of how they are invoked:

| Event | Triggering syscall |
|---|---|
| `EtwTiLogAllocExecVm` | `NtAllocateVirtualMemory` with `PAGE_EXECUTE_*` protection |
| `EtwTiLogProtectExecVm` | `NtProtectVirtualMemory` transitioning to `PAGE_EXECUTE_*` |
| `EtwTiLogMapExecView` | `NtMapViewOfSection` with `PAGE_EXECUTE_*` |
| `EtwTiLogWriteVm` | `NtWriteVirtualMemory` cross-process |
| `EtwTiLogReadWriteVm` | `NtReadVirtualMemory` targeting LSASS (or any PP) |
| `EtwTiLogSuspendResume` | `NtSuspendThread` / `NtResumeThread` cross-process |
| `EtwTiLogContextModification` | `NtSetContextThread` cross-process |
| `EtwTiLogQueueApcThread` | `NtQueueApcThread*` |
| `EtwTiLogSetSecurityDescriptor` | various |

**Key point**: ETW-TI fires from the syscall handler in the kernel, **after** your userland indirect/desync dispatch has reached the kernel. Bypass requires either kernel code (patching `nt!EtwTiLog*` functions) or using syscalls that don't trigger ETW-TI at all.

Patching `EtwTiLog*` functions in kernel memory requires kernel execution (BYOVD, signed driver, or elevation). `PPROVIDER_ENABLE_INFO` field inside `ETW_REG_ENTRY` / `ETW_GUID_ENTRY` can be overwritten via kernel WRITE primitive to disable the provider for your process.

Reading values of `ETW_TI_PROVIDER_ENABLE_INFO` and matching with `nt!EtwThreatIntProvRegHandle` (exported? no — needs symbol / pattern search) → project EDRSandblast demonstrates this.

---

## Common Nt* syscalls reference (by functional area)

### Memory
- `NtAllocateVirtualMemory`, `NtFreeVirtualMemory`, `NtProtectVirtualMemory`
- `NtWriteVirtualMemory`, `NtReadVirtualMemory`, `NtQueryVirtualMemory`
- `NtAllocateVirtualMemoryEx` (Win10 1803+): supports memory-placement specifier

### Process / thread
- `NtCreateUserProcess` (modern process creation), `NtCreateProcessEx` (legacy)
- `NtOpenProcess`, `NtTerminateProcess`, `NtQueryInformationProcess`
- `NtCreateThreadEx`, `NtOpenThread`, `NtSuspendThread`, `NtResumeThread`, `NtTerminateThread`
- `NtGetContextThread`, `NtSetContextThread`
- `NtQueueApcThread`, `NtQueueApcThreadEx`, `NtQueueApcThreadEx2`

### Sections / mapping
- `NtCreateSection`, `NtOpenSection`, `NtMapViewOfSection`, `NtMapViewOfSectionEx`, `NtUnmapViewOfSection`

### File / registry
- `NtCreateFile`, `NtOpenFile`, `NtReadFile`, `NtWriteFile`
- `NtOpenKey`, `NtQueryValueKey`, `NtSetValueKey`, `NtEnumerateKey`, `NtEnumerateValueKey`

### Token / security
- `NtOpenProcessToken`, `NtOpenThreadToken`, `NtDuplicateToken`, `NtSetInformationThread`
- `NtQueryInformationToken`, `NtAdjustPrivilegesToken`

### System information
- `NtQuerySystemInformation` (SystemProcessInformation → enumerate all processes/threads)
- `NtQueryInformationProcess` (ProcessBasicInformation, ProcessImageFileName, etc.)

### Synchronization / waiting
- `NtWaitForSingleObject`, `NtWaitForMultipleObjects`, `NtDelayExecution`
- `NtCreateEvent`, `NtCreateMutant`, `NtCreateSemaphore`

Full catalog at [ntdoc.m417z.com](https://ntdoc.m417z.com).

---

## SSN stability table (x64 Windows 11, illustrative)

SSNs drift — these are examples for orientation only. Always resolve at runtime.

| Function | 22H2 | 24H2 |
|---|---|---|
| NtAllocateVirtualMemory | 0x18 | 0x18 |
| NtWriteVirtualMemory | 0x3A | 0x3A |
| NtProtectVirtualMemory | 0x50 | 0x50 |
| NtCreateThreadEx | 0xC9 | 0xC7 |
| NtQueueApcThread | 0x45 | 0x45 |
| NtDelayExecution | 0x34 | 0x34 |

The lesson: commonly-used SSNs tend to be stable across several consecutive builds because the alphabetical ordering of kernel functions is stable, but any insertion of a new Nt function alphabetically before yours shifts it by 1. Resolve at runtime.

---

## Detection checklist for syscall dispatch

What a blue team looks for, mapped to what to avoid:

| Indicator | What it catches |
|---|---|
| `syscall` instruction outside ntdll (ETW-TI call stack) | Direct syscall |
| Return address below syscall;ret points to non-loaded-module memory | Indirect syscall from freshly allocated RX page |
| DR0–DR3 set in thread context | HWSyscall / hardware breakpoint use |
| Unbacked memory executing (VAD has no section backing) | Any shellcode |
| Image load notification fires for unsigned module | Reflective loader mapping a new module |
| `NtReadVirtualMemory(LSASS handle)` (ETW-TI) | Credential dumping regardless of indirect/direct |
| Thread entry point inside unbacked memory | Thread creation into shellcode |
| PPID ≠ actual parent (kernel tracks ParentPid in EPROCESS) | PPID spoofing via attribute list |
