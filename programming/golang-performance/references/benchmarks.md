# Go Benchmarks (stable, repeatable)

## Basic benchmark skeleton

```go
func BenchmarkThing(b *testing.B) {
    b.ReportAllocs()

    setup := makeInput()
    b.ResetTimer()

    for i := 0; i < b.N; i++ {
        _ = Thing(setup)
    }
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

## References

- https://pkg.go.dev/testing
- https://go.dev/blog/benchmarks
