# Async and Boundaries

Use this reference when tests touch async code, time, filesystem, network, or other external boundaries.

## Async testing

- Use the runtime's async test attribute, such as `#[tokio::test]`, when the project already uses that runtime
- Await real conditions or events instead of sprinkling `sleep()` and hoping timing lines up
- Bound timeouts explicitly when waiting on async work: `tokio::time::timeout(Duration::from_secs(N), fut)`

## Deterministic time in tokio

- `#[tokio::test(start_paused = true)]` starts the runtime with a paused clock, so time-based logic
  (retries, backoff, intervals) runs instantly instead of sleeping for real. Requires the tokio
  `test-util` feature.
- Pausing works because `#[tokio::test]` defaults to the `current_thread` runtime; advance time
  explicitly with `tokio::time::advance(...)`. The paused clock auto-advances once the runtime has
  no work, unless a blocking task is in flight.
- Set `flavor = "multi_thread"` explicitly when the code under test needs parallel workers instead
  of relying on machine speed or thread count.

## Boundary control

- Use temp directories for filesystem tests
- Replace real network calls with local test servers, fixtures, or fakes
- Abstract time, randomness, and environment access when deterministic behavior matters
- Keep external dependency setup explicit and localized

Use explicit timeout bounds for awaits that depend on external progress to avoid hangs in CI.

## Common footguns

- sharing mutable global state across async tests
- forgetting that doctests and unit tests may run in parallel
- tests that pass only with one specific thread count or machine speed
