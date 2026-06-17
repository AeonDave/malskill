# Custom Tools — Reference

Custom tools are new actions the **model can call**. A plugin returns them under the `tool` hook. Each is built with the `tool()` helper from `@opencode-ai/plugin` (re-exported, also at `@opencode-ai/plugin/tool`).

## The `tool()` API

```ts
import { tool } from "@opencode-ai/plugin"
import type { ToolContext } from "@opencode-ai/plugin"

export function createMyTool() {
  return tool({
    description: "One clear sentence the model reads to decide when to call this.",
    args: {
      query: tool.schema.string().describe("What to look up. Be specific."),
      limit: tool.schema.number().int().min(1).max(100).optional().describe("Max results (default 10)."),
    },
    async execute(args, ctx: ToolContext) {
      // args is fully typed: { query: string; limit?: number }
      return `Found results for ${args.query}`
    },
  })
}
```

Wire it into the plugin:
```ts
const MyPlugin: Plugin = async (input) => {
  return {
    tool: {
      mytool: createMyTool(),        // model calls it as "mytool"
    },
  }
}
```

### `args` and `tool.schema`

`tool.schema` **is zod** (`tool.schema === z`). Build the arg shape with it:
- `tool.schema.string()`, `.number().int()`, `.boolean()`, `.enum([...])`, `.array(...)`, `.object({...})`
- `.optional()`, `.min()/.max()`, `.default(...)`
- **`.describe(...)` on every field** — the description is what the model uses to fill the argument correctly. Treat these descriptions as prompt engineering, not docs.

`args` is a zod **raw shape** (a plain object of schemas), not a wrapped `z.object(...)`. The helper wraps it for you; `execute` receives `z.infer` of the inferred object, so arguments are fully typed.

## `ToolContext`

The second argument to `execute`:

```ts
type ToolContext = {
  sessionID: string                 // current session
  messageID: string                 // current assistant message
  agent: string                     // agent name that invoked the tool
  directory: string                 // session project dir — prefer over process.cwd()
  worktree: string                  // git root — for stable relative paths
  abort: AbortSignal                // cancel long work when the user stops the turn
  metadata(input: { title?: string; metadata?: Record<string, any> }): void
  ask(input: { permission: string; patterns: string[]; always: string[]; metadata: Record<string, any> }): Promise<void>
}
```

- **`metadata({ title })`** — sets the compact one-line header the TUI shows for the tool call. Set it to avoid dumping every argument (including long prompts) into the transcript:
  ```ts
  ctx.metadata({ title: `${args.agent} · ${id}` })
  ```
- **`ask(...)`** — request a permission gate before a side effect.
- **`abort`** — honor it in loops / long fetches: `if (ctx.abort.aborted) return "Cancelled."`
- **`directory` / `worktree`** — resolve paths against these, not `process.cwd()`.

## `ToolResult` — what to return

```ts
type ToolResult =
  | string                                   // shorthand: becomes the output
  | {
      title?: string
      output: string                         // text the model sees
      metadata?: Record<string, any>
      attachments?: Array<{ type: "file"; mime: string; url: string; filename?: string }>
    }
```

- Return a **string** for the simple case.
- Return the **object** when you also want a title/metadata/attachments.
- **`attachments`** surface files (images, generated artifacts) back into the conversation.

## Idioms from real plugins

- **Return guidance, don't throw, for *expected* failures.** Inside `execute`, a thrown error becomes an exception; returning a clear error **string** lets the model recover. Validate inputs and return actionable text:
  ```ts
  if (!ctx?.sessionID) return "❌ This tool requires a sessionID. (System error.)"
  if (!model) return `❌ Invalid model "${args.model}". Expected "provider/model-id".`
  ```
  Reserve `throw` for truly unrecoverable states.
- **Keep the header compact.** Long-prompt tools should call `ctx.metadata({ title })` early so the transcript stays readable.
- **Empty args are fine.** `args: {}` with `execute(_args, ctx)` for tools that take no input (status/list tools).
- **Build tools in factories.** `createX(manager)` returning `tool({...})` keeps state (a manager/store) closed over and keeps `index.ts` thin.
- **Write rich `description`s.** Multi-line is fine; state *when to use*, *what it returns*, and *when not to* — the model reads it verbatim.

## External dependencies in tools

If a tool needs an npm package, it must be installable by OpenCode:
- **Published plugin:** declare it in the plugin's `package.json` `dependencies` (npm installs it into OpenCode's cache).
- **Local plugin:** add a `package.json` to the config dir (`.opencode/package.json` or `~/.config/opencode/package.json`) listing the dep; OpenCode runs `bun install` at startup. See [publishing.md](publishing.md).
