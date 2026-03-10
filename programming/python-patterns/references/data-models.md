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
