# Cancellation and timeouts

## Cancellation

Cancellation is cooperative. `CancelledError` is injected at an `await` point.

`Task.cancel(msg=None)` returns `True` if a cancel was scheduled, `False` if the task is already done. **It is not a coroutine — do not `await task.cancel()`.**

```python
task.cancel()
try:
    await task
except asyncio.CancelledError:
    await cleanup()
    raise
```

Rule: catch `CancelledError` only to clean up, then re-raise. It is a `BaseException`; `except Exception` will not catch it.

`Task.uncancel()` / `cancelling()` (3.11+) decrement/read the cancel request count. They exist so **TaskGroup and `asyncio.timeout` can isolate cancellation**. Application code should not call `uncancel()` to "keep going after cancel" except when implementing a similar structured block.

3.13+: `uncancel()` may clear an internal `_must_cancel` flag when the count hits zero so nested groups don't swallow outer cancellation.

## Timeouts (Python 3.11+)

Prefer `asyncio.timeout()` for scoped timeouts.

```python
async with asyncio.timeout(2.0):
    await slow_op()
```

Expiry raises **`TimeoutError`** (builtin). `asyncio.TimeoutError` is an alias since 3.11 — write `TimeoutError`.

`asyncio.timeout(None)` disables the timeout (infinite). Don't pass 0 thinking it means "no timeout".

`asyncio.timeout_at(when)` for an absolute loop clock deadline.

Fallback (older): `asyncio.wait_for()` — also raises `TimeoutError`; it **cancels** the inner awaitable.

## Timeout hygiene

- Apply timeouts at network boundaries.
- Don't wrap huge call chains with one big timeout unless you truly want that behavior.

## Context-aware cancellation

For library code, prefer an optional timeout the **caller** owns:

```python
async def fetch(url: str, *, timeout: float | None = None) -> bytes:
    async with asyncio.timeout(timeout):
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            return resp.content
```

## Shield

`asyncio.shield(aw)` delays cancellation of `aw` until it finishes; the **caller** can still be cancelled and will wait. Use only for a short critical section (flush). Shielding a whole request hides Ctrl-C and TaskGroup shutdown.

## Anti-patterns

- **`await task.cancel()`**: `cancel()` returns `bool`. Await the **task**, not cancel.
- **Timeout on a whole chain** unless you want all-or-nothing.
- **Swallowing `CancelledError`**: always re-raise after cleanup.
- **Catching `asyncio.TimeoutError` as if it were distinct** from `TimeoutError` on 3.11+.

## References

- https://docs.python.org/3/library/asyncio-task.html#task-cancellation
- https://docs.python.org/3/library/asyncio-task.html#timeouts
- https://docs.python.org/3/library/asyncio-exceptions.html
