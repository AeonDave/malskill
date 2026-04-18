# TDD and test structure

## TDD (red → green → refactor)

1. Write a failing test for one behavior
2. Implement the minimal change to pass
3. Refactor with tests staying green

## Naming

Prefer descriptive names:
- `test_parse_rejects_empty_input`
- `test_login_returns_401_for_invalid_password`

## Organization

Common layout:
- `tests/unit/` for pure logic
- `tests/integration/` for DB/network boundaries
- `tests/e2e/` only when needed

## Anti-patterns

- **Test names that are too generic**: `test_works` or `test_function` hide intent.
- **Testing private methods directly**: Tests should verify public behavior, not implementation.
- **Monolithic test functions**: One test per behavior; avoid testing five things in one function.
- **Tight coupling to internal state**: Mock boundaries, not internals.

## References

- https://docs.pytest.org/
- https://en.wikipedia.org/wiki/Test-driven_development
