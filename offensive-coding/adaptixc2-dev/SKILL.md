---
name: adaptixc2-dev
description: "Auth/lab dev: AdaptixC2 extenders; agents, listeners, services, AxScript UI, configs, protocols, templates, build/validation workflows."
license: MIT
metadata:
  author: AeonDave
  version: "2.0"
---

# AdaptixC2 Development

Workflows and patterns for building extenders (agents, listeners, services) for AdaptixC2 v2.0 and managing them with the `axtool` CLI.

---

## Architecture Overview

AdaptixC2 has three extension points — all are Go plugins (`.so`, `-buildmode=plugin`):

| Type | Purpose | InitPlugin signature |
|------|---------|---------------------|
| **Agent** | Implant builder + session handler | `InitPlugin(ts any, moduleDir string, watermark string) adaptix.PluginAgent` |
| **Listener** | Network transport + agent traffic handler | `InitPlugin(ts any, moduleDir string, listenerDir string) adaptix.PluginListener` |
| **Service** | Auxiliary pipeline (wrapper, hook, tool) | `InitPlugin(ts any, moduleDir string, serviceConfig string) adaptix.PluginService` |

The Teamserver loads plugins via `plugin.Open()`, calls `InitPlugin`, and registers commands from `ax_config.axs`. **Module: `github.com/Adaptix-Framework/axc2/v2` v2.0.13** (Go 1.26.5; requires `axsafe` v0.0.0-…).

---

## 1 — Agent Plugin

### File structure

```
<name>_agent/
├── axtool.spec          # Package spec (name/version/type/build/release)
├── config.yaml          # extender_type: "agent"
├── ax_config.axs        # AxScript UI + command definitions
├── go.mod               # requires axc2/v2 v2.0.13
├── Makefile             # go build -buildmode=plugin → dist/
├── pl_main.go           # InitPlugin, PluginAgent impl
├── pl_packer.go         # PackTasks, PivotPackData
├── pl_utils.go          # Wire types, crypto, pack helpers
└── src_<name>/          # Implant source tree
```

### v2 Plugin interfaces (`axc2/v2`)

```go
// InitPlugin returns a PluginAgent; Teamserver is obtained via ts.(adaptix.Teamserver)
type PluginAgent interface {
    GenerateProfiles(profile adaptix.BuildProfile) ([][]byte, error)
    BuildPayload(profile adaptix.BuildProfile, agentProfiles [][]byte) ([]byte, string, error)
    CreateAgent(beat []byte) (adaptix.AgentData, adaptix.AgentFunctions, error)
    AgentRestore(agentData adaptix.AgentData) adaptix.AgentFunctions  // NEW in v2
    Call(operator string, agentId int64, function string, args string) // NEW in v2
}

// AgentFunctions replaces the v1 ExtenderAgent interface — a struct of function values
type AgentFunctions struct {
    CreateCommand func(AgentData, map[string]any) (TaskData, ConsoleMessageData, error)
    ProcessData   func(AgentData, []byte) error
    PackTasks     func(AgentData, []TaskData) ([]byte, error)
    Encrypt       func([]byte, []byte) ([]byte, error)
    Decrypt       func([]byte, []byte) ([]byte, error)
    PivotPackData func(pivotId string, data []byte) (TaskData, error)
    Delivery      DeliveryFunc                  // optional direct delivery bypass
    TunnelCB      TunnelCallbacks
    TerminalCB    TerminalCallbacks
}
```

**Key v2 changes**: `ExtenderAgent` is gone; `AgentFunctions` is a plain struct. `CreateAgent` now returns `AgentFunctions` (not the interface). `AgentRestore` rebuilds function closures for agents reloaded from DB. `Call` handles direct RPC from other plugins or AxScript.

### Workflow: new agent from scratch

1. Generate scaffold: `axtool template agent <name>`  (fetches from `Adaptix-Framework/templates-extender`)
2. Fill placeholders in `axtool.spec`, `config.yaml`, `go.mod`
3. Implement `CreateCommand` switch — one case per command in `ax_config.axs`
4. Implement `ProcessData` response handler — one case per response code
5. Implement `GenerateProfiles` — serialize listener profiles into config blobs for the implant
6. Implement `BuildPayload` — invoke build toolchain, return compiled binary
7. Implement `AgentRestore` — return same `AgentFunctions` struct from closed-over state
8. Implement implant source in `src_<name>/`
9. Validate: `go mod tidy && go vet ./...`

### config.yaml

