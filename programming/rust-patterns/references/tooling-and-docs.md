# Tooling and Docs

Use this reference when the task touches formatting, linting, rustdoc, features, or crate hygiene.

## Default toolchain habits

- Run `cargo fmt` for formatting
- Run `cargo clippy` and treat meaningful warnings as work, not wallpaper
- Run `cargo test` before finishing behavior-changing work
- Generate docs with `cargo doc` when public API changes need review

## Documentation hygiene

- Document public items with intent, invariants, and usage constraints
- Prefer runnable examples for non-obvious APIs; doctests double as documentation and regression tests
- Keep examples small and realistic

## Crate hygiene

- Keep feature flags additive when possible
- Minimize optional complexity in public APIs
- Be explicit about supported Rust baseline / edition if the project defines one
- Favor small modules with a clean re-exported public surface over deep public trees
