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

## Panic hygiene

- `panic!`, `unwrap`, and `expect` belong in tests, prototypes, or justified invariants
- Production paths should return actionable errors instead of surprising process aborts

## Good patterns

- Convert foreign errors with `From` or focused `map_err`
- Keep messages specific and local to the failing operation
- Separate validation errors from operational errors when the distinction matters
- Avoid deeply nested `match` trees when `?`, helpers, or combinators express the flow more clearly
