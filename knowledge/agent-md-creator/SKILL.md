---
name: agent-md-creator
description: "Create, audit, or streamline root and nested AGENTS.md files. Use when defining repository instructions for coding agents or migrating existing agent instruction files."
license: MIT
metadata:
  author: AeonDave
  version: "1.1"
---

# Agent MD Creator

Produce repository instructions that let an agent complete the requested work using verified commands, local constraints, and clear completion criteria. Keep only guidance that changes a real decision or prevents a demonstrated mistake.

## Find the gap

Start with the requested scope, current user decisions, and applicable instruction files. Inspect the README, command definitions, CI, and code only where needed to establish a missing or disputed fact. A focused update does not require a full repository survey.

For an existing file, identify the concrete failure: stale command, missing constraint, conflicting rule, unnecessary reading, repeated approval, or premature stopping. For a new file, identify what an agent would otherwise need to rediscover or could get wrong. Ask only for information that materially changes the instructions and cannot be established locally.

## Choose the right home

- Root `AGENTS.md`: instructions shared across the repository.
- Nested `AGENTS.md`: commands or constraints that differ for one subtree, when the target host loads nested instructions.
- Existing docs or skills: specialized procedures and explanatory detail. Link with a task trigger, such as "Read `docs/schema.md` when changing the schema."
- Current task: one-off requests and temporary progress; do not turn them into persistent project policy.

Load [references/agents-md-principles.md](references/agents-md-principles.md) when resolving instruction scope, migrating files, or preserving decisions and exceptions.

## Write the operational contract

Include only sections that have concrete content:

- **Commands:** exact command, working directory, prerequisites, and change trigger where they matter. Verify against scripts or CI; do not invent missing commands.
- **Constraints:** non-obvious architecture, compatibility, generated-file ownership, or enforced contribution rules. Prefer a short instruction with its operational reason over broad prohibitions.
- **Completion:** the required result and relevant evidence. Name checks that establish it; state when broader validation is necessary. Preserve required gates without demanding unrelated tests for every edit.
- **Authorization:** retain real approval boundaries and current user decisions. Where useful, identify the already-authorized local work the agent should finish without another approval. Do not add blanket gates for research, debugging, dependencies, or routine edits.
- **Routing:** only the paths that save repeated discovery, with explicit conditions for loading specialized docs. Omit file inventories and duplicated README content.

Specify an exact sequence only when order prevents a concrete failure. Let the agent choose the route when several approaches satisfy the outcome. Examples must encode a verified local rule; do not import tool preferences, ignored warnings, or security choices from an unrelated project.

For a new file, [assets/minimal-agents-template.md](assets/minimal-agents-template.md) is an optional starting point. Replace its placeholders and delete unsupported sections; the template does not establish project policy.

## Review and finish

Read the resulting instructions together with applicable parent and host-specific files. Check that commands and paths exist, task triggers are clear, and edits preserve constraints and user decisions still in force. Do not execute deployment or destructive commands merely to verify their spelling; validate them from their definitions and report what remains unrun.

For a substantial rewrite, load [references/optimization-checklist.md](references/optimization-checklist.md) and compare behavior on representative tasks using the models and hosts the repository actually supports. Fix instructions that cause unnecessary reading, redundant checks, repeated approval, or early stopping while retaining genuine safeguards.

Deliver the edited files with a concise account of the behavior changed, verification performed, and unresolved facts. Completion requires a usable instruction file with no scaffold text, no broken local links, and no unsupported operational claims.