```yaml
extender_type: "agent"
extender_file: "agent_<name>.so"
ax_file: "ax_config.axs"
agent_name: "<name>"
agent_watermark: "<hex8>"
listeners:
  - "<NameCap><ProtoCap>"
multi_listeners: false
```

See [references/plugin-patterns.md](references/plugin-patterns.md) for CreateCommand/ProcessData code patterns.

---

## 2 — Listener Plugin

### File structure

```
<name>_listener/
├── axtool.spec          # Package spec
├── config.yaml          # extender_type: "listener"
├── ax_config.axs        # UI form for listener creation
├── go.mod, Makefile
├── pl_main.go           # InitPlugin, PluginListener impl
└── pl_transport.go      # Network transport
```

### v2 Listener interfaces

```go
type PluginListener interface {
    Create(name, config string, customData []byte) (ExtenderListener, ListenerData, []byte, error)
    Call(operator string, listenerName string, function string, args string) // NEW in v2
}

type ExtenderListener interface {
    Start() error
    Edit(config string) (ListenerData, []byte, error)
    Stop() error
    GetProfile() ([]byte, error)
    InternalHandler(data []byte) (int64, error)  // return type changed to int64 in v2
}
```

**Key v2 changes**: `PluginListener.Call` added for direct RPC. `InternalHandler` now returns `(int64, error)` — the agent ID — instead of `(string, error)`.

### Workflow: new listener

1. Generate scaffold: `axtool template listener <name> --protocol <proto>`
2. Implement `Create()` — parse JSON config, validate, build transport; `customData != nil` means restore from DB
3. Implement `Start()` — bind network, serve HTTP/TCP/DNS/SMB
4. Implement agent registration + callback flow (see [references/plugin-patterns.md](references/plugin-patterns.md))
5. Implement `Stop()` — graceful shutdown
6. Implement `GetProfile()` — serialize crypto keys + config for agent embedding
7. Validate: `go mod tidy && go vet ./...`

### Listener types

- **external**: Binds a network port. Agent connects directly.
- **internal**: No network port. Used for pivot/linked agents. `InternalHandler()` processes relayed data, returns `agentId int64`.

### config.yaml

```yaml
extender_type: "listener"
extender_file: "listener_<name>.so"
ax_file: "ax_config.axs"
listener_name: "<NameCap><ProtoCap>"
listener_type: "external"
protocol: "http"
```

---

## 3 — Service Plugin

### File structure

```
<name>_service/
├── axtool.spec          # Package spec
├── config.yaml          # extender_type: "service"
├── ax_config.axs        # Optional service commands
├── go.mod, Makefile
└── pl_main.go           # InitPlugin, PluginService impl
```

### v2 Service interface

```go
type PluginService interface {
    Call(operator string, function string, args string)
    CallRPC(operator string, function string, args string) (resultJSON string, err error)  // NEW in v2
}
```

**Key v2 changes**: `CallRPC` enables synchronous request/response. Use `Call` for fire-and-forget and `CallRPC` when the AxScript caller needs an immediate return value (`ax.service_command_rpc()`).

### Workflow: new service

1. Generate scaffold: `axtool template service <name>`
2. Implement `Call()` — dispatch by `function` name, parse `args` JSON, send results back via `Ts.TsPluginServiceSendDataClient()`
3. Implement `CallRPC()` — same dispatch, return result as JSON string
4. For wrapper/post-build hooks: register `TsEventHookRegister("agent.generate", ...)` in `InitPlugin`

### config.yaml

```yaml
extender_type: "service"
extender_file: "service_<name>.so"
ax_file: "ax_config.axs"
service_name: "<ServiceName>"
service_config: |
  custom_key: value
```

See [references/plugin-patterns.md](references/plugin-patterns.md) for service dispatch pattern, CallRPC, and wrapper pipeline.

---

## 4 — AxScript (ax_config.axs)

AxScript is JavaScript (Goja engine) with bridge APIs for UI, commands, menus, and events. Files are loaded from `ax_file` in config.yaml.

### Lifecycle summary

| Plugin type | Required functions | Boot call |
|---|---|---|
| **Agent** | `RegisterCommands(listenerType)` → returns `{commands_windows, commands_linux, commands_macos}`; `GenerateUI(listeners_type)` → returns `{ui_panel, ui_container, ui_height, ui_width}` | None (top-level menus/events registered imperatively) |
| **Listener** | `ListenerUI(mode_create)` → returns `{ui_panel, ui_container, ui_height, ui_width}` | None |
| **Service** | `InitService()`, `ServiceUI()`, `data_handler(data)` | `ServiceUI();` must be last line |

