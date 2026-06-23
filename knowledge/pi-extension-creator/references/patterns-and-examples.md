# Pi Extension Patterns And Examples

## Table of Contents

- [Choose A Shape](#choose-a-shape)
- [Safety Gate](#safety-gate)
- [Subprocess Tool](#subprocess-tool)
- [Subagent Or Fork Tool](#subagent-or-fork-tool)
- [Command Rewriter](#command-rewriter)
- [Stateful Tool](#stateful-tool)
- [Dynamic Resources](#dynamic-resources)
- [UI Extension](#ui-extension)
- [Provider Or MCP Bridge](#provider-or-mcp-bridge)
- [Example Sources](#example-sources)

## Choose A Shape

Use this map before writing code:

| Requirement | Shape |
|---|---|
| One permission/path/input rule | Single `.ts` extension |
| One simple tool | Single `.ts` extension |
| Tool plus rendering, config, runner, tests | Package with `src/index.ts` and sibling modules |
| Spawning Pi children | Package with runner module, event parser, config module, renderer |
| Rewriting built-in tool calls | Event gate module plus policy tests |
| Replacing built-in tools | Register same tool names, preserve common args and rendering expectations |
| External binary/runtime integration | Package dependency, resolver, diagnostics command, timeouts |
| Shared skills/prompts/themes | Pi package manifest or `resources_discover` |
| Complex TUI | Directory extension with component modules and mode guards |

## Safety Gate

Pattern:

1. Match the exact event/tool.
2. Classify the operation with pure logic.
3. If safe, return nothing.
4. If risky and UI exists, ask.
5. If risky and non-interactive, use conservative fallback.
6. Return a block reason the model can act on.

Good targets:

- Dangerous bash patterns.
- Protected paths such as `.env`, `.git/`, `node_modules/`, credentials, keys.
- Session changes with dirty git state.
- Project trust decisions.

Avoid broad regex-only gates when an argument parser exists. Put shell/path classification in testable modules.

## Subprocess Tool

Pattern from `pi-fork` and subagent examples:

1. Build a narrow tool schema.
2. Gather minimal context needed by the child process.
3. Spawn with explicit cwd/env/stdio.
4. Connect abort signal to process termination.
5. Parse event stream or output into a structured result.
6. Return dense text and structured `details`.
7. Render collapsed output tersely.

Use config for:

- Model/provider/thinking profiles.
- Child extension loading.
- Offline behavior.
- Environment overlay.
- Timeout and retry behavior.

Do not pass secrets unless the user or settings explicitly require them.

## Subagent Or Fork Tool

Use a fork-style tool when child sessions should inherit active conversation branch context.

Use named subagents when:

- Work should use a named role/persona.
- Agent definitions live in user/project files.
- The caller should select one role and one focused task.

Implementation rules:

- Validate agent names against discovered files.
- Report available agent names on unknown input.
- Keep child report instructions stable; only the task changes.
- Return sections that support decisions: result, evidence, output, learnings.
- Treat recursive extension loading as explicit configuration. Use tri-state semantics when useful:
  - omitted/null: normal Pi loading.
  - empty array: no child extensions.
  - non-empty array: only listed child extensions.

## Command Rewriter

Pattern from Hypa-style integrations:

1. Load config once, resolve binary/runtime path.
2. Register explicit diagnostic command.
3. Register tools first if the integration exposes model-callable functions.
4. Hook `tool_call` for `bash` or selected built-ins.
5. Rewrite event input in place for allowed rewrites.
6. Return `{ block: true, reason }` for deny.
7. Ask user only when `ctx.hasUI`; otherwise follow configured fallback.

Useful diagnostics command output:

- Mode.
- Config source.
- Binary and resolved binary.
- Timeout.
- Non-interactive fallback.
- Last rewrite status.
- Active custom tools.

## Stateful Tool

Use session-persisted `details` for todo lists, game state, queues, counters, and task trackers.

State rules:

- Validate deserialized details before trusting them.
- Rebuild from branch entries in order.
- Store enough data to resume after fork/reload.
- Keep large or private data out of `details`; store paths or summaries instead.
- Use custom rendering for state the user needs to inspect.

When concurrent tool calls can corrupt state, set a sequential execution mode if the current Pi API supports it, or implement a local mutation queue.

## Dynamic Resources

Use `resources_discover` when an extension contributes skills, prompts, or themes based on cwd/config.

Return only paths that exist and are intended for the current project.

Do not expose untrusted project resources before project trust is resolved. Project-local extensions load only after trust; user/global extensions can participate in `project_trust`.

## UI Extension

Use UI for user control, not hidden policy.

Patterns:

- `setStatus` for one-line footer state.
- `setWidget` for persistent dashboards.
- `setHeader`/`setFooter` for broader chrome.
- `ui.custom` for focused multi-step workflows.
- `setEditorText` for command-generated prompt drafts.

Rules:

- Guard TUI-only code with `ctx.mode === "tui"`.
- Keep UI state derived from extension state; clear it on `session_shutdown`.
- Avoid custom UI for decisions that must work in CI or print mode unless a fallback exists.

## Provider Or MCP Bridge

Use provider registration for model/provider integration.

Use MCP or tool bridge patterns when the extension exposes external capabilities:

- Keep discovery separate from call execution.
- Deduplicate generated tools.
- Compress or summarize noisy external output before returning to the model.
- Redact known secrets in diagnostics and tool output.
- Add timeouts for every external call.

## Example Sources

Use these sources as pattern references, not as code to paste blindly:

- Official Pi docs: https://pi.dev/docs/latest/extensions
- Official Pi package docs: https://pi.dev/docs/latest/packages
- Official examples: https://github.com/earendil-works/pi/tree/main/packages/coding-agent/examples/extensions
- `elpapi42/pi-fork`: https://github.com/elpapi42/pi-fork
- `elpapi42/pi-minimal-subagent`: https://github.com/elpapi42/pi-minimal-subagent
- `Hypabolic/Hypa` Pi package: https://github.com/Hypabolic/Hypa/tree/main/packages/pi-hypa

Normalize imports and APIs against current Pi docs before creating new code.
