---
name: adaptixc2-dev
description: >
  Develop, extend, and maintain AdaptixC2 extenders (agents, listeners, services)
  and their template generators. Use when creating new plugins, adding commands,
  building beacon/listener/service implementations, writing AxScript UI, designing
  wire protocols, or using the Template-Generators scaffold system. Covers the full
  plugin lifecycle: Go plugin API (axc2 v1.2.0), AxScript forms/commands/events/menus,
  config.yaml wiring, Teamserver interface, protocol overlays, multi-language implant
  builds (Go/C++/Rust), evasion gates, and validation workflows.
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

## 1 — Creating an Agent Plugin

### File structure

```
<name>_agent/
├── config.yaml          # extender_type: "agent"
├── ax_config.axs        # AxScript UI + command definitions
├── go.mod               # requires axc2 v1.2.0
├── Makefile             # go build -buildmode=plugin
├── pl_main.go           # InitPlugin, PluginAgent, ExtenderAgent
├── pl_build.go          # GenerateProfiles, BuildPayload (one per language)
├── pl_utils.go          # Wire types, crypto, helpers
├── srdi.go              # (Rust only) DLL→shellcode sRDI converter
└── src_<name>/          # Implant source tree
```

### Required interfaces

```go
// PluginAgent — returned by InitPlugin
type PluginAgent interface {
    GenerateProfiles(profile adaptix.BuildProfile) ([][]byte, error)
    BuildPayload(profile adaptix.BuildProfile, agentProfiles [][]byte) ([]byte, string, error)
    CreateAgent(beat []byte) (adaptix.AgentData, adaptix.ExtenderAgent, error)
    GetExtender() adaptix.ExtenderAgent
}

// ExtenderAgent — per-session handler
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
3. Implement `CreateCommand` switch cases — one case per command registered in `ax_config.axs`
4. Implement `ProcessData` response handler — one case per response code in protocol constants
5. Implement `GenerateProfiles` — serialize listener profiles into agent-readable config blobs
6. Implement `BuildPayload` — invoke build toolchain, return compiled binary
7. Implement implant source in `src_<name>/`
8. Validate in WSL: `go mod tidy && go vet ./...`
9. Verify zero placeholder leaks: `Select-String -Path *.go -Pattern '__[A-Z_]+__'`

### CreateCommand pattern

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

### ProcessData pattern

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

### config.yaml

```yaml
extender_type: "agent"
extender_file: "agent_<name>.so"
ax_file: "ax_config.axs"
agent_name: "<name>"
agent_watermark: "<hex8>"
listeners:
  - "<NameCap><ProtoCap>"    # e.g. "BeaconSpectre"
multi_listeners: false
```

---

## 2 — Creating a Listener Plugin

### File structure

```
<name>_listener/
├── config.yaml          # extender_type: "listener"
├── ax_config.axs        # UI form for listener creation
├── go.mod, Makefile
├── pl_main.go           # InitPlugin, PluginListener
├── pl_transport.go      # Network transport (HTTP, TCP, SMB, DNS, etc.)
├── pl_utils.go          # Wire utilities
├── pl_crypto.go         # Encrypt/Decrypt functions
├── pl_internal.go       # Internal listener registration (optional)
└── map.go               # Concurrent connection maps
```

### Required interfaces

```go
// PluginListener — returned by InitPlugin
type PluginListener interface {
    Create(name string, config string, customData []byte) (adaptix.ExtenderListener, adaptix.ListenerData, []byte, error)
}

// ExtenderListener — live listener instance
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
4. Implement agent registration flow: receive beat → `Ts.TsAgentCreate()` → return sessions
5. Implement agent callback flow: receive packet → decrypt → `Ts.TsAgentProcessData()` → get tasks → `Ts.TsAgentGetHostedAll()` → encrypt → respond
6. Implement `Stop()` — graceful shutdown
7. Implement `GetProfile()` — serialize crypto keys + config for agent embedding
8. Validate in WSL: `go mod tidy && go vet ./...`

