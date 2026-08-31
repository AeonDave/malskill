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

Bounded control-plane calls remain inline even when they accept an explicit wait:
use `emulation_operation` directly for native job `list`/`poll`/`cancel`, and
`emulation_endpoint_client` directly for endpoint-client lifecycle operations. Their
wait values are clamped. Wrapping these calls in another detached catalog job makes
recovery and cleanup harder and must not be required by tool metadata.

## Short commands — `execute_command`

- Synchronous: the MCP request blocks until exit or timeout.
- Inline execution is capped at 20s. `MCPWN_INLINE_TIMEOUT_CAP` may lower it to a 5s minimum but cannot raise it; a lower `MCPWN_MAX_LONG_POLL_SECONDS` also lowers it. Process cleanup can add bounded time after the execution timeout, so use `detach=True` near the ceiling. Detached calls have no deadline unless you pass `timeout=N`.
- If an inline command times out at the cap, that work belongs on `detach=True` + `poll_job` — not on a larger timeout. The cap is only liftable server-side, by an operator setting `MCPWN_ALLOW_LONG_INLINE=1` for a client that issues concurrent requests (cap then defaults to 120s and `MCPWN_INLINE_TIMEOUT_CAP` may raise it).
- Some MCP clients serialize calls to one server. An inline command delays unrelated session/catalog calls on those clients, so detach anything duration-uncertain or near the ceiling.
- Known-long workload commands are **rejected synchronously** with `long_running_command`: `nmap -sV`/`-sC`/`-p-`, hydra, ffuf, feroxbuster, gobuster, sqlmap, hashcat, john, masscan, amass, nuclei, wpscan, nikto, kerbrute, katana. Use `detach=True`. Exact info-only forms with no operands (`-h`, `--help`, `-V`, or `--version`) remain inline-safe; the moment an operand or real work option is present, detach.
- With `output_mode='auto'`, output >64 KB is saved to a complete CAS artifact and returns an id + preview; `output_mode='artifact'` always requests that handoff. `/api/command` itself defaults to `inline`. Inline stdout and stderr are independently limited to head/tail previews (4 MiB each by default); inspect `stdout_bytes`, `stderr_bytes`, and the truncation flags. Explicit/automatic artifact handoff streams the full captures rather than storing the previews.
- `timed_out=true` is authoritative and means execution was incomplete; current MCPwn results set `success=false` on timeout. `partial_results=true` also covers a successfully completed command whose inline output was truncated. Inspect `timed_out`, `return_code`, `partial_results`, and truncation flags before accepting a result.
- Use for: `whoami`, `cat`, `ls`, `id`, fast `curl`, short nmap, one-liners.

## Async jobs — `detach=True` + `poll_job`

- Returns `{job_id}` immediately. `poll_job(job_id, wait_seconds=20)` in a loop until terminal status.
- Detached payloads are terminal-only: `list_jobs` exposes lifecycle metadata and `poll_job` advertises `incremental_output_available=false` until the retained result is terminal. Use an interactive session or a bounded workspace progress file for live output; fetch/persist the terminal result or artifact before `delete_job` removes it.
- `long_running=True` catalog tools (including `firmware_analyze`, `binwalk_analyze`, `unblob_analyze`, `auto_malware_hunt`, `analyze_with_radare2`, `decompile_with_radare2`, `pacu_aws_exploit`, `torch_model_inspect`, `keras_model_inspect`, `sklearn_model_inspect`, `vec2text_invert`, `ml_script_execute`, ffuf, feroxbuster, gobuster, hydra, john, hashcat, sqlmap, amass, zap_active_scan, nuclei_scan, katana_crawl, mythril_analyze, and volatility_analyze) **require** `detach=True`.

### Duration-uncertain catalog wrappers

