# Property, Snapshot, and Mock Patterns

Use this reference when example-based unit tests are not enough.

## Property testing

- Use `proptest` for invariants, round-trips, parser robustness, and edge-case exploration
- Keep the property small and meaningful; shrinking is only useful if the property itself is clear

## Snapshot testing

- Use `insta` for large structured output, formatted text, or UI-like render output
- Review snapshot changes intentionally; do not auto-accept without understanding the diff
- Prefer snapshots for stable output formats, not for highly volatile data

## Mocks and fakes

- Prefer lightweight fakes or in-memory implementations when possible
- Use `mockall` or similar only at real boundaries where behavior must be scripted
- Do not mock everything; tests should still reflect meaningful behavior, not just call choreography
