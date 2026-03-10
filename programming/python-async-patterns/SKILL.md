---
name: python-async-patterns
description: "Async Python patterns for building non-blocking I/O with asyncio and async/await: task orchestration, cancellation, timeouts, backpressure, rate limiting, and safe sync/async boundaries. Use when implementing concurrent network/DB workflows or async services."
license: MIT
compatibility: "Python 3.11+ (guidance baseline). asyncio (stdlib). Optional: anyio, httpx, aiohttp, pytest-asyncio."
metadata:
  author: AeonDave
  version: "1.0"
---

# Async Python Patterns

This skill focuses on **practical asyncio patterns** for I/O-bound concurrency.

## When to activate

- You’re building an async service/client (HTTP, DB, queues, websockets)
- You need concurrency with limits (rate limiting, semaphores)
- You need safe cancellation and timeouts
- You suspect event loop blocking (sync call inside async path)

## Rules of engagement

- Prefer async only for **I/O-bound** workloads.
- Never block the event loop (no `time.sleep()`, no sync HTTP/DB in async code).
- Make cancellation and timeouts explicit.
- Bound concurrency; unbounded `gather()` can turn memory into a queue.

## Quick patterns

### Concurrent fan-out with bounds

- Use `asyncio.TaskGroup` (Python 3.11+) for structured concurrency.
- Use a semaphore for concurrency limits.

### Timeouts

- Prefer `asyncio.timeout()` (3.11+) for scoped timeouts.

### Cancellation

- Catch `asyncio.CancelledError` only to clean up, then re-raise.

### Sync/async boundary

- Offload truly blocking work via `asyncio.to_thread()`.

## Resources

Load on demand:

- `references/foundations.md` — event loop, coroutines vs tasks, TaskGroup vs gather
- `references/cancellation-timeouts.md` — cancellation semantics and timeout patterns
- `references/backpressure-rate-limit.md` — queues, semaphores, producer/consumer, rate limiting
- `references/sync-async-interop.md` — to_thread, executors, avoiding hidden blocking
- `references/testing.md` — testing async code patterns (pytest-asyncio) and flake avoidance
