---
name: mcpwn
description: "Operate the MCPwn Kali/Debian MCP efficiently: manage sessions, discover catalog tools, choose synchronous, detached, or interactive execution, move files through workspace/CAS planes, establish tunnels and shells, and run GDB or Frida debugging in the MCPwn runtime or through explicit host/device transports. Use for MCPwn or Kali MCP work, pwn/CTF and dynamic-analysis sessions, remote targets, connectivity or file-transfer problems, and optional NeuroMatrix-backed emulation/debugging through MCPwn's emulation domain."
---

# MCPwn Operator

MCPwn is a Linux-container-backed MCP server (Kali or Debian base — the MCP/catalog contract is the same, while installed runtime tools differ and genuinely heavy tools remain Kali-only): a non-root runtime user with `sudo NOPASSWD:ALL`, ~200 security tools behind a catalog, a container workspace, a CAS artifact plane (`:5001`), tunnels, and reverse-shell handling. Prefix root-only operations with `sudo`. Use the right execution path, discover tools instead of guessing, and move files with the correct mechanism; wrong choices cause timeouts, lost output, orphaned processes, and wasted turns.

**Network sharing is host-OS-dependent:** only a **Linux host** shares its network with the container (`network_mode: host`) — local listeners and the host's `tun0` are directly reachable. On **Windows/macOS** (Docker Desktop) the container is NAT'd, so a listener isn't reachable from the LAN/VPN unless you bring a VPN up *inside* the container (`tunnel_up kind=vpn` → routable `tun0`) or publish via a relay (`reach=public`). Don't assume host reachability off Linux.

**Choose the debugger locus before attaching.** `local` means the process namespace where MCPwn's API runs; in the standard Docker deployment that is the container, not the Windows/macOS host. Separate hosts require an explicit debugger server/transport, while NeuroMatrix is only needed for emulation. Keep a challenge's matching binary, loader, and libc together in the selected runtime.

## The Loop

1. **Session first.** `create_analysis_session()` → keep `session_id` + `workspace`. Reuse it for the whole task. Lost it after a context reset? `list_sessions()` / `list_interactive_sessions()` to rediscover, don't spawn a duplicate.
2. **Discover, never guess.** The **infra tools are always direct** — call them with no discovery: session (`create_analysis_session`/`list_sessions`/`delete_session`), artifacts (`request_upload`/`request_download`/`list_artifacts`/`analyze_artifact`/`import_artifact_to_workspace`), workspace (`write_workspace_file`/`read_workspace_file`/`patch_workspace_file`), storage (`storage_usage`/`prune_*`), execution (`execute_command`), interactive (`start_interactive_shell`/`send_to_shell`/`read_shell_output`/`run_in_shell`/`stabilize_shell`/`close_shell`/`list_interactive_sessions`/`signal_interactive_shell`). Only **DOMAIN** tools (network/web/pwn/…) need discovery: `list_catalog()` → `get_tools(domain=..., query=...)` → `get_tool("name")` (read args) → `run_tool("name", {...})`. Catalog names are hidden until discovered; guessing them wastes turns — but never `list_catalog` to "find" an infra tool.
3. **Execute on the right path** (see decision table below).
4. **Collect** results; large output lands as a CAS artifact — read the digest, not the whole blob.
5. **Cleanup** when done: `close_shell`, `delete_job`, `delete_session`.

## Debugging and optional emulation

MCPwn runs GDB and Frida without NeuroMatrix. It can also map its `emulation` domain onto a standalone, client-neutral NeuroMatrix server when emulation is required.

Load [references/debugging-and-emulation.md](references/debugging-and-emulation.md) before attaching to a host process, choosing GDB versus Frida, or composing MCPwn with NeuroMatrix.

## Execution path — pick correctly (top time-sink)

| Situation | Path |
|-----------|------|
| Short, no stdin, <~3 min (`whoami`, `cat`, `id`, quick `curl`/nmap) | `execute_command(cmd)` |
| Long one-shot, no stdin (`nmap -p-`, hashcat, ffuf, sqlmap, hydra, feroxbuster) | `execute_command(cmd, detach=True)` → `poll_job(job_id, wait_seconds=30)` loop |
| Catalog tool, fast (<30s) | `run_tool("name", {...})` |
| Catalog tool, slow / tagged `long_running` | `run_tool("name", {...}, detach=True)` → `poll_job` |
| Needs stdin/tty or live streaming (nc, ssh, gdb, REPL, penelope) | `start_interactive_shell` → `run_in_shell`/`read_shell_output` → `close_shell` |

