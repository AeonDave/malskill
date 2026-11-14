---
name: sleep-masking-dev
description: "Auth/lab dev: sleep-state research; timers/APC/waitable timers, memory-at-rest, permission transitions, key lifecycle, reliability checks."
license: MIT
compatibility: "Windows x64 user-mode; Linux/macOS and kernel-mode sleep masking are out of scope."
metadata:
  author: AeonDave
  version: "1.1"
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
- **Memory bouncing / ghosting**: encrypted backup -> free original region during sleep -> reallocate/restore/decrypt after wake. See the ghosting subsection below.
- **Protection strategy**: RW/RX flips are common; NOACCESS windows can reduce readable exposure but increase fault risk.

## Ghosting variants

The decommit pattern is community-established (no single canonical publication — treated as no-public-lineage): `NtFreeVirtualMemory(MEM_DECOMMIT)` returns the pages to RESERVED, so committed-memory scanners (PE-Sieve, Moneta) see nothing where the code was; recommit on wake ([NtFreeVirtualMemory semantics](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntfreevirtualmemory)).

Stronger variant (field-reported, project evidence: evasion framework `chrysalis/strategy.go`, "Chrysalis Mode 2"):

1. Encrypt the code region + tracked heap buffers in place (MBA-obfuscated XOR).
2. **`NtFreeVirtualMemory(MEM_RELEASE)`** — the region does not exist during sleep (stronger than decommit; nothing for a scanner to classify).
3. Suspend every other thread (enumerate via `NtQuerySystemInformation(SystemProcessInformation)`), so no thread walks a freed mapping mid-sleep.
4. Sleep via `NtWaitForSingleObject` with a **relative timeout** — zero timer objects, zero APCs, zero ROP chains; orchestration lives in plain code.
5. Reallocate (same base, any-base fallback), restore ciphertext, decrypt, re-protect RX, resume threads.
6. Rotate a 16-byte key **per sleep cycle**; GC/runtime threads get a skip-suspension flag to avoid deadlocks (Go hosts).

Trade-offs: heavier orchestration than Ekko-style, wrong key or missing exclusion policy = hard crash; keys must come from a CSPRNG (a `math/rand`-seeded key is the known weakness of a real implementation).

## Trampoline placement and key hygiene (2026)

- **Place mask trampolines in executable image-backed sections, not private RWX** (evidence: gengar `sleep_trampoline.rs` — trampoline lives in a seed-named PE image section; scratch RW holds only ciphertext). A private RWX trampoline is the single loudest residual artifact of most masks.
- **Keys in registers**: hold the cycle key in `XMM6/XMM7` for the duration — never write it to memory the mask is protecting.
- **Integrity-checked masking (project-reported pattern, no linked qualification record)**: compute a MAC over the ciphertext **and the masked caller stack**; derive the restore key as `key XOR mac32(ciphertext)`. Any tamper with code or stack fails the restore → zero keys and terminate that thread instead of executing corrupted state. Turns the mask into a fail-closed tripwire rather than only concealment.

## Ekko reduced (timer-as-wake-only)

Full Ekko/ROP chains are heavy and telemetry-rich (note: the original Ekko PoC restores RWX, not RX — [Cracked5pider/Ekko](https://github.com/Cracked5pider/Ekko)). A reduced shape (evidence: gengar `ekko.rs`): use the timer queue **only as the wake primitive** (`CreateTimerQueueTimer` with `WT_EXECUTEONLYONCE|WT_EXECUTEINTIMERTHREAD`), perform mask/restore inline in the same thread from a seed-named image section, and resolve timer APIs from the already-mapped KernelBase — no new imports, no ROP.

## Reliability-first guardrails

- Pin critical transitions to predictable thread context where needed.
- Do not suspend control/runtime-critical threads blindly; maintain exclusion policy.
- Keep per-cycle checks: base pointer validity, region size consistency, permission restoration success.
- Use bounded retries for allocation/restore paths; avoid unbounded loops in sleep pipeline.
- Keep sleep cycle idempotent: running it twice should not corrupt state.

## 2024-2026 landscape

- **Thread-pool-timer orchestration** superseded raw timer-queue chains: `CreateThreadpoolTimer`/`SetThreadpoolTimer`, `TpSetWait`, `RtlCreateTimer` — see [GhostTimer](https://github.com/7uckzero/GhostTimer-SleepObf) (2026, Ekko-derived, addresses Hunt-Sleeping-Beacons timer callbacks), [hypnus](https://github.com/joaoviictorti/hypnus) (2025, Rust, Zilean-variant via `TpSetWait`), Havoc Demon `SLEEPOBF_EKKO/ZILEAN/FOLIAGE`.
- **Sleeping Beauty II** ([StealthPalace, Jun 2026](https://maorsabag.github.io/posts/adaptix-stealthpalace/sleeping-beauty-ii)): CFG bypass via `NtSetInformationVirtualMemory(VmCfgCallTargetInformation)` to register ROP gadgets as valid call targets, plus CET-compatible stack spoofing (preserves RIP, mirrors RSP/TIB bounds) around the sleep — the current reference for mitigation-aware masks.
- **Shelter** ([Kudaes](https://github.com/Kudaes/Shelter), 2024): weaponized ROP-based mask; **DeathSleep** (2022): thread-termination variant, a mode the taxonomy above misses.
- **Detector landscape to test against**: [WithSecure TickTock](https://github.com/WithSecureLabs/TickTock) (timer-queue enumeration), [thefLink/Hunt-Sleeping-Beacons](https://github.com/thefLink/Hunt-Sleeping-Beacons), [Moneta](https://github.com/forrest-orr/Moneta), [pe-sieve](https://github.com/hasherezade/pe-sieve).

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

- [references/flows-and-modes.md](references/flows-and-modes.md) — Load when choosing the sleep pipeline shape, phase ordering, and orchestration mode.
- [references/reliability-and-safety.md](references/reliability-and-safety.md) — Load when debugging crashes, rollback failures, race conditions, or unsafe transition order.
- [references/patterns.md](references/patterns.md) — Load for concrete masking patterns, permission-transition designs, and thread-handling trade-offs.
- [../linux-internals-dev/references/syscall-dispatch-linux.md](../linux-internals-dev/references/syscall-dispatch-linux.md) — Cross-reference for Linux syscall gate patterns when adapting ideas across platforms.
