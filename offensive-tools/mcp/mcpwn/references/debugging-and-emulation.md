# MCPwn Debugging and NeuroMatrix Emulation

Use this reference to select the debugger's execution locus and to compose MCPwn with NeuroMatrix without conflating their runtimes.

## Select the locus

| Target | Run the debugger/client | Route |
|---|---|---|
| PID visible to MCPwn's API runtime | Inside MCPwn | `gdb_attach_process` or local Frida |
| Binary staged but not running in an MCPwn workspace | Inside MCPwn | `gdb_batch_analyze` or `gdb_start_interactive` |
| Separate Windows/Linux/macOS host or device | Wherever the exported debug server is reachable | Frida host/device transport or interactive GDB remote |
| QEMU/Renode target inside NeuroMatrix | Prefer inside NeuroMatrix for a provider-local endpoint | NeuroMatrix endpoint client, optionally driven through MCPwn |

`local` is runtime-relative. In Docker, an MCPwn-local PID belongs to the container. Do not pass a Docker-host PID to `gdb_attach_process` or assume `device="local"` can cross the container boundary.

## GDB in MCPwn

1. Create one MCPwn analysis session.
2. Stage the executable, symbols, loader, and libraries in that session. Use `request_upload` plus `import_artifact_to_workspace` for existing files.
3. Start the target with `start_interactive_shell`; keep both `interactive_id` and the returned container `pid`. Recover them with `list_interactive_sessions` after context loss.
4. Discover the exact schema:
   - `get_tools(domain="pwn", query="gdb attach")`
   - `get_tool("gdb_attach_process")`
5. Run `gdb_attach_process(session_id, pid, binary_filename?, commands?, timeout?)` for a bounded attach. `timeout` accepts 1–600 seconds and defaults to 120. It elevates only GDB and detaches the inferior automatically.
6. Use `gdb_batch_analyze(session_id, binary_filename, commands, inferior_args?, timeout)` for scripted work. Commands such as `run` or `continue` can block, so choose an explicit timeout; timeout cleanup owns the GDB/inferior process group and escalates to SIGKILL when needed.
7. Use `gdb_start_interactive` when breakpoints, repeated stepping, or manual `target remote HOST:PORT` commands require a live TTY. Drive it with the returned interactive-shell ID and close it explicitly.

Treat `timed_out=true` as incomplete execution; current MCPwn results set `success=false` on timeout even when `partial_results` preserves useful output. Inspect `timed_out`, `return_code`, and `partial_results` before accepting debugger results. If a catalog call may exceed 30 seconds, dispatch the outer `run_tool` with `detach=true`; the inner GDB timeout remains the execution bound.

For a remote GDB stub, confirm the endpoint is listening and reachable from the MCPwn runtime. A loopback endpoint in another container is not reachable without publishing, forwarding, or running the GDB client in that provider.

## Frida in MCPwn

Discover both wrappers with `get_tools(domain="mobile", query="frida debug")` and inspect their schemas.

- `frida_server_manage` controls Frida Server endpoints over `local`, `adb`, `ssh`, or `docker`. `manifest` only resolves or installs a matching Server/Gadget asset; the target MCP owns start/status/stop, while Gadget injection/repackaging remains a separate workflow.
- Both `frida_server_manage` and `frida_instrument` are catalog-long-running. Dispatch either through `run_tool(..., detach=true)`, poll the job, and apply the cancellation evidence rules from [execution-model.md](execution-model.md).
- `frida_instrument` supports process listing, tracing, spawning with a script, and attaching with a script.
- `device="local", elevated=true` applies passwordless-sudo elevation only to local attach/trace inside MCPwn. Spawn and remote-device workflows remain non-elevated.
- To target a separate Windows/Linux/macOS host, run `frida-server-manager` or the repository host wrapper in that host context. Pass its returned `connection.host` and `connection.token` to `frida_instrument`; supply `certificate` or `keepalive_interval` separately only when an externally configured endpoint requires them.
- On Docker Desktop, the host wrapper normally advertises `host.docker.internal:27042`. Use the returned connection object rather than inventing an address or token.
- The component that starts an external Frida endpoint owns it. Before finishing, run the same host manager's `stop`, then require a verified `status` showing it is no longer running.

