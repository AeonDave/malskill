# Codegen Issues — Before / After Patterns

Reference for Phase 2 audit. Each entry shows the ASM symptom and a corrected version.

---

## 1. Panic / Bounds Paths

### Symptom

A `call` or conditional jump to a panic handler inside or adjacent to a hot loop:

```asm
.LBB0_3:
    cmp     rax, rdx
    jae     .LBB0_panic          ; ← bounds check before every access
    mov     ecx, [rsi + rax*4]
    inc     rax
    cmp     rax, rdi
    jne     .LBB0_3
    ret
.LBB0_panic:
    call    core::panicking::panic_bounds_check
    ud2
```

### Fix (Rust)

Use `split_at` / `chunks_exact` to let the compiler elide the check, or `unsafe get_unchecked`:

```rust
// Hint: proven safe range → no check in loop
for chunk in slice.chunks_exact(4) {
    process(chunk[0], chunk[1], chunk[2], chunk[3]);
}

// Explicit: verified safe, disable per element
unsafe {
    for i in 0..n {
        *out.get_unchecked_mut(i) = *input.get_unchecked(i) * 2;
    }
}
```

**After ASM**: no `jae` / `ud2` in loop body.

---

## 2. Register Spills

### Symptom

Values being written to the stack inside the loop because the compiler runs out of registers:

```asm
.hot_loop:
    mov     [rsp+8],  r13        ; ← spill r13 every iteration
    mov     [rsp+16], r14        ; ← spill r14
    ...
    mov     r13, [rsp+8]         ; ← reload
```

### Fix

- Reduce live variables in the loop body — move invariants outside
- Break the function into smaller callees so each has fewer live values
- In C: `register` keyword (hint only) or reduce struct member references

```c
// Before: many fields accessed inside loop
for (int i = 0; i < n; i++) s->buf[i] += s->base * s->scale;

// After: hoist invariant multiplications
const int factor = s->base * s->scale;
for (int i = 0; i < n; i++) s->buf[i] += factor;
```

**After ASM**: no `mov [rsp+N]` inside loop body.

---

## 3. Dependency Chains

### Symptom

Accumulation into a single register prevents out-of-order execution:

```asm
.sum_loop:
    add     rax, [rsi]       ; every add depends on previous rax
    add     rsi, 8
    dec     rcx
    jnz     .sum_loop
```

One new `add` can start only after the previous completes (3–5 cycle latency).

### Fix

Unroll and use multiple accumulators:

```nasm
.sum_loop:
    add     rax, [rsi]        ; acc0
    add     rbx, [rsi+8]      ; acc1 — independent from rax
    add     rcx, [rsi+16]     ; acc2
    add     rdx, [rsi+24]     ; acc3
    add     rsi, 32
    sub     r8, 4
    jnz     .sum_loop
    add     rax, rbx
    add     rcx, rdx
    add     rax, rcx
```

**After ASM**: 4 independent dependency chains — OOO hardware can overlap all 4 adds.

---

## 4. Missed SIMD / Vectorization

### Symptom

Scalar loop over contiguous float/int array; no `xmm`/`ymm`/`zmm` registers in output:

```asm
.scalar_loop:
    movss   xmm0, [rdi + rax*4]   ; 1 float at a time
    addss   xmm0, xmm1
    movss   [rsi + rax*4], xmm0
    inc     rax
    cmp     rax, rdx
    jl      .scalar_loop
```

### Fix

Annotate for vectorization or use intrinsics:

```c
// C: align + restrict lets auto-vectorizer kick in
void add_scalar(float * restrict a, const float * restrict b, int n) {
    a = __builtin_assume_aligned(a, 32);
    b = __builtin_assume_aligned(b, 32);
    for (int i = 0; i < n; i++) a[i] += b[i];
}
```

```nasm
; Manual SSE2: process 4 floats at a time
.simd_loop:
    movaps  xmm0, [rdi + rax]
    addps   xmm0, [rsi + rax]
    movaps  [rdi + rax], xmm0
    add     rax, 16
    cmp     rax, rdx
    jl      .simd_loop
```

**After ASM**: `movaps`/`addps` or `vmovaps`/`vaddps` in loop body.

---

## 5. Memory Traffic

### Symptom

Repeated loads from the same address not hoisted:

```asm
.loop:
    mov     rax, [config + 8]   ; same address every iteration
    imul    rdi, rax
    inc     rsi
    cmp     rsi, rcx
    jl      .loop
```

### Fix

Load into register before the loop:

```c
const long stride = config->stride;   // hoist before loop
for (int i = 0; i < n; i++) out[i] = in[i] * stride;
```

```nasm
; Or in asm:
    mov     rax, [config + 8]   ; load once, before loop
.loop:
    imul    rdi, rax
    ...
```

**After ASM**: constant appears in a `mov` before the loop label, not inside.

---

## 6. Bad Instruction Selection

### Symptoms and replacements

```asm
; BAD: idiv for power-of-2
    idiv    rcx                     ; 20-40 cycle latency
; GOOD:
    sar     rax, 3                  ; divide by 8 (signed) — 1 cycle

; BAD: imul for small constant multiply
    imul    rdi, 9
; GOOD:
    lea     rdi, [rdi + rdi*8]      ; same, 1 cycle

; BAD: conditional branch for abs()
    test    rax, rax
    jns     .skip
    neg     rax
.skip:
; GOOD:
    mov     rcx, rax
    neg     rcx
    cmovs   rax, rcx                ; branchless

; BAD: loop-carried xor for known init
    xor     eax, eax (inside loop)
; GOOD: move outside
    xor     eax, eax (before loop)
```

---

## See Also

- `references/microarch.md` — execution port pressure and latency tables
