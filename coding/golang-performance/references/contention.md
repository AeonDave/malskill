# Contention and backpressure

## What to measure

- Mutex contention: `pprof/mutex`
- Blocking on channels: `pprof/block`
- Scheduler behavior / goroutine churn: `go tool trace`

## Typical causes

- One global lock protecting a map/cache
- Using unbuffered channels on high-throughput paths
- Spawning unbounded goroutines (burst load)
- Holding locks while doing I/O
- `GOMAXPROCS` far above the cgroup CPU limit (Go 1.25+ usually prevents this unless you set
  `GOMAXPROCS` yourself — see `compiler-and-runtime-tuning.md`)

## Patterns that help

### Shard the lock

Instead of one lock, split by hash prefix.

### Reduce lock scope

Do the minimum work while holding the lock.
Compute outside, then commit.

### Bound concurrency

Use a semaphore or worker pool to cap goroutines.

```go
sem := make(chan struct{}, max)
for _, item := range items {
    sem <- struct{}{}
    go func() {
        defer func() { <-sem }()
        process(item)
    }()
}
```

### Add backpressure

Prefer bounded queues. If producers can outpace consumers forever, memory becomes the buffer.

## Mitigation order (practical)

1. confirm contention with mutex/block profiles
2. shrink critical sections
3. reduce shared state / shard locks
4. bound producer rate (queue + workers)
5. re-profile before considering lock-free redesign

## References

- https://go.dev/blog/pipelines
- https://go.dev/doc/effective_go#concurrency
