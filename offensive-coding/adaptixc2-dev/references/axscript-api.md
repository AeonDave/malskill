# AxScript API lookup

This is a selected, source-verified map for extender UI work, not a frozen or exhaustive API catalog. At a new Adaptix revision, prefer the declarations and implementations:

```bash
rg -n "public Q_SLOTS|Q_INVOKABLE|Q_SIGNALS" \
  AdaptixClient/Headers/Client/AxScript/Bridge*.h \
  AdaptixClient/Headers/Client/AxScript/Ax*Wrappers.h
rg -n "axObj.Set|formObj.Set|menuObj.Set|eventObj.Set" AdaptixServer/core/axscript
```

`BridgeApp.h` is authoritative for the real client `ax` object. For agent/service scripts, server `bridge_*.go` files establish Goja metadata behavior and stub parity. Listener scripts are client-only on the verified baseline.

## Contents

- [Global objects](#global-objects)
- [Plugin bridge calls](#plugin-bridge-calls)
- [Builder and listener factories](#builder-and-listener-factories)
- [Common widget methods](#common-widget-methods)
- [Commands and groups](#commands-and-groups)
- [Contextual menus](#contextual-menus)
- [Client events](#client-events)
- [Files, prompts, encoding, and logging](#files-prompts-encoding-and-logging)

## Global objects

| Object | Purpose |
|---|---|
| `ax` | Adaptix data, command construction, files/prompts, plugin calls, logging |
| `form` | widgets, layouts, containers, dialogs, persistent extender docks |
| `menu` | contextual menu registrations |
| `event` | client events and timers |

Do not infer an API from a similarly named v1 method. A name must exist in the pinned client header and, when evaluated server-side, have the required Goja implementation or stub.

## Plugin bridge calls

| Call | Return and delivery |
|---|---|
| `ax.plugin_service_command(service, command, args?)` | `void`; async acknowledgement discarded; result arrives at service `data_handler(data)` |
| `ax.plugin_service_wait(service, command, args?, timeoutMs?)` | `{ok:false,error}` or `{ok:true,result,raw}` |
| `ax.plugin_agent_command(agentId, command, args?)` | `void`; result arrives at agent `data_handler(agentId, data)` |
| `ax.plugin_listener_command(listenerName, command, args?)` | `void`; result arrives at listener `data_handler(listenerName, data)` |

`args` must be an object, null, or omitted. The wait method also accepts the timeout as its third argument when no args object is needed. Non-positive timeouts fall back to the client default of 30 seconds.

These older-looking names are not present: `service_command`, `service_command_rpc`, `plugin_service_rpc`, `agent_command`, and `listener_command`.

## Builder and listener factories

`form` exposes:

```text
create_vlayout()                  create_hlayout()
create_gridlayout()               create_panel()
create_container()                create_tabs()
create_groupbox(title, checkable)
create_label(text)                create_textline(text)
create_combo()                    create_spin()
create_check(label)               create_switch(label)
create_button(text)               create_textmulti(text)
create_logview()                  create_list()
create_table(headers)             create_selector_file()
create_dialog(title)              create_ext_dialog(title)
create_ext_dock(id, title, location?, icon?)
```

The container is the serialization boundary:

| Method | Meaning |
|---|---|
| `put(key, widget)` | include a widget value in emitted JSON |
| `get(key)` / `contains(key)` / `remove(key)` | manage registered elements |
| `toJson()` / `fromJson(json)` | serialize or restore values |
| `toProperty()` / `fromProperty(object)` | property-shaped conversion |

Only wrappers implementing the element serialization contract contribute values. A selected file contributes base64 content.

## Common widget methods

All visual wrappers expose `setEnabled(bool)`, `setVisible(bool)`, `getEnabled()`, and `getVisible()` unless their header says otherwise.

| Wrapper | Selected methods | Signals for `form.connect` |
|---|---|---|
| text line | `text`, `setText`, `setPlaceholder`, `setReadOnly` | `textChanged`, `textEdited`, `returnPressed`, `editingFinished` |
| combo | `addItem`, `addItems`, `setItems`, `clear`, `currentText`, `setCurrentText`, `currentIndex`, `setCurrentIndex` | `currentTextChanged`, `currentIndexChanged` |
| spin | `value`, `setValue`, `setRange` | `valueChanged` |
| checkbox | `isChecked`, `setChecked` | `stateChanged` |
| button | `text`, `setText`, `setIcon`, `setIconSize`, `setFixedSize` | `clicked` |
| text multi | `text`, `setText`, `appendText`, `setPlaceholder`, `setReadOnly` | none in the current wrapper |
| table | `addItem`, `rowCount`, `text`, `setText`, `selectedRows`, `resizeToContent(column)`, `clear` | `cellChanged`, `cellClicked`, `cellDoubleClicked` |

`form.connect(sender, signalName, handler)` requires the exact Qt signal name exposed by the wrapper.

Layouts and surfaces:

```text
boxLayout.addWidget(widget)
boxLayout.addStretch(stretch?)
gridLayout.addWidget(widget, row, column, rowSpan?, columnSpan?)
panel.setLayout(layout)
dialog.setLayout(layout); dialog.setSize(width, height); dialog.exec()
dock.setLayout(layout); dock.setSize(width, height); dock.show(); dock.hide(); dock.close()
```

Use a unique, stable dock ID. Re-running initialization must not create duplicate docks or signal connections.

## Commands and groups

```javascript
const command = ax.create_command(name, description, example, message);
command.addArgString(name, required, description);
command.addArgFlagString(flag, name, required, description);
command.addArgInt(name, required, description);
command.addArgFlagInt(flag, name, required, description);
command.addArgBool(flag, required, description);
command.addArgFile(name, required, description);
command.addArgFlagFile(flag, name, required, description);
command.setPreHook(handler);
command.setPostHook(handler);
command.setHandler(handler);
command.setDestructive(true);

const group = ax.create_commands_group(name, [command]);
group.add([anotherCommand]);
```

Argument overloads are interpreted dynamically. Copy the closest current in-tree command and verify `AxCommandWrappers.*` plus server `bridge_command.go` before relying on optional forms.

Server-only command metadata supports `group.setDefaultEnabled(bool)` inside `RegisterCommands`; the current Qt `AxCommandGroupWrapper` does not expose that method. Do not call it from client-executed code.

Register explicitly:

```text
ax.register_commands_group(group, agents, os, listeners)
ax.register_service_commands(group)
```

For agent config scripts, the Teamserver also consumes the object returned by `RegisterCommands(listenerType)`; match the current in-tree agent shape rather than inventing a new schema.

## Contextual menus

Create items with `menu.create_action`, `menu.create_menu`, and `menu.create_separator`. Register them with the current contextual methods:

```text
add_session_main       add_session_agent
add_session_browser    add_session_access
add_filebrowser        add_processbrowser
add_downloads_running  add_downloads_finished
add_tasks              add_tasks_job
add_targets            add_credentials
add_payload_store
```

No `add_main`, `add_main_axscript`, or service-wide main-menu method exists in `BridgeMenu.h`. Use an extender dock/dialog for service UI.

## Client events

Selected registrations:

```text
event.on_ready(handler, eventId?)
event.on_disconnect(handler, eventId?)
event.on_new_agent(handler, agents, os?, listeners?, eventId?)
event.on_filebrowser_list(handler, agents, os?, listeners?, eventId?)
event.on_processbrowser_list(handler, agents, os?, listeners?, eventId?)
event.on_interval(handler, delayMs, eventId?) -> id
event.on_timeout(handler, delayMs, eventId?) -> id
event.list()
event.remove(id)
```

Keep timer IDs and remove them when their owning surface closes.

## Files, prompts, encoding, and logging

```text
ax.file_exists(path) -> bool
ax.file_read(path) -> QByteArray
ax.file_write(path, data, append?) -> bool
ax.file_size(path) -> integer
ax.prompt_open_file(caption?, filter?) -> path
ax.prompt_open_dir(caption?) -> path
ax.prompt_save_file(filename, caption?, filter?) -> path
ax.log(text)
ax.log_error(text)
ax.console_message(agentId, message, type?, clearText?)
```

Filesystem calls are subject to the script context policy. Do not persist secrets by default. `file_write_text` and `file_write_binary` do not exist.

`encode_data` and `encode_file` accept `hex`, `base64`, `base32`, `zip`, or `xor`. Text encodings return a string; binary encodings return binary data. `decode_data`/`decode_file` return bytes. Confirm input/output shape before concatenation or JSON serialization.
