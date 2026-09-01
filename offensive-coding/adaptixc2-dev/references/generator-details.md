# `axtool` templates, packaging, and activation

Use `axtool` from the same pinned Adaptix checkout as the Teamserver. Go plugins and the current build/install flow target Linux-like environments; run build and activation checks in the actual Teamserver environment.

## Contents

- [Build and identify the tool](#build-and-identify-the-tool)
- [Scaffold](#scaffold)
- [Project spec](#project-spec-adaptixspec)
- [Package spec](#package-spec-axtoolspec)
- [Install commands](#install-commands)
- [Activation](#activation)
- [Provenance and safe operation](#provenance-and-safe-operation)
- [Preflight and rollback record](#preflight-and-rollback-record)

## Build and identify the tool

```bash
go -C AdaptixTools build -o dist/axtool .
./AdaptixTools/dist/axtool --help
git rev-parse HEAD
```

Project commands take the project/spec path as the first argument. There is no `--spec` flag:

```bash
./AdaptixTools/dist/axtool adaptix.spec ext list
```

Template commands do not take `adaptix.spec`.

## Scaffold

From the directory that should own the new package:

```bash
axtool template agent example-agent
axtool template listener example-listener --protocol https
axtool template service example-service
axtool template axscript example-ui
```

Agent, listener, and service scaffolds default to the mutable `templates-extender@main`. For reproducible work, use `--from` with a reviewed local checkout pinned to a full commit. The AxScript scaffold is generated locally; its `--from` value is currently ignored.

The current scaffold replacement keys are:

| Type | Keys replaced by `axtool` |
|---|---|
| all Go extenders | `_SO_FILE_HERE_` |
| agent | `_AGENT_`, `_RANDOM_HEX_8_`, `adaptix_agent_NAME` |
| listener | `_LISTENER_`, `_PROTOCOL_`, `adaptix_listener_NAME_PROTOCOL`, `listener_LISTENER_` |
| service | `_SERVICE_`, `adaptix_service_NAME_PROTOCOL` |

After scaffolding, replace the generated author/description placeholders and check for unresolved keys:

```bash
rg -n "_SO_FILE_HERE_|_AGENT_|_RANDOM_HEX_8_|adaptix_agent_NAME|_LISTENER_|_PROTOCOL_|adaptix_listener_NAME_PROTOCOL|listener_LISTENER_|_SERVICE_|adaptix_service_NAME_PROTOCOL" .
```

The scaffolder creates `axtool.spec`; it does not prove that the copied template matches the pinned Teamserver contracts. Run the contract gate and compile before adding behavior.

## Project spec: `adaptix.spec`

Paths are relative to the directory containing `adaptix.spec`, except `plugin_dir`, which is relative to `server_dir`.

```yaml
server_version: "v2.0"
server_dir: AdaptixServer
client_dir: AdaptixClient
plugin_dir: extenders

dist_dir: dist
ext_dir: dist/extenders
axscript_dir: dist/axscripts
profile: dist/profile.yaml

packages:
  - source: ./AdaptixServer/extenders/example-service
```

Required fields are `server_version`, `plugin_dir`, and `ext_dir`. Common optional fields are `profile`, `ext_prefix`, `axscript_dir`, `axscript_prefix`, `client_dir`, `dist_dir`, `packages`, `deps`, and `systemd`.

`packages[]` accepts `source`, optional `path`, optional item `name`, and optional `plugin_dir` override. Local `source` values are currently resolved against the process working directory, not the spec directory. Run package operations from the project root and pre-resolve every local path.

Do not depend on `repo_root` to relocate project operations: the current code resolves it into a layout field but no downstream command consumes that field.

## Package spec: `axtool.spec`

### One extender

```yaml
extenders:
  - name: example-service
    version: 0.1.0
    type: service
    min_server_version: "v2.0"
    build:
      - make
    release:
      dir: dist/
      config: config.yaml
```

Required extender fields:

| Field | Contract |
|---|---|
| `name` | `[a-z0-9][a-z0-9_-]*`, unique in the spec |
| `version` | non-empty package version |
| `type` | `agent`, `listener`, or `service` |
| `build` | at least one command |
| `release` | exactly one of `dir` or `globs` |

Optional fields include `description`, `author`, `min_server_version`, `requires`, `source`, and `deps.apt`. `requires` currently warns when a dependency is absent; it does not order or install dependencies.

Build commands run in the installed source directory through `sh -c` and inherit the host environment. Treat the entire spec and source as executable trusted input. Prefer a small checked-in build script, pinned dependencies, and direct validation of its outputs.

The release must contain at least one `.so` and a config file. `release.config` is relative to the collected release root; without it, `axtool` auto-detects the shallowest `config.yaml` or `config.yml`.

### Multi-item package

```yaml
extenders:
  - name: example-agent
    version: 0.1.0
    type: agent
    source: agent
    build: [make]
    release: {dir: dist/}

  - name: example-listener
    version: 0.1.0
    type: listener
    source: listener
    build: [make]
    release: {dir: dist/}
```

Install one item with `--name`. `source` paths must stay within the reviewed package even if current validation appears to accept a broader path.

### AxScript kit

```yaml
scripts:
  - name: example-ui
    version: 0.1.0
    entry: example-ui.axs
    min_server_version: "v2.0"
```

The entry must be a relative `.axs` path. With no release selector, the package tree is copied except `.git`. Keep the kit minimal so unrelated files are not deployed.

## Install commands

Use one source mode:

```bash
# Explicit local package
axtool adaptix.spec ext install ./path/to/package

# One item in a multi-item package
axtool adaptix.spec ext install ./path/to/package --name example-service

# All packages declared in adaptix.spec
axtool adaptix.spec ext install --packages

# A separate packages YAML
axtool adaptix.spec ext install --from packages.yaml
```

Calling `ext install` without a source, `--packages`, or `--from` is an error. `-d` installs declared apt dependencies; review the package list first and use it only on a disposable or managed host.

For an extender, install normally:

1. resolves/copies source under `server_dir/plugin_dir` when needed;
2. adds the source module to `AdaptixServer/go.work`;
3. executes each build command;
4. collects and verifies release files;
5. deploys to `ext_dir/<name>`;
6. adds `<ext_prefix>/<name>/<config>` to `Teamserver.extenders`;
7. writes `AdaptixServer/.installed_plugins.yaml`.

An AxScript kit deploys under `axscript_dir/<name>` and registers `<axscript_prefix>/<name>/<entry>` under `Teamserver.axscripts`.

## Activation

Installation edits disk state; it does not prove runtime load. The predictable activation path is a cold Teamserver restart with working directory equal to `dist_dir`:

```bash
cd dist
./adaptixserver -profile profile.yaml
```

Then verify:

- the profile entry resolves from that working directory;
- loader logs show the expected config, `.so`, AxScript, and exact `InitPlugin` signature;
- the agent/listener/service catalog contains the extender;
- the client reconnects/resyncs and displays expected commands/UI;
- one real request reaches the plugin and produces its terminal state.

Loader failures do not necessarily stop Teamserver startup. A ready process is insufficient evidence. For runtime service removal use the canonical [service state machine](architecture-and-lifecycle.md#service); already-connected clients may also need reconnect/resync to receive changed service AxScript state.

## Provenance and safe operation

- Pin git sources to a reviewed full commit. Branches/tags can move, and the current state file records only a shortened commit string.
- Inspect `axtool.spec` before installation; `build` executes shell commands.
- Pre-resolve `--path`, package `source`, project paths, `plugin_dir`, and profile/release targets and require containment under the intended roots. Current validation is not a complete containment boundary.
- Run one `axtool` mutation at a time. State, profile, and `go.work` writes have no cross-process lock or atomic commit.
- Commit or back up profile, `go.work`, state, and existing release/source trees before `--force`. Rollback is best effort and destructive force cleanup is not transactional.
- Treat `.installed_plugins.yaml` as install bookkeeping, not a provenance seal. Independently record full source commit, tool commit, checksums, Go version, and build flags.
- Avoid printing `profile show`, `profile get all`, or generated service files into shared logs; profile fields may contain passwords or tokens.
- Validate systemd unit name, user, group, binary, working directory, and profile path as trusted values before installation.
- Back up and verify both certificate and key before `--force-cert`; partial pre-existing pairs can be replaced.

## Preflight and rollback record

Before mutation, capture:

```bash
git status --short
git rev-parse HEAD
go version
go -C AdaptixServer env GOOS GOARCH GOVERSION
go -C AdaptixServer list -m all
```

After installation, record release checksums, profile diff, `go.work` diff, state entry, catalog/load evidence, and restart procedure. If activation fails, restore the known-good files/release and restart; do not assume `ext uninstall` reverses an interrupted or forced install completely.
