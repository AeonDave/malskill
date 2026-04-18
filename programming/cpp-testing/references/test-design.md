# Test design

## Unit vs integration

- Unit: deterministic, isolated, no real filesystem/network/db
- Integration: real dependencies, slower, fewer, labeled

Keep integration boundaries explicit: filesystem/network/process tests should not be silently mixed into unit suites.

## Fixtures

Use fixtures when multiple tests share setup/teardown.

Prefer minimal fixtures over heavy global setup.

## Parameterized tests

Use when the same behavior should hold across multiple inputs.

Use descriptive parameter names to keep failure output debuggable.

## Mocks vs fakes

- Fake: simple in-memory implementation
- Mock: verifies interaction (calls, arguments)

Avoid over-mocking value objects.

## Structure guidance (AAA)

- **Arrange**: isolate state and dependencies.
- **Act**: execute one behavior under test.
- **Assert**: verify outcome with targeted expectations.

Prefer one dominant assertion intent per test case to improve triage speed.
