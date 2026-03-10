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
```
