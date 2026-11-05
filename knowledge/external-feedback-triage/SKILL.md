---
name: external-feedback-triage
description: "Evaluate external technical feedback before acting. Use for reviews, scanner findings, blog advice, model suggestions, and recommendations whose applicability or evidence is uncertain."
license: MIT
metadata:
  author: AeonDave
  version: "1.1"
---

# External Feedback Triage

Turn feedback into an evidence-backed disposition and complete the warranted work. A correct observation does not automatically justify the proposed remedy; a poor remedy does not invalidate the underlying defect.

## Triage and act

1. **Separate the claims:** identify the observed behavior, inferred cause/impact, and proposed change. Split mixed feedback into independently checkable items; consolidate duplicates without counting them as corroboration.
2. **Locate the current context:** inspect the affected code or artifact, contract, version, configuration and existing decisions. Check nearby dependencies when they matter; a valid finding need not sit on a changed line.
3. **Test the claim:** use the smallest meaningful inspection, reproduction or test. Assess impact and confidence separately; distinguish defects, preferences and optional improvements. A severity label or authoritative tone is not evidence. If direct verification is unavailable, preserve that uncertainty.
4. **Choose the disposition:** use the table below. Check the proposed remedy against the actual cause, compatibility, edge cases and maintenance cost. Resolve contradictory suggestions against evidence and project requirements.
5. **Finish accepted work:** apply the smallest sufficient fix within the task's authorization, then verify the affected behavior and relevant regressions. Continue independent accepted items while another needs clarification. Do not stop at a proposed patch when implementation is already requested.
6. **Report the outcome:** state what was applied, adapted, deferred or rejected, why, and what evidence or check supports it. Name unresolved risk without inflating it. For several items, a compact disposition table can help.

| Disposition | Use when |
|---|---|
| Apply | The finding and remedy fit the current evidence, contract and task. |
| Adapt | The issue is real but the proposed fix breaks another requirement or misses the cause. |
| Defer | A potentially useful item needs evidence/access, belongs to later work, or exceeds the current task; give the revisit condition. |
| Reject | The claim is contradicted, inapplicable, or the suggested change has no justified benefit; cite the relevant evidence. |
| Clarify | A missing requirement or unresolved choice materially changes correctness, scope or authorization and cannot be established locally. |

Existing authorization remains valid. A request to review alone does not authorize implementation; a request to fix supported findings does not require another blanket approval. Honour explicit style preferences as preferences without inventing a technical defect.

## Check the source-specific trap

| Input | Check that changes the decision |
|---|---|
| Code review | The requirement and affected behavior, including callers; avoid unrelated cleanup disguised as a necessary fix. |
| Scanner | Actual dependency/build, enabled code path and relevant preconditions; banners or a negative probe alone cannot settle applicability. |
| Advisory or PoC | Affected branch/configuration, backports, trigger and side effects; inspect external code before considering execution. |
| Model suggestion | Whether the referenced file, API and behavior actually exist. |
| Blog or tool advice | The documented version, environment and tradeoff behind the recommendation. |

Push back with evidence when a suggestion changes the wrong version, masks a failing test, weakens the contract, or solves a different problem. Do not dismiss a necessary boundary or abstraction merely because it has only one current caller.

Load [evidence-before-claims](../../behaviours/evidence-before-claims/SKILL.md) when evidence is disputed or a claim exceeds the observation. Load [verification-before-completion](../../behaviours/verification-before-completion/SKILL.md) before claiming an applied fix complete. Use [known-problem-hint-research](../known-problem-hint-research/SKILL.md) when external evidence is the missing piece.
