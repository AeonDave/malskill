# Allocations and GC pressure

## The goal

In hot paths, fewer allocations usually means:
- less GC work
- better cache locality
- less latency variability

Measure first with `/debug/pprof/allocs` and `b.ReportAllocs()`.

Do not stack independent release-note percentages. Green Tea (Go 1.26+ default) cuts **GC
overhead** 10–40% on GC-heavy programs; the 1.27 small-object allocator is a separate ~1%
on alloc-heavy programs; `io.ReadAll` (Go 1.26) is often ~2× faster with about half the
memory. Attribute each to a measured profile.

Go 1.24+ maps use Swiss Tables. Don't micro-optimize around the old hashmap; if lookup of a
large comparable key dominates, intern with `unique.Make` (see `golang-patterns`
`effective-go.md`) rather than rewriting hashing.

Go 1.25+/1.26 allocate more slice backing arrays on the **stack**. Faster, but incorrect
`unsafe.Pointer` into a slice is more likely to explode — bisect with
`golang.org/x/tools/cmd/bisect -compile=variablemake`, or disable with
`-gcflags=all=-d=variablemakehash=n`. Prefer `io.ReadAll` as-is on 1.26+; it already
returns a minimally sized buffer.

`weak.Pointer[T]` (Go 1.24) for caches that must not keep values alive: `Value()` returns
`nil` after collection. Pair with `runtime.AddCleanup`, not `SetFinalizer`. Not a general
map key.

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

## Retention diagnostics

If heap stays high after load drops, investigate retained references:
- long-lived caches/maps holding large values
- slices or strings referencing oversized backing arrays
- goroutines capturing large objects in closures

## References

- https://go.dev/doc/diagnostics
- https://go.dev/blog/escape-analysis
