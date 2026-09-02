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

## Platform matrix

| Platform | CPU profile | Allocation profile |
|---|---|---|
| Linux | `perf`/`cargo flamegraph`; `samply` | `heaptrack`, `dhat` |
| Windows | `samply` (dependable choice); WPA/ETW; VTune | `dhat` (`heaptrack` is Linux-only) |
| macOS | `samply`/Instruments; `cargo flamegraph` via `xctrace`/DTrace | Instruments, `dhat` |

- `samply` records a Firefox Profiler-format profile on all three platforms — use it when the
  platform profiler is awkward or when profiles must be shared.
- Keep release `debug = 1` (line tables) until profiling is done; profiles need symbols to name frames.
- `tokio-console` (runtime built with `RUSTFLAGS="--cfg tokio_unstable"`) shows task poll times,
  wakers, and stall points when the symptom is async scheduling.

## Workflow

1. Profile the unmodified baseline
2. Confirm the hottest call paths and call counts
3. Inspect whether time is spent in your code, dependencies, syscalls, allocation, or synchronization
4. Apply one targeted fix, then profile again

Favor fixing the top few dominant hotspots first; lower-ranked frames rarely move the end-to-end metric.

For deterministic instruction-count measurement in CI rather than "why is it slow" diagnosis, see
`measurement-workflow.md` (`iai-callgrind`).
