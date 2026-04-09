# AxScript API Reference

Complete reference for the AxScript JavaScript bridge API (Goja engine).
AxScript files (`.axs`) define UI, commands, menus, and events for AdaptixClient.

---

## Namespaces

| Namespace | Purpose |
|-----------|---------|
| `ax.*` | Bridge functions — commands, data queries, file I/O, utilities |
| `form.*` | UI widget creation — layouts, inputs, dialogs, selectors |
| `menu.*` | Context menu registration |
| `event.*` | Event handler registration |

---

## ax.* — Bridge Functions

### Command Creation

```javascript
// Create a command definition
let cmd = ax.create_command(name, description, example, message)
// name: string — command name (used in CreateCommand switch)
// description: string — shown in help
// example: string — usage example
// message: string — message shown when task is created (optional, default "Task: <name>")

// Argument methods (on command object)
cmd.addArgBool(flag, description)                             // --flag style
cmd.addArgBool(flag, description, value)                      // with default bool value
cmd.addArgInt(name, required, description)                    // integer positional
cmd.addArgInt(name, description, value)                       // optional with default int value
cmd.addArgFlagInt(flag, name, required, description)          // -f <int>
cmd.addArgString(name, required, description)                 // string positional
cmd.addArgString(name, description, value)                    // optional with default string value
cmd.addArgFlagString(flag, name, required, description)       // -f <string>
cmd.addArgFile(name, required, description)                   // file → base64
cmd.addArgFlagFile(flag, name, required, description)         // -f <file>
cmd.addSubCommands(commands_array)                            // subcommand tree

// Hooks (pre-processing / post-processing)
cmd.setPreHook(function(id, cmdline, parsed_json, ...parsed_lines) { /* return modified string or void */ })
cmd.setPostHook(function(hooktask) {
    // hooktask: { agent, type, message, text, completed, index }
    // Modify and return the hooktask
    return hooktask;
})

// Command groups
let group = ax.create_commands_group(name, [cmd1, cmd2, ...])
ax.register_commands_group(group, agents[], os[], listeners[])
// agents: ["beacon", "gopher", etc.] — which agents get these commands
// os: ["windows", "linux", "macos"] or [] for all
// listeners: ["BeaconHTTP", "BeaconSMB"] or [] for all
```

### Command Execution

```javascript
// Execute a command on an agent
ax.execute_command(agentId, commandLine)

// Execute with hook — PostHook callback receives hooktask, returns modified hooktask
ax.execute_command_hook(agentId, commandLine, function(hooktask) {
    // hooktask: { agent, type, message, text, completed, index }
    return hooktask;
})

// Execute with handler — Handler callback receives handlertask, void return
ax.execute_command_handler(agentId, commandLine, function(handlertask) {
    // handlertask: { id, agent, cmdline, type, message, text }
})

// Execute with display alias — show displayCmdline in UI, actually run actualCmd
ax.execute_alias(agentId, displayCmdline, actualCmd, message)

// Execute alias with hook
ax.execute_alias_hook(agentId, displayCmdline, actualCmd, message, function(hooktask) {
    return hooktask;
})

// Execute alias with handler
ax.execute_alias_handler(agentId, displayCmdline, actualCmd, message, function(handlertask) {
    // handlertask: { id, agent, cmdline, type, message, text }
})

// Execute browser command (file browser / process browser)
ax.execute_browser(agentId, commandLine)

// Validate command without executing — returns cmd_info struct
let info = ax.validate_command(agentId, commandLine)
// cmd_info: { valid, message, is_pre_hook, has_output, has_post_hook, parsed }

// Get list of registered commands for an agent
ax.get_commands(agentId)  // returns string[]
```

> **PostHook note**: PostHook callbacks require the originating client to remain connected.
> If the client disconnects before the agent returns, PostHook responses are lost.

### Agent Data

```javascript
// Returns map of all agents: { agentId: AGENT_STRUCT, ... }
ax.agents()

// AGENT structure fields (AxScript JS side — from official docs):
// id, type, listener, external_ip, internal_ip, domain, computer, username,
// impersonated, process, arch, pid, tid, gmt, acp, oemcp, elevated, tags,
// async, sleep, os_full

// Get specific agent property
ax.agent_info(agentId, property)  // returns string/int depending on property

// Get list of all agent IDs
ax.ids()

// Session state checks
ax.arch(agentId)        // architecture string
ax.is64(agentId)        // true if x64
ax.isactive(agentId)    // true if recently checked in
ax.isadmin(agentId)     // true if elevated
```

