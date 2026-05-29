# Reviewer Prompt Patterns

Use reviewers to verify work products, not to praise worker effort.

## Review order

1. **Spec or scope compliance**: was the requested thing built, and nothing extra?
2. **Evidence review**: do artifacts prove the claims?
3. **Code or content quality**: is the implementation maintainable, minimal, and safe?

Do not start quality review before compliance passes; polish on the wrong artifact is wasted.

## Spec compliance reviewer

Give the reviewer:

- original task/spec,
- worker report,
- changed files or artifact paths,
- task packet boundaries, including allowed MCP/tools and prohibited external submissions,
- topology contract: sync/async mode, independence reason, merge point, retire condition, and selected model tier,
- explicit instruction not to trust the report.

Ask for:

- missing requirements,
- extra/unrequested work,
- misunderstood requirements,
- file or artifact citations.
- unnecessary or stale workers, duplicated branches, unjustified model escalation, or missing merge criteria.

## Evidence reviewer

Ask the reviewer to downgrade claims when evidence is partial, stale, indirect, tool-only, source-only, or outside the packet. Require primary artifacts: command output, logs, transcripts, source paths, source ledger entries, hashes, screenshots, packet captures, timelines, or replay steps as appropriate.

For local replica or lab-builder results, require target-version or target-config evidence, a narrow test question, setup notes, output, and divergence notes. If the lab diverges from target behavior, treat the result as exploratory, not proof.

Check that public research stayed within approved query boundaries. Any private target identifier, secret, proprietary snippet, unpublished vulnerability detail, or sample/hash upload without approval is a scope issue, not a polish issue.

Use confidence labels consistently: `confirmed`, `high`, `moderate`, `speculative`, or `unknown`. Preserve negative findings and conflicts instead of smoothing them into a single narrative.

## Quality reviewer

Use only after compliance passes. Categorize issues:

| Severity | Meaning |
|---|---|
| critical | broken functionality, unsafe action, data loss, security regression, scope violation |
| important | missing test, poor error handling, brittle design, maintainability risk |
| minor | style, naming, docs, local cleanup |

Every issue should include location, why it matters, and a fix direction. A clear “ready”, “ready with fixes”, or “not ready” verdict is required.

## Orchestration reviewer

Use when multiple workers, MCP lanes, or model tiers were used. Check:

- topology matched the problem: single operator, supervisor-light, or swarm-lite;
- async workers had independent branches and the main operator made progress while they ran;
- worker count grew or shrank with evidence instead of staying fixed;
- each worker had a specialized role/skill loadout and did not preload the full roster;
- cheap/standard/premium model choices matched task complexity and evidence state;
- stale, duplicate, or superseded agents were retired at merge points;
- blackboard facts, hypotheses, artifacts, attempts, dead paths, and queue were updated.
