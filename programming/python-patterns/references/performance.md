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

(Only after measuring.)
