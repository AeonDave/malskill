# Codemode, MCP, and Tool Orchestration

Load this when the task involves codemode scripts, MCP servers, tool exposure (`direct`/`codemode`/`deferred`/`hidden`), tool search, nested tool calls (`ctx.executeTool`), namespaces/annotations, `prepareLoadout`, or wiring these into the SDK. For the base tool-definition contract (parameters, `content`/`details`, rendering), use [api-surface.md](api-surface.md).

## Contents

- [Built-in extensions](#built-in-extensions)
- [Tool exposure](#tool-exposure)
- [Nested tool calls](#nested-tool-calls)
- [Structured tool output](#structured-tool-output)
- [Codemode runtime](#codemode-runtime)
- [Tool search](#tool-search)
- [MCP servers](#mcp-servers)
- [Register MCP servers from an extension](#register-mcp-servers-from-an-extension)
- [SDK wiring](#sdk-wiring)

## Built-in extensions

The built-in extensions are `codemode`, `tool-search`, `mcp`, and `llama.cpp`. They add the `codemode` and `tool_search` tools, MCP connectivity, and the llama.cpp provider. They are named `builtin:<name>` (for example `builtin:tool-search`) in errors, diagnostics, RPC source info, and bug reports.

- Disable globally or per project in the Built-in section of `pi config`, or set `"extensions": ["-builtin:mcp"]` in [settings](https://pi.dev/docs/latest/settings).
- `--no-extensions` (`-ne`) also disables built-ins. Load one explicitly with `-e builtin:<name>`; `pi -ne -e builtin:mcp` keeps only built-in MCP.
- SDK sessions do not load them (see [SDK wiring](#sdk-wiring)).
- Registering a tool/command/flag named `codemode`, `tool_search`, or `/mcp` replaces the matching built-in and emits a warning.

## Tool exposure

`exposure` on a tool definition controls how the model reaches it. "Callable" means reachable from other tools through `ctx.executeTool()` (listed in `ctx.tools`), as codemode scripts do.

| `exposure` | Declared to model | Callable | Notes |
|---|---|---|---|
| `direct` (default) | while active | while active | Normal tool. Registering activates it. |
| `model-only` | while active | never | For tools that orchestrate other tools or ask the user. Registering activates it. |
| `codemode` | only if activated | whenever registered | Listed by the `codemode` tool. Not activated on registration. |
| `deferred` | only if activated | whenever registered | Like `codemode`, but codemode tools do not list it; `tool_search` can find and activate it. |
| `hidden` | never | never | Registered but unreachable. Re-register a tool with `exposure: "hidden"` to withdraw it (tools cannot be unregistered). |

- The active set is the tools declared to the model: `pi.getActiveTools()` / `pi.setActiveTools(names)`. Unknown names are ignored.
- `pi.getAllTools()` returns each tool's `exposure`, `namespace`, and `annotations`.
- `namespace: { name, description, instructions }` groups related tools, as MCP servers do. Codemode lists a namespace under one heading with its `description`; `instructions` is longer guidance that is not listed and is read by scripts with `describeNamespace(name)`.
- `annotations` are unverified MCP-style hints — `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`. Missing hints take MCP defaults (not read-only, possibly destructive, open world). Permission gates can read them from `pi.getAllTools()` to decide which calls to confirm.

### `prepareLoadout`

A tool that orchestrates others can adjust what the model sees while it is active with `prepareLoadout(loadout)`. It runs whenever the active tools change and receives the declared tools, the callable tools, and every registered tool with its exposure and namespace. It returns replacement `descriptions` for declared tools (including its own) and `hiddenDeclarations` (active tools whose declarations are omitted while they stay active and callable). `codemode` and `tool_search` use only this hook, `exposure`, and `ctx.executeTool()`, so another tool can reimplement that behavior under a different name.

## Nested tool calls

`ctx.executeTool(name, args, { signal, onUpdate })` runs another tool from inside a tool's `execute()`.

- Nested calls pass argument validation and the `tool_call` / `tool_result` handlers like model-issued calls, and emit `tool_execution_start`, `tool_execution_update`, and `tool_execution_end`. All carry `parentToolCallId`; their `toolCallId` is `<parent id>/<n>`.
- Results reach only the calling tool, not the transcript. The calling tool reports them itself (for example through `onUpdate` and `details`).
- The session keeps a bounded `nestedCalls` record on the calling tool's result message: name, arguments, status, duration, error — never results. Arguments over 8 KiB per call or 32 KiB per tool result are omitted, at most 256 calls are kept, and `complete: false` marks a truncated record.
- The `usage` of nested results at every depth is added to the calling tool's result `usage`, so a tool reports only its own usage.
- `ctx.tools` lists the tools `ctx.executeTool()` can call. A `tool_result` handler that redacts `content` should also replace `structuredContent`.

## Structured tool output

Declare `outputSchema` and return a matching `structuredContent` when the result is data:

- The model still receives `content`; programmatic callers such as codemode scripts receive `structuredContent` instead of the text.
- Tools without `outputSchema` are passed to scripts as their text `content`.
- To report a failure that still carries data, return the result with `isError: true` instead of throwing: the model sees an error, and scripts still receive `structuredContent`.

## Codemode runtime

The `codemode` tool runs model-written JavaScript in a QuickJS sandbox that can reach only the other tools. Enable it without MCP by adding `"defaultTools": ["+codemode"]` to [settings](https://pi.dev/docs/latest/settings), or list it in `--tools` (which replaces the whole selection). To prevent automatic activation when an MCP server connects, set `"autoEnableCodemode": false` beside `mcpServers`.

Scripts call tools and emit output:

- `tools.<name>(args)` calls a tool; `ALL_TOOLS` lists callable tools.
- Output comes from `text(value)`, `image(dataUrlOrImageContent)`, `console.*`, and a top-level `return value`; `exit()` ends the script early.
- A first-line `// @options: {"max_output_tokens": 2000, "timeout_ms": 60000}` tunes the run. `max_output_tokens` (default 10000) keeps the output's start and end and writes the full text to a temp file named in the result. `timeout_ms` is a hard deadline, unset by default.
- `codemode.mode` in settings: `on` (default) keeps declared tools declared with call instructions; `only` hides them from the model and lists them in the `codemode` description.

Tool discovery inside scripts:

- The `codemode` description lists callable tools as TypeScript declarations grouped by namespace, under a 3000-token budget (`codemode.inlineBudget`). `deferred`-exposure tools (including MCP tools with the default `codemode` exposure) are not listed; only their namespace and description are.
- `await searchTools(query, { limit, namespace })` ranks tools with BM25; `await describeTool(name)` returns one; filter `ALL_TOOLS` directly.
- `await describeNamespace(name)` returns a namespace's description, its instructions (an MCP server's instructions), and its tool names. For MCP use `describeNamespace("mcp__<server>")`.

Structured results in scripts:

- Tools with an `outputSchema` resolve to structured values: `bash` to `{ output, truncated, full_output_path?, exit_code, wall_time_seconds }` (also for non-zero exit), MCP tools to their `CallToolResult`. Others resolve to text.
- The `bash` `output` holds up to 1 MiB (not the model-facing 2000 lines / 50 KB); longer output keeps its first and last 512 KiB with `truncated` set.
- `store(key, value)` and `load(key)` keep JSON values across `codemode` calls; a storing script appends a `codemode-store` entry, so values survive resume and are branch-scoped. One value holds at most 262144 characters of JSON, all values at most 1048576.
- `models.getModelsOfType`, `getAvailableOfType`, and `getModelOfType` list the catalog; `models.classify(model, context)` runs a classifier and `models.generateImages(model, context)` runs an image model, both with the session's credentials (at most four such calls concurrent per script). Show returned images with `image()`. Their usage is added to the codemode tool result and session cost.

## Tool search

`tool_search` is off by default; enable it with `"defaultTools": ["+tool_search"]` or `--tools`. It ranks tools that are not declared yet (the same ranking as `searchTools()`) and declares the matches for the next model call. Loaded tools are recorded in the session like other tool changes, so they stay declared on that branch.

## MCP servers

Pi connects to MCP servers over stdio or streamable HTTP (the legacy SSE transport is rejected) and exposes their tools as `mcp__<server>__<tool>`.

### Configuration

User servers live in `~/.pi/agent/mcp.json`, project servers in `.pi/mcp.json` (read only after [project trust](https://pi.dev/docs/latest/security); a project entry replaces a same-named user entry). The file matches other MCP clients:

```json
{
  "mcpServers": {
    "filesystem": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "."] },
    "docs": {
      "url": "https://example.com/mcp",
      "headers": { "Authorization": "Bearer ${DOCS_TOKEN}" },
      "description": "Search and read the product documentation",
      "exposure": "codemode"
    }
  }
}
```

- stdio uses `command`, `args`, `env`, `cwd`; HTTP uses `url`, `headers`, `oauth`. Both support `timeout` (seconds, default 60), `enabled: false`, `exposure`, `toolExposure`, and `description`.
- Server names allow only letters, digits, `_`, and `-`. `type` is optional (`command` selects stdio, `url` selects HTTP).
- `env` and `headers` values accept `${VAR}` or a whole-value `!command` (for example `"!echo Bearer $(gh auth token)"`).
- `description` is shown next to the server in the `codemode` and `tool_search` descriptions, so the model knows what to search for.

### CLI and session commands

- Shell (no session, no extensions loaded): `pi mcp add|remove|list|login|logout`. `pi mcp add <server> [--env K=V] [--cwd dir] [--exposure mode] [--description text] [-l] -- <command> [args...]` for stdio; `--url`, `--header K=V`, `--bearer-token-env-var NAME`, and `--oauth-*` for HTTP. `pi mcp list` connects to every enabled server and exits 1 on an invalid entry or a failed connection.
- In session: `/mcp` inspects connections, signs in, reconnects, changes exposure, and enables/disables servers. Run `/reload` after editing `mcp.json` outside the session.
- OAuth tokens are stored in `~/.pi/agent/mcp-auth.json`; `oauth` accepts `clientId`, `clientSecret`, `callbackPort`, `callbackUrl`, `scope`, and `clientName`.

### Exposure

A server's `exposure` uses the same model as [tool exposure](#tool-exposure): `codemode` (default — callable from codemode scripts, server listed with its `description`), `deferred` (declared only after `tool_search` loads a match), `direct` (declared like a built-in and callable from codemode), or `hidden`. `toolExposure` overrides per tool with exact names or `*` patterns (exact wins; among patterns, first match wins):

```json
{
  "mcpServers": {
    "github": {
      "url": "https://api.githubcopilot.com/mcp/",
      "exposure": "deferred",
      "toolExposure": { "search_code": "direct", "get_*": "codemode", "delete_*": "hidden" }
    }
  }
}
```

Resource-bearing servers add `list_mcp_resources`, `list_mcp_resource_templates`, and `read_mcp_resource`. Every MCP call passes through Pi's tool pipeline, so `tool_call`/`tool_result` handlers and permission gates apply; codemode-issued MCP calls carry the codemode call ID as `parentToolCallId`.

## Register MCP servers from an extension

`pi.registerMcpServer(name, config)` adds a server for the current session. `config` has the `mcpServers` entry shape plus `exposure`, `toolExposure`, `description`, `enabled`, and `timeout`:

```typescript
pi.registerMcpServer("jira", { url: "https://mcp.example.com/jira", exposure: "codemode" });
pi.unregisterMcpServer("jira");
```

- Servers registered during load connect at `session_start`; later registrations connect immediately. `unregisterMcpServer()` closes the connection.
- Registrations are not saved — register again on every load (for example from the extension's own settings).
- A file-configured server with the same name takes precedence; `/mcp` shows the override. Re-registering a name replaces the earlier registration; names owned by another extension, invalid names, and invalid configs throw.
- The built-in MCP support connects registered servers. If another extension replaced it, each registration is reported as an extension error. A replacement MCP extension reads servers with `pi.getMcpServers()` on `session_start` and handles the `mcp_servers_change` event for later changes.

## SDK wiring

SDK sessions do not load built-in extensions. Add `createCodemodeExtension()`, `createToolSearchExtension()`, and `createMcpExtension()` to the `extensionFactories` of `DefaultResourceLoader`. `codemode` and `tool_search` register inactive — enable them with `defaultTools` (`["+codemode", "+tool_search"]` keeps the other defaults) or let the MCP extension activate them (`codemode` for servers with `codemode` exposure, `tool_search` for `deferred`). The MCP extension connects its servers on `session_start`, so call `session.bindExtensions()`. See `examples/sdk/14-codemode-mcp.ts` in the Pi repo.
