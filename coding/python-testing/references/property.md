# Property tests (Hypothesis)

Load when a few examples cannot cover a data space (parsers, codecs, invariants) and shrinking would help. Don't property-test every getter.

## Minimal pattern

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sort_sorted(xs: list[int]) -> None:
    ys = sorted(xs)
    assert ys == sorted(ys)
    assert set(ys) == set(xs)
```

- Assert **invariants**, not a second implementation you don't trust.
- Prefer `st` strategies that match the real input (encodings, max size). Unbounded `st.text()` / huge lists make CI slow — `max_size=` / `st.data()`.
- `@example(...)` to pin a shrink that found a bug.
- Flaky wall-clock: `@settings(deadline=None)` only for tests that must do real I/O; otherwise fix the code under test.

Hypothesis is optional (see skill compatibility). Don't add it to assert a single constant.

## References

- https://hypothesis.readthedocs.io/
