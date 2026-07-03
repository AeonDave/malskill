---
name: hypothesis-driven
description: "Investigation discipline for extremely complex problems where the root cause, exploit path, or solution is unknown: hard bugs, flaky systems, CTF challenges, reverse engineering puzzles, incident triage, multi-system failures, and research questions backed by data. Forces explicit hypothesis generation, falsifiable predictions, prioritized experiments, and evidence-based iteration instead of trial-and-error patching or confirmation-biased reasoning. Use when symptoms are far from causes, when guesses keep failing, or when a problem spans tools, layers, or unknowns that defeat linear debugging."
license: MIT
compatibility: "AgentSkills-compatible investigation workflow for debugging, exploit research, CTF solving, incident response, reverse engineering, and data-backed technical research."
metadata:
  author: AeonDave
  version: "1.0"
---

# Hypothesis-Driven Investigation

## When to activate

- A bug, crash, regression, or flaky behavior resists two or more direct fixes.
- A CTF, exploit, or reversing challenge has many possible paths and no obvious next step.
- An incident, outage, or unexpected production behavior has unclear scope or cause.
- Research, fuzzing, or scanner output points in multiple directions and must be triaged.
- The symptom is far from the likely cause: heap corruption, async timing, protocol state, ABI mismatch, cache coherence, cryptographic oracle, side channel, supply chain.
- The agent notices itself looping, repeating searches, or escalating tools without new evidence.

Do not activate for trivial fixes, single-line typos, or tasks where the user already gave a step-by-step procedure. Prefer the smallest competent workflow.

## Core rules

- **Hypotheses must be falsifiable.** If no observation could disprove it, it is not a hypothesis — it is a belief.
- **Reduce before deep-diving.** Shrink noisy inputs, traces, repro steps, or artifact scope until the failure still occurs with minimal irrelevant detail.
- **One experiment, one hypothesis.** Test a single variable; otherwise you cannot tell which assumption was wrong.
- **Write it down.** Maintain an explicit log of hypotheses, predictions, evidence, and verdicts. The cost is small; the cost of re-testing the same idea twice is large.
- **Evidence wins over preference.** When data contradicts a favorite hypothesis, kill the hypothesis, not the data.
- **Stop the loop, not the work.** If three plausible fixes failed, the mental model is wrong. Re-examine assumptions before trying a fourth.

## Workflow

1. **Frame the problem**
   - Restate the symptom in one precise sentence: what is observed, where, when, under which conditions.
   - List what is known, what is assumed, and what is unknown. Separate facts from inference.
   - Preserve a reproducer or evidence baseline. If the input/artifact/log is large, reduce it first while keeping the same failure signal.
   - Define a falsification target: "this hypothesis is wrong if I see X."

2. **Generate hypotheses (breadth before depth)**
   - Enumerate plausible causes before committing to one. Aim for 3-7 candidates, MECE-style (mutually exclusive, collectively exhaustive enough to cover the space).
   - If there is only one candidate, assume anchoring until proven otherwise and generate alternatives. If there are more than ten, group them into higher-level branches before testing.
   - Build a diagnostic "why" tree before jumping to a solution "how" tree; solution ideas are premature until the cause branch is supported.
   - For each candidate, note the mechanism: how would this cause produce the observed symptom?
   - Reject any candidate that is not testable with available access, time, or tooling.

3. **Prioritize**
   - Score each hypothesis on three axes: prior likelihood, cost to test, and information gained if disproven.
   - Test cheapest-and-most-informative first. A fast experiment that eliminates a whole branch beats a slow one that only refines a narrow guess.
   - Prefer experiments that bisect the unknown space (binary search of the hypothesis tree).

4. **Design the experiment**
   - State the prediction: "if hypothesis H is true, then doing X will produce Y."
   - State the falsifier: "if I see Z instead, H is wrong."
   - Choose the smallest reliable observation: log, breakpoint, sanitizer, packet capture, syscall trace, oracle query, diff, replay, controlled input.
   - Prefer probes that expose structure: assertions/contracts for invariants, dependency tracing or slicing for value origins, and hypothesis-tagged instrumentation for runtime facts.
   - Add a negative control when possible: an input or condition where the hypothesis predicts no effect.

5. **Run and record**
   - Execute the experiment unchanged. Resist the urge to modify mid-run.
   - Capture raw evidence: command, input, output, timestamp/context, environment, version. Tag temporary logs or probes with the hypothesis ID so evidence stays attributable.
   - Record the verdict next to the hypothesis: supported, refuted, inconclusive, blocked.

