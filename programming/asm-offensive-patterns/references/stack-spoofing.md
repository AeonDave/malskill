# Call-Stack Spoofing — Draugr, SilentMoonwalk, Eclipse, LayeredSyscall

## Why Call-Stack Spoofing Matters

When an EDR intercepts a syscall (via kernel callback, APC scan, or periodic stack walk):
- It calls `RtlCaptureStackBackTrace` / `RtlVirtualUnwind` on the thread stack
- Expects to see: `ntdll!ZwXxx -> KernelBase!... -> BaseThreadInitThunk -> RtlUserThreadStart`
- Any RX page outside known modules is immediate IOC

Goal: Make the unwinder traverse a synthesized frame chain that looks like a legitimate call path.

---

## Windows Stack Walk Mechanics

Stack unwinding on x64 uses **RUNTIME_FUNCTION** entries in the `.pdata` section.
Each entry maps a range of code to an UNWIND_INFO structure describing:
- Register saves (PUSH_NONVOL)
- Stack allocation (ALLOC_LARGE / ALLOC_SMALL)
- Frame pointer register (SET_FPREG)
- Exception handlers / chained unwind

`RtlVirtualUnwind` reads these to step from frame to frame.
**Key insight**: the unwinder reads metadata from the address of the return addresses on the stack — not from actual register state.

---

## 1. Draugr-Style Spoofing

### Concept
Switch RSP to a heap buffer, build synthetic frames bottom-up (thread-bottom -> ... -> trampoline),
execute the syscall, then restore RSP.

### SpoofContext Structure
```c
typedef struct {
    uintptr_t JmpRbxGadget;           // JMP [RBX] in KernelBase (trampoline)
    uintptr_t BaseThreadInitThunkRet;  // call-followed offset in BaseThreadInitThunk
    uintptr_t RtlUserThreadStartRet;   // call-followed offset in RtlUserThreadStart
    uintptr_t Frame1Size;              // BaseThreadInitThunk frame allocation size
    uintptr_t Frame2Size;              // RtlUserThreadStart frame allocation size
    uintptr_t TrampolineSize;          // JMP [RBX] frame size (>= 0x80 for stack args)
} SpoofContext;
```

### Stack Layout Built on Heap Buffer (bottom-up)

```
[bufBase]                     <- bottom of heap buffer
...
[bufBase + N]   = 0          <- sentinel (thread bottom)
                - Frame2Size
[             ] = RtlUserThreadStartRet
                - Frame1Size
[             ] = BaseThreadInitThunkRet
                - TrampolineSize
[             ] = JmpRbxGadget   <- RSP when CALL R15 fires
[             + 8..] = syscall args
```

### Assembly Sketch (Plan9)
```
PUSHQ R12           ; save real RSP
MOVQ  SP, R12
MOVQ  bufTop(CTX), SP          ; switch to heap buffer top
PUSHQ $0                       ; sentinel
SUBQ  Frame2Size(CTX), SP
MOVQ  RtlUserThreadStartRet(CTX), 0(SP)
SUBQ  Frame1Size(CTX), SP
MOVQ  BaseThreadInitThunkRet(CTX), 0(SP)
SUBQ  TrampolineSize(CTX), SP
MOVQ  JmpRbxGadget(CTX), 0(SP)
; copy args to [SP+8..], set RBX = fixup addr
CALL  R15                      ; R15 = syscall;ret gadget
; on return: RBX gadget -> fixup -> restores R12 -> RSP
```

### Finding Return Addresses
Scan `KernelBase!BaseThreadInitThunk` for a CALL offset (byte 0xFF or 0xE8 followed by the target).
The return address must point to the instruction *after* the CALL.

---

## 2. SilentMoonwalk DESYNC Technique

### Concept
Diverge the **unwinder's metadata path** from the **execution path**.
The CPU executes one code flow; the unwinder sees a different one.

### DESYNC Mechanism
```
Execution path:
  our_code -> CALL R15 (syscall;ret) -> returns to AddRspX;RET gadget
              -> JMP [RBX] -> fixup

Unwind path (what .pdata metadata describes):
  AddRspX frame -> JmpRbx frame (PUSH_NONVOL RBP) -> SecondFrame (SET_FPREG) -> FirstFrame
```

The `AddRspX;RET` gadget appears to the unwinder as if it were called from `JmpRbx`,
because it was placed where the unwinder's `RtlVirtualUnwind` expects `NextRetAddr`.

### DesyncContext Structure
```c
typedef struct {
    uintptr_t AddRspXGadget;          // ADD RSP, X; RET in ntdll or KernelBase
    uintptr_t AddRspXValue;           // X value (byte offset to skip ROP zone)
    uintptr_t JmpRbxGadget;           // JMP [RBX] — Eclipse-validated, call-preceded
    uintptr_t FirstFrameRetAddr;      // SET_FPREG function + call-offset (Frame1)
    uintptr_t SecondFrameRetAddr;     // PUSH_NONVOL RBP function + call-offset (Frame2)
    uintptr_t FirstFrameSize;
    uintptr_t SecondFrameSize;
    uintptr_t JmpRbxFrameSize;
    uintptr_t RbpPlantOffset;         // where to write RBP into the fake JmpRbx frame
} DesyncContext;
```

### Stack Layout

