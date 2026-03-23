---
name: asm-patterns
description: "Assembly language patterns, calling conventions, and code structure for x86-64 and ARM64. Use when writing, reviewing, or generating .asm/.s/.S files; when implementing functions that interoperate with C/system code; or when establishing correct prologues, epilogues, stack management, SIMD loops, syscall stubs, or PIC data access."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
compatibility: "NASM >= 2.15 or GAS (binutils). Targets: x86-64 Linux/macOS (System V) and Windows (Win64), ARM64 Linux/macOS (AAPCS)."
---

# Assembly Patterns

Canonical patterns and guardrails for x86-64 and ARM64 assembly.
Apply to all `.asm`, `.s`, `.S` files and any assembly embedded in C/Rust/Go.

---

## Architecture Selection

Declare the target at the top of every file:

```nasm
; x86-64, NASM, Linux/macOS
; Target: x86-64 System V ABI
; Syntax: Intel (NASM)
```

- **x86-64** — Linux/macOS servers, desktops, WSL
- **ARM64** — Apple Silicon, mobile, embedded Linux
- Never mix architecture paths without `%ifdef` / `.ifdef` guards

---

## Calling Conventions

### x86-64 System V ABI (Linux, macOS, BSD)

| Role | Registers |
|---|---|
| Integer args (1–6) | `rdi`, `rsi`, `rdx`, `rcx`, `r8`, `r9` |
| Float args (1–8) | `xmm0`–`xmm7` |
| Return (int) | `rax` |
| Return (float) | `xmm0` |
| Caller-saved | `rax`, `rcx`, `rdx`, `rsi`, `rdi`, `r8`–`r11` |
| Callee-saved | `rbx`, `rbp`, `r12`–`r15` |
| Stack alignment | 16-byte aligned **before** `call` |

### x86-64 Win64 ABI (Windows, UEFI)

| Role | Registers |
|---|---|
| Integer args (1–4) | `rcx`, `rdx`, `r8`, `r9` |
| Float args (1–4) | `xmm0`–`xmm3` |
| Return (int) | `rax` |
| Return (float) | `xmm0` |
| Caller-saved (volatile) | `rax`, `rcx`, `rdx`, `r8`–`r11`, `xmm0`–`xmm5` |
| Callee-saved (nonvolatile) | `rbx`, `rbp`, `rdi`, `rsi`, `r12`–`r15`, `xmm6`–`xmm15` |
| Stack alignment | 16-byte aligned **before** `call` |
| Shadow space | 32 bytes reserved by caller above return address — **always**, even for 0-arg functions |

**Key differences from System V**:
- Only 4 register args (not 6); args 5+ go on stack **above** shadow space
- `rdi`, `rsi` are callee-saved (volatile on System V)
- `xmm6`–`xmm15` are callee-saved (all volatile on System V)
- Shadow space (home area): 32 bytes at `[rsp+8]`–`[rsp+0x28]` after `call`; callee may use to spill register args
- Exception handling via `RUNTIME_FUNCTION` + unwind codes (not DWARF)

### ARM64 AAPCS (Linux, macOS)

| Role | Registers |
|---|---|
| Integer args (1–8) | `x0`–`x7` |
| Float args (1–8) | `d0`–`d7` |
| Return (int) | `x0` |
| Return (float) | `d0` |
| Callee-saved | `x19`–`x28`, `x29` (FP) |
| Stack alignment | 16-byte aligned at all times |

**Key rule**: in non-leaf functions, save `x29` + `x30` together with `stp` at entry; restore with `ldp` before `ret`.

See [references/x86-64.md](references/x86-64.md) for full register table, sub-register views, and ABI edge cases.

---

## Core Patterns

### x86-64 System V — Non-leaf function

```nasm
; int64_t compute(int64_t x, int64_t y)
; Args: rdi=x, rsi=y   Returns: rax
global compute
compute:
    push    rbp
    mov     rbp, rsp
    push    rbx                 ; callee-saved used below
    sub     rsp, 8              ; keep stack 16-byte aligned

    mov     rbx, rdi            ; save x across call
    call    some_helper         ; rdi..r11 may be clobbered

    imul    rax, rbx            ; result * saved x
    imul    rax, rsi            ; * y

    add     rsp, 8
    pop     rbx
    pop     rbp
    ret
```

