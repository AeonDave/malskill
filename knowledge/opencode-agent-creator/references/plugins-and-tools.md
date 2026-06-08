# Custom Tools, Plugins & Secrets

Extend an OpenCode team with deterministic tools, lifecycle plugins, and safe secret handling.

## Custom tools

Custom tools are TypeScript/JavaScript files the LLM can call like built-ins. They live in `~/.config/opencode/tools/*.ts` (global) or `.opencode/tools/*.ts` (project). The filename becomes the tool name; multiple exports become `<file>_<export>`.

Use a tool when an operation is deterministic and you want it cheaper/more reliable than an LLM doing it by hand (recursive web research, output parsing, API wrappers, redaction).

```ts
import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "What it does and when to use it (the LLM reads this).",
  args: {
    query: tool.schema.string().describe("..."),
    limit: tool.schema.number().default(8).describe("..."),
  },
  async execute(args, context) {
    // context: { agent, sessionID, messageID, directory, worktree }
    return "string result for the model"
  },
})
```

- Args use Zod via `tool.schema`; descriptions guide the model.
- The TS file can shell out to any language (e.g. `Bun.$\`python3 script.py ${arg}\``), so existing Python helpers can be wrapped.
- A custom tool with the same name as a built-in overrides it (useful to restrict `bash`).
- External npm deps: add a `package.json` in the config dir; OpenCode runs `bun install` at startup.

### Worked example — `deep-research` tool

A recursive web-research tool: discover sources (free Jina Search, optional Tavily), fetch pages via **Jina Reader** (`https://r.jina.ai/<url>`, free, clean markdown), follow links breadth-first to a depth, return aggregated content + sources for the agent to synthesize. Design notes that matter:

- **Cheapest fetcher first.** Jina Reader (free) as default; only call a paid API (Tavily) when a flag opts in — so paid quota is not burned by default.
- **Hard caps.** `max_pages` and `max_depth` bound cost; clamp them in code.
- **Per-page char cap.** Truncate each page so one huge page can't blow the context.
- **Return material, not conclusions.** The tool aggregates; the calling agent synthesizes and cites. This keeps the tool deterministic and the judgement with the model.
- **Env, not args, for keys.** Read `TAVILY_API_KEY` / optional `JINA_API_KEY` from `process.env`; never take secrets as tool args.

Point research-oriented agents at it in their prompts ("prefer the `deep-research` tool over many single searches; keep `max_pages` small").

## Plugins

Plugins are JS/TS modules that hook OpenCode lifecycle events. Load via the `plugin` array in `opencode.json` (npm names) or files in `~/.config/opencode/plugins/`.

```jsonc
{ "plugin": ["@scope/some-plugin", "opencode-mem"] }
```

```ts
import type { Plugin } from "@opencode-ai/plugin"
export const MyPlugin: Plugin = async ({ client, $, directory, worktree }) => ({
  "tool.execute.before": async (input, output) => { /* guard/transform */ },
  "session.idle": async () => { /* notify */ },
})
```

Common event hooks: `tool.execute.before/after`, `session.idle/created/compacted`, `file.edited`, `shell.env`, `experimental.session.compacting`. High-value plugins for a team:
- **Context pruning / dynamic context** — drops stale tool output to cut tokens (big win for the expensive supervisor).
- **Persistent memory** — cross-session memory store. Weigh privacy: it can retain scope/target data.

Evaluate plugins critically: a context-compression *proxy* that normalizes models can break per-agent model tiering — prefer native pruning plugins over proxies when your team relies on pinned models.

## Secrets

Never hardcode API keys/tokens in `opencode.json`. Use substitution:

```jsonc
{ "mcp": { "tavily": { "environment": { "TAVILY_API_KEY": "{env:TAVILY_API_KEY}" } } } }
```

- `{env:VAR}` reads an environment variable; `{file:~/.secrets/x}` reads file contents.
- Resolution happens at **startup, before plugins**, so the variable must exist in the environment first.
- OpenCode does **not** auto-load `.env` (it is an open feature request). So either set OS/user env vars, or load a `.env` yourself before launching.

### Reliable `.env` loading on Windows

`setx` truncates values over 1024 chars (a JWT can exceed that), so prefer a launcher that loads a `.env` into the process and then runs `opencode`:

```powershell
# opencode-env.ps1 — load sibling .env into the process, then launch opencode
param([Parameter(ValueFromRemainingArguments=$true)] $Args)
$envFile = Join-Path $PSScriptRoot '.env'
if (Test-Path $envFile) {
  foreach ($raw in Get-Content -LiteralPath $envFile) {
    $line = $raw.Trim(); if (-not $line -or $line.StartsWith('#')) { continue }
    $i = $line.IndexOf('='); if ($i -lt 1) { continue }
    [Environment]::SetEnvironmentVariable($line.Substring(0,$i).Trim(), $line.Substring($i+1).Trim(), 'Process')
  }
}
& opencode @Args
```

Then add a shell shortcut, e.g. `function oc { & "C:\path\to\opencode-env.ps1" @args }`. Keep the `.env` private (gitignore it if the config dir is ever a repo).
