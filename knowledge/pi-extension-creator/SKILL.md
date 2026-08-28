---
name: pi-extension-creator
description: "Create, review, package, and troubleshoot Pi coding-agent extensions and Pi packages. Use when asked to build TypeScript extensions for Pi, register tools with pi.registerTool, subscribe to pi.on lifecycle/tool/input/session events, add slash commands, keyboard shortcuts, or CLI flags, build custom UI/widgets/footers/headers/editors and message or tool renderers, contribute skills/prompts/themes, package resources through package.json pi.extensions/skills/prompts/themes, define subagent-style markdown agents in ~/.pi/agent/agents or .pi/agents, install via pi -e or pi install, or implement patterns like permission gates, protected paths, subagents, command rewriters, custom providers, and dynamic resources."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
---

# Pi Extension Creator

## Start Here

Build Pi extensions as TypeScript modules that export a default factory receiving `ExtensionAPI`.

Use current Pi imports for new work:

```ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
```

Older extensions may import from a previous package scope or from `@sinclair/typebox`. Preserve those only when maintaining that codebase. For new code, follow the current docs and local package conventions.

## Workflow

1. Define the extension surface before coding.
   - LLM-callable capability: `pi.registerTool`.
   - User slash command: `pi.registerCommand`.
   - Gate, rewrite, context injection, or lifecycle reaction: `pi.on`.
   - Persistent visible UI: `ctx.ui.setStatus`, `ctx.ui.setWidget`, `ctx.ui.setHeader`, or `ctx.ui.setFooter`.
   - Custom tool/message rendering: `renderCall`, `renderResult`, or `pi.registerMessageRenderer`.
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

## Design Rules

- Give tools narrow names, explicit parameter descriptions, and strong `description` text that tells the model when to use them.
- Prefer `StringEnum([...])` from `@earendil-works/pi-ai` for enum-like string parameters when Google-compatible schemas matter.
- Return actionable error content with `isError: true`; throw only when the tool execution itself should be reported as a failed tool call.
- Use `signal` and pass it to subprocesses, fetches, timers, and long work.
- Stream progress through `onUpdate` only for meaningful state changes.
- Never rely on closure state alone for session behavior that must survive `/reload`, `/resume`, `/fork`, or restart.
- Keep path handling cross-platform with `node:path`, and normalize only at module boundaries.
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

Load [references/custom-subagent-agents.md](references/custom-subagent-agents.md) when the request says custom agent, subagent, supervisor, scout/planner/reviewer/worker roles, `.pi/agents`, `~/.pi/agent/agents`, `agentScope`, markdown agent files, parallel/chain delegation, or child-session context.

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
- [references/custom-subagent-agents.md](references/custom-subagent-agents.md) - Build subagent-style extensions: markdown agent files, discovery and scope, context isolation, single/parallel/chain delegation, and model routing, grounded in the official Pi subagent example. Load before creating or tuning subagent extensions.
- [references/package-and-release.md](references/package-and-release.md) - Pi package layout, dependencies, install modes, filtering, release checklist, and validation. Load when packaging or distributing.

### scripts/

- [scripts/init_pi_extension.py](scripts/init_pi_extension.py) - Copy the basic template into a target directory and rename package identifiers. Run when starting a new Pi extension package.

### assets/

- [assets/templates/basic-pi-extension/](assets/templates/basic-pi-extension/) - Minimal typed Pi package with `src/index.ts`, `package.json`, `tsconfig.json`, and a small test.
- [assets/agent-template.md](assets/agent-template.md) - Fill-in markdown template for a Pi subagent-style agent (name/description/tools/model). Copy when creating an agent file.
- [assets/examples/](assets/examples/) - Focused single-file examples for common extension surfaces plus a sample subagent agent and workflow prompt. Copy only when the matching pattern is needed.
