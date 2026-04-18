# pytest command recipes

```bash
# Run all tests
pytest

# Verbose
pytest -v

# Select by substring
pytest -k "parse"

# Select by marker
pytest -m "not slow"

# Stop on first failure
pytest -x

# Run last failures
pytest --lf

# Drop into debugger on failure
pytest --pdb

# Coverage report
pytest --cov=mypkg --cov-report=html

# Run with strict markers (fail on typos)
pytest --strict-markers
```

## Tips

- Use `-v` in CI to debug test failures quickly.
- Use `-x` locally to fail fast while developing.
- Use `--lf` to re-run only tests that failed last run.
- Use `pytest --co` to list all tests without running them (useful for validation).

## References

- https://docs.pytest.org/en/stable/reference.html
