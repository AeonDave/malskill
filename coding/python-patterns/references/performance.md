# Performance (stay here only for the rule)

Measurement, GIL, free-threading, JIT, and profilers live in **`python-performance`**. Load that skill when the task is a hotspot, a regression, or a parallelism choice driven by the GIL.

Here:

- Don't micro-optimize without a profile.
- Fix the algorithm and I/O first.
- `slots=True` / generators / `"".join` are mentioned in `data-models.md` and `iteration.md` — apply them when the type or loop is actually hot.

If you already know the bottleneck is CPU-bound Python, read `python-performance` `gil-and-parallelism.md` before adding threads.
