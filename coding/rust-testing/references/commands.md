# Commands

Use these commands as a starting point; select the smallest command that proves the change.

## Core commands

- `cargo test` — run all unit and integration tests
- `cargo test test_name` — run tests matching a name
- `cargo test -- --nocapture` — show test output
- `cargo test --doc` — run doctests only
- `cargo test -- --test-threads=1` — force serial execution when shared state is unavoidable
- `cargo test package::module::test_name -- --exact` — run one exact test path when triaging
- `cargo test -- --ignored` — run tests marked `#[ignore]` (quarantined or slow tests)

## Optional tooling

- `cargo nextest run` — faster parallel test runner (`--profile ci` to use repo config)
- `cargo nextest run --retries 2` — retry flaky tests without editing config
- `cargo llvm-cov` — collect coverage with LLVM-based tooling
- `cargo llvm-cov --fail-under-lines 80` — coverage gate as a CI exit condition
- `cargo mutants` — mutation testing; run when hunting untested logic paths
- `cargo insta review` — review pending snapshot changes when using `insta`

## Benchmark-adjacent

- `cargo bench` — run benchmarks; compare in release mode against a stable baseline
- For benchmark design and criterion setup, load the `rust-performance` skill
