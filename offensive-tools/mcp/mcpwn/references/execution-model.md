# MCPwn Execution Model

Three execution paths. Choosing wrong causes timeouts, orphaned processes, or lost output.

## Decision tree

| Situation | Use |
|-----------|-----|
| Needs stdin/tty mid-run (nc, ssh, gdb, REPL, penelope) | `start_interactive_shell` |
| Expected well below 20s, no stdin | `execute_command(cmd)` |
| Long or duration-uncertain, no stdin | `execute_command(cmd, detach=True)` |
| Catalog tool expected well below 20s | `run_tool("name", {...})` |
| Slow, uncertain, or `long_running=True` tool | `run_tool("name", {...}, detach=True)` |

## Short commands — `execute_command`

- Synchronous: the MCP request blocks until exit or timeout.
- Inline execution is capped at 20s by default. `MCPWN_INLINE_TIMEOUT_CAP` may lower it to a 5s minimum but cannot raise it; a lower `MCPWN_MAX_LONG_POLL_SECONDS` also lowers it. Process cleanup can add bounded time after the execution timeout, so use `detach=True` near the ceiling. Detached calls have no deadline unless you pass `timeout=N`.
- **This ceiling was 120s through v1.3.0 and became 20s in v1.3.1** — a behavioural break the MCP schema cannot express, so an inline call in the 21-120s band just starts timing out. The reason is real: a client that serializes requests to one server turns a 32s inline call into a 32s stall of every other tool, which looks like a disconnection. Move that work to `execute_command(..., detach=True)` + `poll_job(...)`. If your client issues concurrent requests and tolerates a wider request timeout, the operator can set `MCPWN_ALLOW_LONG_INLINE=1` on the server to restore the 120s default (and then raise it further with `MCPWN_INLINE_TIMEOUT_CAP`).
- Some MCP clients serialize calls to one server. An inline command delays unrelated session/catalog calls on those clients, so detach anything duration-uncertain or near the ceiling.
- Known-long commands are **rejected synchronously** with `long_running_command`: `nmap -sV`/`-sC`/`-p-`, hydra, ffuf, feroxbuster, gobuster, sqlmap, hashcat, john, masscan, amass, nuclei, wpscan, nikto, kerbrute, katana. Use `detach=True`.
- Output >64 KB auto-saves to a CAS artifact (`output_mode='auto'`), returning an id + preview — don't try to inline it.
- `timed_out=true` is authoritative and means execution was incomplete; current MCPwn results set `success=false` on timeout while `partial_results` may still preserve useful output. Inspect `timed_out`, `return_code`, and `partial_results` before accepting a result.
- Use for: `whoami`, `cat`, `ls`, `id`, fast `curl`, short nmap, one-liners.

## Async jobs — `detach=True` + `poll_job`

- Returns `{job_id}` immediately. `poll_job(job_id, wait_seconds=30)` in a loop until `status == "done"`.
- `long_running=True` catalog tools (including `analyze_with_radare2`, `decompile_with_radare2`, ffuf, feroxbuster, gobuster, hydra, john, hashcat, sqlmap, amass, zap_active_scan, nuclei_scan, katana_crawl, mythril_analyze, and volatility_analyze) **require** `detach=True`.

### Duration-uncertain catalog wrappers

- Treat deep decompilation, global analysis, and any wrapper with uncertain duration as asynchronous: dispatch with `detach=True`, poll at bounded intervals, and keep concurrent heavy jobs limited so the backend is not saturated.
- A caller/MCP request timeout can end the caller's wait without cancelling the backend job. Re-query job and cancellation state before retrying; when cancellation is needed, use `delete_job` and verify that the job reaches a terminal state.
- If polling reports an unhealthy or unavailable backend, report that condition and stop. Do not restart or rebuild MCPwn/the backend without user direction.

### The two detached paths behave differently — this matters

| | `execute_command(cmd, detach=True)` | `run_tool(name, {...}, detach=True)` |
|---|---|---|
| Timeout with no explicit value | **none — runs until it finishes** | the tool's own ceiling still applies |
| Stopping it | **hard kill**: `delete_job` SIGKILLs the owned process tree and verifies it | cooperative only — no kill hook |
| Backstop | job reaper hard-kills unfinished jobs at 4h | same reaper, but a live HTTP worker is not interrupted |

- So **anything arbitrary and open-ended belongs on `execute_command(detach=True)`**: no deadline unless you set `timeout=N`, and it is genuinely interruptible on demand. This is the path for a tool MCPwn does not wrap at all.
- A detached **catalog** tool is still bounded by its route ceiling (`long_running` scanners now allow up to an hour via `MCPWN_LONG_SCAN_TIMEOUT_CAP`; pass `timeout=N` to ask for more than the default). If you need a scan to run past that, drive the binary through `execute_command(detach=True)` instead.
- `delete_job(job_id)` requests cancellation and removes the record only after stop is observed. For `execute_command` jobs it invokes the hard process-tree kill. A catalog job without a kill hook may return `cancellation_pending=true`, `execution_stopped=false`, and `record_deleted=false`; poll it and retry deletion after it becomes terminal. Do not treat `ok=true` as proof that a pending worker vanished.
- Do NOT tight-loop `poll_job` over a bare sleep. Offload a long timed wait into ONE detached job: `execute_command("until test -f /tmp/ready; do sleep 30; done", detach=True)` or `execute_command("sleep 2700; echo done", detach=True)`, then poll every few minutes. No `timeout` is needed — a detached run has no deadline of its own.

## Interactive shell

Lifecycle:
```
start_interactive_shell(session_id, command) → interactive_id + pid
run_in_shell(interactive_id, cmd)             # discrete command → {output, exit_code}
read_shell_output(interactive_id, wait_seconds=30)  # streaming/TUI only, long-poll, repeat
signal_interactive_shell(interactive_id, "SIGINT")  # cancel a LOCAL tool (not a remote job)
close_shell(interactive_id) → log_path
```

