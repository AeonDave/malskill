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

Keep tests near the public behavior; don’t couple tests to private implementation details.