```
[RSP+0]         = AddRspXGadget (return for syscall;ret)
[RSP+AddRspXValue] ...skipped by AddRspX...
[RSP+X]         = JmpRbxGadget (Eclipse-validated, return for AddRspX;RET)
[RSP+X+8..  ]   = fake JmpRbx frame (PUSH_NONVOL RBP metadata)
   RBP planted at RbpPlantOffset within this frame
[+JmpRbxFrameSize] = SecondFrameRetAddr
[+SecondFrameSize] = FirstFrameRetAddr
[+FirstFrameSize]  = 0 (thread bottom)
```

---

## 3. Eclipse Bypass

### What Eclipse Checks
Eclipse walks the fake stack and verifies that each return address is **preceded by a CALL instruction**:
```
*(ret_addr - 5) == 0xE8   (CALL rel32)
*(ret_addr - 2) == 0xFF   (CALL r/m16|32|64 — indirect)
```
If a return address lacks a CALL instruction before it, Eclipse flags it as spoofed.

### Defense
- All gadget addresses used as return addresses must be **call-preceded** in their source module
- Source gadgets from modules Eclipse typically doesn't harden: `wininet.dll`, `user32.dll`
- Cascade: `wininet` return -> `user32` return -> `kernelbase` return -> `kernelbase` return

---

## 4. LayeredSyscall — Live VEH Frame Overwrite

### Concept
No pre-built heap frame — instead, intercept the thread at the exact moment it enters `NtXxx`
and overwrite the real call frames on the thread's existing stack.

### Steps
```
1. Set Dr0 = &ntdll!NtTargetFunction
2. Configure Dr7: bit0=1 (local enable), bits 16-17 = 00 (execute breakpoint)
3. Register VEH via AddVectoredExceptionHandler
4. Call NtXxx through any normal call chain
5. EXCEPTION_SINGLE_STEP fires:
   a. Locate RSP of the breaked frame
   b. Overwrite saved return addresses at RSP+8, RSP+16 with spoofed chain
   c. NtContinue(ctx)
6. Syscall executes with spoofed frames; unwinder sees clean chain
```

### Advantages over Draugr/DESYNC
- No dependency on correct frame-size calculation
- Works with any call chain — no pre-switch to heap buffer
- Survives CFG checks on the calling path

### Disadvantages
- VEH is visible in the vectored handler list (IOC)
- Dr7 modification visible via `GetThreadContext`
- Single-threaded; concurrent syscalls on same thread need careful Dr7 management

---

## 5. Call-Gadget Stack Insertion (2024–2025)

### Concept

Instead of building fully synthetic frames, insert a single legitimate module into the
call stack by exploiting a controllable `CALL [reg]` gadget inside a system DLL.
This breaks EDR signature rules that match specific module sequences.

### How It Works

```
1. Identify a CALL [reg] gadget inside a rarely-monitored DLL
   (e.g. dsdmo.dll, dbghelp.dll, mshtml.dll)
   Gadget: CALL [RBX] or CALL [RDI] followed by code that returns normally

2. Trigger module loading (LoadLibrary/LdrLoadDll) that internally
   routes through the gadget DLL during initialization
   
3. The gadget's module appears in the resulting call stack between
   the network module (ws2_32/winhttp/wininet) and the caller

4. EDR sees: gadget_module -> wininet -> kernelbase -> ...
   instead of: unbacked_memory -> wininet -> kernelbase -> ...
   Signature mismatch -> no alert
```

### Defeating Elastic EDR Specifically

Elastic's call-stack detection rules look for:
```
process.thread.Ext.call_stack_summary:"unbacked|ntdll.dll|..."
```

By inserting a signed module (via call gadget), the pattern changes to:
```
process.thread.Ext.call_stack_summary:"dsdmo.dll|ntdll.dll|..."
```

The rule no longer matches because `dsdmo.dll` is a legitimate Microsoft-signed module.

### Advantages
- No heap buffer, no frame-size calculation, no RSP switching
- Works alongside indirect syscalls and existing call chains
- Minimal code change: trigger one extra LoadLibrary before the sensitive operation

### Limitations
- Gadget DLL must be present on the target system (Windows version dependent)
- EDR vendor may add the gadget DLL to their signature pattern
- Only helps with call-stack signature rules; does not help with content-based detection

---

## 6. CET-Aware Stack Spoofing Considerations

Intel CET shadow stack validates return addresses at every `RET`.
Implications for stack spoofing techniques:

### What breaks under CET
- Draugr/DESYNC: Synthetic frames on heap buffer contain return addresses that were never
  pushed by a matching `CALL` → shadow stack mismatch → `STATUS_STACK_BUFFER_OVERRUN`
- Return-address overwrites: `RET` compares main stack vs shadow stack → fault

### What survives CET
- **LayeredSyscall (VEH+HWBP)**: Exception dispatch resets the CET context;
  `NtContinue` properly updates the shadow stack
- **NtContinue-based chains** (Ekko/Cronos sleep): `NtContinue` is CET-aware —
  it restores shadow stack state from the saved CONTEXT
- **Call-gadget insertion**: No return address modification; legitimate `CALL` pushes
  to both stacks normally
- **JMP-based indirect syscalls**: `JMP [gadget]` does not push to shadow stack;
  the subsequent `SYSCALL;RET` in ntdll matches ntdll's own `CALL` pair

### Practical recommendation
On CET-enabled targets, prefer VEH+HWBP (LayeredSyscall) or call-gadget insertion
over Draugr/DESYNC. For sleep obfuscation, use `NtContinue`-based techniques (Ekko).
