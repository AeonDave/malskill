# Unit and Integration Tests

Use this reference when deciding test scope and file placement in Rust.

## Scope rules

- Put unit tests next to the code with `#[cfg(test)]` when they validate internal logic or private helpers
- Put integration tests under `tests/` when they exercise public API or cross-module behavior
- Use doctests for public examples that should keep compiling and behaving correctly

## Good test shape

- Name tests by behavior, not by function name alone
- Keep setup close to the assertion unless a helper clearly improves readability
- Prefer one behavior per test; table-style loops are fine when cases are closely related
- Return `Result<(), E>` and use `?` inside the test when asserting error paths, instead of `unwrap()` chains

## Parameterized tests with rstest

When table-style loops grow past a few cases, `rstest` is drop-in better: each case becomes an
individually named, individually filterable test, and fixtures resolve test arguments by name
(fixtures can depend on other fixtures).

```rust
use rstest::{rstest, fixture};

#[fixture]
fn db() -> TestDb { TestDb::new_in_memory() }

#[rstest]
#[case("hello", 5)]
#[case("", 0)]
fn strlen(#[case] input: &str, #[case] expected: usize) {
    assert_eq!(input.len(), expected);
}

#[rstest]
fn insert(db: TestDb) { /* assert on db */ }
```

Skip it for one-off tests — `rstest` pays off only when cases, fixtures, or shared context repeat.

## Panic testing discipline

- If the API returns `Result`, assert on the error (`is_err()`, `unwrap_err()`, or the variant via
  `matches!`) — do not reach for `#[should_panic]`.
- When a panic genuinely is the contract, use `#[should_panic(expected = "substring")]`; the
  `expected` filter blocks a wrong panic from passing. Bare `#[should_panic]` accepts *any* panic.

## Assertion readability

`pretty_assertions` is a drop-in replacement for `assert_eq!`/`assert_ne!` that prints a colored
diff on failure — worth adding when tests compare structs or long strings:

```rust
use pretty_assertions::assert_eq;
```

## Compile-fail tests for macro crates

Proc-macro authors verify that bad input fails to compile with `trybuild`:

```rust
#[test]
fn ui() { trybuild::TestCases::new().compile_fail("tests/ui/*.rs"); }
```

Each case pairs an `.rs` file against an expected `.stderr` snapshot; run with `TRYBUILD=overwrite`
to (re)write snapshots. Treat snapshot updates as reviewed behavior changes, same as `insta`.

## Avoid

- giant “workflow” tests for ordinary logic
- asserting on private implementation details from integration tests
- re-testing the same happy path at every layer without adding signal
