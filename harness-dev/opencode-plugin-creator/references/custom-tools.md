# Custom model-callable tools

Use this reference for the V1 `tool` map. Baseline: [tool types](https://github.com/anomalyco/opencode/blob/53d1eabb61e21162157817bf677da0a4ad3332e3/packages/plugin/src/tool.ts) and [registry adapter](https://github.com/anomalyco/opencode/blob/53d1eabb61e21162157817bf677da0a4ad3332e3/packages/opencode/src/tool/registry.ts) in 1.18.35.

```ts
import { tool } from "@opencode-ai/plugin"

const lookup = tool({
  description: "Return a bounded result for a project query.",
  args: {
    query: tool.schema.string().min(1).describe("Project query."),
    limit: tool.schema.number().int().min(1).max(20).default(5),
  },
  async execute(args, context) {
    context.abort.throwIfAborted()
    return { title: "Project lookup", output: args.query }
  },
})
```

Return it under `{ tool: { project_lookup: lookup } }`. Use a distinctive tool name; a matching custom name can replace a built-in tool.

## Arguments and context

`args` is a Zod raw shape, not `z.object(...)`. `tool.schema` is the package's Zod value. Describe fields only where it helps the model provide the correct input; constrain size and allowed values in the schema.

The execution context includes `sessionID`, `messageID`, `agent`, `directory`, `worktree`, `abort`, `metadata`, and `ask`. Resolve project-relative paths from `directory`; check whether `worktree` is suitable before using it for repository identity. Pass `abort` into cancellable operations.

Before a tool's side effect, await a gate using the operation's actual resource patterns:

```ts
await context.ask({
  permission: "edit",
  patterns: [targetPath],
  always: [targetPath],
  metadata: { targetPath },
})
```

The host bridges `ask` into a Promise. Do not swallow a denied permission and continue the operation.

## Results and failure

Return a string, or:

```ts
{
  title: "Compact result title",
  output: "Text supplied to the model",
  metadata: { count: 3 },
  attachments: [{ type: "file", mime: "text/plain", url: artifactUrl, filename: "result.txt" }],
}
```

Only `output` is required in the object. In the 1.18.35 plugin adapter, final title/metadata come from this result; `context.metadata()` is not bridged like `ask`, so do not depend on it for plugin tool updates. Return a compact title when arguments or output are large. The host may truncate output and add truncation metadata.

Return actionable guidance for expected lookup/input failures. Throw for denied operations, cancellation, or failures that should mark the tool call unsuccessful. Do not report failed side effects as success.

For runtime npm imports, declare dependencies in the plugin package. For a local loose file, place dependencies in the relevant OpenCode config directory's `package.json`; see [publishing.md](publishing.md).
