# Condition-Based Waiting

Use when a test, exploit harness, service integration, or agent workflow currently sleeps and hopes.

## Replace sleeps with conditions

| Bad wait | Better condition |
|---|---|
| sleep 5 seconds after server start | port accepts connection or health endpoint returns ready |
| sleep before reading file | file exists and size/hash stabilizes |
| sleep after async task | future/event/channel completed |
| sleep before exploit stage | target state observed on wire/log/API |
| retry loop with no reason | retry only on documented transient state |

## Wait design

- Poll the narrowest observable condition.
- Use a deadline and show the last observed state on timeout.
- Keep intervals short but bounded; avoid hot loops.
- Fail loudly when preconditions never appear.
- In tests, prefer fake clocks/events when supported.

## Offensive cautions

- Sleeps can hide races that break outside the lab.
- Long waits may increase target noise or make tooling look hung.
- Retrying exploitation without state checks may change target state or lock accounts.
- A reliable harness records why each stage advanced.
