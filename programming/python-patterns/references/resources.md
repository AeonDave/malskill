# Resource management

## Context managers

Use `with` for files, locks, temp dirs, network sessions, etc.

```python
with path.open("r", encoding="utf-8") as f:
    return f.read()
```

## contextlib

Use `contextlib.contextmanager` for simple custom context managers.

## Cleanup

- Prefer deterministic cleanup (`with`, `try/finally`).
- Avoid relying on `__del__`.

## Anti-patterns

- **Forgetting `with` and manually calling `.close()`**: Brittle if an exception occurs before close.
- **Nesting context managers without clarity**: Use parentheses or multiple `with` lines for readability.
- **Relying on `__del__` for cleanup**: Non-deterministic; always use context managers.

## CI discipline

- Run `pylint --disable=all --enable=R0924` (too many arguments in function) and similar checks.
- Use `ruff check --select F821` to catch undefined names before runtime.