### Agent Management

```javascript
ax.agent_hide(ids)                                         // Hide sessions from UI (string[])
ax.agent_remove(ids)                                       // Remove sessions permanently (string[])
ax.agent_set_color(ids, bg, fg, reset)                     // Set display colors
ax.agent_set_impersonate(agentId, impersonate, elevated)   // Set impersonation state
ax.agent_set_mark(agentId, mark)                           // Set mark text
ax.agent_set_tag(agentId, tag)                             // Set comma-separated tags
ax.agent_update_data(agentId, jsonData)                    // Partial update of agent data
```

### Credentials

```javascript
// Add credential (storage and host are additional params vs minimal form)
ax.credentials_add(username, password, realm, type, tag, storage, host)

// Add list of credentials
ax.credentials_add_list(credentialsArray)

// List all credentials — returns map: { credId: CRED_STRUCT }
ax.credentials()

// CRED structure:
// id, username, password, realm, type, tag, date, storage, agent_id, host
```

### Targets

```javascript
// Add target
ax.targets_add(computer, domain, address, os, osDesc, tag, info, alive)

// Add list of targets
ax.targets_add_list(targetsArray)

// List all targets — returns map: { targetId: TARGET_STRUCT }
ax.targets()

// TARGET structure (from official docs):
// id, computer, domain, address, tag, date, info, alive, owned, os, os_desc
```

### Downloads / Screenshots / Tunnels

```javascript
// Returns map of download entries
ax.downloads()
// DOWNLOAD structure (full, from official docs):
// id, agent_id, agent_name, user, computer, filename, recv_size, total_size, date, state

// Returns screenshot entries
ax.screenshots()
// SCREEN structure:
// id, user, computer, note, date

// Returns tunnel entries
ax.tunnels()
// TUNNEL structure (full, from official docs):
// id, agent_id, username, computer, process, type, info, interface, port, client, f_port, f_host
```

### UI Actions

```javascript
// Open agent console
ax.open_agent_console(agentId)

// Open browsers
ax.open_browser_files(agentId)          // File browser
ax.open_browser_process(agentId)        // Process browser

// Open interactive sessions
ax.open_remote_shell(agentId)           // Shell
ax.open_remote_terminal(agentId)        // Terminal

// Open Access panel (tunnels)
ax.open_access_tunnel(agentId, socks4Port, socks5Port, localPortForward, remotePortForward)

// Copy to clipboard
ax.copy_to_clipboard(text)
```

### Data Encoding

```javascript
// Encode/decode data (base64 I/O)
ax.encode_data(algorithm, b64data, key)   // returns base64
ax.decode_data(algorithm, b64data, key)   // returns base64

// Supported algorithms: "xor", "rc4", "aes256_cbc", "base64"
// key is base64-encoded

// Encode/decode files
ax.encode_file(algorithm, filepath, key)  // returns base64
ax.decode_file(algorithm, filepath, key)  // returns base64
```

### File I/O

```javascript
ax.file_read(filepath)                    // returns base64 content
ax.file_write_text(filepath, text)        // write text file
ax.file_write_binary(filepath, b64data)   // write binary (base64 input)
ax.file_exists(filepath)                  // boolean
ax.file_basename(filepath)               // filename only
ax.file_dirname(filepath)                // directory only
ax.file_extension(filepath)              // extension
ax.file_size(filepath)                   // file size in bytes
```

### Utilities

