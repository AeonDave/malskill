---
name: pi-extension-creator
description: "Create or revise Pi extensions, plugins, and themes. Use for extension entrypoints, tools, commands, events, UI integration, state, MCP servers, codemode and tool exposure, virtual models, theme files, and packaging."
license: MIT
metadata:
  author: AeonDave
  version: "1.4"
---

# Pi Extension Creator

## Start Here

Build Pi extensions as TypeScript modules that export a default factory receiving `ExtensionAPI`.

Import from the current Pi packages:

```ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
```

## Capabilities

Pi 1.0 extension-facing capabilities, where each is covered in this skill, and its official doc. Load the listed reference before building against a capability.

| Capability | Load | Pi doc |
|---|---|---|
| Model-callable tools, nested calls, structured output | [api-surface](references/api-surface.md), [codemode-and-mcp](references/codemode-and-mcp.md) | [extensions](https://pi.dev/docs/latest/extensions) |
| Lifecycle events and hooks | [api-surface](references/api-surface.md) | [extensions](https://pi.dev/docs/latest/extensions) |
| Slash commands, shortcuts, CLI flags | [api-surface](references/api-surface.md) | [slash-commands](https://pi.dev/docs/latest/slash-commands) |
| Terminal UI, chrome, custom rendering | [advanced-redesign](references/advanced-redesign.md), [api-surface](references/api-surface.md) | [tui](https://pi.dev/docs/latest/tui) |
| Session state and custom entries | [api-surface](references/api-surface.md) | [session-format](https://pi.dev/docs/latest/session-format) |
| Codemode scripts, classifiers, image models | [codemode-and-mcp](references/codemode-and-mcp.md) | [codemode](https://pi.dev/docs/latest/codemode) |
| Tool exposure and tool search | [codemode-and-mcp](references/codemode-and-mcp.md) | [mcp](https://pi.dev/docs/latest/mcp) |
| MCP servers | [codemode-and-mcp](references/codemode-and-mcp.md) | [mcp](https://pi.dev/docs/latest/mcp) |
| Virtual models (per-request routing) | [virtual-models](references/virtual-models.md) | [virtual-models](https://pi.dev/docs/latest/virtual-models) |
| Custom model providers and OAuth | [api-surface](references/api-surface.md) | [custom-provider](https://pi.dev/docs/latest/custom-provider) |
| Themes (color files and theme APIs) | [themes](references/themes.md) | [themes](https://pi.dev/docs/latest/themes) |
| Subagent-style delegation | [custom-subagent-agents](references/custom-subagent-agents.md) | [extensions](https://pi.dev/docs/latest/extensions) |
| Contribute skills and prompt templates | [package-and-release](references/package-and-release.md) | [skills](https://pi.dev/docs/latest/skills), [prompts](https://pi.dev/docs/latest/prompt-templates) |
| Package and distribute | [package-and-release](references/package-and-release.md) | [packages](https://pi.dev/docs/latest/packages) |
| Run modes and embedding (TUI/RPC/JSON/print, SDK) | [api-surface](references/api-surface.md), [codemode-and-mcp](references/codemode-and-mcp.md) | [sdk](https://pi.dev/docs/latest/sdk) |

The [API Index](references/api-surface.md#api-index) lists the complete `pi`, `ctx`, and `ctx.ui` method surface.

## Workflow

1. Define the extension surface before coding.
   - LLM-callable capability: `pi.registerTool`.
   - User slash command: `pi.registerCommand`.
   - Gate, rewrite, context injection, or lifecycle reaction: `pi.on`.
   - Persistent visible UI: `ctx.ui.setStatus`, `ctx.ui.setWidget`, `ctx.ui.setHeader`, or `ctx.ui.setFooter`.
   - Custom tool/message rendering: `renderCall`, `renderResult`, or `pi.registerMessageRenderer`.
   - Transform rendered markdown: `pi.registerMarkdownTransformer`.
   - MCP server connection: `pi.registerMcpServer` or `mcp.json`.
   - Codemode/tool-search visibility and nested calls: tool `exposure` plus `ctx.executeTool`.
   - Per-request model routing: `pi.registerVirtualModel`.
   - Colors only: a JSON theme file (no code).
   - Shared installable bundle: Pi package with `package.json` `pi` manifest.
2. Pick the smallest layout.
   - Single `.ts` file for one tool, one command, or a simple event gate.
   - Directory with `index.ts` plus sibling modules for stateful tools, subprocess runners, renderers, or policies.
   - npm/git Pi package when users should install it with `pi install`.
3. Keep the extension factory light.
   - Register tools, commands, flags, shortcuts, and event handlers there.
   - Do not start long-lived watchers, servers, child processes, or timers in the factory.
   - Start session-scoped resources from `session_start`, a command, a tool call, or the exact event that needs them.
   - Clean up in `session_shutdown`; make cleanup idempotent.
4. Implement with Pi runtime modes in mind.
   - Check `ctx.hasUI` before confirm/select/input/notify flows.
   - Check `ctx.mode === "tui"` before custom TUI components or editor replacement.
   - Provide non-interactive fallbacks for `print`, JSON, and CI usage.
5. Persist state through the session, not hidden process memory.
   - Put reconstructable state in tool result `details` when it affects future behavior.
   - Rebuild in-memory state from `ctx.sessionManager.getBranch()` on `session_start`.
   - Use `pi.appendEntry()` for custom persistent entries that are not natural tool results.
6. Test pure logic outside Pi.
   - Move parsing, settings resolution, command construction, and policy decisions into plain modules.
   - Unit-test those modules with `node --test`, `tsx --test`, or the project toolchain.
   - Typecheck with `tsc --noEmit`.
7. Verify in Pi before claiming it works.
   - Quick load: `pi -e ./path/to/index.ts`.
   - Auto-discovery: copy/link into `~/.pi/agent/extensions/` or `.pi/extensions/`, then use `/reload`.
   - Package install: `pi install ./package` or `pi -e ./package`.

## API Routing

Load [references/api-surface.md](references/api-surface.md) when writing handler signatures, event returns, tool result shapes, UI behavior, rendering, or provider/resource integration.

Use these defaults:

| Goal | API |
|---|---|
| Add a model-callable operation | `pi.registerTool({ name, label, description, parameters, execute })` |
| Block or rewrite a tool call | `pi.on("tool_call", handler)` |
| Modify per-turn system context | `pi.on("before_agent_start", handler)` or `pi.on("context", handler)` |
| Add `/command` | `pi.registerCommand("name", { description, handler })` |
| Add keyboard shortcut | `pi.registerShortcut("ctrl+x", { description, handler })` |
| Add CLI flag | `pi.registerFlag("name", { type, default, description })` |
| Run a shell command | `pi.exec("git", ["status"], { signal, timeout })` |
| Inject a user message or trigger a turn | `pi.sendUserMessage(text, { deliverAs })` |
| Enable/disable tools at runtime | `pi.setActiveTools(names)` / `pi.getAllTools()` |
| Ask the user | `ctx.ui.confirm`, `ctx.ui.select`, `ctx.ui.input`; guard with `ctx.hasUI` |
| Show status or dashboard text | `ctx.ui.setStatus`, `ctx.ui.setWidget` |
| Override a built-in tool | Register a tool with the same name, then preserve expected args/rendering |
| Contribute skills/prompts/themes dynamically | `pi.on("resources_discover", handler)` |
| Communicate across extensions | `pi.events` |
| Add a provider/model source | `pi.registerProvider` |
| Connect an MCP server | `pi.registerMcpServer(name, config)` |
| Control model/codemode visibility of a tool | `exposure`, `namespace`, `prepareLoadout` |
| Call a tool from inside a tool | `ctx.executeTool(name, args, opts)` |
| Return machine-readable data to scripts | `outputSchema` + `structuredContent` |
| Route each request to a physical model | `pi.registerVirtualModel(def)` |
| Transform rendered markdown | `pi.registerMarkdownTransformer(fn)` |
| Read or switch the active theme | `ctx.ui.getAllThemes` / `ctx.ui.setTheme` |
| Read merged user+project settings | `pi.getSettings()` |

## Design Rules

- Give tools narrow names, explicit parameter descriptions, and strong `description` text that tells the model when to use them.
- Prefer `StringEnum([...])` from `@earendil-works/pi-ai` for enum-like string parameters when Google-compatible schemas matter.
- Return actionable error content with `isError: true`; throw only when the tool execution itself should be reported as a failed tool call.
- Use `signal` and pass it to subprocesses, fetches, timers, and long work.
- Stream progress through `onUpdate` only for meaningful state changes.
- Never rely on closure state alone for session behavior that must survive `/reload`, `/resume`, `/fork`, or restart.
- Keep path handling cross-platform with `node:path`, and normalize only at module boundaries.
- Choose tool `exposure` deliberately: `direct` for tools the model calls, `model-only` for orchestrators, `codemode`/`deferred` for tools reached through scripts or `tool_search`, `hidden` to withdraw one.
- Return `outputSchema` + `structuredContent` for data tools so codemode scripts and `ctx.executeTool` callers get structured values, not reparsed text.
- Treat project-local extensions and packages as trusted code that run with full system access; keep security-sensitive defaults conservative.

## Example Selection

Load [references/patterns-and-examples.md](references/patterns-and-examples.md) when choosing structure. It maps common surfaces to the official Pi extension examples:

- Safety gates and protected paths.
- Runtime/dynamic tool registration.
- Stateful tools with custom `renderCall`/`renderResult`.
- Subprocess and subagent (child-session) runners.
- Dynamic resource contribution.
- Packages that bundle npm dependencies.
- Custom message and entry rendering.

Load [references/advanced-redesign.md](references/advanced-redesign.md) when the request says redesign, advanced theme, UI chrome, statusline, powerline footer, hide/show Pi UI, replace footer/header/editor, or combine a JSON theme with extension behavior.

Load [references/themes.md](references/themes.md) when authoring a JSON theme file: color roles/tokens, color syntax (hex, OKLCH, OKHSL, 256-index), `appearance`, `vars`, HTML `export` colors, the `system` theme, or reading/switching themes from an extension.

Load [references/custom-subagent-agents.md](references/custom-subagent-agents.md) when the request says custom agent, subagent, supervisor, scout/planner/reviewer/worker roles, `.pi/agents`, `~/.pi/agent/agents`, `agentScope`, markdown agent files, parallel/chain delegation, or child-session context.

Load [references/codemode-and-mcp.md](references/codemode-and-mcp.md) when the request says codemode, MCP, `mcp.json`, `registerMcpServer`, tool exposure, `tool_search`, nested tool calls, `ctx.executeTool`, `structuredContent`, `namespace`, `prepareLoadout`, built-in extensions, or the codemode/MCP SDK wiring.

Load [references/virtual-models.md](references/virtual-models.md) when the request says virtual model, model router, routing by task/cost/phase, `registerVirtualModel`, `route()`, or `provider/auto`.

## Packaging

Load [references/package-and-release.md](references/package-and-release.md) before publishing, installing, adding dependencies, or wiring a repo as a Pi package.

Minimum package manifest:

```json
{
  "name": "my-pi-extension",
  "type": "module",
  "keywords": ["pi-package"],
  "pi": {
    "extensions": ["./src/index.ts"]
  }
}
```

Use peer dependencies for Pi-provided packages and runtime dependencies for everything your extension imports at runtime.

## Resources

### references/

- [references/api-surface.md](references/api-surface.md) - Pi extension APIs, event routing, tool signatures, UI modes, rendering, state, and error behavior. Load before implementing API handlers.
- [references/patterns-and-examples.md](references/patterns-and-examples.md) - Architecture patterns mapped to the official Pi extension examples. Load when choosing a design or reviewing an existing extension.
- [references/advanced-redesign.md](references/advanced-redesign.md) - Theme-vs-extension decision rules, advanced UI chrome replacement, statusline/footer/header/editor patterns, mode limits, and validation. Load before implementing a redesign or advanced theme package.
- [references/themes.md](references/themes.md) - JSON theme authoring: file format, color roles and syntax, `appearance`, `vars`, HTML `export`, the `system` theme, loading/hot-reload, and extension theme APIs. Load before writing a theme file.
- [references/custom-subagent-agents.md](references/custom-subagent-agents.md) - Build subagent-style extensions: markdown agent files, discovery and scope, context isolation, single/parallel/chain delegation, and model routing, grounded in the official Pi subagent example. Load before creating or tuning subagent extensions.
- [references/codemode-and-mcp.md](references/codemode-and-mcp.md) - Built-in extensions, tool exposure model, codemode runtime, `tool_search`, nested `ctx.executeTool` calls, structured output, MCP server config and extension registration, and SDK wiring. Load before working with codemode, MCP, or tool orchestration.
- [references/virtual-models.md](references/virtual-models.md) - Register a virtual model and route each request to a physical model with `route()`, including request reasons and branch-scoped routing state. Load before building a model router.
- [references/package-and-release.md](references/package-and-release.md) - Pi package layout, dependencies, install modes, filtering, release checklist, and validation. Load when packaging or distributing.

### scripts/

- [scripts/init_pi_extension.py](scripts/init_pi_extension.py) - Copy the basic template into a target directory and rename package identifiers. Run when starting a new Pi extension package.

### assets/

- [assets/templates/basic-pi-extension/](assets/templates/basic-pi-extension/) - Minimal typed Pi package with `src/index.ts`, `package.json`, `tsconfig.json`, and a small test.
- [assets/agent-template.md](assets/agent-template.md) - Fill-in markdown template for a Pi subagent-style agent (name/description/tools/model). Copy when creating an agent file.
- [assets/examples/](assets/examples/) - Focused single-file examples for common extension surfaces plus a sample subagent agent and workflow prompt. Copy only when the matching pattern is needed.
