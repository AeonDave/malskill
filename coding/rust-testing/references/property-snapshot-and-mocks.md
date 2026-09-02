# Property, Snapshot, and Mock Patterns

Use this reference when example-based unit tests are not enough.

## Property testing

- Use `proptest` for invariants, round-trips, parser robustness, and edge-case exploration
- Keep the property small and meaningful; shrinking is only useful if the property itself is clear

## Snapshot testing

- Use `insta` for large structured output, formatted text, or UI-like render output
- Review snapshot changes intentionally; do not auto-accept without understanding the diff
- Prefer snapshots for stable output formats, not for highly volatile data

Treat snapshot updates as behavior changes requiring human review, not mechanical golden refreshes.

## Mocks and fakes

- Prefer lightweight fakes or in-memory implementations when possible
- Use `mockall` or similar only at real boundaries where behavior must be scripted
- Do not mock everything; tests should still reflect meaningful behavior, not just call choreography

### mockall in practice

`#[automock]` on a trait generates `Mock<T>` automatically; expectations are scripted with
`expect_<method>()` chains and verified when the mock drops, so unmet expectations panic the test:

```rust
use mockall::{automock, predicate::eq};

#[automock]
trait Repo { fn find(&self, id: u64) -> Option<User>; }

#[test]
fn service_returns_user_when_found() {
    let mut mock = MockRepo::new();
    mock.expect_find()
        .with(eq(42))     // argument matcher
        .times(1)         // call count assertion
        .returning(|_| Some(User::default()));
    let svc = UserService::new(Box::new(mock));
    assert_eq!(svc.get_user(42).unwrap().id, 42);
}
```

Rules that keep mocks honest:

- `.times(n)` (or `.never()`) turns choreography into an assertion; without it, mockall only
  requires the call be possible.
- Keep the mocked trait small and boundary-shaped: one mock per real external system, not one per
  helper function.
- When several tests script the same choreography repeatedly, write a fake instead of a mock.