Known-long commands are **rejected synchronously** on `execute_command` — use `detach=True`. Never send `nmap -p-`, brute-force, hashcat, or ffuf inline.

**The detached contract, because it decides what you can run at all:** `execute_command(cmd, detach=True)` with no `timeout` has **no deadline** — it runs to completion — and stays interruptible, because `delete_job` SIGKILLs its owned process tree and verifies the kill. That is the path for *any* program MCPwn does not wrap, however long it runs. Inline is the opposite by design: a base timeout clamped to `MCPWN_INLINE_TIMEOUT_CAP` (~120s) so an abandoned call can't strand a process. A detached **catalog** tool is the middle case — bounded by its own route ceiling and only *cooperatively* cancellable (no kill hook), so when a scan must outlive that ceiling, drive the binary through `execute_command(detach=True)` instead.

**Interactive shells: prefer `run_in_shell(id, cmd)` for a discrete command.** It is marker-synced — returns THAT command's output + `exit_code` in ONE call (autodetects posix/powershell/cmd) — so no guess-the-timing `send_to_shell`+`read_shell_output` loop and no command-echo / job-control noise bleeding into the read. Keep `read_shell_output(wait_seconds=N)` for streaming / TUI / a shell you must watch live; `wait_seconds` is server-clamped to ~20s, so **loop it** for longer waits rather than expecting one 60s block. Full rules, sleep/backgrounding traps, and the interactive lifecycle: load `references/execution-model.md`.

## Moving files — use the right mechanism

| Goal | Mechanism |
|------|-----------|
| Text you AUTHOR in-context (script/config/exploit) | `write_workspace_file(content_text=...)` — 1 call, already in context, no corruption risk; auto-creates parent dirs |
| Read/patch a workspace file | `read_workspace_file` / `patch_workspace_file` (no shell; reads are bounded and paginatable; patches are atomic) |
| A file that ALREADY EXISTS on disk (any size, binary or text) | `request_upload` → `curl -X PUT --data-binary @f` the raw bytes to the `:5001` URL **from your own local shell** → `import_artifact_to_workspace` (only *after* the 201; skip import if a CAS ref is enough). |
| Small binary blob generated in-context, not on disk | `write_workspace_file(content_base64=..., sha256=<digest>)` — last resort |
| Pull a result OUT | `request_download` → `curl` the tokenized `:5001` GET URL from your local shell |
| CAS artifact → mutable workspace (needed by GDB/pwntools/patch tools) | `import_artifact_to_workspace` |
| Inspect an artifact without transferring | `analyze_artifact` (preview) / `list_artifacts` |
| Read-only analyzers | pass the CAS ref directly: `mcp://artifacts/<sha256>` |
| Ship a payload TO a target host | `list_payloads` → `get_payload` → `upload_to_target` (smb/scp/ftp/http, PtH-aware) |

**Decide by source/type, not size.** **NEVER `base64 -w0` a file that exists on disk into `write_workspace_file`** — it streams the bytes through model context (token cost ∝ file size) and one flipped char stays valid base64 = silent corruption (decoded bytes differ from source with no error; downstream PKI/binary consumers reject the result). The `:5001` PUT has **no minimum size** and is SHA-addressed — default for any on-disk file. If you must send `content_base64`, pass `sha256=` (server refuses on mismatch).

Details, the pre-staged `/opt/*-payloads` depots, and the sub-agent CAS-handoff rule: `references/files-and-artifacts.md`.

## Connectivity & reverse shells (bring reachability up FIRST)

A missing route fakes an all-filtered scan — establish and verify the path before enumerating.

