---
name: golang-testing
description: "Go testing patterns for unit tests, table-driven tests, subtests, test helpers, mocking/fakes, benchmarks, fuzzing, and coverage. Use when writing or reviewing Go tests to improve correctness, stability, and maintainability."
license: MIT
compatibility: "Go 1.22+ (guidance baseline). Tools: go test, go tool cover. Optional: race detector (-race), fuzzing (built-in), benchmark stats (benchstat)."
metadata:
  author: AeonDave
  version: "1.1"
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
