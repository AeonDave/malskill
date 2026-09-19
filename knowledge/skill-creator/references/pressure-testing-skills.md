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

Use natural requests. Do not disclose the expected answer in a multiple-choice prompt or ask the agent to recite the skill. Add time pressure or ambiguity only when it reflects the intended workload.

## Compare fairly

Snapshot the pre-edit skill or use no skill as the baseline. Run baseline and candidate in separate clean contexts with the same prompt, inputs, model, tools, permissions, and configuration. Keep output directories isolated; do not show either run the other's result.

Inspect both artifacts and execution traces. Use mechanical checks for objective contracts and qualitative review for judgment. Record:

- task success and correctness;
- constraints preserved and completion reached;
- unnecessary resource reads, tool calls, test reruns, or questions;
- configuration and targets actually exercised.

Do not grade exact prose, headings, or implementation choices unless the output contract requires them. If both versions succeed, report preserved behavior; fewer words alone do not prove faster or better execution. Repeat variable cases before attributing an improvement to one edit.

If a skill is shared across models or hosts, test the relevant targets or explicitly limit the conclusion. A thought experiment or reviewer reading the text is design review, not an execution test.

## Diagnose before adding rules

Locate the cause in the trace: missed activation, conflicting instructions, unnecessary prerequisite, unclear outcome, missing fact, unavailable resource, or a tool/environment failure. Change the responsible layer.

Try removing or narrowing an instruction when it caused the failure. Add a durable constraint only when the task requires it. Do not add a separate prohibition for every failed prompt or turn an environment problem into permanent skill policy.

Rerun affected scenarios after a correction, retaining unrelated success cases as regression checks. Stop expanding tests once the change is supported and no material uncertainty remains; report unavailable checks instead of inventing evidence.

Keep temporary outputs outside the skill directory. Bundle fixtures only when they will be reused, and keep evaluation notes out of runtime instructions.