### config.yaml

```yaml
extender_type: "listener"
extender_file: "listener_<name>.so"
ax_file: "ax_config.axs"
listener_name: "<NameCap><ProtoCap>"
listener_type: "external"    # or "internal"
protocol: "http"             # transport protocol identifier
```

### Listener types

- **external**: Binds a network port. Agent connects directly. Most common.
- **internal**: No network port. Used for pivot/linked agents. `InternalHandler()` processes data relayed by other agents.

---

## 3 — Creating a Service Plugin

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

### Important: service name routing

The name in `ax.service_command(...)` (axscript) and `TsServiceSendDataClient/TsServiceSendDataAll` (plugin) must match `config.yaml → service_name` exactly. Mismatches cause silent routing failures.

---

## 4 — AxScript (ax_config.axs)

AxScript is JavaScript (Goja engine) with bridge APIs for UI, commands, menus, and events. Files are loaded from `ax_file` in config.yaml. **Each plugin type has a different required lifecycle.**

### 4.1 — Three .axs Lifecycles

#### Agent .axs lifecycle

Agent `.axs` files must define two functions and register menus/events at top level:

```javascript
// REQUIRED: Define CLI commands. Called by framework with the listener type string.
function RegisterCommands(listenerType) {
    let cmd_shell = ax.create_command("shell", "Run shell cmd", "shell whoami", "Task: shell");
    cmd_shell.addArgString("cmd_params", true, "Command");

    let cmd_sleep = ax.create_command("sleep", "Set sleep", "sleep 5s 20");
    cmd_sleep.addArgString("interval", true, "Duration");
    cmd_sleep.addArgInt("jitter", false, "Jitter %");

    let win = ax.create_commands_group("<agent_name>", [cmd_shell, cmd_sleep]);
    let unix = ax.create_commands_group("<agent_name>", [cmd_sleep]);

    // MUST return this structure:
    return {
        commands_windows: win,
        commands_linux:   unix,
        commands_macos:   unix
    };
}

// REQUIRED: Build the "Generate Agent" dialog form.
// Receives array of listener type strings (e.g. ["BeaconHTTP", "BeaconSMB"]).
function GenerateUI(listeners_type) {
    let container = form.create_container();
    let layout = form.create_gridlayout();
    // ... build form ...
    let panel = form.create_panel();
    panel.setLayout(layout);

    // MUST return this structure:
    return {
        ui_panel:     panel,       // the root panel widget
        ui_container: container,   // framework calls container.toJson() on OK
        ui_height:    400,         // dialog height
        ui_width:     600          // dialog width
    };
}

// TOP-LEVEL: Register menus and events (imperative, outside functions)
let action_fb = menu.create_action("Download", function(files) { ... });
menu.add_filebrowser(action_fb, ["<agent_name>"]);
event.on_filebrowser_list(function(id, path) { ax.execute_browser(id, "ls " + path); }, ["<agent_name>"]);
event.on_filebrowser_disks(function(id) { ax.execute_browser(id, "disks"); }, ["<agent_name>"]);
event.on_processbrowser_list(function(id) { ax.execute_browser(id, "ps list"); }, ["<agent_name>"]);
```

#### Listener .axs lifecycle

Listener `.axs` files must define one function:

```javascript
// REQUIRED: Build the listener configuration form.
// mode_create: true = new listener, false = viewing/editing existing.
function ListenerUI(mode_create) {
    let container = form.create_container();
    let layout = form.create_gridlayout();

    let txtHost = form.create_textline("0.0.0.0");
    let spinPort = form.create_spin();
    spinPort.setRange(1, 65535);
    spinPort.setValue(443);

    layout.addWidget(form.create_label("Bind Host:"), 0, 0, 1, 1);
    layout.addWidget(txtHost, 0, 1, 1, 1);
    layout.addWidget(form.create_label("Bind Port:"), 1, 0, 1, 1);
    layout.addWidget(spinPort, 1, 1, 1, 1);

    container.put("host", txtHost);
    container.put("port", spinPort);

    let panel = form.create_panel();
    panel.setLayout(layout);

    // MUST return this structure:
    return {
        ui_panel:     panel,
        ui_container: container,
        ui_height:    300,
        ui_width:     500
    };
}
```