```javascript
// Random generation
ax.random_string(length, charset)         // charset: "alpha", "num", "alphanum", "hex"
ax.random_int(min, max)

// Hashing
ax.hash(algorithm, length, data)          // algorithm: "md5", "sha1", "sha256", "sha512"

// BOF argument packing
ax.bof_pack(formatString, ...args)
// Format chars: b=byte (bytes), h=short (16-bit), i=int (32-bit),
//               z=cstr (null-terminated ANSI), Z=wstr (null-terminated wide), B=binary (len-prefixed)

// Platform info
ax.arch()           // "x86" or "x64" (client arch — no arg version)
ax.interfaces()     // network interfaces

// Time/size formatting
ax.format_time(format, unixTimestamp)     // format: Go-style time format string
ax.format_size(bytes)                     // human-readable size

// Ticks
ax.ticks()          // current tick count

// Project info
ax.get_project()    // returns project name/info

// Code generation
ax.convert_to_code(language, b64data, variableName)
// language: "c", "csharp", "python", "powershell", "vbscript"

// Console output
ax.console_message(agentId, messageType, text)
// messageType: "info", "error", "success"

// Dialogs
ax.show_message(title, message)
ax.prompt_confirm(title, message)              // returns bool
ax.prompt_open_file(caption, filter)           // returns filepath
ax.prompt_open_dir(caption)                    // returns dirpath
ax.prompt_save_file(title, filter, filename)   // returns filepath

// Logging
ax.log(message)
ax.log_error(message)

// Script management
ax.script_import(filepath)
ax.script_load(filepath)
ax.script_unload(filepath)
ax.script_dir()                                // script directory path
```

### Service Communication

```javascript
// Send command to Go service plugin (fire-and-forget)
ax.service_command(serviceName, function, data)
// Go plugin receives in Call(operator, function, args)
// Go plugin sends results back via TsServiceSendDataClient()
// → arrives at data_handler(data) as JSON string
```

---

## form.* — UI Widgets

### Layouts

```javascript
form.create_vlayout()       // Vertical layout
form.create_hlayout()       // Horizontal layout
form.create_gridlayout()    // Grid layout

// Layout methods
layout.addWidget(widget)                         // vlayout/hlayout
layout.addWidget(widget, row, col, rowSpan, colSpan)  // gridlayout
layout.addLayout(sublayout)
```

### Input Widgets

```javascript
// Text input
form.create_textline(defaultValue)
textline.setPlaceholder(text)
textline.setText(text)
textline.text()                    // returns string
textline.setReadOnly(bool)
textline.setVisible(bool)
// Signals: "textChanged", "returnPressed"

// Multiline text
form.create_textmulti()
textmulti.setText(text)
textmulti.text()
textmulti.append(text)

// Dropdown
form.create_combo()
combo.setItems(["item1", "item2"])
combo.setCurrentIndex(i)
combo.currentIndex()
combo.currentText()
// Signals: "currentTextChanged", "currentIndexChanged"

// Spinbox
form.create_spin()
spin.setRange(min, max)
spin.setValue(n)
spin.value()
// Signals: "valueChanged"

// Checkbox
form.create_check(label)
check.setChecked(bool)
check.isChecked()
// Signals: "stateChanged"

// Date input
form.create_dateline(format)      // format: date format string (e.g. "yyyy-MM-dd")
dateline.setDate(year, month, day)
dateline.date()

// Time input
form.create_timeline(format)      // format: time format string (e.g. "HH:mm")
timeline.setTime(hour, minute)
timeline.time()
```

### Display Widgets

```javascript
// Label
form.create_label(text)
label.setText(text)

// Button
form.create_button(text)
// Signals: "clicked"

// Horizontal separator line
form.create_hline()

// Vertical separator line
form.create_vline()

// Vertical spacer (pushes widgets apart vertically)
form.create_vspacer()

// Horizontal spacer (pushes widgets apart horizontally)
form.create_hspacer()
```

### Container Widgets

