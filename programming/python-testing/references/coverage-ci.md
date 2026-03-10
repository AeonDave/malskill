# Coverage and CI

## Coverage (pytest-cov)

```bash
pytest --cov=mypkg --cov-report=term-missing --cov-report=html
```

## Guidance

- Treat coverage as a signal.
- Avoid excluding code unless you have a clear policy.
- Prefer testing critical behavior over chasing percentages.

## CI

Run at least:
- `pytest`
- optional: `pytest -q` and a coverage step
