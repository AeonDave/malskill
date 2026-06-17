# OpenCode Agent Config Reference

Complete field reference for OpenCode agents. Agents are defined either as Markdown files (frontmatter + body) or as JSON under the `agent` key of `opencode.json`. Both are merged; keep identical settings consistent across the two.

## Contents
- [Locations](#locations)
- [Built-in agents](#built-in-agents)
- [Markdown agent skeleton](#markdown-agent-skeleton)
- [Field reference](#field-reference)
- [Permissions](#permissions)
- [`opencode.json` essentials](#opencodejson-essentials)
- [Variable substitution](#variable-substitution-config-only)
- [Model variants](#model-variants)
- [CLI: create / list / attach](#cli-create--list)
- [Session navigation (parent/child)](#session-navigation-parentchild)
- [Gotchas](#gotchas)

## Locations

- Global Markdown: `~/.config/opencode/agents/<name>.md` (the filename is the agent name).
- Project Markdown: `.opencode/agents/<name>.md`.
- JSON: `opencode.json` → `"agent": { "<name>": { ... } }`.
- Singular `agent/` directory is also accepted for backwards compatibility (the `opencode agent create --path` default still writes `.opencode/agent`); prefer plural `agents/`.

## Built-in agents

OpenCode ships these — extend or route to them rather than cloning. Names are case-insensitive in config.

| Agent | Mode | Role |
|---|---|---|
| `build` | primary | Default. All tools enabled — full file ops + system commands. |
| `plan` | primary | Analysis/planning. `edit` (writes/patches/edits) and `bash` default to `ask` — no unintended changes. |
| `general` | subagent | Full tool access **except** `todo`. For multi-step work and **running multiple units of work in parallel**. Can make file changes. |
| `explore` | subagent | Fast **read-only** codebase exploration: find files by pattern, search code, answer "where/how" questions. Cannot modify files. |
| `scout` | subagent | **Read-only** external-docs/dependency research: clones a dependency repo into OpenCode's managed cache, inspects library source, cross-references local vs upstream. May require `OPENCODE_EXPERIMENTAL_SCOUT`. |
| `compaction`, `title` | primary | Hidden system agents (context summarization, session titling). Not user-selectable; do not redefine. |

## Markdown agent skeleton

```markdown
---
description: One paragraph — what it does and when to use it (required).
mode: subagent              # primary | subagent | all
model: provider/model-id    # optional; omit to inherit
hidden: true                # subagent-only; hide from @-menu
temperature: 0.2            # optional
steps: 30                   # optional cost cap (max agentic iterations)
reasoningEffort: high       # provider-specific passthrough (e.g. OpenAI/GPT)
permission:
  task: deny                # subagents: block re-dispatch
  edit: deny                # optional
  bash: deny                # optional
---
You are <role>. <system prompt body>.
```

The Markdown file name becomes the agent name; there is **no `name` field** in frontmatter.

## Field reference

| Field | Values | Notes |
|---|---|---|
| `description` | string (required) | Routing signal. For subagents it becomes the Task-tool entry the supervisor reads — make it assertive and specific so auto-routing works. |
| `mode` | `primary` \| `subagent` \| `all` | `primary` = Tab-selectable, handles main conversation. `subagent` = invoked via Task tool or `@mention`. `all` (default) = usable as either. |
| `model` | `provider/model-id` | If omitted: a primary uses the globally configured/selected model; a subagent **inherits the model of the primary that invoked it**. Pin it to control cost. |
| `hidden` | `true` \| `false` | Subagent-only. `true` removes it from the `@` autocomplete; still invokable by the model via Task if permissions allow. Users can always `@mention` it regardless. |
| `temperature` | 0.0–1.0 | Lower = deterministic. Omit for model default. |
| `top_p` | 0.0–1.0 | Alternative to temperature. |
| `steps` | integer | Max agentic iterations before a forced text-only response (cost cap). Legacy name `maxSteps` is deprecated. |
| `prompt` | `"{file:./prompts/x.txt}"` or inline (JSON) | In Markdown the body *is* the prompt; in JSON use `prompt` (a string or a `{file:...}` reference). |
| `color` | hex or theme value (`primary`, `accent`, …) | UI accent for the agent. |
| `disable` | `true` | Turns the agent off. |
| `permission` | object | Per-tool access control (see below). |
| `reasoningEffort`, `textVerbosity`, … | provider-specific | Any extra key is passed through to the provider as a model option. |

## Permissions

`permission` controls what the agent may do. Each key takes a shorthand action (`allow` \| `ask` \| `deny`); some keys also accept a `{ pattern: action }` object for fine-grained control. Agent permissions are merged with global config; **agent rules take precedence**.

Current permission keys:

| Key | Governs | Granular? |
|---|---|---|
| `read` | reading a file | by file path |
| `edit` | all file modifications (covers `edit`, `write`, `patch`) | by path glob |
| `glob` | file globbing | by glob pattern |
| `grep` | content search | by regex |
| `list` | directory listing | — |
| `bash` | shell commands | by parsed command prefix |
| `task` | launching subagents via the Task tool | by subagent name/glob |
| `skill` | loading a skill | by skill name |
| `lsp` | LSP queries | not granular yet |
| `webfetch` | fetching a URL | by URL |
| `websearch` | web search | by query |
| `todowrite` | todo-list management | action only |
| `external_directory` | a tool touching paths outside the project working dir | action only |
| `question` | the agent asking the user a question mid-run | action only |
| `doom_loop` | repeated-action loop guard | action only |

### `permission.task` — the dispatch whitelist

Globs matched against subagent names; **last matching rule wins**, so put `*` first:

```json
{ "agent": { "supervisor": { "mode": "primary",
  "permission": { "task": { "*": "deny", "team-*": "allow", "reviewer": "ask" } } } } }
```

`deny` removes the subagent from the Task tool description entirely (the model won't try to call it). Set `task: deny` on every subagent to keep delegation hierarchical (no native recursion-depth guard — issue #18100; subagent peer-delegation is also unreliable — issue #7296).

### bash command patterns

```yaml
permission:
  bash:
    "*": ask
    "git status *": allow
    "rm -rf *": deny
```

## `opencode.json` essentials

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "supervisor",      // auto-select this primary on launch (must be a primary; falls back to "build" with a warning if missing/not-primary)
  "model": "provider/model-id",       // global default model
  "small_model": "provider/cheap",    // lightweight tasks (e.g. title generation)
  "agent": {
    "supervisor": { "mode": "primary", "permission": { "task": { "*": "deny", "team-*": "allow" } } },
    "team-x":     { "mode": "subagent", "model": "provider/strong", "permission": { "task": "deny" } }
  }
}
```

## Variable substitution (config only)

- `{env:VAR}` — substitutes an environment variable (empty string if unset). Resolved at startup, **before plugins load**.
- `{file:~/.secrets/key}` — substitutes file contents (relative to config dir, or absolute `/`/`~`).

Use these for API keys and tokens; never hardcode secrets in the config.

## Model variants

Some providers expose variants (e.g. Anthropic `high`/`max`; OpenAI `minimal`/`low`/`medium`/`high`/`xhigh`). Select with `provider/model-id` plus the variant the provider documents, or define custom variants under `provider.<id>.models.<model>.variants`.

## CLI: create / list

```bash
opencode agent create     # interactive scaffold; writes to global or .opencode/agents based on the prompt
opencode agent list       # list all available agents

# non-interactive (passing all four runs without prompts):
opencode agent create \
  --path .opencode/agents \
  --description "Reviews code for security and quality, read-only" \
  --mode subagent \
  --permissions read,grep,glob,list \   # alias: --tools; anything omitted is denied
  --model anthropic/claude-sonnet-4-6
```

`--permissions` (alias `--tools`) accepts a comma list from: `bash, read, edit, glob, grep, webfetch, task, todowrite, websearch, lsp, skill`. Everything omitted is denied — a quick way to build a least-privilege agent.

## Session navigation (parent/child)

When a primary dispatches subagents, each runs in a child session. Navigate between them with the keybinds (defaults): `session_child_first` (Leader+Down), `session_child_cycle` (Right), `session_child_cycle_reverse` (Left), `session_parent` (Up). Useful when smoke-testing a team to watch what each dispatched subagent actually did.

## Gotchas

- Subagents start with a **fresh, isolated context** — they see only the dispatch prompt, not the conversation, files, or skills the primary loaded.
- Changing frontmatter requires an OpenCode **restart** to take effect.
- A documentation/registry JSON you keep beside the agents is **not** read by OpenCode unless it is the actual `opencode.json`; keep it in sync manually or treat it as notes only.
- The legacy `tools: { write: false, bash: false }` map still works (`true`≈allow, `false`≈deny, wildcards like `"mymcp_*": false`) but prefer `permission` for new configs.
