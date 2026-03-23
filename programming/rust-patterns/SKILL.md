---
name: rust-patterns
description: "Idiomatic Rust patterns and best practices for readable, safe, maintainable Rust: ownership, borrowing, API design, enums/traits, error handling, iterators, module layout, and tooling. Use when writing or reviewing `.rs` code, refactoring crates, porting non-idiomatic code into Rust, or designing Rust APIs."
license: MIT
compatibility: "Rust stable baseline (2024 edition-friendly). Tools: cargo, rustfmt, clippy, rustdoc. Optional: rust-analyzer."
metadata:
  author: AeonDave
  version: "1.0"
---

# Rust Patterns

This skill is for **day-to-day idiomatic Rust**: clear ownership, small APIs, and code that feels native to the language instead of a direct port from somewhere else.

If the task is primarily profiling/benchmarking, use `rust-performance`. If the task is primarily test design or test repair, use `rust-testing`.

## When to activate

- Writing or refactoring `.rs` modules, libraries, CLIs, or services
- Reviewing Rust PRs for ownership, borrowing, API shape, and common footguns
- Porting code from C/C++/Go/Python into idiomatic Rust
- Improving error handling, trait design, iterators, module boundaries, or docs

---

## Core rules (high signal)

- Make ownership obvious in signatures: **borrow by default, own when storing or crossing boundaries**.
- Model the domain with **enums, newtypes, and builders** instead of flag soup and loosely related primitives.
- Use `Result` for fallible work; reserve `panic!`, `unwrap`, and `expect` for tests or truly impossible states.
- Prefer iterators and pattern matching when they make intent clearer; do not turn readable logic into adapter golf.
- Keep public APIs small and deliberate; re-export intentionally and hide implementation details.
- Run `cargo fmt` and `cargo clippy`; style should not be negotiated by hand.

---

## Quick review checklist

- No `clone()` used only to silence the borrow checker unless the clone is cheap and intentional
- Inputs borrow where possible (`&str`, `&[T]`, `&Path`, `impl AsRef<Path>`) instead of forcing ownership
- Error paths preserve context and use `?`; production code does not rely on stray `unwrap`
- Enums beat boolean parameters; newtypes beat domain-significant bare integers/strings
- Traits are small and consumer-oriented; generic signatures are useful, not ornamental
- Module visibility is tidy (`pub`, `pub(crate)`, private helpers, selective `pub use`)

## Resources

Load on demand:

- `references/ownership-and-borrowing.md` — use when signatures, lifetimes, moves, or borrow-checker friction are central
- `references/api-design.md` — use when shaping public types, traits, builders, and module boundaries
- `references/errors-and-results.md` — use when designing recoverable errors or cleaning up panic-prone code
- `references/collections-and-iterators.md` — use when choosing collections or refactoring loops into clearer iterator code
- `references/tooling-and-docs.md` — use when reviewing formatting, clippy, rustdoc, features, and crate hygiene
