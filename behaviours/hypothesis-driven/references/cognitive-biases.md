# Cognitive Biases That Derail Hypothesis-Driven Work

Each entry: the signal that the bias is active in the current investigation, and the counter-move to apply now (not in retrospect).

## Confirmation bias

- **Signal**: every experiment is designed in a way that can only confirm the favorite hypothesis.
- **Counter**: write the falsifier first. If no observable would disprove the hypothesis, redesign the experiment before running it. Include a negative control where the hypothesis predicts no effect.

## Anchoring

- **Signal**: the first hypothesis stays at the top of the list regardless of new evidence.
- **Counter**: generate 3-7 alternatives explicitly before testing any of them. Re-rank after every experiment, not only when the leader is refuted.

## Sunk-cost continuation

- **Signal**: "I've already spent an hour on this hypothesis, I should keep going."
- **Counter**: effort is not evidence. Decide whether to continue based only on the strength of the latest result, not on prior investment.

## Symptom chasing

- **Signal**: fixes target the line where the program crashes, the endpoint that returns 500, or the byte that prints wrong.
- **Counter**: trace backward to the first wrong state. The defect is upstream of the symptom in most non-trivial bugs.

## Tool authority

- **Signal**: a scanner finding, decompiler output, LLM suggestion, or stack trace is treated as ground truth.
- **Counter**: every tool output is a lead until reproduced by an independent observation. Tools have false positives, decompilers lie, traces lose frames.

## Deductive impossibility

- **Signal**: a path, primitive, or exploit vector is abandoned because a *reasoning chain* concluded it "can't work / is unreachable / is a dead vector" — with no failing live test. The argument keeps getting longer instead of a probe getting run.
- **Counter**: impossibility is a hypothesis, and code paths / primitives / gadgets / inputs can never be fully enumerated, so a deductive impossibility proof is almost always an incomplete-model error that discards the correct path. Demote every "X is impossible" to "X untested," then run the one experiment that would make it work — hook the candidate call site and fuzz thresholds (input length, allocation size, error/locale paths); internal scratch-buffer growth and parser edge cases create calls absent from normal flow. Only "no hit after adversarial fuzzing" counts as unreachable.

## Compound changes

- **Signal**: two variables changed between runs (code edit + env tweak, payload + target version).
- **Counter**: change one thing at a time. If multiple changes are needed, sequence them and record the verdict after each.

## Vague predictions

- **Signal**: "something should look different" or "it might work."
- **Counter**: name the observable, the value, and the falsifier before running. If you cannot, the experiment is not ready.

## Silent assumptions

- **Signal**: building on unstated premises — version, target, encoding, endianness, scope, identity, time zone, network path.
- **Counter**: list the load-bearing assumptions. Promote the riskiest one to a hypothesis and verify it cheaply before depending on it.

## Availability bias

- **Signal**: the candidate cause is the one the agent debugged last week, not the one most consistent with current evidence.
- **Counter**: generate hypotheses from the failure mode, not from memory. Then check whether the familiar candidate actually fits.

## Narrative coherence

- **Signal**: a story explains every observation neatly — including ones the hypothesis was never tested against.
- **Counter**: ask which observation, if discovered next, would break the story. If none, the story is unfalsifiable, not strong.

## Ladder-of-inference jump

- **Signal**: the investigation moves directly from selected data to action: "the graph spiked, so roll back" or "the crash is here, so patch this line."
- **Counter**: write the missing middle steps: selected data → interpretation → assumption → conclusion → action. Test the weakest assumption before acting.

## Base-rate neglect

- **Signal**: an exotic explanation outranks a common one without evidence because it is more interesting or recent.
- **Counter**: rank by prior likelihood before tool excitement. A cheap falsifier can still test the exotic branch, but it should not crowd out common causes.

## Premature solutioning

- **Signal**: the team builds a fix plan before it has supported the diagnostic branch of the problem tree.
- **Counter**: separate the "why" tree from the "how" tree. Solutions become candidates only after a cause has enough support to justify action.

## Tunnel vision under pressure

- **Signal**: time pressure, operator urgency, or a long session collapse the candidate set to one.
- **Counter**: spend two minutes generating alternatives anyway. Pressure increases the cost of being wrong; it does not justify skipping the gate.

## Hindsight reframing

- **Signal**: after a fix works, the investigation log is rewritten so the final hypothesis looks obvious.
- **Counter**: keep the original log intact. The dead ends are the most valuable record for the next investigation.

## Authority deference

- **Signal**: an earlier reviewer, doc, or senior engineer asserted a cause, so the hypothesis space is trimmed prematurely.
- **Counter**: treat prior assertions as hypotheses with priors, not as constraints. They still need a falsifier.
