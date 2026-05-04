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
- explicit instruction not to trust the report.

Ask for:

- missing requirements,
- extra/unrequested work,
- misunderstood requirements,
- file or artifact citations.

## Evidence reviewer

Ask the reviewer to downgrade claims when evidence is partial, stale, indirect, or tool-only. Require primary artifacts: command output, logs, transcripts, source paths, hashes, screenshots, packet captures, or replay steps as appropriate.

## Quality reviewer

Use only after compliance passes. Categorize issues:

| Severity | Meaning |
|---|---|
| critical | broken functionality, unsafe action, data loss, security regression, scope violation |
| important | missing test, poor error handling, brittle design, maintainability risk |
| minor | style, naming, docs, local cleanup |

Every issue should include location, why it matters, and a fix direction. A clear “ready”, “ready with fixes”, or “not ready” verdict is required.
