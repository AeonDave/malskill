# Microarchitecture Reference

Core principles for reasoning about assembly performance at the CPU level.

---

## Instruction-Level Parallelism (ILP)

Modern out-of-order CPUs can execute multiple independent instructions per cycle.
Dependency chains kill ILP.

### The critical path rule

The minimum execution time of a sequence is:
- `max(sum of loop-carried latencies, throughput limit based on port pressure)`

If a loop has a 4-cycle dependency chain and the CPU can retire 4 instructions/cycle, the bottleneck is the chain — not throughput.

### Breaking dependency chains

- Use multiple accumulators (see `codegen-issues.md` §3)
- Interleave unrelated instructions between dependent ones
- Use `xor reg, reg` to break dependencies — recognized as zero-idiom, zero latency (both Intel and AMD)
- `pxor xmm0, xmm0` and `vpxor ymm0, ymm0, ymm0` are zero-idioms — not dispatched to execution units

---

## Execution Units (x86-64, Zen3/Skylake-class)

| Unit | Operations |
|---|---|
| ALU (3–4 ports) | Integer add, sub, and, or, xor, cmp, test, lea |
| Shift | shl, shr, sar, rol (often 1 port) |
| Multiply | imul (1 port, 3 cycle latency on Zen) |
| Branch | Conditional/unconditional jumps |
| Load | mov from memory — 2 load units typical |
| Store | mov to memory — 1 store unit typical (Zen4/Golden Cove: 2 stores/cycle) |
| FP/SIMD | addps, mulps, etc. — separate from integer ALU |
| Divide | div/idiv — not pipelined, 20–90 cycles |

**Key insight**: `lea` uses ALU, not multiply unit. `imul` ties up multiply unit and has 3-cycle latency. Prefer `lea` for 2-operand address expressions.

---

## Latency vs Throughput

- **Latency**: cycles before the result is available for the next dependent instruction
- **Throughput** (reciprocal): how often the instruction can start (e.g., 0.5 = 2 per cycle)

| Instruction | Latency | Throughput |
|---|---|---|
| `add`/`sub`/`or` | 1 | 0.25 |
| `imul r64, r64` | 3 | 1 |
| `lea` (2 ops) | 1 | 0.5 |
| `div r64` | 35–90 | —  |
| `movaps` | 1 | 0.33 |
| `addps` | 4 | 0.5 |
| `mulps` | 4 | 0.5 |
| `vdivps` | 11–24 | 5–11 |
| `popcnt` | 3 | 1 |
| `vfmadd*ps` (FMA) | 4 | 0.5 |

