---
name: rust-performance
description: "Rust performance workflow: benchmark and profile first, identify hotspots, reduce allocations and contention, improve data layout, tune release profiles, and verify gains with repeatable evidence. Use only after you have a real Rust performance symptom, regression, or hotspot in `.rs` code."
license: MIT
compatibility: "Rust stable baseline. Tools: cargo, Criterion, cargo bench. Optional: cargo flamegraph, perf, heaptrack, dhat, samply, valgrind, rayon."
metadata:
  author: AeonDave
  version: "1.0"
---

# Rust Performance

This skill is about **measurement-first optimization** in Rust.

If the task is primarily code style, ownership, or API design, use `rust-patterns` first.

## When to activate

- Investigating latency, throughput, CPU, memory, or allocation regressions in Rust
- Benchmarking a hot path before and after a change
- Hunting down lock contention, slow async pipelines, or poor data layout
- Tuning release profiles or deciding whether parallelism actually helps

---

## Rules of engagement

- **Measure before changing code.** Hot takes are not hot paths.
- **Change one variable at a time.** Keep a stable baseline and compare before vs after.
- Fix **algorithm and data-structure issues first**, then allocations, then micro-optimizations.
- Optimize the code you can prove is hot, not the code that merely looks suspicious.
- Preserve correctness, readability, and maintainability; fast wrong code is still wrong.

---

## Workflow

1. **Make the problem measurable**
	- Define the symptom: latency, throughput, CPU, heap, alloc count, lock wait, or tail latency.
	- Add a benchmark or a reproducible workload before touching the implementation.

2. **Capture evidence**
	- CPU profile for time spent
	- Allocation / heap profile for churn and retention
	- Contention evidence for locks, channels, or task scheduling

3. **Analyze the bottleneck**
	- Confirm whether the problem is algorithmic, allocation-heavy, cache-unfriendly, or synchronization-heavy.
	- Inspect the hottest call paths before proposing fixes.

4. **Apply targeted fixes**
	- Pre-allocate, reuse buffers, remove needless clones, tighten data layout, or reduce synchronization.
	- Add parallelism only when the workload is large enough and coordination cost is justified.

5. **Verify the result**
	- Re-run the same benchmark/profile
	- Record the measurable improvement and ensure behavior is unchanged

## Resources

Load on demand:

- `references/measurement-workflow.md` — use when defining benchmarks, baselines, and release settings
- `references/profiling.md` — use when choosing CPU, heap, allocation, or contention profilers
- `references/allocations-and-data-layout.md` — use when the bottleneck smells like cloning, heap churn, or cache locality
- `references/concurrency-and-throughput.md` — use when evaluating Rayon, async throughput, locks, channels, or backpressure
