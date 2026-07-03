# OpenCode Plugin Hooks — Reference

Authoritative signatures from `@opencode-ai/plugin` (the `Hooks` interface and `PluginInput`). Hook keys that contain a `.` are **string-literal keys** — write them quoted (`"tool.execute.before"`), not camelCase.

## Contents

- [The plugin function & PluginInput](#the-plugin-function--plugininput)
- [Mutate-vs-throw rules](#mutate-vs-throw-rules)
- [Lifecycle & meta hooks](#lifecycle--meta-hooks): `dispose`, `event`, `config`
- [Tool hooks](#tool-hooks): `tool`, `tool.execute.before`, `tool.execute.after`, `tool.definition`
- [Chat / LLM hooks](#chat--llm-hooks): `chat.message`, `chat.params`, `chat.headers`
- [Permission & command hooks](#permission--command-hooks): `permission.ask`, `command.execute.before`, `shell.env`
- [Provider & auth hooks](#provider--auth-hooks): `provider`, `auth`
- [Experimental hooks](#experimental-hooks): system/messages transform, compaction, text.complete, small_model
- [SDK `event` types](#sdk-event-types)

---

## The plugin function & PluginInput

```ts
export type Plugin = (input: PluginInput, options?: PluginOptions) => Promise<Hooks>

export type PluginInput = {
  client: ReturnType<typeof createOpencodeClient>  // OpenCode SDK client (HTTP API)
  project: Project                                 // current project info
  directory: string                                // current working directory
  worktree: string                                 // git worktree root
  serverUrl: URL                                   // OpenCode server URL (>=1.17)
  $: BunShell                                      // Bun's shell API ($`cmd`)
  experimental_workspace: { register(type, adapter): void }
}
```

`options` is the second element of a `["pkg", { ...opts }]` entry in the `opencode.json` `plugin` array — use it for per-install config.

Notes on the inputs:
- **`client`** — call the OpenCode HTTP API: `client.app.log(...)`, session/message reads, prompt routes, etc. Always invoke methods **on the object** so the internal `this` binding survives.
- **`$`** — Bun shell. `` const out = await $`git rev-parse HEAD`.text() ``. Has `.quiet()`, `.nothrow()`, `.cwd()`, `.env()`, `.text()`, `.json()`, `.lines()`.
- **`directory` vs `worktree`** — `directory` is the cwd; `worktree` is the git root (stable for path math). Non-git projects can report `/` as worktree — fall back to `directory`.
- **`serverUrl`** — only on newer hosts (>=1.17). Treat as possibly `undefined` for back-compat: `const url = (input as { serverUrl?: URL }).serverUrl`.

## Mutate-vs-throw rules

Every hook (except `dispose`, `event`, `config`, and custom-tool `execute`) takes `(input, output)`:
- **`input`** is read-only context.
- **`output`** is a pre-populated object you **mutate in place**. Push to its arrays, set its fields. **Reassigning `output` or returning a value does nothing.**
- To **abort** an action (`tool.execute.before`, `permission.ask`, `command.execute.before`), **`throw`** — the thrown message is surfaced.

---

## Lifecycle & meta hooks

### `dispose`
```ts
dispose?: () => Promise<void>
```
Runs on plugin teardown (config reload, shutdown). Release ports, file watchers, timers, intervals. Without it, servers/watchers leak across reloads.
```ts
return { dispose: async () => { server?.stop() } }
```

### `event`
```ts
event?: (input: { event: Event }) => Promise<void>
```
Fires for **every** OpenCode event. Switch on `event.type` and read `event.properties`. This is the main read-only firehose for session/message/tool activity. See [SDK event types](#sdk-event-types).
```ts
event: async ({ event }) => {
  if (event.type === "session.idle") { /* event.properties.sessionID */ }
  if (event.type === "message.part.updated") { /* event.properties.part */ }
}
```

### `config`
```ts
config?: (input: Config) => Promise<void>
```
Receives the **merged** config object (after all sources combine). Mutate it in place — e.g. rewrite placeholders, inject defaults, register MCP servers. Runs after plugin init but before the config is consumed.
```ts
config: async (config) => { /* mutate config.* in place */ }
```

---

## Tool hooks

### `tool` (register custom tools)
```ts
tool?: { [name: string]: ToolDefinition }
```
Each entry is built with `tool({ description, args, execute })`. The model can then call `name`. Full API in [custom-tools.md](custom-tools.md).

### `tool.execute.before`
```ts
"tool.execute.before"?: (
  input: { tool: string; sessionID: string; callID: string },
  output: { args: any },
) => Promise<void>
```
Runs before a tool executes. **Mutate `output.args`** to rewrite arguments, or **`throw`** to block the call. Classic guard:
```ts
"tool.execute.before": async (input, output) => {
  if (input.tool === "read" && String(output.args.filePath).includes(".env"))
    throw new Error("Refusing to read .env files")
}
```

### `tool.execute.after`
```ts
"tool.execute.after"?: (
  input: { tool: string; sessionID: string; callID: string; args: any },
  output: { title: string; output: string; metadata: any },
) => Promise<void>
```
Runs after a tool finishes. Inspect or rewrite the result the model sees (`output.output`), the TUI title, or metadata.

### `tool.definition`
```ts
"tool.definition"?: (
  input: { toolID: string },
  output: { description: string; parameters: any },
) => Promise<void>
```
Modify the description/parameters of a tool **as presented to the model**.

---

## Chat / LLM hooks

### `chat.message`
```ts
"chat.message"?: (
  input: { sessionID: string; agent?: string; model?: { providerID: string; modelID: string }; messageID?: string; variant?: string },
  output: { message: UserMessage; parts: Part[] },
) => Promise<void>
```
Fires when a new user message arrives. Read or mutate `output.message` / `output.parts` (e.g. append context parts to the user's turn).

### `chat.params`
```ts
"chat.params"?: (
  input: { sessionID: string; agent: string; model: Model; provider: ProviderContext; message: UserMessage },
  output: { temperature: number; topP: number; topK: number; maxOutputTokens: number | undefined; options: Record<string, any> },
) => Promise<void>
```
Tune sampling params and provider-specific `options` before the request.

### `chat.headers`
```ts
"chat.headers"?: (
  input: { sessionID: string; agent: string; model: Model; provider: ProviderContext; message: UserMessage },
  output: { headers: Record<string, string> },
) => Promise<void>
```
Add/override HTTP headers on the provider request (telemetry, gateway routing, custom auth).

---

## Permission & command hooks

### `permission.ask`
```ts
"permission.ask"?: (
  input: Permission,
  output: { status: "ask" | "deny" | "allow" },
) => Promise<void>
```
Intercept a permission prompt. Set `output.status` to `"allow"` or `"deny"` to decide automatically, or leave `"ask"` to defer to the user. (You may also `throw` to hard-block.)

### `command.execute.before`
```ts
"command.execute.before"?: (
  input: { command: string; sessionID: string; arguments: string },
  output: { parts: Part[] },
) => Promise<void>
```
Runs before a slash command executes; mutate `output.parts` or `throw` to block.

### `shell.env`
```ts
"shell.env"?: (
  input: { cwd: string; sessionID?: string; callID?: string },
  output: { env: Record<string, string> },
) => Promise<void>
```
Inject environment variables into the `bash` tool and user terminals. Write to `output.env`. Respect existing values unless you intend an override:
```ts
"shell.env": async (_input, output) => {
  if (output.env.API_KEY === undefined) output.env.API_KEY = loaded.API_KEY
}
```

---

## Provider & auth hooks

### `provider`
```ts
provider?: {
  id: string
  models?: (provider, ctx: { auth?: Auth }) => Promise<Record<string, Model>>
}
```
Register/augment a provider and return a dynamic model map. Use for custom or gateway providers whose model list is fetched at runtime.

### `auth`
```ts
auth?: {
  provider: string
  loader?: (auth, provider) => Promise<Record<string, any>>
  methods: Array<OAuthMethod | ApiKeyMethod>  // type: "oauth" | "api"
}
```
Add a custom authentication method for a provider. `methods` support `prompts` (text/select, with `when` rules) and an `authorize()` that returns success (with `refresh`/`access`/`expires` or `key`) or failure. See the `AuthHook`/`AuthOAuthResult` types in the package for the full shape; reach for this only when integrating a new provider's login flow.

---

## Experimental hooks

Namespaced under `experimental.*`. Stable enough to use in real plugins (the bundled examples rely on them), but the host may evolve them.

### `experimental.chat.system.transform`
```ts
"experimental.chat.system.transform"?: (
  input: { sessionID?: string; model: Model },
  output: { system: string[] },
) => Promise<void>
```
Inject text into the system prompt — **push** to `output.system`:
```ts
"experimental.chat.system.transform": async (_input, output) => {
  output.system.push("Project rule: always run the linter before finishing.")
}
```

### `experimental.chat.messages.transform`
```ts
"experimental.chat.messages.transform"?: (
  input: {},
  output: { messages: { info: Message; parts: Part[] }[] },
) => Promise<void>
```
Rewrite the full message array sent to the model (filter, redact, reorder, summarize).

### `experimental.session.compacting`
```ts
"experimental.session.compacting"?: (
  input: { sessionID: string },
  output: { context: string[]; prompt?: string },
) => Promise<void>
```
Before compaction: **push** strings to `output.context` to carry information through, or set `output.prompt` to replace the compaction prompt entirely. Used to preserve plugin state (e.g. running background tasks) across context loss.

### `experimental.compaction.autocontinue`
```ts
"experimental.compaction.autocontinue"?: (
  input: { sessionID: string; agent: string; model: Model; provider: ProviderContext; message: UserMessage; overflow: boolean },
  output: { enabled: boolean },
) => Promise<void>
```
Set `output.enabled = false` to skip the synthetic "continue" user turn after compaction.

### `experimental.text.complete`
```ts
"experimental.text.complete"?: (
  input: { sessionID: string; messageID: string; partID: string },
  output: { text: string },
) => Promise<void>
```
Post-process a completed assistant text part — rewrite `output.text`.

### `experimental.provider.small_model`
```ts
"experimental.provider.small_model"?: (
  input: { provider },
  output: { model?: Model },
) => Promise<void>
```
Choose the small/cheap model the host uses for auxiliary work (titles, summaries).

---

## SDK `event` types

The `event` hook's `event.type` is the discriminant of the SDK `Event` union (`import type { Event } from "@opencode-ai/sdk"`). `event.properties` is typed per variant. Commonly used types:

| `event.type` | Key `properties` | Typical use |
|---|---|---|
| `session.created`, `session.updated` | `info` (id, parentID, title, directory) | track sessions |
| `session.idle` | `sessionID` | session finished a turn |
| `session.status` | `sessionID`, `status.type` | detect idle/working transitions |
| `session.compacted`, `session.deleted`, `session.error` | `sessionID` | react to session lifecycle |
| `message.updated` | `info` (role, sessionID, tokens, cost) | per-message accounting; heartbeat |
| `message.part.updated` | `part` (type: text/tool/agent/retry/…) | live token/tool tracking |
| `message.part.removed`, `message.removed` | ids | reconcile state |
| `file.edited`, `file.watcher.updated` | path | watch edits |
| `permission.asked`, `permission.replied` | permission info | audit permissions |
| `todo.updated` | session todos | mirror the todo list |
| `command.executed` | command info | observe slash commands |
| `lsp.client.diagnostics`, `lsp.updated` | diagnostics | surface LSP state |
| `installation.updated`, `server.connected` | — | host lifecycle |

For a tool part: `part.state.status` is `"completed" | "error" | ...`, with `part.state.output`, `part.state.time.{start,end}`, `part.tool`, `part.callID`, `part.sessionID`.

> **Plugin hooks ≠ SDK events.** The `Hooks` interface above is the contract a plugin implements. The names in this table are values of `event.type` you switch on **inside** the single `event` hook — they are not themselves hook keys.