- Treat deep decompilation, global analysis, and any wrapper with uncertain duration as asynchronous: dispatch with `detach=True`, poll at bounded intervals, and keep concurrent heavy jobs limited so the backend is not saturated.
- `firmware_analyze` requires a managed session and scans only by default. The forensics `binwalk_analyze`/`unblob_analyze` extraction paths use the same session-owned bounded model, and `auto_malware_hunt` is scan-only unless `extract=true`. Keep extraction opt-in and detached; these paths bound logs and use unique output directories with depth, file-count, filesystem-entry, and aggregate-byte budgets (plus Binwalk's distinct per-file cap).
- The PyTorch, Keras, and scikit-learn inspectors deserialize formats that can execute code. Treat them as destructive execution, not read-only parsing, and use only authorized artifacts.
- `torch_model_inspect`, `keras_model_inspect`, `sklearn_model_inspect`, and `vec2text_invert` have no execution deadline unless `timeout` is set to 1–3600 seconds. `ml_script_execute` remains bounded: default 120 seconds, maximum 600.
- `pacu_aws_exploit` requires a workspace-relative `credentials_file`; `aws_profile` must exist in it or the optional workspace-relative `config_file`, and is imported on every call. Ambient AWS credential sources are disabled; keep secrets out of `module_args`. State is isolated under `.pacu-home/<pacu_session>` inside the analysis workspace. Concurrent use fails fast with `pacu_session_busy`: retry instead of creating a duplicate. Set `create_pacu_session=true` only on the first call, then reuse with `false`. Omit `timeout` for no module deadline or set 1–3600 seconds; always dispatch detached.
- A caller/MCP request timeout can end the caller's wait without cancelling the backend job. Re-query job and cancellation state before retrying; when cancellation is needed, use `delete_job` and verify that the job reaches a terminal state.
- If polling reports an unhealthy or unavailable backend, report that condition and stop. Do not restart or rebuild MCPwn/the backend without user direction.

### The two detached paths behave differently

| | `execute_command(cmd, detach=True)` | `run_tool(name, {...}, detach=True)` |
|---|---|---|
| Timeout with no explicit value | **none — runs until it finishes** | route-specific: a default ceiling or no deadline; inspect `get_tool` |
| Stopping it | **hard kill**: `delete_job` SIGKILLs the owned process tree and verifies it | dynamic: hard-killable while a local subprocess reports `killable=true`; otherwise cooperative |
| Backstop | job reaper hard-kills unfinished jobs at 4h | hard-kills an active bound subprocess; otherwise retains truthful pending state for retry |

- So **anything arbitrary and open-ended belongs on `execute_command(detach=True)`**: no deadline unless you set `timeout=N`, and it is genuinely interruptible on demand. This is the path for a tool MCPwn does not wrap at all.
- Catalog deadlines are route-specific. Long-scan wrappers exposing `MCPWN_LONG_SCAN_TIMEOUT_CAP` remain bounded; Radare2 defaults to 120 seconds and accepts 1–270; `ml_script_execute` defaults to 120 and caps at 600; the Pacu/ML exceptions above default to no execution deadline. If a bounded wrapper cannot run long enough, drive the binary through `execute_command(detach=True)`.
- `delete_job(job_id)` requests cancellation and removes the record only after stop is observed. For `execute_command` jobs it invokes the hard process-tree kill. A catalog job acquires a dynamic kill hook only while its current local subprocess is active; inspect `killable` immediately before deletion. Pure-Python, remote, and between-command phases may return `cancellation_pending=true`, `execution_stopped=false`, and `record_deleted=false`; poll and retry after the worker reaches a bounded checkpoint. `cancellation_pending` is not proof of stop, and neither is `ok=true`; require observed `execution_stopped=true` before destruction or workspace removal.
- Do NOT tight-loop `poll_job` over a bare sleep. Offload a long timed wait into ONE detached job: `execute_command("until test -f /tmp/ready; do sleep 30; done", detach=True)` or `execute_command("sleep 2700; echo done", detach=True)`, then poll every few minutes. No `timeout` is needed — a detached run has no deadline of its own.

### Provider job identity and recovery

For a detached NeuroMatrix bridge call, persist both handles: `operation_id` is the
MCPwn bridge job used with `poll_job`/`delete_job`, while `neuromatrix_job_id` is the
native provider job used with `emulation_operation` and provider recovery. They are
opaque, provider-scoped values; do not substitute one for the other. If a bridge is
lost or reports `PROVIDER_IDENTITY_MISMATCH`, rediscover `list_catalog`, `list_jobs`,
and `list_artifacts`, then restage inputs before retrying provider operations.

## Interactive shell

Lifecycle:
```
start_interactive_shell(session_id, command) → interactive_id + pid
run_in_shell(interactive_id, cmd)             # discrete command → {output, exit_code}
read_shell_output(interactive_id, wait_seconds=20)  # streaming/TUI only, long-poll, repeat
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
