---
name: asm-testing
description: "Assembly code testing and verification workflow: C harness for unit testing hand-written functions, GDB/LLDB register inspection, objdump structural analysis, ABI compliance checklist, and cycle-accurate measurement. Use when verifying correctness of new .asm/.s/.S files or debugging unexpected behavior in manually written or hand-optimized assembly."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
compatibility: "x86-64 and ARM64. Tools: GDB >= 10 or LLDB >= 12, gcc/clang, nasm, objdump (binutils)."
---

# asm-testing

Structured workflow for testing and verifying hand-written assembly.

---

## Phase 1 — ABI Compliance Checklist

Run this before writing a single test. A function that violates the ABI may appear to work until it silently corrupts caller state.

### x86-64 System V

- [ ] `rsp` is 16-byte aligned at every `call` site (misalignment triggers SSE crashes)
- [ ] `rbx`, `r12`–`r15` are restored to their entry values before `ret`
- [ ] Integer return value in `rax`; float/double in `xmm0`
- [ ] Stack frame properly deallocated (no net drift)
- [ ] No writes below `rsp` except within the red zone (leaf functions only)

### ARM64 AAPCS

- [ ] `sp` is 16-byte aligned at all times (hardware enforces this)
- [ ] `x19`–`x28` and `d8`–`d15` restored before `ret`
- [ ] `x29` (fp) and `x30` (lr) saved with `stp x29, x30, [sp, #-N]!` if calling out
- [ ] Integer return in `x0`; float return in `d0`

---

## Phase 2 — Structural Analysis (before running)

```bash
# Disassemble and check prologue/epilogue
objdump -d -M intel -S my.o | grep -A40 '<my_fn>:'

# Verify callee-saved registers are saved
objdump -d -M intel my.o | grep -E 'push|pop|mov \[rsp'

# Check section flags
objdump -h my.o

# Verify exported symbols
nm my.o | grep ' T '

# Show relocation targets (PIC / GOT usage)
objdump -r my.o
```

**What to confirm**:
- Prologue saves the registers the function uses
- Epilogue restores exactly those registers in reverse order
- Stack allocation/deallocation is symmetric
- No jump to undefined symbols

---

## Phase 3 — C Harness Unit Test

Write a thin C driver that calls the ASM function and asserts results.

```c
/* test_hot_fn.c */
#include <stdio.h>
#include <stdint.h>
#include <assert.h>
#include <string.h>

/* Declare the ASM function */
extern int64_t hot_fn(int64_t a, int64_t b);

typedef struct { int64_t a; int64_t b; int64_t expected; } Case;

static const Case cases[] = {
    { 0,  0,  0 },
    { 1,  2,  3 },
    { -1, 1,  0 },
    { INT64_MAX, 0, INT64_MAX },
};

int main(void) {
    int failed = 0;
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        int64_t got = hot_fn(cases[i].a, cases[i].b);
        if (got != cases[i].expected) {
            fprintf(stderr, "FAIL case %zu: hot_fn(%ld, %ld) = %ld, want %ld\n",
                    i, cases[i].a, cases[i].b, got, cases[i].expected);
            failed++;
        }
    }
    if (!failed) puts("ALL PASS");
    return failed ? 1 : 0;
}
```

### Build and run

```bash
# NASM + C harness
nasm -f elf64 hot_fn.asm -o hot_fn.o
gcc -g -o test_hot_fn test_hot_fn.c hot_fn.o
./test_hot_fn

# GAS + C harness
as -g --gstabs+ hot_fn.s -o hot_fn.o
gcc -g -o test_hot_fn test_hot_fn.c hot_fn.o
./test_hot_fn
```

> Load `references/c-harness.md` for Makefile patterns and assertion helpers for floats, SIMD output, and memory buffers.

---

## Phase 4 — GDB / LLDB Verification

Use the debugger to step through the function and verify register state at each critical point.

### GDB session

```bash
gdb ./test_hot_fn
(gdb) break hot_fn
(gdb) run
(gdb) layout asm          # split ASM view
(gdb) layout regs         # show register panel
(gdb) si                  # step one instruction
(gdb) info registers      # dump all GP registers
(gdb) p/x $rax            # print register as hex
(gdb) x/8gx $rsp          # examine 8 quadwords at rsp
```

### LLDB session

```bash
lldb ./test_hot_fn
(lldb) b hot_fn
(lldb) run
(lldb) disassemble --pc   # disassemble around current PC
(lldb) register read      # all GP registers
(lldb) register read xmm0 # specific register
(lldb) memory read --size 8 --count 8 $rsp
(lldb) si                 # step one instruction
```

> Load `references/debug-commands.md` for the full command reference including watchpoints, memory inspection, and conditional breakpoints.

### Checklist during stepping

- At function entry: note values of `rbx`, `r12`–`r15` (`rsp – offset` saved?)
- After prologue: stack pointer difference from entry equals declared frame size
- At every `call`: verify `rsp` is 16-byte aligned (`p/x $rsp % 16` must be 0)
- At `ret`: `rbx`, `r12`–`r15` match their entry values; `rax` holds the correct result

---

## Phase 5 — SIMD / Float Output Verification

Standard integer comparison fails for SIMD types. Use `memcmp` for exact bit equality or a tolerance check for floats.

```c
#include <immintrin.h>
#include <stdint.h>
#include <string.h>

/* ASM: void vec_add(float *dst, const float *src, int n) */
extern void vec_add(float *dst, const float *src, int n);

static void test_vec_add(void) {
    float dst[8] = {1,2,3,4,5,6,7,8};
    float src[8] = {1,1,1,1,1,1,1,1};
    float exp[8] = {2,3,4,5,6,7,8,9};

    vec_add(dst, src, 8);
    for (int i = 0; i < 8; i++) {
        if (dst[i] != exp[i]) {
            fprintf(stderr, "FAIL dst[%d] = %f, want %f\n", i, dst[i], exp[i]);
        }
    }
}
```

For floating-point functions with rounding: use `fabsf(got - expected) < 1e-6f`.

---

## Phase 6 — Cycle Measurement

Only after correctness is confirmed.

```c
/* Portable RDTSC (x86-64) */
#include <stdint.h>
static inline uint64_t rdtsc(void) {
    uint32_t lo, hi;
    __asm__ volatile(
        "lfence\n"
        "rdtsc\n"
        "lfence\n"
        : "=a"(lo), "=d"(hi)
        :
        : "memory"
    );
    return ((uint64_t)hi << 32) | lo;
}

void bench_hot_fn(void) {
    const int RUNS = 10000;
    uint64_t total = 0;
    for (int i = 0; i < RUNS; i++) {
        uint64_t t0 = rdtsc();
        hot_fn(i, i+1);
        uint64_t t1 = rdtsc();
        total += t1 - t0;
    }
    printf("avg cycles: %.2f\n", (double)total / RUNS);
}
```

For meaningful results: pin to one CPU core (`taskset -c 0 ./bench`), disable turbo if possible.

---

## Resources

- `references/debug-commands.md` — full GDB/LLDB/objdump/readelf/strace command reference
- `references/c-harness.md` — Makefile templates, float comparison helpers, memory buffer tests