```javascript
// Panel (layout wrapper — the universal building block)
form.create_panel()
panel.setLayout(layout)            // set the layout for the panel
panel.setEnabled(bool)             // enable/disable all children
// NOTE: read enabled state with panel.getEnabled(), NOT isEnabled()

// Group box — ALWAYS use setPanel(), never setLayout() directly
form.create_groupbox(title, checkable)  // checkable: false=static, true=toggle
groupbox.setPanel(panel)           // set content panel
groupbox.setChecked(bool)          // only for checkable groupboxes
groupbox.isChecked()               // read checked state
// Signals: "clicked" (receives bool checked arg for checkable groupbox)
// In container: checkable groupbox serializes as boolean true/false

// Scroll area — ALWAYS use setPanel(), never setWidget()
form.create_scrollarea()
scrollarea.setPanel(panel)         // set scrollable content

// Splitter (two variants — from official docs)
form.create_vsplitter()            // vertical splitter
form.create_hsplitter()            // horizontal splitter
splitter.addPage(widget)           // add pane to splitter
splitter.setSizes(sizesArray)      // set pane sizes
// Signals: "splitterMoved"

// Tabs
form.create_tabs()
tabs.addTab(widget, title)         // add tab with title
tabs.setCurrentIndex(i)

// Stack (only one child visible at a time)
form.create_stack()
stack.addPage(panel)               // NOTE: addPage(), not addWidget()
stack.setCurrentIndex(i)

// Segmented control — NOT in official docs; discovered in source code
// Use with caution — may be undocumented/internal API
form.create_segcontrol()
segctrl.addItems(["Tab1", "Tab2"])
segctrl.currentIndex()             // read selected tab
// Signals: "currentIndexChanged"
```

### Data Containers

```javascript
// Container — key/value store bound to widgets
form.create_container()
container.put(key, widget)     // Bind widget to key
container.get(key)             // Get widget by key
container.toJson()             // Serialize all values to JSON string
container.fromJson(jsonStr)    // Recover widget values from JSON (officially documented)

// Table widget (constructor takes headers array)
form.create_table(headersArray)
table.addItem(rowArray)            // add a row ["val1", "val2"]
table.selectedRows()               // returns selected row indices
table.setSortingEnabled(bool)
table.resizeToContent()
table.setHeadersVisible(bool)
table.setColumnAlign(column, alignment)
// Signals: "cellChanged", "cellClicked", "cellDoubleClicked"

// List widget
form.create_list()
list.addItem(text)
list.addItems(["a", "b"])
list.selectedItems()
// Signals: "itemClickedText", "itemDoubleClickedText", "currentTextChanged", "currentRowChanged"
// In container: serializes as array
```

### Selectors

```javascript
// File selector (path input + browse button)
form.create_selector_file()
selector.setPlaceholder(text)
// In container: value = base64-encoded file content

// Agent selector dialog
form.create_selector_agents(headersArray)
// Possible columns: "id", "type", "listener", "external_ip", "internal_ip",
//                   "domain", "computer", "username", "process", "pid", "tid", "os", "tags"
selector.setSize(w, h)
selector.close()
let agents = selector.exec()   // modal — returns AGENT[] or []
// AGENT: id, type, listener, external_ip, internal_ip, domain, computer,
//        username, impersonated, process, pid, tid, tags, os

// Credential selector dialog
form.create_selector_credentials(headersArray)
// Possible columns: "username", "password", "realm", "type", "tag", "date", "storage", "agent_id", "host"
selector.setSize(w, h)
selector.close()
let creds = selector.exec()    // modal — returns CRED[] or []
// CRED: id, username, password, realm, type, tag, date, storage, agent_id, host
```

### Dialogs

```javascript
// Standard modal dialog
form.create_dialog(title)
dialog.setSize(w, h)
dialog.setLayout(layout)
dialog.setButtonsText(okText, cancelText)  // customize button labels
// Pass "" for cancelText to hide the cancel button
let accepted = dialog.exec()          // shows modal, returns true if OK/Save clicked
dialog.close()

// Extended dialog — NOT in official docs; discovered in source code
// May have slightly different blocking semantics
form.create_ext_dialog(title)
// Same API as create_dialog: setSize, setLayout, setButtonsText, exec, close
```

### Signals

```javascript
// Connect widget signal to handler
form.connect(widget, signal, handler)

// Common signals:
// button: "clicked"                                → handler()
// textline: "textChanged", "returnPressed"          → handler() / handler(text)
// combo: "currentTextChanged"                       → handler(text)
// combo: "currentIndexChanged"                      → handler()
// check: "stateChanged"                             → handler()
// spin: "valueChanged"                              → handler()
// checkable groupbox: "clicked"                     → handler(checked_bool)
// segcontrol: "currentIndexChanged"                 → handler()    [source-only]
// table: "cellChanged", "cellClicked", "cellDoubleClicked" → handler()
// list: "itemClickedText", "itemDoubleClickedText"  → handler()
// list: "currentTextChanged", "currentRowChanged"   → handler()
// splitter: "splitterMoved"                         → handler()
```

