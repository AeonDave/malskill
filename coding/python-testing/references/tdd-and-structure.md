# TDD and test structure

## TDD (red → green → refactor)

Load [test-driven-development](../../test-driven-development/SKILL.md) for the shared workflow, including existing implementations and behavior-preserving refactors. Keep pytest setup and organization here.

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
