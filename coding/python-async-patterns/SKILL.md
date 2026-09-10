---
name: python-async-patterns
description: "Async Python patterns for non-blocking I/O with asyncio: TaskGroup, cancellation, timeouts, backpressure, rate limiting, and safe sync/async boundaries. Use when implementing concurrent network/DB workflows or async services — not for thread/process GIL tuning (python-performance) or general Python style (python-patterns)."
license: MIT
compatibility: "Python 3.11+ (guidance baseline; current stable CPython 3.14.7). asyncio (stdlib). Optional: anyio, httpx, aiohttp, pytest-asyncio."
metadata:
  author: AeonDave
  version: "1.2"
---

# Async Python Patterns

This skill focuses on **practical asyncio patterns** for I/O-bound concurrency.

Thread/process/subinterpreter parallelism and the GIL are `python-performance` / `python-patterns` `concurrency.md`.

## When to activate

- You’re building an async service/client (HTTP, DB, queues, websockets)
- You need concurrency with limits (rate limiting, semaphores)
- You need safe cancellation and timeouts
- You suspect event loop blocking (sync call inside async path)
- A task is stuck: 3.14+ call-graph / `python -m asyncio pstree`

## Rules of engagement

- Prefer async only for **I/O-bound** workloads.
- Never block the event loop (no `time.sleep()`, no sync HTTP/DB in async code).
- Make cancellation and timeouts explicit.
- Bound concurrency; unbounded `gather()` can turn memory into a queue.
- `asyncio.CancelledError` is a **`BaseException`**. `except Exception` will not see it. Cleanup, then re-raise.
- Do not call `asyncio.get_event_loop()` to create work. From sync code use `asyncio.run()` (or `asyncio.Runner` 3.11+). Inside async code use `get_running_loop()` only when you must.

## Outcome expectations

- Concurrent I/O tasks are orchestrated with clear boundaries and failure semantics.
- Cancellation and timeouts are explicit and tested.
- Event loop is never blocked by sync calls; backpressure prevents unbounded growth.

## Recommended workflow

1. Define scope and concurrency bounds before writing async code.
2. Use TaskGroup for orchestration; avoid fire-and-forget `create_task`.
3. Apply timeouts at I/O boundaries, not broad scopes.
4. Test cancellation paths; use pytest-asyncio with function-scoped loops.
5. Profile event loop blocking; offload sync work via `to_thread()` when necessary.

## Quick patterns

### Concurrent fan-out with bounds (TaskGroup preferred)

Prefer `asyncio.TaskGroup` (Python 3.11+) for structured concurrency with clear failure propagation.

```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(fetch_url(url1))
    tg.create_task(fetch_url(url2))
# All tasks joined; exceptions aggregated as ExceptionGroup
```

For concurrency limits, add a semaphore:

```python
sem = asyncio.Semaphore(10)
async def bounded():
    async with sem:
        return await fetch_url(url)
```

### Timeouts

- Prefer `asyncio.timeout()` (3.11+) for scoped timeouts. On expiry it raises **`TimeoutError`** (builtin). `asyncio.TimeoutError` is a 3.11+ **alias** of that builtin — prefer `TimeoutError`.
- `asyncio.timeout(None)` means no timeout.

### Cancellation

- `task.cancel()` is **not awaitable**; it returns `bool` (False if already done). Then `await task` and handle `CancelledError`.
- Catch `CancelledError` only to clean up, then re-raise.

### Sync/async boundary

- Offload truly blocking work via `asyncio.to_thread()`.

## Resources

Load on demand:

- `references/foundations.md` — event loop, coroutines vs tasks, TaskGroup vs gather, 3.12 eager tasks, 3.14 call graphs
- `references/cancellation-timeouts.md` — `cancel()` / `CancelledError` / `timeout` / `uncancel`
- `references/backpressure-rate-limit.md` — queues (`QueueShutDown` 3.13+), semaphores, producer/consumer, rate limiting
- `references/sync-async-interop.md` — `to_thread`, executors, free-threaded loops (3.14)
- `references/testing.md` — pytest-asyncio and cancellation tests (pair with `python-testing`)
