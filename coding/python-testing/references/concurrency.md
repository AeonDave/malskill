# Concurrency and free-threaded tests

Load when tests start threads, process/interpreter pools, or must pass on a free-threaded CPython build. Async cancellation stays in `async.md` / `python-async-patterns`.

## Contents

- [Don't sleep](#dont-sleep)
- [Shared state](#shared-state)
- [Free-threaded CI](#free-threaded-ci)
- [Process and interpreter pools](#process-and-interpreter-pools)

## Don't sleep

Use `threading.Event` / `Barrier` to wait for a worker. `time.sleep(0.1)` flakes under load and hides deadlocks.

```python
done = threading.Event()

def worker():
    try:
        run()
    finally:
        done.set()

t = threading.Thread(target=worker)
t.start()
assert done.wait(timeout=2)
t.join()
```

Fail the test on timeout; don't extend the sleep.

## Shared state

Default GIL serializes bytecode; a race can still pass locally and fail on `python3.14t`. Tests that mutate module globals, caches, or singleton clients must isolate (unique object per test, or a lock the production code actually uses).

`pytest-xdist` is **process** isolation (`-n auto`), not a thread-safety proof.

Prefer asserting outcomes, not `Mock.call_count`, when many threads hit a mock.

## Free-threaded CI

Optional extra job:

```bash
python3.14t -c "import sys,sysconfig; assert sysconfig.get_config_var('Py_GIL_DISABLED')==1"
python3.14t -m pytest
```

If `sys._is_gil_enabled()` is unexpectedly true, an imported C extension re-enabled the GIL — the job is not testing free-threading. See `python-performance` `gil-and-parallelism.md`.

Do not skip locking tests "because we have the GIL".

## Process and interpreter pools

- `ProcessPoolExecutor` / `multiprocessing`: callables must be picklable (module-level). 3.14 Unix default start method is `forkserver` — watch `NameError` / pickling failures that `fork` used to hide.
- `InterpreterPoolExecutor` (3.14): same pickling/isolation rules; don't expect in-memory object identity across workers.

## References

- https://docs.python.org/3/howto/free-threading-python.html
- https://docs.python.org/3/library/threading.html
- https://docs.python.org/3/library/concurrent.futures.html
