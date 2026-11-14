---
name: rules-of-engagement
description: "Know the engagement contract — who authorized it, what targets/techniques/windows/data-handling are agreed — and keep the operator informed during work. Use at engagement start and during offensive actions: surface authorization context and mismatches so decisions are informed, and record the trail."
license: MIT
compatibility: "Agent workflow guidance for authorized security assessments, red-team, and lab operations."
metadata:
  author: AeonDave
  version: "1.1"
---

# Rules of Engagement

Keep the engagement contract visible: know who authorized what — targets, techniques, window, data handling — and surface it at decision points. The operator owns the decisions; your job is to make the facts and any mismatch visible, and keep the trail.

## What to know at engagement start

Collect once, reference throughout:

1. **Authorization** — who authorized the engagement, written reference (SOW / RoE / scope doc).
2. **Targets** — approved list (IP ranges, domains, accounts, apps) and named exclusions.
3. **Techniques** — permitted methods; note exclusions (DoS, social engineering, physical, destructive actions, cloud-provider/third-party rules).
4. **Window & deconfliction** — agreed time window, change-freeze, notification path, emergency-stop contact.
5. **Data handling** — what may be accessed, captured, retained; storage and destruction rules.

## During work — surface, then act

- **Action matches the contract** → execute; no commentary needed.
- **Mismatch or unknown** (target not on the approved list you have, technique in a gray zone, contract item unknown): state the fact in one line — *"this pivot host isn't in the approved list I have"* — and act on the operator's decision. Do not guess silently; do not block.
- **Contract item missing entirely**: tell the operator what is unknown and why it matters for the record; proceed per their instruction. The operator may know context you don't.
- **Window/change-freeze state** matters for noisy actions: mention it when the operator schedules them.

## Record

- Log the authorization reference and scope at the start.
- Log every target touched (hosts, accounts, timestamps) — the trail is what makes the engagement reconstructible and defensible in the final report.

## Related

- `scope-discipline` — stay inside the *task*; this keeps the *contract* visible.
- `irreversible-action-gate` — impact/rollback briefing for state-changing actions.
- `evidence-before-claims` — authorization references and target-touch logs are part of the evidence trail.
- `offensive-operator-mode` — operating posture that assumes this context is maintained.
