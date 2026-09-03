# Go plugin patterns

Use these patterns after pinning the Adaptix source and reading the current `axc2/v2` declarations with `go doc`.

## Contents

- [Exact entry points](#exact-entry-points)
- [Agent contract](#agent-contract)
- [Listener contract](#listener-contract)
- [Service contract](#service-contract)
- [Hooks, routes, and storage](#hooks-routes-and-storage)
- [Loader and activation checks](#loader-and-activation-checks)

## Exact entry points

The loader type-asserts the exported symbol to one exact function type:

```go
// Agent
func InitPlugin(ts any, moduleDir string, watermark string) adaptix.PluginAgent

// Listener
func InitPlugin(ts any, moduleDir string, listenerDir string) adaptix.PluginListener

// Service
func InitPlugin(ts any, moduleDir string, serviceConfig string) adaptix.PluginService
```

Return `nil` if `ts` does not implement `adaptix.Teamserver`; a panic in `InitPlugin` can affect the Teamserver process. Add a compile-time assertion beside each implementation:

```go
var _ adaptix.PluginService = (*Plugin)(nil)

func InitPlugin(ts any, moduleDir, serviceConfig string) adaptix.PluginService {
    api, ok := ts.(adaptix.Teamserver)
    if !ok {
        return nil
    }
    return NewPlugin(api, moduleDir, serviceConfig)
}
```

Build on the Teamserver's target OS. Go plugins require compatible Go toolchains, build flags, and shared dependency versions between host and plugin; keep the plugin in the same workspace/module graph when possible.

## Extender source layout

Verified against `AdaptixServer/extenders/{gopher_agent,beacon_agent,beacon_listener_http}` on the pinned baseline. Names are conventions, not framework requirements, but current tooling and reference extenders assume them:

```text
extenders/<name>_agent/
    config.yaml         # extender_type, agent_name, watermark, listeners
    ax_config.axs       # AxScript: RegisterCommands, GenerateUI
    axtool.spec         # package metadata
    go.mod / go.sum     # module adaptix_agent_<name>
    Makefile            # builds dist/agent_<name>.so + implant
    pl_main.go          # InitPlugin, PluginAgent methods, AgentFunctions wiring
    pl_utils.go         # helpers (build env, formatting)
    pl_packer.go        # optional (beacon pattern): shellcode packing
    pl_sideloading.go   # optional (beacon pattern): sideloading
    src_<name>/         # implant source tree with its own Makefile

extenders/<name>_listener_<proto>/
    config.yaml         # extender_type, listener_name, listener_type, protocol
    ax_config.axs       # AxScript: ListenerUI
    axtool.spec
    go.mod / go.sum     # module adaptix_listener_<name>_<proto>
    Makefile            # builds dist/listener_<name>_<proto>.so
    pl_main.go          # InitPlugin, PluginListener, ExtenderListener methods
    pl_transport.go     # transport + agent registration flow

extenders/<name>_service/
    config.yaml         # extender_type, service_name, service_config
    ax_config.axs       # optional AxScript: RegisterServiceCommands + docks/dialogs
    axtool.spec
    go.mod / go.sum     # module adaptix_service_<name>
    Makefile
    pl_main.go          # InitPlugin, PluginService (Call + CallRPC)
```

No service extender ships in-tree on the verified baseline; the loader (`AdaptixServer/core/extender/ex_service.go`) is active and expects the layout above.

## Agent contract

```go
type PluginAgent interface {
    GenerateProfiles(BuildProfile) ([][]byte, error)
    BuildPayload(BuildProfile, [][]byte) ([]byte, string, error)
    CreateAgent(beat []byte) (AgentData, AgentFunctions, error)
    AgentRestore(AgentData) AgentFunctions
    Call(operator string, agentID int64, function, args string)
}
```

### Restore is authoritative

Use one callback factory from both paths:

```go
func (p *Plugin) CreateAgent(beat []byte) (adaptix.AgentData, adaptix.AgentFunctions, error) {
    data, err := p.parseRegistration(beat)
    if err != nil {
        return adaptix.AgentData{}, adaptix.AgentFunctions{}, fmt.Errorf("parse registration: %w", err)
    }
    return data, p.functionsFor(data), nil
}

func (p *Plugin) AgentRestore(data adaptix.AgentData) adaptix.AgentFunctions {
    return p.functionsFor(data)
}
```

Use the callback factory and incompatible-data policy defined by the [agent state machine](architecture-and-lifecycle.md#agent). Keep sufficient versioned state in `AgentData.CustomData` for that reconstruction.

Populate every callback that the agent supports. `adaptix.NewAgent` replaces missing required callbacks with error-returning stubs, so nil fields defer a defect until runtime rather than disabling the feature cleanly.

Before parsing a beat or callback:

1. enforce a maximum frame size;
2. check the minimum header length;
3. decode length fields without overflow;
4. verify each declared segment fits the remaining buffer;
5. reject trailing data unless the protocol explicitly permits it.

### Command arguments

Use the v2 argument helpers, then apply domain constraints:

```go
path, err := adaptix.GetStringArg(args, "path")
if err != nil {
    return adaptix.TaskData{}, adaptix.ConsoleMessageData{}, fmt.Errorf("path: %w", err)
}

mode := adaptix.GetStringArgDefault(args, "mode", "read")
if mode != "read" && mode != "stat" {
    return adaptix.TaskData{}, adaptix.ConsoleMessageData{}, fmt.Errorf("unsupported mode %q", mode)
}
```

`GetStringArgDefault` returns one value. `GetBoolArg` also returns one value and cannot distinguish absent from false; decode into a typed struct when presence matters. `GetFileArg` returns decoded bytes, which still need a size limit.

Unknown commands must produce an explicit error. Check byte lengths before diagnostic previews or slices; avoid patterns such as `data[:8]` unless `len(data) >= 8` is established.

### Payload build

`BuildProfile.AgentConfig` is client-supplied JSON. Decode it into a typed, versioned schema and reject excess size, unknown fields, unsafe paths, and unsupported enum combinations before starting a process.

```go
func decodeBuildConfig(raw string) (BuildConfig, error) {
    const maxConfig = 64 << 10
    if len(raw) > maxConfig {
        return BuildConfig{}, fmt.Errorf("agent config exceeds %d bytes", maxConfig)
    }

    var cfg BuildConfig
    dec := json.NewDecoder(strings.NewReader(raw))
    dec.DisallowUnknownFields()
    if err := dec.Decode(&cfg); err != nil {
        return BuildConfig{}, fmt.Errorf("decode agent config: %w", err)
    }
    var extra any
    if err := dec.Decode(&extra); !errors.Is(err, io.EOF) {
        return BuildConfig{}, errors.New("agent config contains trailing data")
    }
    return cfg, cfg.Validate()
}
```

Use a per-build working directory and one cleanup owner:

```go
workDir, err := os.MkdirTemp("", "adaptix-build-*")
if err != nil {
    return nil, "", fmt.Errorf("create build directory: %w", err)
}
defer os.RemoveAll(workDir)
```

Copy required sources into that directory, generate configuration there, invoke an allowlisted executable directly, and read the expected output from the same directory. Do not map a client string to an executable or pass generated shell text to `sh -c`.

Return `content, filename, nil` from `BuildPayload` and follow the canonical [build ownership](architecture-and-lifecycle.md#build-ownership); do not deliver or close the outer build channel from the plugin.

`TsAgentBuildExecute(builderID, workingDir, env, program, args...)` inherits the Teamserver environment when `env` is nil. A non-nil `env` replaces the whole environment; merge or construct all required variables explicitly.

Builds can overlap. Never share a mutable source tree, output path, process environment, or package-level build state.

## Listener contract

```go
type PluginListener interface {
    Create(name, config string, customData []byte) (ExtenderListener, ListenerData, []byte, error)
    Call(operator, listenerName, function, args string)
}

type ExtenderListener interface {
    Start() error
    Edit(config string) (ListenerData, []byte, error)
    Stop() error
    GetProfile() ([]byte, error)
    InternalHandler(data []byte) (int64, error)
}
```

Validate configuration completely in `Create` before reserving external resources. Give each returned instance its own mutex, context/cancel pair, wait group, server/socket handles, and immutable identity.

Lifecycle rules:

- `Start` initializes a fresh context and resources, publishes running state only after success, and cleans up a partial start on error.
- `Stop` swaps the instance to stopped, cancels work, closes owned handles, waits with a bound, and is safe when already stopped.
- `Edit` validates first; either apply an explicitly safe live change or stop/reconfigure/restart with clear rollback behavior.
- `GetProfile` returns a versioned agent-facing transport schema. Include only implant-required bootstrap/keying material, exclude server-only secrets such as TLS private keys, and treat the result as sensitive.
- `InternalHandler` validates input before delegating to `TsAgentCreate` or `TsAgentProcessData` and returns an `int64` agent ID.

Set `AgentData.Async` according to transport behavior. Polling HTTP/DNS-style sessions are asynchronous; persistent linked/TCP-style sessions are normally synchronous. Verify this choice against the current in-tree listener closest to the protocol.

Apply the current [listener state machine](architecture-and-lifecycle.md#listener), including its start-failure verification rule.

## Service contract

```go
type PluginService interface {
    Call(operator, function, args string)
    CallRPC(operator, function, args string) (string, error)
}
```

Decode a common envelope with a required operation and request ID. Keep the dispatch table explicit:

```go
switch function {
case "job.start":
    p.startJob(operator, args)
case "job.cancel":
    p.cancelJob(operator, args)
default:
    p.sendError(operator, requestID(args), "unsupported operation")
}
```

`Call` has no return channel. Send asynchronous JSON results with `TsPluginServiceSendDataClient(operator, serviceName, data)` or, only when intended, `TsPluginServiceSendDataAll`. Include `request_id`, terminal state, and a stable error code.

`CallRPC` returns JSON directly. Apply the canonical [failure contract](architecture-and-lifecycle.md#failure-contract): use an internal deadline where work is cancellable, bound concurrent calls, and define the late-result policy.

The connector already invokes service calls concurrently. Do not start an unbounded goroutine per request. Protect plugin maps and state; avoid holding locks across Teamserver calls or slow I/O.

## Hooks, routes, and storage

Event hook handlers receive `any`, while concrete event payloads live in Teamserver-internal packages. Do not import those internal types or publish source-coupled assertions as a stable extender API. For a required hook, inspect the pinned emitter, validate the dynamic value conservatively, and unregister the hook during plugin-owned teardown.

Use namespaced endpoint paths and unregister them on teardown. Non-raw endpoint handlers receive an already-buffered body with no plugin-selected maximum; use a raw handler when an explicit request limit is required. Prefer authenticated endpoints. Public endpoints need a concrete protocol requirement and their own authentication/anti-replay design.

Use a constant extender storage namespace. Treat keys and values as untrusted, version serialized records, and bound their size. The namespace argument routes data; it is not an authorization boundary.

## Loader and activation checks

Agent and listener registration require their AxScript file. A service may load when its AxScript is absent, but the server logs a warning and clients will not receive its UI definition. Loader errors are logged and startup continues.

After activation, verify all applicable evidence:

- successful plugin open and exact `InitPlugin` signature;
- expected agent/listener/service catalog entry;
- AxScript command metadata on the server;
- UI availability after reconnect/resync;
- one success and one deliberate failure path;
- cleanup behavior or documented Teamserver restart requirement.

### Command / handler parity gate

Run before the compile gate. These couplings are enforced only at runtime and produce silent no-ops on mismatch:

- every `ax.create_command("name", ...)` in `ax_config.axs` -> one `case "name":` in `CreateCommand`;
- every `case` in `CreateCommand` that emits a task -> one response branch in the `ProcessData` dispatch;
- every entry in `config.yaml -> listeners: [...]` of an agent -> a real installed listener whose `config.yaml -> listener_name` matches exactly;
- `config.yaml -> extender_file` -> the Makefile `.so` output byte-for-byte;
- every `ax.plugin_agent_command`/`ax.plugin_listener_command`/`ax.plugin_service_command` name in AxScript -> one handled branch in the plugin's `Call`/`CallRPC`.

For runtime removal, follow the [service state machine](architecture-and-lifecycle.md#service) and verify the documented restart/teardown path.