6. **Update beliefs (Bayesian, not stubborn)**
   - If refuted: cross it out and move on. Do not resurrect without new evidence.
   - If supported: refine into a more specific sub-hypothesis. One supportive experiment is not proof.
   - If inconclusive: ask why the experiment was weak before designing the next one. Often the falsifier was not sharp enough.
   - Pause and re-frame whenever evidence contradicts a foundational assumption.

7. **Converge to a diagnosis**
   - A diagnosis is a hypothesis that (a) explains every prior observation and (b) predicts the next observation correctly.
   - Before acting on it, write the causal chain end-to-end: defect → faulty state → mechanism → observed symptom. If a link is hand-waved, the diagnosis is incomplete.
   - Show both causality and incorrectness: why this state caused the failure, and why the state itself is wrong rather than merely surprising.

8. **Act, then verify**
   - Apply the smallest change that the diagnosis predicts will work.
   - Re-run the original reproducer and at least one negative control.
   - When safe, run a counter-experiment: revert the fix or reintroduce the condition and confirm the original symptom returns.
   - If the fix works but the diagnosis was wrong, the symptom is likely to return; investigate further before claiming completion.

## Hypothesis log format

Keep it short. Update in place; do not let it grow into prose.

```text
H1: <one-line hypothesis>
  Mechanism: <how it would cause the symptom>
  Predicts:  <observation expected if H1 is true>
  Falsifier: <observation that would disprove H1>
  Test:      <command / experiment>
  Evidence:  <raw output, link, or summary>
  Verdict:   supported | refuted | inconclusive | blocked
```

For named failure modes to resist during investigation, load `references/cognitive-biases.md`.

## Domain-specific accents

- **Debugging**: minimize the reproducer, isolate environment, then bisect the code/data path with the cheapest instrumentation. Add assertions around invariants and trace data/control dependencies when the bad value's origin is unclear. Pair with `systematic-debugging` and `test-driven-development`.
- **CTF / exploit research**: enumerate attack surfaces before deep-diving one. Use oracles and probes that return distinguishable outputs (yes/no, timing, length). Bias toward experiments that eliminate whole categories (auth vs injection vs deserialization vs logic).
- **Reverse engineering**: separate observations (what the binary does) from inferences (why). Confirm guessed semantics with a controlled input before generalizing.
- **Incident response**: enumerate possible contributors before naming a root cause; distinguish root cause, trigger, contributing factors, impact, and mitigation. Correlate timelines, deploys, configs, and dependencies. Action items should be owned, measurable, and aimed at prevention or faster detection, not blame.
- **Research and data analysis**: pre-register the prediction before running the query; otherwise the analysis silently fits the data to the favorite story.

## Stop conditions

- The diagnosis is complete: the causal chain is explicit and reproduces the symptom on demand.
- The next experiment requires access, authorization, or destructive action beyond approved scope — pause and escalate.
- Three plausible fixes failed: stop patching, re-open assumptions.
- Evidence contradicts a load-bearing assumption: re-frame before generating more hypotheses on a broken foundation.

## Output contract

When reporting investigation results, include:

- **Symptom**: the precise observable being explained.
- **Diagnosis**: the supported causal chain, or "no diagnosis yet" with current best hypotheses.
- **Evidence**: experiments that confirmed it and at least one that ruled out a credible alternative.
- **Limits**: what was not tested, what assumptions remain.
- **Next step**: smallest action to either act on the diagnosis or sharpen it.

## Resources

Load on demand:

- `references/hypothesis-patterns.md` — hypothesis templates and falsifier examples per domain (debugging, CTF/exploit, reversing, incident, research).
- `references/cognitive-biases.md` — biases that derail investigation and counter-moves to apply during it.

Pair with:

- `systematic-debugging` for code-level reproduction, instrumentation, and patching once the hypothesis narrows to a code defect.
- `loop-control-and-pivots` when three attempts have failed and the mental model likely needs re-framing before more work.
- `evidence-before-claims` before reporting a cause, vulnerability, or fix as confirmed.
- `verification-before-completion` before claiming the investigation is done.
- `design-before-implementation` when the diagnosis triggers a non-trivial change.
- `known-problem-hint-research` when local hypotheses are exhausted and an external clue is needed.
