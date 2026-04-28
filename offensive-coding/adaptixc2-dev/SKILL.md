---
name: adaptixc2-dev
description: "Develop, extend, and maintain AdaptixC2 extenders (agents, listeners, services) and their template generators. Use when creating new plugins, adding commands, building beacon/listener/service implementations, writing AxScript UI, designing wire protocols, or using the Template-Generators scaffold system. Covers the full plugin lifecycle: Go plugin API (axc2 v1.2.0), AxScript forms/commands/events/menus, config.yaml wiring, Teamserver interface, protocol overlays, multi-language implant builds (Go/C++/Rust), evasion gates, and validation workflows."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
---

# AdaptixC2 Development

Workflows and patterns for building extenders (agents, listeners, services) for the AdaptixC2 framework and maintaining the Template-Generators scaffold system.

---

## Architecture Overview

AdaptixC2 has three extension points — all are Go plugins (`.so`, `-buildmode=plugin`):

| Type | Purpose | InitPlugin signature |
|------|---------|---------------------|
| **Agent** | Implant builder + session handler | `InitPlugin(ts any, moduleDir string, watermark string) adaptix.PluginAgent` |
| **Listener** | Network transport + agent traffic handler | `InitPlugin(ts any, moduleDir string, listenerDir string) adaptix.PluginListener` |
| **Service** | Auxiliary pipeline (wrapper, hook, tool) | `InitPlugin(ts any, moduleDir string, serviceConfig string) adaptix.PluginService` |

The Teamserver loads plugins via `plugin.Open()`, calls `InitPlugin`, registers commands from `ax_config.axs`, and stores instances in safe maps. The axc2 v1.2.0 module defines all interfaces.

---

## 1 — Agent Plugin

### File structure

```
<name>_agent/
├── config.yaml          # extender_type: "agent"
├── ax_config.axs        # AxScript UI + command definitions
├── go.mod               # requires axc2 v1.2.0
├── Makefile             # go build -buildmode=plugin
├── pl_main.go           # InitPlugin, PluginAgent, ExtenderAgent
├── pl_build.go          # GenerateProfiles, BuildPayload
├── pl_utils.go          # Wire types, crypto, helpers
└── src_<name>/          # Implant source tree
```

### Required interfaces

```go
type PluginAgent interface {
    GenerateProfiles(profile adaptix.BuildProfile) ([][]byte, error)
    BuildPayload(profile adaptix.BuildProfile, agentProfiles [][]byte) ([]byte, string, error)
    CreateAgent(beat []byte) (adaptix.AgentData, adaptix.ExtenderAgent, error)
    GetExtender() adaptix.ExtenderAgent
}

type ExtenderAgent interface {
    CreateCommand(agentData adaptix.AgentData, args map[string]any) (adaptix.TaskData, adaptix.ConsoleMessageData, error)
    ProcessData(agentData adaptix.AgentData, decryptedData []byte) error
    Encrypt(data []byte, key []byte) ([]byte, error)
    Decrypt(data []byte, key []byte) ([]byte, error)
    PackTasks(agentData adaptix.AgentData, tasks []adaptix.TaskData) ([]byte, error)
    TunnelCallbacks() adaptix.TunnelCallbacks
    TerminalCallbacks() adaptix.TerminalCallbacks
    PivotPackData(pivotId string, data []byte) (adaptix.TaskData, error)
}
```

### Workflow: new agent from scratch

1. Decide language (Go/C++/Rust) and wire protocol
2. Generate scaffold: `.\agent\generator.ps1 -Name <name> -Watermark <hex8> -Protocol <proto> -Language <lang> -Toolchain <tc>`
3. Implement `CreateCommand` switch cases — one per command in `ax_config.axs`
4. Implement `ProcessData` response handler — one per response code
5. Implement `GenerateProfiles` — serialize listener profiles into agent config blobs
6. Implement `BuildPayload` — invoke build toolchain, return compiled binary
7. Implement implant source in `src_<name>/`
8. Validate: `go mod tidy && go vet ./...`
9. Check placeholders: `Select-String -Path *.go -Pattern '__[A-Z_]+__'`

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
├── config.yaml          # extender_type: "listener"
├── ax_config.axs        # UI form for listener creation
├── go.mod, Makefile
├── pl_main.go           # InitPlugin, PluginListener
├── pl_transport.go      # Network transport
├── pl_crypto.go         # Encrypt/Decrypt
└── pl_internal.go       # Internal listener (optional)
```

### Required interfaces

```go
type PluginListener interface {
    Create(name string, config string, customData []byte) (adaptix.ExtenderListener, adaptix.ListenerData, []byte, error)
}

