---
name: verification-before-completion
description: "Use when about to claim work is done, fixed, passing, validated, merged, report-ready, or safe to proceed. Requires fresh verification evidence before success claims, commits, pull requests, task completion, operator reports, cleanup claims, or moving to the next step."
license: MIT
compatibility: "AgentSkills-compatible verification workflow for coding, skill curation, research, and authorized security work."
metadata:
  author: AeonDave
  version: "1.0"
---

# Verification Before Completion

Completion is a claim. Claims need fresh evidence.

Boundary: `evidence-before-claims` governs claim wording and evidence quality in general. This skill is the **freshness gate at the completion boundary** — did you actually re-run the check after the last change?

## Core rule

Do not say work is complete, fixed, passing, clean, validated, or ready unless the verification command or artifact was checked **after the last change** in the current context.

## Gate workflow

1. **Name the claim**: what exactly is being asserted?
2. **Choose proof**: command, test, diff, log, replay, artifact, or checklist that would falsify the claim.
3. **Run fresh, post-edit**: use the full relevant check on the current tree; any prior run before the last edit is stale.
4. **Read the output**: exit code, failures, warnings, skipped checks, and scope limits. Exit 0 ≠ objective met — inspect what the tool actually produced.
5. **Report accurately**: claim success only when evidence supports it; otherwise state the actual status and next smallest fix.

## Common claim gates

| Claim | Requires | Not enough |
|---|---|---|
| Tests pass | fresh run **after the last code edit**, zero relevant failures | earlier green run before further edits |
| Build succeeds | build command exit 0 on current tree | lint-only, or stale build artifact |
| Bug fixed | original reproducer now fails-then-passes across the fix | code changed near symptom, or “should work” |
| Requirements met | checklist mapped to each spec/request item | tests pass without covering the requirement |
| Skill valid | `quick_validate.py` on the changed skill dir | frontmatter looks right by inspection |
| Objective met via tool | tool output shows the objective state | tool exit 0 or “no error” |
| Delegated / sub-agent work done | controller inspects diff/artifacts and re-runs the check | worker/sub-agent report says done |
| Cleanup / remediation complete | post-action target-state re-inspected | remediation command ran without error |

## Security and offensive focus

- Exploit/tooling claims need reproduced primitive, target/build context, or marked uncertainty.
- Cleanup/remediation claims need post-action target-state evidence.
- Scanner triage needs replay, source/sink confirmation, or explicit downgrade.
- Report-ready findings need evidence, limits, and smallest next verification step.

## Resources

Load on demand:

- `references/completion-evidence.md` — detailed claim evidence table and red flags.