### Enable/Visible State (GOTCHA)

```javascript
// Setting:
widget.setEnabled(bool)
widget.setVisible(bool)

// Reading — NOTE the asymmetry:
widget.getEnabled()      // NOT isEnabled()
// isChecked() works for checkboxes
// isChecked() works for checkable groupboxes
```

---

## menu.* — Context Menus

### Creating menu items

```javascript
menu.create_action(text, handler)     // Clickable action
menu.create_menu(text)                // Submenu container
menu.create_separator()               // Visual separator

// Submenu nesting
let sub = menu.create_menu("Parent");
sub.addAction(action);
sub.addMenu(childMenu);
sub.addSeparator();
```

### Registration targets

All session/browser/download/task add-functions accept: `(item, agents[], os[], listeners[])`
except where noted.

| Function | Context | Handler signature |
|----------|---------|-------------------|
| `menu.add_main` | Main menu bar | `handler()` |
| `menu.add_main_projects` | Main → Projects | `handler()` |
| `menu.add_main_axscript` | Main → AxScript | `handler()` |
| `menu.add_main_settings` | Main → Settings | `handler()` |
| `menu.add_session_main` | Session context (after Access) | `handler(ids[])` |
| `menu.add_session_agent` | Session → Agent submenu | `handler(ids[])` |
| `menu.add_session_browser` | Session → Browsers submenu | `handler(ids[])` |
| `menu.add_session_access` | Session → Access submenu | `handler(ids[])` |
| `menu.add_filebrowser` | File Browser context | `handler(FILE_INFO[])` |
| `menu.add_processbrowser` | Process Browser context | `handler(PROC_INFO[])` |
| `menu.add_downloads_running` | Downloads (running) | `handler(DOWNLOAD_CTX[])` |
| `menu.add_downloads_finished` | Downloads (finished) | `handler(DOWNLOAD_CTX[])` |
| `menu.add_tasks` | All tasks | `handler(TASK[])` |
| `menu.add_tasks_job` | Running jobs | `handler(TASK[])` |
| `menu.add_targets` | Targets table — **different signature**: `(item, pos)` where pos = "top"\|"center"\|"bottom" | `handler(ids[])` |
| `menu.add_credentials` | Credentials table — **no agents/os/listeners filter**: `(item)` | `handler(ids[])` |

### Context data structures

```javascript
// FILE_INFO (filebrowser context)
{ agent_id, path, name, type }   // type: "file" | "dir"

// PROC_INFO (processbrowser context)
{ agent_id, pid, ppid, arch, session_id, context, process }
// Note: arch = "" on unix; session_id = TTY on unix

// DOWNLOAD_CTX (downloads context menu — subset of full DOWNLOAD)
{ agent_id, file_id, path, state }   // state: "finished"|"running"|"stopped"

// TASK (tasks context)
{ agent_id, task_id, state, type }
// state: "Hosted"|"Running"|"Success"|"Error"|"Canceled"
// type: "TASK"|"JOB"|"TUNNEL"|"unknown"
```

---

## event.* — Event Handlers

### Registration

```javascript
event.on_EVENT(handler, agents[], os[], listeners[], eventId)
// eventId is optional — use it to remove handler later
event.remove(eventId)
event.list()  // returns all registered handler IDs
```

### Available events

| Function | Trigger | Handler |
|----------|---------|---------|
| `event.on_new_agent` | New session registered | `handler(agentId)` |
| `event.on_filebrowser_disks` | Disks button clicked | `handler(agentId)` |
| `event.on_filebrowser_list` | Directory listing requested | `handler(agentId, path)` |
| `event.on_filebrowser_upload` | File upload triggered | `handler(agentId, path, filepath)` |
| `event.on_processbrowser_list` | Process list requested | `handler(agentId)` |
| `event.on_ready` | Client synced with server | `handler()` |
| `event.on_disconnect` | Client disconnected | `handler()` |
| `event.on_interval` | Periodic timer (every n sec) | `handler()` — returns event ID |
| `event.on_timeout` | One-shot timer (after n sec) | `handler()` — returns event ID |
