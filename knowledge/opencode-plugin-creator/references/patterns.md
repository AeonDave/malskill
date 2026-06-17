# Patterns & Gotchas — Reference

Battle-tested idioms distilled from real OpenCode plugins. Apply these while implementing.

## 1. Thin entry, testable siblings

Keep `src/plugin/index.ts` to **wiring**: read config, construct a manager/store, return the `Hooks` object. Put real logic in sibling modules (`pricing.ts`, `aggregator.ts`, `substitute.ts`, `delegation-manager.ts`) and import it. This is what makes the plugin unit-testable — hook closures can't be tested directly, but the functions they call can. Tests target the siblings:
```ts
import { substituteConfig } from "../src/plugin/substitute"
test("rewrites placeholders", () => { expect(substituteConfig({ k: "${A}" })).toBe(1) })
```

## 2. Logging through the client (binding gotcha)

`client.app.log({ body: { service, level, message } })` writes to OpenCode's log. **Call it on the client object** — a detached reference (`const log = client.app.log`) loses the internal `this` binding and throws. Wrap it with a fallback:
```ts
function makeLog(client, service, silent) {
  return (level: "debug" | "info" | "warn" | "error", message: string) => {
    if (silent && level === "debug") return
    if (client?.app?.log) { client.app.log({ body: { service, level, message } }).catch(() => {}); return }
    console[level === "warn" || level === "error" ? "error" : "log"](`[${service}] ${message}`)
  }
}
```

## 3. Never block startup — fire-and-forget heavy init

The plugin function is awaited before sessions start. Anything slow (network calls, history backfill, state restore) must **not** be awaited inline:
```ts
const MyPlugin: Plugin = async (input) => {
  const mgr = new Manager(input.client)
  void mgr.restoreState()          // fire-and-forget; settles in the background
  void backfill(mgr).then(n => { if (n) console.log(`[svc] backfilled ${n}`) })
  return { /* hooks */ }
}
```

## 4. `dispose` releases resources

If the plugin opens a port, file watcher, timer, or child process, return a `dispose` that tears it down — config reloads re-run the plugin and would otherwise leak:
```ts
return { dispose: async () => { server?.stop(); watcher?.close() } }
```

## 5. Single-instance side effects

Multiple OpenCode windows load the plugin multiple times. For singletons (a web server on a fixed port), make the bind idempotent — try to listen, and if the port is taken, assume another instance owns it and skip rather than crash.

## 6. The `event` hook is a switch

One `event` hook receives all events. Branch on `event.type`; the `properties` shape is narrowed per type. Use cheap events as heartbeats and part events for content:
```ts
event: async ({ event }) => {
  switch (event.type) {
    case "session.idle": return onIdle(event.properties.sessionID)
    case "message.updated": return onMessage(event.properties.info)
    case "message.part.updated": return onPart(event.properties.part)
  }
}
```

## 7. Mutate `output`, never reassign

```ts
// ✅ push / assign fields
output.system.push(rule)
output.args.path = safePath
output.env.KEY = value
// ❌ ignored
output = { system: [rule] }
```
To **block** in `tool.execute.before` / `permission.ask` / `command.execute.before`, `throw` — the message is surfaced to the model/user.

## 8. Cross-platform

- Build paths with `node:path`; never hand-concatenate `/`.
- Resolve the home dir with `os.homedir()`; config lives at `~/.config/opencode` on every OS (including Windows).
- In shim re-exports, use **forward slashes with the drive letter** on Windows (`C:/path/to/...`).
- Don't assume `worktree` is a git root — non-git projects report `/`; fall back to `directory`.

## 9. Stable project identity

For state that must persist across worktrees/sessions of the same project, derive an ID from the git root commit (or fall back to a directory hash) rather than the volatile cwd. Store under `~/.local/share/opencode/<feature>/<projectId>/` or similar.

## 10. Config via env vars

Lightweight, dependency-free per-user config: read `process.env.MYPLUGIN_*` flags (truthy = `1`/`true`/`yes`/`on`). Document each in the README. Reserve `opencode.json` plugin-options (the function's 2nd `options` arg) for structured config.

## 11. `tsconfig.json` that matches the runtime

Bun runs the TS; the config only typechecks. Use Bundler resolution and Bun types:
```jsonc
{
  "compilerOptions": {
    "target": "ES2022", "module": "ESNext", "moduleResolution": "Bundler",
    "lib": ["ES2022"], "types": ["bun"], "strict": true, "noEmit": true,
    "esModuleInterop": true, "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true, "resolveJsonModule": true,
    "verbatimModuleSyntax": true
  },
  "include": ["src/**/*.ts"]
}
```
`verbatimModuleSyntax` forces `import type { Plugin }` for type-only imports — keep types and values separated.

## 12. Verification rule (do not skip)

A plugin that typechecks and passes unit tests can still fail to load (bad export, wrong hook key, runtime import error). **Before reporting success:**
1. `tsc --noEmit` clean.
2. `bun test` green.
3. Load it (shim or npm entry) and **start OpenCode**; confirm the plugin's startup log line appears and the target hook actually fires (trigger it and observe the effect).

Report what you verified and how. If you couldn't start OpenCode in this environment, say so explicitly — never claim a hook "works" on the strength of a typecheck alone.
