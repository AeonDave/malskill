# Plugin Implementation Patterns

Detailed Go code patterns for agent, listener, and service plugins (axc2/v2).

---

## Agent — CreateCommand Pattern

`CreateCommand` receives the `args` map from AxScript. Use `adaptix.GetStringArg` etc. instead of raw assertions.

```go
func CreateCommand(agentData adaptix.AgentData, args map[string]any) (adaptix.TaskData, adaptix.ConsoleMessageData, error) {
    command, _ := adaptix.GetStringArg(args, "command")
    subcommand, _ := adaptix.GetStringArgDefault(args, "subcommand", "")

    var taskData adaptix.TaskData
    var msgData  adaptix.ConsoleMessageData

    switch command {
    case "shell":
        cmdStr, err := adaptix.GetStringArg(args, "command_line")
        if err != nil {
            return taskData, msgData, err
        }
        packed, _ := PackArray([]interface{}{COMMAND_SHELL, cmdStr})
        taskData = adaptix.TaskData{Type: adaptix.TASK_TYPE_TASK, Data: packed}
        msgData  = adaptix.ConsoleMessageData{Message: "Task: shell", Status: adaptix.MESSAGE_INFO}

    case "download":
        path, err := adaptix.GetStringArg(args, "file")
        if err != nil {
            return taskData, msgData, err
        }
        fileId := Ts.TsFileGenID()
        packed, _ := PackArray([]interface{}{COMMAND_DOWNLOAD, fileId, path})
        taskData = adaptix.TaskData{Type: adaptix.TASK_TYPE_TASK, Data: packed}
        msgData  = adaptix.ConsoleMessageData{Message: "Task: download", Status: adaptix.MESSAGE_INFO}
    }
    return taskData, msgData, nil
}
```

---

## Agent — ProcessData Pattern

```go
func ProcessData(agentData adaptix.AgentData, data []byte) error {
    var msg Message
    if err := Unmarshal(data, &msg); err != nil {
        return err
    }
    for _, raw := range msg.Object {
        var cmd Command
        Unmarshal(raw, &cmd)
        switch cmd.Code {
        case COMMAND_SHELL:
            taskData := adaptix.TaskData{
                TaskId:      cmd.TaskId,
                AgentId:     agentData.Id,
                MessageType: adaptix.MESSAGE_SUCCESS,
                Message:     string(cmd.Data),
                Completed:   true,
            }
            Ts.TsTaskUpdate(agentData.Id, taskData)

        case COMMAND_DOWNLOAD_INIT:
            fileId, _ := UnpackInt64(cmd.Data[:8])
            name := string(cmd.Data[8:])
            Ts.TsDownloadAdd(agentData.Id, fileId, name, cmd.TotalSize)

        case COMMAND_DOWNLOAD_DATA:
            fileId, _ := UnpackInt64(cmd.Data[:8])
            Ts.TsDownloadUpdate(fileId, adaptix.TRANSFER_STATE_RUNNING, cmd.Data[8:])

        case COMMAND_DOWNLOAD_DONE:
            fileId, _ := UnpackInt64(cmd.Data[:8])
            Ts.TsDownloadClose(fileId, adaptix.TRANSFER_STATE_FINISHED)
        }
    }
    return nil
}
```

---

## Agent — AgentFunctions Struct

`CreateAgent` initializes per-session state and returns `AgentFunctions`. `AgentRestore` must return an equivalent struct for sessions reloaded from DB. Both use closures over the same state.

```go
func (p *PluginAgent) CreateAgent(beat []byte) (adaptix.AgentData, adaptix.AgentFunctions, error) {
    agentData, err := ParseBeat(beat)
    if err != nil {
        return adaptix.AgentData{}, adaptix.AgentFunctions{}, err
    }
    return agentData, buildFunctions(), nil
}

func (p *PluginAgent) AgentRestore(agentData adaptix.AgentData) adaptix.AgentFunctions {
    return buildFunctions()  // must return same set as CreateAgent
}

func buildFunctions() adaptix.AgentFunctions {
    return adaptix.AgentFunctions{
        CreateCommand: CreateCommand,
        ProcessData:   ProcessData,
        PackTasks:     PackTasks,
        Encrypt:       Encrypt,
        Decrypt:       Decrypt,
        PivotPackData: PivotPackData,
        TunnelCB: adaptix.TunnelCallbacks{
            ConnectTCP: TunnelMessageConnectTCP,
            ConnectUDP: TunnelMessageConnectUDP,
            WriteTCP:   TunnelMessageWriteTCP,
            WriteUDP:   TunnelMessageWriteUDP,
            Pause:      TunnelMessagePause,
            Resume:     TunnelMessageResume,
            Close:      TunnelMessageClose,
            Reverse:    TunnelMessageReverse,
        },
        TerminalCB: adaptix.TerminalCallbacks{
            Start: TerminalMessageStart,
            Write: TerminalMessageWrite,
            Close: TerminalMessageClose,
        },
    }
}
```

