# Packaging, Installing & Publishing — Reference

## `package.json` for a publishable plugin

The proven shape (from the real plugins). Key points: `type: "module"`, `main`/`exports` point at the **`.ts`** entry (Bun runs TS directly), `@opencode-ai/*` are **optional peer deps**, and the `opencode-plugin` keyword aids discovery.

```jsonc
{
  "name": "@you/opencode-myplugin",
  "version": "0.1.0",
  "description": "One-line summary of what it does.",
  "keywords": ["opencode", "opencode-plugin", "<feature-tags>"],
  "homepage": "https://github.com/you/opencode-myplugin#readme",
  "bugs": "https://github.com/you/opencode-myplugin/issues",
  "repository": { "type": "git", "url": "git+https://github.com/you/opencode-myplugin.git" },
  "license": "MIT",
  "type": "module",
  "main": "src/plugin/index.ts",
  "exports": { ".": "./src/plugin/index.ts" },
  "files": ["src", "README.md", "LICENSE"],
  "scripts": {
    "typecheck": "tsc --noEmit",
    "test": "bun test"
  },
  "peerDependencies": {
    "@opencode-ai/plugin": "*",
    "@opencode-ai/sdk": "*"
  },
  "peerDependenciesMeta": {
    "@opencode-ai/plugin": { "optional": true },
    "@opencode-ai/sdk": { "optional": true }
  },
  "devDependencies": {
    "@opencode-ai/plugin": "latest",
    "@opencode-ai/sdk": "latest",
    "@types/bun": "latest",
    "typescript": "latest"
  }
}
```

- **Peer + optional:** the host provides `@opencode-ai/plugin` at runtime; marking it an *optional* peer means consumers aren't forced to install it, while your dev environment pulls it via `devDependencies` for typing/tests.
- **Only need `@opencode-ai/sdk`** if you import its types (`Event`, `Project`, `Message`, …) or call typed client methods. The `dotenv` plugin omits it; `tokenomics` and `background-agents` use it.
- **Runtime `dependencies`** (e.g. `unique-names-generator`) go in `dependencies`, not dev — OpenCode installs them into its cache when the plugin loads from npm.
- **`files`** must include the `src` entry plus anything shipped (e.g. a built dashboard's `dist`). Don't ship `node_modules` or tests.

## Where plugins load from

OpenCode discovers plugins from these sources (this is also the **load order**; all hooks from all sources run in sequence):

1. Global config — `~/.config/opencode/opencode.json` (`plugin` array)
2. Project config — `./opencode.json` (`plugin` array)
3. Global plugin directory — `~/.config/opencode/plugins/`
4. Project plugin directory — `./.opencode/plugins/`

Files dropped in a plugin directory auto-load at startup. Duplicate npm packages (same name+version) load once; a local plugin and an npm plugin with similar names both load.

> **⚠️ `plugin/` vs `plugins/` gotcha.** The current official docs use the **plural** `plugins/` for both the project (`.opencode/plugins/`) and global (`~/.config/opencode/plugins/`) directories. Some OpenCode versions historically used the **singular** `plugin/` (and existing setups/shims may rely on it). If a local plugin isn't loading, try the other spelling and check your `opencode` version. When in doubt, prefer npm/`opencode.json` installs (below), which avoid the directory-name ambiguity entirely.

## Three ways to install

### 1. From npm (recommended for users)

Add the package to the `plugin` array in `opencode.json`:
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["@you/opencode-myplugin@latest"]
}
```
OpenCode installs it automatically with Bun on next start, caching to `~/.cache/opencode/node_modules/`. Pin a version with `@0.1.0` instead of `@latest`. Per-plugin options use the tuple form: `["@you/opencode-myplugin", { "key": "value" }]` (delivered as the plugin function's second `options` argument).

### 2. Local files (quick experiments)

Drop a `.ts`/`.js` file exporting a `Plugin` into the plugin directory (see the gotcha above for the exact name). It auto-loads. Good for one-off project plugins committed alongside the repo in `.opencode/plugins/`.

### 3. Local-clone shim (developing an unpublished plugin)

Re-export your working tree's entry point from a file in the global plugin directory so edits take effect on restart without publishing:

```ts
// ~/.config/opencode/plugins/myplugin.ts   (use the dir name your version expects)
export { default } from "/absolute/path/to/opencode-myplugin/src/plugin/index.ts"
```
On Windows use forward slashes **with the drive letter**:
```ts
export { default } from "C:/path/to/opencode-myplugin/src/plugin/index.ts"
```
Restart OpenCode; `src/` edits apply on the next restart. Delete the shim to uninstall. **Use one install method at a time** — remove the shim if you also add the npm entry, or the plugin loads twice.

## Dependencies for local plugins / custom tools

Local plugins (not installed from npm) can still use npm packages: add a `package.json` to the config directory and OpenCode runs `bun install` at startup.
```jsonc
// .opencode/package.json  (or ~/.config/opencode/package.json)
{ "dependencies": { "shescape": "^2.1.0" } }
```

## Versioning & publishing checklist

- `npm run typecheck` and `bun test` pass.
- Plugin **actually loads** in OpenCode and logs its startup line (see patterns.md verification rule).
- `README.md` documents install (npm + shim), config/env vars, and a **"not affiliated with OpenCode"** disclaimer if it's a third-party plugin.
- Bump `version`, then `npm publish` (use `--access public` for a first-time scoped package).
