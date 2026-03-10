# Test design

## Unit vs integration

- Unit: deterministic, isolated, no real filesystem/network/db
- Integration: real dependencies, slower, fewer, labeled

## Fixtures

Use fixtures when multiple tests share setup/teardown.

## Parameterized tests

Use when the same behavior should hold across multiple inputs.

## Mocks vs fakes

- Fake: simple in-memory implementation
- Mock: verifies interaction (calls, arguments)

Avoid over-mocking value objects.
