# Behavior Testing Skills

Use when an instruction change needs behavioral evidence or a real run reveals a failure. Editorial changes can use diff review and structural checks.

## Define an observable contract

Choose realistic tasks that exercise the changed decision. Record inputs, expected artifacts or actions, prohibited outcomes, and what counts as complete before running them. Use a few representative cases initially; expand only for unresolved variation or risk.

Examples of useful checks:

| Change | Expected behavior | Failure to detect |
|---|---|---|
| Conditional reference loading | Reads the selected format's rules and produces a valid export | Loads every format guide or omits required constraints |
| Flexible tool choice | Uses an available helper that satisfies the contract | Reimplements working tooling to follow an arbitrary recipe |
| Completion guidance | Finishes authorized edits, relevant checks, and corrections | Stops after a draft or repeats checks with no new reason |
| Approval boundary | Continues permitted local work; asks at an actual restricted action | Adds approval stops or expands authorization |
| Scope control | Keeps a typo fix local | Rebuilds the workflow or adds a new skill for a one-off input |
| Waiting for a job | Uses the supported completion mechanism and verifies the result | Repeated empty checks, premature cancellation, or ending the turn without a viable resume path |

Use natural requests. Do not disclose the expected answer in a multiple-choice prompt or ask the agent to recite the skill. Add time pressure or ambiguity only when it reflects the intended workload.

## Compare fairly

Snapshot the pre-edit skill or use no skill as the baseline. Run baseline and candidate in separate clean contexts with the same prompt, inputs, model, tools, permissions, and configuration. Keep output directories isolated; do not show either run the other's result.

For historical incidents, define the simulated investigation time and preserve the permitted code and telemetry. Record expired evidence; exclude later fixes, postmortems, recovery data, saved notes, and previous-run results that reveal answers unavailable at that time. Inspect transcripts for leakage. Grade onset, affected scope, cause, and uncertainty separately; correct timing does not establish causality. Test handoff usefulness against a fixed evidence snapshot and the recipient's next decision, separately from diagnosis accuracy. See [OpenAI's incident evaluations](https://openai.com/index/how-openai-performance-factory-keeps-chatgpt-fast/).

Keep all valid trials, including task failures and regressions, in the outcome denominator. Define exclusions for invalid measurements before comparing results and report excluded trials with reasons. Report cost among successful runs as conditional, alongside the success rate; dropping failures or runs where the candidate loses does not establish a general improvement.

Inspect both artifacts and execution traces. Use mechanical checks for objective contracts and qualitative review for judgment. Record:

- task success and correctness;
- constraints preserved and completion reached;
- unnecessary resource reads, tool calls, test reruns, or questions;
- configuration and targets actually exercised.

Do not grade exact prose, headings, or implementation choices unless the output contract requires them. If both versions succeed, report preserved behavior; fewer words alone do not prove faster or better execution. Repeat variable cases before attributing an improvement to one edit.

For reviews or scans, use [evidence-before-claims](../../../behaviours/evidence-before-claims/SKILL.md) to distinguish refuted findings from unresolved ones. Track known-issue coverage and missed cases alongside false positives; fewer reported findings can reduce both errors and valid detections. State each metric's denominator and reference scope: incomplete labels support recall only for that labeled subset. Separate harness/grader failures from agent errors and resolve material grading defects before comparing quality.

If a skill is shared across models or hosts, test the relevant targets or explicitly limit the conclusion. A thought experiment or reviewer reading the text is design review, not an execution test.

For efficiency claims, compare total work through verified completion, including coordination, waiting, review, and repairs. Record model requests, elapsed time, and available usage counters with cached input separated from uncached input and output. Label the measurement boundary and pricing basis; API-equivalent cost estimates do not establish subscription-quota savings. Change one factor at a time when claiming what caused a difference.

## Diagnose before adding rules

Locate the cause in the trace: missed activation, conflicting instructions, unnecessary prerequisite, unclear outcome, missing fact, unavailable resource, or a tool/environment failure. Change the responsible layer.

Try removing or narrowing an instruction when it caused the failure. Add a durable constraint only when the task requires it. Do not add a separate prohibition for every failed prompt or turn an environment problem into permanent skill policy.

Rerun affected scenarios after a correction, retaining unrelated success cases as regression checks. Stop expanding tests once the change is supported and no material uncertainty remains; report unavailable checks instead of inventing evidence.

Keep temporary outputs outside the skill directory. Bundle fixtures only when they will be reused, and keep evaluation notes out of runtime instructions.
