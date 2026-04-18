# Project layout and tooling

## Layout (typical)

- `src/<package>/` for library code
- `tests/` for tests
- `pyproject.toml` for tooling config

## Tooling notes

- `ruff` can replace multiple linters with one config.
- `mypy` helps for stable public APIs; keep it incremental.
- `pytest` is the default test runner ecosystem.

## Ruff configuration (pragmatic)

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N"]  # Style, undefined names, imports, naming
ignore = ["E501"]  # Line length (handled by formatter)
```

## Mypy for public APIs

- Enable on public API modules; relax for internal utilities if needed.
- Use `--disallow-untyped-defs` on strict modules.

## pytest baseline

- Run with `--cov` to track coverage trends.
- Set CI gate at minimum 80% (adjust per project).

## CI quality gates

- Ruff format and lint (non-negotiable)
- Mypy --strict on public APIs
- pytest --cov with coverage floor
- No uncommitted changes after tooling run
