# AxScript Patterns

Detailed code patterns for AxScript (.axs) UI, commands, events, and data flow.

---

## Three .axs Lifecycles

### Agent .axs lifecycle

Agent `.axs` files must define two functions and register menus/events at top level:

```javascript
// REQUIRED: Define CLI commands. Called by framework with the listener type string.
function RegisterCommands(listenerType) {
    let cmd_shell = ax.create_command("shell", "Run shell cmd", "shell whoami", "Task: shell");
    cmd_shell.addArgString("cmd_params", true, "Command");

    let cmd_sleep = ax.create_command("sleep", "Set sleep", "sleep 5s 20");
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
function GenerateUI(listeners_type) {
    let container = form.create_container();
    let layout = form.create_gridlayout();
    // ... build form ...
    let panel = form.create_panel();
    panel.setLayout(layout);

    // MUST return this structure:
    return {
        ui_panel:     panel,
        ui_container: container,
        ui_height:    400,
        ui_width:     600
    };
}

// TOP-LEVEL: Register menus and events (imperative, outside functions)
let action_fb = menu.create_action("Download", function(files) { ... });
menu.add_filebrowser(action_fb, ["<agent_name>"]);
event.on_filebrowser_list(function(id, path) { ax.execute_browser(id, "ls " + path); }, ["<agent_name>"]);
event.on_filebrowser_disks(function(id) { ax.execute_browser(id, "disks"); }, ["<agent_name>"]);
event.on_processbrowser_list(function(id) { ax.execute_browser(id, "ps list"); }, ["<agent_name>"]);
```

### Listener .axs lifecycle

Listener `.axs` files must define one function:

```javascript
// REQUIRED: Build the listener configuration form.
function ListenerUI(mode_create) {
    let container = form.create_container();
    let layout = form.create_gridlayout();

    let txtHost = form.create_textline("0.0.0.0");
    let spinPort = form.create_spin();
    spinPort.setRange(1, 65535);
    spinPort.setValue(443);

    layout.addWidget(form.create_label("Bind Host:"), 0, 0, 1, 1);
    layout.addWidget(txtHost, 0, 1, 1, 1);

    container.put("host", txtHost);
    container.put("port", spinPort);

    let panel = form.create_panel();
    panel.setLayout(layout);

    return {
        ui_panel:     panel,
        ui_container: container,
        ui_height:    300,
        ui_width:     500
    };
}
```

### Service .axs lifecycle

Service `.axs` files must define three functions and end with the boot call:

```javascript
var serviceName = "<ServiceNameV2>";   // must match config.yaml → service_name
var g_output_widget = null;

// REQUIRED: Called once when plugin loads.
function InitService() {
    ax.log("Service loaded.");
    ax.service_command(serviceName, "load_settings", null);
    let action = menu.create_action("Open Tool", function() { buildMainWindow(); });
    menu.add_main_axscript(action);
}

// REQUIRED: Called after InitService. Usually minimal.
function ServiceUI() {
    ax.log("Service UI ready.");
}

// REQUIRED: Receives async responses from Go plugin.
function data_handler(data) {
    let response = JSON.parse(data);
    switch (response.action) {
        case "load_settings_result":
            break;
        case "compile_log":
            if (g_output_widget !== null) g_output_widget.appendText(response.output);
            break;
        case "compile_done":
            if (response.success && response.file_content) {
                let path = ax.prompt_save_file(response.file_name || "output.exe");
                if (path && path !== "") ax.file_write_binary(path, response.file_content);
            }
            break;
    }
}

// REQUIRED: Boot statement — must be last line in the file.
ServiceUI();
```

**Key data flow**: `ax.service_command()` is fire-and-forget. Go plugin's `Call()` processes the request, pushes results back via `TsServiceSendDataClient()` → arrives at `data_handler(data)` as JSON. All communication is asynchronous.

---

## UI Layout Patterns

### GroupBox + Panel (standard section pattern)

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

### Checkable GroupBox (toggle section)

```javascript
let grp = form.create_groupbox("Use Proxy", true);   // true = checkable
grp.setPanel(panel);
grp.setChecked(false);
form.connect(grp, "clicked", function(checked) { panel.setEnabled(checked); });
container.put("use_proxy", grp);  // serializes as boolean
```

### ScrollArea (tall forms)

```javascript
let mainLayout = form.create_vlayout();
mainLayout.addWidget(grp1);
mainLayout.addWidget(grp2);

let innerPanel = form.create_panel();
innerPanel.setLayout(mainLayout);

let scroll = form.create_scrollarea();
scroll.setPanel(innerPanel);      // NOTE: setPanel(), not setWidget()

let outerLayout = form.create_vlayout();
outerLayout.addWidget(scroll);
let outerPanel = form.create_panel();
outerPanel.setLayout(outerLayout);
```

### Stack + Segmented Control (tab interface)

> `create_segcontrol` is NOT in official docs — discovered in source code.

```javascript
let controller = form.create_segcontrol();
controller.addItems(["Main", "Headers", "Advanced"]);

let stack = form.create_stack();
stack.addPage(panel1);
stack.addPage(panel2);
stack.setCurrentIndex(0);

form.connect(controller, "currentIndexChanged", function() {
    stack.setCurrentIndex(controller.currentIndex());
});
```

### Dialog types

```javascript
// Standard modal dialog
let dialog = form.create_dialog("Title");
dialog.setSize(600, 400);
dialog.setLayout(layout);
dialog.setButtonsText("Save", "Cancel");
let accepted = dialog.exec();

// Extended dialog (for service/tool windows)
let ext = form.create_ext_dialog("Title");
ext.setSize(600, 400);
ext.setButtonsText("Close", "");   // "" hides cancel button
ext.exec();
```

