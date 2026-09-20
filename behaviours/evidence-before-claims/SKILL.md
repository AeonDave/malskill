---
name: evidence-before-claims
description: "Evidence gate for security research, scanner triage, code review, and reporting. Use before confirming vulnerability impact, auth material, control results, cleanup, or root cause."
license: MIT
compatibility: "AgentSkills-compatible workflow guidance for code review, security testing, research, forensics, and reporting."
metadata:
  author: AeonDave
  version: "1.1"
---

# Evidence Before Claims

Use this skill when a conclusion could mislead an operator, reviewer, or report reader if it is overstated.

## Activation triggers

- Reporting exploitability, vulnerability impact, credential validity, bypass success, persistence, or cleanup.
- Summarizing scanner output, fuzzing crashes, reverse-engineering findings, malware behavior, or OSINT pivots.
- Saying a bug is fixed, a target is safe, a false positive is dismissed, or a root cause is known.

## Evidence ladder

Prefer the strongest evidence that is practical and authorized. Scale the bar to the claim's stakes: high-impact, irreversible, or report-bound claims demand the top tiers; reversible local notes do not.

1. **Observed behavior**: a recorded command/API/action and result for the relevant environment. Repeat nondeterministic checks according to the uncertainty; a fixed number of passes does not prove reliability.
2. **Primary artifact**: logs, packet capture, crash trace, hash, file path, HTTP transcript, debugger output. Preserve provenance and context; prefer searchable originals for textual evidence, while screenshots can be primary evidence for visual behavior.
3. **Independent corroboration**: second tool, manual replay, source review, negative control, or version check.
4. **Reasoned hypothesis**: clearly marked as likely/plausible and not final.
5. **Unverified lead**: useful for next steps only, never reported as confirmed. Includes any LLM/subagent assertion not yet checked against a primary artifact.

## Claim workflow

1. State the claim in one sentence.
2. Identify what evidence would falsify it.
3. Gather or cite the freshest available evidence.
4. Downgrade wording if evidence is partial or stale.
5. Preserve reproduction details: command, input, timestamp/context, output, and limitations.
6. Separate confirmed facts from operator judgment and recommended next steps.

## Self-check before asserting

Before emitting a consequential conclusion, check its load-bearing assertions:

- List each load-bearing assertion; for any that no primary artifact backs, verify it or label it a lead — reasoning is not evidence.
- Flag any claim you would not stake a fresh reproduction on, and downgrade its wording to match.
- Inspect the primary artifacts behind prior output or a subagent report. Reuse applicable verified evidence; rerun only when state, provenance, or coverage is insufficient (see `verification-before-completion`).

## Wording discipline

| Evidence state | Use wording like | Avoid |
|---|---|---|
| Reproduced now | confirmed, reproduced, observed | guaranteed, always |
| Strong but indirect | strongly indicates, consistent with | proven |
| Partial | likely, plausible, needs validation | vulnerable, exploitable |
| Tool-only | scanner reports, tool flagged | confirmed finding |
| Not checked | unverified lead | real issue |
| LLM/subagent said so | reported by model/subagent, pending replay | found, confirmed |

## Stop conditions

Do not expand access or authorization merely to verify a claim. If a needed check is outside the approved boundary, report that limitation and obtain the missing authorization before it; continue independent permitted work.

## Output contract

For consequential findings, include the following information without requiring a separate template for every minor observation:

- **Claim**: the exact statement being made.
- **Evidence**: artifacts and commands used to support it.
- **Limits**: what was not tested or remains uncertain.
- **Next verification**: the smallest safe action to increase confidence.

## Resources

Load on demand:

- [references/offensive-evidence-gates.md](references/offensive-evidence-gates.md) — load when grading domain-specific research evidence or worker claims.

Pair with `verification-before-completion` before claiming a task, fix, validation, or report is complete.
