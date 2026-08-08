---
name: neuromatrix
description: "Operate the standalone, client-neutral NeuroMatrix emulation MCP: create isolated sessions, stage CAS artifacts, discover and run Unicorn/Qiling/QEMU/Renode tools, manage jobs and interactive processes, expose guest endpoints, and debug emulated targets with GDB. Use for reverse engineering, user-mode or full-system emulation, firmware/kernel/MCU analysis, guest-service rehosting, runtime-evidence collection, or as the optional emulation provider behind MCPwn or another orchestrator."
---

# NeuroMatrix Operator

NeuroMatrix is a standalone, client-neutral MCP server for reverse-engineering emulation. It gives any compatible client one session/artifact/job/endpoint surface across Unicorn, Qiling, QEMU, and Renode. It does not depend on MCPwn; MCPwn is one optional orchestrator.

Use the default Streamable HTTP MCP endpoint (`/mcp`) unless the deployment explicitly enables legacy SSE. Keep the direct MCP surface small, discover backend tools through the catalog, move large bytes through the artifact data plane, and collect runtime evidence before claiming support.

## Safety and trust

- NeuroMatrix executes uploaded binaries, emulator processes, and trusted script tools. Use it only in an isolated, authorized lab.
- Keep MCP and artifact HTTP listeners bound to loopback unless they sit behind a trusted authenticated boundary.
- Windows and macOS runtime assets are proprietary and caller-supplied; do not expect them in a fresh image.
- Do not treat an emulator startup, profile listing, static classification, or missing-error-free response as proof that a target actually ran.

## The Loop

1. **Connect and create one session.** Use `create_session(backend, arch, os_name?, rootfs?, config?, session_id?)`. Reuse the session for the task. Lost state after context reset? Use `list_sessions`, `list_events`, and `list_guest_endpoints` before creating another one.
2. **Discover before calling.** In `agent` mode, backend-specific tools are catalog-only. Use `list_catalog(category="backend", backend="<backend>", include_schema=true)` or `get_tool("<name>")`, then call `run_tool("<name>", {...})`.
3. **Move artifacts correctly.** Existing disk files go through `request_upload` + HTTP `PUT`, then use `mcp://artifacts/<sha256>` directly or `import_artifact_to_workspace` when mutation/execution from a workspace path is needed.
4. **Choose the backend lane.** Use the backend routing table below. If the lane fails because a lower layer is missing, escalate to the backend that models that layer.
5. **Run with the right lifecycle.** Short catalog tools can run inline. Long-running tools require `run_tool(..., detach=true)` and `poll_job`.
6. **Collect evidence.** Use memory/register output, disassembly, traces, QEMU console transcripts, QMP/GDB endpoint reachability, Renode UART/peripheral facts, guest service responses, and artifact-backed outputs.
7. **Clean up.** Close guest endpoints and interactive sessions, delete finished jobs, then call `destroy_session` synchronously; detached destruction is rejected because the destroy job would own the session it removes. Session destruction drains leased operations, removes mutable workspace state, and preserves immutable CAS artifacts until explicit confirmed deletion. If cleanup fails, inspect the retained `cleanup_failed` session and retry.

## Direct vs catalog tools

Direct `agent` tools are infrastructure:

- catalog: `list_catalog`, `get_tool`, `run_tool`
- sessions/events: `create_session`, `destroy_session`, `list_sessions`, `list_events`, `supported_architectures`
- files/artifacts: `upload_file`, `download_file`, `list_session_files`, `request_upload`, `request_download`, `list_artifacts`, `analyze_artifact`, `extract_artifact_subartifact`, `import_artifact_to_workspace`, `delete_artifact`
- jobs: `list_jobs`, `poll_job`, `delete_job`
- guest endpoints: `list_guest_endpoints`, `get_guest_endpoint`, `register_guest_endpoint`, `close_guest_endpoint`, `endpoint_client_context`, `spawn_endpoint_client`
- small direct binary helpers: `load_binary`, `inspect_binary`
- interactive process helpers: `start_interactive_session`, `read_interactive_session`, `send_interactive_input`, `signal_interactive_session`, `close_interactive_session`, `list_interactive_sessions`

Backend state operations belong behind `run_tool` in `agent` mode. Never guess backend tool schemas; call `get_tool`.

## Backend routing

The backend identifiers are exactly `unicorn`, `qiling`, `qemu`, and `renode`.
OVMF, SeaBIOS, and AAVMF are QEMU firmware assets, not backend identifiers; use
`backend="qemu"` for those lanes and never pass a firmware name as `backend`.

| Need | Backend |
|---|---|
| Raw CPU bytes, shellcode, decode loop, patch/trace memory/registers | Unicorn |
| Userland binary with OS syscalls/APIs, rootfs, Windows PE, Mach-O, UEFI target/API hooks | Qiling |
| Linux user-mode, full VM, Linux kernel, disks, firmware boot, OVMF/SeaBIOS, QMP/GDB, Hexagon DSP | QEMU |
| MCU/RTOS/SoC board behavior, UART/GPIO/peripherals, `.repl`/`.resc`, board GDB | Renode |
| Firmware service exposed over UART/TCP/HTTP/SSH/etc. | Backend endpoint tools + guest endpoint registry |
| Unknown router/camera/Linux firmware | Artifact analysis → rootfs/init/kernel facts → QEMU user/system or Qiling fallback |

For detailed lane choices, load [references/backend-routing.md](references/backend-routing.md).

## Execution path

