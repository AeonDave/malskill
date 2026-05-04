# Completion Evidence Gates

Use this reference before finishing tasks, writing report conclusions, committing, opening pull requests, or moving to the next plan step.

## Red flags

- Words like “should”, “probably”, “seems fixed”, “looks good”, or “ready” without a fresh check.
- Relying on a subagent, scanner, or tool summary without inspecting primary output.
- Treating one passing proxy as proof for a broader claim.
- Skipping verification because the change is small, urgent, or obvious.
- Calling a regression test valid without proving it fails on the broken behavior.

## Evidence by work type

| Work type | Strong evidence | Downgrade wording when |
|---|---|---|
| Code change | focused test, relevant broader tests, diff review | only static inspection was done |
| Build or packaging | build/package command exit 0 and artifacts exist | only lint or editor diagnostics passed |
| Skill edit | changed skill validates and resources are linked | only Markdown was visually checked |
| Research claim | cited primary sources and conflict check | sources are stale, indirect, or single-source |
| Exploit/tooling | clean reproduction with inputs, environment, and limits | works once, only under debugger, or timing is unstable |
| Delegated work | controller inspected diff and reran checks | worker report is the only evidence |

## Regression proof

For a bug fix, the best evidence is:

1. reproduce the original failure,
2. apply the fix,
3. observe the reproducer pass,
4. run the smallest broader check that could catch collateral damage.

When a full red-green reversal is too expensive, state the limitation explicitly.

## Completion output pattern

Use this shape for non-trivial completion claims:

- **Claim**: exact status being asserted.
- **Evidence**: commands/artifacts checked and relevant output summary.
- **Limits**: what was not checked or remains uncertain.
- **Next step**: merge, continue, investigate, or ask.
