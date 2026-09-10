# Backpressure and rate limiting

## Bound concurrency with a semaphore

```python
sem = asyncio.Semaphore(10)

async def bounded_call(x):
    async with sem:
        return await call(x)
```

## Producer/consumer with asyncio.Queue

Use a bounded queue to avoid unbounded memory growth.

```python
q: asyncio.Queue[int] = asyncio.Queue(maxsize=100)

async def producer():
    for i in range(1000):
        await q.put(i)
    q.shutdown()  # 3.13+: further put() raises; get() raises QueueShutDown once empty

async def consumer():
    try:
        while True:
            i = await q.get()
            try:
                await handle(i)
            finally:
                q.task_done()
    except asyncio.QueueShutDown:
        return
```

- `asyncio.Queue.shutdown(immediate=False)` (3.13+) — not `queue.Queue.shutdown`. The exception is **`asyncio.QueueShutDown`**, not `queue.ShutDown`.
- `immediate=True` drains the queue and unblocks `join()` even if `task_done` was never called — don't use it if you still need "all work finished".

## Rate limiting

- Concurrency limits are not the same as rate limits.
- For a simple token bucket, track timestamps and sleep; for robust needs, use a dedicated library.

## References

- https://docs.python.org/3/library/asyncio-queue.html
