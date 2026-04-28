# Plugin Implementation Patterns

Detailed Go code patterns for agent, listener, and service plugins.

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
