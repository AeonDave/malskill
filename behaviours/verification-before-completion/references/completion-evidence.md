# Completion Evidence

Load when selecting regression checks or reconciling a completion claim with partial evidence.

## Evidence gaps

- A check predates a change that could affect its result.
- Only a worker summary is available; the artifact or check output is missing.
- Exit success is substituted for inspection of the intended output or state.
- A passing subset is described as full coverage.
- An environment failure, skip, or missing prerequisite is reported as a pass.
- Static review is described as executed behavior.

For each gap, either obtain the missing evidence or narrow the claim. Do not repeat unaffected checks simply to create a newer timestamp.

## Regression verification

When practical, demonstrate the original failure, apply the fix, observe the reproducer pass, and run the smallest relevant check for collateral damage. Use an isolated baseline or saved artifact rather than undoing concurrent user work.

For nondeterministic behavior, record conditions and repeated outcomes; a fixed number of passing runs does not prove absence of a race. If a baseline or broader check is unavailable, name the limitation.

Report what changed, the verified outcome, and remaining uncertainty. The general claim/evidence/limits contract lives in `evidence-before-claims`.
