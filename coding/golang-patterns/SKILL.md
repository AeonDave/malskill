---
name: golang-patterns
description: "Idiomatic Go patterns, best practices, and conventions for building robust, readable, and maintainable Go code. Use when writing, reviewing, or refactoring Go (APIs, packages, errors, interfaces, concurrency, code style), choosing a dispatch or plugin mechanism, or building low-level/offensive Go with `unsafe`, `cgo`, syscall dispatch, or RE-resistant static builds."
license: MIT
compatibility: "Go 1.22+ (guidance baseline; notes flag features from Go 1.19–1.25). Optional tools: gofmt, goimports, staticcheck, golangci-lint, gopls, govulncheck, gosec, garble."
metadata:
  author: AeonDave
  version: "1.5"
---

# Go Patterns

This skill focuses on **idiomatic Go design and code review guidance**.

If your task is primarily measurement/profiling/optimization, use `golang-performance`.

## When to activate

- Writing new Go code (packages, APIs, services)
- Reviewing PRs for idioms, readability, and maintainability
- Refactoring for cleaner error handling and smaller interfaces
- Designing concurrency flows with cancellation and backpressure
- Choosing a dispatch/plugin mechanism, adding modules to a compiled binary, or building low-level/offensive Go tooling

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
- `references/security-review.md` — use when auditing Go for security bugs: untrusted input, panics/DoS, TLS defaults, secrets, supply chain (`govulncheck`, `gosec`)
- `references/unsafe-cgo.md` — use for `unsafe.Pointer` rules, `syscall`/`x/sys`, cgo boundaries, and static/cross-compiled offensive-tooling builds
- `references/dispatch-and-plugins.md` — use when choosing `dyn` interfaces vs enum dispatch, building registries and command dispatchers, or adding modules to a compiled binary (`plugin`, `hashicorp/go-plugin`, `wazero`/`extism`, `yaegi`, `selfupdate`, `tableflip`)
- `references/offensive-lowlevel.md` — use for RE-resistance, symbol/metadata stripping, `garble`/`GoReSym`, string obfuscation, syscall dispatch strategy, and in-memory execution
