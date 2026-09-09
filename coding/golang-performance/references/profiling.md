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

For accurate mutex/block data, set sampling rates in code where appropriate:

```go
runtime.SetMutexProfileFraction(1)
runtime.SetBlockProfileRate(1)
```

Use lower sampling rates in production if overhead is a concern.

## Goroutine leak profile (Go 1.27 stable)

Reports goroutines the GC can prove will never wake: blocked on a channel, `sync.Mutex`,
`sync.Cond`, etc. whose primitive is unreachable from any runnable goroutine (or from
goroutines those could unblock). No extra cost until you collect it.

```bash
go tool pprof http://127.0.0.1:6060/debug/pprof/goroutineleak
```

Misses: network/I/O waits, leaks whose primitive is a package global or is still reachable
from a live goroutine. Complement with `/debug/pprof/goroutine` and test-time `goleak` /
`synctest` (`golang-testing`). Go 1.26 required `GOEXPERIMENT=goroutineleakprofile`; that
experiment flag is gone in 1.27.

Classic leak: early `return` while workers still send on an unbuffered result channel —
exactly what this profile is for.

## go tool trace

Trace is useful when the scheduler and GC behavior are part of the problem.

```bash
curl -o trace.out http://127.0.0.1:6060/debug/pprof/trace?seconds=5
go tool trace trace.out
```

Go 1.26+ `go tool pprof -http` defaults to the flame graph (`View → Graph` or `/ui/graph`
for the old graph). Go 1.27 `go tool trace -http=:6060` binds localhost; use
`-http=0.0.0.0:6060` only when you mean it.

## Flight recorder (Go 1.25+)

`runtime/trace.FlightRecorder` keeps a ring buffer of execution trace. On a rare event
(timeout spike, deadlock suspect), `WriteTo` dumps the last few seconds. Cheaper than a
continuous trace. Configure window via `FlightRecorderConfig`. Do not leave an unbounded
flight recorder dump path on a public pprof mux.

## Minimal analysis checklist

1. Confirm the hotspot appears consistently across runs
2. Confirm whether it is CPU, allocs/GC, syscalls, or contention
3. Make one change and re-measure
4. Keep profile type, load shape, and duration consistent when comparing runs

## References

- pprof: https://pkg.go.dev/net/http/pprof
- Goroutine leak profiles: https://go.dev/blog/goroutine-leak-profiles
- Go blog (pprof): https://go.dev/blog/pprof
- Go blog (trace): https://go.dev/blog/trace
