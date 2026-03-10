---
name: asm-performance
description: "Assembly performance optimization workflow: collect compiler-emitted ASM, audit for codegen issues (bounds checks, register spills, dependency chains, missed vectorization, memory traffic, bad instruction selection), apply one change at a time, measure, and report. Use after profiling confirms ASM is the bottleneck."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
compatibility: "x86-64 Linux/macOS. Tools: objdump (binutils), cargo-show-asm (Rust), perf stat (Linux), llvm-mca."
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

### C/C++ (objdump)

```bash
gcc -O2 -g -c hot.c -o hot.o
objdump -d -S -M intel hot.o > hot.asm

# Named function only
objdump -d -M intel hot.o | awk '/^[0-9a-f]+ <your_fn>:/,/^$/'
```

### Shared library / binary

```bash
objdump -d -M intel --demangle target/release/mybinary | grep -A200 '<hot_fn'
nm -S target/release/mybinary | grep hot_fn   # confirm symbol exists
```

---

## Phase 2 — Audit

Scan the collected ASM for the 6 issue categories. Mark each instance.

| # | Category | Signal |
|---|---|---|
| 1 | **Panic / bounds paths** | `call core::panicking` / `ud2` reachable from hot loop |
| 2 | **Register spills** | `mov [rsp+N], reg` inside loop body; non-constant stack depth |
| 3 | **Dependency chains** | Back-to-back instructions reading/writing same register with no ILP |
| 4 | **Missed SIMD** | Scalar loop over contiguous data; no `xmm`/`ymm` in output |
| 5 | **Memory traffic** | Redundant loads/stores to same address; no register hoisting |
| 6 | **Bad instruction selection** | `idiv`/`div` for power-of-2; `imul` for `lea`-friendly constants |

> Load `references/codegen-issues.md` for before/after ASM patterns for each category.

### Audit checklist

For each issue found, record:

```
CATEGORY: [1-6]
LOCATION: symbol + offset or line
SYMPTOM: what you see in the ASM
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

### Cycle-accurate — llvm-mca

```bash
llvm-mca -mcpu=znver3 -iterations=100 < snippet.s
# Reports: throughput, latency, port pressure
```

---

## Phase 5 — Report

```
== ASM Optimization Report ==
Function: <fully-qualified name>
Date:     YYYY-MM-DD

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

```rust
// Rust: disable bounds checks in hot loop
unsafe { *slice.get_unchecked(i) }

// Rust: hint for loop unroll
#[allow(clippy::all)]
let mut i = 0;
while i < n { /* body */ i += 1; }

// Rust: force inline
#[inline(always)]
fn hot_fn() { ... }

// C: restrict pointer aliasing
void process(float * restrict dst, const float * restrict src, int n);

// C: assume aligned
__builtin_assume_aligned(ptr, 32);
```

---

## Resources

- `references/codegen-issues.md` — before/after ASM patterns for all 6 issue categories
- `references/microarch.md` — ILP, execution units, cache line effects, branch prediction rules
