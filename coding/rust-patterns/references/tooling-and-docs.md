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
- Set `edition` and `rust-version` in `Cargo.toml`. `edition` is a **language**
  gate (2024 capture/drop/`unsafe` attrs); `rust-version` is the MSRV cargo
  enforces. A 1.98 toolchain with `edition = "2021"` is still 2021 semantics.
- Migrate editions with `cargo fix --edition`, then review `#[unsafe(no_mangle)]`
  and `set_var` sites by hand (`language.md`).
- Favor small modules with a clean re-exported public surface over deep public trees

## Compile-time visibility

- `cargo build --timings` — HTML of crate parallelism. A tall red "waiting"
  stack means one crate is serializing the graph; split that crate or cut
  its proc-macro surface. Runtime optimization is the `rust-performance` skill.
- Rust 1.90+ uses **LLD by default** on `x86_64-unknown-linux-gnu`. Faster
  links; opt out with `-C linker-features=-lld` if a linker script/BFD feature
  breaks. Details in `rust-performance` `compiler-and-build-tuning.md`.

## CLI stdio

`std::io::IsTerminal` (1.70): `std::io::stdout().is_terminal()` before emitting
color/progress. Do not key color on `cfg(unix)` alone.

## Practical quality gates

- `cargo fmt --check`
- `cargo clippy --all-targets --all-features -- -D warnings` (or repo-approved strictness)
- `cargo test` (plus doctests when public API changed)
