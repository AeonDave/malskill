# Advanced Performance Strategies

Deep-dive strategies referenced from Phase 1.5 (TMA) and the expanded audit categories.

---

## TMA-Guided Remediation

After classifying the bottleneck with `perf stat -M TopdownL1` or `toplev`, use this table to focus effort:

### Frontend Bound

| L2/L3 Sub-category | Likely Cause | Remediation |
|---|---|---|
| Fetch Latency > 10% | i-cache misses, iTLB misses | Reduce code size; use PGO/LTO; 2M huge pages for code |
| Fetch Bandwidth | Instruction decode limits | Keep hot loops < 32 bytes for DSB; align loop entry |
| DSB Switches | Toggling between DSB and MITE decode | Avoid crossing 32-byte boundaries mid-loop |

### Backend Bound — Memory

| L3 Sub-category | Likely Cause | Remediation |
|---|---|---|
| L1 Bound | Store-forwarding stalls, cache-line splits | Fix store/load width mismatch; align data |
| L2 Bound | Working set exceeds L1 | Software prefetch, reduce data footprint |
| L3 Bound | Working set exceeds L2 | Tiling / blocking, SoA layout |
| DRAM Bound | Working set exceeds LLC | NT stores, huge pages, reduce bandwidth demand |
| Store Bound | Store buffer full | Reduce store count; batch writes |

### Backend Bound — Core

| L3 Sub-category | Likely Cause | Remediation |
|---|---|---|
| Divider | `div`/`idiv` or FP divide | Replace with shifts/reciprocals/Newton-Raphson |
| Ports Utilization | Imbalanced port pressure | Redistribute instructions across ports (lea vs imul) |

### Bad Speculation

| L2 Sub-category | Likely Cause | Remediation |
|---|---|---|
| Branch Mispredicts | Unpredictable data-dependent branches | cmov/csel, SIMD masking, sort input if possible |
| Machine Clears | Memory ordering violations, self-modifying code | Fix aliasing, avoid store/load overlaps |

---

## Non-Temporal (Streaming) Stores

When writing large buffers that won't be read soon, NT stores bypass the cache hierarchy — avoiding cache pollution and write-allocate overhead.

### When to use

- Write-only patterns: initializing arrays, writing output buffers
- Working set much larger than LLC (streaming write > 2× LLC size)
- Measured DRAM Bound in TMA and stores dominate

### When NOT to use

- Data will be read again shortly (NT evicts from cache immediately)
- Small buffers (< LLC size) — normal stores with write-back are faster
- Mixed read-write patterns — NT stores don't benefit from cache reuse

### x86-64

```nasm
; Streaming store — bypasses cache, writes directly to memory
vmovntps [rdi + rax], ymm0        ; 256-bit NT store (AVX)
vmovntdq [rdi + rax], ymm0        ; integer NT store
movnti   [rdi + rax], eax         ; scalar 32-bit NT store

; REQUIRED: sfence after NT store sequence before any read
sfence

; Enhanced REP MOVSB (ERMSB) — uses NT stores internally for large copies
; Check CPUID: ERMS bit (EAX=7, ECX=0 → EBX bit 9)
rep movsb                          ; for large copies, hardware uses NT internally
```

### ARM64

```asm
; STNP — store pair, non-temporal hint
STNP    q0, q1, [x0]              ; 256-bit NT store (2×128 NEON)
STNP    x2, x3, [x0, #16]        ; 128-bit NT store (2×64 GP)

; DC ZVA — zero a full cache line without read-for-ownership
DC      ZVA, x0                    ; zero 64 bytes at [x0], no cache fill
```

### Source-level

```c
// SSE/AVX intrinsics
_mm256_stream_ps(dst + i, val);    // vmovntps
_mm_stream_si128((__m128i*)dst, v); // movntdq

// After streaming stores, fence before reads
_mm_sfence();

// C11/C++11 with compiler support
// GCC: __builtin_nontemporal_store(val, ptr)
```

---

## Software Prefetching Strategy

Hardware prefetchers handle sequential and simple-stride patterns. Software prefetch for:
- Irregular access patterns (hash tables, pointer chasing, B-trees)
- Known-ahead-of-time random access (e.g., gather from precomputed indices)

### Distance calculation

```
prefetch_distance = memory_latency × loop_throughput
                  = ~200 cycles × 1 iteration/cycle = 200 iterations ahead

# In cache lines:
prefetch_lines_ahead = prefetch_distance × bytes_per_iter / 64
```

### Patterns

```c
// Prefetch for pointer chasing (linked list traversal)
for (node_t *n = head; n; n = n->next) {
    if (n->next) __builtin_prefetch(n->next->next, 0, 1);  // 2 hops ahead
    process(n);
}

// Prefetch for indirect array access
for (int i = 0; i < n; i++) {
    __builtin_prefetch(&data[indices[i + 8]], 0, 3);  // 8 iterations ahead
    sum += data[indices[i]];
}
```

### ARM64 prefetch

```asm
; Loop with prefetch 4 cache lines ahead
PRFM    PLDL1KEEP, [x0, #256]     ; temporal read prefetch into L1
PRFM    PLDL2KEEP, [x0, #512]     ; prefetch into L2
PRFM    PSTL1KEEP, [x1, #256]     ; prefetch for write
```