### Critical rules

- GroupBox and ScrollArea: use `.setPanel(panel)`, never `.setLayout()` directly
- `getEnabled()` not `isEnabled()` to read enabled state
- File selector in container serializes as **base64**
- `ax.service_command()` is fire-and-forget; results arrive via `data_handler(data)`
- Service name in `ax.service_command(...)` must match `config.yaml → service_name` exactly

See [references/axscript-patterns.md](references/axscript-patterns.md) for lifecycle examples, UI layout patterns, signal connections, command definitions, and gotchas table.
See [references/axscript-api.md](references/axscript-api.md) for complete function reference.

---

## 5 — Teamserver Interface & Data Types

The `Teamserver` interface (type-asserted from `ts any` in `InitPlugin`) provides all server-side operations. See [references/teamserver-api.md](references/teamserver-api.md) for the full signature table.

### Most-used methods

```go
// Agent lifecycle
Ts.TsAgentCreate(agentCrc string, agentUid []byte, beat []byte, listenerName string, ExternalIP string, Async bool) (adaptix.AgentData, error)
Ts.TsAgentProcessData(agentId int64, bodyData []byte) error
Ts.TsAgentUpdateData(newAgentData adaptix.AgentData) error
Ts.TsAgentGetHostedAll(agentId int64, maxDataSize int) ([]byte, adaptix.StatTasks, error)
Ts.TsAgentCommandGroupSet(agentId int64, groupId string, enabled bool) error

// Build
Ts.TsAgentBuildCreateChannel(buildData string, wsconn adaptix.WebSocketConn, creator string) error
Ts.TsAgentBuildExecute(builderId string, workingDir string, env []string, program string, args ...string) error
Ts.TsAgentBuildLog(builderId string, status int, message string) error
Ts.TsAgentBuildSendFile(builderId string, filename string, content []byte) error
Ts.TsAgentBuildClose(builderId string)

// Tasks
Ts.TsTaskCreate(agentId int64, cmdline string, client string, taskData adaptix.TaskData)
Ts.TsTaskUpdate(agentId int64, data adaptix.TaskData)

// Downloads / Uploads
Ts.TsDownloadAdd(AgentId int64, fileId int64, fileName string, fileSize int64) error
Ts.TsDownloadUpdate(fileId int64, state int, data []byte) error
Ts.TsDownloadClose(fileId int64, reason int) error
Ts.TsUploadAddContent(agentId int64, fileId int64, remotePath string, content []byte, canceled bool, kind int, artname string, arttype string) error

// Plugin-to-plugin communication
Ts.TsPluginServiceSendDataClient(operator string, service string, data string)
Ts.TsPluginServiceSendDataAll(service string, data string)
Ts.TsPluginServiceCallWait(serviceName string, operator string, function string, args string, timeoutMs int) (resultJSON string, err error)
Ts.TsPluginAgentCall(agentId int64, operator string, function string, args string)
Ts.TsPluginListenerCall(listenerName string, operator string, function string, args string)

// Events
Ts.TsEventHookRegister(eventType string, name string, phase int, priority int, handler func(event any) error) string
Ts.TsEventHookOnPre(eventType string, name string, handler func(event any) error) string
Ts.TsEventHookOnPost(eventType string, name string, handler func(event any) error) string
Ts.TsEventHookUnregister(hookID string) bool

// Custom HTTP endpoints
Ts.TsEndpointRegister(method, path string, handler func(username string, body []byte) (int, []byte)) error
Ts.TsEndpointRegisterPublic(method, path string, handler func(body []byte) (int, []byte)) error

// Persistent extender storage
Ts.TsExtenderDataSave(extenderName, key string, data []byte) error
Ts.TsExtenderDataLoad(extenderName, key string) ([]byte, error)
Ts.TsExtenderDataDelete(extenderName, key string) error
Ts.TsExtenderDataKeys(extenderName string) ([]string, error)
```

### Key type facts (v2)

- `AgentData.Id` is **`int64`** — not `string` as in v1
- `AgentData.UID` is `[]byte` — passed to `TsAgentCreate` as `agentUid`
- `AgentData.Sleep` is `uint` (seconds)
- `AgentData.Pid`/`Tid` are `string`
- `AgentData.Os`: `adaptix.OS_WINDOWS=1`, `OS_LINUX=2`, `OS_MAC=3` (never `OS_MACOS`)
- `TsAgentGetHostedAll` returns `([]byte, StatTasks, error)` — three values in v2
- `TsDownloadAdd` takes `fileId int64` and `fileSize int64` (not `int`)
- `TsAgentBuildExecute` takes `env []string` (new param) before `program`
- Helper functions in `helpers.go`: `adaptix.GetStringArg`, `GetIntArg`, `GetBoolArg`, `GetFileArg`, `GetFloatArg` + `*Default` variants — use these instead of raw type assertions

