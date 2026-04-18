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

## Fixture scope rules

- `function` (default): New fixture per test; safest.
- `module`: Shared across tests in one file; risky if state carries over.
- `session`: Shared across entire test run; only for truly stateless setup (config, temporary directories).

## Anti-patterns

- **Over-parameterization**: If you have >10 parameter combinations, consider a builder pattern or helper.
- **Fixture interdependencies**: Fixtures that depend on other fixtures can create hidden coupling.
- **Mixing test setup and fixture setup**: Use fixtures for dependencies; test code for scenario setup.

## References

- https://docs.pytest.org/en/stable/how-to/fixtures.html
