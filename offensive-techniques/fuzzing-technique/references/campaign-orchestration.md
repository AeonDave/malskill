# Campaign orchestration

## Objective

Run fuzzing as an engineered campaign with clear phases, exit criteria, and plateau response.

## Phase model

1. **Smoke phase (short)**
   - Validate harness/model stability and replay.
   - Identify dominant failure classes.
   - Exit only when runs are deterministic enough.

2. **Scale phase (medium/long)**
   - Increase parallel diversity, not just clone count.
   - Keep at least one throughput-focused and one signal-focused profile.
   - Track coverage/state-depth and unique bucket growth trends.

3. **Refinement phase**
   - Prioritize bottlenecks: seed quality, dictionary quality, model depth, reset stability.
   - Re-run focused subsets rather than restarting everything blindly.

## Parallel strategy

- Use diversified instances (different guidance profiles, not identical copies).
- In stateful fuzzing, reserve capacity for depth-first sequences.
- In parser fuzzing, reserve capacity for strict triage/sanitizer confirmation.

## Plateau playbook

If progress stalls:

1. Re-check harness determinism and reset behavior.
2. Improve seed diversity and remove redundant corpus bulk.
3. Improve constraints/tokens/dictionaries for hard comparisons.
4. Narrow to high-value entrypoints.
5. Add or refine state/dependency modeling for APIs/protocols.

Do not respond to plateaus only by increasing runtime.

## Continuous strategy

- Keep minimized corpus as reusable campaign asset.
- Run short CI fuzzing loops for regression detection.
- Run longer periodic campaigns for discovery.
- Keep clear separation between CI noise and confirmed findings.

## Exit criteria

- New unique buckets have flattened for sustained interval.
- High-priority buckets are minimized and replayable.
- Regression corpus includes fixed vulnerabilities.
