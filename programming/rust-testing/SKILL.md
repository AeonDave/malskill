---
name: rust-testing
description: "Rust testing patterns for unit, integration, async, doc, property, snapshot, and benchmark-adjacent tests. Use when writing or reviewing tests for `.rs` code, reducing flakiness, designing fixtures/fakes, or improving CI confidence in Rust crates and workspaces."
license: MIT
compatibility: "Rust stable baseline. Tools: cargo test. Optional: cargo nextest, proptest, insta, mockall, tokio, cargo llvm-cov."
metadata:
  author: AeonDave
  version: "1.0"
---

# Rust Testing

High-signal guidance for Rust tests that are **deterministic, maintainable, and worth running**.

Use this skill when tests are part of the change, when flakiness needs to die quietly, or when CI needs stronger signal.

## When to activate

- Adding unit, integration, async, or doctests for Rust code
- Refactoring brittle or slow Rust tests
- Introducing fakes, mocks, property tests, or snapshot tests
- Tightening CI feedback with coverage, nextest, or command selection

---

## Core rules

- Prefer **small unit tests** for logic and **integration tests** for public behavior and boundaries.
- Keep tests deterministic: avoid sleep-based timing and shared mutable global state.
- Use mocks sparingly; prefer fakes, temp dirs, test servers, and controlled inputs.
- Treat doctests as part of the public contract, not decorative comments.
- Coverage is a signal, not the goal; strong assertions beat inflated percentages.

---

## Quick review checklist

- Test names describe behavior, not implementation trivia
- Setup is short and local; helpers remove noise without hiding intent
- External boundaries (time, filesystem, network, randomness) are controlled explicitly
- Async tests await real conditions instead of sleeping and hoping
- CI runs the right mix of `cargo test`, doctests, and any nextest/coverage steps

## Resources

Load on demand:

- `references/unit-and-integration.md` — use when deciding what belongs beside the code vs under `tests/`
- `references/async-and-boundaries.md` — use when testing async code, time, IO, and network boundaries
- `references/property-snapshot-and-mocks.md` — use when example-based tests are not enough or output is bulky
- `references/coverage-and-ci.md` — use when wiring coverage, nextest, or stable CI gates
- `references/commands.md` — use for the most common Rust test commands and selectors
