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
- Use `pxor xmm0, xmm0` (latency 1) not `xorps xmm0, xmm0` (latency 1 but FP unit) to zero FP registers

---

## Execution Units (x86-64, Zen3/Skylake-class)

| Unit | Operations |
|---|---|
| ALU (3–4 ports) | Integer add, sub, and, or, xor, cmp, test, lea |
| Shift | shl, shr, sar, rol (often 1 port) |
| Multiply | imul (1 port, 3 cycle latency on Zen) |
| Branch | Conditional/unconditional jumps |
| Load | mov from memory — 2 load units typical |
| Store | mov to memory — 1 store unit typical |
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

For current data: `llvm-mca` or [uops.info](https://uops.info/).

---

## Cache Line Effects

- **Cache line**: 64 bytes on x86-64 and ARM64
- A single cache line miss costs ~50–200 cycles (L3 latency) or ~100–300 cycles (DRAM)
- Accessing elements across cache line boundaries (false sharing, scattered access) destroys performance

### Patterns

```
Good:  sequential access  → hardware prefetcher covers you
Bad:   stride-N access (N > 8)  → misses every stride step
Bad:   scatter/gather without prefetch hints
```

### Prefetching (manual)

```nasm
prefetchnta [rsi + 256]   ; non-temporal hint, 4 lines ahead
prefetcht0  [rsi + 128]   ; L1 prefetch
```

Only effective if compute time per element exceeds memory latency.

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
- Indirect calls / virtual dispatch with many targets

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

---

## Loop Optimization Rules

1. **Align hot loops**: `align 16` or `align 32` before loop label
2. **Unroll 2–8x** to amortize loop overhead and expose ILP
3. **Peel the first/last iteration** to handle remainder cleanly without branching inside
4. **Hoist invariants** (loads, multiplications) before the loop
5. **Avoid function calls inside loops** — spill pressure + call overhead

---

## Measurement Tools

```bash
# Per-run hardware counters
perf stat -e cycles,instructions,L1-dcache-load-misses,branch-misses ./prog

# Static throughput analysis (no hardware required)
llvm-mca -mcpu=znver3 -iterations=200 < hot_loop.s

# Flame graph with perf
perf record -g ./prog && perf report
```

---

## External References

- [Agner Fog: Instruction Tables](https://www.agner.org/optimize/instruction_tables.pdf)
- [uops.info — instruction latency/throughput database](https://uops.info/)
- [llvm-mca documentation](https://llvm.org/docs/CommandGuide/llvm-mca.html)
- [Intel Optimization Reference Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)
