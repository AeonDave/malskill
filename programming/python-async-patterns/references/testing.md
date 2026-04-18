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

## Determinism checklist

- Mock `asyncio.sleep()` and time-based operations to avoid real delays.
- Avoid relying on task scheduling order; use explicit synchronization (Event, Condition).
- Use `pytest.mark.asyncio(loop_scope="function")` to isolate event loop per test.
- Avoid `pytest-asyncio` auto mode if multiple tests share the same loop (use function scope).

## Testing cancellation

```python
@pytest.mark.asyncio
async def test_cancellation_cleanup():
    task = asyncio.create_task(long_operation())
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    # Verify cleanup occurred
```

## Anti-patterns

- **Real network calls in unit tests**: Use mocks (`unittest.mock.AsyncMock`).
- **Relying on `asyncio.sleep()` timing**: Sleep times are not guaranteed; use Event or mock time.
- **Mixed sync/async fixtures**: Avoid pytest fixtures that are async but don't explicitly mark scope.

## References

- https://pytest-asyncio.readthedocs.io/
- https://docs.python.org/3/library/unittest.mock.html#asyncio-support
