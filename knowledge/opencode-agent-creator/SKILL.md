---
name: opencode-agent-creator
description: "Design, build, and tune OpenCode CLI agents and multi-agent teams. Use when asked to create an OpenCode agent, a subagent, an orchestrator/supervisor, a roster of specialists, a swarm/parallel fan-out, or an agent .md / opencode.json config. Covers agent modes (primary/subagent/all), the built-in agents (build, plan, general, explore, scout), the native Task tool for hierarchical delegation, permission.task dispatch whitelists, per-agent model/cost routing (and the no-per-task-model constraint plus the background-agents plugin workaround), the supervisor/swarm/mesh/template topologies and which are natively supported, custom tools, plugins, and secrets. Not for AGENTS.md instruction files (use agent-md-creator), generic Agent Skills (use skill-creator), or Claude Code subagents (use agents-claude-creator)."
license: MIT
compatibility: "OpenCode CLI (opencode.ai), current docs as of 2026-06. Agents are Markdown files under ~/.config/opencode/agents/ or .opencode/agents/, or JSON under the 'agent' key of opencode.json. Multi-agent delegation uses the native Task tool; async/background delegation is experimental natively (OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS) or via the opencode-background-agents plugin."
metadata:
  author: AeonDave
  version: "2.0"
---

# OpenCode Agent Creator

Build precise, functional, professional OpenCode agents and agent teams without re-researching the platform. The reference shape is **one visible primary "supervisor" that plans and delegates, dispatching a roster of model-tiered subagents through the native `task` tool**. This skill encodes the official OpenCode agent model plus field-tested orchestration, topology, and cost-routing patterns.

> Scope: this skill creates **OpenCode agents** (the runtime actors). For repo instruction files use `agent-md-creator`; for portable Agent Skills use `skill-creator`; for Claude Code subagents use `agents-claude-creator`. An OpenCode subagent often *loads* a Skill to get its methodology — the two compose via the `skill` tool.

## The one constraint that shapes every decision

**OpenCode fixes the model per agent.** The native `task` tool accepts only `description`, `prompt`, and `subagent_type` — there is **no `model` parameter**. A primary agent cannot pick a model per dispatch at runtime. Therefore:

- **Cost control = routing, not runtime selection.** Pre-create agents pinned to different models; the supervisor controls cost by choosing *which agent* to dispatch — a cheap model for trivial/bulk work, a strong model for hard reasoning, each a separate agent.
- "Create a team with the best/cheapest models" is a **config-time** act (writing `model:` into each agent), not something the supervisor does live.
- To get "cheap for easy, strong for hard" inside one domain, make **two agents** (e.g. `x-operator` and `x-operator-heavy`) and let the supervisor route between them.

Internalize this first — it is why the architecture looks the way it does.

## The cold-context contract (the other thing that shapes every prompt)

**A dispatched subagent starts cold.** It sees only the dispatch `prompt` — not the conversation, the files the primary read, the skills the primary loaded, or the active agent mode. Any skill name, target context, constraint, or behavioral instruction must be written **into the dispatch packet** or it does not cross. Design each subagent prompt as if briefing a brand-new contractor who can read the repo but was in none of your meetings.

## Workflow

### 1. Single agent, or a team — and which topology?

- **Single subagent** — one bounded specialty (a reviewer, a researcher). Write one `.md`; skip the orchestration sections.
- **Team** — multi-domain work, parallelism, or cost tiering. Default when the user says "agents" (plural), "team", "squad", "orchestrator", "swarm", or "sub-agents".

Pick the topology by what the work needs (full catalog + native-support status: [references/multi-agent-topologies.md](references/multi-agent-topologies.md)):

| Topology | Shape | OpenCode support |
|---|---|---|
| **Subagent** | one specialist invoked by a primary or `@mention` | native (`mode: subagent`) |
| **Supervisor / hierarchical** | one primary plans → dispatches specialists, synthesizes | **native, recommended** (`task` tool + `permission.task`) |
| **Swarm / parallel** | primary fans out many `task` calls at once (dependency-batched) | native; synchronous unless background (experimental/plugin) |
| **Mesh / peer-to-peer** | subagents call each other directly | **not reliably native** — emulate hub-and-spoke via the supervisor |
| **Template** | reusable agent scaffolds you instantiate per project | `opencode agent create` + the skeletons in [assets/](assets/) |

### 2. Don't recreate the built-ins

