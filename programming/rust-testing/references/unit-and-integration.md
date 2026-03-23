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
- Make failures easy to diagnose with helpful assertion context

## Avoid

- giant “workflow” tests for ordinary logic
- asserting on private implementation details from integration tests
- re-testing the same happy path at every layer without adding signal
