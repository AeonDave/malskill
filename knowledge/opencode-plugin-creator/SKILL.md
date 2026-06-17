---
name: opencode-plugin-creator
description: "Build, structure, test, and ship OpenCode CLI plugins — the JS/TS modules that extend OpenCode through the @opencode-ai/plugin API. Use when asked to create an OpenCode plugin, add a plugin hook (event, config, chat.message, chat.params, chat.headers, permission.ask, tool.execute.before/after, shell.env, command.execute.before, tool.definition, auth, provider, dispose, or any experimental.* hook for system-prompt/messages transform or compaction), register a custom tool() backed by a zod schema, scaffold a plugin package.json + tsconfig, wire the `plugin` array in opencode.json, install a local plugin via shim, or publish a plugin to npm. Covers the PluginInput context (client, $, directory, worktree, project, serverUrl), the Hooks return shape, ToolContext/ToolResult, the Bun runtime, and cross-platform gotchas. NOT for OpenCode agents/subagents (use opencode-agent-creator), AGENTS.md files (use agent-md-creator), or portable Agent Skills (use skill-creator)."
license: MIT
compatibility: "OpenCode CLI (opencode.ai). Plugins are JS/TS modules under ~/.config/opencode/plugins/ or .opencode/plugins/, or npm packages in the 'plugin' array of opencode.json."
metadata:
  author: AeonDave
  version: "1.0"
---

# OpenCode Plugin Creator

## Overview

An OpenCode plugin is a JS/TS module that **exports a `Plugin` function**. OpenCode calls it once at startup with a context object (`PluginInput`) and the function returns a **`Hooks` object**. Hooks intercept tools, tune LLM params, add custom tools the model can call, inject system prompts, react to lifecycle events, register auth/providers, and release resources on shutdown.

Plugins run inside OpenCode's **Bun** runtime: TypeScript executes directly (no build step), top-level `await` works, and `import type { Plugin } from "@opencode-ai/plugin"` gives full typing.

The canonical shape — everything else is variations on this:

```ts
import type { Plugin } from "@opencode-ai/plugin"

export const MyPlugin: Plugin = async ({ client, $, directory, worktree, project }) => {
  // one-time init runs here (load config, start servers, restore state)
  return {
    // hooks go here — return only the ones you implement
    "tool.execute.before": async (input, output) => { /* ... */ },
  }
}

export default MyPlugin
```

## Build workflow

Follow these steps in order. **Do not skip step 1** — hook names and the input/output split are precise and easy to get wrong from memory.