- Route/pivot/VPN/LHOST → `get_tools(domain="network")` then `tunnel_up` (`kind` = `vpn`/`expose`/`proxy`/`forward`) and `tunnel_revshell` (cross-OS LHOST:LPORT + ready payloads).
- VPN by artifact: `run_tool("tunnel_up", {"kind":"vpn","config_ref":"mcp://artifacts/<sha>"})` → `iface=tun0` + IP.
- Catch shells with **penelope** (default), not raw `nc`: auto PTY upgrade + on-disk transcript. penelope/pwncat are **pty-only** — launch them via `start_interactive_shell` (pexpect gives them a TTY); fired through `execute_command` they're now guarded (you get `guard: pty_only_listener` + an `nc` `fallback_command`, not a crash — treat it as a signal to relaunch interactively). After catching, `stabilize_shell` (shell-aware — auto-skips the Linux PTY upgrade on a Windows shell); run discrete commands with `run_in_shell` (returns scoped output + exit_code — no fragmented reads). Never SIGINT the listener to stop a remote job (it drops the shell).
- **Windows / AD / Kerberos:** a raw Windows callback has no Unix PTY — drive it with `run_in_shell` (cmd/powershell autodetected), then pivot to **evil-winrm** for a clean PTY (creds / `-H <nthash>` PtH / `-r <REALM>` Kerberos). Kerberos needs the DC FQDN **and** REALM in `/etc/hosts` + no clock skew (`krb_time_probe` → `faketime`, `impacket-getTGT` → `KRB5CCNAME`). Full flow: `references/tunnels-and-shells.md`.

Tunnel kinds, cross-OS reach logic, Windows/AD shell pivots, and raw-channel survival patterns: `references/tunnels-and-shells.md`.

## Catalog domains

16 domains for `get_tools(domain=...)`: `network`, `web`, `pwn`, `crypto`, `forensics`, `pcap`, `mobile`, `cloud`, `web3`, `ics`, `osint`, `llm`, `ml`, `runtime`, `sessions`, `emulation`. Search is tag/alias-aware — query by intent (`rdp`, `smb`, `jwt`, `rop`, `pivot`, `disk image`, `factordb`, `neuromatrix`) not exact tool names.

## Strict rules

- One session per task; discover before running; read `get_tool` args before first use of any wrapper.
- Long/known-slow work → `detach=True` + `poll_job`, or an interactive shell. Never inline.
- Don't hand-read large outputs. Auto-CAS only triggers at ~64 KB, so **bulky sub-64 KB dumps** (a few hundred lines) still print inline and silently burn context when you loop them — the classic tax on iterative analysis of a big read-only artifact (mmap-carving a memory dump, sifting a PCAP/disk image via heredoc scripts). Fix: write results to a workspace file and `grep`/`head` only the slice you need, or force a handoff with `execute_command(..., output_mode="artifact", output_filename="...")`. Extract the few lines that matter; never reprint the whole set each turn. For a long carving/sift loop, quarantine it in a sub-agent that returns a digest.
- `execute_command` is `sh -c` (dash on a Debian base, bash on Kali) — wrap bashisms in `bash -c '...'` so they don't silently degrade. `start_interactive_shell` has no shell — use `cwd=` (no `cd &&`) or `bash -lc`.
- `/etc/hosts` is a bind mount — append with `sudo tee -a`, not `sed -i`.
- Sub-agents don't inherit the MCP client — hand off state as `mcp://artifacts/<sha>`.
- **Server readiness and profile ports:** proxy profiles expose MCP `/health` on their published MCP port (normally `:5000`; Debian/macOS defaults to `:5002`) and artifact `/health` on the published artifact port (normally `:5001`). The Kali/macOS dev profile publishes FastMCP directly on host `:5000` -> container `:8080`, so it has no proxy `/health`; validate it with an MCP `initialize` or `create_analysis_session`, and probe artifact health separately. `:8081/mcp` is an optional direct FastMCP diagnostic endpoint on the proxy profiles and must be tested with MCP `initialize`, not `GET /health`.
- Cleanup: close shells, delete finished jobs, delete the session.

## Resources

### references/

- `references/execution-model.md` — load when a command times out, output is lost/fragmented, a process orphans, or you need the sleep/backgrounding/interactive-shell rules and the short-vs-async-vs-interactive decision in full.
- `references/files-and-artifacts.md` — load for any non-trivial file movement: the `:5001` upload/download handoff, workspace vs CAS vs import, the `/opt` payload depots, `upload_to_target` (incl. pass-the-hash), and the sub-agent handoff pattern.
- `references/tunnels-and-shells.md` — load when establishing connectivity or catching a shell: `tunnel_up` kinds and params, `tunnel_revshell` cross-OS reach, penelope/`stabilize_shell`/`run_in_shell`, and raw nc/socat survival tradecraft.
- `references/debugging-and-emulation.md` — load for GDB/Frida sessions, container-versus-host reachability, debugger-server transports, Frida loader-crash triage, or the optional MCPwn-to-NeuroMatrix emulation bridge.