---

## Listener — Agent Registration & Callback Flow

### Registration (external listener)

```go
func (l *Listener) serveHTTP(w http.ResponseWriter, r *http.Request) {
    body, _ := io.ReadAll(r.Body)

    // Attempt to look up existing agent by UID
    uid := extractUID(body)
    agentId, exists := Ts.TsAgentIdByUID(uid)

    if !exists {
        // New agent registering
        agentData, err := Ts.TsAgentCreate(AgentCrc, uid, body, l.Name, r.RemoteAddr, false)
        if err != nil {
            http.Error(w, "bad beat", 400)
            return
        }
        agentId = agentData.Id
    }
    Ts.TsAgentSetTick(agentId, l.Name)

    // Process inbound data
    if len(body) > UIDLen {
        Ts.TsAgentProcessData(agentId, body[UIDLen:])
    }

    // Build response with hosted tasks
    packed, _, err := Ts.TsAgentGetHostedAll(agentId, MaxDataSize)
    if err != nil || len(packed) == 0 {
        packed, _ = Ts.TsAgentBuildEmptyTasks(agentId)
    }
    w.Write(packed)
}
```

### Internal listener (pivot)

```go
func (l *Listener) InternalHandler(data []byte) (int64, error) {
    uid := extractUID(data)
    agentId, exists := Ts.TsAgentIdByUID(uid)
    if !exists {
        agentData, err := Ts.TsAgentCreate(AgentCrc, uid, data, l.Name, "", true)
        if err != nil {
            return 0, err
        }
        return agentData.Id, nil
    }
    return agentId, Ts.TsAgentProcessData(agentId, data[UIDLen:])
}
// Note: return type is int64 (agent ID), not string — v2 change
```

---

## Service — Call and CallRPC Dispatch

```go
func (p *PluginService) Call(operator string, function string, args string) {
    switch function {
    case "compile":
        go func() {  // fire-and-forget; do work async
            var req CompileRequest
            json.Unmarshal([]byte(args), &req)
            result := compile(req)
            resultJson, _ := json.Marshal(result)
            Ts.TsPluginServiceSendDataClient(operator, ServiceName, string(resultJson))
        }()

    case "status":
        Ts.TsPluginServiceSendDataAll(ServiceName, `{"status":"ok"}`)
    }
}

// CallRPC: synchronous — caller blocks until this returns
func (p *PluginService) CallRPC(operator string, function string, args string) (string, error) {
    switch function {
    case "validate":
        var req ValidationRequest
        if err := json.Unmarshal([]byte(args), &req); err != nil {
            return "", err
        }
        ok := validate(req)
        return fmt.Sprintf(`{"valid":%v}`, ok), nil
    }
    return "", fmt.Errorf("unknown function: %s", function)
}
```

### Important: routing

- `ax.service_command(name, fn, data)` → `Call(operator, fn, data)` — fire-and-forget
- `ax.service_command_rpc(name, fn, data)` → `CallRPC(operator, fn, data)` — sync return
- Service `name` in AxScript, `TsPluginServiceSendDataClient`, and `config.yaml:service_name` must match exactly.
- Do not call `TsPluginServiceCallWait` on the same service from inside its own `Call/CallRPC` — deadlocks.

---

## Adding a New Command (End-to-End)

1. **ax_config.axs** — define command and args: `let cmd = ax.create_command("mycmd", ...)` + add to group
2. **pl_utils.go** — add `COMMAND_MYCMD` constant + request/response structs
3. **pl_main.go CreateCommand** — add `case "mycmd":` — marshal args → `TaskData.Data`
4. **pl_main.go ProcessData** — add `case COMMAND_MYCMD:` — unmarshal response, call Ts methods
5. **Implant** — add handler in implant `tasks.go` / `tasks.cpp` / `tasks.rs`
6. **AgentRestore** — if CreateCommand uses new state, ensure AgentRestore returns it
7. Validate: `go vet ./...`

## Wrapper Service (Post-Build Pipeline)

```go
func InitPlugin(ts any, moduleDir string, serviceConfig string) adaptix.PluginService {
    Ts = ts.(adaptix.Teamserver)
    hookId = Ts.TsEventHookOnPost("agent.generate", "wrapper_post_build",
        func(event any) error {
            ev := event.(*AgentGenerateEvent)
            ev.Payload = transform(ev.Payload)   // modify in-place
            return nil
        })
    return &PluginService{}
}
```

## Build Channel Pattern

Used when `BuildPayload` needs to stream progress to the UI:

