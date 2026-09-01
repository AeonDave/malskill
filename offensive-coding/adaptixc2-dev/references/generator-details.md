# axtool & Spec Reference

Full field reference for `axtool.spec` (package spec) and `adaptix.spec` (project spec), plus `axtool` CLI commands for scaffolding, building, and installing extenders.

---

## Table of Contents
1. [axtool CLI Commands](#axtool-cli-commands)
2. [adaptix.spec — Project Spec](#adaptixspec--project-spec)
3. [axtool.spec — Package Spec](#axtoolspec--package-spec)
4. [Install State](#install-state)
5. [Template Placeholder System](#template-placeholder-system)

---

## axtool CLI Commands

```bash
# Scaffold from templates-extender (fetches github.com/Adaptix-Framework/templates-extender@main by default)
axtool template agent   <name> [--from <src>]
axtool template listener <name> [--from <src>] [--protocol <proto>]
axtool template service  <name> [--from <src>]
axtool template axscript <name> [--from <src>]
# --from: local path or github.com/org/repo@ref
# If name omitted, uses current directory name
# Creates <name>/ with: axtool.spec, config.yaml, go.mod, Makefile, pl_main.go, ax_config.axs

# Extender management (requires adaptix.spec path or project root as first arg)
axtool adaptix.spec ext install                        # install all packages: in adaptix.spec
axtool adaptix.spec ext install github.com/org/repo@v1 # install a remote package
axtool adaptix.spec ext install ./path/to/pkg          # install from local path
axtool adaptix.spec ext install <src> --name <extname> # install one extender from multi-item repo
axtool adaptix.spec ext install -d                     # also install apt deps
axtool adaptix.spec ext install --from packages.yaml   # install from a packages file
axtool adaptix.spec ext list                           # list installed extenders
axtool adaptix.spec ext uninstall <name>               # uninstall an extender

# Server
axtool adaptix.spec server build                       # build all packages + server binary
axtool adaptix.spec server build -d                    # also install apt deps
axtool adaptix.spec server daemon install              # install systemd unit
axtool adaptix.spec server daemon start|stop|restart

# Client
axtool adaptix.spec client build
axtool adaptix.spec client build -d
```

### What `ext install` does

1. Clones / copies source into `server_dir/plugin_dir/<name>`
2. Adds `./plugin_dir/<name>` to `AdaptixServer/go.work`
3. Runs `build:` commands from `axtool.spec` in the plugin source directory
4. Deploys `release.dir` (or `release.globs` files) into `ext_dir/<name>/`
5. Writes `<ext_prefix>/<name>/<config>` entry into the runtime `profile.yaml`
6. Records install state in `AdaptixServer/.installed_plugins.yaml`

---

## adaptix.spec — Project Spec

Located at the repository root (the directory containing `AdaptixServer/` and `AdaptixClient/`).

### Fields

| Field | Required | Relative to | Description |
|-------|----------|-------------|-------------|
| `server_version` | yes | — | Compared against plugin `min_server_version` (e.g. `"v2.0"`) |
| `server_dir` | no | project root | Teamserver sources + `go.work`. Default: `AdaptixServer` |
| `plugin_dir` | yes | `server_dir` | Where plugin sources are placed. Example: `extenders` |
| `ext_dir` | yes | project root | Deployed extender releases. Example: `dist/extenders` |
| `profile` | no | project root | Runtime profile patched by axtool. Default: sibling of `ext_dir` |
| `ext_prefix` | no | — | Path prefix for profile entries as seen from server CWD. Default: basename of `ext_dir` |
| `axscript_dir` | no | project root | AxScript kit install root. Default: sibling of `ext_dir` named `axscripts` |
| `axscript_prefix` | no | — | Prefix for `Teamserver.axscripts` entries |
| `client_dir` | no | project root | GUI client sources. Default: `AdaptixClient` |
| `dist_dir` | no | project root | Binary staging dir. Default: `dist` |
| `packages` | no | — | Default package list for `ext install` |
| `deps` | no | — | Host apt packages (only apt implemented) |
| `systemd` | no | — | Defaults for `server daemon` |

### packages[] fields

| Field | Required | Description |
|-------|----------|-------------|
| `source` | yes | Local path, `github.com/org/repo@ref`, or git URL |
| `path` | no | Subdirectory inside source that contains `axtool.spec` |
| `name` | no | Install only this extender from a multi-item package |
| `plugin_dir` | no | Override top-level `plugin_dir` for this package |

### deps format

```yaml
deps:
  common:
    apt: [git, make, build-essential]
  server:
    apt: [libssl-dev, mingw-w64, g++-mingw-w64]
  client:
    apt: [cmake, qt6-base-dev, qt6-websockets-dev]
```

### systemd fields

| Field | Default | Description |
|-------|---------|-------------|
| `name` | `adaptixserver` | Unit basename → `/etc/systemd/system/<name>.service` |
| `user` | root | Process user |
| `group` | root | Process group |
| `debug` | false | Append `-debug` to ExecStart |
| `user_mode` | false | Install as systemd user unit |

### Full example

```yaml
server_version: "v2.0"

server_dir: AdaptixServer
client_dir: AdaptixClient
plugin_dir: extenders

dist_dir: dist
ext_dir: dist/extenders
axscript_dir: dist/axscripts
profile: dist/profile.yaml

systemd:
  name: adaptix
  user: root

deps:
  common:
    apt: [git, make, build-essential]
  server:
    apt: [libssl-dev, mingw-w64]
  client:
    apt: [cmake, qt6-base-dev]

packages:
  - source: ./AdaptixServer/extenders/beacon_listener_http
  - source: ./AdaptixServer/extenders/beacon_agent
```

---

## axtool.spec — Package Spec

Located at the root of each plugin or kit repository (or a monorepo listing several items).

### Extender fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | `[a-z0-9][a-z0-9_-]*`; matches directory name under source and release trees |
| `version` | yes | Version string |
| `type` | yes | `listener` \| `agent` \| `service` |
| `description` | no | Human-readable summary |
| `author` | no | Attribution |
| `min_server_version` | no | Soft check vs project `server_version`; fails unless `--ignore-version` |
| `requires` | no | Other plugin names; warn if missing from install state |
| `source` | no | Subdirectory of the package that is this plugin's root (multi-plugin repos) |
| `deps.apt` | no | Extra apt packages for this plugin |
| `build` | yes | Ordered shell commands run via `sh -c` in the plugin source directory |
| `release` | yes | Exactly one of `dir` or `globs` |

### release fields

| Field | Required | Description |
|-------|----------|-------------|
| `dir` | one of | Directory under plugin source; entire contents deployed to `ext_dir/<name>/` |
| `globs` | one of | Glob patterns relative to plugin source |
| `config` | no | Config path relative to release root. Default: auto-detect shallowest `config.yaml` |

After build, axtool verifies the release contains:
1. A config file (`config.yaml` or `release.config`)
2. At least one `*.so` file

### AxScript kit fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Kit id; install directory name under `axscript_dir` |
| `version` | yes | Version string |
| `entry` | yes | Main `.axs` path relative to kit root |
| `source` | no | Subdirectory of the package that is the kit root |
| `release` | no | Optional `dir` or `globs`; default = copy whole tree except `.git` |

Profile registration for kits:
```text
Teamserver.axscripts:
  - <axscript_prefix>/<name>/<entry>
```

### Single plugin example (`release.dir`)

```yaml
extenders:
  - name: beacon_agent
    version: 1.0.0
    type: agent
    min_server_version: "v2.0"
    requires: [beacon_listener_http]
    deps:
      apt: [mingw-w64, g++-mingw-w64]
    build:
      - make
    release:
      dir: dist/
```

### In-place plugin example (`release.globs`)

```yaml
extenders:
  - name: mcp_server
    version: 1.0.0
    type: service
    build:
      - make
    release:
      globs:
        - config.yaml
        - mcp_server.so
        - ax_config.axs
```

### Multi-plugin monorepo example

```yaml
extenders:
  - name: my_agent
    version: 1.0.0
    type: agent
    source: ./my_agent
    build: [make]
    release: { dir: dist/ }

  - name: my_listener
    version: 1.0.0
    type: listener
    source: ./my_listener
    build: [make]
    release: { dir: dist/ }
```

### AxScript kit example

```yaml
scripts:
  - name: extension-kit
    version: 1.0.0
    entry: extension-kit.axs
    min_server_version: "v2.0"
```

---

## Install State

File: `AdaptixServer/.installed_plugins.yaml` — managed by axtool; do not hand-edit.

Per entry: `name`, `version`, `type`, `source`, `commit`, `source_path`, `release_path`, `profile_entry`, `installed_at`.

`type` may be `listener`, `agent`, `service`, or `axscript`.

---

## Template Placeholder System

Templates from `github.com/Adaptix-Framework/templates-extender` use these placeholders — all must be replaced before the plugin builds:

| Placeholder | Replacement |
|-------------|-------------|
| `_NAME_` | lowercase plugin name (e.g. `beacon`) |
| `_LISTENER_1_`, `_LISTENER_2_` | listener registration names in `config.yaml` |
| `_AGENT_` | agent registration name in `go.mod` |
| `_PROTOCOL_` | transport protocol string (set via `--protocol` flag) |

After `axtool template`, verify:

```bash
grep -r '_[A-Z][A-Z_]*_' *.go *.yaml go.mod
# Expect zero results
```

---

## Placeholder System

All must be substituted — zero survivors in output:

| Placeholder | Value | Context |
|-------------|-------|---------|
| `__NAME__` | lowercase name | All files |
| `__NAME_CAP__` | Capitalized | Class names |
| `__WATERMARK__` | 8-char hex | Agent config |
| `__PACKAGE__` | `main`/`crypto`/`protocol` | Go package name |
| `__BUILD_TOOL__` | From toolchain YAML | Build command |
| `__PROTOCOL__` | Protocol name | Wire format |
| `__PROTOCOL_CAP__` | Capitalized protocol | Listener names |
| `__LISTENER_TYPE__` | `external`/`internal` | Listener behavior |

## Protocol Overlay Mechanism

Protocols live in `protocols/<name>/` and can override plugin templates:

1. `types.go.tmpl` + `constants.go.tmpl` → merged into `pl_utils.go` (repackaged as `main`)
2. `crypto.go.tmpl` → injected into `src_<name>/crypto/crypto.go` (repackaged as `crypto`)
3. `pl_main.go.tmpl` → **replaces** base `pl_main.go` entirely
4. `pl_transport.go.tmpl` → replaces listener transport
5. `pl_internal.go.tmpl` → replaces internal listener handler
6. `pl_build_<lang>.go.tmpl` → replaces build handler for that language
7. `implant/` overlays → merged into implant source tree

## Toolchains

Default safe toolchains: Go → `go-standard`, C++ → `mingw`, Rust → `cargo`.

Toolchain YAML format:
```yaml
name: go-standard
language: go
compiler:
  binary: go
build:
  command: "go build"
  env: { CGO_ENABLED: "0" }
  flags: ["-trimpath"]
  ldflags: "-s -w"
targets:
  - { goos: linux, goarch: amd64, suffix: "_linux_amd64" }
  - { goos: windows, goarch: amd64, suffix: "_windows_amd64.exe" }
```

## Evasion Gate

Generated with `-Evasion` flag. Scaffolds `evasion/` directory with a `Gate` interface (5 methods). Markers in templates:

- Go: `// __EVASION_IMPORT__`, `// __EVASION_FIELD__`, `// __EVASION_INIT__`
- C++: `// __EVASION_INCLUDE__`, `// __EVASION_MEMBER__`, `// __EVASION_CTOR__`
- Rust: `// __EVASION_MOD__`, `# __EVASION_FEATURES__` (must stay inside `[features]` in Cargo.toml)

Without `-Evasion`: all markers are stripped, no `evasion/` directory.