#### Service .axs lifecycle

Service `.axs` files must define three functions and end with the boot call:

```javascript
var serviceName = "<ServiceNameV2>";   // must match config.yaml → service_name
var g_output_widget = null;

// REQUIRED: Called once when plugin loads.
function InitService() {
    ax.log("Service loaded.");
    // Load persisted settings from Go side:
    ax.service_command(serviceName, "load_settings", null);
    // Register menu entries:
    let action = menu.create_action("Open Tool", function() { buildMainWindow(); });
    menu.add_main_axscript(action);
}

// REQUIRED: Called after InitService. Usually minimal.
function ServiceUI() {
    ax.log("Service UI ready.");
}

// REQUIRED: Receives async responses from Go plugin.
// Go calls TsServiceSendDataClient(serviceName, client, function, jsonArgs)
// → arrives here as a JSON string.
function data_handler(data) {
    let response = JSON.parse(data);
    switch (response.action) {
        case "load_settings_result":
            // restore settings
            break;
        case "compile_log":
            if (g_output_widget !== null) {
                g_output_widget.appendText(response.output);
            }
            break;
        case "compile_done":
            if (response.success && response.file_content) {
                let path = ax.prompt_save_file(response.file_name || "output.exe");
                if (path && path !== "") ax.file_write_binary(path, response.file_content);
            }
            break;
    }
}

// ... buildMainWindow() and other functions ...

// REQUIRED: Boot statement — must be last line in the file.
ServiceUI();
```

**Key service data flow**: `ax.service_command()` is fire-and-forget. The Go plugin's `Call()` method processes the request, then pushes results back via `TsServiceSendDataClient()`, which arrives at `data_handler(data)` as JSON. There is NO request-response mechanism — all communication is asynchronous. Dispatch responses using an `action` field in the JSON.

### 4.2 — UI Layout Patterns

#### GroupBox + Panel (the standard section pattern)

Every form section uses this pattern — **always `groupbox.setPanel(panel)`**, never `setLayout` directly on groupbox:

```javascript
let grid = form.create_gridlayout();
grid.addWidget(form.create_label("Name:"), 0, 0, 1, 1);
grid.addWidget(txtName, 0, 1, 1, 1);

let panel = form.create_panel();
panel.setLayout(grid);

let grp = form.create_groupbox("Section Title", false);  // false = not checkable
grp.setPanel(panel);
```

#### Checkable GroupBox (toggle section)

Pass `true` as second arg to make it checkable — acts like a collapsible toggle:

```javascript
let grp = form.create_groupbox("Use Proxy", true);   // true = checkable
grp.setPanel(panel);
grp.setChecked(false);         // initially collapsed/disabled

// Toggle child enable state:
form.connect(grp, "clicked", function(checked) {
    panel.setEnabled(checked);
});

// In a container, serializes as boolean:
container.put("use_proxy", grp);  // → {"use_proxy": true/false}
```

#### ScrollArea (for tall forms)

Wrap content in a scrollarea when the form exceeds dialog height:

```javascript
let mainLayout = form.create_vlayout();
mainLayout.addWidget(grp1);
mainLayout.addWidget(grp2);
mainLayout.addWidget(grp3);

let innerPanel = form.create_panel();
innerPanel.setLayout(mainLayout);

let scroll = form.create_scrollarea();
scroll.setPanel(innerPanel);      // NOTE: setPanel(), not setWidget()

let outerLayout = form.create_vlayout();
outerLayout.addWidget(scroll);

// For agent/listener, return outerPanel:
let outerPanel = form.create_panel();
outerPanel.setLayout(outerLayout);
// For services, use as dialog layout directly
```

