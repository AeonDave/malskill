---
name: opencode-plugin-creator
description: "Create or revise OpenCode plugins: server entrypoints, hooks, custom tools, lifecycle, installation, and packaging."
license: MIT
compatibility: "OpenCode CLI with Bun. Match @opencode-ai/plugin to the target host; bundled template targets OpenCode 1.18.35."
metadata:
  author: AeonDave
  version: "1.1"
---

# OpenCode Plugin Creator

Use [opencode-agent-creator](../opencode-agent-creator/SKILL.md) for agent definitions, permissions, and task delegation. Keep plugin mechanics here.

## Match the host before coding

Record `opencode --version` and the installed `@opencode-ai/plugin` version. This skill's template targets [OpenCode 1.18.35](https://github.com/anomalyco/opencode/releases/tag/v1.18.35), tag commit `53d1eabb61e21162157817bf677da0a4ad3332e3`.

Choose the API from the target package's exports and types. The released root import uses a `Plugin` function returning `Hooks`; its V2 Promise/Effect exports are different APIs. Current [V2 documentation](https://opencode.ai/v2/docs/build/plugins/) can describe fields absent from 1.18.35. Do not mix its examples into a V1 hook object.

For terminal UI behavior, load the [official CLI-plugin guide](https://opencode.ai/v2/docs/build/plugins/cli/) and the target host's [`@opencode-ai/plugin/tui` types](https://github.com/anomalyco/opencode/blob/53d1eabb61e21162157817bf677da0a4ad3332e3/packages/plugin/src/tui.ts). Use its distinct TUI entrypoint/API and package `./tui` export; match the guide's imports to the installed version rather than using server hooks for UI work.

## Build and verify

1. Load [references/hooks.md](references/hooks.md) when choosing an entrypoint or interception hook; check its host call site as well as its type.
2. Copy [assets/template/](assets/template/) into the target project. Set the package name and supported host range; pin the SDK/plugin version used for development.
3. Implement only the required hooks. Mutate the provided `output` fields in place. Load [references/custom-tools.md](references/custom-tools.md) when adding model-callable actions.
4. Load [references/patterns.md](references/patterns.md) for initialization, cancellation, logging, state ownership, or teardown.
5. Run the template's typecheck and tests in its own directory. Test the returned hooks and custom tool, including the blocked/error path.
6. Load [references/publishing.md](references/publishing.md) when installing or packaging. Start the matching host in an isolated project, confirm initialization, and exercise the intended behavior. Report unit/typecheck evidence separately from host execution.
7. Inspect the package contents before an authorized publication.

## Minimal server plugin

```ts
import type { Plugin, PluginModule } from "@opencode-ai/plugin"

const Guard: Plugin = async () => ({
  "tool.execute.before": async (input, output) => {
    if (input.tool === "read" && output.args.filePath === "blocked.txt")
      throw new Error("This read is blocked by the project guard.")
  },
})

export default { id: "example.guard", server: Guard } satisfies PluginModule
```

A guard for one tool is scoped to that tool. Set agent/config permissions for access policy; a type declaration alone does not establish that a permission hook runs.

The template exports one explicit server module. Keep helper functions in imported siblings rather than exporting them from a legacy plugin entrypoint.
