# Async testing

If you are writing asyncio-heavy code, also consider `python-async-patterns`.

## pytest-asyncio

```python
import pytest

@pytest.mark.asyncio
async def test_async_fn():
    assert await async_fn() == 1
```

## Flake avoidance

- Don’t rely on scheduling order.
- Use timeouts explicitly.
- Prefer deterministic fakes over real network.
