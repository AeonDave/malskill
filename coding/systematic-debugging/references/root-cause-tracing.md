# Root Cause Tracing

Use when the symptom is downstream of the defect.

## Trace pattern

1. Mark the first observable bad output.
2. Identify the input/state that produced it.
3. Walk one boundary backward: caller, parser, allocator, transport, fixture, config, or external service.
4. Repeat until the first wrong assumption or state transition is found.
5. Patch there, not at the final symptom.

## Evidence to collect

- exact failing command/input/seed
- stack trace or call path
- relevant variables at the first bad state
- version/build/configuration
- environmental differences between pass/fail

## Common traps

- Fixing a null dereference without finding why null became possible.
- Increasing timeouts without finding the condition that never becomes true.
- Retrying network calls without checking protocol state or auth/session invalidation.
- Treating exploit instability as “bad luck” without measuring mitigations and target build.
- Trusting a sanitizer backtrace as the allocation root cause without checking ownership flow.

## Minimal patch test

A root-cause fix should make the original reproducer pass and should not require broad unrelated changes. If the fix needs many special cases, the traced cause is probably still too late in the chain.
