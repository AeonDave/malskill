---
name: external-feedback-triage
description: "Triage external technical feedback before applying it. Use for code reviews, scanner findings, exploit PoC notes, blog advice, LLM suggestions, issue comments, and advisory recommendations. Verifies context fit, evidence, risk, and minimal changes instead of accepting or rejecting feedback performatively."
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
3. **Classify severity**: critical correctness, security risk, maintainability, style, or preference.
4. **Verify evidence** before acting: reproduction, source citation, local test, or manual replay.
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
- evidence checked
- remaining risk or follow-up

## Resources

Load on demand:

- `references/review-feedback.md` — decision table for reviews, scanner output, advisories, PoCs, and model suggestions.
