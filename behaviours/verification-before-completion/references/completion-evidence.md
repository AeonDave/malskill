# Completion Evidence Gates

Deep-dive for the freshness gate: red flags, downgrade wording, regression proof.
Output shape (Claim / Evidence / Limits / Next) lives in `evidence-before-claims`.

## Red flags

- Words like "should", "probably", "seems fixed", "looks good", or "ready" without a fresh check.
- Relying on a sub-agent, scanner, or tool summary without inspecting primary output.
- Tool exited 0 or "no error" treated as objective met.
- Green test run cited after further code edits (stale).
- Treating one passing proxy as proof for a broader claim.
- Skipping verification because the change is small, urgent, or obvious.
- Calling a regression test valid without proving it fails on the broken behavior.

## Downgrade wording by work type

| Work type | Downgrade wording when |
|---|---|
| Code change | only static inspection was done, no test run |
| Build / packaging | only lint or editor diagnostics passed |
| Skill edit | only Markdown was visually checked, validator not run |
| Research claim | sources are stale, indirect, or single-source |
| Exploit / tooling | works once, only under debugger, or timing is unstable |
| Delegated / sub-agent work | worker report is the only evidence, no diff replay |
| Cleanup / remediation | remediation ran but target state not re-inspected |

## Regression proof

For a bug fix, the strongest evidence is:

1. reproduce the original failure,
2. apply the fix,
3. observe the reproducer pass,
4. run the smallest broader check that could catch collateral damage.

When a full red-green reversal is too expensive, state the limitation explicitly.