### Anti-patterns

- Prefetching sequential access — hardware prefetcher already handles this
- Prefetching too far ahead — data evicted before use
- Prefetching too close — arrives after the load miss stalls
- Prefetching in very short loops — overhead exceeds benefit

---

## Loop Tiling / Blocking

For operations on large 2D arrays (matrix multiply, convolution, stencils), process data in tiles that fit in L1/L2 cache:

```c
// Before: column access pattern causes cache misses every iteration
for (int j = 0; j < N; j++)
    for (int i = 0; i < N; i++)
        C[i][j] += A[i][k] * B[k][j];

// After: tiled — each tile fits in L1 cache
#define TILE 64  // 64×64 doubles = 32K → fits in 32K L1d
for (int jj = 0; jj < N; jj += TILE)
  for (int ii = 0; ii < N; ii += TILE)
    for (int j = jj; j < jj+TILE; j++)
      for (int i = ii; i < ii+TILE; i++)
        C[i][j] += A[i][k] * B[k][j];
```

Tile size selection:
- L1d: 32–48 KB → tile ≈ 64×64 floats (16 KB working set)
- L2: 256 KB–1 MB → outer tile for L2, inner tile for L1
- Measure: if L1 miss rate drops significantly, tiling is working

---

## Modulo Scheduling (ARM64 / hand-written ASM)

For loops with multi-step dependency chains and no inter-iteration dependencies, overlap iterations to hide latency.

### Concept

Given a loop with steps A, B, C, D:
```
; Unrolled but serialized (dependency chain limits throughput):
A₀ B₀ C₀ D₀  A₁ B₁ C₁ D₁  A₂ B₂ C₂ D₂ ...

; Modulo scheduled (overlap iterations):
A₀
A₁ B₀
A₂ B₁ C₀
A₃ B₂ C₁ D₀     ← steady state: all functional units busy
A₄ B₃ C₂ D₁
...
```

### ARM64 example — interleave load/compute/store

```asm
; Prologue: prime the pipeline
LDR     q0, [x0], #16
LDR     q1, [x0], #16
FMUL    v4.4s, v0.4s, v2.4s      ; compute iteration 0

; Steady state:
.loop:
    LDR     q0, [x0], #16         ; load iteration N+2
    STR     q4, [x1], #16         ; store iteration N
    FMUL    v4.4s, v1.4s, v2.4s   ; compute iteration N+1
    LDR     q1, [x0], #16         ; load iteration N+3
    STR     q4, [x1], #16         ; store iteration N+1
    FMUL    v4.4s, v0.4s, v2.4s   ; compute iteration N+2
    SUBS    x3, x3, #4
    B.GT    .loop

; Epilogue: drain remaining
```

Key: memory operations and compute operations use different pipeline units — interleaving keeps both busy.

---

## SIMD Width Selection Strategy

### x86-64 decision tree

```
1. Is AVX-512 available AND loop is large (> 100 iterations)?
   YES → Use AVX-512; accept ~100 MHz clock drop on some Intel parts
   NO  ↓
2. Is AVX2 available?
   YES → Default choice. Best throughput/compatibility balance.
   NO  ↓
3. Use SSE4.1/SSE2 — still 4× throughput over scalar for float

Always:
- Runtime dispatch: check CPUID once, select function pointer
- vzeroupper after AVX code returning to SSE callers
- Test on target hardware — simulated frequencies differ from real throttling
```

### ARM64 decision tree

```
1. Is SVE/SVE2 available?
   YES → Use SVE intrinsics (scalable, width-agnostic)
   NO  ↓
2. Use NEON (128-bit fixed) — always available on AArch64
```

SVE advantage: same binary runs on 128-bit (Graviton3), 256-bit (Graviton4), or 512-bit implementations without recompilation.

---

## Profile-Guided Optimization (PGO)

PGO uses runtime profiles to guide compiler decisions. Typical 10–30% speedup for complex code.

### What PGO optimizes

| Optimization | How it helps |
|---|---|
| Basic block reordering | Cold paths moved away; hot path falls through linearly |
| Function inlining decisions | Inline only actually-hot callees |
| Branch prediction hints | Compiler annotates likely/unlikely based on real data |
| Register allocation | Better allocation for actually-hot variables |
| Vectorization decisions | Knows actual trip counts → better unroll/vectorize choices |

### Workflow

```bash
# GCC/Clang
gcc -O2 -fprofile-generate -o prog_instr prog.c
./prog_instr <representative workload>
gcc -O2 -fprofile-use -o prog_opt prog.c

# Rust
RUSTFLAGS="-Cprofile-generate=/tmp/pgo" cargo build --release
./target/release/prog <workload>
llvm-profdata merge -o /tmp/pgo/merged.profdata /tmp/pgo
RUSTFLAGS="-Cprofile-use=/tmp/pgo/merged.profdata" cargo build --release
```

Combine with LTO (`-flto` / `lto = "fat"`) for best results — LTO enables cross-module inlining that PGO can then further optimize.

---

## See Also

- `codegen-issues.md` — before/after ASM patterns for audit categories
- `microarch.md` — ILP, execution units, cache hierarchy, branch prediction