OpenCode ships agents — extend or route to them instead of cloning:
- **Primary:** `build` (all tools), `plan` (edits + bash gated to `ask`). (`compaction`, `title`, `summary` are hidden system primaries.)
- **Subagent:** `general` (full tools except todo; the docs' own answer to "run multiple units of work in parallel"), `explore` (fast read-only codebase search), `scout` (read-only external-docs/dependency research).

Create a custom agent only when a focused role, tool boundary, or pinned model beats the built-ins.

### 3. Choose where agents live, and scaffold

- **Markdown** (preferred for prompts): `~/.config/opencode/agents/<name>.md` (global) or `.opencode/agents/<name>.md` (project). **Filename = agent name** (no `name` field in frontmatter). Frontmatter + system-prompt body.
- **JSON**: the `agent` key in `opencode.json` (terse model/permission overrides).
- Both merge; Markdown is auto-discovered. Keep one source of truth per agent to avoid drift.
- Scaffold fast with **`opencode agent create`** (interactive) or non-interactively with `--path --description --mode --permissions --model`. List with `opencode agent list`.
- Make the visible primary the launch default with `"default_agent": "<supervisor-name>"` in `opencode.json` (must be a primary).

Full field reference: [references/agent-config-reference.md](references/agent-config-reference.md). Copy-ready skeletons: [assets/](assets/).

### 4. Design the roster (team case)

Separate by **independent decision boundary**, not convenience:

- **1 supervisor** — `mode: primary`, the only CLI-visible agent. Plans, gates scope, decomposes, dispatches, reviews evidence, synthesizes. Does **not** execute noisy/destructive work itself.
- **N specialist subagents** — `mode: subagent`, `hidden: true`. One bounded domain each, pinned to a capable model.
- **M utility subagents** — `mode: subagent`, `hidden: true`. Trivial/bulk/token-heavy work (summarize, parse, public lookup, boilerplate), pinned to cheap/free models.

Keep each subagent to **one bounded question with one deliverable**. If you cannot state its success signal in one sentence, split it. A scout-first habit (dispatch a read-only `explore`/`scout` to gather context before any write) keeps expensive agents cheap — see the OpenAgentsControl-derived discipline in [references/multi-agent-topologies.md](references/multi-agent-topologies.md).

### 5. Assign models by tier (cost routing)

| Tier | Agent(s) | Model class | Rationale |
|---|---|---|---|
| Brain | supervisor | strongest available, or leave `model` unset to inherit the user's `/models` pick | only agent worth premium tokens |
| Specialist | domain subagents | capable mid model with strong tool-calling | real reasoning + tool use |
| Utility | helper subagents | free/cheap models | bulk work at ~zero cost |

Model id is always `provider/model-id` (e.g. `github-copilot/gpt-5.4`, `opencode/big-pickle`). Leaving a subagent's `model` unset makes it **inherit the primary that invoked it** — the native "fallback" and the single dial for the whole team. The Zen catalog, free tier, inheritance-as-fallback, the per-call-model plugin workaround, and the free-model privacy caveat are in [references/model-tiering.md](references/model-tiering.md).

### 6. Wire permissions and the no-cascade guard

- **Supervisor** — whitelist only its roster so unrelated agents vanish from its Task tool (last matching rule wins; put `*` first):
  ```yaml
  permission:
    task:
      "*": deny
      "specialist-*": allow
      "utility-*": allow
  ```
  If it should dispatch-and-inspect but never execute, add `edit: deny` and `bash: deny` (it keeps read/grep/glob/list to review results).
- **Every subagent** — `permission: { task: deny }`. OpenCode has **no recursion depth guard** (issue #18100), and subagent peer-delegation is unreliable anyway (issue #7296). Keep delegation strictly hierarchical: only the supervisor dispatches. Without `task: deny`, a subagent can spawn subagents and create runaway sessions.

### 7. Write the prompts

- **Supervisor body**: authorization/scope gate → roster table → dispatch protocol → anti-loop + delegation discipline → routing table. The single most important rule: **subagents start cold** and inherit nothing but the dispatch prompt. Any skill name, behavioral mode, target context, or constraint must be written **into the packet** or it does not cross.
- **Subagent body**: role + which Skills it loads + mission + operating principles + evidence requirements + a tight output contract. Skill names are bare (no paths); the subagent loads them via the `skill` tool.

The body shape, dispatch protocol, anti-loop/delegation rules, and parallel-batch discipline: [references/orchestrator-pattern.md](references/orchestrator-pattern.md). Two prompt styles work — a lean imperative body (Claude-style) or the XML-structured `<role>/<task>/<workflow>` body OpenAgentsControl uses; pick by team convention, both are covered. Ready-to-adapt skeletons: [assets/](assets/).

### 8. Add tools and plugins (optional, high-leverage)

- **Custom tools** (`~/.config/opencode/tools/*.ts`): TypeScript functions the agent calls like built-ins; can shell out to Python. Best for deterministic wrappers (recursive web research, output parsers, redaction) that beat an LLM on cost and reliability.
- **Plugins** (`plugin` array or `~/.config/opencode/plugins/`): npm or local; hook lifecycle events. High-value: `opencode-background-agents` (async read-only delegation that survives compaction), context pruning, persistent memory.

APIs, the ecosystem plugin shortlist, experimental flags, and a worked `deep-research` tool: [references/plugins-and-tools.md](references/plugins-and-tools.md).

### 9. Handle secrets correctly

Never hardcode keys/tokens in `opencode.json` — use `{env:VAR}` or `{file:~/.secrets/x}`. OpenCode does **not** auto-load `.env`, and `{env:}` resolves at startup before plugins, so the variable must already exist in the environment. On Windows, a small launcher that loads a `.env` into the process then runs `opencode` is the reliable path — see [references/plugins-and-tools.md](references/plugins-and-tools.md).

### 10. Validate and test

- Each agent's frontmatter is valid YAML between `---`; `name`/filename match; model ids are real (`opencode models`). `opencode.json` parses if used.
- Restart OpenCode after edits so frontmatter is re-read.
- Smoke-test: `@mention` a subagent directly (behavior), and give the supervisor a task that should fan out (routing). Verify it dispatches (not executes), respects the task whitelist, and that hidden agents stay out of the `@` menu. Full method: [references/triggering-and-testing.md](references/triggering-and-testing.md).

## Anti-patterns

- **Hardcoding a per-task model in the supervisor prompt** — impossible natively; route to a pre-created pinned agent.
- **Forgetting `task: deny` on subagents** — invites recursive fan-out (no native depth guard).
- **Building a true mesh** (subagents calling each other) — unreliable on OpenCode; emulate hub-and-spoke through the supervisor.
- **Assuming active skills/modes propagate to subagents** — they don't (cold context); inject into the packet.
- **Recreating `build`/`plan`/`general`/`explore`/`scout`** — extend or route to the built-ins.
- **Specializing portable Skills on OpenCode internals** — keep model-tiering/Task-tool details in the agent files, not in reusable Skills.
- **Over-tiering** — don't split into cheap/strong variants unless the cost delta is real; one well-chosen model is simpler.
- **Secrets in config** — always `{env:}`/`{file:}`.

## Resources

- [references/agent-config-reference.md](references/agent-config-reference.md) — complete frontmatter + `opencode.json` field reference: `mode`, `model`, `hidden`, `temperature`, `top_p`, `steps`, `reasoningEffort`, `color`, `disable`, the full `permission.*` key list and `permission.task` globs, `tools` (legacy), `default_agent`, model variants, the built-in agents, `opencode agent create`/`list` CLI, and session navigation. Load when writing or debugging agent config.
- [references/multi-agent-topologies.md](references/multi-agent-topologies.md) — the topology catalog (subagent, supervisor/hierarchical, swarm/parallel, mesh, template), each with when-to-use, OpenCode native-support status, a config sketch, and the OpenAgentsControl-derived discipline (scout-first context, dependency-batched parallelism, context-level allocation, stage gating). Load when choosing or composing a team shape.
- [references/orchestrator-pattern.md](references/orchestrator-pattern.md) — supervisor + subagent architecture on the **native `task` tool**: adaptable prompt skeletons (lean and XML-structured), dispatch protocol, wave parallelism, anti-loop guard, delegation discipline, cold-context packet rules. Load when building a team.
- [references/model-tiering.md](references/model-tiering.md) — the per-agent-fixed-model constraint, the Zen catalog and free tier, cost-routing tiers, inheritance-as-fallback, the dynamic-model-selection roadmap, and the free-model privacy caveat. Load when assigning models or controlling cost.
- [references/plugins-and-tools.md](references/plugins-and-tools.md) — custom tools API (TypeScript, Zod args, context), plugin hooks/events, the ecosystem plugin shortlist (`opencode-background-agents`, workspace, skillful, supermemory), experimental flags, a worked `deep-research` custom tool, and the secrets/`.env` handling pattern. Load when extending agents with tools, plugins, or env-based secrets.
- [references/triggering-and-testing.md](references/triggering-and-testing.md) — does the supervisor route to the right subagent, and does each agent stay in its permission boundary and honor its output contract? Triggering, behavior, and adversarial checks. Load before finalizing.
- [assets/agent-template.md](assets/agent-template.md), [assets/supervisor-template.md](assets/supervisor-template.md) — fill-in skeletons for a subagent and a primary supervisor. [assets/examples/](assets/examples/) — ready-to-adapt agents: `supervisor.md`, `code-reviewer.md` (read-only), `researcher.md` (scout-style), `summarizer.md` (cheap utility). Read for concrete patterns.