### x86-64 System V — Leaf function (red zone)

```nasm
; int64_t add3(int64_t a, int64_t b, int64_t c)
; Args: rdi=a, rsi=b, rdx=c   Returns: rax
global add3
add3:
    lea     rax, [rdi + rsi]    ; rax = a + b
    add     rax, rdx            ; rax += c
    ret
```

### x86-64 Win64 — Non-leaf function with shadow space

```nasm
; int64_t compute(int64_t x, int64_t y)
; Args: rcx=x, rdx=y   Returns: rax
global compute
compute:
    push    rbx
    sub     rsp, 32             ; shadow space (always 32 bytes)

    mov     rbx, rcx            ; save x across call (rbx callee-saved)
    call    some_helper         ; rcx, rdx, r8-r11 clobbered

    imul    rax, rbx

    add     rsp, 32
    pop     rbx
    ret
```

**Win64 >4 args pattern**:
```nasm
; call func(rcx, rdx, r8, r9, arg5)
mov     rcx, val1
mov     rdx, val2
mov     r8,  val3
mov     r9,  val4
mov     qword [rsp+32], val5   ; arg5 above shadow space
sub     rsp, 40                ; 32 shadow + 8 for arg5 (aligned)
call    func
add     rsp, 40
```

### ARM64 — Non-leaf function

```asm
// int64_t compute(int64_t x, int64_t y)
// x0=x, x1=y  →  x0=result
    .global compute
compute:
    stp     x29, x30, [sp, #-32]!   // save fp+lr, alloc frame
    mov     x29, sp
    stp     x19, x20, [sp, #16]     // save callee-saved

    mov     x19, x0                  // save x across call
    bl      some_helper

    mul     x0, x0, x19             // result * saved x
    mul     x0, x0, x1              // * y

    ldp     x19, x20, [sp, #16]
    ldp     x29, x30, [sp], #32
    ret
```

### SIMD — SSE2 float loop (x86-64)

```nasm
; void vadd_f32(float *dst, const float *a, const float *b, size_t n)
; n must be a multiple of 4; dst/a/b may be unaligned
global vadd_f32
vadd_f32:
    test    rcx, rcx
    jz      .done
    shr     rcx, 2              ; n /= 4
.loop:
    movups  xmm0, [rsi]
    addps   xmm0, [rdx]
    movups  [rdi], xmm0
    add     rsi, 16
    add     rdx, 16
    add     rdi, 16
    dec     rcx
    jnz     .loop
.done:
    ret
```

### SIMD — NEON float loop (ARM64)

```asm
// void vadd_f32(float *dst, const float *a, const float *b, size_t n)
    .global vadd_f32
vadd_f32:
    cbz     x3, .done
    lsr     x3, x3, #2          // n /= 4
.loop:
    ld1     {v0.4s}, [x1], #16
    ld1     {v1.4s}, [x2], #16
    fadd    v0.4s, v0.4s, v1.4s
    st1     {v0.4s}, [x0], #16
    subs    x3, x3, #1
    b.ne    .loop
.done:
    ret
```

### Linux x86-64 Syscall

```nasm
; syscall(number, arg1, arg2, arg3)
; Note: r10 replaces rcx (syscall clobbers rcx and r11)
SYS_WRITE equ 1
SYS_EXIT  equ 60

section .data
    msg  db "hello", 10
    mlen equ $ - msg

section .text
global _start
_start:
    mov  rax, SYS_WRITE
    mov  rdi, 1
    lea  rsi, [rel msg]     ; RIP-relative — required for PIC/PIE
    mov  rdx, mlen
    syscall

    mov  rax, SYS_EXIT
    xor  edi, edi
    syscall
```

### ARM64 Linux Syscall

```asm
// ARM64 Linux: x8 = syscall number, x0-x5 = args, svc #0
    .equ SYS_WRITE, 64
    .equ SYS_EXIT,  93

    .global _start
_start:
    mov     x8, #SYS_WRITE
    mov     x0, #1              // fd = stdout
    adr     x1, msg             // PC-relative address
    mov     x2, #6              // length
    svc     #0

    mov     x8, #SYS_EXIT
    mov     x0, #0
    svc     #0

    .section .rodata
msg:    .ascii "hello\n"
```

### macOS ARM64 Syscall

