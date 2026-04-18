# Data models

## dataclasses

Use for lightweight data containers.

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
```

Notes:
- `frozen=True` helps immutability.
- `slots=True` can reduce memory overhead.

## Validation

Prefer validating at boundaries (parsing/IO). If you must validate on construction, use `__post_init__`.

## NamedTuple

Useful for small immutable tuples with names.

```python
from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
```

## Validation patterns

Use `__post_init__` sparingly; prefer validation at parsing boundaries:

```python
def parse_user(data: dict) -> User:
    if not isinstance(data.get("id"), str):
        raise ValueError("id must be string")
    return User(id=data["id"], email=data["email"])
```

## Anti-patterns

- **Mutable default field values** (lists, dicts): Use `field(default_factory=list)`.
- **Mixing validation logic inside dataclass constructor**: Separate parsing from object construction.

## CI discipline

- Ensure all public dataclasses are frozen or explicitly mark as mutable.
- Use `slots=True` for dataclasses with many instances to reduce memory overhead.
