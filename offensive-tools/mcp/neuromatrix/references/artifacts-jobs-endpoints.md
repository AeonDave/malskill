# NeuroMatrix Artifacts, Jobs, and Endpoints

Use this reference when moving files, running long jobs, or talking to guest-exposed services/debug channels.

## Artifact upload

For existing local files, do not inline base64 through MCP.

1. Compute size and SHA-256 locally.
2. `request_upload(filename, file_size_bytes, checksum_sha256, session_id?, mime_type?)`
3. PUT raw bytes to the returned URL:
   `curl -sS -X PUT --data-binary @artifact.bin "<upload_url>" -o /dev/null -w "%{http_code}\n"`
4. Use the returned `artifact_id` or `mcp://artifacts/<sha256>`.
5. If a tool needs a mutable server path, call `import_artifact_to_workspace(session_id, artifact_id, executable?)`.

Analyze before routing:

```json
{"tool":"analyze_artifact","arguments":{"artifact_id":"mcp://artifacts/<sha256>"}}
```

Use `extract_artifact_subartifact` for byte ranges/gzip members and `extract_artifact_filesystem` for supported filesystem extraction. Filesystem extraction is long-running: detach it.

## Artifact download

- `request_download(artifact_id, filename?)` returns an expiring HTTP GET URL.
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

## Detached jobs

Long-running catalog tools must be called with `detach=true`.

```json
{"tool":"run_tool","arguments":{"name":"qemu_linux_start","arguments":{"session_id":"k1","kernel":"mcp://artifacts/<sha256>"},"detach":true}}
{"tool":"poll_job","arguments":{"job_id":"job-...","wait_seconds":30}}
```

Use `list_jobs` after a context reset. Use `delete_job` for cancellation or cleanup; if a backend has a native process handle, NeuroMatrix should attempt a hard kill.

Do not tight-loop `poll_job`. Long-poll with bounded waits and report the latest job state.

## Interactive sessions

Use `start_interactive_session` for a long-lived server-side process in the session workspace, not for guest UART/GDB/QMP endpoints unless that endpoint client itself is a process you want to drive.

Lifecycle:

```json
{"tool":"start_interactive_session","arguments":{"session_id":"s1","command":"bash","args":["-lc","python3 client.py"],"cwd":"."}}
{"tool":"read_interactive_session","arguments":{"interactive_id":"int-...","wait_seconds":5,"output_mode":"auto"}}
{"tool":"send_interactive_input","arguments":{"interactive_id":"int-...","input":"status","append_newline":true}}
{"tool":"close_interactive_session","arguments":{"interactive_id":"int-..."}}
```

`output_mode="auto"` should keep large output out of the MCP channel and return artifact metadata.

## Guest endpoints

Backends register endpoint metadata for UART, GDB remote, QMP, HTTP/HTTPS, SSH/FTP/Telnet, RTSP/ONVIF, Modbus, GPIO/JTAG, raw TCP/UDP, Unix sockets, and custom protocols.

Flow:

1. `list_guest_endpoints(session_id)`
2. `get_guest_endpoint(endpoint_id)`
3. `endpoint_client_context(endpoint_id)` to obtain environment variables and connection hints
4. use external tools directly, or `spawn_endpoint_client(endpoint_id, command, args?, cwd?, output_mode?)`

Backend helpers should register endpoints automatically:

- QEMU: serial, QMP, GDB, and user-network forwards
- Qiling: long-running service endpoint declarations
- Renode: UART, GDB, and peripheral metadata endpoints

Do not ask NeuroMatrix to implement protocol clients for HTTP/SSH/FTP/Telnet. The server exposes the endpoint; external tools perform protocol interaction.

## Endpoint evidence

- UART: connect and capture bytes, prompt, banner, or expected marker.
- HTTP/HTTPS/custom TCP: one external request/response through the advertised endpoint.
- GDB remote: handshake, stop packet, register read, or breakpoint evidence.
- QMP: `query-status` or another QMP response.
- GPIO/JTAG/custom metadata: observed peripheral path/range and the command or register operation that touched it.

