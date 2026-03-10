# Interface design

## Keep interfaces small

Small interfaces are easier to satisfy, mock, and evolve.

```go
type Store interface {
    Get(ctx context.Context, id string) (User, error)
}
```

## Define interfaces where they’re used

Consumers should define the interface they need; providers should just provide concrete types.

## Accept interfaces, return concrete types

Accepting an interface improves flexibility; returning concrete types keeps APIs clear.

## Optional behavior

Use a small optional interface + type assertion.

```go
type Flusher interface{ Flush() error }

func WriteAndMaybeFlush(w io.Writer, p []byte) error {
    if _, err := w.Write(p); err != nil { return err }
    if f, ok := w.(Flusher); ok { return f.Flush() }
    return nil
}
```

## Avoid “provider interfaces”

Avoid returning interfaces just to hide the implementation. Prefer returning a concrete type and keep the interface at the edge (caller side).

## References

- https://go.dev/doc/effective_go#interfaces
- https://github.com/golang/go/wiki/CodeReviewComments#interfaces
