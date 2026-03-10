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
