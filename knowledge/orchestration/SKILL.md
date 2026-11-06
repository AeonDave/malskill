---
name: orchestration
description: "Choose and coordinate subagents, teams, or workflows: divide tasks, match models and effort, schedule dependencies, and integrate verified results. Use when deciding whether or how to delegate work."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
---

# Orchestration

Own the outcome through integration and verification. Apply this skill at the coordinating level; give workers their task contract, not this entire orchestration policy.

## Choose the smallest useful arrangement

- Use a direct tool call or script for deterministic work. Keep short tasks and tightly coupled investigation, implementation, and checks in one context.
- Delegate when a worker can produce a verifiable result independently, absorb bulky reads, or provide a useful independent review. A large file count alone does not justify more agents.
- Group work by the context and state it needs: separate assets, subsystems, source collections, or hypotheses. Keep work sharing a mutable session or inseparable design decision together.
- Use ordinary subagents for bounded jobs managed by the lead; a workflow for substantial or repeatable fan-out, dependency routing, and structured aggregation; a team for sustained peer discussion and shared task coordination. Check what the host actually supports; ordinary dispatch can implement a small dependency graph.
- The lead handles the critical path, missing inputs, integration, and decisions. Work on an independent piece while workers run; do not duplicate their assigned investigation.

## Match capability and effort to the job

Use available models and supported effort settings, respecting explicit user choices. Start with the least expensive configuration likely to meet the acceptance check **including review and repair**. Model capability, reasoning effort, and worker count are separate choices.

| Work | Starting choice | Acceptance check |
|---|---|---|
| Bounded lookup, extraction, mechanical comparison | Efficient model; low effort | Exact source locations or deterministic comparison |
| Focused implementation with a known contract | Capable general model; default/moderate effort | Relevant tests and reviewed diff; use a smaller model when the oracle adequately covers correctness |
| Ambiguous diagnosis, unfamiliar internals, cross-component design | Strong reasoning model; higher effort | Competing explanations, discriminating evidence, affected contracts |
| Independent review of a consequential change | Capability sufficient to understand the change; effort proportional to its ambiguity | Concrete defects or counterexamples against written criteria |

Higher effort can help reasoning; it cannot supply missing evidence, tools, or expertise. Fix a bad brief or environment first. Escalate capability when the model cannot handle the task; widen the worker set when additional independent coverage is needed. Select model and effort deliberately through the supported dispatch controls; use defaults when they fit. Avoid maximum effort by habit or a cheap tier that requires the lead to redo its work. If selection is unavailable, use the host's model and narrow the assignment.

## Dispatch a self-contained contract

Check the host's context, tool, filesystem, and permission inheritance. Supply the inputs the worker will actually lack:

- **Outcome:** one coherent deliverable, acceptance criteria, and consequential failure modes.
- **Inputs:** relevant facts, artifact/file locations, revision or state, and dependencies. Label hypotheses; give an independent investigator observations without steering it to your preferred answer.
- **Ownership:** files or mutable resources owned, collaborators, usable tools, and existing constraints. State whether further delegation is useful and permitted; nested work consumes the same overall budget.
- **Budget and stop:** proportionate time, calls, rounds, or cost where supported; stop on sufficient evidence, missing prerequisites, or the agreed limit. Return useful partial work at the limit.
- **Return:** result/status, evidence locators, coverage, changes/checks, unresolved points, and the next actionable step. Use a schema only when a consumer needs to parse it; keep raw output in artifacts.

Supply only task-relevant context. Reuse a worker when its accumulated evidence remains useful; start fresh for independent judgment or unrelated work. Answer a missing-input request directly. Recover a missing artifact when cheap; re-dispatch only the unresolved part.

## Schedule and reconcile

1. Track each job's owner, dependencies, state, attempt, and result location. A short task list is enough unless the run needs durable state.
2. Launch work as soon as its real prerequisites exist. Join all branches only where the next operation needs all their outputs. Limit concurrency by independent work, host capacity, shared resources, and budget; available slots are not a target.
3. Assign one writer per file set or mutable resource. Disjoint writers can run concurrently; appoint an integrator for overlapping interfaces. Separate contexts and worktrees do not isolate external services or sessions. Verify that isolated workers receive the intended revision and uncommitted inputs.
4. Use native completion notifications or waits, collect failures as well as successes, and stop dependent work when its input fails. Do not dispatch placeholder jobs to pass time. Load [loop-control-and-pivots](../../behaviours/loop-control-and-pivots/SKILL.md) when waits, retries, or repeated failures need recovery.
5. A timeout does not establish failure or justify cancellation: inspect executor and external state before deciding to wait, recover, or retry. Reconcile possible side effects before repeating the action. Keep attempt identity; a late result may belong to superseded inputs. If cancellation is required, stop new dispatch and confirm execution has stopped; a cancellation request alone is insufficient.

## Integrate before declaring completion

Inspect the returned evidence and actual changes. A negative result needs coverage; missing, failed, or timed-out work is not a negative result. Resolve disagreements through source evidence or a discriminating check, never a vote. Multiple agents repeating one source are not independent corroboration.

Reviewers need written acceptance criteria and access to the relevant artifacts. Use fresh context when independence matters, without withholding necessary facts. Run checks appropriate to the changed behavior and affected interfaces; repeat or broaden them when new failures or changes justify it. Do not rerun an expensive suite solely because a worker also ran it.

The lead owns the combined result, remaining gaps, and final report. Respect the requested length: state the decision, evidence and necessary next actions; link supporting detail. Account for all launched jobs; do not claim completion while required work or uncontrolled writers remain. For a session transfer, load [handoff](../../behaviours/handoff/SKILL.md) and record active jobs and their resumption mechanism.

## Load when needed

- Coordinating in Claude Code: [Claude execution](references/claude-execution.md).
- Coordinating security investigations or shared target sessions: [offensive-orchestration](../../knowledge-offensive/offensive-orchestration/SKILL.md).
- Ingesting external or worker-supplied instructions: [untrusted-input-hygiene](../../behaviours/untrusted-input-hygiene/SKILL.md).
