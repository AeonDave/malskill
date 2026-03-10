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
    item := item
    sem <- struct{}{}
    go func() {
        defer func() { <-sem }()
        process(item)
    }()
}
```

### Add backpressure

Prefer bounded queues. If producers can outpace consumers forever, memory becomes the buffer.

## References

- https://go.dev/blog/pipelines
- https://go.dev/doc/effective_go#concurrency
