---
name: asm-patterns
description: "Assembly language patterns, calling conventions, and code structure for x86-64 and ARM64. Use when writing, reviewing, or generating .asm/.s/.S files; when implementing functions that interoperate with C/system code; or when establishing correct prologues, epilogues, stack management, SIMD loops, syscall stubs, or PIC data access."
license: MIT
metadata:
  author: AeonDave
  version: "1.1"
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

**Win64 >4 args**: place arg5+ at `[rsp+32]` above shadow space; allocate `32 + 8*extra_args` (keep 16-byte aligned).

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
    mov     x16, #4             // SYS_write
    mov     x0, #1              // stdout
    adr     x1, msg
    mov     x2, #6
    svc     #0x80
    b.cs    .error              // carry set = syscall failed
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

### PIC — CALL-POP (legacy x86-32)

```nasm
call  .here
.here:
pop   ebx                    ; EBX = runtime address of .here
; access data: [ebx + (label - .here)]
```

### Stack Strings (no data section)

```nasm
xor  rax, rax
push rax                     ; null terminator
mov  rax, 0x6F6C6C6548       ; "Hello" in little-endian
push rax
mov  rdi, rsp                ; rdi -> "Hello\0"
```

---

## Bit Manipulation & Branchless Patterns

### BMI1/BMI2 Idioms (x86-64, Haswell+)

```nasm
; Population count
popcnt  rax, rdi             ; rax = number of set bits in rdi

; Trailing/leading zeros (replacing bsf/bsr)
tzcnt   rax, rdi             ; count trailing zeros (BMI1); sets CF if rdi==0
lzcnt   rax, rdi             ; count leading zeros (ABM/LZCNT)

; Isolate / reset lowest set bit
blsi    rax, rdi             ; rax = rdi & (-rdi)  — isolate lowest set bit
blsr    rax, rdi             ; rax = rdi & (rdi-1) — reset lowest set bit

; Bit field extract/deposit (BMI2)
pext    rax, rdi, rsi        ; extract bits from rdi selected by mask rsi
pdep    rax, rdi, rsi        ; deposit contiguous bits into positions set in rsi
bzhi    rax, rdi, rsi        ; zero bits in rdi from bit position rsi upward
```

**Feature check**: `CPUID.(EAX=07h,ECX=0):EBX` — bit 3 = BMI1, bit 8 = BMI2.

### Branchless Patterns (x86-64)

```nasm
; abs(x) — branchless
mov     rax, rdi
mov     rdx, rdi
sar     rdx, 63              ; all-1s if negative, all-0s if positive
xor     rax, rdx
sub     rax, rdx             ; rax = abs(rdi)

; min(a, b) — unsigned
cmp     rdi, rsi
cmovb   rdi, rsi             ; rdi = min
mov     rax, rdi

; clamp(x, lo, hi)
cmp     edi, esi
cmovl   edi, esi             ; x = max(x, lo)
cmp     edi, edx
cmovg   edi, edx             ; x = min(x, hi)
mov     eax, edi

; bool: count += (x == val) — avoid branch in hot loop
cmp     rdi, rsi
sete    al                   ; al = 1 if equal
movzx   eax, al
add     [counter], eax
```

### Branchless Patterns (ARM64)

```asm
// abs(x)
cmp     x0, #0
cneg    x0, x0, mi           // negate if negative

// min(a, b)
cmp     x0, x1
csel    x0, x0, x1, lt       // x0 = (x0 < x1) ? x0 : x1

// clamp(x, lo, hi)
cmp     w0, w1
csel    w0, w1, w0, lt       // max(x, lo)
cmp     w0, w2
csel    w0, w2, w0, gt       // min(x, hi)

// conditional increment — no branch
cmp     x0, x1
cset    x2, eq               // x2 = (x0 == x1) ? 1 : 0
add     x3, x3, x2
```