#### Stack + Segmented Control (tab interface)

> `create_segcontrol` is NOT in official docs — discovered in source code. Use with caution.

```javascript
let controller = form.create_segcontrol();
controller.addItems(["Main", "Headers", "Advanced"]);

let stack = form.create_stack();
stack.addPage(panel1);
stack.addPage(panel2);
stack.addPage(panel3);
stack.setCurrentIndex(0);

form.connect(controller, "currentIndexChanged", function() {
    stack.setCurrentIndex(controller.currentIndex());
});
```

#### Dialog types

```javascript
// Standard modal dialog (blocks until closed)
let dialog = form.create_dialog("Title");
dialog.setSize(600, 400);
dialog.setLayout(layout);
dialog.setButtonsText("Save", "Cancel");    // customize button labels
let accepted = dialog.exec();               // returns true if OK/Save clicked
if (accepted) { /* persist settings */ }

// Extended dialog (for service/tool windows)
let ext = form.create_ext_dialog("Title");
ext.setSize(600, 400);
ext.setButtonsText("Close", "");   // "" hides the cancel button
ext.exec();
```

### 4.3 — Signal connection patterns

```javascript
// Button click
form.connect(btn, "clicked", function() { /* ... */ });

// Checkbox toggle → show/hide dependent fields
form.connect(chk, "stateChanged", function() {
    let checked = chk.isChecked();
    lbl.setVisible(checked);
    txt.setVisible(checked);
});

// Combo selection change (receives new text)
form.connect(combo, "currentTextChanged", function(text) {
    chk.setEnabled(text.toLowerCase() !== "bin");
});

// Checkable groupbox toggle
form.connect(grp, "clicked", function(checked) {
    panel.setEnabled(checked);
});

// Segmented control tab switch
form.connect(segctrl, "currentIndexChanged", function() {
    stack.setCurrentIndex(segctrl.currentIndex());
});

// Mutual exclusion between checkboxes
form.connect(chkA, "stateChanged", function() {
    if (chkA.isChecked()) { chkB.setChecked(false); chkB.setEnabled(false); }
    else { chkB.setEnabled(true); }
});
```

### 4.4 — Container + file selector pipeline

```javascript
// File selector gives base64 content when read through container
let fileSelector = form.create_selector_file();
fileSelector.setPlaceholder("/path/to/file.dll");

let container = form.create_container();
container.put("dll_content", fileSelector);

// Check if file was selected:
if (!container.get("dll_content")) {
    ax.show_message("Error", "File is required.");
    return;
}

// Extract base64 content:
let json = JSON.parse(container.toJson());
let base64Data = json.dll_content;
```

### 4.5 — Command definitions

```javascript
let cmd = ax.create_command("name", "description", "example", "task message");

// Argument types:
cmd.addArgString("name", true, "help");          // positional, required
cmd.addArgString("path", false, "help");          // positional, optional
cmd.addArgString("path", ".", "help");            // optional with default "."
cmd.addArgInt("count", true, "help");             // integer
cmd.addArgInt("count", "help", 10);               // optional with default value
cmd.addArgBool("-v", "verbose");                  // flag (true if present)
cmd.addArgBool("-v", "verbose", true);            // flag with default bool value
cmd.addArgFlagInt("-n", "num", false, "help");         // -n <int>
cmd.addArgFile("payload", true, "help");          // file → base64
cmd.addArgFlagString("-o", "output", false, "help");   // -o <string>
cmd.addArgFlagFile("-f", "file", true, "help");        // -f <file>
cmd.addSubCommands([sub1, sub2]);                      // subcommand tree

// PreHook — rewrite command before execution (e.g., alias)
cmd.setPreHook(function(id, cmdline, parsed_json, ...parsed_lines) {
    let real_cmd = "ps run -o C:\\Windows\\System32\\cmd.exe /c " + parsed_json["cmd_params"];
    ax.execute_alias(id, cmdline, real_cmd, "Running shell via ps");
});

// PostHook — process result after agent returns (hooktask struct)
cmd.setPostHook(function(hooktask) {
    // hooktask: { agent, type, message, text, completed, index }
    // Modify and return; requires originating client to stay connected
    return hooktask;
});

// Register per-OS command groups
let win = ax.create_commands_group("<agent>", [cmd1, cmd2, cmd_win_only]);
let unix = ax.create_commands_group("<agent>", [cmd1, cmd2, cmd_unix_only]);
ax.register_commands_group(win, ["<agent>"], ["windows"], []);
ax.register_commands_group(unix, ["<agent>"], ["linux", "macos"], []);
// Or return from RegisterCommands: { commands_windows: win, commands_linux: unix }
```

