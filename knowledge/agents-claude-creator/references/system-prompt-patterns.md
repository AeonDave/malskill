# System-Prompt and Description Patterns

How to write the two parts of an agent that decide whether it works: the **`description`** (does Claude delegate to it?) and the **body** (does it do the job well?).

## Contents
- [Writing the description (the router)](#writing-the-description-the-router)
- [Writing the body (the system prompt)](#writing-the-body-the-system-prompt)
- [Degrees of freedom](#degrees-of-freedom)
- [Briefing a cold agent](#briefing-a-cold-agent)
- [Output contracts](#output-contracts)
- [Annotated example agents](#annotated-example-agents)
- [Teams and orchestration](#teams-and-orchestration)

## Writing the description (the router)

Claude picks an agent by reading every agent's `description`. It is the single most important field. Rules:

- **Third person, present tense.** "Reviews code for security issues." Not "I review…" or "You can use this to…".
- **State what it does AND when to use it.** Pack concrete triggers: file types, task verbs, situations, error symptoms.
- **Add a proactivity cue** when you want hands-free delegation: "Use proactively after…", "Use immediately after writing or modifying code", "Use when encountering any errors or test failures."
- **Keep it sharp and single-purpose.** A description covering five jobs routes to none reliably.

| Weak (never triggers) | Strong (routes reliably) |
|---|---|
| `Helps with code` | `Expert code-review specialist. Proactively reviews changes for quality, security, and maintainability. Use immediately after writing or modifying code.` |
| `Database stuff` | `Executes read-only SQL/BigQuery queries and summarizes results. Use proactively for data-analysis tasks and reporting.` |
| `Fixes bugs` | `Debugging specialist for errors, test failures, and unexpected behavior. Use proactively when encountering any issue or stack trace.` |
| `Testing agent` | `Runs the test suite in isolation and reports only failing tests with their error messages. Use when tests need to run without flooding the main context.` |

## Writing the body (the system prompt)

The Markdown body becomes the agent's system prompt. The shape that consistently works:

```
You are a <role> specializing in <domain>.

When invoked:
1. <first concrete action — orient: run git diff, read the failing test, list the target files>
2. <core work step>
3. <produce the deliverable>

<Checklist / key practices — the standards the agent must apply>

<Output: exactly how to format the result returned to the caller>

<Focus rule: the single thing to optimize, or the thing never to do>
```

Why each part:
- **Role line** — sets stance and tone in one sentence; meaningfully shifts behavior.
- **"When invoked"** — a numbered procedure prevents the agent from wandering or skipping the orienting step (it starts cold and must gather its own context first).
- **Checklist** — the explicit quality bar; turns "review the code" into a repeatable standard.
- **Output contract** — the agent's result is the only thing that returns to the main conversation; specify its shape so the caller can use it.
- **Focus rule** — e.g. "Fix the root cause, not the symptom"; "You have read-only access — never attempt writes."

Keep it concise. Claude is already capable — add only what it doesn't already know (repo conventions, the exact workflow, the output shape). Don't explain general concepts.

## Degrees of freedom

Match specificity to how fragile the task is:

- **High freedom** (open-ended judgement: code review, research) — give direction and a checklist, trust the model to choose the path. Over-scripting hurts.
- **Low freedom** (fragile/destructive: schema migrations, batch edits, release steps) — give exact, ordered commands and a validation gate ("run X, only proceed if it passes"). Add a plan→validate→execute loop for high-stakes batch work.

## Briefing a cold agent

The agent sees none of the current conversation. Anything it must know goes into one of:
- **the body** — stable facts and conventions ("This repo uses pytest; tests live in `tests/`; never touch `vendor/`.");
- **`skills:`** — preloaded methodology/standards (full skill content injected at startup);
- **the delegation prompt** — task-specific, one-off context you state when you ask Claude to use the agent ("…and ignore the generated `dist/` folder").

If an agent keeps missing something, decide which of the three layers it belongs in. Stable → body. Reusable methodology → a skill. One-off → the delegation prompt.

## Output contracts

Make the returned summary directly usable. Examples:

- **Reviewer:** "Group findings by priority: Critical (must fix) / Warnings (should fix) / Suggestions. For each, give file:line, the problem, and a concrete fix."
- **Researcher:** "Return a short findings list with `file:line` citations and a one-paragraph synthesis. Do not paste large file contents."
- **Test runner:** "Return only failing tests with their error messages and the suspected file. Omit passing tests."

A tight output contract is also what keeps a high-volume agent (tests, search) from dumping its verbose context back into the main conversation — the whole reason to isolate it.

## Annotated example agents

### Read-only reviewer — boundary by tool restriction
```markdown
---
name: code-reviewer
description: Expert code-review specialist. Proactively reviews changes for quality, security, and maintainability. Use immediately after writing or modifying code.
tools: Read, Grep, Glob, Bash
model: inherit
---

You are a senior code reviewer ensuring high standards of quality and security.

When invoked:
1. Run git diff to see recent changes
2. Focus on the modified files
3. Begin the review immediately

Review checklist:
- Code is clear and readable; names convey intent
- No duplicated logic; proper error handling
- No exposed secrets or API keys; inputs validated
- Adequate test coverage; performance considered

Report findings by priority — Critical (must fix) / Warnings (should fix) /
Suggestions — each with file:line and a concrete fix.
```
*Why:* no `Write`/`Edit` → physically cannot modify code; "Run git diff" makes a cold agent orient itself; the output contract makes the result actionable.

### Fix-capable debugger — adds `Edit` because the job requires changes
```markdown
---
name: debugger
description: Debugging specialist for errors, test failures, and unexpected behavior. Use proactively when encountering any issue or stack trace.
tools: Read, Edit, Bash, Grep, Glob
---

You are an expert debugger specializing in root-cause analysis.

When invoked:
1. Capture the error message and stack trace
2. Identify reproduction steps and isolate the failure location
3. Form a hypothesis, add targeted logging, and confirm it
4. Implement the minimal fix and verify it resolves the issue

For each issue report: root cause, the evidence, the specific fix, and how you
verified it. Fix the underlying cause, not the symptom.
```

### Restricted researcher — read-only, cheap model
```markdown
---
name: safe-researcher
description: Read-only research agent that maps how a feature works across the codebase. Use proactively to gather context before planning a change, without making edits.
tools: Read, Grep, Glob
model: haiku
---

You are a codebase researcher. You never modify files.

When invoked:
1. Search broadly for the relevant modules, entry points, and call sites
2. Read only what you need to understand the flow
3. Return a concise map: key files with file:line, the data/control flow, and
   the seams where a change would land. Cite every claim with file:line.
Do not paste large file contents; summarize.
```

### Test runner — isolates verbose output
```markdown
---
name: test-runner
description: Runs the test suite in its own context and reports only failures. Use when tests would otherwise flood the main conversation with output.
tools: Bash, Read, Grep, Glob
model: haiku
---

You run tests and surface only what matters.

When invoked:
1. Detect the test command (package.json scripts, pytest, etc.)
2. Run the suite
3. Return ONLY failing tests: name, error message, and the file:line of the
   assertion or stack frame in our code. Omit passing tests and setup noise.
If everything passes, say so in one line.
```

## Teams and orchestration

For multi-domain work, build a **coordinator** plus focused **specialists** rather than one mega-agent.

- Keep each specialist single-responsibility with a sharp `description` and a tight tool boundary.
- The coordinator (often run as the main agent via `--agent`, or just the main conversation) decomposes the task and delegates. Restrict which types it may spawn with `tools: Agent(reviewer, debugger, test-runner), Read, Bash`.
- Specialists return summaries; the coordinator synthesizes. Because every spawn is cold, the coordinator must pass each specialist the context it needs in the delegation prompt.
- Route by cost: cheap specialists (search, summarize) on `haiku`; reasoning specialists on `sonnet`/`opus`.
- A subagent can spawn nested subagents (if `Agent` is in its `tools`) — useful for "reviewer dispatches a verifier per finding" so intermediate output never reaches the main conversation. Only the top-level summary returns.

Compose with skills: a specialist's methodology belongs in a **Skill** it preloads (`skills:`), keeping the agent file about role/tools/model and the reusable know-how portable.