---

## Signal Connection Patterns

```javascript
// Button click
form.connect(btn, "clicked", function() { /* ... */ });

// Checkbox toggle → show/hide dependent fields
form.connect(chk, "stateChanged", function() {
    let checked = chk.isChecked();
    lbl.setVisible(checked);
    txt.setVisible(checked);
});

// Combo selection change
form.connect(combo, "currentTextChanged", function(text) {
    chk.setEnabled(text.toLowerCase() !== "bin");
});

// Checkable groupbox toggle
form.connect(grp, "clicked", function(checked) { panel.setEnabled(checked); });

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

---

## Container + File Selector Pipeline

```javascript
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

---

## Command Definitions

```javascript
let cmd = ax.create_command("name", "description", "example", "task message");

// Argument types:
cmd.addArgString("name", true, "help");          // positional, required
cmd.addArgString("path", false, "help");          // positional, optional
cmd.addArgString("path", ".", "help");            // optional with default "."
cmd.addArgInt("count", true, "help");             // integer
cmd.addArgInt("count", "help", 10);               // optional with default
cmd.addArgBool("-v", "verbose");                  // flag
cmd.addArgBool("-v", "verbose", true);            // flag with default
cmd.addArgFlagInt("-n", "num", false, "help");
cmd.addArgFile("payload", true, "help");          // file → base64
cmd.addArgFlagString("-o", "output", false, "help");
cmd.addArgFlagFile("-f", "file", true, "help");
cmd.addSubCommands([sub1, sub2]);

// PreHook — rewrite command before execution
cmd.setPreHook(function(id, cmdline, parsed_json, ...parsed_lines) {
    let real_cmd = "ps run -o C:\\Windows\\System32\\cmd.exe /c " + parsed_json["cmd_params"];
    ax.execute_alias(id, cmdline, real_cmd, "Running shell via ps");
});

// PostHook — process result after agent returns
cmd.setPostHook(function(hooktask) {
    // hooktask: { agent, type, message, text, completed, index }
    return hooktask;
});

// Register per-OS command groups
let win = ax.create_commands_group("<agent>", [cmd1, cmd2]);
let unix = ax.create_commands_group("<agent>", [cmd1, cmd2]);
```

---

## Menus and Events

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

---

## Key ax.* Functions

- `ax.execute_command(id, cmdline)` — issue command to agent
- `ax.execute_command_hook(id, cmdline, hook)` — execute with PostHook
- `ax.execute_command_handler(id, cmdline, handler)` — execute with Handler
- `ax.execute_alias(id, displayCmdline, actualCmd, message)` — show one command, run another
- `ax.execute_alias_hook(id, displayCmdline, actualCmd, message, hook)` — alias with PostHook
- `ax.execute_alias_handler(id, displayCmdline, actualCmd, message, handler)` — alias with Handler
- `ax.execute_browser(id, cmd)` — browser command
- `ax.service_command(svcName, function, data)` — send command to Go service plugin
- `ax.agents()` / `ax.ids()` / `ax.agent_info(id, prop)` — session data
- `ax.credentials()` / `ax.credentials_add(...)` / `ax.credentials_add_list(arr)` — credential management
- `ax.targets()` / `ax.targets_add(...)` / `ax.targets_add_list(arr)` — target management
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

---

## .axs UI Gotchas

| Gotcha | Detail |
|--------|--------|
| **`setPanel()` not `setLayout()`** | GroupBox and ScrollArea use `.setPanel(panel)`. Never call `.setLayout()` on them directly. |
| **`getEnabled()` not `isEnabled()`** | To read enabled state, use `widget.getEnabled()`. Asymmetric with `widget.setEnabled(bool)`. |
| **`setItems()` vs `addItems()`** | `combo.setItems([])` clears then sets. `combo.addItems([])` appends. Use `setItems()` inside signal handlers. |
| **`fromJson()` exists but rare** | `container.fromJson(jsonStr)` recovers widget values from JSON. Manual restoration with `.setText()` etc. is more common. |
| **File selector in container** | `container.put("key", fileSelector)` serializes file content as **base64**. Must `JSON.parse(container.toJson())` to extract. |
| **Checkable groupbox as boolean** | `container.put("key", checkableGroupbox)` serializes as `true/false`. |
| **`addArg*` default overloads** | `addArgString(name, true, desc)` = required. `addArgString(name, false, desc)` = optional. `addArgString(name, ".", desc)` = optional with default. |
| **`ServiceUI()` boot call** | Must be the last line of a service `.axs` file. Without it, the service won't initialize. |
| **`data_handler` is async-only** | `ax.service_command()` is fire-and-forget. No return value. Results come back via `TsServiceSendDataClient()` → `data_handler(data)`. |
| **`create_dialog` vs `create_ext_dialog`** | `create_dialog` is in official docs. `create_ext_dialog` is NOT — discovered in source code. |
| **`create_segcontrol`** | NOT in official docs — discovered in source code. Use with caution. |
| **Separator / spacer names** | `form.create_hline()`, `form.create_vline()`, `form.create_vspacer()`, `form.create_hspacer()`. |
| **Splitter creation** | Official: `form.create_vsplitter()` / `form.create_hsplitter()`, not `form.create_splitter(orientation)`. |
| **PostHook requires connection** | PostHook callbacks need the originating client to stay connected. Disconnection loses responses. |
