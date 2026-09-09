# Concurrency patterns

## Cancellation and timeouts

- `context.Context` should be the **first parameter**.
- Every goroutine should have a stop condition: `ctx.Done()`, channel close, or bounded loop.

```go
func Fetch(ctx context.Context, url string) ([]byte, error) {
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
    if err != nil { return nil, err }

    resp, err := http.DefaultClient.Do(req)
    if err != nil { return nil, err }
    defer resp.Body.Close()

    return io.ReadAll(resp.Body)
}
```

## Avoid goroutine leaks

If a goroutine can block forever on send/receive, it’s a leak.

```go
ch := make(chan T, 1)

select {
case ch <- v:
case <-ctx.Done():
}
```

## errgroup for coordinated work

```go
g, ctx := errgroup.WithContext(ctx)
g.SetLimit(runtime.GOMAXPROCS(0)) // cap fan-out; blocks Go() until a slot frees
for _, u := range urls {
    g.Go(func() error { _, err := Fetch(ctx, u); return err })
}
if err := g.Wait(); err != nil { return err }
```

`errgroup.SetLimit(n)` replaces hand-rolled semaphore + worker-pool patterns for capped fan-out.

## Worker pools and backpressure

- Prefer bounded queues.
- Cap concurrency.
- The sender closes the jobs channel.

## Shutdown contract

For long-running workers, make shutdown order explicit:
1. stop accepting new work
2. signal cancellation (`cancel()` / close control channel)
3. drain/join workers (`WaitGroup`)
4. close result channels once producers are done

## Modern concurrency primitives

- `sync.WaitGroup.Go(func())` (Go 1.25) — replaces `wg.Add(1); go func() { defer wg.Done(); ... }()`.
  `go vet` / gopls `waitgroupgo` (renamed from `waitgroup` in Go 1.27) catches `Add` *inside* the
  new goroutine.
- `context.WithoutCancel(ctx)` (Go 1.21) — detach values from cancellation for background work that
  must outlive the request (audit logs, metric flushes). Without it, returning from a handler
  cancels goroutines you spawned with `ctx`.
- `context.WithTimeoutCause` / `WithDeadlineCause` (Go 1.21) — same as timeout/deadline, plus a
  cause retrieved with `context.Cause`. Use when callers must distinguish "we canceled" from
  "deadline fired".
- `sync.OnceFunc` / `sync.OnceValue` / `sync.OnceValues` (Go 1.21) — typed lazy init without the
  `sync.Once` + mutable variable dance.
- Typed atomics `atomic.Int32/Int64/Uint64/Bool/Pointer[T]` (Go 1.19) — replace mutex-protected
  counters/flags and fix the 32-bit ARM alignment footgun of the legacy `atomic.AddInt64` API.
- `context.AfterFunc(ctx, f)` (Go 1.21) — runs `f` in its own goroutine when `ctx` is cancelled;
  cleaner than a manual `select { case <-ctx.Done() }` goroutine.

## Timer channels (Go 1.23+, locked in 1.27)

`time.Timer` / `Ticker` / `time.After` channels are **unbuffered** (synchronous) when the main
module's `go` line is 1.23+. Go 1.27 **removed** `GODEBUG=asynctimerchan`; the unbuffered behavior
is unconditional. `Stop`/`Reset` results are reliable: a delayed receive cannot sneak a leftover
value into a buffered chan. Do not write `asynctimerchan=1` in `go.mod` — Go 1.27 rejects a
removed GODEBUG set to the old value.

`runtime.LockOSThread` still pins the calling goroutine to its OS thread (cgo thread-local APIs,
`runtime.LockOSThread` + `UnlockOSThread` pairs). Cgo already takes an M; locking extra threads
is for TLS/affinity, not for "more parallelism". Scheduler/GOMAXPROCS tuning is in
`golang-performance` `compiler-and-runtime-tuning.md`.

## Fast leak triage

- Check `/debug/pprof/goroutineleak` (Go 1.27 stable; experimental in 1.26 via
  `GOEXPERIMENT=goroutineleakprofile`) for goroutines permanently blocked on channels/`sync`
  primitives. It will **not** report I/O waits or leaks whose primitive is still reachable from a
  runnable goroutine or a global. See `golang-performance` `profiling.md`.
- Check the full goroutine profile (`/debug/pprof/goroutine?debug=2`) when counts grow.
- Look for blocked send/receive without `select { case <-ctx.Done(): ... }`.
- Audit any background goroutine started in constructors/init paths.
- Tests: `goleak` plus `testing/synctest` — see `golang-testing` `fuzzing-and-race.md`.

## References

- https://go.dev/blog/pipelines
- https://pkg.go.dev/golang.org/x/sync/errgroup
- https://go.dev/doc/effective_go#concurrency
