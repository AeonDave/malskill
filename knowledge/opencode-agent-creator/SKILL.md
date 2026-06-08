---
name: opencode-agent-creator
description: "Design, build, and tune OpenCode CLI agents and multi-agent teams: a single visible supervisor (primary) that dispatches hidden, model-tiered subagents via the Task tool. Use when asked to create an OpenCode agent, an orchestrator/supervisor, a roster of subagents, agent .md frontmatter, opencode.json agent config, per-agent model/cost routing, permissions and task whitelists, custom tools, or plugins. Covers the constraint that OpenCode fixes the model per agent (no per-task model selection) and how to do cost control by routing instead. Not for AGENTS.md instruction files (use agent-md-creator) or generic Agent Skills (use skill-creator)."
license: MIT
compatibility: "OpenCode CLI (opencode.ai). Agents are Markdown files under ~/.config/opencode/agents/ or .opencode/agents/, or JSON under the 'agent' key of opencode.json."
metadata:
  author: AeonDave
  version: "1.0"
---

# OpenCode Agent Creator

Build precise, functional, professional OpenCode agents and agent teams without re-researching the platform. The reference pattern is **one visible primary "supervisor" that plans and delegates, dispatching a roster of hidden, model-tiered subagents through the Task tool**. This skill encodes the official OpenCode agent model plus field-tested orchestration and cost-routing patterns.

> Scope: this skill creates **OpenCode agents** (the runtime actors). For repo instruction files use `agent-md-creator`; for portable Agent Skills use `skill-creator`. An OpenCode subagent often *loads* a Skill to get its methodology — the two compose.

## The one constraint that shapes every decision

**OpenCode fixes the model per agent.** The `task` tool accepts only `description`, `prompt`, and `subagent_type` — there is **no `model` parameter**. A primary agent cannot pick a model per dispatch at runtime (it is an open feature request, not shipped). Therefore:

- **Cost control = routing, not runtime selection.** Pre-create agents pinned to different models; the supervisor controls cost by choosing *which agent* to dispatch — a cheap model for trivial/bulk work, a strong model for hard reasoning, each a separate agent.
- "Create a team with the best/cheapest models" is a **config-time** act (writing `model:` into each agent), not something the supervisor does live.
- To get "cheap for easy, strong for hard" inside one domain, make **two agents** (e.g. `x-operator` and `x-operator-heavy`) and let the supervisor route between them.

Internalize this first — it is why the architecture looks the way it does.

## Workflow

### 1. Decide: single agent or a team?

- **Single subagent** — one bounded specialty (a reviewer, a researcher). Write one `.md`; skip the orchestration sections.
- **Team (supervisor + subagents)** — multi-domain work, parallelism, or cost tiering. Use the full pattern. This is the default when the user says "agents" (plural), "team", "squad", "orchestrator", or "sub-agents".

### 2. Choose where agents live

- **Markdown** (preferred for prompts): `~/.config/opencode/agents/<name>.md` (global) or `.opencode/agents/<name>.md` (project). Filename = agent name. Frontmatter + system-prompt body.
- **JSON**: the `agent` key in `opencode.json` (terse model/permission overrides).
- Both merge; Markdown is auto-discovered. Keep one source of truth per agent to avoid drift.
- Make the visible primary the launch default with `"default_agent": "<supervisor-name>"` in `opencode.json`.

Full field reference: [references/agent-config-reference.md](references/agent-config-reference.md).

### 3. Design the roster (team case)

Separate by **independent decision boundary**, not convenience:

- **1 supervisor** — `mode: primary`, the only CLI-visible agent. Plans, gates scope, decomposes, dispatches, reviews evidence, synthesizes. Does **not** execute noisy/destructive work itself.
- **N specialist subagents** — `mode: subagent`, `hidden: true`. One bounded domain each, pinned to a capable model.
- **M utility subagents** — `mode: subagent`, `hidden: true`. Trivial/bulk/token-heavy work (summarize, parse, public lookup, boilerplate), pinned to cheap/free models.

Keep each subagent to **one bounded question with one deliverable**. If you cannot state its success signal in one sentence, split it.

### 4. Assign models by tier (cost routing)

| Tier | Agent(s) | Model class | Rationale |
|---|---|---|---|
| Brain | supervisor | strongest available, or leave `model` unset to inherit the user's `/models` pick | only agent worth premium tokens |
| Specialist | domain subagents | capable mid model with strong tool-calling | real reasoning + tool use |
| Utility | helper subagents | free/cheap models | bulk work at ~zero cost |

