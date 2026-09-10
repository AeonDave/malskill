# Profiling CPython

Load when you need commands and a measurement loop. Parallelism choice is `gil-and-parallelism.md`.

## Contents

- [Baseline](#baseline)
- [cProfile](#cprofile)
- [py-spy](#py-spy)
- [tracemalloc](#tracemalloc)
- [scalene](#scalene)
- [Anti-patterns](#anti-patterns)

## Baseline

```bash
python -m timeit -s "from pkg import fn" "fn(data)"
```

Keep the input representative. Micro-`timeit` on tiny N lies. Record Python version (`python -VV`) and whether the build is free-threaded.

## cProfile

```bash
python -m cProfile -o out.prof script.py
python -c "import pstats; p=pstats.Stats('out.prof'); p.sort_stats('cumtime').print_stats(30)"
```

In-process:

```python
import cProfile
cProfile.run("hot()")
```

`cumtime` is inclusive; `tottime` is exclusive. Fix the function that owns `tottime` first unless a caller is doing too much work in a loop.

`cProfile` adds overhead and serializes poorly with threads. Prefer `py-spy` for a live multi-thread process.

## py-spy

Sampling profiler; attach without restarting when permissions allow.

```bash
py-spy record -o profile.svg -- python script.py
py-spy top --pid <pid>
py-spy dump --pid <pid>
```

For a live multi-thread process, sampling (py-spy) shows where threads actually run; if cores stay idle on CPU-bound Python, read `gil-and-parallelism.md`.

## tracemalloc

```python
import tracemalloc

tracemalloc.start()
# ... workload ...
snap = tracemalloc.take_snapshot()
for stat in snap.statistics("lineno")[:15]:
    print(stat)
```

Compare two snapshots for leaks vs one-shot churn. Peak RSS without a snapshot is not a leak.

## scalene

Use when you need combined CPU + Python-vs-C + allocation lines and you already depend on it. Do not add it to a project just to look around; `cProfile` + `tracemalloc` is enough for a first pass.

## Anti-patterns

- Optimizing without a profile.
- Comparing numbers across GIL vs free-threaded builds without labeling the build.
- Using `time.time()` around a single run on a noisy laptop as the only evidence.

## References

- https://docs.python.org/3/library/profile.html
- https://docs.python.org/3/library/tracemalloc.html
- https://docs.python.org/3/library/timeit.html
