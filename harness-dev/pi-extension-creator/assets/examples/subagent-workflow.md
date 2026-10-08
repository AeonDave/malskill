---
description: Scout, plan, then implement a change through subagents
argument-hint: <change description>
---

Use the subagent tool to complete this request in three steps.

1. Chain: have `scout` find the code relevant to "$@", then have `planner` draft a minimal plan from `{previous}`.
2. Review the plan and tighten scope if needed.
3. Have `worker` implement the approved plan.

Request: $@
