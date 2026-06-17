# Multi-Agent Topologies on OpenCode

Which team shapes OpenCode actually supports, and how to build each. Read this to pick a topology; read [orchestrator-pattern.md](orchestrator-pattern.md) for the supervisor prompt mechanics and [agent-config-reference.md](agent-config-reference.md) for fields.

The honest summary: **OpenCode is built for hierarchical delegation** (a primary dispatches subagents via the `task` tool). Everything else is a composition of, or a constrained variation on, that one primitive. Don't fight the platform — emulate exotic topologies through the supervisor.

## Contents
- [At a glance](#at-a-glance)
- [1. Subagent (the atom)](#1-subagent-the-atom)
- [2. Supervisor / hierarchical](#2-supervisor--hierarchical)
- [3. Swarm / parallel fan-out](#3-swarm--parallel-fan-out)
- [4. Mesh / peer-to-peer](#4-mesh--peer-to-peer)
- [5. Template (reusable scaffolds)](#5-template-reusable-scaffolds)
- [Cross-cutting discipline (from OpenAgentsControl)](#cross-cutting-discipline-from-openagentscontrol)

## At a glance

| Topology | One-line | OpenCode support | Build with |
|---|---|---|---|
| Subagent | one isolated specialist | **native** | `mode: subagent` |
| Supervisor / hierarchical | primary plans → dispatches → synthesizes | **native, recommended** | primary + `task` + `permission.task` |
| Swarm / parallel | many specialists run at once, dependency-batched | **native** (sync) / experimental or plugin (async) | multiple `task()` calls per turn |
| Mesh / peer-to-peer | subagents call each other | **not reliably native** | emulate via supervisor (hub-and-spoke) |
| Template | reusable agent scaffolds | tooling | `opencode agent create` + [assets/](../assets/) |

## 1. Subagent (the atom)

The unit every team is made of: one `mode: subagent` agent with a sharp `description`, a least-privilege `permission` set, an optional pinned `model`, and a tight output contract. Invoked by a primary via `task`, or by a user via `@mention`.

When a single subagent is the whole answer:
- A focused reviewer, researcher, summarizer, or test-runner you keep re-invoking.
- You want a permission boundary (read-only) or a cheap model on a repeated chore.

Set `permission: { task: deny }` even on a standalone subagent — it should never spawn others.

## 2. Supervisor / hierarchical

**The default for any team.** One `mode: primary` supervisor is the only visible agent; it plans, decomposes, dispatches `hidden: true` subagents through the `task` tool, reviews their evidence, and synthesizes. This is the manager-worker pattern and the shape OpenCode documents for orchestration.

```jsonc
{ "agent": {
  "supervisor": { "mode": "primary",
    "permission": { "task": { "*": "deny", "team-*": "allow", "util-*": "allow" } } },
  "team-review":  { "mode": "subagent", "hidden": true, "model": "anthropic/claude-sonnet-4-6",
                    "permission": { "task": "deny" } },
  "util-summarize": { "mode": "subagent", "hidden": true, "model": "opencode/big-pickle",
                    "permission": { "task": "deny", "edit": "deny" } }
}}
```

Use when: multi-domain work, you want cost tiering, or you want verbose work isolated from the main context. Prompt skeletons + dispatch protocol: [orchestrator-pattern.md](orchestrator-pattern.md).

**Stage-gated variant.** For high-stakes pipelines, give the supervisor explicit stages with validation gates (architecture → tasks → execute → integrate), refusing to advance until a stage's outputs validate. This is the OpenAgentsControl `StageOrchestrator` model — strict sequential stages, rollback on failure. Worth the extra prompt weight only when a wrong early step is expensive to unwind.

## 3. Swarm / parallel fan-out

A supervisor dispatching **many subagents at once** for throughput. Natively, the supervisor emits **multiple `task()` calls in a single turn** and OpenCode runs them concurrently, returning all results (the built-in `general` subagent exists precisely to "run multiple units of work in parallel").

Make it disciplined, not chaotic — use **wave parallelism** (group independent subtasks into a wave, barrier between waves on dependencies). The full pattern with the batch/barrier diagram is in [orchestrator-pattern.md](orchestrator-pattern.md#wave-parallelism).

Caveats:
- Native fan-out is **synchronous** — the supervisor blocks until the wave returns. Fine for bounded waves.
- For **async** swarms (keep working while research runs), use `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS` (preview) or the `opencode-background-agents` plugin's `delegate` (read-only subagents only). See [plugins-and-tools.md](plugins-and-tools.md).
- Width still costs tokens linearly — fan out only what is genuinely independent, and push the bulk legs to cheap utility models.

## 4. Mesh / peer-to-peer

A topology where subagents call **each other** directly (worker A asks worker B mid-task). **OpenCode does not reliably support this**, and you should not design for it:

- Subagent-to-subagent task delegation is effectively blocked — the runtime has historically hardcoded `task` off for subagent sessions, so a peer-delegation `permission.task` whitelist on a subagent is ignored (issue #7296, open feature request).
- Where recursion *does* slip through, there is **no depth guard** — a subagent can spawn subagents without limit (issue #18100). That is a failure mode, not a feature.

**Do this instead — hub-and-spoke (emulated mesh):** route every cross-worker need through the supervisor. If `team-a` needs something from `team-b`, `team-a` returns "I need X from team-b" to the supervisor, which dispatches `team-b` and feeds the result into the next `team-a` packet. The supervisor is the message bus; workers stay leaves. You get peer collaboration semantics with a single, debuggable point of control and no runaway recursion.

If you truly need autonomous agent-to-agent messaging, that lives outside OpenCode's agent tree — in a plugin/harness (e.g. a workspace/background-agents harness) — not in subagent `task` permissions.

## 5. Template (reusable scaffolds)

"Template" here means **parameterized agent starting points** you instantiate per project, not a runtime topology. Two layers:

- **CLI scaffold:** `opencode agent create` generates a fresh agent file (interactive, or non-interactive with `--mode`/`--permissions`/`--model`). Good for one-offs.
- **Skeleton assets:** keep filled-in templates in version control and copy them. This skill ships [assets/agent-template.md](../assets/agent-template.md) (subagent), [assets/supervisor-template.md](../assets/supervisor-template.md) (primary), and concrete examples under [assets/examples/](../assets/examples/).

A "team template" is just a directory of these plus an `opencode.json` wiring the `permission.task` whitelist — drop it into `.opencode/` and a project has a working supervisor + roster. The OpenAgentsControl `system-builder` is this idea taken to its limit: an orchestrator that *generates* a whole `.opencode/` system (agents + context + commands) from a domain brief.

## Cross-cutting discipline (from OpenAgentsControl)

Patterns that make any topology above more reliable, distilled from the OpenAgentsControl roster:

- **Scout-first.** Before any write, dispatch a read-only `explore`/`scout` (or a ContextScout-style subagent) to gather project context and current external-library docs. Training data is stale for fast-moving libraries; a cheap read-only pass prevents expensive rework. Bake "discover before you build" into the supervisor's stage 1.
- **Context-level allocation.** Pass each subagent only what it needs: most dispatches need just the task spec (isolation); some need a filtered slice of the plan; almost none need the whole picture. Tighter packets = fewer tokens and sharper work.
- **Context bundle for big handoffs.** For multi-file features, write a `bundle.md` (objective, loaded standards, constraints, acceptance criteria) and pass its path in the packet, instead of inlining everything — the subagent reads it on start.
- **Dependency-batched parallelism.** Independent subtasks run together; dependent ones wait at a barrier. Never start a wave whose inputs aren't ready.
- **Validation gates.** Define a success signal per subtask and a pass/fail gate per stage. Don't advance on unverified output; re-dispatch with a tighter packet instead.
- **Evidence over assertion.** Require subagents to cite `file:line` / command output and to return failures rather than guess. The supervisor reviews evidence, not vibes.
