# Errors and Results

Use this reference when deciding how Rust code should fail, recover, and carry context.

## Baseline strategy

- Use `Result<T, E>` for recoverable failures
- Use `Option<T>` only when absence is expected and not diagnostic
- Use `?` for propagation; add context at boundaries where it helps the caller

## Error type choices

- Libraries: prefer a concrete error enum or struct; `thiserror` is a good fit
- Applications / binaries: an aggregator like `anyhow` can be fine at the top level
- Preserve domain information instead of erasing everything into strings too early

Rule of thumb: typed errors in library boundaries, aggregated errors at executable boundaries.

```rust
// library boundary — typed
#[derive(thiserror::Error, Debug)]
pub enum StorageError {
    #[error("record not found: {id}")]
    NotFound { id: u64 },
    #[error("io")]
    Io(#[from] std::io::Error),
}

// executable boundary — aggregated
fn run() -> anyhow::Result<()> {
    let cfg = read_config().context("load config")?;
    // ...
    Ok(())
}
```

## `core::error::Error` (1.81+)

The `Error` trait lives in `core` (`core::error::Error`, re-exported as
`std::error::Error`). `no_std` + `alloc` libraries can implement `Error` without
`std`. Keep `thiserror` / `anyhow` at the crate boundary as before.

`std::error::Report` is **nightly** (`error_reporter`) as of 1.98 — use `anyhow`
or a `Display` wrapper in `main` on stable.

`std::panic::Location::caller()` is the right source location for "this is where
it was constructed" in error types; do not parse backtraces for that.

`Result::flatten` (1.89) unwraps `Result<Result<T, E>, E>` → `Result<T, E>`. Use
it after `map` that already returns `Result`, not as a substitute for `?`.

## Panic hygiene

- `panic!`, `unwrap`, and `expect` belong in tests, prototypes, or justified invariants
- Production paths should return actionable errors instead of surprising process aborts

## Good patterns

- Convert foreign errors with `From` or focused `map_err`
- Keep messages specific and local to the failing operation
- Separate validation errors from operational errors when the distinction matters
- Avoid deeply nested `match` trees when `?`, helpers, or combinators express the flow more clearly