### 4.6 — Menus and events

See [references/axscript-api.md](references/axscript-api.md) for the complete API. Key patterns:

```javascript
// Context menus
menu.add_filebrowser(action, ["<agent>"]);
menu.add_session_agent(action, ["<agent>"]);
menu.add_processbrowser(action, ["<agent>"], ["windows"]);
menu.add_downloads_running(action, ["<agent>"]);
menu.add_tasks_job(action, ["<agent>"]);

// Events
event.on_filebrowser_list(handler, ["<agent>"]);
event.on_new_agent(handler, ["<agent>"]);
event.on_ready(handler);
event.on_interval(handler, seconds);
```

### 4.7 — Key ax.* functions

- `ax.execute_command(id, cmdline)` — issue command to agent
- `ax.execute_command_hook(id, cmdline, hook)` — execute with PostHook callback (`hooktask` → returns modified `hooktask`)
- `ax.execute_command_handler(id, cmdline, handler)` — execute with Handler callback (`handlertask` → void)
- `ax.execute_alias(id, displayCmdline, actualCmd, message)` — show one command, run another (4 params)
- `ax.execute_alias_hook(id, displayCmdline, actualCmd, message, hook)` — alias with PostHook
- `ax.execute_alias_handler(id, displayCmdline, actualCmd, message, handler)` — alias with Handler
- `ax.execute_browser(id, cmd)` — browser command
- `ax.service_command(svcName, function, data)` — send command to Go service plugin
- `ax.agents()` / `ax.ids()` / `ax.agent_info(id, prop)` — session data
- `ax.credentials()` / `ax.credentials_add(user, pass, realm, type, tag, storage, host)` — credential management
- `ax.targets()` / `ax.targets_add(computer, domain, address, os, osDesc, tag, info, alive)` — target management
- `ax.credentials_add_list(arr)` / `ax.targets_add_list(arr)` — bulk add
- `ax.bof_pack(types, args)` — BOF argument packing (`b`=bytes, `h`=short, `i`=int, `z`=cstr, `Z`=wstr, `B`=binary)
- `ax.console_message(id, msg, type, text)` — output to console
- `ax.open_browser_files(id)` / `ax.open_browser_process(id)` / `ax.open_remote_shell(id)` / `ax.open_remote_terminal(id)` — UI actions
- `ax.show_message(title, msg)` / `ax.prompt_save_file(name)` / `ax.prompt_confirm(title, msg)` — dialogs
- `ax.file_read(path)` / `ax.file_write_text(path, text)` / `ax.file_write_binary(path, b64)` — file I/O
- `ax.random_string(len, set)` / `ax.hash(algo, len, data)` — utilities
- `ax.encode_data(algo, data, key)` / `ax.decode_data(algo, b64, key)` — codec
- `ax.convert_to_code(lang, b64data, varName)` — shellcode formatter
- `ax.validate_command(id, cmd)` — returns `{valid, message, is_pre_hook, has_output, has_post_hook, parsed}`
- `ax.agent_set_impersonate(id, impersonate, elevated)` / `ax.copy_to_clipboard(text)` — session helpers
- `ax.log(msg)` / `ax.log_error(msg)` — logging
- `ax.get_project()` / `ax.ticks()` — project info + timing

