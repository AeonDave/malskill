# Asyncio foundations

## Contents

- [Coroutines vs tasks](#coroutines-vs-tasks)
- [Structured concurrency (Python 3.11+)](#structured-concurrency-python-311)
- [gather() vs TaskGroup](#gather-vs-taskgroup)
- [TaskGroup semantics (Python 3.11+)](#taskgroup-semantics-python-311)
- [Eager task factory (3.12+)](#eager-task-factory-312)
- [Call-graph introspection (3.14+)](#call-graph-introspection-314)
- [Common gotchas](#common-gotchas)
- [Anti-patterns](#anti-patterns)

## Coroutines vs tasks

- A coroutine is created by calling an `async def` function.
- A task schedules a coroutine to run concurrently on the event loop.

```python
coro = fetch(url)
task = asyncio.create_task(fetch(url))

result = await coro
result2 = await task
```

Entry from sync code: `asyncio.run(main())`. `asyncio.Runner` (3.11+) when you must run several top-level coroutines on one loop. Do not use `get_event_loop().run_until_complete(...)` in new code.

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

## TaskGroup semantics (Python 3.11+)

TaskGroup uses **exception groups** to aggregate errors from multiple concurrent tasks.

```python
from asyncio import TaskGroup

try:
    async with TaskGroup() as tg:
        tg.create_task(task1())
        tg.create_task(task2())
except* OSError as eg:
    ...
except ExceptionGroup as eg:
    for exc in eg.exceptions:
        print(f"Task failed: {exc}")
```

`except Exception` does **not** match exceptions nested in an `ExceptionGroup` — use `except*` or catch `ExceptionGroup`. See `python-patterns` `errors.md`.

Safer than `gather(return_exceptions=True)` because:

- Failures are explicit and grouped.
- Siblings are automatically cancelled on first failure.
- Cancellation is not swallowed (`CancelledError` is `BaseException`).

3.13+: TaskGroup colliding with outer cancellation preserves `cancelling()` counts so cancellation is not lost.

## Eager task factory (3.12+)

```python
loop = asyncio.get_running_loop()
loop.set_task_factory(asyncio.eager_task_factory)
```

Coroutines start **synchronously** during `Task` construction and only schedule if they block. Wins when many tasks complete without I/O (caches). Opt-in; don't set globally unless measured. `asyncio.create_eager_task_factory` when you need to wrap an existing factory.

## Call-graph introspection (3.14+)

Stuck task in-process:

```python
asyncio.print_call_graph()  # current task
asyncio.capture_call_graph(task)
```

Another process: `python -m asyncio pstree <pid>` or `python -m asyncio ps <pid>`.

## Common gotchas

- Forgetting `await` returns a coroutine object.
- Creating tasks without awaiting them can leak work.
- Using blocking calls inside async code stalls all tasks.

## Anti-patterns

- **Fire-and-forget tasks**: untracked `create_task()` without owning cancellation. Use TaskGroup.
- **Unbounded gather()**: hundreds of tasks without a semaphore.
- **Blocking inside async**: `requests.get()` or `time.sleep()` stalls the loop.
- **`get_event_loop()` to spawn work** from sync code.

## References

- https://docs.python.org/3/library/asyncio-task.html
- https://docs.python.org/3/library/asyncio-runner.html
- https://docs.python.org/3/library/asyncio-graph.html
- https://docs.python.org/3/library/asyncio-exceptions.html
