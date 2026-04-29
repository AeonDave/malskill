---
name: rust-patterns
description: "Idiomatic Rust patterns and best practices for readable, safe, maintainable Rust: ownership, borrowing, API design, enums/traits, error handling, iterators, module layout, and tooling. Use when writing or reviewing `.rs` code, refactoring crates, porting non-idiomatic code into Rust, or designing Rust APIs."
license: MIT
compatibility: "Rust stable baseline (2024 edition-friendly). Tools: cargo, rustfmt, clippy, rustdoc. Optional: rust-analyzer."
metadata:
  author: AeonDave
  version: "1.1"
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

## Outcome expectations

- Public APIs make ownership and failure behavior obvious at call sites.
- Domain modeling uses enums/newtypes/builders instead of ad-hoc primitives.
- Borrowing is preferred where practical; cloning is intentional and justified.
- Tooling (`fmt`, `clippy`, `test`, docs) is part of the definition of done.

---

## Recommended workflow

1. Define API boundaries and ownership semantics in function signatures.
2. Model states/errors with enums and typed results before implementing details.
3. Implement with small focused functions and explicit visibility boundaries.
4. Run `cargo fmt`, `cargo clippy`, and `cargo test` before review.
5. Review for accidental clones, over-broad traits, and panic-prone paths.

---

## Quick review checklist

- No `clone()` used only to silence the borrow checker unless the clone is cheap and intentional
- Inputs borrow where possible (`&str`, `&[T]`, `&Path`, `impl AsRef<Path>`) instead of forcing ownership
- Error paths preserve context and use `?`; production code does not rely on stray `unwrap`
- Enums beat boolean parameters; newtypes beat domain-significant bare integers/strings
- Traits are small and consumer-oriented; generic signatures are useful, not ornamental
- Module visibility is tidy (`pub`, `pub(crate)`, private helpers, selective `pub use`)

---

## Common anti-patterns to reject

- `clone()` used only to “make borrow checker errors go away”
- Public APIs that force ownership when a borrow would do
- Boolean/flag parameter combinations that should be enums
- Library code depending on routine `unwrap`/`expect` in operational paths
- Large traits that couple unrelated behavior and block evolution

## Platform and FFI boundaries

- Keep platform-specific modules small and make them return the same public types as the shared path.
- Prefer adapting one unstable primitive over forking a full protocol or workflow. Example shape: `connect_with_timeout(...) -> io::Result<TcpStream>` can use `std::net` normally and a Windows FFI helper only in a constrained build mode.
- Use feature gates to remove incompatible definitions, not just unreachable call sites, when signatures or imports differ by build mode.
- After adding Windows FFI bindings or `windows-sys` features, run a real target build; `cargo check` can pass before the linker sees missing imports or feature flags.

## Resources

Load on demand:

- `references/ownership-and-borrowing.md` — use when signatures, lifetimes, moves, or borrow-checker friction are central
- `references/api-design.md` — use when shaping public types, traits, builders, and module boundaries
- `references/errors-and-results.md` — use when designing recoverable errors or cleaning up panic-prone code
- `references/collections-and-iterators.md` — use when choosing collections or refactoring loops into clearer iterator code
- `references/tooling-and-docs.md` — use when reviewing formatting, clippy, rustdoc, features, and crate hygiene
