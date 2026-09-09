# Concurrency and Throughput

Use this reference when Rust performance work touches threads, Rayon, async tasks, channels, or locks.

For which concurrency primitive to choose (channel types, shared-state patterns, async design),
load the `rust-patterns` skill's `references/concurrency.md` first; this file covers the
performance side only.

## Parallelism rules

- Add parallelism only when the workload is large enough to amortize coordination cost
- CPU-bound data parallelism often fits Rayon well
- IO-bound concurrency belongs in an async runtime with bounded task creation

## `available_parallelism` and OS threads

`std::thread::available_parallelism()` (1.59) is the portable pool size: logical
CPUs, **capped by cgroup / affinity** when the OS exposes them. It is **not**
cached — do not call it in a hot loop. Errors if the platform cannot answer;
fall back to `1`.

```rust
let n = std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1);
```

- Size Rayon / a hand-rolled pool / `tokio` `worker_threads` from this value (or
  leave Rayon/Tokio defaults, which already consult it). Do **not** spawn
  `available_parallelism()` OS threads **per request**.
- Linux caveats (from std docs): may overcount when affinity/cgroup cannot be
  queried (sandbox); may undercount when the current thread's affinity is a
  subset of the process cpuset; ignores `ulimit -u`. Windows may undercount
  above 64 logical CPUs unless the process opted into >64-CPU support.
- Extra OS threads are expensive (stack + scheduler). Cap blocking
  `spawn_blocking` (`max_blocking_threads`); CPU work belongs in Rayon, not a
  growing blocking pool.
- Primitive choice (`Mutex` vs channel vs atomics, `thread::scope`, poison) is
  in `rust-patterns` `concurrency.md`. This file is cost and sizing only.

## Common bottlenecks

- `Arc<Mutex<T>>` around hot shared state
- channels without backpressure or batching
- excessive task spawning for tiny units of work
- false sharing or over-eager atomics in tight loops

## False sharing

Two threads writing different fields on the same 64-byte cache line force cache-line ping-pong
even with no logical sharing. Fix per-thread hot data:

```rust
#[repr(align(64))]
struct Padded<T>(T);  // one hot counter per thread/shard, each on its own line
```

- Shard counters per thread and merge once at the end instead of sharing one atomic.
- Some libraries (crossbeam, folly) pad to 128 bytes because Intel spatial prefetchers fetch
  line pairs; use 64 first and try 128 if contention symptoms persist.

## Async runtime tuning

- Tokio's default multi-thread runtime uses one worker thread per core — tune
  `worker_threads(n)` only for constrained containers or oversubscribed hosts.
- Never block a worker: blocking work goes to `spawn_blocking` (bounded by
  `max_blocking_threads`); sustained CPU work belongs in Rayon, not async tasks.
- Bound concurrency explicitly: `mpsc::channel(capacity)` provides backpressure; unbounded
  queues hide overload until memory runs out. The capacity value is application-specific.
- Avoid one `tokio::spawn` per tiny item — batch items into fewer, longer-lived tasks.
- `tokio-console` (runtime built with `--cfg tokio_unstable`) diagnoses task stalls and
  over-spawning live.
- `Atomic*::update` (1.95) is still an atomic RMW — it does not remove contention.
  Shard first. `Atomic::from_mut` (1.98) is for unique `&mut` views, not for
  introducing atomics on a shared location.
- `hint::select_unpredictable` (1.88) for a rare branch you must keep; `hint::cold_path`
  (1.95) to mark an error/slow path. Measure; these are not substitutes for fixing
  the hot branch.

## High-signal fixes

- shard shared state and merge later
- reduce lock scope and move work out of critical sections
- batch small messages or updates
- measure whether sequential code beats parallel overhead for small inputs

## Throughput triage order

1. verify queue/backpressure behavior under representative load
2. identify contention points (locks/channels/atomics)
3. reduce coordination overhead before adding more worker parallelism
4. re-check p95/p99 latency, not only average throughput

Note: deterministic profilers (Valgrind-based, e.g. `iai-callgrind`) serialize threads and cannot
represent parallel behavior — use wall-clock benchmarks for contention measurements.
