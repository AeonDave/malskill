# Project layout and tooling

## Layout (typical)

- `src/<package>/` for library code
- `tests/` for tests
- `pyproject.toml` for tooling config

## Tooling notes

- `ruff` can replace multiple linters with one config.
- `mypy` helps for stable public APIs; keep it incremental.
- `pytest` is the default test runner ecosystem.

Keep tooling recommendations minimal and repo-appropriate.
