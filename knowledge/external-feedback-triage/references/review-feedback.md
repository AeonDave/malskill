# Review Feedback Decision Table

## Classify input

| Source | First check | Common failure |
|---|---|---|
| Code review | Does it apply to changed lines and project style? | Drive-by refactor |
| Scanner | Can it be manually replayed or correlated? | False positive from version/banner |
| Advisory | Does target version/config match? | Patch assumed from wrong branch |
| Exploit PoC | Are preconditions and side effects acceptable? | Lab-only exploit treated as real |
| LLM suggestion | Is it grounded in files/evidence? | Plausible but invented API/path |
| Blog/tool guide | Is the recommendation current and scoped? | Cargo-cult flags |

## Actions

- **Apply**: evidence is strong, scope fits, change is minimal.
- **Adapt**: core issue is real but proposed fix does not match local architecture.
- **Defer**: valid but outside current objective or needs owner approval.
- **Reject**: evidence is wrong, stale, unsafe, or out of scope.
- **Ask**: ambiguity affects safety, architecture, or data integrity.

## Evidence before acceptance

For code feedback, prefer failing test, compiler/linter error, or direct code citation.

For security feedback, prefer reproduction, reachable source/sink path, packet/log trace, or trusted advisory plus matching version/configuration.

For performance feedback, prefer benchmark/profiler output before and after.

## Response patterns

- “Accepted with adaptation: local API uses X, so the minimal fix is Y.”
- “Rejected: scanner matched version string, but feature Z is disabled and manual replay returns 404.”
- “Deferred: valid hardening idea, but it changes auth behavior outside this patch.”
- “Need clarification: proposed exploit step is noisy/destructive and scope does not authorize it.”

## PR and merge rigor

Before accepting broad feedback or preparing a review request, check:

- What problem is this change solving?
- Does the change bundle unrelated work?
- Were alternatives considered or intentionally rejected?
- Was the affected behavior tested adversarially, not only on the happy path?
- Did a human or independent reviewer inspect the complete diff when risk is high?
