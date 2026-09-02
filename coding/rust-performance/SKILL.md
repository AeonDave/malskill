---
name: rust-performance
description: "Rust performance workflow: benchmark and profile first, identify hotspots, reduce allocations and contention, improve data layout, tune release profiles, and verify gains with repeatable evidence. Use only after you have a real Rust performance symptom, regression, or hotspot in `.rs` code."
license: MIT
compatibility: "Rust stable baseline. Tools: cargo, Criterion, cargo bench, divan, iai-callgrind. Optional: cargo flamegraph, samply, perf, heaptrack, dhat, valgrind, rayon, cargo-pgo, mimalloc."
metadata:
  author: AeonDave
  version: "1.3"
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

## Outcome expectations

- Performance claims are backed by reproducible measurements.
- Profile data points clearly to one or few prioritized hotspots.
- Fixes are incremental and attributable (one change, one measurement delta).
- Correctness and behavior remain unchanged after optimization.

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

---

## Symptom to first tool mapping

- High CPU or low throughput -> Criterion + CPU profiler / flamegraph
- Memory growth or heap churn -> allocation/heap profiler (`dhat`, `heaptrack`)
- Latency spikes with shared state -> contention and lock analysis
- Async scheduling inefficiency -> runtime-aware tracing and task instrumentation
- CI performance regressions -> deterministic instruction-count benchmarking (`iai-callgrind`)
- Shipping a binary that is already profile-tuned and needs final codegen/build tuning -> build tuning (`compiler-and-build-tuning.md`)

## Resources

Load on demand:

- `references/measurement-workflow.md` — use when defining benchmarks, baselines, and release settings
- `references/profiling.md` — use when choosing CPU, heap, allocation, or contention profilers
- `references/allocations-and-data-layout.md` — use when the bottleneck smells like cloning, heap churn, or cache locality
- `references/concurrency-and-throughput.md` — use when evaluating Rayon, async throughput, locks, channels, backpressure, or false sharing
- `references/compiler-and-build-tuning.md` — use when release-profile knobs are not enough, or when tuning `-C target-cpu`, PGO, or BOLT for a final binary
