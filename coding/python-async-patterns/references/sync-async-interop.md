# Sync/async interoperability

## Don't block the event loop

Blocking examples:

- `time.sleep()`
- sync HTTP clients (`requests`) used inside async functions
- CPU-heavy loops

## Offload blocking work

### to_thread (Python 3.9+)

```python
result = await asyncio.to_thread(blocking_fn, arg1, arg2)
```

Use when:

- you must use a sync library
- the operation is short enough that threads are acceptable

CPU-bound pure Python on a GIL build will **not** scale in `to_thread`; use `ProcessPoolExecutor` / `InterpreterPoolExecutor` from `python-patterns` `concurrency.md` (loop: `asyncio.get_running_loop().run_in_executor(...)`).

## Executors

Use executors for fine control or process pools for CPU work. Don't call `run_in_executor` without a running loop (`get_event_loop()` in a fresh thread is the old trap).

## Free-threaded asyncio (3.14)

On a free-threaded build with the GIL actually off, asyncio documents first-class support: **multiple event loops on different threads** can run in parallel. That does not make a single loop multi-core. Don't share one loop across threads. See `python-performance` `gil-and-parallelism.md`.

## References

- https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread
- https://docs.python.org/3/library/asyncio-runner.html
