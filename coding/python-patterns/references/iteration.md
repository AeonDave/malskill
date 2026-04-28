# Iteration and collections

## Comprehensions

Good for simple transforms:

```python
names = [u.name for u in users if u.active]
```

If it becomes hard to read, use an explicit loop.

## Generators

Prefer generators for streaming large data.

```python
def lines(path: Path):
    with path.open() as f:
        for line in f:
            yield line.rstrip("\n")
```

## itertools

Use `itertools` for composable iteration (groupby, chain, islice), but don’t sacrifice clarity.
## Anti-patterns

- **Comprehensions over 2-3 lines**: Refactor to explicit loop with clear variable names.
- **Nested comprehensions**: Hard to debug and test; use explicit loops instead.
- **Generator expressions without reason**: If you materialize it immediately, use a list comprehension.

## References

- https://docs.python.org/3/library/itertools.html