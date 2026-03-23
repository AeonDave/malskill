# Async and Boundaries

Use this reference when tests touch async code, time, filesystem, network, or other external boundaries.

## Async testing

- Use the runtime's async test attribute, such as `#[tokio::test]`, when the project already uses that runtime
- Await real conditions or events instead of sprinkling `sleep()` and hoping timing lines up
- Bound timeouts explicitly when waiting on async work

## Boundary control

- Use temp directories for filesystem tests
- Replace real network calls with local test servers, fixtures, or fakes
- Abstract time, randomness, and environment access when deterministic behavior matters
- Keep external dependency setup explicit and localized

## Common footguns

- sharing mutable global state across async tests
- forgetting that doctests and unit tests may run in parallel
- tests that pass only with one specific thread count or machine speed
