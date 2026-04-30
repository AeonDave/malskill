---
name: sleep-masking
description: "Design, implement, review, and debug sleep-masking workflows for Windows x64 implants/loaders: timer-queue, APC, waitable-timer, and hook-driven sleep cycles; memory encryption-at-rest; permission transitions; thread-state control; key lifecycle and rotation; and mitigation-aware reliability (CET shadow stack, CFG, modern EDR timer/APC heuristics). Use when building or evaluating encrypted-sleep behavior, selecting between Ekko/Foliage/Cronos-style flows, or reducing crash/detection risk in repeated sleep cycles."
license: MIT
compatibility: "Windows x64 user-mode. Linux/macOS and kernel-mode sleep masking are out of scope."
metadata:
  author: AeonDave
  version: "1.0"
  category: evasion
  language: c,cpp,rust,go,asm
---

# Sleep Masking

Goal: keep dormant code/data minimally observable during idle windows while preserving execution stability across repeated cycles.

## When to activate

- You need encrypt-at-sleep behavior for an in-memory agent or loader.
- You are choosing among timer-queue/APC/waitable-timer/hook-based sleep orchestration.
- Your current sleep cycle is unstable (races, crashes, deadlocks) or noisy (easy telemetry signatures).
- You need mitigation-aware design for modern Windows hardening (CET/CFG) and stronger timer/APC hunting.

## Core flow model

Treat sleep masking as a state machine:

1. **Pre-sleep prep**: optional thread gating/suspend strategy, context capture, key selection.
2. **Permission shift**: executable -> writable (or no-access depending on pattern).
3. **In-memory transform**: encrypt payload/critical heaps with symmetric transform.
4. **Dormant interval**: sleep/wait primitive executes while transformed memory is non-executable.
5. **Restore phase**: decrypt, restore permissions, restore contexts/threads.
6. **Post-sleep hygiene**: rotate keys, wipe transient material, verify invariants.

If any transition fails, fail closed with deterministic rollback (restore permissions/context before continuing).

## Sleep orchestration patterns

### Timer-queue chain (Ekko-style)

- Queue staged callbacks to perform: protect RW -> encrypt -> delay -> decrypt -> protect RX.
- Strength: composable chain with clear phase boundaries.
- Risk: timer object/callback telemetry and worker-thread artifacts.

### APC/context chain (Foliage-style)

- Queue context-driven callbacks (often via NtContinue/SetThreadContext pathways) for phase execution.
- Strength: flexible sequencing and context-level control.
- Risk: suspicious APC/context manipulation patterns in modern detection pipelines.

### Waitable timer + ROP/context chain (Cronos-style)

- Use waitable-timer/APC completion sequencing with context or ROP-like dispatch.
- Strength: precise phase timing and chained transitions.
- Risk: fragile stack/context correctness and higher crash risk under mitigation changes.

### Hooked sleep surface

- Intercept sleep entry point and route through custom encrypt-sleep-decrypt pipeline.
- Strength: easy integration in existing loops.
- Risk: hook visibility and call-path anomalies.

## Memory masking patterns

- **Region masking**: transform code region only (lower blast radius, easier reliability).
- **Heap-assisted masking**: additionally mask selected heap buffers with strict tracking/untracking lifecycle.
- **Memory bouncing**: encrypted backup -> free original region during sleep -> reallocate/restore/decrypt after wake.
- **Protection strategy**: RW/RX flips are common; NOACCESS windows can reduce readable exposure but increase fault risk.

## Reliability-first guardrails

- Pin critical transitions to predictable thread context where needed.
- Do not suspend control/runtime-critical threads blindly; maintain exclusion policy.
- Keep per-cycle checks: base pointer validity, region size consistency, permission restoration success.
- Use bounded retries for allocation/restore paths; avoid unbounded loops in sleep pipeline.
- Keep sleep cycle idempotent: running it twice should not corrupt state.

## Key lifecycle and anti-forensics

- Generate per-run seed and rotate per sleep cycle when feasible.
- Separate key storage from transformed region; avoid static long-lived key bytes.
- Wipe transient key material and context copies after successful restore.
- Design rollback for failed rotation (continue with last-good key only if integrity checks pass).

## Mitigation-aware constraints (2026-focused)

- **CET shadow stack**: return-address or context-redirection assumptions can break; design flows that remain valid under stricter control-flow checks.
- **CFG and call-target policies**: indirect transitions must remain policy-compatible.
- **Timer/APC hunting maturity**: defenders increasingly correlate repeated timer/APC/context patterns with long-lived sleepers.
- **Telemetry minimization**: reduce repetitive, highly regular phase cadence; prefer operational jitter and bounded variability over fixed intervals.

## Validation workflow

1. Verify one complete cycle in debugger with explicit phase checkpoints.
2. Run repeated-cycle stress (e.g., 50+ cycles) and record failures by phase.
3. Validate restoration invariants after each cycle (permissions, entry pointer, key state, tracked heaps).
4. Compare behavior under different sleep durations and jitter bands.
5. Re-test after OS/mitigation baseline changes.

## Anti-patterns

- Encrypt/decrypt without strict permission restoration checks.
- Suspending every thread without exclusion policy.
- Static keys reused indefinitely across cycles.
- Fixed phase timing with no jitter and highly repeatable API cadence.
- Treating sleep masking as “set once and forget”; it must be continuously regression-tested.

## Resources

- [references/flows-and-modes.md](references/flows-and-modes.md)
- [references/reliability-and-safety.md](references/reliability-and-safety.md)
- [references/patterns.md](references/patterns.md)
