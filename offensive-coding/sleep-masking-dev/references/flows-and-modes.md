# Sleep Masking Flows and Modes

Use this document to pick a sleep orchestration model before coding.

## Canonical phase sequence

1. Select region(s) and verify boundaries.
2. Switch protection to writable (or no-access strategy).
3. Encrypt targeted regions.
4. Enter sleep primitive.
5. Decrypt targeted regions.
6. Restore execute/read protections.
7. Rotate/wipe keys and transient state.

Never skip explicit success/failure checks between phases.

## Mode comparison

### Timer-queue callback pipeline

- Best for: explicit multi-step sequencing.
- Typical primitives: timer queue creation, callback scheduling, context payload.
- Common failure: race windows between queued callbacks and thread scheduling.

### APC/context pipeline

- Best for: controlled callback sequencing on selected threads.
- Typical primitives: APC queueing + context redirection.
- Common failure: unstable behavior when thread/context assumptions drift.

### Waitable timer pipeline

- Best for: deterministic delay control with chained wake routines.
- Typical primitives: waitable timers + completion behavior.
- Common failure: fragile context/stack transitions in complex chains.

### Hook-driven sleep pipeline

- Best for: retrofitting existing execution loop.
- Typical primitives: sleep API interception + custom pre/post hooks.
- Common failure: hook visibility and API-path integrity issues.

## Optional extensions

- Heap masking for sensitive runtime buffers.
- Memory bouncing (backup/free/realloc/restore).
- Selective thread suspension with exclusion list.

Choose extensions only if they improve your measured detection/reliability profile.
