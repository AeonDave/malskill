# @you/opencode-myplugin

> Replace with a one-line description of what this plugin does.

A plugin for [OpenCode](https://github.com/sst/opencode).

## Installation

### From npm (recommended)

Add the package to the `plugin` array in your OpenCode config (`~/.config/opencode/opencode.json`):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["@you/opencode-myplugin@latest"]
}
```

OpenCode installs it automatically on next start. Pin a version with `@0.1.0`.

### From a local clone (shim)

```bash
git clone https://github.com/you/opencode-myplugin.git
cd opencode-myplugin && npm install
```

Create a re-export shim in your global plugin directory (use `plugin/` or `plugins/`
depending on your OpenCode version):

```ts
// ~/.config/opencode/plugins/myplugin.ts
export { default } from "/absolute/path/to/opencode-myplugin/src/plugin/index.ts"
// Windows: export { default } from "C:/path/to/opencode-myplugin/src/plugin/index.ts"
```

Restart OpenCode. Delete the shim to uninstall. Use one install method at a time.

## Configuration

Describe env vars and `opencode.json` plugin-options here. Delete this section if none.

## Development

```bash
npm install
npm run typecheck
npm test
```

## Disclaimer

This project is not built by the OpenCode team and is not affiliated with
[OpenCode](https://github.com/sst/opencode).

## License

MIT
