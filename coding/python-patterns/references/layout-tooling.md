# Project layout and tooling

## Layout (typical)

- `src/<package>/` for library code
- `tests/` for tests
- `pyproject.toml` for project metadata and tooling (PEP 621)

Read config with stdlib `tomllib` (3.11+, read-only). Do not add `tomli` on 3.11+. Writing TOML needs a third-party writer.

Dev-only tools: prefer PEP 735 `[dependency-groups]` when the installer supports it; don't overload `[project.optional-dependencies]` as a test-runner extra unless consumers install that extra.

## Removed stdlib (don't import)

- `distutils` — removed in 3.12. Use packaging / setuptools / `pyproject.toml`.
- PEP 594 "dead batteries" (`cgi`, `imghdr`, `audioop`, …) — **removed in 3.13**. Use PyPI replacements if you still need them.
- `Path` as a context manager — removed in 3.13 (it never closed anything).

Don't add `setup.py` unless an existing tool requires it.

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
select = ["E", "F", "W", "I", "N"]
ignore = ["E501"]
```

Raise `target-version` to the oldest Python you actually support (`py312` / `py314`) so ruff can flag APIs you cannot use.

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
