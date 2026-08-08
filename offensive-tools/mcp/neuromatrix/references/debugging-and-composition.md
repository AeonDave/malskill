# NeuroMatrix Debugging and Client Composition

Use this reference for real debugger sessions and for mapping NeuroMatrix into another MCP client without making NeuroMatrix client-specific.

## Debugger boundary

`attach_debugger` stores debugger selection, endpoint, and mode in session state. It is metadata only: it does not start a stub, launch GDB, connect a client, start Frida, or inject a process.

Use an actual backend path:

| Target | Start the debug surface | Connect the client |
|---|---|---|
| QEMU full-system Linux/firmware | `qemu_linux_start(gdb=true)`, `qemu_firmware_start(gdb=true)`, or `qemu_gdbserver_start` | registered `gdb-remote` endpoint |
| Running generic QEMU system VM | `qemu_gdbserver_start` | registered `gdb-remote` endpoint |
| QEMU user-mode process | `start_interactive_session` with `qemu-ARCH -g PORT <internal_path>` | manually registered/verified endpoint |
| Renode machine | `renode_start_gdbserver` | registered `gdb-remote` endpoint |

`qemu_gdbserver_start` controls the `qemu-system-*` stub. If no VM is running, its planned configuration applies to the next `qemu_system_start`, not to `qemu_start_process`.

## QEMU user-mode GDB flow

1. Create a QEMU session for the target architecture.
2. Upload the executable through the artifact data plane and call `import_artifact_to_workspace(..., executable=true)`.
3. Start the matching provider-side emulator with `start_interactive_session`, for example `qemu-x86_64-static` with `args=["-g", "1234", "<internal_path>"]`.
4. Register or inspect a `gdb-remote` endpoint whose `scope` matches its real reachability.
5. Call `endpoint_client_context`; inspect `client_execution.can_spawn_from_neuromatrix`, `available_clients`, and `client_requirement`.
6. If the endpoint is `neuromatrix_local`, use `spawn_endpoint_client` with an installed `gdb` or `gdb-multiarch`. Substitute the literal host and port returned by `endpoint_client_context`:

   ```json
   {"tool":"spawn_endpoint_client","arguments":{"endpoint_id":"gend-...","command":"gdb","args":["-q","-nx","-batch","-ex","target remote 127.0.0.1:1234","-ex","info registers rip"]}}
   ```

   `command`/`args` are direct-exec values: `$NEUROMATRIX_ENDPOINT_HOST` and `$NEUROMATRIX_ENDPOINT_PORT` are not expanded. If shell expansion is deliberate, make the shell explicit:

   ```json
   {"tool":"spawn_endpoint_client","arguments":{"endpoint_id":"gend-...","command":"/bin/sh","args":["-lc","gdb -q -nx -batch -ex \"target remote ${NEUROMATRIX_ENDPOINT_HOST}:${NEUROMATRIX_ENDPOINT_PORT}\" -ex \"info registers rip\""]}}
   ```

7. Capture the returned `interactive_id`, call `read_interactive_session(interactive_id, wait_seconds=5, output_mode="auto")`, and require a successful remote handshake plus a real register/PC, disassembly, breakpoint, or stepping result. Process creation or endpoint metadata alone is not connection evidence.
8. Call `close_interactive_session(interactive_id)`. Otherwise deliberately publish/forward the endpoint and connect from the reachable client scope. Detach GDB, close the endpoint and interactive emulator, then destroy the session.

The official Docker runtime includes GDB clients. A custom or bare-metal deployment must install one or import a suitable executable; `spawn_endpoint_client` never installs software.

## Interactive process rules

Use the exact lifecycle:

1. `start_interactive_session`
2. `send_interactive_input`
3. `read_interactive_session`
4. `signal_interactive_session` or `close_interactive_session`

There is no `send_interactive_session` tool. `send_interactive_input.input` is JSON text encoded as UTF-8. It is suitable for commands and line protocols, not packed addresses, NUL bytes, or arbitrary binary payloads. For exact bytes, stage and execute a provider-side harness or send hex/base64 text and decode it before writing to the target.

Long-poll with bounded `wait_seconds` and use `output_mode="auto"` so large transcripts become artifacts instead of flooding the MCP channel.

Terminal states are evidence: zero exit is `exited`, unexpected non-zero is `error`, a requested signal is `terminated`, and closing a running process is `closed`. Closing an already-finished process preserves its original terminal state. The returned `pid` belongs to the target; `supervisor_pid` identifies the per-process ownership helper. On Linux that helper is the local subreaper; on Windows it owns the target Job Object. Never attach a debugger to `supervisor_pid`.

## External clients and MCPwn

NeuroMatrix exposes native `session_id`, artifact, job, endpoint, and interactive handles. It does not know which MCP client invokes it.

An orchestrator must:

- preserve each returned `provider_ref` because artifact URIs are provider-scoped;
- inspect `list_catalog.provider_identity.stable_across_restarts` before persisting mappings: when false, scope them to the current provider process and rediscover after restart; configure `NEUROMATRIX_INSTANCE_ID` when durable cross-restart mappings are required;
- map any local scenario name to the native NeuroMatrix `session_id`;
- discover exact native schemas instead of translating guessed tool names;
- move artifact bytes through upload/download data planes rather than MCP JSON;
- honor endpoint scope and run the client in a reachable execution context;
- clean both its own registry and NeuroMatrix's registry.

When MCPwn is the orchestrator, its catalog-only `emulation` domain provides `emulation_discover`, `emulation_scenario`, `emulation_artifact`, `emulation_run_tool`, `emulation_operation`, `emulation_endpoints`, and `emulation_endpoint_client`. These are compatibility mappings, not capabilities hidden inside NeuroMatrix. NeuroMatrix works identically when called directly by another MCP client.

NeuroMatrix has no native Frida wrapper. An orchestrator may run Frida against an explicitly reachable process or server, but owns that Frida lifecycle itself.

## Cleanup contract

`destroy_session` is synchronous and idempotent; `run_tool(..., detach=true)` is rejected for it. It drains leased operations, stops session-owned runtime resources, closes endpoints and interactive clients, cancels jobs, removes the mutable workspace without following symlinks, and preserves immutable CAS artifacts. Cleanup failure retains a retryable session instead of claiming success. A repeated destroy retries stale workspace cleanup and may report that no workspace was found.
