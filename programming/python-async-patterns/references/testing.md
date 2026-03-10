# Testing async Python

## pytest-asyncio

```python
import pytest

@pytest.mark.asyncio
async def test_fetch():
    result = await fetch("https://example.com")
    assert result is not None
```

## Avoid flakiness

- avoid real network calls in unit tests (use fakes/mocks)
- control timeouts
- avoid relying on scheduling order

## References

- https://pytest-asyncio.readthedocs.io/
