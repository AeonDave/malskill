---
name: golang-patterns
description: "Idiomatic Go patterns, best practices, and conventions for building robust, readable, and maintainable Go code. Use when writing, reviewing, or refactoring Go (APIs, packages, errors, interfaces, concurrency, and code style)."
license: MIT
compatibility: "Go 1.22+ (guidance baseline). Optional tools: gofmt, goimports, staticcheck, golangci-lint."
metadata:
  author: AeonDave
  version: "1.3"
---

# Go Patterns

This skill focuses on **idiomatic Go design and code review guidance**.

If your task is primarily measurement/profiling/optimization, use `golang-performance`.

## When to activate

- Writing new Go code (packages, APIs, services)
- Reviewing PRs for idioms, readability, and maintainability
- Refactoring for cleaner error handling and smaller interfaces
- Designing concurrency flows with cancellation and backpressure

---

## Core principles (high signal)

- **gofmt is non-negotiable.** Style debates end at `gofmt`.
- Prefer **clarity**: small functions, early returns, explicit control flow.
- Make the **zero value useful**.
- Keep **interfaces small**; define them where they’re consumed.
- Handle **errors explicitly**; wrap with context; avoid `panic` for control flow.
- Concurrency should be **bounded** and **cancellable**; avoid goroutine leaks.

---

## Outcome expectations

- Public APIs are small, explicit, and boring to maintain.
- Error handling is consistent and machine-checkable with `errors.Is/As`.
- Concurrency flows always have cancellation and backpressure.
- Tooling baseline (`gofmt`, tests, vet/race) is easy to run in CI.

---

## Recommended workflow

1. Define package boundary + API contracts (inputs, outputs, errors) first.
2. Implement with small functions and explicit control flow.
3. Add context propagation and cancellation checks on blocking operations.
4. Run formatting/tests/vet/race before review.
5. Review for leaks, hidden globals, and interface over-abstraction.

---

## Quick review checklist

- Naming: MixedCaps for exported, no underscores, packages short and lower-case
- Errors: `fmt.Errorf("context: %w", err)`, `errors.Is/As` used correctly
- Context: `ctx` is first param; cancellation propagates; no `context.Context` stored in structs
- Interfaces: accept interfaces, return concrete types; no “kitchen-sink” interfaces
- Concurrency: goroutines have a stop condition; channels are closed by senders; backpressure exists
- Tooling: `go test ./...`, `go test -race ./...`, `go vet ./...`

---

## Common anti-patterns to reject

- Storing `context.Context` in structs
- Unbounded goroutine fan-out in request paths
- Catch-all interfaces like `Doer`, `Manager`, `Service` without clear boundary
- Returning wrapped errors without enough domain context
- Package-level mutable state hidden behind helper functions

---

## Resources

Load on demand (progressive disclosure):

- `references/effective-go.md` — distilled Effective Go + Code Review Comments pointers
- `references/errors.md` — wrapping, sentinel vs typed errors, validation, retryable errors
- `references/interfaces.md` — interface placement, design patterns, optional behavior
- `references/concurrency.md` — cancellation, errgroup, leaks, worker pools, backpressure
- `references/api-and-structs.md` — receiver rules, functional options, embedding
- `references/package-layout.md` — project layout, package naming, dependency injection
- `references/tooling.md` — gofmt/goimports, vet, staticcheck, golangci-lint guidance
