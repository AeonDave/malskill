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

## Context-aware cancellation

For library code, prefer to accept an optional cancellation token or timeout parameter:

```python
async def fetch(url: str, *, timeout: float | None = None) -> bytes:
    async with asyncio.timeout(timeout):
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            return resp.content
```

Caller controls the deadline, not the callee.

## Anti-patterns

- **Bare `await task.cancel()` without awaiting cancellation result**: The task may not stop immediately.
- **Timeout on a whole chain of operations**: Unless you truly want all-or-nothing, apply timeouts at leaf boundaries (network calls, DB operations).
- **Ignoring CancelledError**: Always re-raise after cleanup to propagate the cancellation signal upward.

## References

- https://docs.python.org/3/library/asyncio-task.html#timeouts
- https://docs.python.org/3/library/asyncio-task.html#cancellation