If Frida reports `diagnostic_code="frida_injected_loader_crash"`, treat it as target/runtime incompatibility common with static or static-PIE ELF injection, not as proof of a sudo/PTRACE failure. Follow `recommended_tool`; for a local target this is normally `gdb_attach_process`.

## Optional NeuroMatrix bridge

MCPwn can run without NeuroMatrix. NeuroMatrix is a standalone, client-neutral MCP server; the MCPwn adapter only maps its native handles and never creates hidden emulator state.

1. Configure `NEUROMATRIX_MCP_URL` and `NEUROMATRIX_ARTIFACT_BASE_URL` in the MCPwn runtime, then recreate it so the adapter reads them. On Docker Desktop, set `NEUROMATRIX_MCP_URL=http://host.docker.internal:8000/mcp` and `NEUROMATRIX_ARTIFACT_BASE_URL=http://host.docker.internal:5101`; the NeuroMatrix artifact port must differ because MCPwn already owns host port `5001`.
2. Discover `get_tools(domain="emulation", query="neuromatrix")`.
3. Call `emulation_discover` and inspect the provider catalog revision and exact remote schemas.
4. Create a scenario with `emulation_scenario(action="create", backend=..., arch=...)`. Its `scenario_id` is the NeuroMatrix `session_id`.
5. Stage immutable bytes with `emulation_artifact(action="stage", artifact_ref=..., scenario_id=..., executable=true)`; never pass an MCPwn workspace path as a NeuroMatrix path.
6. Run a discovered native backend tool through `emulation_run_tool`. For detached work, poll the returned MCPwn bridge operation ID; retain the native NeuroMatrix job ID as the recovery path for `emulation_operation`. If the local bridge watcher times out, remote execution may still continue: inspect `execution_stopped`/`remote_execution_may_continue`, invoke deletion, and retain the bridge until provider cancellation is proven.
7. Inspect endpoint scope with `emulation_endpoints(action="context", endpoint_id=...)`. Check `client_execution.can_spawn_from_neuromatrix`, `available_clients`, and `client_requirement`; use `emulation_endpoint_client` when the client must execute inside NeuroMatrix.
8. Close endpoint clients/endpoints, cancel or delete jobs, then destroy the scenario synchronously. MCPwn and NeuroMatrix CAS references are provider-scoped; collect an artifact explicitly when moving it between stores.

## Emulated GDB sessions

- QEMU full-system: start or configure the QEMU system GDB stub, inspect its `gdb-remote` endpoint, then spawn the client from a reachable scope. For a `neuromatrix_local` endpoint, use `emulation_endpoint_client(action="spawn", endpoint_id=..., command="/bin/sh", args=["-lc", "gdb -q -nx -batch -ex 'set pagination off' -ex \"target remote ${NEUROMATRIX_ENDPOINT_HOST}:${NEUROMATRIX_ENDPOINT_PORT}\" -ex 'info registers'"])`. NeuroMatrix injects the endpoint variables; do not override reserved `NEUROMATRIX_ENDPOINT_*` names.
- QEMU user-mode: import the target into the NeuroMatrix workspace, start `qemu-ARCH` interactively with `-g PORT`, register/inspect the endpoint, and run GDB where that provider-local port is reachable.
- Renode: start its GDB server and use the registered endpoint.
- NeuroMatrix `attach_debugger` records debugger metadata only. It does not launch GDB, connect a client, start Frida, or inject a process.
- NeuroMatrix has no native Frida tool. If Frida is appropriate, MCPwn or another client owns the Frida lifecycle and must reach an explicitly exposed target.

Endpoint status/address/scope are declarations until verified. Require a real GDB handshake plus register, PC, disassembly, breakpoint, or stepping evidence before claiming the debug session works; close the endpoint client afterward.

Interactive input is UTF-8 JSON text, not arbitrary bytes. For packed exploit payloads, stage a provider-side harness or send hex/base64 text and decode it before the target consumes it.

## Cleanup proof

Before finishing, verify every lifecycle owner independently:

- MCPwn: no unintended sessions, jobs, or interactive shells.
- NeuroMatrix: no unintended sessions, jobs, endpoints, or interactive clients.
- External host/device: stop and verify any Frida server, GDB stub, tunnel, or forward started outside those registries.
- Destroying a NeuroMatrix session removes its mutable workspace but preserves immutable CAS artifacts until explicit confirmed deletion.
