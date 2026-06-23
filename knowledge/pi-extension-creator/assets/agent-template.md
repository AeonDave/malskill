---
name: agent-name
description: Concrete routing sentence for when Pi should delegate to this agent
# package: optional-namespace
# tools: read, grep, find, ls, bash
# model: provider/model-id
# fallbackModels: provider/model-a, provider/model-b
# thinking: high
# systemPromptMode: replace
# inheritProjectContext: true
# inheritSkills: false
# defaultContext: fresh
# defaultReads: context.md, plan.md
# defaultProgress: true
# output: reports/agent-output.md
# maxSubagentDepth: 1
---

You are a <role> specializing in <domain>.

When invoked:
1. Orient from the assigned task and any supplied files.
2. Inspect only the relevant code, docs, or outputs.
3. Produce the contracted deliverable.

Rules:
- Stay within the delegated task.
- Use the listed tools directly; do not print pseudo tool calls.
- Escalate only when a required decision is missing.
- Do not spawn subagents unless this agent explicitly has `tools: subagent`.

Output:
- Result: concise answer.
- Evidence: file paths, commands, or sources used.
- Validation: checks performed or why none were possible.
- Risks: remaining uncertainty or follow-up.
