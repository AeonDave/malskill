# Cancellation and timeouts

## Cancellation

- In asyncio, cancellation is cooperative.
- `asyncio.CancelledError` can be raised at an `await` point.

Rule: catch it only to clean up, then re-raise.

```python
try:
    await do_work()
except asyncio.CancelledError:
    await cleanup()
    raise
```

## Timeouts (Python 3.11+)

Prefer `asyncio.timeout()` for scoped timeouts.

```python
async with asyncio.timeout(2.0):
    await slow_op()
```

Fallback (older): `asyncio.wait_for()`

```python
await asyncio.wait_for(slow_op(), timeout=2.0)
```

## Timeout hygiene

- Apply timeouts at network boundaries.
- Don’t wrap huge call chains with one big timeout unless you truly want that behavior.

## References

- https://docs.python.org/3/library/asyncio-task.html#timeouts
