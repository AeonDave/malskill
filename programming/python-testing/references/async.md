# Async testing

If you are writing asyncio-heavy code, also consider `python-async-patterns`.

## pytest-asyncio

```python
import pytest

@pytest.mark.asyncio
async def test_async_fn():
    assert await async_fn() == 1
```

## Determinism checklist

- Use `pytest.mark.asyncio(loop_scope="function")` to isolate loop per test.
- Mock `asyncio.sleep()` and time-based operations to avoid real delays.
- Avoid relying on task scheduling order; use explicit `Event` or `Condition` for coordination.
- Use `AsyncMock` for async dependencies.

## Common async test pitfalls

- **Auto mode in pytest-asyncio**: If multiple tests share the event loop, state can leak between tests.
- **Real network calls in tests**: Always mock `httpx`, `aiohttp`, etc.
- **Mixing sync and async fixtures**: Avoid; keep fixtures consistently typed.

## References

- https://pytest-asyncio.readthedocs.io/
- https://docs.python.org/3/library/unittest.mock.html#asyncio-support
