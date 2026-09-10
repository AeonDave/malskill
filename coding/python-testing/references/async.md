# Async testing

If you are writing asyncio-heavy code, also load `python-async-patterns` `testing.md` (cancellation, TaskGroup, `TimeoutError`).

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
- Avoid relying on task scheduling order; use explicit `Event` or `Condition`.
- Use `AsyncMock` for async dependencies.

## Exceptions pytest will miss

- `asyncio.CancelledError` is `BaseException` — `pytest.raises(Exception)` does not match. Use `pytest.raises(asyncio.CancelledError)`.
- TaskGroup: `pytest.raises(ExceptionGroup)` or `except*`. `pytest.raises(ValueError)` does not match a `ValueError` inside a group.
- Timeouts: `pytest.raises(TimeoutError)` (builtin alias of `asyncio.TimeoutError` since 3.11).

## Common async test pitfalls

- **Auto mode in pytest-asyncio**: if multiple tests share the event loop, state can leak.
- **Real network calls**: mock `httpx` / `aiohttp`.
- **`await task.cancel()`**: `cancel()` returns `bool`; await the task.

## References

- https://pytest-asyncio.readthedocs.io/
- https://docs.python.org/3/library/unittest.mock.html#asyncio-support
