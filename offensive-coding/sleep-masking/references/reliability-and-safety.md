# Reliability and Safety Checklist

This checklist is for engineering-quality sleep masking rather than one-off PoCs.

## Pre-flight checks

- Region base and size are validated and immutable during one cycle.
- Permission API paths are tested for both success and rollback.
- Key material source is initialized and error-handled.
- Sleep primitive supports intended duration/jitter range.

## Thread and context safety

- Exclude control/runtime-critical threads from suspension.
- Bound suspension duration; guarantee resume in all error paths.
- Keep a canonical restore order for context and permissions.
- Avoid assumptions that all thread states are stable at scan/suspend time.

## Memory integrity checks

- Hash/checksum optional: verify encrypted backup and restored content consistency.
- Confirm reallocation path supports original-base failure fallback.
- Track and untrack heap buffers explicitly; no orphaned entries.
- Enforce zeroization of temporary buffers and old keys.

## Failure taxonomy (log by phase)

- P1 setup/context errors
- P2 protection transition failures
- P3 transform/encryption failures
- P4 sleep primitive anomalies
- P5 restore/decrypt failures
- P6 post-restore invariants violated

Phase-tagged telemetry makes regressions debuggable.

## Regression strategy

- Run repeated cycles at short, medium, long delays.
- Include stress runs with allocation pressure.
- Re-run after compiler/toolchain and OS patch updates.
- Track crash-free cycles and restore-failure rate as first-class metrics.
