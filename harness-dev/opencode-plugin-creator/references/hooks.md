# Server hooks and entrypoints

Baseline: `@opencode-ai/plugin@1.18.35`. Use the [released types](https://github.com/anomalyco/opencode/blob/53d1eabb61e21162157817bf677da0a4ad3332e3/packages/plugin/src/index.ts) and [host dispatcher](https://github.com/anomalyco/opencode/blob/53d1eabb61e21162157817bf677da0a4ad3332e3/packages/opencode/src/plugin/index.ts) together.

## Entrypoint and context

`Plugin` is `(input: PluginInput, options?: Record<string, unknown>) => Promise<Hooks>`. Export a default `PluginModule` with `server: Plugin` and an optional stable `id`, or a legacy plugin function. Legacy entries inspect exported values; unrelated helper exports can fail loading.

`PluginInput` provides `client`, `project`, `directory`, `worktree`, `serverUrl`, Bun's `$`, and `experimental_workspace.register`. A configured `["package", { ... }]` tuple supplies the second `options` argument. Validate options before using them.

## Select the narrow hook

For exact parameter types, index the installed interface instead of hand-maintaining a signature:

```ts
import type { Hooks } from "@opencode-ai/plugin"

const before: NonNullable<Hooks["tool.execute.before"]> = async (input, output) => {
  if (input.tool === "read") output.args.filePath = "safe.txt"
}
```

| Behavior | V1 hook and writable output |
|---|---|
| Rewrite/block a tool call | `tool.execute.before`: `args`; throw rejects this operation |
| Rewrite completed tool output | `tool.execute.after`: `title`, `output`, `metadata` |
| Change model-visible tool definition | `tool.definition`: `description`, `parameters` |
| Handle a user message | `chat.message`: `message`, `parts` |
| Tune generation | `chat.params`: `temperature`, `topP`, `topK`, `maxOutputTokens`, `options` |
| Add provider HTTP headers | `chat.headers`: `headers` |
| Inject system text | `experimental.chat.system.transform`: `system` array |
| Rewrite outbound message history | `experimental.chat.messages.transform`: `messages` |
| Prepare a command | `command.execute.before`: `parts` |
| Supply shell environment | `shell.env`: `env` |
| Add compaction context/replace prompt | `experimental.session.compacting`: `context`, optional `prompt` |
| Skip synthetic post-compaction continuation | `experimental.compaction.autocontinue`: `enabled` |
| Rewrite completed text | `experimental.text.complete`: `text` |

The dispatcher awaits hooks sequentially and returns the same output object. Assign its fields or push to its arrays; reassigning the parameter or returning a replacement is ignored. Inspect the caller before relying on exception propagation for another hook.

`config` mutates the merged config; `event` receives SDK events; `dispose` releases resources. `tool`, `auth`, and `provider` register capabilities rather than intercepting an `(input, output)` operation. Read the installed `AuthHook`/`ProviderHook` types when adding an integration.

### Permission boundary

The V1 type still contains `permission.ask`, but the released [permission service](https://github.com/anomalyco/opencode/blob/53d1eabb61e21162157817bf677da0a4ad3332e3/packages/opencode/src/permission/index.ts) does not dispatch it. Do not implement policy enforcement by assuming it runs. Configure permissions through [opencode-agent-creator](../../opencode-agent-creator/SKILL.md); custom tools request a gate with `context.ask`.

## V2 work

Load the installed `@opencode-ai/plugin/v2/promise` or `/v2/effect` types when the project explicitly uses V2. In 1.18.35, Promise exports `define({ id, setup })`; its context exposes agent, aisdk, catalog, command, integration, plugin, reference, and skill domains. It does not expose the session/tool domains shown in newer V2 pages.

Use the [tagged V2 Promise context](https://github.com/anomalyco/opencode/blob/53d1eabb61e21162157817bf677da0a4ad3332e3/packages/plugin/src/v2/promise/context.ts) to select available transforms. Test against that host; do not translate hook names mechanically from the [migration guide](https://opencode.ai/v2/docs/build/plugins/migrate-v1).
