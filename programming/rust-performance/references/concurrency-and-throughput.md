# Concurrency and Throughput

Use this reference when Rust performance work touches threads, Rayon, async tasks, channels, or locks.

## Parallelism rules

- Add parallelism only when the workload is large enough to amortize coordination cost
- CPU-bound data parallelism often fits Rayon well
- IO-bound concurrency belongs in an async runtime with bounded task creation

## Common bottlenecks

- `Arc<Mutex<T>>` around hot shared state
- channels without backpressure or batching
- excessive task spawning for tiny units of work
- false sharing or over-eager atomics in tight loops

## High-signal fixes

- shard shared state and merge later
- reduce lock scope and move work out of critical sections
- batch small messages or updates
- measure whether sequential code beats parallel overhead for small inputs