### 4.8 — .axs UI Gotchas

| Gotcha | Detail |
|--------|--------|
| **`setPanel()` not `setLayout()`** | GroupBox and ScrollArea use `.setPanel(panel)`. Never call `.setLayout()` on them directly. |
| **`getEnabled()` not `isEnabled()`** | To read enabled state, use `widget.getEnabled()`. This is asymmetric with `widget.setEnabled(bool)`. |
| **`setItems()` vs `addItems()`** | `combo.setItems([])` clears then sets. `combo.addItems([])` appends. Use `setItems()` inside signal handlers to replace options. |
| **`fromJson()` exists but rare** | `container.fromJson(jsonStr)` is officially documented and recovers widget values from JSON. Manual restoration with `.setText()` etc. is more common in practice. |
| **File selector in container** | `container.put("key", fileSelector)` serializes file content as **base64**. Must `JSON.parse(container.toJson())` to extract it. |
| **Checkable groupbox as boolean** | `container.put("key", checkableGroupbox)` serializes as `true/false`. |
| **`addArg*` default overloads** | `addArgString(name, true, desc)` = required. `addArgString(name, false, desc)` = optional. `addArgString(name, ".", desc)` = optional with default. Same for `addArgInt(name, desc, value)` and `addArgBool(flag, desc, value)`. |
| **`ServiceUI()` boot call** | Must be the last line of a service `.axs` file. Without it, the service won't initialize. |
| **`data_handler` is async-only** | `ax.service_command()` is fire-and-forget. No return value. Go side sends results back via `TsServiceSendDataClient()` → `data_handler(data)`. |
| **`create_dialog` vs `create_ext_dialog`** | `create_dialog` is in official docs. `create_ext_dialog` is NOT in official docs — discovered in source code. May have different blocking semantics. |
| **`create_segcontrol`** | NOT in official docs — discovered in source code. Use with caution; may be internal/undocumented. |
| **Separator / spacer names** | Official API: `form.create_hline()` (horizontal line), `form.create_vline()` (vertical line), `form.create_vspacer()` (vertical spacer), `form.create_hspacer()` (horizontal spacer). |
| **Splitter creation** | Official docs use `form.create_vsplitter()` / `form.create_hsplitter()`, not `form.create_splitter(orientation)`. |
| **PostHook requires connection** | PostHook callbacks need the originating client to stay connected. Disconnection loses responses. |

---

## 5 — Teamserver Interface & Data Types

The `Teamserver` interface (type-asserted from `ts any` in `InitPlugin`) provides all server-side operations. See [references/teamserver-api.md](references/teamserver-api.md) for complete method signatures and data types.

### Most-used methods (quick reference)

```go
// Agent lifecycle
Ts.TsAgentCreate(agentCrc, agentId string, beat []byte, listenerName, externalIP string, async bool) (adaptix.AgentData, error)
Ts.TsAgentProcessData(agentId string, bodyData []byte) error
Ts.TsAgentUpdateData(newAgentData adaptix.AgentData) error
Ts.TsAgentSetTick(agentId, listenerName string) error
Ts.TsAgentGetHostedAll(agentId string, maxDataSize int) ([]byte, error)
Ts.TsAgentConsoleOutput(agentId string, result adaptix.ConsoleMessageData) error

// Tasks
Ts.TsTaskCreate(agentId, cmdline, client string, data adaptix.TaskData)
Ts.TsTaskUpdate(agentId string, data adaptix.TaskData)

// Downloads
Ts.TsDownloadAdd(agentId, fileId, fileName string, totalSize int) error
Ts.TsDownloadUpdate(agentId, fileId string, data []byte) error
Ts.TsDownloadClose(agentId, fileId string) error

// Build
Ts.TsAgentBuildExecute(builderId, workingDir, program string, args ...string) error
Ts.TsAgentBuildLog(builderId string, status int, message string) error

// Services (send data back to AxScript data_handler)
Ts.TsServiceSendDataClient(serviceName, client, function, args string) error
Ts.TsServiceSendDataAll(serviceName, function, args string) error

// Events
Ts.TsEventHookRegister(event string, phase int, priority int, handler func(...)) (string, error)
```