```asm
// macOS: x16 = syscall number, svc #0x80; carry flag set on error
    mov     x16, #4             // SYS_write (macOS numbering)
    mov     x0, #1              // fd = stdout
    adr     x1, msg
    mov     x2, #6
    svc     #0x80
    b.cs    .error              // branch if carry set (syscall failed)
```

### Position-Independent Code (PIC)

```nasm
default rel                 ; make ALL memory refs RIP-relative (NASM)

section .data
    counter dq 0

section .text
global get_counter
get_counter:
    mov  rax, [counter]     ; compiles to: mov rax, [rip + offset]
    ret
```

### PIC — LEA for address loading

```nasm
; Load address of data (not value) — needed for passing pointers
lea  rdi, [rel my_string]    ; NASM: RIP-relative address
lea  rdi, my_string(%rip)    ; GAS: same thing, AT&T syntax
call puts
```

### PIC — CALL-POP base address (no RIP-relative)

```nasm
; Fallback for x86 (32-bit) or when RIP-relative is unavailable
call  .here
.here:
pop   ebx                    ; EBX = runtime address of .here
; access data: [ebx + (label - .here)]
```

### Stack-Based Strings (no data section)

```nasm
; Build "Hello" on stack without data section (useful for PIC/shellcode)
xor  rax, rax
push rax                     ; null terminator
mov  rax, 0x6F6C6C6548       ; "Hello" in little-endian
push rax
mov  rdi, rsp                ; rdi -> "Hello\0"
```

---

## Atomics & Memory Ordering (x86-64)

x86-64 provides acquire-release ordering automatically on regular `MOV`. Explicit fences/atomics are only needed for sequential consistency or special cases.

### Atomic Compare-and-Swap

```nasm
; lock cmpxchg: if [rdi] == rax then [rdi] = rcx; else rax = [rdi]
; Returns: ZF set on success; rax = old value either way
mov     rax, expected
mov     rcx, desired
lock cmpxchg [rdi], rcx
jnz     .retry               ; CAS failed — rax has current value
```

### Atomic Increment

```nasm
lock inc qword [rdi]         ; atomic increment, no return value
; or:
mov     rax, 1
lock xadd [rdi], rax         ; atomic fetch-and-add; old value in rax
```

### Memory Fences

| Instruction | Effect |
|---|---|
| `mfence` | Full barrier — serializes all loads and stores |
| `lfence` | Load barrier — serializes loads (also serializes RDTSC) |
| `sfence` | Store barrier — serializes stores (needed for NT stores) |
| `lock` prefix | Implicit full barrier on the locked instruction |

**Rule of thumb**: `lock cmpxchg` / `lock xchg` act as full barriers; separate `mfence` rarely needed on x86-64 for acquire-release.

For ARM64 atomics, see [references/arm64.md](references/arm64.md).

---

## Traps & Debugging

### Software Breakpoints

```nasm
; x86-64
int3                         ; SIGTRAP / EXCEPTION_BREAKPOINT

; ARM64
brk  #0                      ; BRK — triggers debug exception
```

### Undefined Instruction (crash intentionally)

```nasm
; x86-64: guaranteed #UD exception (useful for unreachable code)
ud2

; ARM64: undefined instruction
.inst 0x00000000             ; always SIGILL
```

### Stack Canary Check (GCC-style)

```nasm
; Prologue: load canary
mov  rax, [fs:0x28]          ; __stack_chk_guard (Linux x86-64)
mov  [rsp + FRAME_SIZE - 8], rax
; Epilogue: verify
mov  rax, [rsp + FRAME_SIZE - 8]
cmp  rax, [fs:0x28]
jne  __stack_chk_fail        ; abort — stack smashed
```

### Signal-Safe Probing (test memory access)

```nasm
; Linux x86-64: probe via mini-syscall (mincore, access, etc.)
; Safer than direct dereference for potentially unmapped memory
mov  rax, 27                 ; SYS_mincore
mov  rdi, addr
mov  rsi, 1                  ; length
lea  rdx, [rsp - 8]          ; vec buffer (red zone)
syscall
test rax, rax
js   .page_not_mapped
```

---

## Code Style Rules

