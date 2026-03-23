# Commands

Use these commands as a starting point; select the smallest command that proves the change.

## Core commands

- `cargo test` — run all unit and integration tests
- `cargo test test_name` — run tests matching a name
- `cargo test -- --nocapture` — show test output
- `cargo test --doc` — run doctests only
- `cargo test -- --test-threads=1` — force serial execution when shared state is unavoidable

## Optional tooling

- `cargo nextest run` — faster parallel test runner with better CI ergonomics
- `cargo llvm-cov` — collect coverage with LLVM-based tooling
- `cargo insta review` — review pending snapshot changes when using `insta`

## Benchmark-adjacent

- `cargo bench` — run benchmarks
- run benchmarks in release mode and compare against a stable baseline before drawing conclusions
