---
name: mcpwn
description: "Drive the MCPwn Kali-backed MCP server cleanly and fast: create a session, discover tools via the catalog (list_catalog/get_tools/get_tool/run_tool) instead of guessing names, pick the right execution path (execute_command vs detach+poll_job vs interactive shell), move files with the correct mechanism (write_workspace_file, request_upload/request_download data plane, import_artifact_to_workspace, upload_to_target, list_payloads/get_payload), and bring up connectivity (tunnel_up VPN/proxy/forward, tunnel_revshell, penelope reverse shells, run_in_shell/stabilize_shell). Use whenever running MCPwn / mcpwn_* tools, a Kali MCP, or when a run stalls on timeouts, lost output, missing routes, wrong tool names, or clumsy file transfer."
---

# MCPwn Operator

MCPwn is a Linux-container-backed MCP server (Kali or Debian base — same tools/functions, only the base image differs): **passwordless root** (the container user has `sudo NOPASSWD:ALL` — prefix `sudo` freely, edit root-owned files in place), ~200 security tools behind a catalog, a container workspace, a CAS artifact plane (`:5001`), tunnels, and reverse-shell handling. Use it well by choosing the right execution path, discovering tools instead of guessing, and moving files with the correct mechanism. Wrong choices cause timeouts, lost output, orphaned processes, and wasted turns.

**Network sharing is host-OS-dependent:** only a **Linux host** shares its network with the container (`network_mode: host`) — local listeners and the host's `tun0` are directly reachable. On **Windows/macOS** (Docker Desktop) the container is NAT'd, so a listener isn't reachable from the LAN/VPN unless you bring a VPN up *inside* the container (`tunnel_up kind=vpn` → routable `tun0`) or publish via a relay (`reach=public`). Don't assume host reachability off Linux.

**Host routing — mcpwn vs a local Linux (don't burn turns on the wrong host).** mcpwn's edge is the ~200-tool arsenal, connectivity/pivoting, remote targets, and the pre-staged `/opt/*-payloads`. It is **not** the best host for a *local* binary/CTF artifact that must run against a **specific provided libc/loader** while you iterate in gdb: you'd have to push binary+libc+ld into the container (each ≥64 KB file needs the `:5001` PUT, a client-side step the agent can't do inline), and the container's libc **won't match** the challenge's, so every gdb/offset loop pays a transfer + mismatch tax. When a local Linux (WSL/native) already has the artifacts mounted and `gdb`+`pwntools`, drive the whole reverse/exploit-dev loop there; reach into mcpwn's `pwn` domain only when you lack a local Linux, want its bundled pwn tooling (`ROPgadget`/`one_gadget`/pwntools/gdb) without installing, or need to interact with the **remote** service. Decide the host once, up front — a brief catalog peek then a pivot is fine, but don't half-run the loop on both.

## The Loop

1. **Session first.** `create_analysis_session()` → keep `session_id` + `workspace`. Reuse it for the whole task. Lost it after a context reset? `list_sessions()` / `list_interactive_sessions()` to rediscover, don't spawn a duplicate.
2. **Discover, never guess.** `list_catalog()` → `get_tools(domain=..., query=...)` → `get_tool("name")` to read args → `run_tool("name", {...})`. Tool names are hidden until discovered; guessing wastes turns.
3. **Execute on the right path** (see decision table below).
4. **Collect** results; large output lands as a CAS artifact — read the digest, not the whole blob.
5. **Cleanup** when done: `close_shell`, `delete_job`, `delete_session`.

## Execution path — pick correctly (top time-sink)

| Situation | Path |
|-----------|------|
| Short, no stdin, <~3 min (`whoami`, `cat`, `id`, quick `curl`/nmap) | `execute_command(cmd)` |
| Long one-shot, no stdin (`nmap -p-`, hashcat, ffuf, sqlmap, hydra, feroxbuster) | `execute_command(cmd, detach=True)` → `poll_job(job_id, wait_seconds=30)` loop |
| Catalog tool, fast (<30s) | `run_tool("name", {...})` |
| Catalog tool, slow / tagged `long_running` | `run_tool("name", {...}, detach=True)` → `poll_job` |
| Needs stdin/tty or live streaming (nc, ssh, gdb, REPL, penelope) | `start_interactive_shell` → `run_in_shell`/`read_shell_output` → `close_shell` |

Known-long commands are **rejected synchronously** on `execute_command` — use `detach=True`. Never send `nmap -p-`, brute-force, hashcat, or ffuf inline. Full rules, sleep/backgrounding traps, and the interactive lifecycle: load `references/execution-model.md`.

## Moving files — use the right mechanism

