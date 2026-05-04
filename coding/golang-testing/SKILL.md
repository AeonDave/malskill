---
name: golang-testing
description: "Go testing patterns for unit tests, table-driven tests, subtests, test helpers, mocking/fakes, benchmarks, fuzzing, and coverage. Use when writing or reviewing Go tests to improve correctness, stability, and maintainability."
license: MIT
compatibility: "Go 1.22+ (guidance baseline). Tools: go test, go tool cover. Optional: race detector (-race), fuzzing (built-in), benchmark stats (benchstat)."
metadata:
  author: AeonDave
  version: "1.2"
---

# Go Testing

This skill is about writing tests that are **reliable**, **readable**, and **useful as documentation**.

## When to activate

- Writing new tests for functions, packages, or APIs
- Refactoring tests for clarity and reduced flakiness
- Adding benchmarks or fuzz tests
- Improving coverage without gaming the metric

---

## Core rules (high signal)

- Prefer **table-driven tests** for coverage and readability.
- Use **t.Helper()** and **t.Cleanup()** to keep failures actionable.
- Tests should be deterministic: avoid `time.Sleep()` unless unavoidable.
- Prefer **fakes** (in-memory implementations) over heavy mocks.
- Use `t.Parallel()` only when the test is truly isolated.
- Keep test data local and explicit; avoid hidden cross-test coupling.
- Do not add exported production APIs solely for tests; prefer package seams, interfaces, or local fakes.
- Pair with `test-driven-development` when implementing persistent code or bug fixes test-first.
- Pair with `testing-reliability` for mock/timing anti-patterns and `systematic-debugging` when failure attribution is unclear.

---

## Outcome expectations

- Unit tests are fast, deterministic, and easy to debug.
- Flaky tests are triaged with a repeatable reproduction loop.
- Bench/fuzz/coverage are used as correctness signals, not vanity metrics.

---

## Recommended workflow

1. Write/adjust focused unit tests first (table + subtests).
2. Run targeted test selection to confirm behavior quickly.
3. Add race detector and coverage checks.
4. For instability, reproduce with repeated runs (`-count`) and isolate state/time dependencies.
5. Add benchmarks/fuzz tests when behavior or performance risk justifies them.

---

## Quick checklist for a review

- Setup is outside the assertion loop; minimal shared mutable state
- Subtests have meaningful names (`t.Run("case", ...)`)
- Error messages show got/want and context
- External dependencies are explicit (DBs, network, time)
- Benchmarks report allocs when relevant (`b.ReportAllocs()`)

---

## Resources

Load on demand:

- `references/unit-tests.md` — TDD loop, table tests, subtests, parallel subtests
- `references/helpers-fixtures.md` — helpers, TempDir, Cleanup, testdata, golden files
- `references/mocking-fakes.md` — interfaces for dependencies, fakes vs mocks, examples
- `references/http-testing.md` — httptest patterns and JSON assertions
- `references/bench-fuzz.md` — benchmarks and fuzzing best practices
- `references/coverage-ci.md` — cover profiles, coverpkg notes, CI integration cautions
- `references/commands.md` — go test command recipes (race, timeout, count, patterns)