See [references/teamserver-api.md](references/teamserver-api.md) for full method signatures and data types.

---

## 6 — axtool — Scaffold & Extender Management

`axtool` is the v2 CLI that replaces all v1 PowerShell generators. It manages scaffolding, building, installing, and profiling extenders.

### Scaffolding a new plugin

```bash
# Creates <name>/ with axtool.spec, config.yaml, go.mod, Makefile, pl_main.go, ax_config.axs
axtool template agent   <name>                        # agent scaffold
axtool template listener <name> --protocol <proto>    # listener scaffold (proto used as placeholder)
axtool template service  <name>                       # service scaffold
axtool template axscript <name>                       # AxScript kit scaffold

# --from: override template source (local path or github.com/org/repo@ref)
# If name is omitted, uses the current directory name
```

Template source defaults to `github.com/Adaptix-Framework/templates-extender@main`.

### Package specs

Every plugin needs an **`axtool.spec`** at its root:

```yaml
extenders:
  - name: my_agent           # [a-z0-9][a-z0-9_-]*; matches install directory name
    version: 1.0.0
    type: agent              # listener | agent | service
    min_server_version: "v2.0"
    requires: [my_listener_http]
    deps:
      apt: [mingw-w64, g++-mingw-w64]
    build:
      - make                 # ordered shell commands run in the plugin source dir
    release:
      dir: dist/             # deploy entire dist/ contents to ext_dir/<name>/
      # globs: [config.yaml, my_agent.so]  # alternative: explicit file list
```

The project root needs an **`adaptix.spec`**:

```yaml
server_version: "v2.0"
server_dir: AdaptixServer
client_dir: AdaptixClient
plugin_dir: extenders            # relative to server_dir

dist_dir: dist
ext_dir: dist/extenders
axscript_dir: dist/axscripts
profile: dist/profile.yaml

packages:
  - source: ./AdaptixServer/extenders/my_listener_http
  - source: ./AdaptixServer/extenders/my_agent
```

### Build and install

```bash
# Install all packages from adaptix.spec
axtool adaptix.spec ext install

# Install a single remote package
axtool adaptix.spec ext install github.com/org/repo@v1

# Install only one extender from a multi-item repo
axtool adaptix.spec ext install github.com/org/repo@v1 --name my_agent

# Install with apt dep resolution
axtool adaptix.spec ext install -d

# Build the server
axtool adaptix.spec server build

# List installed extenders
axtool adaptix.spec ext list
```

After install, axtool:
1. Adds `./plugin_dir/<name>` to `AdaptixServer/go.work`
2. Runs `build:` commands in the plugin source directory
3. Deploys `release.dir` to `ext_dir/<name>/`
4. Writes `<ext_prefix>/<name>/<config>` into the runtime `profile.yaml`

Install state is tracked in `AdaptixServer/.installed_plugins.yaml` — do not hand-edit.

See [references/generator-details.md](references/generator-details.md) for full axtool.spec and adaptix.spec field reference.

---

## 7 — Validation Workflow

### Go validation

```bash
# From plugin root (WSL preferred on Windows for Linux .so targets)
go mod tidy && go vet ./...

# Or via wsl
wsl bash -lc 'cd /mnt/d/Sources/.../my_agent && /usr/local/go/bin/go mod tidy && /usr/local/go/bin/go vet ./...'
```

### Placeholder leak check (templates-extender placeholders)

```bash
# Template uses _NAME_, _LISTENER_1_, etc. — zero survivors expected after scaffold fill
grep -r '_[A-Z][A-Z_]*_' *.go
```

### Parity checks

- Every command object built in `ax_config.axs` → matching `CreateCommand` case in `pl_main.go`
- Every `CreateCommand` case → matching `ProcessData` handler
- `AgentRestore` must return functionally equivalent `AgentFunctions` to `CreateAgent`
- `TsAgentGetHostedAll` returns three values — always capture `StatTasks` or discard with `_`

---

## 8 — Hard Constraints