| Goal | Mechanism |
|------|-----------|
| Small text/config INTO workspace (<64 KB) | `write_workspace_file` (base64 for binary; auto-creates parent dirs) |
| Read/patch a workspace file | `read_workspace_file` / `patch_workspace_file` (no shell, no size cap, atomic) |
| Large/binary file (≥64 KB) INTO the server | `request_upload` → `curl -X PUT --data-binary @f` the raw bytes to the `:5001` URL **from your own local shell** → `import_artifact_to_workspace`. Don't base64-chunk (burns context); import only *after* the 201. |
| Pull a result OUT | `request_download` → `curl` the tokenized `:5001` GET URL from your local shell |
| CAS artifact → mutable workspace (needed by GDB/pwntools/patch tools) | `import_artifact_to_workspace` |
| Inspect an artifact without transferring | `analyze_artifact` (preview) / `list_artifacts` |
| Read-only analyzers | pass the CAS ref directly: `mcp://artifacts/<sha256>` |
| Ship a payload TO a target host | `list_payloads` → `get_payload` → `upload_to_target` (smb/scp/ftp/http, PtH-aware) |

Details, the pre-staged `/opt/*-payloads` depots, and the sub-agent CAS-handoff rule: `references/files-and-artifacts.md`.

## Connectivity & reverse shells (bring reachability up FIRST)

A missing route fakes an all-filtered scan — establish and verify the path before enumerating.

- Route/pivot/VPN/LHOST → `get_tools(domain="network")` then `tunnel_up` (`kind` = `vpn`/`expose`/`proxy`/`forward`) and `tunnel_revshell` (cross-OS LHOST:LPORT + ready payloads).
- VPN by artifact: `run_tool("tunnel_up", {"kind":"vpn","config_ref":"mcp://artifacts/<sha>"})` → `iface=tun0` + IP.
- Catch shells with **penelope** (default), not raw `nc`: auto PTY upgrade + on-disk transcript. penelope/pwncat are **pty-only** — launch them via `start_interactive_shell` (pexpect gives them a TTY); fired through `execute_command` they're now guarded (you get `guard: pty_only_listener` + an `nc` `fallback_command`, not a crash — treat it as a signal to relaunch interactively). After catching, `stabilize_shell` (shell-aware — auto-skips the Linux PTY upgrade on a Windows shell); run discrete commands with `run_in_shell` (returns scoped output + exit_code — no fragmented reads). Never SIGINT the listener to stop a remote job (it drops the shell).
- **Windows / AD / Kerberos:** a raw Windows callback has no Unix PTY — drive it with `run_in_shell` (cmd/powershell autodetected), then pivot to **evil-winrm** for a clean PTY (creds / `-H <nthash>` PtH / `-r <REALM>` Kerberos). Kerberos needs the DC FQDN **and** REALM in `/etc/hosts` + no clock skew (`krb_time_probe` → `faketime`, `impacket-getTGT` → `KRB5CCNAME`). Full flow: `references/tunnels-and-shells.md`.

Tunnel kinds, cross-OS reach logic, Windows/AD shell pivots, and raw-channel survival patterns: `references/tunnels-and-shells.md`.

## Catalog domains

15 domains for `get_tools(domain=...)`: `network`, `web`, `pwn`, `crypto`, `forensics`, `pcap`, `mobile`, `cloud`, `web3`, `ics`, `osint`, `llm`, `ml`, `runtime`, `sessions`. Search is tag/alias-aware — query by intent (`rdp`, `smb`, `jwt`, `rop`, `pivot`, `disk image`, `factordb`) not exact tool names.

## Strict rules

- One session per task; discover before running; read `get_tool` args before first use of any wrapper.
- Long/known-slow work → `detach=True` + `poll_job`, or an interactive shell. Never inline.
- Don't hand-read large outputs. Auto-CAS only triggers at ~64 KB, so **bulky sub-64 KB dumps** (a few hundred lines) still print inline and silently burn context when you loop them — the classic tax on iterative analysis of a big read-only artifact (mmap-carving a memory dump, sifting a PCAP/disk image via heredoc scripts). Fix: write results to a workspace file and `grep`/`head` only the slice you need, or force a handoff with `execute_command(..., output_mode="artifact", output_filename="...")`. Extract the few lines that matter; never reprint the whole set each turn. For a long carving/sift loop, quarantine it in a sub-agent that returns a digest.
- `execute_command` is `sh -c` (dash on a Debian base, bash on Kali) — wrap bashisms in `bash -c '...'` so they don't silently degrade. `start_interactive_shell` has no shell — use `cwd=` (no `cd &&`) or `bash -lc`.
- `/etc/hosts` is a bind mount — append with `sudo tee -a`, not `sed -i`.
- Sub-agents don't inherit the MCP client — hand off state as `mcp://artifacts/<sha>`.
- Cleanup: close shells, delete finished jobs, delete the session.

## Resources

### references/

- `references/execution-model.md` — load when a command times out, output is lost/fragmented, a process orphans, or you need the sleep/backgrounding/interactive-shell rules and the short-vs-async-vs-interactive decision in full.
- `references/files-and-artifacts.md` — load for any non-trivial file movement: the `:5001` upload/download handoff, workspace vs CAS vs import, the `/opt` payload depots, `upload_to_target` (incl. pass-the-hash), and the sub-agent handoff pattern.
- `references/tunnels-and-shells.md` — load when establishing connectivity or catching a shell: `tunnel_up` kinds and params, `tunnel_revshell` cross-OS reach, penelope/`stabilize_shell`/`run_in_shell`, and raw nc/socat survival tradecraft.
