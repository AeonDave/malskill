# Performance (pragmatic)

## Rules

- Measure before optimizing (profilers, not guesses).
- Optimize the algorithm before micro-optimizing.
- Avoid building huge intermediate lists when a generator works.

## Common wins

- Use `"".join(...)` instead of string concatenation in loops.
- Prefer local variables in hot loops (minor, only when measured).
- Use `slots=True` on many-instance dataclasses.

## Notes

If the workload is CPU-bound, consider:
- `multiprocessing`
- vectorization (numpy)
- moving hotspots to Rust/C

## Profiling workflow

1. Identify the bottleneck with `cProfile` or `py-spy`.
2. Measure before and after each change.
3. Avoid micro-optimizations without evidence.

## Anti-patterns

- **Premature optimization**: Optimize where measurement shows slowness, not guesses.
- **Building huge intermediate lists in loops**: Use generators or list comprehensions carefully.
- **Ignoring algorithmic complexity**: An O(n²) bug beats any micro-optimization.

## When to move to compiled languages

Only after profiling shows CPU-bound hotspot that can't be improved in Python:
- CPU-heavy math → consider numpy or Rust
- Memory-intensive tasks → consider Cython or C extensions
- Tight loops → measure first
