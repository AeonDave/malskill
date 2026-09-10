# Resource management

## Context managers

Use `with` for files, locks, temp dirs, network sessions, etc.

```python
from pathlib import Path

with path.open("r", encoding="utf-8") as f:
    return f.read()
```

`pathlib.Path` is the default for filesystem paths. `Path.walk()` (3.12+) replaces most `os.walk` call sites.

Do **not** use `with path:` on a `Path` — the context-manager behavior was a no-op and was **removed in 3.13**.

## contextlib

Use `contextlib.contextmanager` for simple custom context managers. `ExitStack` when the number of resources is dynamic.

## Cleanup

- Prefer deterministic cleanup (`with`, `try/finally`).
- Avoid relying on `__del__`.

## Anti-patterns

- **Forgetting `with` and manually calling `.close()`**: brittle if an exception occurs before close.
- **Nesting context managers without clarity**: use parentheses or multiple `with` items.
- **Relying on `__del__` for cleanup**: non-deterministic.
- **`os.path` string concatenation** for new code: `Path` / `/` operator.

## References

- https://docs.python.org/3/library/pathlib.html
- https://docs.python.org/3/library/contextlib.html
