# Pi Extension API Surface

## Table of Contents

- [Imports](#imports)
- [Factory](#factory)
- [Events](#events)
- [Tools](#tools)
- [Commands And Input](#commands-and-input)
- [UI](#ui)
- [State](#state)
- [Rendering](#rendering)
- [Modes](#modes)
- [Errors](#errors)

## Imports

For new code:

```ts
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { StringEnum } from "@earendil-works/pi-ai";
import { Text } from "@earendil-works/pi-tui";
```

Use Node built-ins with `node:` imports:

```ts
import { spawn } from "node:child_process";
import path from "node:path";
```

If maintaining older extensions, check the repo before changing imports. Public examples may still use `@mariozechner/*` or `@sinclair/typebox`.

## Factory

The extension entry point is a default export:

```ts
export default function myExtension(pi: ExtensionAPI) {
  pi.registerTool({ /* ... */ });
  pi.registerCommand("name", { /* ... */ });
  pi.on("session_start", async (event, ctx) => { /* ... */ });
}
```

Async factories are allowed, but Pi waits for them before normal startup. Use async factories only for required startup discovery such as model/provider listing.

Do not start long-lived resources in the factory. Start them lazily and close them from `session_shutdown`.

## Events

Core lifecycle:

```text
startup -> project_trust -> session_start -> resources_discover
user prompt -> input -> before_agent_start -> agent_start -> turn_start
tool use -> tool_execution_start -> tool_call -> tool_result -> tool_execution_end
turn_end -> agent_end
session changes -> session_before_* -> session_shutdown -> session_start
```

Common handlers:

```ts
pi.on("tool_call", async (event, ctx) => {
  if (event.toolName !== "bash") return;
  const command = event.input.command;
  if (typeof command === "string" && command.includes("rm -rf")) {
    if (!ctx.hasUI) return { block: true, reason: "Blocked dangerous command." };
    const ok = await ctx.ui.confirm("Dangerous command", command);
    if (!ok) return { block: true, reason: "Blocked by user." };
  }
});
```

Use event returns only where Pi documents a return shape. For gates, return `{ block: true, reason }` or mutate the event input in place when rewriting.

Useful event choices:

| Need | Event |
|---|---|
| Trust or decline project-local resources | `project_trust` |
| Rehydrate state, register session-specific tools | `session_start` |
| Add skill/prompt/theme paths | `resources_discover` |
| Intercept user text before agent run | `input` |
| Inject per-turn system prompt additions | `before_agent_start` |
| Add/trim context before provider request | `context` |
| Gate or rewrite tool args | `tool_call` |
| Inspect or alter tool result | `tool_result` |
| Update footer/status after work | `turn_end`, `agent_end` |
| Prevent destructive session operations | `session_before_switch`, `session_before_fork`, `session_before_compact` |
| Release resources | `session_shutdown` |

## Tools

Register tools with `pi.registerTool`. Tools may be registered at load time, on `session_start`, or later from commands/events.

```ts
const Params = Type.Object({
  action: StringEnum(["status", "run"] as const),
  target: Type.Optional(Type.String({ description: "Path, command, or item to process" })),
});

pi.registerTool({
  name: "example_tool",
  label: "Example",
  description: "Run a narrow operation. Use when the user asks for example status or execution.",
  promptSnippet: "Use example_tool for example extension status or execution.",
  promptGuidelines: ["Call with action=status before action=run when target is unclear."],
  parameters: Params,
  async execute(toolCallId, params, signal, onUpdate, ctx) {
    onUpdate?.({ content: [{ type: "text", text: "Starting..." }] });
    return {
      content: [{ type: "text", text: `Action: ${params.action}` }],
      details: { params, cwd: ctx.cwd },
    };
  },
});
```

Tool result rules:

- `content` is what the model sees.
- `details` is persisted and can support reconstruction or custom rendering.
- `isError: true` marks recoverable tool failure.
- `terminate: true` is for final structured-output tools that should end the agent loop.
- Include compact, actionable text. Put bulky structured state in `details`.

For subprocess tools:

- Pass `signal` to the process or kill on abort.
- Return stdout/stderr summaries, exit code, and decisive artifacts.
- Avoid dumping large output; truncate deterministically and include where the full output was saved.

## Commands And Input

Commands are user-facing slash commands:

```ts
pi.registerCommand("example", {
  description: "Show extension diagnostics",
  handler: async (args, ctx) => {
    ctx.ui.notify(`Args: ${args || "(none)"}`, "info");
  },
});
```

Use commands for user-controlled operations, settings views, diagnostics, reload flows, and editor helpers.

Use `input` event transforms for syntax that should work in normal prompts:

```ts
pi.on("input", async (event) => {
  if (event.source === "extension") return { action: "continue" };
  if (!event.text.includes("!{date}")) return { action: "continue" };

  return {
    action: "transform",
    text: event.text.replaceAll("!{date}", "Run date now"),
  };
});
```

Keep input transforms predictable. Do not hide network calls or destructive behavior inside prompt rewrites.

Input handlers must return one of:

- `{ action: "continue" }` to let normal prompt processing continue.
- `{ action: "transform", text, images? }` to replace the user input.
- `{ action: "handled" }` when the extension fully handled the input and no model turn should start.

## UI

Dialog methods:

```ts
if (ctx.hasUI) {
  const ok = await ctx.ui.confirm("Proceed?", "This changes session state.");
  if (!ok) return;
}
```

Status and widgets:

```ts
ctx.ui.setStatus("my-ext", ctx.ui.theme.fg("dim", "my-ext idle"));
ctx.ui.setWidget("my-ext", ["My Extension", "Ready"]);
```

Use `ctx.mode === "tui"` before custom components, keyboard handling, custom editors, games, or overlay-style UI.

Always provide non-interactive behavior:

- Deny risky gates by default.
- Allow safe diagnostics.
- Return an actionable message explaining how to run interactively if needed.

## State

Closure state is acceptable for per-process caches only. Anything needed after `/reload`, `/resume`, restart, or fork must be reconstructable.

Tool-backed persistence:

```ts
return {
  content: [{ type: "text", text: "Added item." }],
  details: { items: nextItems },
};
```

Rehydrate:

```ts
pi.on("session_start", async (_event, ctx) => {
  for (const entry of ctx.sessionManager.getBranch()) {
    if (entry.type !== "message") continue;
    const details = entry.message?.details;
    // Validate shape before using.
  }
});
```

Use `pi.appendEntry(customType, data)` for extension-owned state that is not tied to a tool result. Pair it with a custom renderer if users should inspect it.

## Rendering

Use custom rendering when default output is too noisy or the tool has durable structured state.

Tool rendering:

```ts
import { Text } from "@earendil-works/pi-tui";

pi.registerTool({
  name: "status_tool",
  label: "Status",
  description: "Show status",
  parameters: Type.Object({}),
  async execute() {
    return { content: [{ type: "text", text: "ok" }], details: { ok: true } };
  },
  renderCall(args, theme) {
    return new Text(theme.fg("accent", "status_tool"), 0, 0);
  },
});
```

Message rendering:

```ts
import { Text } from "@earendil-works/pi-tui";

pi.registerMessageRenderer("my-extension", (message, options, theme) => {
  const extra = options.expanded ? `\n${JSON.stringify(message.details, null, 2)}` : "";
  return new Text(theme.fg("accent", `[my-extension] ${message.content}${extra}`), 0, 0);
});
```

Prefer compact collapsed views and useful expanded details.

## Modes

Mode behavior:

| Mode | `ctx.mode` | `ctx.hasUI` | Rule |
|---|---|---|---|
| Interactive terminal | `tui` | `true` | Full UI and TUI components |
| RPC | `rpc` | `true` | Dialogs/notifications work; custom TUI may not |
| JSON stream | `json` | `false` | No prompts; return text decisions |
| Print | `print` | `false` | No prompts; avoid UI-only flows |

Guard mode-specific code explicitly.

## Errors

Use these defaults:

- Gate denial: return `{ block: true, reason }`.
- Recoverable tool failure: return `{ content, details, isError: true }`.
- Programming/runtime failure inside a tool: throw and let Pi report the failed tool call.
- Event handler exceptions are logged; `tool_call` errors fail safe and block the tool.

Error content should tell the agent what can be retried, what is blocked, and what evidence was collected.
