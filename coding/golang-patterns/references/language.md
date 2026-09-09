# Language features (Go 1.22–1.27)

Load when writing or reviewing code that uses per-iteration loop vars, range-over-func,
`new(expr)`, self-referential constraints, generic methods, embedded-field keys, or 1.27
type inference. HTTP mux patterns live in `api-and-structs.md`. JSON defaults live in
`json-v2.md`. The `go` directive in `go.mod` (not the installed toolchain alone) gates
which of these compile — see `tooling.md`.

## Contents

- [Loop variables and range-over-int (Go 1.22+)](#loop-variables-and-range-over-int-go-122)
- [Range-over-func (Go 1.23+)](#range-over-func-go-123)
- [new(expr) (Go 1.26+)](#newexpr-go-126)
- [Self-referential constraints (Go 1.26+)](#self-referential-constraints-go-126)
- [Generic methods (Go 1.27+)](#generic-methods-go-127)
- [Embedded field keys and inference (Go 1.27+)](#embedded-field-keys-and-inference-go-127)

## Loop variables and range-over-int (Go 1.22+)

When the file's language version is Go 1.22+, each `for` iteration creates **new**
variables. Closures and `go func()` that capture the loop var see that iteration's
value — drop the `i := i` / `tt := tt` capture dance.

This is **not** a toolchain property: a 1.27 toolchain compiling a module with
`go 1.21` keeps the old shared-variable semantics. Set `go 1.22` (or later) in
`go.mod` before deleting captures.

```go
for i := range 10 { // 0..9; n<=0 runs zero times, no panic
    go work(i)      // safe under go 1.22+
}
```

Prefer `for i := range n` over `for i := 0; i < n; i++` when the index is the only
state.

## Range-over-func (Go 1.23+)

A `for range` may iterate a function of type `func(yield func(V) bool)` or
`func(yield func(K, V) bool)` (`iter.Seq` / `iter.Seq2`). Yield returns false when
the caller `break`s — **must** stop producing.

```go
func (s Set[T]) All() iter.Seq[T] {
    return func(yield func(T) bool) {
        for v := range s.m {
            if !yield(v) {
                return
            }
        }
    }
}

for v := range s.All() { ... }
keys := slices.Sorted(maps.Keys(m)) // maps.Keys is an iterator
```

Write an iterator when the sequence is large, lazy, or not a slice. Collect with
`slices.Collect` / `slices.Sorted` / `maps.Collect` only when you need a concrete
container. Do not invent a custom callback API for "for each" on new types.

## new(expr) (Go 1.26+)

`new` accepts a value. `new(expr)` allocates a `T`, stores `expr`, returns `*T`.
Use it for optional pointer fields (JSON, protobuf) instead of a temp var or a
`ptr[T any](v T) *T` helper.

```go
type Person struct {
    Name string `json:"name"`
    Age  *int   `json:"age"`
}
json.Marshal(Person{Name: name, Age: new(yearsSince(born))})
```

`new(42)` is `*int` pointing at 42. `new(nil)` does not compile (no concrete type).
`go fix` rewrites `ptr`-style helpers to `new` and can `//go:fix inline` the leftover
wrappers — see `tooling.md`.

## Self-referential constraints (Go 1.26+)

A generic type may name itself in its own type-parameter list (F-bounded
polymorphism). Use it when a method must accept/return **the same concrete type**,
not the interface:

```go
type Adder[A Adder[A]] interface {
    Add(A) A
}

func algo[A Adder[A]](x, y A) A { return x.Add(y) }
```

Typical targets: fluent builders, numeric types, clone-in-place trees. Do not use
it as a substitute for a small consumer-side interface.

## Generic methods (Go 1.27+)

A **concrete** method may declare its own type parameters. That is not the same as
a method on a generic type (`func (List[E]) Len()` has no method type params).

Reach for a generic method when the operation belongs on the type but the extra
type varies per call — mapping, converting, sampling — and a package-level
`MapList[E, R]` would crowd the package or force inside-out call nesting.

```go
func (l List[E]) Map[R any](f func(E) R) List[R] { /* ... */ }

NewList(0, 2, 4).Map(add2).Map(div2)
```

`math/rand/v2.Rand` gained `func (r *Rand) N[Int intType](n Int) Int` for the same
reason: one method instead of `Int32N`/`Int64N`/`IntN` copies.

**Interface rule:** interface methods **cannot** declare type parameters. A generic
method does **not** implement an interface method, even if some instantiation has
the same signature. Implementation is a property of the (possibly instantiated)
type's declared methods, not of one instantiation. Keep the interface method
non-generic; put the generic helper on the concrete type. See `interfaces.md`.

Instantiate before use (call or convert to a function). Method expressions work:
`List[int].Map[int]`.

Requires `go 1.27` (or later) in `go.mod` and a 1.27+ toolchain.

## Embedded field keys and inference (Go 1.27+)

A struct-literal key may be any valid field **selector**, so nested/embedded fields
initialize without naming the embed:

```go
type Habitat struct{ Burrow string }
type Gopher struct {
    Name string
    Habitat
}
g := Gopher{Name: "Gopher", Burrow: "Burrow #42"}
```

Use it when the embed is an implementation detail. Prefer an explicit nested
composite when two embeds share a field name or the nesting is the API.

Type inference for generic functions applies in assignment contexts: assigning to
a typed variable, composite-literal elements, conversions, and channel sends.

```go
func GenericFormatter[T any](v T) string { return fmt.Sprintf("%v", v) }
type IntFormatter func(int) string

formatters := []IntFormatter{GenericFormatter}
fn := IntFormatter(GenericFormatter)
ch <- GenericFormatter
```

If inference fails, instantiate explicitly (`GenericFormatter[int]`) rather than
adding dummy wrappers.

## References

- https://go.dev/doc/go1.22
- https://go.dev/doc/go1.23
- https://go.dev/doc/go1.26
- https://go.dev/doc/go1.27
- https://go.dev/blog/generic-methods
- https://go.dev/blog/range-functions
