# Concurrency primitives (threads, processes, interpreters)

Load when writing threaded or multiprocess Python, `concurrent.futures`, or 3.14 subinterpreters. **Not** for asyncio — that is `python-async-patterns`. Cost, GIL, and free-threading measurement: `python-performance` `gil-and-parallelism.md`.

## Contents

- [Pick the primitive](#pick-the-primitive)
- [Threads and ThreadPoolExecutor](#threads-and-threadpoolexecutor)
- [Queues](#queues)
- [Processes](#processes)
- [Subinterpreters (3.14)](#subinterpreters-314)
- [contextvars](#contextvars)

## Pick the primitive

| Need | Use |
|---|---|
| Overlap I/O, shared memory, GIL build | `ThreadPoolExecutor` / `threading` |
| CPU-bound pure Python, GIL build | `ProcessPoolExecutor` or `InterpreterPoolExecutor` (3.14+) |
| CPU-bound on a free-threaded build with GIL actually off | threads (still lock shared mutables) |
| Structured async I/O | `python-async-patterns` (`TaskGroup`) |
| Isolation without a new process (3.14) | `InterpreterPoolExecutor` / `concurrent.interpreters` |

Unbounded `threading.Thread` fan-out is a leak. Cap with an executor or a semaphore.

## Threads and ThreadPoolExecutor

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor() as ex:  # default max_workers: see below
    futs = [ex.submit(fetch, u) for u in urls]
    for fut in as_completed(futs):
        fut.result()
```

- 3.13+ default `max_workers` is `min(32, (os.process_cpu_count() or 1) + 4)`. `os.process_cpu_count()` (3.13+) is the process-visible CPU count; prefer it over `os.cpu_count()` when sizing by hand.
- `Future.cancel()` only works if the callable has **not** started. Running work is not interrupted.
- `threading.Thread(daemon=True)` does not run `atexit` / finally on interpreter shutdown — don't use daemons for work that must flush.

`threading.Barrier` for "everyone reaches this point". Don't busy-wait on a flag.

## Queues

```python
from queue import Queue, ShutDown

q: Queue[str] = Queue(maxsize=100)
# producers
q.put(item)
# shutdown (3.13+): no more puts; get remaining items
q.shutdown()  # then get() until ShutDown, or shutdown(immediate=True) to drain
```

- `queue.ShutDown` (3.13+) is raised from `put`/`get` after `Queue.shutdown()`.
- `queue.SimpleQueue` is unbounded, no `task_done`/`join`/`shutdown` — fine for simple handoff, not for backpressure.
- `multiprocessing.Queue` is **not** `queue.Queue`: no `shutdown()` / `task_done` / `join`. Close it with `.close()`.
- asyncio queues: `asyncio.Queue.shutdown` raises `asyncio.QueueShutDown` (3.13+), not `queue.ShutDown`. See `python-async-patterns`.

## Processes

```python
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

# 3.14 Unix (not macOS): default start method is forkserver, not fork
with ProcessPoolExecutor() as ex:
    ex.map(cpu_fn, items)
```

- Callables and arguments must pickle (`spawn` / `forkserver`). Use **module-level** functions.
- 3.14: to force fork, `ProcessPoolExecutor(mp_context=mp.get_context("fork"))`. Don't, if other threads exist (3.12+ `os.fork` deprecation).
- Windows / macOS: `spawn`. Guard entry with `if __name__ == "__main__"`.
- `max_workers` default is `os.process_cpu_count()` (3.13+); Windows max 61.

## Subinterpreters (3.14)

Module: **`concurrent.interpreters`** (`from concurrent import interpreters`). Not a top-level `interpreters` package.

```python
from concurrent.futures import InterpreterPoolExecutor

def cpu_fn(n: int) -> int:
    return sum(range(n))

with InterpreterPoolExecutor() as ex:
    print(ex.submit(cpu_fn, 1_000_000).result())
```

`InterpreterPoolExecutor` is a `ThreadPoolExecutor` subclass: each worker thread has its own interpreter (own GIL). Args/results are copied (pickle for most objects). Workers cannot share mutable Python objects. Extension modules may be incompatible. **Not** a security sandbox.

Lower-level:

```python
from concurrent import interpreters

def cpu_fn(n: int) -> int:
    return sum(range(n))

interp = interpreters.create()
try:
    interp.exec("print(1)")
    result = interp.call(cpu_fn, 10)
finally:
    interp.close()
```

`call` runs in the **current** OS thread (switch interpreter). `call_in_thread` starts a thread. Isolation is best-effort; C extensions can share memory.

## contextvars

Use `ContextVar` for request-scoped state instead of `threading.local` when the same context must follow asyncio tasks.

3.14 `sys.flags.thread_inherit_context` (`-X thread_inherit_context` / `PYTHON_THREAD_INHERIT_CONTEXT`):

- GIL-enabled default: **false** — new `threading.Thread` starts with an empty `contextvars.Context`.
- Free-threaded default: **true** — threads copy the caller's context at `start()`.

Don't assume either. Copy explicitly when you must: `ctx = contextvars.copy_context(); threading.Thread(target=ctx.run, args=(fn,))`.

## References

- https://docs.python.org/3/library/concurrent.futures.html
- https://docs.python.org/3/library/concurrent.interpreters.html
- https://docs.python.org/3/library/queue.html
- https://docs.python.org/3/library/multiprocessing.html
- https://docs.python.org/3/library/contextvars.html
- https://docs.python.org/3/library/os.html#os.process_cpu_count
