# Engagement Assurance Gate

**Load when**: you are about to declare the engagement (or a phase) complete, hand off to the client, or emit the supervisor report.

Engagement-LEVEL gate over the whole operation — distinct from per-finding proof. The per-claim evidence ladder and wording discipline live in `evidence-before-claims`; do not restate them. Here you verify a small matrix of ENGAGEMENT claims, each backed by an artifact and an honest status label, before anything ships. Pair with `verification-before-completion`.

## The no-labeling-up rule

Every engagement claim carries exactly one status. You **MUST NOT** label up.

| Status | Means | You may report it only when |
|---|---|---|
| `verified` | Supervisor personally re-checked the artifact just now. | YOU re-ran/re-inspected the proof yourself, fresh. |
| `attested` | Worker-reported; artifact is on file; NOT re-checked by you. | The artifact exists and is filed, but you did not re-verify it. |
| `unverified` | Claimed; no artifact backs it. | A claim exists with no proof — flag it as a gap, never as done. |

Hard line: **no `verified` without the supervisor's own fresh check.** A worker's "confirmed" is at most `attested` until you re-check it. Spot-check worker success-claims to promote `attested` → `verified`; never assume up.

## Engagement claim matrix

Before declaring complete, fill a status + artifact for each. Aim `verified` on scope, destructive-action, and cleanup claims at minimum.

```yaml
- claim: "Every reported finding has a reproduced artifact (req/resp, cmd+output, or trace)."
  status: verified | attested | unverified
  artifact: "path/id of each finding's proof"

- claim: "Scope was never exceeded — no out-of-scope host/URL/CIDR was touched."
  status: verified | attested | unverified
  artifact: "target log / proxy history scoped to ROE set"

- claim: "All worker success-claims were independently spot-checked by the supervisor."
  status: verified | attested | unverified
  artifact: "which claims re-run, with fresh output"

- claim: "Cleanup done — dropped files, test accounts, webshells, artifacts removed where required."
  status: verified | attested | unverified
  artifact: "removal command+output / confirmation per artifact"

- claim: "No destructive action was taken without explicit prior confirmation."
  status: verified | attested | unverified
  artifact: "confirmation record + list of any destructive step and its approval"

- claim: "Credentials were handled read-only unless write/use was explicitly authorized."
  status: verified | attested | unverified
  artifact: "what was done with each cred; authorization reference"

- claim: "Every worker failure preserved its root cause up to this report (no flattening)."
  status: verified | attested | unverified
  artifact: "wrapped error chains — see decision-and-error-journaling.md"
```

## Evidence package (sketch)

Attach, do not assert. Per shipped claim:

- **Claim** — the exact engagement statement.
- **Status** — `verified` / `attested` / `unverified` per the rule above.
- **Artifact** — the file path, id, or transcript that backs it (never prose-only).
- **Checked-by / when** — supervisor + fresh timestamp for anything `verified`.

## Rules

- **Gate blocks the handoff**: any `unverified` on a safety claim (scope, destructive, cleanup, cred handling) stops the report until resolved or explicitly disclosed as an open gap.
- **Attested is honest, inflation is not**: reporting `attested` when you did not re-check is correct and expected. Reporting `verified` when you did not is the failure this gate exists to catch.
- **Per-finding proof is upstream**: individual finding evidence is gathered via `evidence-before-claims`; this gate confirms the SET is complete and labeled, not each finding's internal ladder.
- **Downgrade on stale**: if an artifact is old or the environment changed, drop `verified` to `attested` or re-check.