type ExtenderListener interface {
    Start() error
    Stop() error
    Edit(config string) (adaptix.ListenerData, []byte, error)
    GetProfile() ([]byte, error)
    InternalHandler(data []byte) (string, error)  // internal listeners only
}
```

### Workflow: new listener

1. Generate scaffold: `.\listener\generator.ps1 -Name <name> -Protocol <proto> -ListenerType external`
2. Implement `Create()` — parse JSON config, validate, build transport
3. Implement `Start()` — bind network, serve HTTP/TCP/DNS/etc.
4. Implement agent registration + callback flow (see [references/plugin-patterns.md](references/plugin-patterns.md))
5. Implement `Stop()` — graceful shutdown
6. Implement `GetProfile()` — serialize crypto keys + config for agent embedding
7. Validate: `go mod tidy && go vet ./...`

### Listener types

- **external**: Binds a network port. Agent connects directly.
- **internal**: No network port. Used for pivot/linked agents. `InternalHandler()` processes relayed data.

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
├── config.yaml          # extender_type: "service"
├── ax_config.axs        # Optional UI + service commands
├── go.mod, Makefile
└── pl_main.go           # InitPlugin, PluginService
```

### Required interface

```go
type PluginService interface {
    Call(operator string, function string, args string)
}
```

### Workflow: new service

1. Generate scaffold: `.\service\generator.ps1 -Name <name>` (add `-Wrapper` for post-build pipeline)
2. Implement `Call()` — dispatch by `function` name, parse `args` JSON
3. Use Teamserver hooks for event-driven behavior: `TsEventHookRegister()`
4. For wrapper services: hook `agent.generate` to intercept and transform payloads

### config.yaml

```yaml
extender_type: "service"
extender_file: "service_<name>.so"
ax_file: "ax_config.axs"
service_name: "<ServiceName>"
service_config: |
  custom_key: value
```

See [references/plugin-patterns.md](references/plugin-patterns.md) for service dispatch pattern and wrapper pipeline.

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

The `Teamserver` interface (type-asserted from `ts any` in `InitPlugin`) provides all server-side operations.

### Most-used methods

```go
// Agent lifecycle
Ts.TsAgentCreate(agentCrc, agentId string, beat []byte, listenerName, externalIP string, async bool) (adaptix.AgentData, error)
Ts.TsAgentProcessData(agentId string, bodyData []byte) error
Ts.TsAgentUpdateData(newAgentData adaptix.AgentData) error
Ts.TsAgentGetHostedAll(agentId string, maxDataSize int) ([]byte, error)

// Tasks
Ts.TsTaskCreate(agentId, cmdline, client string, data adaptix.TaskData)
Ts.TsTaskUpdate(agentId string, data adaptix.TaskData)

// Downloads
Ts.TsDownloadAdd(agentId, fileId, fileName string, totalSize int) error
Ts.TsDownloadUpdate(agentId, fileId string, data []byte) error
Ts.TsDownloadClose(agentId, fileId string) error

// Services
Ts.TsServiceSendDataClient(serviceName, client, function, args string) error
Ts.TsServiceSendDataAll(serviceName, function, args string) error

// Events
Ts.TsEventHookRegister(event string, phase int, priority int, handler func(...)) (string, error)
```

### Key type gotchas

- `AgentData.Sleep` is `uint` (seconds) — convert with `time.ParseDuration()` then cast
- `AgentData.Pid` is `string` — convert with `fmt.Sprintf("%d", pid)`
- `AgentData.Os` uses `adaptix.OS_WINDOWS=1`, `OS_LINUX=2`, `OS_MAC=3` — never `OS_MACOS`
- `BuildProfile.AgentConfig` is JSON string from `container.toJson()` in GenerateUI

See [references/teamserver-api.md](references/teamserver-api.md) for full method signatures and data types.

---

## 6 — Template Generators

The scaffold system at `AdaptixC2-Template-Generators/` generates plugin + implant boilerplate.