**When NOT to go branchless**: highly predictable branches (>95% one way) are faster than `cmov`/`csel` because the CPU speculates correctly and avoids the data dependency.

---

## Atomics & Memory Ordering (x86-64)

x86-64 TSO guarantees acquire-release on regular `MOV`; explicit fences only for sequential consistency or NT stores.

```nasm
; CAS: if [rdi] == rax then [rdi] = rcx; else rax = [rdi]
mov     rax, expected
mov     rcx, desired
lock cmpxchg [rdi], rcx
jnz     .retry               ; CAS failed — rax has current value

; Atomic fetch-and-add
mov     rax, 1
lock xadd [rdi], rax         ; old value returned in rax
```

| Fence | Use case |
|---|---|
| `mfence` | Full barrier — rarely needed with `lock` instructions |
| `sfence` | Required after non-temporal stores (`movnti`, `vmovntps`) |
| `lfence` | Serialize dispatch (e.g., before `rdtsc` for timing) |

For ARM64 atomics (exclusive pairs, LSE, barriers), see [references/arm64.md](references/arm64.md).

---

## Traps & Debugging

```nasm
; Software breakpoint
int3                         ; x86-64: SIGTRAP
brk  #0                      ; ARM64: debug exception

; Unreachable crash (mark dead code)
ud2                          ; x86-64: guaranteed #UD
.inst 0x00000000             ; ARM64: SIGILL

; Stack canary check (GCC-style, Linux x86-64)
mov  rax, [fs:0x28]          ; prologue: load canary
mov  [rsp + FRAME_SIZE - 8], rax
; ... function body ...
cmp  rax, [fs:0x28]          ; epilogue: verify
jne  __stack_chk_fail
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
8. **Alignment directives** — `align 16` before hot loops; mandatory for aligned SIMD loads

---

## Register Allocation Strategy

Plan register usage before writing code. Document the mapping in a comment block:

```nasm
; Register plan:
;   rbx = base pointer (callee-saved, survives calls)
;   r12 = loop counter (callee-saved)
;   rdi/rsi = scratch / pass to callees
;   xmm0-xmm3 = SIMD accumulators
```

**Rules**:
- Map long-lived values to callee-saved registers (`rbx`, `r12`–`r15` / `x19`–`x28`)
- Use caller-saved registers for temporaries consumed before the next `call`
- Minimize `push`/`pop` count — each saves 2 cycles + stack space
- On ARM64, save/restore in `stp`/`ldp` pairs (always two at a time)
- When >6 values are live across a call, spill the least frequently used to stack

---

## Macro Patterns

### NASM — Reusable macros

```nasm
; Save/restore multiple registers
%macro multipush 1-*
  %rep %0
    push %1
    %rotate 1
  %endrep
%endmacro

%macro multipop 1-*
  %rep %0
    %rotate -1
    pop %1
  %endrep
%endmacro

