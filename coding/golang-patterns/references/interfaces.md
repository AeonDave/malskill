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

## Generic methods do not satisfy interfaces (Go 1.27+)

A concrete method may declare type parameters (`func (T) M[P any]()`). Interface methods **cannot**. `T` does not implement `interface{ M() }` just because `T.M[int]` happens to have that signature — implementation looks at declared methods, not instantiations.

Keep interface methods non-generic. Put the generic helper on the concrete type. See `language.md`.

## Interface size heuristic

If an interface exceeds 3–4 methods, challenge whether it actually models multiple responsibilities.
Split by capability and keep each interface behavior-focused.

## Testability without over-design

Start with concrete dependencies. Extract an interface only when you have a second implementation need
(tests, adapter, or alternative backend) and can name the behavior precisely.

## References

- https://go.dev/doc/effective_go#interfaces
- https://github.com/golang/go/wiki/CodeReviewComments#interfaces