### Generation commands (PowerShell)

```powershell
# Agent
.\agent\generator.ps1 -Name <name> -Watermark a1b2c3d4 -Protocol <proto> -Language <lang> -Toolchain <tc>
# With evasion gate
.\agent\generator.ps1 -Name <name> -Watermark a1b2c3d4 -Protocol <proto> -Language <lang> -Toolchain <tc> -Evasion

# Listener
.\listener\generator.ps1 -Name <name> -Protocol <proto> -ListenerType external

# Service
.\service\generator.ps1 -Name <name>
# Service with wrapper pipeline
.\service\generator.ps1 -Name <name> -Wrapper
```

See [references/generator-details.md](references/generator-details.md) for placeholder system, protocol overlays, toolchain YAML format, and evasion gate details.

---

## 7 — Validation Workflow

### Go validation (WSL preferred on Windows)

```powershell
wsl bash -lc 'cd /mnt/d/Sources/AdaptixC2-Template-Generators/output/<dir> && /usr/local/go/bin/go mod tidy && /usr/local/go/bin/go vet ./...'
```

### Placeholder leak check

```powershell
Select-String -Path output\<dir>\*.go -Pattern '__[A-Z_]+__'
# Zero matches expected
```

### Parity checks

- Every `create_command()` in `ax_config.axs` → matching `CreateCommand` case in `pl_main.go`
- Every `CreateCommand` case → matching `ProcessData` handler
- BOF types must survive protocol overlay into `pl_utils.go`
- Protocol `pl_main.go.tmpl` overrides must pass `go vet`

---

## 8 — Hard Constraints

| Forbidden | Correct |
|-----------|---------|
| Edit `output/` by hand in regeneration workflow | Fix template, re-generate |
| `adaptix.OS_MACOS` | `adaptix.OS_MAC` |
| `SessionInfo.Sleep` (string) → `AgentData.Sleep` (uint) | `time.ParseDuration(si.Sleep)` then cast |
| `ProcessId` (int) → `AgentData.Pid` (string) | `fmt.Sprintf("%d", params.ProcessId)` |
| `# __EVASION_FEATURES__` outside `[features]` | Keep marker inside `[features]` TOML section |
| Adding command to `ax_config.axs` without handler | Add `CreateCommand` + `ProcessData` simultaneously |
| Module ref without implementation file | Create implementation file simultaneously |
| Stubs that compile but do nothing at runtime | Implement fully or remove entirely |

---

## 9 — Learned Pitfalls

- **C++ clang compat**: Casting member-fn-ptr to `void*` is a GCC extension. Use `__builtin_return_address(0)`.
- **C++ Makefiles with .c files**: Clang rejects `-std=c++17` for C files. Compile C_SOURCES separately with `-std=c11`.
- **Rust linker-plugin-lto**: Requires `lld`. Route `-mllvm` flags as `-Wl,-mllvm,<arg>`.
- **Rust evasion Cargo.toml**: `# __EVASION_FEATURES__` must be inside `[features]` to avoid duplicate sections.
- **PE hardening**: Never inflate VirtualSize when diluting entropy — only extend RawSize.
- **Section names**: Don't use `.rsrc` as import padding — conflicts with resource injection.
- **COFF string encryption**: GCC statement expressions with static guards don't work in PIC blobs.

---

## Resources

| File | When to load |
|---|---|
| [references/plugin-patterns.md](references/plugin-patterns.md) | CreateCommand/ProcessData patterns, adding commands end-to-end, protocol/wrapper/build workflows |
| [references/axscript-patterns.md](references/axscript-patterns.md) | AxScript lifecycle examples, UI layout, signals, commands, containers, gotchas |
| [references/axscript-api.md](references/axscript-api.md) | Complete AxScript function reference with signatures |
| [references/teamserver-api.md](references/teamserver-api.md) | Full Teamserver method signatures and data types |
| [references/generator-details.md](references/generator-details.md) | Placeholders, protocol overlays, toolchain YAML, evasion gate |
| Online docs | https://adaptix-framework.gitbook.io/adaptix-framework/development/ |
| Extension-Kit | https://github.com/Adaptix-Framework/Extension-Kit |
| axc2 module | `github.com/Adaptix-Framework/axc2` v1.2.0 |