Model id is always `provider/model-id` (e.g. `github-copilot/gpt-5.4`, `opencode/big-pickle`). Leaving the supervisor's `model` unset makes it inherit whatever strong model the user selects with `/models`. **Robustness option:** you can also leave the *specialists'* `model` unset so they inherit the supervisor too — one always-working dial, since OpenCode has no native model-fallback list and a metered pinned model can run out and silently fail dispatches. The Zen catalog, free tier, cheap zero-retention fallbacks, the inheritance-as-fallback pattern, and the privacy caveat (free models may log/train on data — never route sensitive engagement data to them) are in [references/model-tiering.md](references/model-tiering.md).

### 5. Wire permissions and the no-cascade guard

- **Supervisor** — whitelist only its roster so unrelated agents vanish from its Task tool:
  ```yaml
  permission:
    task:
      "*": deny
      "specialist-*": allow
      "utility-*": allow
  ```
  If it should dispatch-and-inspect but never execute, add `edit: deny` and `bash: deny` (it keeps read/grep/glob/list to review results).
- **Every subagent** — `permission: { task: deny }`. Only the supervisor holds dispatch authority. Without this, subagents can recursively spawn subagents (OpenCode has no depth guard), wasting tokens and creating runaway sessions.

### 6. Write the prompts

- **Supervisor body**: authorization/scope gate → roster table → dispatch protocol → anti-loop + delegation discipline → routing table. The single most important rule: **subagents start cold** and inherit nothing but the dispatch prompt. Any skill name, behavioral mode, target context, or constraint must be written **into the packet** or it does not cross.
- **Subagent body**: role + which Skills it loads + mission + operating principles + evidence requirements + adaptive skill loading. Skill names are bare (no paths); the subagent loads them via the `skill` tool.

Ready-to-adapt prompt skeletons, the dispatch protocol, and the anti-loop/delegation rules: [references/orchestrator-pattern.md](references/orchestrator-pattern.md).

### 7. Add tools and plugins (optional, high-leverage)

- **Custom tools** (`~/.config/opencode/tools/*.ts`): TypeScript functions the agent calls like built-ins; can shell out to Python. Best for deterministic wrappers (recursive web research, output parsers) that beat an LLM on cost and reliability.
- **Plugins** (`plugin` array or `~/.config/opencode/plugins/`): npm or local; hook lifecycle events. Useful ones: context pruning (token savings), persistent memory.
- APIs plus a worked `deep-research` tool: [references/plugins-and-tools.md](references/plugins-and-tools.md).

### 8. Handle secrets correctly

Never hardcode keys/tokens in `opencode.json` — use `{env:VAR}` or `{file:~/.secrets/x}`. OpenCode does **not** auto-load `.env`, and `{env:}` resolves at startup before plugins, so the variable must already exist in the environment. On Windows, a small launcher that loads a `.env` into the process then runs `opencode` is the reliable path — see [references/plugins-and-tools.md](references/plugins-and-tools.md).

### 9. Validate and test

- Each agent's frontmatter is valid YAML between `---`; `name`/filename match; model ids are real (`opencode models`).
- `opencode.json` parses if used.
- Restart OpenCode after edits so frontmatter is re-read.
- Smoke-test: `@mention` a subagent directly, and give the supervisor a task that should fan out. Verify it dispatches (not executes), respects the task whitelist, and that hidden agents stay out of the `@` menu.

## Anti-patterns

- **Hardcoding a per-task model in the supervisor prompt** — impossible; route to a pinned agent instead.
- **Forgetting `task: deny` on subagents** — invites recursive fan-out.
- **Assuming active skills/modes propagate to subagents** — they don't (cold context); inject into the packet.
- **Specializing portable Skills on OpenCode internals** — keep model-tiering/Task-tool details in the agent files, not in reusable Skills.
- **Over-tiering** — don't split into cheap/strong variants unless the cost delta is real; one well-chosen model is simpler.
- **Secrets in config** — always `{env:}`/`{file:}`.

## Resources

- [references/agent-config-reference.md](references/agent-config-reference.md) — complete frontmatter + `opencode.json` field reference: `mode`, `model`, `hidden`, `temperature`, `reasoningEffort`, `permission.*`, `permission.task` globs, `tools` (deprecated), `default_agent`, model variants. Load when writing or debugging agent config.
- [references/orchestrator-pattern.md](references/orchestrator-pattern.md) — supervisor + hidden-subagent architecture: adaptable prompt skeletons, dispatch protocol, wave parallelism, anti-loop guard, delegation discipline, cold-context packet rules. Load when building a team.
- [references/model-tiering.md](references/model-tiering.md) — the per-agent-fixed-model constraint, OpenCode Zen catalog and free tier, cost-routing tiers, zero-retention fallbacks, the dynamic-model-selection roadmap (issue #6651), and the free-model privacy caveat. Load when assigning models or controlling cost.
- [references/plugins-and-tools.md](references/plugins-and-tools.md) — custom tools API (TypeScript, Zod args, context), plugin hooks/events, a worked `deep-research` custom tool, and the secrets/`.env` handling pattern. Load when extending agents with tools, plugins, or env-based secrets.
