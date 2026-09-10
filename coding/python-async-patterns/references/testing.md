# Testing async Python

Pair with `python-testing`. This file is asyncio-specific pitfalls; fixtures and pytest commands stay there.

## pytest-asyncio

```python
import pytest

@pytest.mark.asyncio
async def test_fetch():
    result = await fetch("https://example.com")
    assert result is not None
```

Use `loop_scope="function"` (marker or config) so loops don't leak across tests.

## Avoid flakiness

- avoid real network calls in unit tests (use fakes/mocks)
- control timeouts
- avoid relying on scheduling order

## Determinism checklist

- Mock `asyncio.sleep()` and time-based operations to avoid real delays.
- Avoid relying on task scheduling order; use explicit synchronization (Event, Condition).
- Use `pytest.mark.asyncio(loop_scope="function")` to isolate event loop per test.
- Avoid pytest-asyncio auto mode if multiple tests share the same loop (use function scope).

## Testing cancellation

```python
@pytest.mark.asyncio
async def test_cancellation_cleanup():
    task = asyncio.create_task(long_operation())
    await asyncio.sleep(0)  # let it start; don't use wall-clock sleeps
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
```

`CancelledError` is `BaseException` — `pytest.raises(Exception)` will **not** match it.

TaskGroup failures: `pytest.raises(ExceptionGroup)` or `except*`. A nested `ValueError` is not caught by `pytest.raises(ValueError)`.

Timeouts: `pytest.raises(TimeoutError)` (builtin), not a distinct `asyncio.TimeoutError` type on 3.11+.

## Anti-patterns

- **Real network calls in unit tests**: use mocks (`unittest.mock.AsyncMock`).
- **Relying on `asyncio.sleep()` timing**: sleep times are not guaranteed; use Event or mock time.
- **`await task.cancel()`** in tests — `cancel()` is not awaitable.
- **Mixed sync/async fixtures**: avoid pytest fixtures that are async but don't mark scope.

## References

- https://pytest-asyncio.readthedocs.io/
- https://docs.python.org/3/library/unittest.mock.html#asyncio-support
