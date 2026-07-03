# Proof Capsule

A portable, self-contained receipt that lets a third party re-prove a VERIFIED finding against the live target **without trusting your tooling**. If it cannot be replayed by someone else, it is not a proof capsule.

## Contents
- [Required fields](#required-fields)
- [Schema](#schema)
- [Replay contract](#replay-contract)
- [Multi-step chains](#multi-step-chains)
- [What disqualifies a capsule](#what-disqualifies-a-capsule)

## Required fields

Every capsule must carry, at minimum:

- **finding_id / title / class** — what and which vuln class.
- **oracle** — the *named* oracle that earned the verdict (gate rule: no name → not VERIFIED).
- **target** — host-locked scope the recipe runs against.
- **recipe** — the exact, replayable action: full HTTP request (method, path, headers, body) or command line + payload. No placeholders the replayer must guess.
- **positive_signal** — the machine-decidable condition that means "vulnerable" (regex, exact token, arithmetic result, OOB token seen).
- **runs** — the N/N log: each run's outcome, proving determinism (default N=3).
- **control** — the safe surface tried and the fact that the oracle *failed* there.
- **severity + impact_basis** — rating and whether it is reachability-only (medium) or impact-proven.
- **replay** — a single command/step the recipient runs to reproduce it.

## Schema

Portable JSON skeleton (adapt keys to your report tooling; keep all required fields):

```json
{
  "finding_id": "a1b2c3d4",
  "title": "JWT alg:none accepted on /api/admin",
  "class": "auth-jwt-bypass",
  "verdict": "VERIFIED",
  "oracle": "jwt_alg_none_protected_endpoint",
  "target": "https://staging.example.com",
  "recipe": {
    "type": "http",
    "request": "GET /api/admin/users HTTP/1.1\nHost: staging.example.com\nAuthorization: Bearer <forged-alg-none-jwt>\n",
    "payload_notes": "header {\"alg\":\"none\"}, claim {\"role\":\"admin\"}, empty signature"
  },
  "positive_signal": { "type": "response_contains", "value": "\"role\":\"admin\"" },
  "runs": [
    { "n": 1, "result": "positive", "status": 200 },
    { "n": 2, "result": "positive", "status": 200 },
    { "n": 3, "result": "positive", "status": 200 }
  ],
  "control": {
    "surface": "same request, valid HS256 signature stripped to wrong key",
    "expected": "reject",
    "observed": "401",
    "passed": true
  },
  "severity": "high",
  "impact_basis": "returned admin-only user list (impact-proven, not reachability-only)",
  "replay": "ptai-style: replay recipe.request, assert positive_signal, assert control rejects"
}
```

## Replay contract

A capsule is valid only if an independent replayer can:

1. Load `recipe` and fire it verbatim against `target`.
2. Evaluate `positive_signal` on the response → must be true.
3. Fire the `control` surface → `positive_signal` must be false.
4. Conclude VERIFIED **only** when 2 passes and 3 fails.

Provide the replay as one command where possible. The recipient must not need your source, your DB, or your session to reach the same verdict.

## Multi-step chains

- One capsule per proven finding; for a chain, bundle every hop's capsule under a `chain` wrapper with ordered `hops[]`, each independently replayable.
- A chain is `VERIFIED` only if **every** hop is `VERIFIED`. One `candidate` hop makes the whole chain `candidate`.
- Carry state between hops explicitly (token/id extracted at hop k feeds hop k+1) so the chain replays end to end.

## What disqualifies a capsule

- No named oracle → downgrade to `candidate`.
- Missing or passing control (oracle also fired on the safe surface) → not proven.
- Recipe depends on a stale cached token/session instead of fresh state per run.
- `positive_signal` is a scanner label or an LLM sentence, not a condition on the target's real response.
- Runs are < N or not all positive.
- Recipe contains unresolved placeholders the replayer must invent.
