---
name: evidence-before-claims
description: "Evidence gate for security research, scanner triage, code review, and reporting. Use before confirming vulnerability impact, auth material, control results, cleanup, or root cause."
license: MIT
compatibility: "AgentSkills-compatible workflow guidance for code review, security testing, research, forensics, and reporting."
metadata:
  author: AeonDave
  version: "1.0"
---

# Evidence Before Claims

Use this skill when a conclusion could mislead an operator, reviewer, or report reader if it is overstated.

## Activation triggers

- Reporting exploitability, vulnerability impact, credential validity, bypass success, persistence, or cleanup.
- Summarizing scanner output, fuzzing crashes, reverse-engineering findings, malware behavior, or OSINT pivots.
- Saying a bug is fixed, a target is safe, a false positive is dismissed, or a root cause is known.

## Evidence ladder

Prefer the strongest evidence that is practical and authorized:

1. **Fresh reproduction**: exact command/API/action rerun in the current environment.
2. **Primary artifact**: logs, packet capture, crash trace, screenshot, hash, file path, HTTP transcript, debugger output.
3. **Independent corroboration**: second tool, manual replay, source review, negative control, or version check.
4. **Reasoned hypothesis**: clearly marked as likely/plausible and not final.
5. **Unverified lead**: useful for next steps only, never reported as confirmed.

## Claim workflow

1. State the claim in one sentence.
2. Identify what evidence would falsify it.
3. Gather or cite the freshest available evidence.
4. Downgrade wording if evidence is partial or stale.
5. Preserve reproduction details: command, input, timestamp/context, output, and limitations.
6. Separate confirmed facts from operator judgment and recommended next steps.

## Wording discipline

| Evidence state | Use wording like | Avoid |
|---|---|---|
| Reproduced now | confirmed, reproduced, observed | guaranteed, always |
| Strong but indirect | strongly indicates, consistent with | proven |
| Partial | likely, plausible, needs validation | vulnerable, exploitable |
| Tool-only | scanner reports, tool flagged | confirmed finding |
| Not checked | unverified lead | real issue |

## Stop conditions

Stop and ask for scope/authorization when verification requires destructive changes, credential use beyond read-only checks, noisy exploitation, persistence, or access outside the approved target set.

## Output contract

When finishing, include:

- **Claim**: the exact statement being made.
- **Evidence**: artifacts and commands used to support it.
- **Limits**: what was not tested or remains uncertain.
- **Next verification**: the smallest safe action to increase confidence.

## Resources

Load on demand:

- `references/offensive-evidence-gates.md` — concrete evidence requirements by offensive/research domain.

Pair with `verification-before-completion` before claiming a task, fix, validation, or report is complete.