1. **Decide the surface.** Use the routing table below to map each behavior to a hook or a custom tool. Before writing any hook body, open [references/hooks.md](references/hooks.md) and copy the **exact** signature — the second `output` argument is mutated in place, and several names are namespaced strings (`"tool.execute.before"`, not `toolExecuteBefore`).
2. **Scaffold.** Copy `assets/template/` to a new directory and rename. It is a complete, working plugin (package.json + tsconfig + entry + test). Adjust `name`, `description`, `keywords`, and `main` in `package.json`.
3. **Implement.** Keep one-time setup in the plugin body; put logic in sibling modules under `src/plugin/` and import them (see the real plugins' layout). Mutate hook `output` in place; **never reassign it**. To block a tool/permission, `throw` from the relevant hook.
4. **Test.** `bun test` against pure helper modules (the real plugins keep logic testable by extracting it out of hook closures). `tsc --noEmit` (or `npm run typecheck`) must pass. See [references/patterns.md](references/patterns.md) for what to make testable.
5. **Verify it loads.** Typechecking is not proof. Load it in OpenCode (npm entry or local shim — see [references/publishing.md](references/publishing.md)), start OpenCode, and confirm the plugin's startup log line appears. Only then report it as working — see the verification rule in [references/patterns.md](references/patterns.md).
6. **Ship.** Set `package.json` `main`/`exports`/`files`/`peerDependencies` per [references/publishing.md](references/publishing.md), then publish to npm or document the shim install.

## Hook routing — goal → hook

Load [references/hooks.md](references/hooks.md) for the full signature of any hook below.

| You want to… | Use |
|---|---|
| React to session / message / tool lifecycle events | `event` — switch on `event.type` (SDK event names) |
| Read or rewrite the merged config at startup | `config` |
| Block or rewrite a tool call **before** it runs | `"tool.execute.before"` — mutate `output.args`, or `throw` to block |
| Inspect or annotate a tool result | `"tool.execute.after"` |
| Add a brand-new tool the model can call | `tool: { myTool: tool({...}) }` — see [references/custom-tools.md](references/custom-tools.md) |
| Change a tool's description/params shown to the model | `"tool.definition"` |
| Tune temperature / topP / topK / maxTokens / provider options | `"chat.params"` |
| Add HTTP headers to the provider request | `"chat.headers"` |
| See or rewrite an incoming user message + parts | `"chat.message"` |
| Inject extra text into the system prompt | `"experimental.chat.system.transform"` — push to `output.system` |
| Rewrite the whole message array sent to the model | `"experimental.chat.messages.transform"` |
| Auto-allow / auto-deny permission prompts | `"permission.ask"` — set `output.status` |
| Inject env vars into the bash tool & terminals | `"shell.env"` — write to `output.env` |
| Run code before a slash command executes | `"command.execute.before"` |
| Customize the compaction prompt / carry context across compaction | `"experimental.session.compacting"` |
| Skip the synthetic auto-continue after compaction | `"experimental.compaction.autocontinue"` |
| Post-process completed assistant text | `"experimental.text.complete"` |
| Register a provider / dynamic model list | `provider` |
| Add a custom auth method (OAuth / API key) | `auth` |
| Choose the small/cheap model | `"experimental.provider.small_model"` |
| Release ports / watchers / timers on reload or shutdown | `dispose` |

## Project layout (convention)

The proven layout from real plugins — entry point is thin, logic lives in siblings, logic is unit-tested:

```
my-plugin/
├── package.json          # name, type:module, main → src entry, peerDeps, "opencode-plugin" keyword
├── tsconfig.json         # Bundler resolution, strict, types:["bun"], verbatimModuleSyntax
├── README.md             # what/why/install/config; "not affiliated with OpenCode" disclaimer
├── .gitignore            # node_modules, build output, .env
└── src/plugin/
    ├── index.ts          # the Plugin export; thin — wires siblings, returns Hooks
    ├── <feature>.ts      # pure logic, imported by index.ts
    └── ...
└── test/
    └── <feature>.test.ts # bun:test against the pure logic
```

`main` and `exports` point straight at the **`.ts`** entry — OpenCode/Bun runs TypeScript directly, so there is no build artifact to ship.

## Non-negotiables

- **Hooks mutate `output` in place.** Reassigning the argument or returning a value (other than for custom-tool `execute`) is silently ignored.
- **Throw to block.** A thrown error in `"tool.execute.before"` or `"permission.ask"` stops the action; the message reaches the model. Custom-tool `execute` should usually **return** an error string as guidance instead of throwing (see [references/custom-tools.md](references/custom-tools.md)).
- **Don't block startup.** Heavy init (network, backfill, restore) must be fire-and-forget (`void doWork()`), or it delays every session. See [references/patterns.md](references/patterns.md).
- **Log through the client, keep the binding.** `client.app.log({ body: { service, level, message } })` — call it via the client object (a detached reference loses `this` and throws). Fall back to `console`.
- **Verify before claiming success.** Typecheck + tests are necessary, not sufficient. The plugin must actually load in OpenCode and run its hook. See the verification rule in [references/patterns.md](references/patterns.md).

## Resources

### references/

- **[references/hooks.md](references/hooks.md)** — Complete `Hooks` catalog: every hook name, its exact `(input, output)` signature, when it fires, mutate-vs-throw semantics, and a focused example. Also documents `PluginInput` (client/$/directory/worktree/project/serverUrl) and the SDK `event` types. **Load before writing any hook body.**
- **[references/custom-tools.md](references/custom-tools.md)** — The `tool()` API: zod args via `tool.schema`, `ToolContext` (sessionID/messageID/agent/abort/metadata/ask), `ToolResult` shapes (string / object / attachments), and idioms (return-guidance-not-throw, compact title via the returned `{title, output}` — `ctx.metadata` is a no-op for plugin tools). **Load when adding a `tool:` hook.**
- **[references/publishing.md](references/publishing.md)** — `package.json` fields, the three install paths (npm `plugin` array, local files in the plugin dir, local-clone shim), the **`plugin/` vs `plugins/` directory gotcha**, `.opencode/package.json` for tool dependencies, load order, and versioning. **Load when packaging, installing, or publishing.**
- **[references/patterns.md](references/patterns.md)** — Battle-tested patterns and gotchas from real plugins: logger binding, fire-and-forget init, `dispose` cleanup, single-instance servers, the `event` switch, cross-platform paths, env-var config, testability, and the verification rule. **Load while implementing.**

### assets/

- **[assets/template/](assets/template/)** — A complete, ready-to-rename minimal plugin (package.json, tsconfig.json, .gitignore, README.md, `src/plugin/index.ts`, `test/index.test.ts`). Copy it in step 2 of the workflow as the starting point.
