# Fixtures and parametrization

## Fixtures

Use fixtures to share setup, not to hide logic.

```python
import pytest

@pytest.fixture
def sample_user():
    return {"id": 1, "name": "Alice"}
```

### Cleanup

Prefer `yield` fixtures for teardown.

```python
@pytest.fixture
def tmp_file(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("hi")
    yield p
    # tmp_path is cleaned up automatically
```

## Parametrization

```python
@pytest.mark.parametrize(
    "text,want",
    [("a", "A"), ("hello", "HELLO")],
)
def test_upper(text, want):
    assert text.upper() == want
```

Use `ids=` when it improves readability.
