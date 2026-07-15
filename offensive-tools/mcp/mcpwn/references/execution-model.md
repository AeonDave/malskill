# MCPwn Execution Model

Three execution paths. Choosing wrong causes timeouts, orphaned processes, or lost output.

## Decision tree

| Situation | Use |
|-----------|-----|
| Needs stdin/tty mid-run (nc, ssh, gdb, REPL, penelope) | `start_interactive_shell` |
| Short, no stdin, <3 min | `execute_command(cmd)` |
| Long, no stdin, >3 min | `execute_command(cmd, detach=True)` |
| Catalog tool, fast (<30s) | `run_tool("name", {...})` |
| Catalog tool, slow (>30s) or `long_running=True` | `run_tool("name", {...}, detach=True)` |

## Short commands — `execute_command`

- Synchronous: the MCP request blocks until exit or timeout.
- Default timeout 180s; override `timeout=N`. Inline calls are clamped to `MCPWN_INLINE_TIMEOUT_CAP` (~120s) regardless of `timeout`, so raising it only matters together with `detach=True`.
- Known-long commands are **rejected synchronously** with `long_running_command`: `nmap -sV`/`-sC`/`-p-`, hydra, ffuf, feroxbuster, gobuster, sqlmap, hashcat, john, masscan, amass, nuclei, wpscan, nikto, kerbrute. Use `detach=True`.
- Output >64 KB auto-saves to a CAS artifact (`output_mode='auto'`), returning an id + preview — don't try to inline it.
- Use for: `whoami`, `cat`, `ls`, `id`, fast `curl`, short nmap, one-liners.

## Async jobs — `detach=True` + `poll_job`

- Returns `{job_id}` immediately. `poll_job(job_id, wait_seconds=30)` in a loop until `status == "done"`.
- `long_running=True` catalog tools (ffuf, feroxbuster, gobuster, hydra, john, hashcat, sqlmap, amass, zap_active_scan, nuclei_scan, mythril_analyze, volatility_analyze) **require** `detach=True`.
- `delete_job(job_id)`: for `execute_command` jobs → SIGKILL to the Kali process tree; for `run_tool` jobs → soft-cancel (the HTTP call may still finish). Jobs auto-expire after 2h.
- Do NOT tight-loop `poll_job` over a bare sleep. Offload a long timed wait into ONE detached job: `execute_command("until <cond>; do sleep 30; done", detach=True)` or `execute_command("sleep 2700; echo done", detach=True)` (detach bypasses the inline sleep limit), then poll every few minutes.

## Interactive shell

Lifecycle:
```
start_interactive_shell(session_id, command) → interactive_id
run_in_shell(interactive_id, cmd)             # discrete command → {output, exit_code}
read_shell_output(interactive_id, wait_seconds=30)  # streaming/TUI only, long-poll, repeat
signal_interactive_shell(interactive_id, "SIGINT")  # cancel a LOCAL tool (not a remote job)
close_shell(interactive_id) → log_path
```

- Runs with `cwd=workspace`. ANSI stripped, `\r` progress redraws collapsed, 256 KB buffer with disk overflow, output >64 KB → CAS.
- **`run_in_shell` over `send_to_shell`+`read_shell_output`**: it appends a unique completion marker with the exit code and reads exactly to it (posix/powershell/cmd autodetected) — no fragmented reads, no previous-command bleed (evil-winrm/CLM). Keep `read_shell_output` for streaming or full-screen TUI programs with no single command to bracket.
- `stabilize_shell(interactive_id)` upgrades a raw caught shell to a target-side PTY (python→script fallback) and fixes `TERM`.
- **Readline/TUI first prompt has no trailing newline** — `read_shell_output` returns empty until you act. Send a `\n` (`send_to_shell(id,"\n")`) to force a redraw, then read; loop `read_shell_output(wait_seconds=N)` for late frames. A blank read is *not* a dead process.
- **Don't hand-run a long-lived TUI daemon in an interactive shell** (e.g. `ligolo-proxy` stalls on its `Enable WebUI? [y/N]` prompt and never binds the listener until answered) — use the daemonized wrapper (`tunnel_up kind=proxy` for ligolo/chisel) so there's no prompt to babysit. If you must, answer the prompt with `send_to_shell` before expecting output.
- **A hang-prone command freezes the whole interactive session** until it returns (`showmount`, `getent` on SSSD, `nfs-cp`/curl over a dead tunnel, a nc to a closed port). Wrap remote work as `timeout N cmd` or `cmd >/tmp/o 2>&1; cat /tmp/o` so the channel never blocks. If a *local* tool hangs, `signal_interactive_shell(SIGINT)` cancels it (safe for gdb/REPL/scanner; NOT for an nc/penelope listener — SIGINT there drops the shell).
- Verbose scan wrappers (`feroxbuster_scan`/`ffuf_scan`/`nuclei_scan`/`katana_crawl`) default to `view="summary"` (compact digest + CAS pointer); pass `view="full"` to inline everything.
- Use for: nc, ssh, gdb, python REPL, penelope, anything needing stdin.

## Container gotchas that cause fake failures

- **Shell**: `execute_command` = `sh -c` — the base image decides the interpreter (dash on a Debian base, bash on Kali). Bashisms (`$RANDOM`, arrays, `<()`) silently degrade under dash, so wrap `bash -c '<cmd>'` when you rely on them (don't assume the base).
- **Interactive has no shell**: `start_interactive_shell` execs directly (pexpect). `cd x && cmd` fails; pipes/globs/`$VARS` don't expand. Use `cwd=` (relative = inside workspace) or wrap `bash -lc '<cmd>'`.
- **Inline sleep**: `sleep N` >60s (incl. `sleep 90; cmd`) is auto-rejected → detached job.
- **pty-only listeners**: `penelope`/`pwncat`/`pwncat-cs` need a controlling TTY — run them via `start_interactive_shell`. Through `execute_command` they're auto-guarded: you get `guard: pty_only_listener` + an `nc` `fallback_command` (not a crash/hang), signalling *relaunch under an interactive shell*.
- **Inline backgrounding**: a bare `cmd &` under `execute_command` is SIGKILLed when the call returns. Persist a listener/`http.server`/watcher with `setsid cmd &`, `nohup cmd &`, or `detach=True`. Anything that can hang → `detach=True` or prefix `timeout N` (a stall burns the whole ~60s transport window).
- **/etc/hosts**: Docker bind mount — `sed -i` fails EBUSY; use `sudo tee -a /etc/hosts`.
- **Python**: runtime venv is `/opt/venv-core`; system `python3` is PEP-668 managed. Install with `/opt/venv-core/bin/pip install <pkg>`.
- **Kerberos skew**: `run_tool("krb_time_probe", {...})` reads the DC clock and emits a `faketime -f +Ns` wrapper on >5 min skew.
- **No NFS kernel client**: the container has no `nfs` in `/proc/filesystems` and no `CAP_SYS_ADMIN` — `mount -t nfs` fails `Operation not permitted`/`Protocol not supported`. Use the **`nfs_enum`** catalog tool (`get_tools(domain="network", query="nfs")`) — it wraps the userspace libnfs clients: `action=showmount|ls|cat`, with `uid`/`gid` to spoof AUTH_UNIX and beat `root_squash` (root→nobody, other ids pass through; set `gid` to a `0770` dir's group to read it). Or raw: `nfs-ls`/`nfs-cp` on `nfs://host/export?version=3&uid=X&gid=Y`. Reach an internal 2049 through a `tunnel_up` pivot first.
