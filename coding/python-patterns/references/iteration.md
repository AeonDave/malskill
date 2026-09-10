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

Use `itertools` for composable iteration (`groupby`, `chain`, `islice`), but don't sacrifice clarity.

`itertools.batched(iterable, n)` (3.12+) yields tuples of length `n` (last batch shorter). Prefer it over a hand-rolled chunk loop.

## `match` (3.10+)

Use structural pattern matching for tagged shapes (dicts with a `type` key, enums, small ADTs). Keep patterns shallow.

```python
match event:
    case {"type": "click", "x": int(x), "y": int(y)}:
        handle_click(x, y)
    case {"type": "quit"}:
        return
    case _:
        raise ValueError(f"unknown event: {event!r}")
```

Pitfalls:

- `case status:` **captures** (always matches). Match a value with `case 200:` or `case Status.OK:`, or a dotted enum member.
- Irrefutable patterns (`case x:`, `case _:`) must be last.
- Or-patterns must bind the same names on every branch.
- Don't replace a simple `if/elif` on a bool with `match`.

## Anti-patterns

- **Comprehensions over 2–3 lines**: refactor to an explicit loop.
- **Nested comprehensions**: hard to debug; use loops.
- **Generator expressions you immediately list()**: use a list comprehension.

## References

- https://docs.python.org/3/library/itertools.html
- https://docs.python.org/3/reference/compound_stmts.html#the-match-statement
