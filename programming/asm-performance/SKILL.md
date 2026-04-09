---
name: asm-performance
description: "Assembly performance optimization workflow: collect compiler-emitted ASM, classify bottlenecks with TMA, audit for codegen issues (bounds checks, register spills, dependency chains, missed vectorization, memory traffic, bad instruction selection, store-forwarding stalls, frontend pressure, data layout), apply one change at a time, measure, and report. Use after profiling confirms ASM is the bottleneck."
license: MIT
metadata:
  author: AeonDave
  version: "1.1"
compatibility: "x86-64 and ARM64 Linux/macOS/Windows. Tools: objdump, cargo-show-asm, perf stat, toplev, llvm-mca, uiCA."
---

# asm-performance

Systematic workflow for auditing and improving compiler-emitted assembly.

**Prerequisite**: profile first. Identify the hot function before examining ASM.

---

## Phase 1 — Collect ASM

### Rust (cargo-show-asm)

```bash
cargo install cargo-show-asm

# Full function — verbose
cargo asm --release --rust <crate> <module>::<function>

# LLVM IR + ASM side by side
cargo asm --release --llvm-ir <crate> <function>

# Filter to specific basic block
cargo asm --release <crate> <function> | grep -A30 '<label>:'
```

### C/C++ (multiple methods)

```bash
# objdump: post-compile disassembly
gcc -O2 -g -c hot.c -o hot.o
objdump -d -S -M intel hot.o > hot.asm

# Named function only
objdump -d -M intel hot.o | awk '/^[0-9a-f]+ <your_fn>:/,/^$/'

# Direct compiler ASM output (preserves source mapping)
gcc -O2 -S -masm=intel -fverbose-asm hot.c -o hot.s
clang -O2 -S -masm=intel -fno-asynchronous-unwind-tables hot.c -o hot.s
```

### Source-correlated profiling

```bash
# perf annotate — shows ASM with per-line cycle counts
perf record -g ./prog
perf annotate hot_fn

# Godbolt / Compiler Explorer: paste code at godbolt.org
# Use -O2 -march=native, compare output across gcc/clang versions
```

### Shared library / binary

```bash
objdump -d -M intel --demangle target/release/mybinary | grep -A200 '<hot_fn'
nm -S target/release/mybinary | grep hot_fn   # confirm symbol exists
```

---

## Phase 1.5 — Top-Down Classification (TMA)

Before ASM audit, classify where pipeline slots are wasted. This directs your audit effort.

### Quick TMA (Linux perf)

```bash
# Level 1 — which bucket dominates?
perf stat -M TopdownL1 ./bench

# Level 2 — drill into the dominant bucket
perf stat -M TopdownL2 ./bench
```

### toplev (pmu-tools, deeper analysis)

```bash
# Install
pip install pmu-tools
# Level 1–3 analysis
toplev --core S0-C0 -l3 -v --no-desc taskset -c 0 ./bench
```

### TMA categories and what they mean

| L1 Category | Meaning | Typical ASM Symptoms |
|---|---|---|
| **Retiring** | Useful work. Target: as high as possible | — |
| **Bad Speculation** | Branch mispredictions, machine clears | Many conditional jumps, indirect calls |
| **Frontend Bound** | Instruction fetch/decode starvation | Code too large for µop cache, misaligned loops |
| **Backend Bound** | Execution or memory stalls | Dependency chains, cache misses, port pressure |

At L2, Backend splits into **Memory Bound** vs **Core Bound**:
- Memory Bound → focus on data layout, prefetching, NT stores, TLB
- Core Bound → focus on dependency chains, port pressure, instruction selection

> Load `references/advanced-strategies.md` for detailed TMA-guided remediation.

---

## Phase 2 — Audit

Scan the collected ASM for the 9 issue categories. Mark each instance.

