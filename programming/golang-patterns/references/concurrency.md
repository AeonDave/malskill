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
for _, u := range urls {
    u := u
    g.Go(func() error { _, err := Fetch(ctx, u); return err })
}
if err := g.Wait(); err != nil { return err }
```

## Worker pools and backpressure

- Prefer bounded queues.
- Cap concurrency.
- The sender closes the jobs channel.

## References

- https://go.dev/blog/pipelines
- https://pkg.go.dev/golang.org/x/sync/errgroup
- https://go.dev/doc/effective_go#concurrency
