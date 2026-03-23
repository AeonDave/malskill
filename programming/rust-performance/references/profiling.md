# Profiling

Use this reference when benchmarking says “slow” but not yet “why”.

## Match the tool to the symptom

- CPU hot path: flamegraph / sampling profiler
- Allocation churn or retention: heap / allocation profiler
- Locking and channel stalls: contention-focused tooling or traces
- Async scheduling issues: runtime-aware traces and task-level instrumentation

## Practical tool choices

- `cargo flamegraph` or platform profilers for CPU time
- `perf` for Linux sampling and hardware counters
- `heaptrack` or `dhat` for allocation-heavy workloads
- `samply` or native platform profilers when flamegraph tooling is awkward

## Workflow

1. Profile the unmodified baseline
2. Confirm the hottest call paths and call counts
3. Inspect whether time is spent in your code, dependencies, syscalls, allocation, or synchronization
4. Apply one targeted fix, then profile again
