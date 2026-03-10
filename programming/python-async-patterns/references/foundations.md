# Asyncio foundations

## Coroutines vs tasks

- A coroutine is created by calling an `async def` function.
- A task schedules a coroutine to run concurrently on the event loop.

```python
coro = fetch(url)
task = asyncio.create_task(fetch(url))

result = await coro
result2 = await task
```

## Structured concurrency (Python 3.11+)

Prefer `asyncio.TaskGroup` when you own the orchestration.

```python
async with asyncio.TaskGroup() as tg:
    t1 = tg.create_task(fetch(a))
    t2 = tg.create_task(fetch(b))
# if one fails, the group cancels siblings
```

## gather() vs TaskGroup

- `asyncio.gather()` is fine for quick fan-out, but error handling and cancellation are easier to reason about with TaskGroup.
- Prefer TaskGroup when you need clear failure semantics.

## Common gotchas

- Forgetting `await` returns a coroutine object.
- Creating tasks without awaiting them can leak work.
- Using blocking calls inside async code stalls all tasks.

## References

- https://docs.python.org/3/library/asyncio-task.html
