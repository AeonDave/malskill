---
name: golang-performance
description: "Go performance workflow: benchmark and profile (pprof/trace), identify hotspots, reduce allocations/GC and contention, and verify improvements with repeatable measurement. Use only after you have evidence the Go code is the bottleneck."
license: MIT
compatibility: "Go 1.22+ (guidance baseline). Tools: go test, go tool pprof, go tool trace. Optional: benchstat (golang.org/x/perf/cmd/benchstat), perf (Linux)."

metadata:
  author: AeonDave
  version: "1.1"
---

# Go Performance

This skill is about **measurement-first optimization** in Go.

## When to activate

Use this skill when you need to:

- Confirm a performance regression (latency/throughput/CPU/memory)
- Identify hot paths with pprof (CPU / heap / mutex / block)
- Reduce allocations and GC pressure in a measured hotspot
- Fix contention (mutex, scheduler, channel backpressure)
- Validate improvements with benchmarks and repeatable runs

If you need general idioms and patterns (not measurement), use `golang-patterns`.

---

## Rules of engagement

- **Profile before optimizing.** A fast guess beats a slow change.
- **Change one thing at a time.** Measure after each change.
- **Keep a baseline.** Every claim should have “before vs after”.
- **Don’t optimize the cold path.** Make the hot path boring.

---

## Workflow

1. **Make it measurable**
   - Add a benchmark (or a reproducible load test) for the suspected hotspot.
   - Run multiple iterations; record mean + variance.

2. **Capture evidence**
   - CPU profile for time
   - Heap/allocs profile for memory
   - Mutex/block profiles for contention
   - Trace when the scheduler / GC behavior matters

3. **Analyze before changing code**
   - Identify top offenders (`top`, `top -cum`)
   - Inspect annotated source (`list`)
   - Confirm whether you are bound by CPU, allocations, syscalls, or contention

4. **Apply targeted fixes**
   - Allocation and GC: reduce allocations, reuse buffers, avoid retaining large backing arrays
   - Data layout: improve locality, avoid interface boxing in hot loops
   - Concurrency: reduce contention, bound goroutines, add backpressure

5. **Verify and document**
   - Re-run the benchmark/profile
   - Ensure correctness isn’t traded away
   - Record the change and its measured impact

---

## Safety note: exposing pprof

`net/http/pprof` endpoints can leak sensitive runtime data. Prefer:
- bind to `localhost`
- protect with auth / firewall
- enable only in dev / controlled environments

---

## Resources

Load these references on demand:

- `references/profiling.md` — pprof + trace collection and analysis commands
- `references/benchmarks.md` — stable benchmarks, -benchmem, benchstat, hygiene
- `references/allocations-gc.md` — allocation patterns, slice retention, sync.Pool guidance
- `references/contention.md` — mutex/block profiles, contention patterns, backpressure
