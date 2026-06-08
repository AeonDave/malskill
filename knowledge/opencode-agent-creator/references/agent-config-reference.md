# OpenCode Agent Config Reference

Complete field reference for OpenCode agents. Agents are defined either as Markdown files (frontmatter + body) or as JSON under the `agent` key of `opencode.json`. Both are merged; identical settings in JSON and frontmatter should be kept consistent.

## Locations

- Global Markdown: `~/.config/opencode/agents/<name>.md` (the filename is the agent name).
- Project Markdown: `.opencode/agents/<name>.md`.
- JSON: `opencode.json` → `"agent": { "<name>": { ... } }`.
- Singular `agent/` directory is also accepted for backwards compatibility; prefer plural `agents/`.

## Markdown agent skeleton

```markdown
---
description: One paragraph — what it does and when to use it (required).
mode: subagent              # primary | subagent | all
model: provider/model-id    # optional; omit to inherit
hidden: true                # subagent-only; hide from @-menu
temperature: 0.2            # optional
reasoningEffort: high       # provider-specific passthrough (e.g. OpenAI/GPT)
permission:
  task: deny                # subagents: block re-dispatch
  edit: deny                # optional
  bash: deny                # optional
---
You are <role>. <system prompt body>.
```

The Markdown file name becomes the agent name; there is no `name` field in frontmatter.

## Field reference

| Field | Values | Notes |
|---|---|---|
| `description` | string (required) | Routing signal. For subagents it becomes the Task-tool entry the supervisor reads — make it assertive and specific so auto-routing works. |
| `mode` | `primary` \| `subagent` \| `all` | `primary` = Tab-selectable, handles main conversation. `subagent` = invoked via Task tool or `@mention`. Default `all`. |
| `model` | `provider/model-id` | If omitted: primary uses the globally configured/selected model; a subagent inherits the model of the primary that invoked it. Pin it to control cost. |
| `hidden` | `true` \| `false` | Subagent-only. `true` removes it from the `@` autocomplete; still invokable by the model via Task. Users can always `@mention` it regardless. |
| `temperature` | 0.0–1.0 | Lower = deterministic. Omit for model default. |
| `top_p` | 0.0–1.0 | Alternative to temperature. |
| `steps` | integer | Max agentic iterations before forced text-only response (cost cap). Legacy name `maxSteps` is deprecated. |
| `prompt` | `"{file:./prompts/x.txt}"` or inline (JSON) | In Markdown the body *is* the prompt; in JSON use `prompt`. |
| `color` | hex or theme name | UI accent for the agent. |
| `disable` | `true` | Turns the agent off. |
| `reasoningEffort`, `textVerbosity`, … | provider-specific | Any extra key is passed through to the provider as a model option. |

## Permissions

`permission` controls what the agent may do. Keys accept a shorthand action (`allow` \| `ask` \| `deny`) and some accept a `{ pattern: action }` object.

| Key | Governs |
|---|---|
| `read`, `edit`, `glob`, `grep`, `list`, `bash`, `lsp`, `skill` | The matching tools. `edit` covers write/edit/apply_patch. Accept shorthand or pattern→action. |
| `task` | Which subagents this agent may invoke via the Task tool. |
| `webfetch`, `websearch`, `todowrite`, `external_directory`, `question`, `doom_loop` | Shorthand action only. |

### `permission.task` — the dispatch whitelist

Globs matched against subagent names; **last matching rule wins**, so put `*` first:

```json
{ "agent": { "supervisor": { "mode": "primary",
  "permission": { "task": { "*": "deny", "team-*": "allow", "reviewer": "ask" } } } } }
```

`deny` removes the subagent from the Task tool description entirely (the model won't try to call it). Set `task: deny` on every subagent to prevent recursive fan-out (OpenCode has no max-depth guard).

### bash command patterns

```yaml
permission:
  bash:
    "*": ask
    "git status *": allow
    "rm -rf *": deny
```

## `tools` (deprecated)

The old `tools: { write: false, bash: false }` map still works (`true`≈allow, `false`≈deny, wildcards like `"mymcp_*": false` supported) but prefer `permission` for new configs.

## `opencode.json` essentials

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "supervisor",      // auto-select this primary on launch (must be a primary)
  "model": "provider/model-id",       // global default model
  "small_model": "provider/cheap",    // lightweight tasks (e.g. title generation)
  "agent": {
    "supervisor": { "mode": "primary", "permission": { "task": { "*": "deny", "team-*": "allow" } } },
    "team-x":     { "mode": "subagent", "model": "provider/strong", "permission": { "task": "deny" } }
  }
}
```

## Variable substitution (config only)

- `{env:VAR}` — substitutes an environment variable (empty string if unset). Resolved at startup.
- `{file:~/.secrets/key}` — substitutes file contents (relative to config dir, or absolute `/`/`~`).

Use these for API keys and tokens; never hardcode secrets in the config.

## Model variants

Some providers expose variants (e.g. Anthropic `high`/`max`; OpenAI `minimal`/`low`/`medium`/`high`/`xhigh`). Select with `provider/model-id` plus the variant the provider documents, or define custom variants under `provider.<id>.models.<model>.variants`.

## Gotchas

- Subagents start with a **fresh, isolated context** — they see only the dispatch prompt, not the conversation, files, or skills the primary loaded.
- Changing frontmatter requires an OpenCode restart to take effect.
- A documentation/registry JSON you keep beside the agents is **not** read by OpenCode unless it is the actual `opencode.json`; keep it in sync manually or treat it as notes only.
