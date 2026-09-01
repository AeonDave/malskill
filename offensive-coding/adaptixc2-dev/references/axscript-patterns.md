# AxScript UI patterns

Use this reference for payload-builder forms, listener forms, service docks/dialogs, and UI-to-plugin calls. Confirm individual methods in `BridgeApp.h`, `BridgeForm.h`, `BridgeMenu.h`, `BridgeEvent.h`, and the wrapper headers at the pinned revision.

## Contents

- [Design for two runtimes](#design-for-two-runtimes)
- [Payload-builder form](#payload-builder-form)
- [Listener create/edit form](#listener-createedit-form)
- [Service dock with asynchronous work](#service-dock-with-asynchronous-work)
- [Bounded synchronous service request](#bounded-synchronous-service-request)
- [Agent and listener plugin calls](#agent-and-listener-plugin-calls)
- [Service command metadata](#service-command-metadata)
- [UI acceptance checks](#ui-acceptance-checks)

## Design for two runtimes

Agent and service `.axs` files are evaluated in two places:

- Teamserver Goja builds command and service-command metadata. Client UI methods are mostly stubs there.
- Qt `QJSEngine` creates real forms, menus, events, and plugin bridge requests.

Listener `.axs` is loaded only by the Qt client on the verified baseline; the Teamserver registers listener metadata without evaluating its script.

Keep top-level work limited to definitions and declarative registrations that both runtimes support. Do not read/write files, require an active profile, issue plugin calls, open dialogs, or create service UI at top level.

Use only these lifecycle entry points:

| Extender | Entry point | Invocation |
|---|---|---|
| Agent | `RegisterCommands(listenerType)` | Teamserver metadata registration |
| Agent | `GenerateUI(listenerTypes)` | Client requests a payload-builder form |
| Listener | `ListenerUI(modeCreate)` | Client creates or edits a listener |
| Service | `RegisterServiceCommands()` | Teamserver service command registration |
| Service | `InitService()` | Client calls it automatically after loading the service script |
| Any plugin UI | `data_handler(...)` | Client receives plugin-pushed data |

There is no `ServiceUI()` lifecycle call. Do not invoke `InitService()` or another UI function manually at the end of the file.

## Payload-builder form

`GenerateUI` returns a panel plus a container. The client serializes every element placed in the container and sends that JSON as `BuildProfile.AgentConfig`.

```javascript
function GenerateUI(listenerTypes) {
    const arch = form.create_combo();
    arch.addItems(["amd64", "arm64"]);

    const format = form.create_combo();
    format.addItems(["exe", "dll"]);

    const layout = form.create_gridlayout();
    layout.addWidget(form.create_label("Architecture"), 0, 0, 1, 1);
    layout.addWidget(arch, 0, 1, 1, 1);
    layout.addWidget(form.create_label("Format"), 1, 0, 1, 1);
    layout.addWidget(format, 1, 1, 1, 1);

    const container = form.create_container();
    container.put("schema_version", form.create_textline("1"));
    container.put("arch", arch);
    container.put("format", format);

    const panel = form.create_panel();
    panel.setLayout(layout);
    return {
        ui_panel: panel,
        ui_container: container,
        ui_height: 260,
        ui_width: 520
    };
}
```

The keys in `container.put` are the wire schema. Keep them stable and version the schema. The Go builder must still validate all values; disabled or hidden widgets are not a security boundary.

`form.create_selector_file()` serializes selected file content as base64, not the local path. Bound the encoded and decoded size server-side and avoid placing secrets in long-lived UI configuration.

The current payload dialog does not surface every build-socket error through its visible controls. Treat Teamserver build logs and the received artifact as completion evidence, not a quiet client dialog.

## Listener create/edit form

`ListenerUI(true)` is create mode; `ListenerUI(false)` is edit mode. Disable immutable identity/bind fields during edit and let the container restore existing JSON values.

```javascript
function ListenerUI(modeCreate) {
    const host = form.create_combo();
    const interfaces = ax.interfaces();
    for (const address of interfaces) {
        host.addItem(address);
    }
    host.setEnabled(modeCreate);

    const port = form.create_spin();
    port.setRange(1, 65535);
    port.setValue(8443);
    port.setEnabled(modeCreate);

    const timeout = form.create_spin();
    timeout.setRange(1, 300);
    timeout.setValue(30);

    const layout = form.create_gridlayout();
    layout.addWidget(form.create_label("Bind host"), 0, 0, 1, 1);
    layout.addWidget(host, 0, 1, 1, 1);
    layout.addWidget(form.create_label("Bind port"), 1, 0, 1, 1);
    layout.addWidget(port, 1, 1, 1, 1);
    layout.addWidget(form.create_label("Timeout (s)"), 2, 0, 1, 1);
    layout.addWidget(timeout, 2, 1, 1, 1);

    const container = form.create_container();
    container.put("host_bind", host);
    container.put("port_bind", port);
    container.put("timeout", timeout);

    const panel = form.create_panel();
    panel.setLayout(layout);
    return {ui_panel: panel, ui_container: container, ui_height: 260, ui_width: 520};
}
```

UI editability and server editability must agree. If a live field cannot be changed safely, keep it disabled in edit mode and reject changes in the plugin.

## Service dock with asynchronous work

Use `form.create_ext_dock` or `form.create_ext_dialog`; there is no global main-menu API for launching a service script. `InitService` is called automatically by the client.

```javascript
const SERVICE = "artifact-index";
let serviceUi = null;

function InitService() {
    if (serviceUi !== null) {
        serviceUi.dock.show();
        return;
    }

    const query = form.create_textline();
    const run = form.create_button("Search");
    const output = form.create_textmulti();
    output.setReadOnly(true);

    const layout = form.create_vlayout();
    layout.addWidget(query);
    layout.addWidget(run);
    layout.addWidget(output);

    const dock = form.create_ext_dock("artifact-index.results", "Artifact index", "right");
    dock.setLayout(layout);
    serviceUi = {dock: dock, output: output, pending: {}};

    form.connect(run, "clicked", function() {
        const requestId = ax.random_string(24, "hex");
        serviceUi.pending[requestId] = true;
        output.appendText("[pending] " + requestId);
        ax.plugin_service_command(SERVICE, "search.start", {
            request_id: requestId,
            query: query.text()
        });
    });

    dock.show();
}

function data_handler(data) {
    let message;
    try {
        message = JSON.parse(data);
    } catch (error) {
        ax.log_error(SERVICE + ": invalid response JSON");
        return;
    }

    if (!message.request_id || !serviceUi) {
        return;
    }
    delete serviceUi.pending[message.request_id];
    serviceUi.output.appendText(JSON.stringify(message));
}
```

`ax.plugin_service_command(service, command, objectOrNull)` is asynchronous. Its HTTP acknowledgement is discarded by the bridge; the plugin must send completion through `TsPluginServiceSendDataClient` or `TsPluginServiceSendDataAll`, which invokes `data_handler(data)`.

Show pending, success, error, timeout, and disconnected states explicitly. Keep a request ID because responses can arrive out of order or after the initiating view changes.

## Bounded synchronous service request

Use the wait form only for quick, bounded queries:

```javascript
const response = ax.plugin_service_wait(
    "artifact-index",
    "status.get",
    {request_id: ax.random_string(24, "hex")},
    3000
);

if (!response.ok) {
    ax.log_error("status.get: " + response.error);
} else {
    const result = response.result;
    ax.log("service state: " + JSON.stringify(result));
}
```

The method returns `{ok: false, error}` or `{ok: true, result, raw}`; it does not throw on normal transport/plugin failure. It is synchronous on the client path and can block UI responsiveness. Apply the [timeout and late-result contract](architecture-and-lifecycle.md#failure-contract).

## Agent and listener plugin calls

Both calls are asynchronous and accept an object or null:

```javascript
ax.plugin_agent_command(String(agentId), "cache.refresh", {request_id: requestId});
ax.plugin_listener_command(listenerName, "stats.get", {request_id: requestId});
```

Replies arrive at type-specific handlers:

```javascript
function data_handler(agentId, data) { /* agent AxScript */ }
function data_handler(listenerName, data) { /* listener AxScript */ }
function data_handler(data) { /* service AxScript */ }
```

Use string agent IDs when the source value is available as text. The current client converts the agent ID to a JavaScript number when invoking the agent `data_handler`, so values beyond JavaScript's safe-integer range remain a client limitation; do not round-trip them through arithmetic.

## Service command metadata

Register service console commands on the server runtime without issuing a service call during registration:

```javascript
function RegisterServiceCommands() {
    const status = ax.create_command("status", "Show service status");
    const group = ax.create_commands_group("artifact-index", [status]);
    ax.register_service_commands(group);
}
```

For agent commands, return the OS-specific command-group object expected by the current in-tree agent scripts. `setDefaultEnabled` is currently a server-side command-group builder method; use it only inside `RegisterCommands`, not client-executed code.

## Menus, files, and timers

- `menu` supports contextual registrations such as `add_session_agent`, `add_session_browser`, `add_filebrowser`, `add_targets`, `add_credentials`, and `add_payload_store`. It does not expose `add_main` or `add_main_axscript`.
- Use `ax.file_read` and `ax.file_write(path, data, append)`. There are no `file_write_text` or `file_write_binary` methods.
- `ax.prompt_save_file(filename, caption, filter)` takes the suggested filename first.
- `event.on_timeout` and `event.on_interval` return IDs; remove retained timers with `event.remove(id)` when the view is closed or no longer owns them.
- `encode_data`/`encode_file` support `hex`, `base64`, `base32`, `zip`, and `xor`. Text algorithms return strings; binary algorithms return `ArrayBuffer`-like data. Verify shape before composition.

## UI acceptance checks

Test every applicable runtime:

1. For agent/service scripts, Teamserver Goja loads the file and publishes intended command metadata; for listeners, verify listener catalog metadata without a Goja expectation.
2. Client reconnect/resync receives the file, Qt `QJSEngine` executes it, and the script creates exactly one dock/dialog or builder/listener form.
3. Submitted container JSON matches the Go schema, including file size behavior.
4. One plugin error and one malformed pushed result produce visible, bounded failure states.
5. Closing/reopening does not duplicate docks, signal connections, or timers.
6. Async responses remain correlated when two requests complete out of order.
