# Error handling

## Catch specific exceptions

```python
try:
    data = json.loads(text)
except json.JSONDecodeError as e:
    raise ValueError("invalid JSON") from e
```

Avoid `except Exception:` unless you are a boundary (CLI / request handler) and will log + re-raise / map errors.

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

## Boundary rule

- Inner functions: raise domain-specific errors.
- Outer boundary (CLI/HTTP handler): translate to exit codes / responses and log context.
