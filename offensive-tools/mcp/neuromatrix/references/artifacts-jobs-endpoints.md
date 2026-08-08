# NeuroMatrix Artifacts, Jobs, and Endpoints

Use this reference when moving files, running long jobs, or talking to guest-exposed services/debug channels.

## Artifact upload

For existing local files, do not inline base64 through MCP.

1. Compute size and SHA-256 locally.
2. `request_upload(filename, file_size_bytes, checksum_sha256, session_id?, mime_type?)`
3. Branch on the returned ticket:
   - `upload_required=true`: PUT raw bytes to the exact returned URL and include every `required_headers` entry.
     - POSIX: `curl -sS -X PUT --data-binary @artifact.bin "<upload_url>" -o /dev/null -w "%{http_code}\n"`
     - PowerShell: `curl.exe -sS -X PUT --data-binary "@artifact.bin" "<upload_url>" -o NUL`
   - `upload_required=false` / `already_exists=true`: do not expect an `upload_url` and do not PUT; reuse the returned `artifact_id` / `resource_uri` directly.
4. Use the returned `artifact_id` or `mcp://artifacts/<sha256>`.
5. If a tool needs a mutable server path, call `import_artifact_to_workspace(session_id, artifact_id, executable?)`.

Analyze before routing:

```json
{"tool":"analyze_artifact","arguments":{"artifact_id":"mcp://artifacts/<sha256>"}}
```

Use `extract_artifact_subartifact` for byte ranges/gzip members and `extract_artifact_filesystem` for supported filesystem extraction. Filesystem extraction is long-running: detach it.

## Artifact download

- `request_download(artifact_id, filename?)` returns an expiring HTTP GET URL.
- POSIX: `curl -sS "<download_url>" -o artifact.bin`; PowerShell: `curl.exe -sS "<download_url>" -o "artifact.bin"`.
- Use it for large outputs, disk images, transcripts, memory dumps, extracted filesystems, and generated initramfs/ESP/rootfs artifacts.
- `download_file` is for small session workspace files, not CAS-scale outputs.

## Workspace files

Use the session workspace for files that must be mutable or executable by server-side tools:

- patched binaries
- GDB scripts
- generated `.repl` / `.resc`
- temporary client scripts
- writable disk copies

Use `list_session_files` to inspect workspace state. Prefer workspace/file tools over shell `cat` for bounded reads.

`destroy_session` is synchronous: do not call it through `run_tool(..., detach=true)`. It marks the session `destroying`, rejects new leased operations, drains active operations, then stops session-owned resources and removes the mutable workspace. A failed cleanup keeps the session visible as `cleanup_failed` for inspection/retry. It does not delete immutable CAS artifacts. Repeated destruction is safe and retries stale workspace cleanup from an interrupted or older run.

## Detached jobs

Long-running catalog tools must be called with `detach=true`.

```json
{"tool":"run_tool","arguments":{"name":"qemu_linux_start","arguments":{"session_id":"k1","kernel":"mcp://artifacts/<sha256>"},"detach":true}}
{"tool":"poll_job","arguments":{"job_id":"job-...","wait_seconds":30}}
```

Use `list_jobs` after a context reset. `delete_job` removes a running record only after execution stop is proven. Backends with a native process handle attempt a hard kill; otherwise the result may remain `cancellation_pending` with `record_deleted=false` and `retry_delete_after_stop=true`. Poll until terminal, then retry deletion. A successful cancellation request alone is not proof that the worker stopped.

Do not tight-loop `poll_job`. Long-poll with bounded waits and report the latest job state.

## Guest endpoints

Backends register endpoint metadata for UART, GDB remote, QMP, HTTP/HTTPS, SSH/FTP/Telnet, RTSP/ONVIF, Modbus, GPIO/JTAG, raw TCP/UDP, Unix sockets, and custom protocols.

Flow:

1. `list_guest_endpoints(session_id)`
2. `get_guest_endpoint(endpoint_id)`
3. `endpoint_client_context(endpoint_id)` to obtain environment variables and connection hints
4. use external tools directly, or `spawn_endpoint_client(endpoint_id, command, args?, cwd?, variables?)`

`spawn_endpoint_client` returns an `interactive_id`. Read its output with
`read_interactive_session(interactive_id, wait_seconds?, max_bytes?, output_mode?)`;
`output_mode` is a read option, not a spawn argument.

Before spawning, inspect `client_execution.can_spawn_from_neuromatrix`, `available_clients`, and `client_requirement`. These report executables available in the current provider runtime. `spawn_endpoint_client` runs an installed or uploaded client; it never installs one.

Backend helpers should register endpoints automatically:

- QEMU: serial, QMP, GDB, and user-network forwards
- Qiling: long-running service endpoint declarations
- Renode: UART, GDB, and peripheral metadata endpoints

Do not ask NeuroMatrix to implement protocol clients for HTTP/SSH/FTP/Telnet. The server exposes the endpoint; external tools perform protocol interaction.

Closing an endpoint reports whether its cleanup hook ran and succeeded; a failed cleanup retains the handle for inspection/retry. Treat a loopback endpoint according to its declared `scope`; provider-local loopback is not automatically host-reachable. Caller/backend `status`, address, and scope remain declarations unless `status_verified`/`reachability_verified` or a client probe records evidence.

## Endpoint evidence

- UART: connect and capture bytes, prompt, banner, or expected marker.
- HTTP/HTTPS/custom TCP: one external request/response through the advertised endpoint.
- GDB remote: handshake, stop packet, register read, or breakpoint evidence.
- QMP: `query-status` or another QMP response.
- GPIO/JTAG/custom metadata: observed peripheral path/range and the command or register operation that touched it.

