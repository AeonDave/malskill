---
name: evidence-before-claims
description: "Evidence gate for security research, scanner triage, code review, and reporting. Use before confirming vulnerability impact, auth material, control results, cleanup, or root cause."
license: MIT
compatibility: "AgentSkills-compatible workflow guidance for code review, security testing, research, forensics, and reporting."
metadata:
  author: AeonDave
  version: "1.3"
---

# Evidence Before Claims

Use this skill when a conclusion could mislead an operator, reviewer, or report reader if it is overstated.

## Activation triggers

- Reporting exploitability, vulnerability impact, credential validity, bypass success, persistence, or cleanup.
- Summarizing scanner output, fuzzing crashes, reverse-engineering findings, malware behavior, or OSINT pivots.
- Saying a bug is fixed, a target is safe, a false positive is dismissed, or a root cause is known.

## Match evidence to the claim

Choose evidence that can establish the specific claim within authorized scope. Scale verification effort to the consequences and uncertainty; execution is not required for every fact.

- **Observed behavior**: a recorded action and result for the relevant environment. Repeat nondeterministic checks according to the uncertainty; a fixed number of passes does not prove reliability.
- **Established from artifacts**: inspected source, configuration, documents, logs, or other primary material supports the conclusion. Show the derivation and its conditions; distinguish documented or statically established behavior from behavior observed in a running target.
- **Reported or hypothesized**: attribute unchecked reports and label inferences with unresolved premises. An LLM/subagent summary alone is a lead, not confirmation.

Preserve provenance and context. Prefer searchable originals for textual evidence; screenshots can be primary evidence for visual behavior. A primary source establishes what it records, not automatically every claim its author makes.

Use corroboration to address a specific uncertainty. Check whether sources or methods share the same underlying report, signature, or failure mode; agreement alone is not independent confirmation.

## Claim workflow

1. State the claim and its scope: target, revision/configuration, and time window where relevant.
2. Identify evidence that could falsify it or distinguish competing explanations.
3. Inspect applicable evidence and its provenance. Separate observed facts, derived conclusions, and unresolved assumptions.
4. Address material contradictory evidence; check for different states or conditions before choosing a conclusion. If unresolved, report the conflict.
5. Preserve enough detail to check the result: source locator or command/input, relevant state, output, and limitations.
6. Narrow the wording to what the evidence establishes; separate findings from recommendations.

## Self-check before asserting

Before emitting a consequential conclusion, check its load-bearing assertions:

- Check that each load-bearing assertion has supporting material and that any derivation follows from it; plausibility alone is not evidence.
- For negative claims, check collection success, search coverage, permissions, and time range. No match supports only the examined scope; failed access or missing telemetry leaves the result unknown.
- Inspect the primary artifacts behind prior output or a subagent report; use `verification-before-completion` for freshness and rerun decisions.

## Wording discipline

| Evidence state | Use wording like | Avoid |
|---|---|---|
| Reproduced now | confirmed, reproduced, observed | guaranteed, always |
| Established from inspected source | code establishes X under conditions Y | observed in production, dynamically reproduced |
| Strong but indirect | strongly indicates, consistent with | proven |
| Partial | supported within X; Y remains unverified | claims broader than the evidence |
| Unreviewed scanner finding | scanner reports, tool flagged | confirmed finding |
| Not checked | unverified lead | real issue |
| LLM/subagent summary only | reported by model/subagent, pending artifact review | found, confirmed |

The general stance behind this table — labeling every statement by the confidence it earned — is `uncertainty-calibration`.

## Stop conditions

Do not expand access or authorization merely to verify a claim. If a needed check is outside the approved boundary, report that limitation and obtain the missing authorization before it; continue independent permitted work.

## Output contract

For consequential findings, include the following information without requiring a separate template for every minor observation:

- **Claim**: the exact statement being made.
- **Evidence**: artifacts and commands used to support it.
- **Limits**: what was not tested or remains uncertain.
- **Next verification**, if uncertainty remains: the smallest authorized action that could resolve it, or the missing prerequisite.

## Resources

Load on demand:

- [references/offensive-evidence-gates.md](references/offensive-evidence-gates.md) — load when grading domain-specific research evidence, worker claims, or an engagement's final evidence summary.

Pair with `verification-before-completion` before claiming a task, fix, validation, or report is complete.
