# Coverage and CI

Use this reference when turning Rust tests into reliable automation.

## Coverage guidance

- Coverage is a diagnostic tool, not the definition of quality
- Use `cargo llvm-cov` or project-approved tooling when branch or line coverage is needed
- Prefer adding assertions for important behaviors over chasing arbitrary percentages

## CI habits

- Run `cargo test` for baseline confidence
- Add `cargo test --doc` if doctests matter; `cargo nextest` does not replace doctest coverage
- Use `cargo nextest` when faster parallel execution and better CI ergonomics help
- Prefer `--locked` in CI when reproducibility matters

## Flake reduction

- isolate shared state
- remove timing assumptions
- retry only when the underlying cause cannot be eliminated quickly