```go
func (p *PluginAgent) BuildPayload(profile adaptix.BuildProfile, agentProfiles [][]byte) ([]byte, string, error) {
    Ts.TsAgentBuildLog(profile.BuilderId, adaptix.BUILD_LOG_INFO, "Compiling...")
    err := Ts.TsAgentBuildExecute(profile.BuilderId, buildDir, nil, "make", "all")
    if err != nil {
        Ts.TsAgentBuildLog(profile.BuilderId, adaptix.BUILD_LOG_ERROR, err.Error())
        return nil, "", err
    }
    content, _ := os.ReadFile(filepath.Join(buildDir, "output.bin"))
    Ts.TsAgentBuildSendFile(profile.BuilderId, "agent.bin", content)
    Ts.TsAgentBuildLog(profile.BuilderId, adaptix.BUILD_LOG_SUCCESS, "Done")
    // TsAgentBuildClose is called by the server after BuildPayload returns
    return content, "agent.bin", nil
}
```

---

## Agent — CreateCommand Pattern

Every command in `ax_config.axs` needs a matching case in `CreateCommand`:

```go
func (ext *Extender) CreateCommand(agentData adaptix.AgentData, args map[string]any) (adaptix.TaskData, adaptix.ConsoleMessageData, error) {
    command, _ := args["command"].(string)
    subcommand, _ := args["subcommand"].(string)

    switch command {
    case "shell":
        cmdStr, _ := args["command_line"].(string)
        // Marshal into wire format, return TaskData with .Data = serialized bytes
    case "download":
        path, _ := args["remote_path"].(string)
        // ...
    }
    return taskData, messageData, nil
}
```

## Agent — ProcessData Pattern

```go
func (ext *Extender) ProcessData(agentData adaptix.AgentData, data []byte) error {
    var msg Message
    Unmarshal(data, &msg)
    for _, raw := range msg.Object {
        var cmd Command
        Unmarshal(raw, &cmd)
        switch cmd.Code {
        case COMMAND_SHELL:
            Ts.TsTaskUpdate(agentData.Id, taskData)
        case COMMAND_DOWNLOAD:
            Ts.TsDownloadUpdate(agentData.Id, downloadData)
        }
    }
    return nil
}
```

## Listener — Agent Registration & Callback Flow

### Registration flow

```
receive beat → Ts.TsAgentCreate() → return sessions
```

### Callback flow

```
receive packet → decrypt → Ts.TsAgentProcessData() → get tasks
→ Ts.TsAgentGetHostedAll() → encrypt → respond
```

## Service — Call Dispatch Pattern

```go
func (p *Plugin) Call(operator string, function string, args string) {
    switch function {
    case "compile":
        var req CompileRequest
        json.Unmarshal([]byte(args), &req)
        // process...
        Ts.TsServiceSendDataClient(serviceName, operator, "compile_done", resultJson)
    case "load_settings":
        // ...
    }
}
```

### Important: service name routing

The name in `ax.service_command(...)` (axscript) and `TsServiceSendDataClient/TsServiceSendDataAll` (plugin) must match `config.yaml → service_name` exactly. Mismatches cause silent routing failures.

---

## Adding a New Command (End-to-End)

1. **ax_config.axs**: `let cmd = ax.create_command("mycmd", "desc", "mycmd arg1")` + add to group
2. **pl_utils.go**: Add `COMMAND_MYCMD` constant + request/response structs
3. **pl_main.go CreateCommand**: Add `case "mycmd":` — marshal args into wire struct
4. **pl_main.go ProcessData**: Add `case COMMAND_MYCMD:` — unmarshal response, call Ts methods
5. **Implant**: Add handler in implant `tasks.go` / `tasks.cpp` / `tasks.rs`
6. Validate: `go vet`, check placeholder leaks

## Adding a New Protocol

1. Run `.\generator.ps1 -Mode protocol` → creates `protocols/<name>/`
2. Implement `crypto.go.tmpl` (encrypt/decrypt), `constants.go.tmpl`, `types.go.tmpl`
3. Update `meta.yaml`
4. Add `pl_main.go.tmpl` / `pl_transport.go.tmpl` overrides if needed
5. Add implant overlays in `implant/` if needed (Go root, C++ in `cpp/`, Rust in `rust/`)
6. Generate agent + listener with `-Protocol <name>`, validate with `go vet`

## Wrapper Service (Post-Build Pipeline)

1. Generate: `.\service\generator.ps1 -Name <name> -Wrapper`
2. Implement stages in `pl_wrapper.go`
3. Hook `agent.generate` event to intercept payload after build
4. `Ts.TsServiceSendDataClient()` for per-client updates

## Multi-Language Build Support

`pl_build.go` switches on `Language` field:
- Go: `go build` with cross-compilation env vars
- C++: `make` with MinGW/Clang toolchain
- Rust: `cargo build` with target flags, optional LLVM obfuscation via linker-plugin-lto

Rust LLVM obfuscation requires: `-C link-arg=-fuse-ld=lld` and `-C link-arg=-Wl,-mllvm,<flag>` routing.
