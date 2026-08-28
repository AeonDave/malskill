# Pi Package And Release Guide

## Table of Contents

- [Install Modes](#install-modes)
- [Package Layout](#package-layout)
- [Manifest](#manifest)
- [Dependencies](#dependencies)
- [Settings And Filtering](#settings-and-filtering)
- [Validation](#validation)
- [Release Checklist](#release-checklist)

## Install Modes

Use local quick test:

```bash
pi -e ./src/index.ts
pi -e ./package-dir
```

Use auto-discovery during development:

```text
~/.pi/agent/extensions/*.ts
~/.pi/agent/extensions/*/index.ts
.pi/extensions/*.ts
.pi/extensions/*/index.ts
```

Use installable packages:

```bash
pi install ./package-dir
pi install git:github.com/user/repo@v1.0.0
pi install npm:@scope/package@1.0.0
```

Project installs use `pi install -l` and write `.pi/settings.json`. Project-local resources load after the project is trusted.

## Package Layout

Simple package:

```text
my-pi-extension/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts
│   ├── config.ts
│   └── policy.ts
└── test/
    └── policy.test.ts
```

Conventional multi-resource package:

```text
my-pi-package/
├── package.json
├── extensions/
│   └── index.ts
├── skills/
│   └── my-skill/SKILL.md
├── prompts/
│   └── review.md
└── themes/
    └── theme.json
```

If no `pi` manifest exists, Pi auto-discovers conventional `extensions/`, `skills/`, `prompts/`, and `themes/` directories.

## Manifest

Explicit manifest:

```json
{
  "name": "my-pi-extension",
  "version": "0.1.0",
  "type": "module",
  "main": "src/index.ts",
  "files": ["src", "README.md", "LICENSE"],
  "keywords": ["pi-package", "pi"],
  "pi": {
    "extensions": ["./src/index.ts"],
    "skills": ["./skills"],
    "prompts": ["./prompts"],
    "themes": ["./themes"]
  }
}
```

Paths are relative to package root. Arrays may use globs and exclusions.

Use `pi.image` or `pi.video` metadata only when preparing a package-gallery presentation.

## Dependencies

Pi-provided packages belong in `peerDependencies`:

```json
{
  "peerDependencies": {
    "@earendil-works/pi-ai": "*",
    "@earendil-works/pi-agent-core": "*",
    "@earendil-works/pi-coding-agent": "*",
    "@earendil-works/pi-tui": "*",
    "typebox": "*"
  }
}
```

Runtime packages your extension imports belong in `dependencies`.

Development-only test/typecheck packages belong in `devDependencies`.

To ship a third-party package that itself contributes Pi resources, add it to `dependencies` and `bundledDependencies`, then reference its resources through `node_modules/<pkg>/...` paths in the `pi` manifest:

```json
{
  "dependencies": { "helper-package": "^1.0.0" },
  "bundledDependencies": ["helper-package"],
  "pi": {
    "extensions": ["extensions", "node_modules/helper-package/extensions"],
    "skills": ["skills", "node_modules/helper-package/skills"]
  }
}
```

For git/npm installs, Pi runs npm install for packages with `package.json`. Make postinstall scripts deterministic and safe; avoid surprise network work beyond normal package installation.

If the extension shells out to an external binary:

- Resolve it from config, PATH, or bundled dependency.
- Add a diagnostic command that reports the resolved path.
- Time out probes.
- Redact secrets.
- Fail with actionable installation guidance.

## Settings And Filtering

Settings can include packages and direct extensions:

```json
{
  "packages": [
    "npm:my-pi-package",
    {
      "source": "git:github.com/user/repo@v1.0.0",
      "extensions": ["src/index.ts", "!src/legacy.ts"],
      "skills": []
    }
  ],
  "extensions": [
    "/path/to/local/extension.ts",
    "/path/to/local/extension-dir"
  ]
}
```

Filtering rules:

- Omitted resource key: load all allowed resources of that type.
- Empty array: load none of that type.
- `!pattern`: exclude glob match.
- `+path`: force include exact path.
- `-path`: force exclude exact path.

Local relative paths are resolved from the settings file directory.

## Validation

Minimum checks:

```bash
npm install
npm run typecheck
npm test
pi -e .
```

For a single `.ts` file:

```bash
pi -e ./extension.ts
```

For auto-discovery:

1. Place the file under `~/.pi/agent/extensions/` or `.pi/extensions/`.
2. Start Pi or run `/reload`.
3. Confirm the tool/command/event behavior, not only TypeScript success.

For packages:

1. Install locally with `pi install ./package-dir`.
2. Confirm settings entry is correct.
3. Start Pi from a clean shell.
4. Confirm dependencies resolve without dev dependencies.
5. Test project-local install with `pi install -l ./package-dir` if teams will share it.

## Release Checklist

- `package.json` `name`, `version`, `description`, `license`, `repository`, `keywords`, `files`, and `pi` manifest are correct.
- Public package includes `pi-package` keyword.
- Current imports use `@earendil-works/*` unless maintaining older code.
- Runtime imports are in `dependencies` or Pi peer dependencies.
- Pure logic has tests.
- `tsc --noEmit` passes.
- `pi -e .` or `pi install .` was verified.
- README install command matches source type.
- Configuration examples avoid secrets.
- Non-interactive mode behavior is documented.
