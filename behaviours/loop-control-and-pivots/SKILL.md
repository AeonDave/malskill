---
name: loop-control-and-pivots
description: "Stop unproductive retries and repeated polling. Use when the same failure recurs, a side issue consumes the task, or unfinished jobs are checked without new evidence."
license: MIT
compatibility: "AgentSkills-compatible loop-control guidance for coding, debugging, security testing, and research."
metadata:
  author: AeonDave
  version: "1.3"
---

# Loop Control and Pivots

Keep the requested outcome while changing approaches that no longer yield evidence.

## Retry or change course

- After repeated equivalent failures, compare the expected and actual result before another attempt. A small retry count is a reassessment cue, not proof that a cause or solution is impossible.
- Do not repeat unchanged authentication, permission, malformed-input, or unsupported-feature failures. Correct a demonstrated cause, use a supported route, or identify the missing capability.
- Retry transient failures only within the tool's retry policy and task budget, respecting backoff or server guidance.
- Record the failed approach, decisive error, and what the next attempt changes. Preserve useful partial results instead of restarting discovery.
- Give side issues a budget proportionate to their role in the deliverable. Continue independent work when a dependency is unresolved.

Use `hypothesis-driven` when the causal model is uncertain and `known-problem-hint-research` when a precise unresolved question would benefit from external evidence. Do not invent additional work simply to avoid reporting a limitation.

## Persistence and stopping

A failed approach does not automatically block the whole task. Check remaining supported alternatives that fit the authorization and budget. Stop at an explicit limit, an unavailable required capability, or a request to pause.

Distinguish a proven constraint from an untested assumption. Static evidence or a valid proof can justify a bounded conclusion; unsuccessful sampling alone cannot prove impossibility. Do not demand live actions outside the authorized scope to support every negative claim.

## Waiting for running work

- For a long-running job, identify its completion signal and execution deadline. Check the current host's tool contract before choosing a wait or notification mechanism.
- Prefer supported completion notifications or native waits. Do independent useful work meanwhile; when exhausted, use a wait suited to the expected duration within tool limits and higher-priority responsiveness requirements.
- If polling is the only supported option, space checks with backoff bounded by the job deadline and required intervention latency. Avoid short sleep/check loops and rereading unchanged logs.
- A wait returning early or timing out does not establish job failure. Check its reported state; silence alone does not justify cancellation, relaunch, or counting a failed attempt.
- End a turn with work pending only if the job can survive it; also require reliable host resumption or a user-agreed handoff. State the job, result location, and resume mechanism; otherwise retain responsibility for completion. Instructions alone do not create wake-ups.
- On completion, verify exit status and required artifacts before continuing dependent work. A delivered notification is not evidence of success.

## Budgets and handoff

Respect explicit runtime, cost, retry, and scope limits. If estimating a budget, scale it to the uncertainty and retain enough capacity for verification and reporting; no universal call count proves exhaustion.

For delegated work, enforce the agreed budget and investigate a missed milestone, reported failure, or scope drift before reassignment. Apply the running-work rules to a quiet worker.

When blocked, report the missing capability, exact failure or constraint, useful results, and the smallest action that would unblock the work. Follow the host's task-state contract before marking a goal blocked; the label is not a substitute for evidence.
