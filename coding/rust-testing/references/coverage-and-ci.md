# Coverage and CI

Use this reference when turning Rust tests into reliable automation.

## Coverage guidance

- Coverage is a diagnostic tool, not the definition of quality
- Use `cargo llvm-cov` or project-approved tooling when branch or line coverage is needed
- `cargo llvm-cov --fail-under-lines N` (or `--fail-under-functions N`) turns coverage into a stable
  CI gate that exits 1 below the threshold — pin important behaviors with assertions first, then a
  threshold
- Prefer adding assertions for important behaviors over chasing arbitrary percentages

## nextest configuration

- Repository config lives in `.config/nextest.toml`; profiles inherit from `default`
- Declare retries per profile: `[profile.ci]` with `retries = 2` means two retries (three attempts
  total) for flaky tests
- `flaky-result = "fail"` makes a test that only passes on retry count as failing — useful CI
  discipline against known-flaky names
- **nextest does not run doctests** (stable-Rust limitation): keep a separate `cargo test --doc`
  step or the contract examples lose coverage

## Mutation testing

`cargo mutants` injects real bugs (operator swaps, default returns) and runs the suite against
each; a surviving mutant means the tests don't actually pin that behavior. Install with
`cargo install --locked cargo-mutants`; run it as a scheduled or on-demand deep check, not a PR
gate — cost scales with suite time × mutant count.

## CI habits

- Run `cargo test` for baseline confidence
- Add `cargo test --doc` if doctests matter; `cargo nextest` does not replace doctest coverage
- Gate on `cargo fmt --check` and `cargo clippy -- -D warnings` before running the test stage
- Prefer `--locked` in CI when reproducibility matters

Practical caution: coverage collection can significantly slow execution; keep dedicated coverage
jobs separate from fast PR gating.

## Flake reduction

- isolate shared state
- remove timing assumptions
- retry only when the underlying cause cannot be eliminated quickly
