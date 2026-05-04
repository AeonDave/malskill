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

## Core rule

Do not say work is complete, fixed, passing, clean, validated, or ready unless the verification command or artifact was checked in the current context.

## Gate workflow

1. **Name the claim**: what exactly is being asserted?
2. **Choose proof**: command, test, diff, log, replay, artifact, or checklist that would falsify the claim.
3. **Run or inspect fresh evidence**: use the full relevant check, not a partial proxy.
4. **Read the output**: exit code, failures, warnings, skipped checks, and scope limits.
5. **Report accurately**: claim success only when evidence supports it; otherwise state the actual status and next smallest fix.

## Common claim gates

| Claim | Requires | Not enough |
|---|---|---|
| Tests pass | fresh focused or suite output with zero relevant failures | previous run or assumed pass |
| Build succeeds | build command exit 0 | lint-only success |
| Bug fixed | original reproducer now passes | code changed near symptom |
| Requirements met | checklist against spec or request | tests pass without coverage of requirements |
| Skill valid | `quick_validate.py` on changed skill | frontmatter looks right by inspection |
| Delegated work done | inspect diff/artifacts and verify outputs | worker report says done |

## Security and offensive focus

- Exploit/tooling claims need reproduced primitive, target/build context, or marked uncertainty.
- Cleanup/remediation claims need post-action target-state evidence.
- Scanner triage needs replay, source/sink confirmation, or explicit downgrade.
- Report-ready findings need evidence, limits, and smallest next verification step.

## Resources

Load on demand:

- `references/completion-evidence.md` — detailed claim evidence table and red flags.
