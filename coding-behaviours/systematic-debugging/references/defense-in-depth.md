# Defense In Depth for Bug Fixes

Use after the root cause is known and the first minimal fix is clear.

## Layered fix model

1. **Source fix**: correct the wrong state transition, ownership, validation, or assumption.
2. **Boundary guard**: reject invalid external input at API/protocol/file boundaries.
3. **Invariant check**: assert or test impossible internal states where failure would be dangerous.
4. **Regression test**: preserve the reproducer or minimized case.
5. **Observability**: add targeted logs/errors only if future diagnosis would otherwise be blind.

## Avoid over-layering

Do not add guards everywhere. Add layers where they catch distinct failure classes or protect trust boundaries.

## Security-specific examples

- Parser bug: fix length calculation, add boundary validation, add malformed corpus case.
- Auth bypass: fix authorization decision, add negative test for lower-privileged principal, log denied path.
- Exploit harness race: fix state machine, wait on observable state, add deterministic replay test.
- Secret leak: remove source, rotate/disable if authorized, add scanner/denylist test where appropriate.