| # | Category | Signal |
|---|---|---|
| 1 | **Panic / bounds paths** | `call core::panicking` / `ud2` reachable from hot loop |
| 2 | **Register spills** | `mov [rsp+N], reg` inside loop body; non-constant stack depth |
| 3 | **Dependency chains** | Back-to-back instructions reading/writing same register with no ILP |
| 4 | **Missed SIMD** | Scalar loop over contiguous data; no `xmm`/`ymm` in output |
| 5 | **Memory traffic** | Redundant loads/stores to same address; no register hoisting |
| 6 | **Bad instruction selection** | `idiv`/`div` for power-of-2; `imul` for `lea`-friendly constants |
| 7 | **Store-forwarding stalls** | Store followed by load at overlapping-but-mismatched width/offset |
| 8 | **Frontend pressure** | Large code in loop, `nop` padding, function calls bloating i-cache |
| 9 | **Data layout inefficiency** | Scattered field access in AoS; wasted cache-line bandwidth |

> Load `references/codegen-issues.md` for before/after ASM patterns for each category.

### Audit checklist

For each issue found, record:

```
CATEGORY: [1-9]
LOCATION: symbol + offset or line
SYMPTOM: what you see in the ASM
TMA LEVEL: which TMA bucket flagged this (if available)
ROOT CAUSE: why the compiler made this choice
PLAN: specific change (source or inline asm constraint)
```

---

## Phase 3 — Forge Loop

One change per iteration. Never batch.

```
1. Make ONE change (source, hint, attribute, or asm constraint)
2. Collect new ASM (Phase 1 command)
3. Diff old vs new ASM
4. Measure: perf stat / criterion / RDTSC
5. Accept or revert — see decision table
6. Repeat
```

### Diff workflow

```bash
# Save baseline
cargo asm --release <crate> <fn> > asm_before.s

# After change
cargo asm --release <crate> <fn> > asm_after.s

diff asm_before.s asm_after.s
```

### Decision table

| Observation | Action |
|---|---|
| Issue gone, benchmark faster | Accept — commit |
| Issue gone, benchmark same | Accept for code size; investigate if cycles expected to drop |
| Issue gone, benchmark **slower** | Revert — compiler knew something you don't |
| Issue persists | Try next approach (attribute, manual hint, intrinsic) |
| New issue introduced | Revert — net negative if it adds a different problem |
| `ud2` / panic path visible | Revert or add explicit bounds check |

---

## Phase 4 — Measure

### Linux — perf stat

```bash
perf stat -e cycles,instructions,cache-misses,branch-misses ./bench
perf stat -r 5 ./bench          # 5 runs, aggregate

# TMA-guided — drill into specific counters after classification
perf stat -e mem_load_retired.l3_miss,mem_load_retired.fb_hit ./bench  # memory bound
perf stat -e frontend_retired.dsb_miss,icache_64b.iftag_miss ./bench   # frontend bound
```

### Rust — criterion

```rust
// In benches/
use criterion::{black_box, criterion_group, criterion_main, Criterion};
fn bench_hot(c: &mut Criterion) {
  let input = black_box(/* build input */);
  c.bench_function("hot_fn", |b| b.iter(|| hot_fn(black_box(input))));
}
criterion_group!(benches, bench_hot);
criterion_main!(benches);
```

### Static analysis — llvm-mca

```bash
# Basic throughput and port pressure
llvm-mca -mcpu=znver3 -iterations=100 < snippet.s

# Bottleneck analysis — detailed stall report
llvm-mca -mcpu=skylake -bottleneck-analysis -iterations=200 < snippet.s
```

### Static analysis — uiCA (more accurate for recent Intel)

```bash
# uiCA: simulation-based, tracks µop cache and frontend effects
pip install uiCA
uiCA snippet.s -arch SKL   # Skylake
uiCA snippet.s -arch ICL   # Ice Lake
```

> uiCA is more accurate than llvm-mca for Intel cores (MAPE ~26% vs ~33%).
> Use llvm-mca for AMD Zen targets where uiCA lacks models.

### C/C++ — Google Benchmark

```cpp
#include <benchmark/benchmark.h>
static void BM_HotFn(benchmark::State& state) {
  auto input = /* setup */;
  for (auto _ : state) benchmark::DoNotOptimize(hot_fn(input));
}
BENCHMARK(BM_HotFn);
```

---

## Phase 5 — Report

