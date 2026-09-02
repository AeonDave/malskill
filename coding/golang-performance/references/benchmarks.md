# Go Benchmarks (stable, repeatable)

## Basic benchmark skeleton

Go 1.24+ has `for b.Loop() { ... }` which is the preferred shape: it hides the timer around
setup/cleanup, and the compiler refuses to eliminate the loop body, so you no longer need
`b.ResetTimer` or sink variables to defeat dead-code elimination.

```go
func BenchmarkThing(b *testing.B) {
    b.ReportAllocs()
    input := makeInput()

    for b.Loop() {
        _ = Thing(input) // compiler-safe: DCE disabled inside b.Loop
    }
}
```

Legacy `b.N`-style is still supported and required on pre-1.24 toolchains:

```go
func BenchmarkThingLegacy(b *testing.B) {
    b.ReportAllocs()
    input := makeInput()
    b.ResetTimer()
    var sink Result
    for i := 0; i < b.N; i++ {
        sink = Thing(input) // sink prevents dead-code elimination
    }
    _ = sink
}
```

## Run benchmarks

```bash
go test -run=^$ -bench=. -benchmem ./...

# Longer benches reduce noise
go test -run=^$ -bench=. -benchmem -benchtime=3s ./...

# Fix CPU variability where possible
GOMAXPROCS=1 go test -run=^$ -bench=. -benchmem ./...
```

## Compare before/after (benchstat)

`benchstat` summarizes change with statistics.

```bash
# Install once
go install golang.org/x/perf/cmd/benchstat@latest

# Capture output
go test -run=^$ -bench=BenchmarkThing -benchmem ./... > before.txt
# apply change
go test -run=^$ -bench=BenchmarkThing -benchmem ./... > after.txt

benchstat before.txt after.txt
```

## Benchmark hygiene

- Keep setup outside the timer (`b.ResetTimer()`)
- Avoid allocations in the benchmark loop unless you’re measuring them
- Use `b.StopTimer()` / `b.StartTimer()` for expensive setup between iterations
- Use sub-benchmarks (`b.Run`) for comparisons

Additional stability tips:
- Avoid running heavyweight background processes while benchmarking.
- Prefer fixed input datasets so before/after runs are comparable.
- Capture multiple runs and compare with `benchstat` instead of single-run conclusions.

## References

- https://pkg.go.dev/testing
- https://go.dev/blog/benchmarks
