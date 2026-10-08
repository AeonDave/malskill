# Claude Code Agent Configuration

Use the [official subagent specification](https://code.claude.com/docs/en/sub-agents) for the installed host. These rules target Claude Code 2.1.293; a newer documentation example may require a newer release.

## Scope and discovery

Precedence: managed definitions, session `--agents`, project `.claude/agents/`, user `~/.claude/agents/`, then plugin `agents/`. Within nested project roots, the definition closest to the current working directory wins. Directories supplied through `--add-dir` also contribute project agents.

Project/user trees are recursive and identity comes from `name`, independent of the filename. Keep names unique within a tree; same-scope duplicates have filesystem-order behavior. Plugin subfolders contribute to names such as `my-plugin:review:security`.

Agent files require parseable YAML frontmatter and a system-prompt body. Use lowercase hyphenated names by convention; the host accepts names up to 256 characters and reserves `:` for plugin scope. Unknown camelCase fields are silently ignored. Missing `name` or malformed YAML skips project/user definitions; plugin fallback behavior differs. Inspect `--debug` when discovery fails.

## Fields to choose

| Field | Contract |
|---|---|
| `name`, `description` | Required identity and delegation trigger. |
| `tools`, `disallowedTools` | Comma-separated names or YAML lists. Omitted `tools` inherits the available pool; deny entries are removed before allowlist resolution. |
| `model` | `sonnet`, `opus`, `haiku`, `fable`, an available full ID, or `inherit`. Omission follows model resolution below. |
| `permissionMode` | `default` (`manual` alias), `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, or `plan`; parent precedence still applies. |
| `maxTurns` | Turn cap; reaching it can return a partial result that needs continuation. |
| `skills` | Named skills whose full contents are preloaded; missing, disabled, or `disable-model-invocation: true` skills are skipped. |
| `mcpServers` | Configured server names or inline name-to-config mappings. |
| `hooks` | Agent-scoped lifecycle hooks; `Stop` becomes `SubagentStop`. |
| `memory` | `user`, `project`, or `local`; see the capability change below. |
| `background` | `true` keeps the worker in the background. Omission lets the host choose according to execution mode. |
| `omitClaudeMd` | Omits user/project/local instructions, retaining managed policy except for managed definitions. Ignored for a main-session agent. Requires 2.1.271+. |
| `effort` | `low`, `medium`, `high`, `xhigh`, `max`, subject to model support. Overrides session effort, not `CLAUDE_CODE_EFFORT_LEVEL`. |
| `isolation` | `worktree`; its branch base is normally the default branch, not the parent session's `HEAD`. |
| `color` | `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, or `cyan`. |
| `initialPrompt` | First turn when the definition runs as the main agent; ignored for plugin subagents. |
| `experimental` | File-only experimental options; `cacheTtl` accepts `5m` or `1h`, with account restrictions documented by the host. |

Plugin subagents ignore `permissionMode`, `mcpServers`, and `hooks`. Put required capabilities in plugin-level configuration or use a project/user definition.

## Effective tools and permissions

An allowlist narrows the available pool; it cannot add tools the host removes. Background workers have a smaller built-in pool than foreground workers, while explicit conversation forks retain the parent's pool. Do not promise UI-bound tools such as `AskUserQuestion` to a named subagent. An unresolved allowlist can prevent launch.

`disallowedTools: Bash(git push *)` removes all of `Bash`. For command-level restrictions, keep Bash and use session `permissions.deny` or a validating `PreToolUse` hook. MCP server patterns such as `mcp__github` or `mcp__github__*` select the server's tools; `mcp__*` can deny all MCP tools.

`Agent(worker, researcher)` limits spawn types only when the definition runs as the main session through `--agent`. In a subagent it grants `Agent`, but the parenthesized type filter is ignored. Nested workers still obey host depth limits.

When the parent uses `bypassPermissions`, `acceptEdits`, or `auto`, that mode wins. With `default`, `dontAsk`, or `plan`, the definition's mode applies except that `bypassPermissions` cannot elevate the parent. An omitted mode inherits. `dontAsk` denies prompts rather than granting capabilities.

## Model resolution

Ordinary order: invocation override, definition `model`, `CLAUDE_CODE_SUBAGENT_MODEL`, then parent model. `model: inherit` explicitly selects the parent; omission leaves the environment default eligible. A mod's `agent.spawn` hook can replace the invocation value, and organization model policy can substitute a permitted model.

`CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` changes this order: paired with `CLAUDE_CODE_SUBAGENT_MODEL`, it forces that model across applicable workers. Without a paired model it uses the parent, with built-in Explore exceptions. Conversation forks and subagent skills declaring `model: inherit` retain the parent model. Inspect `/tasks` to confirm the actual model/effort instead of inferring it from a definition.

Do not assume Explore uses Haiku: its current built-in model follows the parent/provider rules. Select `haiku` in a custom definition when that choice is intended.

## Skills, memory, MCP, and hooks

Preloading does not grant the `Skill` tool. Include `Skill` when the worker must discover or invoke additional skills. Keep reusable methodology in skills rather than copying it into several agent bodies.

`memory: user` stores under `~/.claude/agent-memory/<name>/`; `project` uses `.claude/agent-memory/<name>/`; `local` uses `.claude/agent-memory-local/<name>/`. Enabled memory injects the first 200 lines or 25KB of `MEMORY.md` and automatically grants Read/Write/Edit. When auto memory is disabled, the field has no effect. Omit memory for a strict no-write worker.

```yaml
mcpServers:
  - github
  - browser:
      type: stdio
      command: npx
      args: ["-y", "@playwright/mcp@latest"]
```

Named servers reuse the parent's connection; inline servers connect for the worker's lifetime. Inline definitions support the MCP config's `stdio`, `http`, `sse`, and `ws` transports. Project/additional-directory inline servers and frontmatter hooks require trust for the folder containing the definition; parent-folder trust or a non-interactive session does not substitute. Managed MCP policies still apply. Diagnose skipped servers/hooks through `--debug`.

For conditional execution checks, use a `PreToolUse` command hook and exit 2 to block. Validate its actual JSON input and command semantics. Windows hooks can use `shell: powershell`; do not treat a keyword filter as a reliable shell or SQL parser.

## Context and execution

A named non-fork worker receives its body, delegation message, applicable instruction hierarchy, optional git snapshot, and preloaded skills. It does not receive parent conversation history, previously read files, output style, or the parent's auto-memory content. Explore/Plan skip the instruction hierarchy and git snapshot; `omitClaudeMd` changes custom-agent instruction loading.

An explicit conversation fork inherits the conversation, system prompt, model, and tool pool. A skill with `context: fork` uses the skill-subagent mechanism and does not inherit conversation history. Select the mode based on the required context and capability boundary.

Nested spawning defaults to three layers below the main conversation; `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` disables nesting. The concurrent-worker cap is separately controlled by `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`. Wait for active workers to complete rather than retrying a concurrency-limit error. A background worker may finish in a later turn; do not claim its result before delivery. Resume a custom worker when its existing history is needed; Explore/Plan are one-shot.

With `isolation: worktree`, provide the required base and change set explicitly if current uncommitted work matters. Verify the worktree's revision and inputs before editing; a separate checkout does not automatically contain the parent's changes.

## Invocation and CLI definitions

Name the worker in the delegation request or use `@agent-<name>` to force a behavior check. `claude --agent <name>` uses the definition for the whole session. Deny `Agent(<name>)` in session permissions to block a type.

`--agents` takes a JSON object keyed by agent name; each definition uses `prompt` for the body and the supported frontmatter fields. `color` and `experimental` are ignored in this form. Non-interactive `claude -p --agents ./agents.json` accepts a file as of 2.1.281; interactive mode requires inline JSON. Empty `prompt` is supported in that release, with different main-session behavior when no memory is set.

```bash
claude --agents '{"change-reviewer":{"description":"Reviews a supplied change set","prompt":"Inspect the supplied files; return defects with file references.","tools":["Read","Grep","Glob"],"model":"inherit"}}'
```

In PowerShell, pass multiline JSON as a literal here-string. Use [triggering-and-testing.md](triggering-and-testing.md) for reload and validation checks.
