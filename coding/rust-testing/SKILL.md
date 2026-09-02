---
name: rust-testing
description: "Rust testing patterns for unit, integration, async, doc, property, snapshot, fuzz, and benchmark-adjacent tests. Use when writing or reviewing tests for `.rs` code, reducing flakiness, designing fixtures/fakes, improving CI confidence, or hardening `unsafe`, FFI, and parser-heavy code with Miri and sanitizers."
license: MIT
compatibility: "Rust stable baseline. Tools: cargo test. Optional: rstest, pretty_assertions, mockall, tokio (test-util), proptest, insta, trybuild, cargo nextest, cargo llvm-cov, cargo-mutants. Nightly: cargo-fuzz/Miri/sanitizers."
metadata:
  author: AeonDave
  version: "1.3"
---

# Rust Testing

High-signal guidance for Rust tests that are **deterministic, maintainable, and worth running**.

Use this skill when tests are part of the change, when flakiness needs to die quietly, or when CI needs stronger signal.

## When to activate

- Adding unit, integration, async, or doctests for Rust code
- Refactoring brittle or slow Rust tests
- Introducing fakes, mocks, property tests, or snapshot tests
- Tightening CI feedback with coverage, nextest, or command selection
- Hardening parsers, `unsafe`, or FFI code against arbitrary input with fuzzing, Miri, or sanitizers

---

## Core rules

- Prefer **small unit tests** for logic and **integration tests** for public behavior and boundaries.
- Keep tests deterministic: avoid sleep-based timing and shared mutable global state.
- Use mocks sparingly; prefer fakes, temp dirs, test servers, and controlled inputs.
- Treat doctests as part of the public contract, not decorative comments.
- Coverage is a signal, not the goal; strong assertions beat inflated percentages.
- Avoid production-only test hooks unless they expose a legitimate public or crate-private seam.
- Pair with `test-driven-development` when implementing persistent code or bug fixes test-first.
- Pair with `testing-reliability` for mock/timing anti-patterns and `systematic-debugging` when the root cause is unclear.

---

## Outcome expectations

- Tests are deterministic, debuggable, and fast enough to run frequently.
- Boundaries (time/fs/network/randomness) are explicit and controllable.
- CI separates fast confidence checks from heavier coverage/property/snapshot stages.

---

## Recommended workflow

1. Start with focused unit/integration tests for the behavior change.
2. Run targeted commands before full-suite reruns.
3. Stabilize async/boundary tests via explicit timeouts and local fixtures.
4. Add property/snapshot tests when they increase signal, not just volume.
5. Verify CI command mix remains fast and reproducible.

---

## Quick review checklist

- Test names describe behavior, not implementation trivia
- Setup is short and local; helpers remove noise without hiding intent
- External boundaries (time, filesystem, network, randomness) are controlled explicitly
- Async tests await real conditions instead of sleeping and hoping
- CI runs the right mix of `cargo test`, doctests, and any nextest/coverage steps

## Resources

Load on demand:

- `references/unit-and-integration.md` — use when deciding what belongs beside the code vs under `tests/`, when picking `rstest` over table loops, `should_panic` discipline, or `trybuild` compile-fail tests
- `references/async-and-boundaries.md` — use when testing async code, time, IO, and network boundaries
- `references/property-snapshot-and-mocks.md` — use when example-based tests are not enough, when output is bulky, or when scripting `mockall` expectations
- `references/fuzzing-and-sanitizers.md` — use to hunt panics, memory-safety bugs, and UB on arbitrary input (cargo-fuzz, arbitrary, AFL, Miri, sanitizers)
- `references/coverage-and-ci.md` — use when wiring coverage, nextest profiles, mutation testing, or stable CI gates
- `references/commands.md` — use for the most common Rust test commands and selectors
