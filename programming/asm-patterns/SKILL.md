---
name: asm-patterns
description: "Assembly language patterns, calling conventions, and code structure for x86-64 and ARM64. Use when writing, reviewing, or generating .asm/.s/.S files; when implementing functions that interoperate with C/system code; or when establishing correct prologues, epilogues, stack management, SIMD loops, syscall stubs, or PIC data access."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
compatibility: "NASM >= 2.15 or GAS (binutils). Targets: x86-64 Linux/macOS (System V ABI), ARM64 Linux/macOS (AAPCS)."
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

---

## Core Patterns

### x86-64 — Non-leaf function

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

### x86-64 — Leaf function (no calls, red zone)

```nasm
; int64_t add3(int64_t a, int64_t b, int64_t c)
; Args: rdi=a, rsi=b, rdx=c   Returns: rax
global add3
add3:
    lea     rax, [rdi + rsi]    ; rax = a + b
    add     rax, rdx            ; rax += c
    ret
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

## Resources

Load on demand during development:

- [references/x86-64.md](references/x86-64.md) — complete register table, instruction selection guide, SSE/AVX patterns, x86-64 ABI edge cases
- [references/arm64.md](references/arm64.md) — ARM64 register table, NEON/SVE patterns, AAPCS edge cases, Apple Silicon specifics