| Situation | Path |
|---|---|
| Fast direct infrastructure tool | call it directly |
| Fast backend catalog tool | `run_tool("name", {...})` |
| Long-running catalog tool | `run_tool("name", {...}, detach=true)` → `poll_job(job_id, wait_seconds=30)` |
| Live stdin/stdout process in session workspace | `start_interactive_session` → keep target `pid` + handle → `read_interactive_session` / `send_interactive_input` |
| Guest-exposed UART/GDB/QMP/service endpoint | `list_guest_endpoints` → `endpoint_client_context` → external tool or `spawn_endpoint_client` |

Known long-running catalog tools include `qemu_start_process`, `qemu_system_start`, `qemu_linux_start`, `qemu_firmware_start`, `qiling_run_os_binary`, `renode_start`, `renode_continue`, `build_initramfs_artifact`, `build_rootfs_disk_artifact`, `build_esp_image_artifact`, `extract_artifact_filesystem`, and trace/export/continue-style tools.

## File movement

| Goal | Mechanism |
|---|---|
| Small text or generated bytes already in context | `upload_file` |
| Existing local binary/firmware/kernel/rootfs/disk | `request_upload` → HTTP `PUT --data-binary` → `mcp://artifacts/<sha256>` |
| Read-only analysis | pass `mcp://artifacts/<sha256>` to `analyze_artifact`, `inspect_binary`, or compatible backend tools |
| Tool must mutate/execute a real file path | `import_artifact_to_workspace(session_id, artifact_id, executable?)` |
| Pull a large result out | `request_download` → HTTP `GET` |
| Pull small session file out | `download_file` |

Do not base64 a disk file through the model. Use the artifact data plane even for medium-sized files.

For job/artifact/endpoint details, load [references/artifacts-jobs-endpoints.md](references/artifacts-jobs-endpoints.md).

## Guest endpoints

NeuroMatrix reports reachable guest surfaces as session-scoped endpoint metadata: `uart`, `unix`, `raw-tcp`, `raw-udp`, `http`, `https`, `ssh`, `ftp`, `telnet`, `rtsp`, `onvif`, `modbus`, `gdb-remote`, `qmp`, `hmp`, `jtag`, `gpio`, and `custom`.

NeuroMatrix does not provide first-party HTTP/SSH/FTP/Telnet clients. Use the endpoint context to drive external tools, Python virtualenv clients, or uploaded workspace scripts. `spawn_endpoint_client` is for running those client commands with endpoint environment variables pre-populated.

Respect endpoint `scope`. A `neuromatrix_local` loopback address is reachable by a client spawned inside NeuroMatrix, not automatically by a different container or host. Treat `status`, address, and scope as declarations until `status_verified`/`reachability_verified` or a real client handshake supplies evidence.

## Debugging and composition

- `attach_debugger` records session metadata only; it does not launch or connect a debugger.
- For QEMU full-system or Renode, start the backend GDB stub and use the registered `gdb-remote` endpoint.
- For QEMU user-mode debugger waits or prompt-driven binaries, import the executable and start the matching `qemu-ARCH` process through `start_interactive_session`; `qemu_start_process` is bounded and has no stdin.
- Use `endpoint_client_context` before connecting. Run `gdb`/`gdb-multiarch` with `spawn_endpoint_client` when the endpoint is provider-local; custom deployments must make a suitable client available.
- NeuroMatrix has no native Frida tool. An external client may manage Frida against an explicitly reachable target, but NeuroMatrix remains unaware of that client.

Load [references/debugging-and-composition.md](references/debugging-and-composition.md) for concrete GDB flows, interactive binary-input rules, and the optional MCPwn mapping.

## Strict rules

- One session per task unless isolation requires more.
- Always inspect a backend tool schema with `get_tool` before first use.
- Long-running catalog tools without `detach=true` return a structured error; do not fight the timeout.
- Use the documented interactive text transport and terminal-state contract; do not infer binary-safe stdin or rewrite a terminal failure as a successful close. `pid` is the target process; `supervisor_pid` is lifecycle infrastructure and is not a debug target.
- No default kernel, firmware, rootfs, DTB, symbols, or proprietary OS assets are bundled as task evidence. The caller supplies them.
- Windows/macOS Qiling lanes require legitimate OS assets; Wine/ReactOS-style substitutes are not parity proof.
- Renode profile discovery is not firmware runtime evidence; prove firmware load, CPU execution, UART/GDB/peripheral behavior, or an expected failure.
- Generic Xtensa is not ESP8266 parity; use an ESP8266-aware runtime or report `unsupported_by_installed_backend`.
- QEMU OVMF/SeaBIOS boot is firmware evidence, not a claim of complete SMM/SMRAM/Ring -2 platform parity.
- If a hook/stub/fake environment value is used, label it and do not confuse it with native target behavior.

## Resources

- [references/backend-routing.md](references/backend-routing.md) — load when choosing Unicorn/Qiling/QEMU/Renode or deciding whether a failed lane should escalate.
- [references/artifacts-jobs-endpoints.md](references/artifacts-jobs-endpoints.md) — load for artifact upload/download/import, detached jobs, workspace cleanup, and guest endpoint clients.
- [references/debugging-and-composition.md](references/debugging-and-composition.md) — load for QEMU/Renode GDB sessions, debugger endpoint scope, interactive text driving and binary-input limitations, or optional use through MCPwn.
- [references/evidence-and-limitations.md](references/evidence-and-limitations.md) — load before reporting capability coverage, runtime success, or support limitations.