```
== ASM Optimization Report ==
Function: <fully-qualified name>
Date:     YYYY-MM-DD

TMA classification: Backend Bound > Memory Bound > DRAM Bound (67%)

Baseline (cycles/iter): N
Final    (cycles/iter): N
Delta:                  -N%

Changes applied:
  1. [CATEGORY] Description of change — effect on ASM
  2. ...

Issues NOT fixed (and why):
  - [CATEGORY] Description — blocked by <reason>

Remaining hotspots: <next function to examine>
```

---

## Common Source-Level Hints

### Rust

```rust
// Disable bounds checks in hot loop
unsafe { *slice.get_unchecked(i) }

// Use chunks_exact to eliminate bounds checks and enable vectorization
for chunk in data.chunks_exact(4) { /* compiler knows length = 4 */ }

// Force inline
#[inline(always)]
fn hot_fn() { ... }

// Target-specific codegen
#[target_feature(enable = "avx2")]
unsafe fn hot_fn_avx2() { ... }

// PGO: build with profile
// RUSTFLAGS="-Cprofile-generate=/tmp/pgo" cargo build --release
// RUSTFLAGS="-Cprofile-use=/tmp/pgo/merged.profdata" cargo build --release
```

### C/C++

```c
// Restrict pointer aliasing — enables vectorization
void process(float * restrict dst, const float * restrict src, int n);

// Assume aligned — enables aligned SIMD loads
__builtin_assume_aligned(ptr, 32);

// Unreachable branch elimination
if (n < 0) __builtin_unreachable();

// Force vectorization width (GCC/Clang)
#pragma GCC ivdep                    // no loop-carried dependencies
#pragma clang loop vectorize_width(8)
#pragma clang loop unroll_count(4)

// PGO: -fprofile-generate → run → -fprofile-use
// LTO: -flto — enables cross-module inlining and devirtualization

// Non-temporal store hint for write-only streaming patterns
_mm_stream_si128((__m128i*)dst + i, val);  // bypasses cache
```

### Data Layout for Performance

```c
// BAD: Array of Structs — 75% wasted bandwidth reading one field
struct Particle { float x, y, z, mass; };
struct Particle particles[N];
for (i = 0; i < N; i++) sum += particles[i].mass;  // stride 16, uses 4 of 64 bytes

// GOOD: Struct of Arrays — contiguous, vectorizable
struct Particles { float x[N]; float y[N]; float z[N]; float mass[N]; };
for (i = 0; i < N; i++) sum += particles.mass[i];   // stride 4, full cache line usage
```

### ARM64-specific

```c
// NEON intrinsics
#include <arm_neon.h>
float32x4_t va = vld1q_f32(a + i);   // load 4 floats
float32x4_t vc = vfmaq_f32(vc, va, vb);  // fused multiply-add

// SVE intrinsics (scalable, works across different vector widths)
#include <arm_sve.h>
svfloat32_t va = svld1_f32(pg, a + i);
```

---

## ARM64 Performance Notes

ARM64 in-order or narrow OOO cores (Cortex-A55, Cortex-A510) are latency-sensitive:
- Instruction scheduling order matters more than on x86-64
- Interleave memory and compute to hide load latency (4+ cycles)
- Use modulo scheduling: overlap iterations to break dependency chains

Wide OOO cores (Neoverse V2, Apple M-series, Cortex-X4):
- Similar to x86-64 — dependency chains and port pressure dominate
- NEON fixed 128-bit, SVE/SVE2 scales 128–2048 bits per implementation
- `PRFM PLDL1KEEP, [x0, #256]` — software prefetch equivalent
- Avoid `ins` (element insert) in hot loops: 5+ cycle latency on many cores

> Load `references/advanced-strategies.md` for modulo scheduling walkthrough and ARM64 pipeline details.

---

## Resources

- `references/codegen-issues.md` — before/after ASM patterns for all 9 issue categories
- `references/microarch.md` — ILP, execution units, cache line effects, branch prediction rules
- `references/advanced-strategies.md` — TMA methodology, data layout, NT stores, prefetching, ARM64 optimization
