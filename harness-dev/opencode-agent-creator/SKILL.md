---
name: opencode-agent-creator
description: "Create, revise, or debug OpenCode agent definitions and teams: Markdown/JSON configuration, permissions, model routing, discovery, and native Task delegation."
license: MIT
compatibility: "OpenCode CLI. Guidance checked against stable v1.18.35; verify the target CLI and schema before using another generation."
metadata:
  author: AeonDave
  version: "2.1"
---

# OpenCode Agent Creator

Create the smallest agent definition or roster that handles the requested work. Prefer project-local `.opencode/agents/` unless another scope is requested. Preserve existing agent identities, permissions, and user decisions.

Use `agent-md-creator` for repository instructions, `skill-creator` for portable skills, and `claude-agents-creator` for Claude Code subagents. Use [opencode-plugin-creator](../opencode-plugin-creator/SKILL.md) for custom tool or plugin implementations.

## Workflow

1. Run `opencode --version`; inspect the existing project configuration and requested agent scope. These instructions target [stable v1.18.35](https://github.com/anomalyco/opencode/releases/tag/v1.18.35). For a different release or V2 target, verify its actual schema and runtime first.
2. Choose one bounded specialist, or a primary supervisor plus the needed specialists. Reuse an available built-in when it already fits. Load [multi-agent-topologies.md](references/multi-agent-topologies.md) when choosing a team shape.
3. Give each custom agent a concise routing description, explicit mode, task-specific prompt, and appropriate permissions. Keep one definition per agent. Load [agent-config-reference.md](references/agent-config-reference.md) when writing fields, resolving discovery, or configuring nested delegation.
4. Start from [agent-template.md](assets/agent-template.md) or [supervisor-template.md](assets/supervisor-template.md). The [examples](assets/examples/) form a read-only review team; add a real write-capable worker when implementation is required.
5. Leave `model` unset to inherit, or pin a model verified by `opencode models`. Load [model-tiering.md](references/model-tiering.md) when choosing model policies or investigating a failed dispatch. Task has no per-dispatch model parameter.
6. Give workers the target, constraints, relevant context, and expected result in each dispatch. A fresh child does not receive the parent's conversation; a resumed child retains its own history. Load [orchestrator-pattern.md](references/orchestrator-pattern.md) for packets, task resumption, and experimental background work.
7. Enforce capabilities with permissions. `hidden` controls autocomplete visibility, not access. Keep leaf workers at `task: deny`; configure depth and task permissions explicitly for intentional nested delegation. A read-only supervisor can dispatch a write-capable worker, so constrain each worker separately.
8. Reload the definitions and inspect `opencode agent list`. Test routing, the promised permission boundary, the returned result, and any resume/background behavior used. Load [triggering-and-testing.md](references/triggering-and-testing.md) before completion.

Report the files changed, target OpenCode version, checks actually run, and any untested model or delegation behavior. File/schema validation alone does not prove model routing or tool enforcement.

Load [plugins-and-tools.md](references/plugins-and-tools.md) when an agent needs a custom tool, plugin, or launch-time secret; it routes implementation work to the plugin skill.
