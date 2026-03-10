# Profiling Go with pprof and trace

Use this reference when you need concrete commands and a minimal workflow.

## Enable pprof (HTTP)

```go
import (
    "net/http"
    _ "net/http/pprof"
)

// Bind to localhost to reduce exposure.
go func() {
    _ = http.ListenAndServe("127.0.0.1:6060", nil)
}()
```

## CPU profile

```bash
go tool pprof http://127.0.0.1:6060/debug/pprof/profile?seconds=30

# Inside pprof
(pprof) top
(pprof) top -cum
(pprof) list YourFunc
(pprof) web
```

## Heap and allocs

```bash
go tool pprof http://127.0.0.1:6060/debug/pprof/heap
go tool pprof http://127.0.0.1:6060/debug/pprof/allocs

(pprof) top
(pprof) top -cum
(pprof) list YourFunc
```

Tips:
- Use `/allocs` to find **allocation sites**.
- Use `/heap` to find **live objects** (retention).

## Contention profiles (mutex/block)

- Mutex profile: time spent waiting on `sync.Mutex`/`RWMutex`
- Block profile: goroutines blocked on channel ops, select, etc.

```bash
# mutex and block endpoints exist when the runtime has profiling enabled
go tool pprof http://127.0.0.1:6060/debug/pprof/mutex
go tool pprof http://127.0.0.1:6060/debug/pprof/block
```

## go tool trace

Trace is useful when the scheduler and GC behavior are part of the problem.

```bash
curl -o trace.out http://127.0.0.1:6060/debug/pprof/trace?seconds=5
go tool trace trace.out
```

## Minimal analysis checklist

1. Confirm the hotspot appears consistently across runs
2. Confirm whether it is CPU, allocs/GC, syscalls, or contention
3. Make one change and re-measure

## References

- pprof: https://pkg.go.dev/net/http/pprof
- Go blog (pprof): https://go.dev/blog/pprof
- Go blog (trace): https://go.dev/blog/trace