### Key type gotchas

- `AgentData.Sleep` is `uint` (seconds) — convert from string with `time.ParseDuration()` then cast
- `AgentData.Pid` is `string` — convert from int with `fmt.Sprintf("%d", pid)`
- `AgentData.Os` uses `adaptix.OS_WINDOWS=1`, `OS_LINUX=2`, `OS_MAC=3` — never `OS_MACOS`
- `TaskData.Data` is `[]byte` — serialized wire-format command payload
- `BuildProfile.AgentConfig` is JSON string from `container.toJson()` in the GenerateUI form

---

## 6 — Template Generators

The scaffold system at `AdaptixC2-Template-Generators/` generates plugin + implant boilerplate.

### Generation commands (PowerShell)

```powershell
# Agent (all flags required for non-interactive)
.\agent\generator.ps1 -Name <name> -Watermark a1b2c3d4 -Protocol <proto> -Language <lang> -Toolchain <tc>
# With evasion gate
.\agent\generator.ps1 -Name <name> -Watermark a1b2c3d4 -Protocol <proto> -Language <lang> -Toolchain <tc> -Evasion

# Listener
.\listener\generator.ps1 -Name <name> -Protocol <proto> -ListenerType external

# Service
.\service\generator.ps1 -Name <name>
# Service with wrapper pipeline
.\service\generator.ps1 -Name <name> -Wrapper

# Protocol scaffold
.\generator.ps1 -Mode protocol

# Crypto swap
.\generator.ps1 -Mode crypto
```

### Placeholder system

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

### Protocol overlay mechanism

Protocols live in `protocols/<name>/` and can override plugin templates:

1. `types.go.tmpl` + `constants.go.tmpl` → merged into `pl_utils.go` (repackaged as `main`)
2. `crypto.go.tmpl` → injected into `src_<name>/crypto/crypto.go` (repackaged as `crypto`)
3. `pl_main.go.tmpl` → **replaces** base `pl_main.go` entirely
4. `pl_transport.go.tmpl` → replaces listener transport
5. `pl_internal.go.tmpl` → replaces internal listener handler
6. `pl_build_<lang>.go.tmpl` → replaces build handler for that language
7. `implant/` overlays → merged into implant source tree

### Toolchains

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

### Evasion gate

Generated with `-Evasion` flag. Scaffolds `evasion/` directory with a `Gate` interface (5 methods). Markers in templates:

- Go: `// __EVASION_IMPORT__`, `// __EVASION_FIELD__`, `// __EVASION_INIT__`
- C++: `// __EVASION_INCLUDE__`, `// __EVASION_MEMBER__`, `// __EVASION_CTOR__`
- Rust: `// __EVASION_MOD__`, `# __EVASION_FEATURES__` (must stay inside `[features]` in Cargo.toml)

Without `-Evasion`: all markers are stripped, no `evasion/` directory.

---

## 7 — Validation Workflow

### Go validation (WSL preferred on Windows)

```powershell
wsl bash -lc 'cd /mnt/d/Sources/AdaptixC2-Template-Generators/output/<dir> && /usr/local/go/bin/go mod tidy && /usr/local/go/bin/go vet ./...'
```

### Rust validation (WSL)

```powershell
wsl bash -lc 'cd /mnt/d/Sources/AdaptixC2-Template-Generators/output/<dir>/src_<name> && cargo check'
```

### Placeholder leak check

```powershell
Select-String -Path output\<dir>\*.go -Pattern '__[A-Z_]+__'
# Zero matches expected
```

### Parity checks

