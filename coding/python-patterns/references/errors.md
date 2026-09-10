# Error handling

## Catch specific exceptions

```python
try:
    data = json.loads(text)
except json.JSONDecodeError as e:
    raise ValueError("invalid JSON") from e
```

Avoid `except Exception:` unless you are a boundary (CLI / request handler) and will log + re-raise / map errors.

`except Exception` does **not** catch `BaseException` subclasses: `KeyboardInterrupt`, `SystemExit`, `asyncio.CancelledError`. That is the point — don't "fix" cancellation by broadening the except.

## Exception chaining

Always preserve the original exception when re-raising with context:

```python
raise ConfigError(f"bad config: {path}") from e
```

## Custom exception hierarchy

Use a small base error for your domain.

```python
class AppError(Exception):
    pass

class ValidationError(AppError):
    pass
```

## Exception groups (3.11+)

Concurrent work (especially `asyncio.TaskGroup`) raises `ExceptionGroup` when several tasks fail.

```python
try:
    ...
except* ValueError as eg:
    handle_values(eg.exceptions)
except* OSError as eg:
    handle_os(eg.exceptions)
```

`except*` matches **sub-exceptions** inside a group (and still matches a bare `ValueError`). A plain `except ValueError` does **not** catch that `ValueError` nested in an `ExceptionGroup`.

Unwrap only at a boundary when you must present a single error; don't discard sibling failures.

## `finally` (3.14, PEP 765)

`return` / `break` / `continue` that **leave** a `finally` block emit `SyntaxWarning` — they swallow the original exception. Restructure so `finally` only cleans up.

## Boundary rule

- Inner functions: raise domain-specific errors.
- Outer boundary (CLI/HTTP handler): translate to exit codes / responses and log context.

## Anti-patterns

- **Silent exception swallowing**: `try: ... except: pass` hides bugs.
- **Generic `except Exception`** in library code: let exceptions propagate unless you're at a boundary.
- **`raise` without `from e`**: loses the cause.
- **Catching `Exception` around asyncio work** expecting to see `CancelledError` — you won't.

## References

- https://docs.python.org/3/library/exceptions.html#exception-groups
- https://peps.python.org/pep-0654/
- https://peps.python.org/pep-0765/
