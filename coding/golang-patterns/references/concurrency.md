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
    u := u
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
  `gopls`'s `waitgroupgo` analyzer offers the rewrite; `go vet`'s `waitgroup` catches the classic
  race of calling `Add` *inside* the new goroutine.
- `context.WithoutCancel(ctx)` (Go 1.21) — detach values from cancellation for background work that
  must outlive the request (audit logs, metric flushes). Without it, returning from a handler
  cancels goroutines you spawned with `ctx`.
- `sync.OnceFunc` / `sync.OnceValue` / `sync.OnceValues` (Go 1.21) — typed lazy init without the
  `sync.Once` + mutable variable dance.
- Typed atomics `atomic.Int32/Int64/Uint64/Bool/Pointer[T]` (Go 1.19) — replace mutex-protected
  counters/flags and fix the 32-bit ARM alignment footgun of the legacy `atomic.AddInt64` API.
- `context.AfterFunc(ctx, f)` (Go 1.21) — runs `f` in its own goroutine when `ctx` is cancelled;
  cleaner than a manual `select { case <-ctx.Done() }` goroutine.

## Fast leak triage

- Check goroutine profile (`/debug/pprof/goroutine?debug=2`) when counts grow.
- Look for blocked send/receive without `select { case <-ctx.Done(): ... }`.
- Audit any background goroutine started in constructors/init paths.

## References

- https://go.dev/blog/pipelines
- https://pkg.go.dev/golang.org/x/sync/errgroup
- https://go.dev/doc/effective_go#concurrency