For current data: `llvm-mca`, [uops.info](https://uops.info/), or `uiCA`.

---

## Frontend Pipeline

### µop cache (DSB) — Intel

- Decoded Stream Buffer caches up to ~1536 µops (Skylake) or ~4096 (Golden Cove)
- A loop that fits in the DSB avoids instruction decode overhead every iteration
- If a loop exceeds DSB capacity → falls back to MITE (legacy decode) → Frontend Bound
- Each DSB set maps to a 32-byte region of code; crossing 32-byte boundaries wastes DSB entries

### Loop Stream Detector (LSD)

- Small loops (~64 µops) may lock into the LSD and replay from a buffer
- Disabled on some microarchitectures due to errata (Skylake, some Zen)

### Instruction fetch

- Fetches 16 bytes/cycle (Intel) or 32 bytes/cycle (Zen4)
- Long instructions (10+ byte VEX/EVEX encodings) reduce fetch throughput
- Misaligned loop entry can split the first fetch across two cache lines

### Mitigation

- Keep hot loops under ~64 µops (LSD) or ~500 µops (DSB)
- Align loop entry to 32 bytes (but only if padding cost ≤ 10 bytes)
- Use PGO/LTO to optimize code layout and eliminate cold-path bloat

---

## Store Buffer and Forwarding

The store buffer holds pending writes before they commit to cache. It enables store-to-load forwarding — a load reads from a pending store without waiting for cache write.

### Forwarding rules

- **Succeeds** if load address and width match the most recent store exactly
- **Fails** (stall ~10–15 cycles) if load is narrower, wider, or misaligned vs the store
- **Fails** if load spans two pending stores

### Common pitfalls

- Union type punning: writing `uint64_t`, reading `uint32_t`
- Stack frame reuse: compiler spills a 64-bit value, reloads a 32-bit portion
- Struct packing with mixed-width bitfields

---

## Cache Line Effects

- **Cache line**: 64 bytes on x86-64 and ARM64
- A single cache line miss costs ~4 cycles (L1), ~12 cycles (L2), ~40 cycles (L3), ~100–300 cycles (DRAM)
- Accessing elements across cache line boundaries (false sharing, scattered access) destroys performance

### False sharing

Two threads writing to different variables in the same 64-byte cache line cause constant invalidation bouncing:

```c
struct Bad  { int counter_a; int counter_b; };            // same cache line
struct Good { alignas(64) int counter_a; alignas(64) int counter_b; }; // separate lines
```

### Alignment penalties

| Access type | Within cache line | Crossing cache line | Crossing 4K page |
|---|---|---|---|
| Scalar (mov) | 0 cycles penalty | ~5× slower | ~20× slower |
| SIMD (vmovaps) | 0 | Fault if aligned variant | ~5× slower |
| SIMD (vmovups) | 0 | ~2-6 cycles | ~10× slower |

### Prefetching (manual)

```nasm
; x86-64
prefetchnta [rsi + 256]   ; non-temporal hint — L1 only, evict early
prefetcht0  [rsi + 128]   ; temporal — bring into all cache levels

; ARM64
PRFM PLDL1KEEP, [x0, #256]   ; prefetch read, L1, keep (temporal)
PRFM PLDL1STRM, [x0, #256]   ; prefetch read, L1, streaming (non-temporal)
```

Rules:
- Only effective if compute time per element exceeds memory latency
- Prefetch 2–4 cache lines ahead (128–256 bytes at typical loop body sizes)
- Over-prefetching evicts useful data — measure before adding

---

## TLB and Page Walks

Translation Lookaside Buffer caches virtual-to-physical address mappings.

| Level | Entries (typical) | Miss cost |
|---|---|---|
| L1 dTLB | 64 entries (4K pages) | ~7 cycles |
| L2 TLB | 1536–2048 entries | ~20 cycles |
| Full page walk | — | ~100+ cycles (touches 4 levels of page table) |

### When TLB matters

- Working set > 256 KB (64 pages × 4K) → starts missing L1 dTLB
- Scattered access across many 4K pages (hash tables, linked lists, B-trees)
- Large array access: N elements × stride > L2 TLB capacity → page walk storm

### Mitigation

- Use 2M huge pages: 1 TLB entry covers 2M instead of 4K → 512× less TLB pressure
  - Linux: `madvise(addr, len, MADV_HUGEPAGE)` or `mmap` with `MAP_HUGETLB`
- Keep hot data contiguous — SoA layout, arena allocation
- Pool allocations to reduce page scatter

---

## Branch Prediction

Modern CPUs have ~95%+ prediction accuracy for regular patterns. Misprediction costs 15–20 cycles.

### When branches are free / cheap

- Loop counter (always predicted taken until last iteration)
- `if` at start of function for early exit (cold path)
- Sorted-input dependent branches (pattern stabilizes)

### When branches are expensive

- Data-dependent branches with random input
- Branches inside tight loops (SIMD reduction, string scan)
- Indirect calls / virtual dispatch with many targets (>4 targets overwhelms BTB)

### Branchless alternatives

Use `cmov`, `csel` (ARM64), `set*`, or bit tricks:

```nasm
; x = (a > b) ? a : b  →  max
cmp     rdi, rsi
cmovle  rdi, rsi
mov     rax, rdi

; Clamp to [0, 255] — branchless
xor     ecx, ecx
cmp     eax, 255
cmovg   eax, [rip + .val_255]
cmovl   eax, ecx
```

**Caveat**: `cmov` has a data dependency on both operands — both paths execute. If the "wrong" path involves an expensive load, a branch may be faster (predictable case only).

---

## Loop Optimization Rules

1. **Align hot loops**: `.p2align 5,,10` — align to 32 only if padding ≤ 10 bytes
2. **Unroll 2–8×** to amortize loop overhead and expose ILP
3. **Peel the first/last iteration** to handle remainder cleanly without branching inside
4. **Hoist invariants** (loads, multiplications) before the loop
5. **Avoid function calls inside loops** — spill pressure + call overhead
6. **Keep loop body < 64 µops** for LSD or < 500 µops for DSB (Intel)
7. **Use counted loops** (`dec rcx; jnz`) — predicted perfectly unlike data-dependent exits
8. **Strength reduction**: replace `imul` with `add` for loop-incremented products

---

## Measurement Tools

### Hardware counter profiling

```bash
# Per-run counters
perf stat -e cycles,instructions,L1-dcache-load-misses,branch-misses ./prog

# TMA top-down classification (Linux perf, Intel)
perf stat -M TopdownL1 ./prog
perf stat -M TopdownL2 ./prog

# toplev — deeper TMA with drill-down
toplev --core S0-C0 -l3 -v --no-desc taskset -c 0 ./prog
```

### Static throughput analysis

```bash
# llvm-mca — AMD Zen and LLVM targets
llvm-mca -mcpu=znver3 -iterations=200 < hot_loop.s
llvm-mca -bottleneck-analysis -mcpu=skylake < hot_loop.s

# uiCA — Intel simulation-based (more accurate for Intel cores)
uiCA hot_loop.s -arch ICL

# OSACA — portable, supports x86 and ARM64
osaca --arch ZEN3 hot_loop.s
```

### Sampling and visualization

```bash
# Flame graph with perf
perf record -g ./prog && perf report

# Source-annotated hotspots
perf annotate hot_fn
```

---

## ARM64 Microarchitecture Notes

ARM64 cores vary more widely than x86-64. Key differences:

| Feature | Cortex-A55/A510 (little) | Neoverse V2 / Cortex-X4 (big) | Apple M-series |
|---|---|---|---|
| Pipeline | In-order, 8-stage | OOO, 10+ wide | OOO, 16+ wide |
| ILP sensitivity | Very high | Moderate | Low (deep OOO) |
| SIMD | NEON 128-bit | NEON + SVE/SVE2 | NEON 128-bit |
| Load latency | 3–4 cycles | 4–5 cycles | 3 cycles |

- `ins` (element insert into vector) has 5+ cycle latency on many cores — avoid in hot loops
- ARM64 has 32 GP registers vs x86-64's 16 — register spills are rarer
- SVE auto-vectorization is width-agnostic; write once, runs at implementation's VL (128–2048 bits)

---

## External References

- [Agner Fog: Instruction Tables](https://www.agner.org/optimize/instruction_tables.pdf)
- [Agner Fog: Microarchitecture Manual](https://www.agner.org/optimize/microarchitecture.pdf)
- [uops.info — instruction latency/throughput database](https://uops.info/)
- [uiCA — accurate Intel code analyzer](https://uica.uops.info/)
- [llvm-mca documentation](https://llvm.org/docs/CommandGuide/llvm-mca.html)
- [Intel Optimization Reference Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)
- [Top-Down Microarchitecture Analysis (TMA) — easyperf.net](https://easyperf.net/blog/2019/02/09/Top-Down-performance-analysis-methodology)
- [AWS Graviton — ARM64 Assembly Optimization](https://github.com/aws/aws-graviton-getting-started/blob/main/arm64-assembly-optimization.md)
