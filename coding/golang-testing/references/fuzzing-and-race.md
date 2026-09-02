# Fuzzing, Race Detector, and Deterministic Goroutine Tests

Load when example-based unit tests aren't enough: hunting panics or data races on arbitrary input,
stabilizing goroutine-heavy tests, or gating a service against concurrent-access bugs. For plain
benchmarks and one-off fuzz examples, see `bench-fuzz.md`; for `-race` in CI, see `coverage-ci.md`.

## Contents

- [When to fuzz vs when to property-test](#when-to-fuzz-vs-when-to-property-test)
- [go test -fuzz operational recipe](#go-test--fuzz-operational-recipe)
- [Writing a fuzz target](#writing-a-fuzz-target)
- [Corpus, minimization, reproduction](#corpus-minimization-reproduction)
- [The race detector in anger](#the-race-detector-in-anger)
- [Goroutine leaks: goleak](#goroutine-leaks-goleak)
- [testing/synctest for deterministic goroutine tests](#testingsynctest-for-deterministic-goroutine-tests)

## When to fuzz vs when to property-test

- Fuzz when: parsers, decoders, path/URL handling, anything with `unsafe`/`cgo`, wire protocols,
  input validation, hex/base64 decode paths — anywhere untrusted bytes reach code.
- The fuzzer's free oracle is a panic. Add stronger oracles inside the target: `Decode(Encode(x))
  == x` round-trip, cross-check against a reference implementation, invariant asserts.
- On fuzzed paths, a panic *is* the bug — fix the code to return an error; don't wrap the target in
  `defer recover()`.

## go test -fuzz operational recipe

```bash
# Discover and run every fuzz target briefly (like a normal test pass).
go test -run=^$ -fuzz=. -fuzztime=30s ./...

# Focus on one target (only one -fuzz target may run per invocation).
go test -run=^$ -fuzz=FuzzParse -fuzztime=1h ./parser

# CI-style bounded run.
go test -run=^$ -fuzz=FuzzParse -fuzztime=60s -parallel=4 ./parser
```

- `-fuzz` accepts a regex but the fuzzer engages **exactly one** matching target per run — pick a
  target explicitly; wildcard runs are for smoke testing.
- `-fuzztime` bounds wall-clock; `-fuzzminimizetime` bounds shrinking of a failing input.
- Crashes are written under `testdata/fuzz/<TargetName>/` as text files; re-running the ordinary
  `go test` re-executes them as regression cases automatically.

## Writing a fuzz target

Keep the target thin: map raw bytes to the API, let the oracle fire.

```go
func FuzzParse(f *testing.F) {
    // Seed with real, valid samples so coverage grows fast.
    f.Add([]byte("hello=world"))
    f.Add([]byte(""))

    f.Fuzz(func(t *testing.T, b []byte) {
        v, err := Parse(b)
        if err != nil {
            return // rejecting invalid input is expected
        }
        // Round-trip oracle: encoding a decoded value must reproduce input semantics.
        if got, _ := Parse(Encode(v)); got != v {
            t.Fatalf("round-trip mismatch for %q", b)
        }
    })
}
```

- Seed with **valid** and **borderline** samples; the fuzzer's mutator adds noise, but it doesn't
  discover the language shape from zero.
- Fuzz targets must be pure: no filesystem, no network. Reproducibility and shrinking break
  otherwise.

## Corpus, minimization, reproduction

- Persistent corpus lives in `testdata/fuzz/<Target>/` — commit interesting seeds and shrunk
  crashers so future runs don't have to rediscover them.
- A crash writes a single reproducer file into that directory; the next `go test ./<pkg>` runs it
  as a regression case and fails until fixed.
- Shrinking is automatic on a crash; if the crash file is still large, raise `-fuzzminimizetime`
  and re-run against that specific reproducer.

## The race detector in anger

`-race` is not a benchmark: expect ~2x CPU and ~5–10x memory. Run it separately from the fast PR
lane.

- `go test -race ./...` — enables the runtime race detector; finds true happens-before violations,
  not heuristics. A hit is a real bug.
- Race hits are **non-deterministic**: absence of a hit is not proof of absence. Long-running
  chaos-style tests (`-count=100`) or fuzzing under `-race` shake more loose.
- Race under `-fuzz`: cargo-cult wisdom said "not supported", but modern toolchains combine them;
  it just runs slower. Use for the concurrent-mutation-heavy targets.
- Common patterns that fire: writes to a map from multiple goroutines, `wg.Add` inside the
  goroutine (see `waitgroup` analyzer), reading a `time.Time` field without a lock, sharing an
  `http.Request` across goroutines.

## Goroutine leaks: goleak

Panics and races are visible; leaks look like "slow memory growth". `go.uber.org/goleak` turns
package-level leaks into test failures.

```go
package mypkg

import (
    "testing"
    "go.uber.org/goleak"
)

func TestMain(m *testing.M) {
    goleak.VerifyTestMain(m)
}
```

Add per-test with `defer goleak.VerifyNone(t)` for finer scope. Options let you ignore
framework-owned goroutines (e.g. `goleak.IgnoreTopFunction`).

## testing/synctest for deterministic goroutine tests

`testing/synctest` runs a function inside a "bubble" with a **fake clock** — every `time.Sleep`,
`time.After`, `context.WithTimeout` advances instantly, and `synctest.Wait` blocks until every
goroutine in the bubble is idle. It makes timing-driven concurrent tests deterministic and fast.

- Go 1.24: experimental; requires `GOEXPERIMENT=synctest go test ./...`.
- Go 1.25+: stable in the standard library, no build flag.

```go
func TestRetry(t *testing.T) {
    synctest.Run(func() {
        ctx, cancel := context.WithTimeout(context.Background(), time.Hour)
        defer cancel()

        done := make(chan error, 1)
        go func() { done <- RetryLoop(ctx) }() // uses time.After internally

        synctest.Wait() // wait until every goroutine in the bubble is blocked
        // Now assert observable state without racing against real time.
    })
}
```

Rules:

- The bubble panics if you try to interact with a bubbled channel from outside — keep everything
  the test observes inside `synctest.Run`.
- Only `time` package sleeps/timers are faked. `runtime.Gosched`, `os.Sleep`, or a real network
  syscall still block for real.
- Prefer over `time.Sleep`-based tests everywhere the code under test uses `time` primitives;
  removes an entire class of CI flakes.
