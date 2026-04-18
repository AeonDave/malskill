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

## TaskGroup semantics (Python 3.11+)

TaskGroup uses **exception groups** to aggregate errors from multiple concurrent tasks.

```python
from asyncio import TaskGroup

try:
    async with TaskGroup() as tg:
        tg.create_task(task1())  # fails
        tg.create_task(task2())  # fails
except ExceptionGroup as eg:
    for exc in eg.exceptions:
        print(f"Task failed: {exc}")
```

This is safer than `gather(return_exceptions=True)` because:
- Failures are explicit and grouped.
- Siblings are automatically cancelled on first failure.
- No accidental swallowing of cancellation signals.

## Anti-patterns

- **Fire-and-forget tasks**: Create untracked work via `create_task()` without owning cancellation. Use TaskGroup to own the scope.
- **Unbounded gather()**: Launching hundreds of tasks without semaphore leads to resource exhaustion.
- **Blocking inside async**: `requests.get()` or `time.sleep()` inside async function stalls the entire event loop.

## References

- https://docs.python.org/3/library/asyncio-task.html
- https://docs.python.org/3/library/asyncio-exceptions.html#exception-groups
