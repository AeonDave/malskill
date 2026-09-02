# API Design

Use this reference when shaping public Rust types, traits, modules, or constructors.

## Constructors and builders

- Use `new()` for obvious required fields
- Implement `Default` when a sensible default exists
- Use a builder when there are many optional fields or validation steps
- Offer `with_capacity()` where pre-allocation matters

## Model the domain directly

- Prefer enums over boolean flag parameters
- Prefer newtypes over domain-significant bare integers and strings
- Make invalid states unrepresentable when practical
- Keep related data and behavior together in `impl` blocks

## Naming conventions

- Accessors have no `get_` prefix: `fn name(&self)`, not `fn get_name(&self)`.
- Conversion methods: `as_*` cheap borrow, `to_*` expensive clone, `into_*` by-value ownership.
- Iterators: `iter()`, `iter_mut()`, `into_iter()`.
- Prefer meaningful lifetime names when several lifetimes interact: `'src`, `'ctx`, not `'a`, `'b`.

## Trait and generic guidance

- Keep traits small and consumer-oriented
- Accept generic inputs when it improves ergonomics (`impl AsRef<Path>`, `impl Into<String>`)
- Return concrete types unless callers truly benefit from abstraction
- Derive common traits aggressively for ergonomic value types: `Debug`, `Clone`, `PartialEq`, `Eq`, `Hash`, `Default`

## Public surface hygiene

- Re-export intentionally with `pub use`
- Prefer `pub(crate)` or private helpers over oversized public modules
- Add `#[must_use]` to results that should not be ignored
- Put runnable examples on public APIs when the usage is non-obvious

## Contract hygiene

- Keep constructor invariants explicit and validated at the boundary.
- Prefer typed IDs/newtypes over raw `String`/`u64` in public APIs.
- If API evolution is expected, avoid exposing internal representation details too early.
