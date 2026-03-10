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
