# Allocations and GC pressure

## The goal

In hot paths, fewer allocations usually means:
- less GC work
- better cache locality
- less latency variability

Measure first with `/debug/pprof/allocs` and `b.ReportAllocs()`.

---

## Common allocation sources

### Growing slices without capacity

```go
// Prefer: make with capacity when size is known.
out := make([]T, 0, n)
for i := 0; i < n; i++ {
    out = append(out, f(i))
}
```

### Building strings in loops

```go
var b strings.Builder
b.Grow(n) // if you can estimate
for _, s := range parts {
    b.WriteString(s)
}
return b.String()
```

### Interface boxing in hot loops

If a hot loop converts to `interface{}` (or `any`), values may escape.
Prefer concrete types and typed helpers.

---

## Slice retention (backing array kept alive)

```go
// BAD: keeps the whole backing array alive
small := big[:10]

// GOOD: copy only what you need
small := make([]byte, 10)
copy(small, big[:10])
```

This often shows up as “mystery memory” in heap profiles.

---

## sync.Pool (use with care)

`sync.Pool` can reduce allocations for short-lived, frequently allocated objects.

Rules:
- Pool **buffers**, not business objects.
- Always `Reset()` buffers before returning to the pool.
- Treat pooled objects as **temporary**: the runtime may drop pool contents at any GC.
- Measure. Pooling can increase CPU due to contention or cache misses.

---

## Escape analysis

```bash
go build -gcflags="-m" ./...
```

Use this output to understand why values move to heap.
Don’t cargo-cult “avoid pointers”: correctness first, measure impact.

## References

- https://go.dev/doc/diagnostics
- https://go.dev/blog/escape-analysis
