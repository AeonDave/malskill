# ARM64 (AArch64) Reference

## Register Table

| Registers | Role | Notes |
|---|---|---|
| `x0`–`x7` | Integer args / return | `x0` = return value; `w0`–`w7` = 32-bit views |
| `x8` | Indirect result location | Used for large struct returns |
| `x9`–`x15` | Caller-saved temporaries | Free to clobber |
| `x16`, `x17` | Intra-procedure-call scratch | Used by linker stubs (avoid in hand-written code) |
| `x18` | Platform register | Reserved on iOS/macOS; avoid |
| `x19`–`x28` | Callee-saved | Must preserve across calls |
| `x29` | Frame pointer (`fp`) | Required for stack unwinding |
| `x30` | Link register (`lr`) | Return address; save before `bl` |
| `xzr` / `wzr` | Zero register | Reads always return 0; writes discarded |
| `sp` | Stack pointer | Must remain 16-byte aligned at all times |
| `d0`–`d7` | Float args / return | `v0`–`v7` for NEON (128-bit) |
| `d8`–`d15` | Callee-saved float | `s8`–`s15` (32-bit), `d8`–`d15` (64-bit) |
| `v16`–`v31` | Caller-saved NEON | Only lower 64 bits callee-saved on AAPCS64 |

---

## Prologue / Epilogue Templates

### Leaf function (no callee-saved regs)

```asm
    .global leaf_fn
leaf_fn:
    // body using only x0-x15 (caller-saved)
    ret
```

### Non-leaf, saves lr + callee-saved

```asm
    .global nonleaf_fn
nonleaf_fn:
    stp     x29, x30, [sp, #-48]!   // alloc 48 bytes, save fp+lr
    mov     x29, sp
    stp     x19, x20, [sp, #16]     // save callee-saved pair
    stp     x21, x22, [sp, #32]

    // body

    ldp     x21, x22, [sp, #32]
    ldp     x19, x20, [sp, #16]
    ldp     x29, x30, [sp], #48
    ret
```

**Key rules**:
- `stp` / `ldp` offsets must be multiples of 8; pre-index `[sp, #-N]!` must be negative
- Stack frame size always a multiple of 16
- Never use `push` — x86 habit; use `str` / `stp` with explicit offsets

---

## Conditional Execution

ARM64 has no predicated instructions (unlike ARM32). Use `csel`, `csinc`, `csinv` for branchless code:

```asm
// x0 = (x0 < x1) ? x0 : x1  →  min
cmp     x0, x1
csel    x0, x0, x1, lt      // x0 = (lt) ? x0 : x1

// x0 = (x0 == 0) ? 1 : 0  →  !x0
cmp     x0, #0
cset    x0, eq              // shorthand for csinc x0, xzr, xzr, ne
```

### Condition codes

| Suffix | Meaning | Flags |
|---|---|---|
| `eq` | equal | Z=1 |
| `ne` | not equal | Z=0 |
| `lt` | less than (signed) | N≠V |
| `le` | less or equal (signed) | Z=1 or N≠V |
| `gt` | greater than (signed) | Z=0 and N=V |
| `ge` | greater or equal (signed) | N=V |
| `lo` / `cc` | unsigned below | C=0 |
| `hi` | unsigned above | C=1 and Z=0 |

---

## NEON Patterns

### NEON vector add (4×float32)

```asm
    ld1     {v0.4s}, [x1], #16   // load + post-increment
    ld1     {v1.4s}, [x2], #16
    fadd    v0.4s, v0.4s, v1.4s
    st1     {v0.4s}, [x0], #16
```

### NEON horizontal sum (4×float32)

```asm
    faddp   v0.4s, v0.4s, v0.4s  // [a+b, c+d, a+b, c+d]
    faddp   s0, v0.2s             // s0 = a+b+c+d
```

### NEON byte search (16 bytes)

```asm
    ld1     {v0.16b}, [x0]
    movi    v1.16b, #0
    cmeq    v0.16b, v0.16b, v1.16b  // 0xFF where byte==0
    umaxv   b2, v0.16b              // b2 != 0 if any match
    umov    w0, v2.b[0]
    cbnz    w0, .found
```

---

## Apple Silicon Specifics

- **PAC** (Pointer Authentication): `bl` / `ret` may insert PAC codes on M1+ in hardened mode. In hand-written asm use `blraaz` / `retaa` only if you understand the context.
- **Memory ordering**: Apple Silicon is TSO (Total Store Order) — weaker than x86 but stronger than generic ARM64. `dmb ish` needed for multi-core; omit for single-threaded.
- **Xcode assembler**: use `.s` extension; GAS AT&T syntax is default. For Intel syntax: `.intel_syntax noprefix` at file top (not recommended — use NASM instead).
- **macOS syscall ABI**: `x16` = syscall number; use `svc #0x80`. Different from Linux (`x8` + `svc #0`).

---

## External References

- [ARM Architecture Reference Manual (ARMv8-A)](https://developer.arm.com/documentation/ddi0487/latest)
- [AArch64 ABI Specification](https://github.com/ARM-software/abi-aa/releases)
- [ARM NEON Intrinsics Reference](https://developer.arm.com/architectures/instruction-sets/intrinsics/)
- [Apple Silicon — Using Assembly in iOS/macOS](https://developer.apple.com/documentation/xcode/writing-arm64-code-for-apple-platforms)