- Every `create_command()` in `ax_config.axs` → matching `CreateCommand` case in `pl_main.go`
- Every `CreateCommand` case → matching `ProcessData` handler for the response
- BOF types (`ParamsExecBof`, `Job`, `BOF_PACK`, `CALLBACK_AX_*`) must survive protocol overlay into `pl_utils.go`
- Protocol `pl_main.go.tmpl` overrides must replace entirely and still pass `go vet`

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

## 9 — Common Patterns

### Adding a new command (end-to-end)

1. **ax_config.axs**: `let cmd = ax.create_command("mycmd", "desc", "mycmd arg1")` + add to group
2. **pl_utils.go**: Add `COMMAND_MYCMD` constant + request/response structs
3. **pl_main.go CreateCommand**: Add `case "mycmd":` — marshal args into wire struct
4. **pl_main.go ProcessData**: Add `case COMMAND_MYCMD:` — unmarshal response, call Ts methods
5. **Implant**: Add handler in implant `tasks.go` / `tasks.cpp` / `tasks.rs`
6. Validate: `go vet`, check placeholder leaks

### Adding a new protocol

1. Run `.\generator.ps1 -Mode protocol` → creates `protocols/<name>/`
2. Implement `crypto.go.tmpl` (encrypt/decrypt), `constants.go.tmpl`, `types.go.tmpl`
3. Update `meta.yaml`
4. Add `pl_main.go.tmpl` / `pl_transport.go.tmpl` overrides if needed
5. Add implant overlays in `implant/` if needed (Go root, C++ in `cpp/`, Rust in `rust/`)
6. Generate agent + listener with `-Protocol <name>`, validate with `go vet`

### Wrapper service (post-build pipeline)

1. Generate: `.\service\generator.ps1 -Name <name> -Wrapper`
2. Implement stages in `pl_wrapper.go`
3. Hook `agent.generate` event to intercept payload after build
4. Ts.TsServiceSendDataClient() for per-client updates

### Multi-language build support

`pl_build.go` switches on `Language` field:
- Go: `go build` with cross-compilation env vars
- C++: `make` with MinGW/Clang toolchain
- Rust: `cargo build` with target flags, optional LLVM obfuscation via linker-plugin-lto

Rust LLVM obfuscation requires: `-C link-arg=-fuse-ld=lld` and `-C link-arg=-Wl,-mllvm,<flag>` routing.

---

## 10 — Learned Pitfalls

These are verified issues from real development:

- **C++ clang compat**: Casting member-fn-ptr to `void*` is a GCC extension. Use `__builtin_return_address(0)`. Use `__builtin_offsetof` instead of `offsetof()` in namespaces.
- **C++ Makefiles with .c files**: Clang rejects `-std=c++17` for C files. Extract C_SOURCES, compile separately with `-std=c11`.
- **Rust linker-plugin-lto**: Requires `lld` (not `ld.bfd`). Route `-mllvm` flags as `-Wl,-mllvm,<arg>`.
- **Rust evasion Cargo.toml**: `# __EVASION_FEATURES__` must be inside the existing `[features]` section to avoid duplicate sections.
- **PE hardening**: Never inflate VirtualSize when diluting entropy — only extend RawSize. VA overlap crashes the PE.
- **Section names**: Don't use `.rsrc` as import padding section name — conflicts with resource injection.
- **COFF string encryption**: GCC statement expressions with static guards don't work in Crystal Palace PIC blobs. Skip obfuscation for COFF; rely on outer payload encryption.
- **Service name routing**: `ax.service_command(...)` name must match `config.yaml → service_name` exactly.

---

## Resources

- [references/teamserver-api.md](references/teamserver-api.md) — Full Teamserver method signatures and data types
- [references/axscript-api.md](references/axscript-api.md) — Complete AxScript function reference with signatures and data models
- Online docs: https://adaptix-framework.gitbook.io/adaptix-framework/development/
- Extension-Kit: https://github.com/Adaptix-Framework/Extension-Kit
- axc2 module: `github.com/Adaptix-Framework/axc2` v1.2.0
