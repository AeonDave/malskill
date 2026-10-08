# Agent configuration

Baseline: stable v1.18.35. Use the [released agent schema](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/core/src/v1/config/agent.ts) and [runtime defaults](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/opencode/src/agent/agent.ts) when website examples differ from the installed release.

## Discovery and identity

- Project Markdown: `.opencode/agents/<name>.md`; global Markdown: the OpenCode config directory's `agents/` folder, normally `~/.config/opencode/agents/`.
- JSON/JSONC: `agent.<name>` in `opencode.json` or `opencode.jsonc`.
- The released loader accepts `agent/` and `agents/`, including nested Markdown files. `agents/team/review.md` derives the name `team/review`. Agent lookup is case-sensitive; use the exact discovered name in Task calls and permission patterns.
- Omit a Markdown `name` override so file identity stays predictable. The body becomes `prompt`; frontmatter supplies configuration.
- JSON and Markdown settings merge. Avoid splitting one role across several definitions unless the overrides are intentional. Check the resolved list after changes.

Sources: [Markdown loader](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/opencode/src/config/agent.ts), [entry naming](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/opencode/src/config/entry-name.ts), [config loader](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/opencode/src/config/config.ts).

## Agent fields

| Field | Use |
|---|---|
| `description` | Routing text; include it for custom agents even though the released schema accepts omission. |
| `mode` | `primary`, `subagent`, or `all`; custom agents default to `all`. Set it explicitly. |
| `model` | `provider/model-id`; omit to inherit. Verify the identifier with `opencode models`. |
| `variant` | Default variant when the agent uses its own configured model. Verify provider support. |
| `hidden` | Removes a subagent from `@` autocomplete; does not prevent explicit invocation. |
| `temperature`, `top_p` | Finite numbers; use only values and controls supported by the chosen provider/model. |
| `steps` | Positive integer limiting agentic iterations before text-only completion. Prefer it over deprecated `maxSteps`. |
| `color` | `#RRGGBB` or `primary`, `secondary`, `accent`, `success`, `warning`, `error`, `info`. |
| `disable` | Removes the configured agent. |
| `prompt` | Inline JSON prompt or `{file:./prompts/review.txt}`; Markdown uses its body. |
| `permission` | Capability rules described below. Prefer it over deprecated `tools`. |
| `options` / extra fields | Provider options; unknown fields are forwarded as options, so misspelled configuration keys may parse without doing the intended thing. |

## Permissions

Actions are `allow`, `ask`, or `deny`. Agent rules override defaults/global agent configuration; last matching rule wins. Put broad patterns first and specific exceptions later. Custom/MCP tool names can also be permission keys.

| Permission shape | Keys |
|---|---|
| Action or pattern-to-action map | `read`, `edit`, `glob`, `grep`, `list`, `bash`, `task`, `external_directory`, `lsp`, `skill` |
| Action only | `todowrite`, `question`, `webfetch`, `websearch`, `doom_loop` |

`edit` gates built-in file mutations, including write/edit/apply-patch operations. It does not disable arbitrary shell commands or custom/MCP tools that mutate files. For a strict read-only role, deny `bash` and unreviewed tools as well; use the deny-all allowlist in the assets. Command patterns are an access policy, not a shell sandbox.

```yaml
permission:
  task:
    "*": deny
    "team-*": allow
    "reviewer": ask
```

Task-denied agents are filtered from its advertised roster. Explicit user `@` invocation follows a separate path; neither this roster filter nor `hidden` is a security boundary against user invocation.

Parent **agent** restrictions apply to the parent, not automatically to workers. Task derives child session permissions from parent **session** deny/external-directory rules, then uses the worker's own agent permissions. A supervisor's `edit: deny` therefore does not make its workers read-only.

Sources: [permission schema](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/core/src/v1/config/permission.ts), [permission documentation](https://opencode.ai/docs/permissions/), [child-session rules](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/opencode/src/agent/subagent-permissions.ts), [Task roster filtering](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/opencode/src/tool/registry.ts).

## Primary selection and nesting

```json
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "supervisor",
  "subagent_depth": 1
}
```

`default_agent` must name an existing visible agent whose mode is not `subagent`; `primary` and `all` qualify. The released runtime errors on an unknown, hidden, or subagent default. It does not silently fall back to Build for these invalid values.

`subagent_depth` is a nonnegative integer, default `1`: the root can dispatch a child, but that child cannot dispatch a grandchild. `0` disables Task delegation at the root. Intentional nested delegation requires a larger limit and the caller worker's explicit `permission.task` rules. Keep leaf workers at `task: deny`; do not infer nested support from an old issue report.

Sources: [config field](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/core/src/v1/config/config.ts), [default resolution](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/opencode/src/agent/agent.ts), [Task depth check](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/opencode/src/tool/task.ts).

## Released built-ins

The stable runtime defines `build`, `plan`, `general`, `explore`, and hidden `compaction`, `title`, `summary`. Config/plugins may add others; confirm them with `opencode agent list` before routing to them.

Do not treat Build or Explore as a strict read-only sandbox. Build follows configured permissions; Explore's released defaults permit Bash. Plan denies ordinary edits while permitting plan-file edits, and its Bash policy comes from defaults/config. Use an explicit custom permission boundary when a task requires stronger restrictions. The website's Scout/default-policy descriptions are not a substitute for the released roster.

## Scaffold commands

```bash
opencode agent list
opencode agent create \
  --path .opencode \
  --description "Reviews named files without editing" \
  --mode subagent \
  --permissions read,glob,grep,skill
```

- `--path` is the configuration root; the released command appends `agents/`. Passing `.opencode/agents` produces `.opencode/agents/agents`.
- All four shown options suppress interactive prompts, but creation still calls a model to generate the identifier and prompt. Copy an asset for a deterministic/offline scaffold.
- `--model` selects the **generator's** model. This release does not persist it into generated agent frontmatter; add the desired runtime `model` afterward.
- `--permissions` (alias `--tools`) denies omitted keys from the command's known list: `bash,read,edit,glob,grep,webfetch,task,todowrite,websearch,lsp,skill`. It is not a deny-all policy for other tools. An empty value selects that full list, not zero permissions.

Source: [released CLI command](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/opencode/src/cli/cmd/agent.ts).

## Configuration secrets

Use `{env:VAR}` or `{file:./private/key}` in JSON config instead of literal secrets. Export required variables before launch; substitution occurs while loading configuration. Verify missing values and the launcher/runtime's `.env` behavior rather than assuming a plugin can supply values after resolution. Relative file references resolve from the config directory.

Source: [configuration variables](https://opencode.ai/docs/config/#variables).
