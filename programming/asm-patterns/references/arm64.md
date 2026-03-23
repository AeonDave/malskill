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

## Atomic Operations

ARM64 has two atomic approaches: exclusive load/store pairs (ARMv8.0) and Large System Extensions (LSE, ARMv8.1+).

### Exclusive Pairs (ARMv8.0)

```asm
// Compare-and-swap using exclusive load/store
atomic_cas:
    ldxr    x2, [x0]            // exclusive load: x2 = *x0
    cmp     x2, x1              // compare with expected
    b.ne    .fail
    stxr    w3, x1, [x0]        // exclusive store: *x0 = x1, w3 = status
    cbnz    w3, atomic_cas       // retry if store failed (contention)
    ret
.fail:
    clrex                        // clear exclusive monitor
    ret
```

### LSE Atomics (ARMv8.1+, preferred on modern hardware)

```asm
// CAS: compare-and-swap with acquire-release ordering
casa    x1, x2, [x0]            // if *x0==x1: *x0=x2; x1=old value

// Atomic fetch-and-add
ldaddal x1, x2, [x0]            // x2 = old *x0; *x0 += x1

// Atomic swap
swpal   x1, x2, [x0]            // x2 = old *x0; *x0 = x1

// Atomic bit operations
ldclral x1, x2, [x0]            // *x0 &= ~x1 (clear bits)
ldsetal x1, x2, [x0]            // *x0 |= x1 (set bits)
```

**Ordering suffixes**: plain (relaxed), `a` (acquire), `l` (release), `al` (acquire-release).

### Memory Barriers

| Instruction | Effect |
|---|---|
| `dmb ish` | Data memory barrier — inner-shareable (multi-core) |
| `dmb ishst` | Store-only barrier (lighter than full `dmb ish`) |
| `dsb ish` | Data synchronization barrier — waits for completion |
| `isb` | Instruction synchronization — flushes pipeline |
| `dmb oshst` | Outer-shareable store barrier (cross-cluster) |

**Rule of thumb**: use `dmb ish` for most acquire/release patterns; `dsb` + `isb` only for page table changes or self-modifying code.

---

## SVE / SVE2 Patterns

SVE (Scalable Vector Extension) uses vector-length-agnostic programming. Vector width is 128–2048 bits, determined at runtime.

### Predicated Vector Loop

```asm
// Add two float arrays: dst[i] = a[i] + b[i], VL-agnostic
vec_add:
    mov     x3, #0               // byte offset
    whilelt p0.s, x3, x2         // p0 = predicate: which lanes active
    b.none  .done
.loop:
    ld1w    {z0.s}, p0/z, [x0, x3, lsl #2]  // load a[] (inactive = 0)
    ld1w    {z1.s}, p0/z, [x1, x3, lsl #2]  // load b[]
    fadd    z0.s, z0.s, z1.s                 // add
    st1w    {z0.s}, p0, [x0, x3, lsl #2]     // store dst[]
    incw    x3                                // x3 += VL in words
    whilelt p0.s, x3, x2
    b.first .loop
.done:
    ret
```

### Key SVE Concepts

- **Predicate registers** `p0`–`p15`: per-element mask (1 bit per byte of element)
- **`whilelt`**: generates predicate from loop counter; replaces explicit tail handling
- **`incw`/`incd`/`incb`**: increment by hardware VL (word/double/byte granularity)
- **No cleanup loop**: final iteration uses partial predicate automatically
- **SVE2**: adds crypto, bit manipulation, histogram, polynomial multiply

---

## Apple Silicon Specifics

- **PAC** (Pointer Authentication): `bl` / `ret` may insert PAC codes on M1+ in hardened mode. In hand-written asm use `blraaz` / `retaa` only if you understand the context. Key families: `IA` (instruction A-key), `DA` (data A-key), `IB`, `DB`. On macOS, system libraries use PAC by default.
- **Memory ordering**: Apple Silicon is TSO (Total Store Order) — stronger than generic ARM64 (weakly ordered). Multi-core code still needs `dmb ish` for portability; `stlr`/`ldar` for acquire-release.
- **x18 register**: reserved as platform register on macOS/iOS — never read or write it.
- **Xcode assembler**: use `.s` extension; GAS AT&T syntax is default. For Intel syntax: `.intel_syntax noprefix` at file top (not recommended — use NASM instead).
- **macOS syscall ABI**: `x16` = syscall number; use `svc #0x80`. Different from Linux (`x8` + `svc #0`).
- **Stack alignment**: SP must always be 16-byte aligned. Hardware exception on misaligned SP access (unlike x86 which silently works).
- **W-register writes**: writing `w0` (32-bit) zeros the upper 32 bits of `x0` (same as x86-64).

### macOS vs Linux Syscall Comparison

| | Linux | macOS |
|---|---|---|
| Syscall number | `x8` | `x16` |
| Instruction | `svc #0` | `svc #0x80` |
| Return | `x0` (negative on error) | `x0`; carry flag set on error |
| Error convention | `x0 = -errno` | `x0 = errno`, carry = 1 |

---

## Performance Tips (ARM64)

- **Use `stp`/`ldp` pairs**: single instruction stores/loads two registers; half the memory ops of individual `str`/`ldr`
- **Branch prediction**: ARM64 has excellent prediction; `cbz`/`cbnz`/`tbz`/`tbnz` are cheap (fused compare+branch)
- **Avoid `x18`**: clobbers TLS on macOS; undefined on some platforms
- **Literal pools**: move large constants with `movz`/`movk` pairs (up to 64-bit in 4 instructions) or `ldr x0, =constant`
- **NEON lane operations**: `umov`/`ins` have higher latency than vector ops; minimize scalar→vector→scalar transitions
- **Alignment**: NEON `ld1`/`st1` handle unaligned data but may be slower; align hot data to 16 bytes
- **Division**: ARM64 has hardware `udiv`/`sdiv` (unlike ARM32); still 10–20 cycles — use shifts for powers of 2

---

## External References

- [ARM Architecture Reference Manual (ARMv8-A)](https://developer.arm.com/documentation/ddi0487/latest)
- [AArch64 ABI Specification](https://github.com/ARM-software/abi-aa/releases)
- [ARM NEON Intrinsics Reference](https://developer.arm.com/architectures/instruction-sets/intrinsics/)
- [Apple Silicon — Using Assembly in iOS/macOS](https://developer.apple.com/documentation/xcode/writing-arm64-code-for-apple-platforms)
- [ARM SVE Programming Guide](https://developer.arm.com/documentation/dai0548/latest)
- [ARM LSE Atomics Overview](https://developer.arm.com/documentation/102336/latest)
