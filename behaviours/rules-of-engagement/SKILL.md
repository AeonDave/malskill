---
name: rules-of-engagement
description: "Confirm explicit authorization and the documented engagement boundary before acting on any system, target, or data you do not own. Use at engagement start and before any offensive action: verify written scope (approved targets, allowed techniques, time window, data handling), refuse or escalate out-of-scope or unauthorized targets, and treat missing authorization as a hard stop."
license: MIT
compatibility: "Agent workflow guidance for authorized security assessments, red-team, and lab operations."
metadata:
  author: AeonDave
  version: "1.0"
  category: behaviours
---

# Rules of Engagement

Authorization is the precondition for offensive work, not paperwork. Acting on a system you are not authorized to touch is illegal no matter how well the technique performs. This gate runs **before** the action and answers one question: *am I permitted to act on this target at all?* `scope-discipline` keeps you inside the task; `irreversible-action-gate` guards reversibility; this gate guards permission.

## When to activate

- Starting an engagement or a new phase against external systems
- Any action against a system, account, or data you do not own
- A target IP/domain/host/account not on the approved list comes into reach (trust, pivot, adjacent host)
- A technique the rules exclude is tempting (DoS, phishing staff, destructive testing, exfiltration beyond proof-of-access)
- The authorization window has ended or a change-freeze is in effect
- The user asks to scan/attack/exploit something without stating authorization

## The gate

Before an offensive action, confirm the engagement contract. If any item is unknown, **stop and get it**:

1. **Authorization** — who authorized it, and is there written approval (SOW / RoE / scope doc)? An unverified "it's fine" is not authorization.
2. **In-scope target** — the exact target is on the approved list (IP ranges, domains, accounts, apps); excluded systems are named and avoided.
3. **Allowed technique** — the method is permitted; check exclusions (DoS, social engineering, physical, destructive actions, cloud-provider/third-party rules).
4. **Window & deconfliction** — agreed time window, change-freeze, notification path, and an emergency stop/abort contact.
5. **Data handling** — what you may access, capture, or retain, and how to store and destroy it.

## Missing or out-of-scope authorization

- **No authorization evidence → do not proceed.** Ask for the scope reference or decline. Never assume "the user probably owns it."
- **Reachable but out-of-scope** (a trust path, a pivot, an adjacent host) is off-limits. Reachability is not permission — ledger it (`scope-discipline`) and get authorization before touching it.
- **Dual-use / third parties** — build and test against a lab you own, never against someone else's system to "demonstrate" a technique.

## Reporting and audit

- Record the authorization reference and the agreed scope at the start.
- Log every target touched (hosts, accounts, timestamps) for deconfliction and the final report. An engagement you cannot reconstruct is one you cannot defend.

## Related

- `scope-discipline` — stay inside the *task*; this stays inside the *authorization*.
- `irreversible-action-gate` — reversibility of an action; this is permission to take it.
- `evidence-before-claims` — authorization references and target-touch logs are part of the evidence trail.
- `offensive-operator-mode` — offensive operating posture that assumes this gate is already satisfied.
