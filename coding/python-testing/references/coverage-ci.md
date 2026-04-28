# Coverage and CI

## Coverage (pytest-cov)

```bash
pytest --cov=mypkg --cov-report=term-missing --cov-report=html
```

## Guidance

- Treat coverage as a signal.
- Avoid excluding code unless you have a clear policy.
- Prefer testing critical behavior over chasing percentages.

## Coverage hygiene

- Use `# pragma: no cover` sparingly (only for unreachable code).
- Aim for >80% coverage on public APIs; relax on internal utilities.
- Coverage is a signal, not a goal; write meaningful assertions, not line-hit chasing.

## CI quality gates

1. **Lint & format**: `ruff check && ruff format --check` (must pass before tests)
2. **Type check**: `mypy --strict` on public APIs
3. **Tests**: `pytest --cov=<pkg> --cov-report=term --cov-report=html`
4. **Coverage floor**: Fail if coverage drops below baseline (usually 80%)
5. **No uncommitted tool changes**: After running ruff/mypy, assert no diff

## References

- https://coverage.readthedocs.io/
- https://pytest-cov.readthedocs.io/
