# Allocations and GC

Load when the profile is allocation churn, RSS growth, or GC pauses — not for first-pass algorithm fixes.

## Contents

- [Churn vs retention](#churn-vs-retention)
- [Hot-path allocations](#hot-path-allocations)
- [Caches](#caches)
- [GC](#gc)

## Churn vs retention

- **Churn**: many short-lived objects → high `tracemalloc` / `gc` counts, CPU in `gc` / allocators.
- **Retention**: objects that live forever → RSS grows; compare two `tracemalloc` snapshots.

Fix churn by reusing buffers and avoiding per-item containers. Fix retention by dropping references (caches, cycles, attached logs).

## Hot-path allocations

- Pre-size lists when the length is known (`[0] * n` or `list.append` in a loop is fine; don't build huge intermediates you immediately discard — generators / `itertools` belong in `python-patterns` `iteration.md`).
- `"".join(parts)` for many small strings; `+=` in a loop allocates repeatedly.
- `@dataclass(slots=True)` for **many** instances (memory). Idiom lives in `python-patterns` `data-models.md`; measure if the type is not on the hot path.
- Local names in a tight loop are a last-resort micro-opt; only after a profile says attribute lookup dominates.

## Caches

- `functools.cache` is `lru_cache(maxsize=None)` — **unbounded**. Use only when the key set is bounded.
- `functools.lru_cache(maxsize=...)` for bounded memoization. Free-threaded 3.14 fixed races in `lru_cache`; still don't use a cache as a lock.
- Don't cache large objects keyed by unbounded user input (memory DoS).

## GC

Cyclic GC is generational. Tune only when `gc` is in the profile.

- `gc.disable()` is for short-lived scripts that create no cycles, not for servers.
- `gc.freeze()` (after import) keeps startup objects out of later collections — rare, measure.
- **3.14.0–3.14.4 shipped an incremental GC, then 3.14.5 reverted to the 3.13 generational GC** because of production memory pressure. Do **not** write code that depends on incremental-GC `gc.collect(1)` semantics. Target 3.14.5+ / 3.13 behavior.
- Do not cargo-cult `gc.set_threshold` without `gc.get_stats()` before/after.

## References

- https://docs.python.org/3/library/gc.html
- https://docs.python.org/3/library/functools.html#functools.lru_cache
- https://docs.python.org/3/whatsnew/3.14.html (Garbage collection / 3.14.5 revert)
