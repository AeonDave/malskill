---
name: verification-before-completion
description: "Check evidence before reporting work complete, fixed, passing, or ready. Use at a completion boundary or when later changes may have invalidated an earlier result."
license: MIT
compatibility: "AgentSkills-compatible verification workflow for coding, skill curation, research, and authorized security work."
metadata:
  author: AeonDave
  version: "1.1"
---

# Verification Before Completion

Match each completion claim to evidence for the state being delivered. `evidence-before-claims` owns general evidence quality and uncertainty; this skill checks freshness and coverage.

## Completion gate

1. Name the outcome being claimed and the check that can detect its failure.
2. Run the relevant check after the last change that could affect its result. Preserve required repository gates.
3. Inspect exit status, substantive output, skipped cases, and the artifact or state actually checked.
4. Map the evidence to acceptance criteria. Report uncovered requirements and unavailable checks explicitly.
5. Correct failures and rerun affected checks. Once checks pass, repeat or broaden them only for a new change, failure, or unresolved concern.

A recorded result may be reused when its command, inputs, revision, environment, and coverage still match. A new turn or a different reader does not by itself make evidence stale. Concurrent changes or uncertain provenance require renewed verification.

## Select the check

| Claim | Useful evidence | Limit |
|---|---|---|
| Tests pass | Relevant suite on the delivered code | Passing tests do not establish untested requirements. |
| Build succeeds | Successful build for the intended target | Lint alone does not establish a build. |
| Bug fixed | Original failure reproduced and then resolved | A nearby edit is not proof; disclose unavailable baseline reproduction. |
| Skill structure valid | Frontmatter validation and resource sweep | Structural checks do not prove behavior or token savings. |
| Delegated work complete | Inspect diff/artifacts and corresponding check output | Rerun when state, coverage, or provenance is insufficient; a summary alone is not evidence. |
| Remediation complete | Relevant post-action state | A successful command may not establish the intended effect. |

Use diff inspection and required structural checks for low-impact editorial work; do not invent runtime tests that merely mirror text. Distinguish checks not run from checks that failed.

Load [references/completion-evidence.md](references/completion-evidence.md) when choosing regression evidence or diagnosing an overstated completion claim.