1. **File header** — purpose, architecture, syntax, author
2. **Function header** — C prototype comment, register mapping, return value
3. **Inline comments** — explain *why*, not *what* (`; pointer alignment check`, not `; compare`)
4. **Label naming** — `module_function_sublabel` (e.g., `crypto_sha256_loop`)
5. **Constants** — always `equ` / `.equ` with descriptive names, never magic numbers
6. **Callee-saved** — always save before use, restore in reverse order
7. **Stack** — 16-byte aligned before every `call`; never leave dirty in epilogue
8. **Alignment directives** — `align 16` before hot loops on x86-64; mandatory for SSE/AVX loads

---

## Toolchain Quick Reference

```bash
# NASM → Linux ELF64 (debug info)
nasm -f elf64 -g -F dwarf file.asm -o file.o

# NASM → macOS Mach-O 64
nasm -f macho64 file.asm -o file.o

# GAS (AT&T syntax)
as --64 -g file.s -o file.o

# Link (no libc)
ld -o prog file.o

# Link (with libc / C interop)
gcc -o prog file.o

# Shared library (PIC required)
gcc -shared -o libfoo.so foo.o

# Inspect symbols
nm -u file.o                 # undefined references
readelf -S file.o            # section layout

# Disassemble with Intel syntax
objdump -d -M intel prog

# Verify calling convention at runtime (GDB)
gdb prog
(gdb) set disassembly-flavor intel
(gdb) layout asm
(gdb) p/x $rsp & 0xf        # must be 0 at every call boundary
```

---

## Performance Guidelines

| Rule | Rationale |
|---|---|
| Profile first, optimize second | Don't write ASM unless profiling proves the C/compiler output is the bottleneck |
| `lea` over `imul` for small multiplies | `lea rax, [rdi+rdi*2]` = 1 cycle; `imul` = 3 cycles |
| `vzeroupper` after AVX code | Avoids SSE-AVX transition penalty on Intel (Haswell-Ice Lake) |
| Multiple accumulators in reduction loops | Breaks dependency chains; uses more execution ports in parallel |
| `cmov` for simple branches | Avoids ~15-cycle misprediction penalty; worse if branch is very predictable |
| Align hot loop entries to 16/32 bytes | Reduces I-cache splits and front-end stalls |
| Avoid `div`/`idiv` in loops | 20-40 cycles; replace constant divisors with multiply+shift |
| `pause` in spinloops | Reduces power and avoids memory-order pipeline flush on x86 |
| Match load/store widths | Prevents store-forwarding stalls (e.g., store dword + load qword) |
| Prefer `movzx eax, X` over `mov al, X` | Avoids partial-register stalls and false dependencies |

For detailed latency tables and alignment guidelines, see [references/x86-64.md](references/x86-64.md).
For ARM64 performance tips, see [references/arm64.md](references/arm64.md).

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Missing shadow space on Win64 calls | Always `sub rsp, 32` before `call` on Windows |
| Stack misaligned before `call` | RSP must be 16-byte aligned at point of `call` |
| Forgetting `syscall` clobbers `rcx`, `r11` | Use `r10` for arg4; save `rcx`/`r11` if needed |
| Using `push`/`pop` on ARM64 | Use `stp`/`ldp` with explicit offsets |
| Missing `vzeroupper` after AVX code | Required before calling SSE/non-AVX code (transition penalty) |
| `movaps` on unaligned address | Use `movups` unless alignment is guaranteed |
| Modifying `x18` on macOS ARM64 | Reserved as platform register — never touch |
| Writing 32-bit reg without knowing upper clear | `mov eax, X` zeros upper 32 bits of `rax`; `mov ax, X` does not |
| Red zone on Windows or in signal handlers | No red zone on Win64; on Linux, only valid in leaf functions |

---

## Resources

Load on demand during development:

| File | When to load |
|---|---|
| [references/x86-64.md](references/x86-64.md) | Register table, instruction selection, SSE/AVX/AVX-512 patterns, Win64 details, atomics, ABI edge cases |
| [references/arm64.md](references/arm64.md) | Register table, NEON/SVE patterns, atomics, AAPCS edge cases, Apple Silicon specifics |
| [assets/function-template-x64.asm](assets/function-template-x64.asm) | NASM function template with System V + Win64 conditional assembly |
| [assets/function-template-arm64.s](assets/function-template-arm64.s) | GAS ARM64 function template with prologue/epilogue |
