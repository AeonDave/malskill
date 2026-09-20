---
name: external-feedback-triage
description: "Evaluate external technical feedback before acting. Use for reviews, scanner findings, blog advice, model suggestions, and recommendations whose applicability or evidence is uncertain."
license: MIT
compatibility: "AgentSkills-compatible review workflow for coding, research, and authorized security assessment."
metadata:
  author: AeonDave
  version: "1.0"
---

# External Feedback Triage

Treat every external suggestion as a hypothesis until it is checked against the current scope and evidence.

## When to activate

- A scanner, reviewer, model, blog, PoC README, advisory, or issue says what to fix or exploit.
- Feedback conflicts with local evidence.
- A requested change feels broad, risky, noisy, or unrelated to the original task.

## Triage loop

1. **Restate feedback** in neutral technical terms.
2. **Check applicability**: version, platform, configuration, code path, permissions, and scope.
3. **Classify independently**: impact (for example correctness, security, availability, or maintainability) and confidence (verified, plausible, or unverified). Record style or preference separately from defects.
4. **Verify evidence**: apply `evidence-before-claims` before accepting.
5. **Choose action**: apply, adapt, defer, reject, or ask for clarification.
6. **Patch minimally** when acting; do not bundle unrelated cleanup.
7. **Report disagreement** with evidence when rejecting or narrowing feedback.

## Pushback is useful

Do not agree just because feedback sounds authoritative. Push back when:

- it assumes an unsupported threat model
- it requires out-of-scope access or noisy actions
- it solves a different version/configuration
- it adds abstraction without repeated need
- it weakens tests, evidence, or operator safety

## Output contract

For non-trivial feedback, return:

- feedback summary
- applicability result
- action taken or rejected
- remaining risk or follow-up

Evidence output shape: pair with `evidence-before-claims`.

## Resources

Load on demand:

- `references/review-feedback.md` — decision table for reviews, scanner output, advisories, PoCs, and model suggestions.

Pair with:

- `evidence-before-claims` — evidence quality and claim wording when verifying accepted feedback.
- `verification-before-completion` — freshness gate before claiming the applied fix is complete.
