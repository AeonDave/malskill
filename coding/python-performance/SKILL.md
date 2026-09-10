---
name: python-performance
description: "Python performance workflow: measure with profilers, then cut allocations, pick the right parallelism (threads vs processes vs subinterpreters vs free-threading), and only then touch experimental JIT/runtime knobs. Use after you have evidence CPython is the bottleneck — not for style or API design."
license: MIT
compatibility: "Python 3.11+ (guidance baseline; current stable CPython 3.14.7). Tools: cProfile, timeit, tracemalloc. Optional: py-spy, scalene, free-threaded `python3.14t`, experimental `PYTHON_JIT`."
metadata:
  author: AeonDave
  version: "1.0"
---

# Python Performance

This skill is **measurement-first optimization** in CPython.

If the task is idioms, typing, or packaging, use `python-patterns`. If it is asyncio orchestration, use `python-async-patterns`. Primitive choice (which executor, queue shutdown, start method) lives in `python-patterns` `concurrency.md`; this skill is cost, GIL, and measurement.

## When to activate

- Confirming a latency, throughput, CPU, or memory regression in Python
- Deciding whether threads, processes, subinterpreters, or a free-threaded build will actually parallelize
- Profiling a hot path before and after a change
- Evaluating experimental JIT or other runtime knobs

## Rules of engagement

- **Profile before changing code.** Algorithm and I/O dominate micro-tweaks.
- **Change one variable at a time.** Keep a before/after number.
- Optimize the proven hot path, not code that merely looks slow.
- Do not treat free-threading or the JIT as default. Both are opt-in; JIT is experimental.

## Outcome expectations

- Claims have a reproducible before/after measurement.
- Parallelism choice matches GIL state (`sysconfig.get_config_var("Py_GIL_DISABLED")` vs `sys._is_gil_enabled()`).
- Experimental flags stay labeled experimental.

## Workflow

1. Make the symptom measurable (`timeit`, a benchmark script, or a representative load).
2. Capture evidence: CPU (`cProfile` / `py-spy`), allocations (`tracemalloc`).
3. Classify: algorithm, I/O wait, GIL serialization, allocation churn, or lock contention.
4. Apply one targeted fix. Re-measure.
5. Only then consider runtime builds (free-threaded) or experimental JIT.

## Symptom to first tool

- High CPU in Python frames -> `cProfile` or `py-spy record`
- Many cores idle on threaded CPU work -> GIL / parallelism (`gil-and-parallelism.md`)
- RSS growth or allocation churn -> `tracemalloc`, then `allocations-gc.md`
- Event-loop stalls -> `python-async-patterns` (don't block the loop); profile with `py-spy`
- Shipped binary already profile-tuned -> `compiler-and-runtime.md`

## Resources

Load on demand:

- `references/profiling.md` — load when choosing cProfile, py-spy, scalene, or tracemalloc
- `references/gil-and-parallelism.md` — load for GIL, free-threading (3.13 experimental / 3.14 supported optional), `InterpreterPoolExecutor`, multiprocessing vs threads
- `references/allocations-gc.md` — load for allocation churn, `gc`, `slots`, caches
- `references/compiler-and-runtime.md` — load for experimental JIT (`PYTHON_JIT`), tail-call interpreter, PGO; not for first-pass code fixes
