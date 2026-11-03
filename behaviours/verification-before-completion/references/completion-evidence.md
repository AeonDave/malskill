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

Distinguish product failures from verification-environment problems. Attribute a failure to the baseline only when applicable prior results or an isolated comparison support that conclusion; otherwise leave attribution unresolved. A pre-existing or environmental failure does not satisfy a required acceptance gate.

## Regression verification

When practical, demonstrate the original failure, apply the fix, observe the reproducer pass, and run the smallest relevant check for collateral damage. Use an isolated baseline or saved artifact rather than undoing concurrent user work.

For nondeterministic behavior, record conditions and repeated outcomes; a fixed number of passing runs does not prove absence of a race. If a baseline or broader check is unavailable, name the limitation.

## Design and implementation consistency

When work has an agreed design or plan, compare its current requirements with the delivered source and relevant diff. Include later authorized decisions. Search for moved or renamed implementations before calling a feature absent; naming differences alone do not establish a behavior mismatch.

For material requirements, locate implementation and verification evidence. Also inspect changed behavior for additions that lack a requirement. Classify discrepancies as missing or conflicting behavior, an authorized design change, stale documentation, or an unchecked area. Cite the requirement and code location; do not treat every undocumented private helper as scope drift.

Correct unintended behavior or update stale documents to reflect authorized decisions. Do not rewrite a requirement merely to make an incomplete implementation appear compliant. Recheck affected contracts after corrections. State review coverage and unavailable checks; agreement between prose and code is not a substitute for execution evidence.

Report what changed, the verified outcome, and remaining uncertainty. The general claim/evidence/limits contract lives in `evidence-before-claims`.

## Source anchor

- [EGM design/code drift workflow](https://github.com/google/elephant-goldfish-model/blob/main/skills/egm-drift-report/SKILL.md).