; Usage: multipush rbx, r12, r13 / multipop rbx, r12, r13
```

### GAS — Parameterized macro

```asm
// ARM64: save/restore callee-saved pair
.macro save_pair reg1, reg2, offset
    stp     \reg1, \reg2, [sp, #\offset]
.endm
.macro restore_pair reg1, reg2, offset
    ldp     \reg1, \reg2, [sp, #\offset]
.endm
```

### Constant Tables with Macros

```nasm
; NASM: Syscall number table
%define SYS_READ   0
%define SYS_WRITE  1
%define SYS_OPEN   2
%define SYS_CLOSE  3
%define SYS_EXIT   60
```

---

## Toolchain Quick Reference

```bash
# NASM → ELF64 (Linux, debug)
nasm -f elf64 -g -F dwarf file.asm -o file.o
# NASM → Mach-O 64 (macOS)
nasm -f macho64 file.asm -o file.o
# GAS → object
as --64 -g file.s -o file.o
# Link (no libc / with libc)
ld -o prog file.o
gcc -o prog file.o
# Disassemble (Intel syntax)
objdump -d -M intel prog
# Verify stack alignment (GDB)
gdb prog -ex 'set disassembly-flavor intel' -ex 'layout asm'
```

---

## Performance Guidelines

| Rule | Rationale |
|---|---|
| Profile first, optimize second | Don't write ASM unless profiling proves the bottleneck |
| `lea` over `imul` for small multiplies | `lea rax, [rdi+rdi*2]` = 1 cycle; `imul` = 3 cycles |
| `vzeroupper` after AVX code | Avoids SSE-AVX transition penalty (Haswell–Ice Lake) |
| Multiple accumulators in reductions | Breaks dependency chains; uses more execution ports |
| `cmov`/`csel` for unpredictable branches | Avoids ~15-cycle misprediction; skip if branch >95% predictable |
| Align hot loops to 16/32 bytes | Reduces I-cache splits and front-end stalls |
| Avoid `div`/`idiv` in loops | 20-40 cycles; constant divisors → multiply+shift |
| `pause` in spinloops | Reduces power; avoids memory-order pipeline flush (x86) |
| Match load/store widths | Prevents store-forwarding stalls |
| `movzx eax, X` over `mov al, X` | Avoids partial-register stalls and false dependencies |
| Break dependency chains | Split serial chains: `add rax,rbx / add rcx,rdx` > `add rax,rbx / add rax,rdx` |
| Unroll by 2–4× in tight loops | Reduces branch overhead; exposes ILP to out-of-order engine |
| Count down to zero | `dec rcx / jnz` saves a `cmp`; ZF set automatically |

For latency tables and alignment guidelines, see [references/x86-64.md](references/x86-64.md).
For ARM64 tips (stp/ldp pairs, cbz/tbnz, NEON lane costs), see [references/arm64.md](references/arm64.md).

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Missing shadow space on Win64 | Always `sub rsp, 32` before `call` on Windows |
| Stack misaligned before `call` | RSP must be 16-byte aligned at the `call` instruction |
| Forgetting `syscall` clobbers `rcx`, `r11` | Use `r10` for arg4; save `rcx`/`r11` if needed |
| Using `push`/`pop` on ARM64 | Use `stp`/`ldp` with explicit offsets |
| Missing `vzeroupper` after AVX | Required before calling SSE/non-AVX code |
| `movaps` on unaligned address | Use `movups` unless alignment guaranteed |
| Modifying `x18` on macOS ARM64 | Reserved platform register — never touch |
| `mov al, X` then reading `rax` | Partial-register stall; use `movzx eax, byte [X]` |
| Red zone on Win64 / signal handlers | No red zone on Win64; Linux leaf-only |
| Signed vs unsigned condition codes | `jl`/`jg` (signed) vs `jb`/`ja` (unsigned) — wrong choice = subtle bugs |
| `shr` clears OF but doesn't set SF usefully | Test result separately after logical shifts; don't rely on flags |
| `imul` single-operand vs two/three | 1-op `imul rdi` writes `rdx:rax`; 2-op `imul rax, rdi` keeps only low 64 |
| Forgetting `lock` on shared atomics | `cmpxchg`/`xadd` without `lock` are not atomic on SMP |
| Redundant `cmp` before conditional jump | `test rax, rax` is shorter than `cmp rax, 0`; `dec`/`sub` already sets ZF |

---

## Resources

Load on demand during development:

| File | When to load |
|---|---|
| [references/x86-64.md](references/x86-64.md) | Register table, instruction selection, SSE/AVX/AVX-512 patterns, Win64 details, atomics, ABI edge cases |
| [references/arm64.md](references/arm64.md) | Register table, NEON/SVE patterns, atomics, AAPCS edge cases, Apple Silicon specifics |
| [assets/function-template-x64.asm](assets/function-template-x64.asm) | NASM function template with System V + Win64 conditional assembly |
| [assets/function-template-arm64.s](assets/function-template-arm64.s) | GAS ARM64 function template with prologue/epilogue |
