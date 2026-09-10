# Data models

## dataclasses

Use for lightweight data containers.

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True, kw_only=True)
class User:
    id: str
    email: str
```

- `frozen=True` — immutability (hashable if all fields are).
- `slots=True` — fewer per-instance dicts; many instances, less RAM. Can't add ad-hoc attributes.
- `kw_only=True` (3.10+) — stops positional accidents on growing structs.

## `copy.replace` (3.13+)

```python
import copy

updated = copy.replace(user, email="new@example.com")
```

Works for dataclasses, named tuples, and types that define `__replace__`. Prefer this over mutating a `frozen` instance or handwritten `_replace` helpers.

## Validation

Prefer validating at boundaries (parsing/IO). If you must validate on construction, use `__post_init__`.

```python
def parse_user(data: dict) -> User:
    if not isinstance(data.get("id"), str):
        raise ValueError("id must be string")
    return User(id=data["id"], email=data["email"])
```

## NamedTuple and StrEnum

```python
from typing import NamedTuple
from enum import StrEnum, auto

class Point(NamedTuple):
    x: float
    y: float

class Color(StrEnum):  # 3.11+; `str` and `Enum` — values are str
    RED = auto()
```

`StrEnum` compares equal to its string value. Don't mix with integer `Enum` for wire formats.

## Template strings (3.14)

`t"..."` yields `string.templatelib.Template`, not `str`. Iterate parts (`str` statics + `Interpolation`) to sanitize SQL/HTML/shell **before** combining. Iteration skips empty statics. Use f-strings when you just need a `str`.

```python
from string.templatelib import Interpolation

def only_static_and_values(template):
    for part in template:
        if isinstance(part, Interpolation):
            yield part.value
        else:
            yield part
```

## Anti-patterns

- **Mutable default field values** (lists, dicts): use `field(default_factory=list)`.
- **Validation inside the dataclass constructor** for IO data: parse first.
- **f-strings for attacker-controlled interpolation** into SQL/HTML: t-strings exist so you can treat interpolations as data.

## CI discipline

- Public dataclasses: `frozen` or explicitly mutable.
- `slots=True` when many instances exist (also a memory win; measure in `python-performance` if unsure).

## References

- https://docs.python.org/3/library/dataclasses.html
- https://docs.python.org/3/library/copy.html#copy.replace
- https://docs.python.org/3/library/enum.html#enum.StrEnum
- https://docs.python.org/3/library/string.templatelib.html
- https://peps.python.org/pep-0750/
