# Supervisor + Hidden Subagents — Orchestrator Pattern

Field-tested pattern for an OpenCode team: one visible primary that thinks and delegates, plus a roster of hidden subagents that execute. Adapt the skeletons; do not copy verbatim.

## Why this shape

- **One visible entry point.** Only the supervisor is `mode: primary`; everything else is `hidden: true` subagent. The user talks to one agent; complexity hides behind it.
- **Isolated context per worker.** Each Task dispatch spins up a fresh session with its own context window and (pinned) model. The only channel in is the dispatch prompt; the only channel out is the worker's final report. This is the core token-saver — and the core constraint.
- **The supervisor is the expensive brain.** It plans, gates scope, decomposes, dispatches, reviews evidence, synthesizes. Push token-heavy/low-judgement work down to cheap workers.

## Supervisor prompt skeleton

```markdown
---
description: >-
  Use this <supervisor-name> for <domain> supervision and coordinated dispatch
  of specialized subagents. It is the sole visible primary: it plans, validates
  scope, decomposes objectives, and delegates to hidden subagents. Use it before
  significant actions and at each milestone.
mode: primary
permission:
  task:
    "*": deny
    "team-*": allow
    "utility-*": allow
  edit: deny        # if it should never modify files itself
  bash: deny        # if it should never execute commands itself
---
You are <supervisor-name>, the primary supervisor and sole visible agent. You plan,
decompose, dispatch, review, and synthesize. You do not act as a direct operator.

## Scope gate
Confirm objective, environment, and constraints before dispatching. If scope is
ambiguous, ask first.

## Roster
| ID | Domain |
|----|--------|
| team-x | <bounded domain> |
| team-y | <bounded domain> |
| utility-reader | parse / extract (cheap model) |
| utility-researcher | public web lookup (cheap model) |

## Dispatch protocol
Invoke subagents with the `task` tool. Each packet MUST be self-contained — the
subagent starts cold and inherits nothing but this prompt. Include:
- the skills it should load (bare skill names; it calls the `skill` tool),
- target/context, constraints, and the exact deliverable + success signal,
- any behavioral mode you want (it does NOT inherit yours).
Dispatch independent workers in parallel (multiple task calls in one turn);
aggregate before the next wave.

## Anti-loop guard
- Cap dispatches per turn; when reached, synthesize and report.
- If the same objective returns to the same worker with no new info, stop.
- Subagents must not dispatch (enforced by their task: deny).

## Delegation discipline
- One task = one bounded question + one deliverable. If you can't state the success
  signal in a sentence, decompose first.
- Match worker weight to difficulty: trivial/bulk/token-heavy work to the lightest
  capable (cheap) worker; reserve strong workers for genuinely hard sub-problems.
- Keep planning, hypothesis selection, and scope yourself. After each return, judge
  done/partial/blocked and accept, re-scope, or close it — never silently drop it.
- Prefer direct read-only local work for cheap deterministic steps; dispatch only
  when depth or parallelism genuinely helps.

## Routing table
<keyword/domain → which subagent>
```

## Subagent prompt skeleton

```markdown
---
description: >-
  Hidden subagent dispatched by <supervisor-name> for <bounded domain>.
  Do not invoke directly; the supervisor routes <domain> tasks here.
mode: subagent
hidden: true
model: provider/capable-model
reasoningEffort: high
permission:
  task: deny
---
You are the <Domain> Operator, dispatched exclusively by <supervisor-name>; you
must not spawn further subagents.

## Skills loaded
When dispatched, load these via the `skill` tool (the supervisor names them in the
packet): <skill-a>, <skill-b>.

## Mission
<what to do, in this domain, with what evidence standard>.

## Operating principles
<ordered, domain-specific discipline>.

## Evidence requirements
<exact artifacts to return>.

## Adaptive skill loading
The injected skills are a baseline, not a ceiling. Load the narrowest matching
skill when the concrete task needs a capability not yet covered. Loading a skill
never expands authorization or scope.
```

## Utility (cheap) subagent skeleton

```markdown
---
description: >-
  Hidden utility subagent for non-specialized, token-heavy work (summarize,
  parse, public lookup, boilerplate). Runs on a free/cheap model. Do not invoke directly.
mode: subagent
hidden: true
model: provider/cheap-or-free-model
temperature: 0.2
permission:
  task: deny
  edit: deny
  bash: deny
---
You are a utility subagent for non-specialized tasks. Keep to the dispatched task;
do not expand scope. If a task needs specialist judgement, report back for re-routing.
```

## Wave parallelism

For multi-domain objectives, dispatch in waves of independent workers, aggregate, then advance:

| Wave | Workers |
|---|---|
| A — discovery | passive/intel workers in parallel |
| B — analysis | active/analysis workers in parallel |
| C — specialist | narrow specialists as needed |

Budget a small cap per wave; for focused single-domain tasks, dispatch one worker directly and skip waves.

## The cold-context rule (most common failure)

A subagent sees **only** the dispatch prompt. It does **not** inherit:
- the conversation history or files the supervisor read,
- skills the supervisor loaded,
- an active behavioral mode the user enabled (e.g. a `/mode`),
- prior worker outputs (unless you put them in the packet).

If the worker needs a path, an error string, a decision, a skill name, or a mode — write it into the packet. Under-specified packets cause expensive rediscovery turns; that is almost always the real cause of a vague or empty worker return. Fix the packet and re-dispatch a *smaller* slice.

## Reference implementations

- The OpenCode `task` tool resolves the model from `Agent.get(subagent_type)` — a pre-existing agent — confirming there is no per-dispatch model parameter.
- Community multi-agent setups (e.g. the Hermes orchestrator) demonstrate: a pure-dispatcher primary with read/write/bash disabled, per-subagent model pinning (cheap scouts vs. strong implementers), and `default_agent` to make the orchestrator the launch primary.
