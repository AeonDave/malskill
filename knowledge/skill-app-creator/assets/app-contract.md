# Application contract

Fill this working template for the target app. Replace prompts with decisions; remove unused rows/sections. Put required rules in the generated skill and schemas; do not ship this planning document automatically.

## Task and delivery

- User action and completion condition:
- Natural activation request; nearest request needing another skill:
- Existing capability to reuse; concrete missing behavior:
- Agent decisions; deterministic helper responsibilities:
- Accepted inputs, validation, and provenance:
- Ordinary-use command and required runtime:

| Deliverable | Exact name/location | Fields/sections, units, order | Unknown/partial representation | Acceptance check |
|---|---|---|---|---|
| Primary result | | | | |
| Human-facing output, if separate | | | | |
| Supporting evidence, if needed | | | | |

## Selected components

| Component | Concrete task need; omit when absent | Interface and dependencies |
|---|---|---|
| Task helper | | |
| Template/schema and validator | | |
| Doctor | | |
| Persistent session | | |
| External service/host adapter | | |
| Viewer/preview/export | | |

## Execution and recovery

- Default scope, inexpensive first path, heavier-work conditions:
- Time/cost limits, progress, cancellation, partial delivery:
- Configuration precedence; resources, outputs, cache locations:
- Required/optional capabilities, doctor checks, fallback:
- Uploads/external writes, credentials, authorization:
- Failure classification, bounded retries, alternative routes:

For persistent apps only:

- Canonical record, schema version, lifecycle and verification states:
- Start/status/resume/check/finalize interface with actual command names:
- Checkpoints, writer ownership, stale-work detection, input invalidation:
- Idempotency, corrections/history, old-record handling:
- Publication consistency, final-location checks, shutdown order:

## Verification contract

- Evidence for substantive results; semantic checks:
- Required success gates and artifact reopening:
- Unresolved/failed/cancelled output; skipped checks and waiver provenance:
- Applicable acceptance cases, fixtures, expected outcomes:
- Claimed hosts/platforms/services and how each will be exercised:
- Agent-use scenario, near miss, comparison baseline when needed:
- Remaining limitations and evidence needed to remove them:
