# Typing (Python 3.11+)

## Prefer built-in generics

```python
def f(items: list[str]) -> dict[str, int]:
    return {s: len(s) for s in items}
```

## Type aliases

```python
type JSON = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None
```

Use aliases to avoid repeating complex unions.

## Optional and None

Prefer `T | None` over `Optional[T]`.

## Protocol for structural typing

```python
from typing import Protocol

class Renderable(Protocol):
    def render(self) -> str: ...
```

Use for “duck typing” APIs.

## Generics

```python
from typing import TypeVar

T = TypeVar("T")

def first(xs: list[T]) -> T | None:
    return xs[0] if xs else None
```

## Notes

- Don’t over-annotate locals; focus on public APIs and tricky parts.
- Keep runtime and typing concerns separate.

## Anti-patterns

- **Bare `Any` or `object` for public APIs**: Hide the actual contract, making callers guess.
- **Over-annotating local variables**: Adds noise without value (`items: list[dict[str, Any]] = [...]`).
- **Mixing `Optional[T]` and `T | None`**: Choose one style per codebase.

## CI discipline

- Run `mypy --strict` on public API files; relax for internal modules if needed.
- Enable `warn_unused_ignores` in mypy config to catch stale `# type: ignore` comments.

## References

- https://docs.python.org/3/library/typing.html
- https://peps.python.org/pep-0484/
- https://peps.python.org/pep-0544/
