# Package and install a server plugin

Use the [official plugin guide](https://opencode.ai/docs/plugins/) for supported config placement and the [1.18.35 loader](https://github.com/anomalyco/opencode/blob/53d1eabb61e21162157817bf677da0a4ad3332e3/packages/opencode/src/plugin/shared.ts) for entrypoint and compatibility behavior.

## Package contract

The template ships TypeScript for Bun. Keep `type: "module"`, include the entrypoint in `files`, and declare `main` plus `exports["./server"]`. The released server loader checks `./server` first, then `main`; a root export alone is insufficient.

Pin `@opencode-ai/plugin` to the version used in development. Importing `tool` is a runtime dependency, so include the plugin package in `dependencies`; a type-only import can stay a dev dependency. Declare other runtime imports as dependencies too. Add the SDK directly only when your code imports it.

Set `engines.opencode` to the host range actually supported. The template uses exact `1.18.35`; broaden it after corresponding host checks. This range is checked by the package loader for ordinary versioned hosts, not inferred from SDK peer dependencies.

Inspect `npm pack --dry-run`: ship required source/assets, omit tests, secrets, caches, and `node_modules`. Supply the promised license file before publishing.

## Install from config

For a published package:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [["@example/opencode-guard@0.1.0", { "enabled": true }]]
}
```

The options object is passed to the server function. Npm packages/dependencies install on startup. For local development, the config can reference a local path or `file://` URL; prefer a package directory with a declared server entrypoint.

Loose `.ts`/`.js` files can also live under `.opencode/plugins/` or `~/.config/opencode/plugins/`. The [released scanner](https://github.com/anomalyco/opencode/blob/53d1eabb61e21162157817bf677da0a4ad3332e3/packages/opencode/src/config/plugin.ts) accepts both `plugin/` and `plugins/`; use the documented plural form. Install external dependencies in that config directory's `package.json`.

For a shim, re-export only the default entrypoint:

```ts
export { default } from "/path/to/opencode-guard/src/plugin/index.ts"
```

Windows module paths require a drive-qualified path with forward slashes.

## Ordering and duplicate installs

The documented order is global config, project config, global plugin files, then project plugin files. The released config deduplicates npm origins by package name, with the later origin winning; different versions are not independent plugin identities. File origins use their exact URL. A shim and npm package remain distinct origins, so use one installation route for a plugin.

Keep server and TUI code separate when both are needed; TUI has its own `./tui` entrypoint/API. Do not call TUI-only APIs from a server hook.

## Release evidence

Before an authorized publication, verify the packaged entrypoint, supported host, installation route, target hook/tool behavior, and declared runtime dependencies. Record the exact package/host versions and what was exercised. Typecheck, tests, and archive inspection alone are not a host load check.