| Forbidden | Correct |
|-----------|---------|
| `adaptix.OS_MACOS` | `adaptix.OS_MAC` |
| `SessionInfo.Sleep` (string) → `AgentData.Sleep` (uint) | `time.ParseDuration(si.Sleep)` then cast |
| `ProcessId` (int) → `AgentData.Pid` (string) | `fmt.Sprintf("%d", params.ProcessId)` |
| `AgentData.Id` as string (v1 habit) | `AgentData.Id` is `int64` in v2 |
| `TsAgentGetHostedAll(id, size)` without capturing `StatTasks` | Capture all 3 return values; discard `_` |
| `TsAgentBuildExecute` without `env []string` param | Pass `nil` or explicit env |
| `TsDownloadAdd(id, id, name, int)` v1 signature | v2: `(int64, int64, string, int64)` |
| `PluginService.Call` without `CallRPC` | Implement both; return `""` if RPC not needed |
| `ExtenderAgent` v1 interface | Use `AgentFunctions` struct with function values |
| Adding command to `ax_config.axs` without `AgentRestore` update | `AgentRestore` closure must expose same functions |
| `TsServiceSendDataClient/All` (v1 names) | `TsPluginServiceSendDataClient/All` in v2 |
| Stubs that compile but do nothing at runtime | Implement fully or remove entirely |

---

## 9 — Learned Pitfalls

- **v2 ID types**: All agent IDs are `int64` everywhere — Teamserver methods, `TaskData.AgentId`, `AgentData.Id`. Passing a string from v1 habit compiles but routes wrong.
- **AgentRestore contract**: `AgentRestore` is called on server restart for every persisted session. If it returns an `AgentFunctions` with nil fields the agent silently stops functioning. Ensure all closures capture a valid `Ts` reference.
- **TsAgentGetHostedAll 3-return**: Ignoring the `StatTasks` return with a single variable panics at compile. Always `data, _, err := ...` or capture all three.
- **TsPluginServiceSendDataClient vs v1**: v1 had `TsServiceSendDataClient(serviceName, client, fn, args)`. v2 is `TsPluginServiceSendDataClient(operator, service, data)` — argument order changed, `data` is a flat string not split function+args.
- **CallRPC deadlock**: Do not call `TsPluginServiceCallWait` from inside a `Call/CallRPC` handler of the same service — it will deadlock. Use goroutines for chained calls.
- **Event hook IDs**: `TsEventHookRegister` returns a `hookID string` (not `(string, error)` as in v1). Store it and call `TsEventHookUnregister(hookID)` in cleanup.
- **go.work membership**: `axtool ext install` adds the plugin to `go.work`. Manual plugin directories not listed in `go.work` will cause build errors during `go build ./...` at the server root.
- **C++ clang compat**: Casting member-fn-ptr to `void*` is a GCC extension. Use `__builtin_return_address(0)`.
- **C++ Makefiles with .c files**: Clang rejects `-std=c++17` for C files. Compile C_SOURCES separately with `-std=c11`.
- **Rust linker-plugin-lto**: Requires `lld`. Route `-mllvm` flags as `-Wl,-mllvm,<arg>`.
- **PE hardening**: Never inflate VirtualSize when diluting entropy — only extend RawSize.
- **Shellcode regression debugging**: Keep a known-good runtime path alive before introducing a shellcode-only fork. Prefer one small boundary adapter plus markers over replacing shared protocol code.
- **Reflective Rust entrypoints**: Do not assume `AddressOfEntryPoint` is safer than exported `DllMain`; test the specific loader/payload contract.

---

## Resources

| File | When to load |
|---|---|
| [references/plugin-patterns.md](references/plugin-patterns.md) | CreateCommand/ProcessData/AgentFunctions patterns, adding commands end-to-end, listener callback flow, service dispatch and CallRPC |
| [references/axscript-patterns.md](references/axscript-patterns.md) | AxScript lifecycle examples, UI layout, signals, commands, command groups, hooks, gotchas |
| [references/axscript-api.md](references/axscript-api.md) | Complete AxScript function reference with signatures |
| [references/teamserver-api.md](references/teamserver-api.md) | Full Teamserver method signatures, data types, and v2 gotchas |
| [references/generator-details.md](references/generator-details.md) | axtool.spec / adaptix.spec full field reference, template placeholder system |
| Online docs | https://adaptix-framework.gitbook.io/adaptix-framework/development/ (may lag source) |
| Templates | https://github.com/Adaptix-Framework/templates-extender |
| axc2/v2 module | `github.com/Adaptix-Framework/axc2/v2` v2.0.13 |
