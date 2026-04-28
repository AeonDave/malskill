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

async def consumer():
    while True:
        i = await q.get()
        try:
            await handle(i)
        finally:
            q.task_done()
```

## Rate limiting

- Concurrency limits are not the same as rate limits.
- For a simple token bucket, track timestamps and sleep; for robust needs, use a dedicated library.

## References

- https://docs.python.org/3/library/asyncio-queue.html
