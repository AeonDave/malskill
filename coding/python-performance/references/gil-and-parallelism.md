# GIL, free-threading, and parallelism cost

Load when CPU-bound work must use more than one core, or when someone claims "threads don't parallelize" / "the GIL is gone". API choice (executors, queues, start methods) is `python-patterns` `concurrency.md`.

## Contents

- [Facts that change the fix](#facts-that-change-the-fix)
- [Which build am I on?](#which-build-am-i-on)
- [Default GIL build](#default-gil-build)
- [Free-threaded build](#free-threaded-build)
- [Subinterpreters](#subinterpreters)
- [Process pools](#process-pools)
- [Sizing](#sizing)

## Facts that change the fix

- The **default** CPython build still has a GIL as of 3.14. Threads interleave bytecode; they do **not** run CPU-bound pure-Python in parallel.
- Threads **do** overlap I/O and C extensions that release the GIL (`time.sleep`, much of numpy/I/O).
- **Free-threaded** CPython (`--disable-gil`, usually `python3.13t` / `python3.14t`) is a **separate ABI**. It is not the default executable.
  - 3.13: experimental; expect bugs and a **substantial** single-thread hit.
  - 3.14: PEP 779 phase II — **officially supported, still optional**. Single-thread penalty roughly **5–10%**. Specializing interpreter is enabled. Not the default; phase III (default no-GIL) is not decided.
- Importing a C extension that is not marked free-thread-safe **re-enables the GIL** at runtime (warning printed). Then threads stop scaling even on a `t` binary.
- **JIT is incompatible with free-threaded builds** (3.14). Do not combine them.

## Which build am I on?

```python
import sys, sysconfig

sysconfig.get_config_var("Py_GIL_DISABLED")  # 1 => free-threaded *build*; recommended check
sys._is_gil_enabled()  # False => GIL currently off (runtime; can disagree with the build)
```

`python -VV` / `sys.version` contain `free-threading build` on those binaries. 3.13 strings said `experimental free-threading build`.

Runtime override on a free-threaded binary: `PYTHON_GIL=1` or `-X gil=1` turns the GIL back on. `PYTHON_GIL=0` / `-X gil=0` requests it off (importing an unmarked extension can still force it on).

C extensions that support no-GIL declare `Py_mod_gil`. From 3.14 on Windows, the build backend must define `Py_GIL_DISABLED` when compiling for the free-threaded ABI.

## Default GIL build

| Workload | Mechanism |
|---|---|
| I/O-bound | `threading` / `ThreadPoolExecutor` / asyncio |
| CPU-bound pure Python | `ProcessPoolExecutor` or (3.14+) `InterpreterPoolExecutor` |
| CPU-bound in a GIL-releasing C ext | threads can scale; measure |

Do not spawn a thread per tiny CPU item. Batch.

## Free-threaded build

Use when the program is **already threaded**, the hot path is **Python bytecode** (or GIL-holding C), and you can run a `t` interpreter with **compatible wheels**.

- Shared mutable Python objects need real synchronization (`threading.Lock`, queues). The GIL was a crude mutex; it is gone only while `sys._is_gil_enabled()` is false.
- 3.14 free-threaded default: `sys.flags.thread_inherit_context` is true (threads copy the caller's `contextvars` at `start()`). GIL builds default that flag false (`-X thread_inherit_context` / `PYTHON_THREAD_INHERIT_CONTEXT`).
- Unmarked C extensions: treat GIL re-enable as a failed experiment, not "threads are slow".
- Do not promise speedups without a before/after on the **same** workload.

## Subinterpreters

Per-interpreter GIL exists since 3.12 (PEP 684). Stdlib API is 3.14:

- `concurrent.futures.InterpreterPoolExecutor` — `ThreadPoolExecutor` subclass; each worker thread has its **own interpreter** (own GIL) → true multi-core for isolated callables.
- `concurrent.interpreters` — create/switch/call; **no concurrency by itself**. Parallelism needs threads (`call_in_thread` or the executor).

Cost vs processes: in-process, less RAM than N processes, but:

- arguments/results are copied (pickle for most objects; a few immutables share)
- extension modules often are **not** isolated yet
- interpreter startup is **not** optimized in 3.14
- **not** a security boundary

Prefer `InterpreterPoolExecutor` over hand-rolling interpreters unless you need custom sharing via `create_queue()`.

## Process pools

Still the portable CPU-bound tool on the default GIL build and when extensions cannot isolate.

- 3.14: `ProcessPoolExecutor` / `multiprocessing` default start method on Unix **except macOS** is **`forkserver`**, not `fork`. Windows/macOS stay **`spawn`**.
- 3.12+: `fork` in a **multi-threaded** process is a `DeprecationWarning` (`os.fork`). Pass `mp_context=multiprocessing.get_context("fork")` only if you truly need fork and have no other threads.
- Workers must pickle callables and args (`spawn`/`forkserver`). Closures and unpicklable sockets fail — use module-level functions.

## Sizing

- `os.process_cpu_count()` (3.13+) — CPUs **available to this process** (affinity/cgroup). Prefer this over `os.cpu_count()` for pool size.
- `ThreadPoolExecutor` default `max_workers` (3.13+): `min(32, (os.process_cpu_count() or 1) + 4)`.
- `ProcessPoolExecutor` default: `os.process_cpu_count()`; Windows capped at 61.

## References

- https://docs.python.org/3/howto/free-threading-python.html
- https://peps.python.org/pep-0703/
- https://peps.python.org/pep-0779/
- https://docs.python.org/3/library/concurrent.futures.html
- https://docs.python.org/3/library/concurrent.interpreters.html
- https://docs.python.org/3/whatsnew/3.14.html
