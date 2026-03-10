# Benchmarks and fuzzing

## Benchmarks

```go
func BenchmarkThing(b *testing.B) {
    b.ReportAllocs()
    input := makeInput()
    b.ResetTimer()

    for i := 0; i < b.N; i++ {
        _ = Thing(input)
    }
}
```

Guidelines:
- keep setup out of the timed loop
- run long enough to reduce noise (`-benchtime=3s`)
- compare before/after with `benchstat` when possible

## Fuzzing

Fuzz tests are great for parsers and validation.

```go
func FuzzParse(f *testing.F) {
    f.Add("seed")

    f.Fuzz(func(t *testing.T, s string) {
        v, err := Parse(s)
        if err != nil {
            return // invalid inputs are expected
        }

        // property-style checks
        if v == (Value{}) {
            t.Fatalf("unexpected zero value")
        }
    })
}
```

Guidelines:
- encode properties, not exact outputs
- keep fuzz target deterministic
- minimize allocations in the fuzz function
