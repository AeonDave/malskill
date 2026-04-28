# Mocking and patching

## Rule of thumb

Mock at boundaries:
- network calls
- filesystem
- time
- external services

Prefer fakes for complex dependencies.

## patch() correctly

Patch the name **as used by the system under test**, not where it was originally defined.

```python
from unittest.mock import patch

@patch("mypkg.module_under_test.requests.get")
def test_fetch(get_mock):
    get_mock.return_value.status_code = 200
    ...
```

## Async mocks

Use `AsyncMock` for `async def` functions.

```python
from unittest.mock import AsyncMock

mock = AsyncMock(return_value=123)
```

## Mocking discipline

- **Mock at entry points**: Don't mock internal function calls; refactor if you need to mock everything.
- **Use fakes for complex objects**: If mocking gets complex, implement a minimal fake instead.
- **Verify call count sparingly**: Only for critical workflows; over-verification couples tests to implementation.

## Anti-patterns

- **Mocking everything**: If every line needs a mock, the code is too tightly coupled.
- **Patching wrong location**: Always patch where the object is **used**, not where it's defined.
- **Returning side_effect as exception**: Use `side_effect=ValueError(...)` only when testing exception handling.

## References

- https://docs.python.org/3/library/unittest.mock.html
- https://docs.python.org/3/library/unittest.mock.html#asyncio-support
