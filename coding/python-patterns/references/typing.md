# Typing (Python 3.11+)

Prefer built-in generics (`list[str]`, `dict[str, int]`). Do not use `typing.List` / `Dict` / `Optional` in new code.

## 3.12+ type parameters and aliases

```python
def first[T](xs: list[T]) -> T | None:
    return xs[0] if xs else None

type JSON = dict[str, JSON] | list[JSON] | str | int | float | bool | None
```

On 3.11 only, `TypeVar` + quoted recursive aliases still work. Do not mix `TypeVar` and PEP 695 syntax in the same module without a reason.

3.13+: type parameters may have defaults (`def f[T = int](...):`).

`type` aliases (3.12+) are lazily evaluated — good for recursive aliases. `TypeAlias` (older) is unnecessary on 3.12+.

## None and unions

Prefer `T | None` over `Optional[T]`. Pick one style per codebase.

## Protocol, Self, override, ReadOnly

```python
from typing import Protocol, Self, override

class Renderable(Protocol):
    def render(self) -> str: ...

class Builder:
    def with_name(self, name: str) -> Self: ...  # 3.11+

class Child(Base):
    @override  # 3.12+
    def get_color(self) -> str: ...
```

`ReadOnly` (3.13+, PEP 705) marks TypedDict keys as immutable for checkers:

```python
from typing import ReadOnly, TypedDict

class Movie(TypedDict):
    name: str
    year: ReadOnly[int]
```

`Self` is 3.11+. `@override` is 3.12+ (`typing.override`). `ReadOnly` is 3.13+ (PEP 705).

## Deferred evaluation (3.14)

Annotations are **not** evaluated at definition time by default (PEP 649 / 749). Forward references need not be strings. `from __future__ import annotations` still stringifies and is slated for removal — don't add it on 3.14+.

Runtime introspection:

```python
from annotationlib import Format, get_annotations

get_annotations(fn, format=Format.VALUE)       # may NameError
get_annotations(fn, format=Format.FORWARDREF)  # placeholders
get_annotations(fn, format=Format.STRING)
```

On 3.11–3.13, `inspect.get_annotations` remains the usual helper. Don't read `__annotations__` hoping for eager values on 3.14+.

## Notes

- Don't over-annotate locals; focus on public APIs and tricky parts.
- Keep runtime and typing concerns separate (don't use annotations as a validation library unless that is the project's contract).

## Anti-patterns

- **Bare `Any` on public APIs**: hides the contract.
- **Mixing `Optional[T]` and `T | None`**.
- **`TypeVar` in new 3.12+ modules** when PEP 695 would do.
- **`from __future__ import annotations` on 3.14+** "for compatibility" when you don't support 3.13-.

## CI discipline

- Run `mypy --strict` on public API files; relax for internal modules if needed.
- Enable `warn_unused_ignores` to catch stale `# type: ignore`.

## References

- https://docs.python.org/3/library/typing.html
- https://docs.python.org/3/library/annotationlib.html
- https://peps.python.org/pep-0695/
- https://peps.python.org/pep-0649/
- https://peps.python.org/pep-0749/