- Runs with `cwd=workspace`. ANSI stripped, `\r` progress redraws collapsed, 256 KB buffer with disk overflow, output >64 KB → CAS.
- **`run_in_shell` over `send_to_shell`+`read_shell_output`**: it appends a unique completion marker with the exit code and reads exactly to it (posix/powershell/cmd autodetected) — no fragmented reads, no previous-command bleed (evil-winrm/CLM). Keep `read_shell_output` for streaming or full-screen TUI programs with no single command to bracket.
- `stabilize_shell(interactive_id)` upgrades a raw caught shell to a target-side PTY (python→script fallback) and fixes `TERM`.
- **Readline/TUI first prompt has no trailing newline** — `read_shell_output` returns empty until you act. Send a `\n` (`send_to_shell(id,"\n")`) to force a redraw, then read; loop `read_shell_output(wait_seconds=N)` for late frames. A blank read is *not* a dead process.
- **Don't hand-run a long-lived TUI daemon in an interactive shell** — use the daemonized wrapper (`tunnel_up kind=proxy` for chisel) so there's no prompt to babysit. If you must, answer the prompt with `send_to_shell` before expecting output.
- **A hang-prone command freezes the whole interactive session** until it returns (`showmount`, `getent` on SSSD, `nfs-cp`/curl over a dead tunnel, a nc to a closed port). Wrap remote work as `timeout N cmd` or `cmd >/tmp/o 2>&1; cat /tmp/o` so the channel never blocks. If a *local* tool hangs, `signal_interactive_shell(SIGINT)` cancels it (safe for gdb/REPL/scanner; NOT for an nc/penelope listener — SIGINT there drops the shell).
- Verbose scan wrappers (`feroxbuster_scan`/`ffuf_scan`/`nuclei_scan`/`katana_crawl`) default to `view="summary"` (compact digest + CAS pointer); pass `view="full"` to inline everything.
- Use for: nc, ssh, gdb, python REPL, penelope, anything needing stdin.

## Container gotchas that cause fake failures

- **Shell**: `execute_command` = `sh -c` — the base image decides the interpreter (dash on a Debian base, bash on Kali). Bashisms (`$RANDOM`, arrays, `<()`) silently degrade under dash, so wrap `bash -c '<cmd>'` when you rely on them (don't assume the base).
- **Interactive has no shell**: `start_interactive_shell` execs directly (pexpect). `cd x && cmd` fails; pipes/globs/`$VARS`/**redirections don't expand** — a trailing `2>&1` or `>file` is passed as literal argv, so the target program dies with a confusing `error: unrecognized arguments: 2>&1` (seen with ntlmrelayx/impacket). Use `cwd=` (relative = inside workspace) or wrap `bash -lc '<cmd>'` whenever you need any shell metacharacter.
- **Inline sleep**: a declared wait at or above the inline cap (`sleep 20` by default, including compound forms) is rejected → detached job.
- **Scanner `ports` argument**: pass the spec only — `1-65535`, `80,443`, `T:80,U:53`. nmap's own idioms are accepted too (`-p-`, `p-`, `-` all mean every port) and a redundant `-p` is absorbed, across nmap/rustscan/masscan/httpx. A *different* selector such as `--top-ports 1000` is passed through rather than glued behind `-p`.
- **pty-only listeners**: `penelope`/`pwncat`/`pwncat-cs` need a controlling TTY — run them via `start_interactive_shell`. Through `execute_command` they're auto-guarded: you get `guard: pty_only_listener` + an `nc` `fallback_command` (not a crash/hang), signalling *relaunch under an interactive shell*.
- **Inline backgrounding**: MCPwn owns a fresh POSIX process group and cleans it on normal return, timeout, cancellation, and post-launch error. A bare `cmd &` dies; `nohup` alone remains in that group and also dies. Prefer a managed interactive/daemon wrapper for an indefinite listener or watcher. If `setsid` is unavoidable, make the new session leader write its PID to a file in the analysis workspace before `exec`; before deleting the session, validate that PID still belongs to the expected command, terminate the exact process group (`-PID`), escalate only if it survives, and verify no member remains. MCPwn intentionally cannot reap a process that escaped its owned group. A detached job has no deadline unless you pass `timeout=N`, so it suits open-ended work — it stays killable through `delete_job` precisely because it never leaves MCPwn's owned group. Anything that can hang → `detach=True` (and prefix `timeout N` only when you want the command itself to give up).
- **/etc/hosts**: Docker bind mount — `sed -i` fails EBUSY; use `sudo tee -a /etc/hosts`.
- **Python**: runtime venv is `/opt/venv-core`; system `python3` is PEP-668 managed. Install with `/opt/venv-core/bin/pip install <pkg>`.
- **Kerberos skew**: `run_tool("krb_time_probe", {...})` reads the DC clock and emits a `faketime -f +Ns` wrapper on >5 min skew.
- **No NFS kernel client**: the container has no `nfs` in `/proc/filesystems` and no `CAP_SYS_ADMIN` — `mount -t nfs` fails `Operation not permitted`/`Protocol not supported`. Use the **`nfs_enum`** catalog tool (`get_tools(domain="network", query="nfs")`) — it wraps the userspace libnfs clients: `action=showmount|ls|cat`, with `uid`/`gid` to spoof AUTH_UNIX and beat `root_squash` (root→nobody, other ids pass through; set `gid` to a `0770` dir's group to read it). Or raw: `nfs-ls`/`nfs-cp` on `nfs://host/export?version=3&uid=X&gid=Y`. Reach an internal 2049 through a `tunnel_up` pivot first.
