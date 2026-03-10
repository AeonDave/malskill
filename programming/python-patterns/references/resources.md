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
