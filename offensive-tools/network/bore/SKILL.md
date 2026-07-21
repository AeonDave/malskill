---
name: bore
description: "Auth/lab ref: ekzhang/bore: minimal Rust-based reverse TCP tunnel exposing a local port through a public relay (default bore.pub) or a self-hosted server, with optional HMAC `--secret` auth."
license: MIT
compatibility: "Linux/macOS/Windows."
metadata:
  author: AeonDave
  version: "1.0"
---

# bore

Tiny Rust TCP tunneling tool by Eric Zhang (`ekzhang/bore`, ~10k LOC). The client opens a control connection to a relay server, registers a remote port, and proxies every accepted TCP connection back to a local service. Default public relay is `bore.pub`; self-hosting on an owned VPS is a one-line command.

Pure TCP only — no HTTP parsing, no TLS termination, no header rewriting, no auth on visitors. Strengths are simplicity, speed, deterministic ports, and a single static binary.

## Scope Guard

- Confirm the exposed service, audience, time window, and authorization before mapping any local port to a public relay.
- Treat `bore.pub` as untrusted infrastructure: anyone can connect to the assigned remote port. Always layer app-level auth, short runtime, and IP allowlists at the OS firewall.
- Do not expose admin interfaces, databases, MCP/AI tools, shells, or unauthenticated dev services to the internet without owner approval.
- For sensitive engagements, self-host the server on owned infrastructure and enable `--secret` HMAC auth so only the operator's clients can register tunnels.
- bore does not encrypt application traffic. If confidentiality matters, terminate TLS at the local service or wrap with `stunnel`/`socat openssl`/SSH.

## When to Pick bore

| Need | Pick |
|---|---|
| Raw TCP ingress, deterministic port, self-host in one command | **bore** |
| HTTPS URL with request debugger, header rewrite, basic auth, QR | `pinggy`, `ngrok`, `cloudflared` |
| OAST / blind-callback collection with web UI + DNS hook | `webhook-site`, `interactsh` |
| SOCKS/port-forward over a compromised pivot, no public relay | `chisel`, `ssh -D`, `ssh -R` |
| Long-lived covert C2 channel | Dedicated C2 (Sliver, Mythic, Adaptix, CS); bore is not designed for stealth |

## Install

```bash
# From crates.io (recommended for operators)
cargo install bore-cli

# Prebuilt binary (Linux x86_64 example; pick the asset for your platform)
curl -fsSL -o /tmp/bore.tgz \
  https://github.com/ekzhang/bore/releases/latest/download/bore-v0.5.2-x86_64-unknown-linux-musl.tar.gz
tar -xzf /tmp/bore.tgz -C /usr/local/bin bore

# Docker (client or server)
docker run --rm -it --init --net=host ekzhang/bore local 8080 --to bore.pub
docker run -d --restart unless-stopped --name bore-server \
  -p 7835:7835 -p 1024-65535:1024-65535 ekzhang/bore server --secret 'CHANGEME'
```

Verify: `bore --version` (should print `bore-cli x.y.z`).

## Quick Starts (Client)

```bash
# Expose local 8080 on a random public port at bore.pub
bore local 8080 --to bore.pub
# -> listening at bore.pub:<RANDOM_PORT>

# Request a specific remote port (server must allow it)
bore local 4444 --to bore.pub --port 4444

# Forward a service bound to a non-loopback local address
bore local 80 --to bore.pub --local-host 192.168.1.50 --port 8080

# Use an authenticated self-hosted server
bore local 9001 --to relay.example.com --secret "$BORE_SECRET" --port 9001

# Background runner with auto-restart (systemd-friendly one-liner)
nohup bore local 4444 --to relay.example.com --secret "$BORE_SECRET" --port 4444 >/tmp/bore.log 2>&1 &
```

The client prints `listening at <host>:<port>` once the remote port is reserved. Any TCP connection to that endpoint is proxied to `local-host:local-port`.

## Quick Starts (Self-Hosted Server)

```bash
# Minimum: open control port 7835 (default), allow tunnel ports 1024-65535
bore server

# Authenticated, narrowed port range, bound only to a private IP
bore server \
  --secret "$(openssl rand -hex 32)" \
  --min-port 20000 --max-port 20100 \
  --bind-addr 10.10.0.5 \
  --bind-tunnels 10.10.0.5

# Behind a firewall: only open 7835/tcp + your chosen tunnel range
ufw allow 7835/tcp
ufw allow 20000:20100/tcp
```

Bind the control port (`7835`) only where operators connect from. Bind the *tunnel* ports (`--bind-tunnels`) to the interface that should receive visitor traffic — often a public IP, but for internal-only labs use a private one.

## CLI Reference

### `bore local`

| Flag | Default | Purpose |
|---|---|---|
| `<LOCAL_PORT>` | — | Local TCP port to forward (positional). |
| `-t, --to <HOST>` | required | Relay server hostname/IP (e.g. `bore.pub`, `relay.example.com`). |
| `-p, --port <PORT>` | `0` (random) | Requested remote port on the relay. Server may refuse if outside its range or already used. |
| `-l, --local-host <HOST>` | `localhost` | Local host the relay should connect back to (use when the service binds to a non-loopback address). |
| `-s, --secret <SECRET>` | unset | HMAC shared secret. Must match server `--secret` or handshake fails. Read from `BORE_SECRET` env if unset. |

Environment: `BORE_SECRET=...` is consumed automatically when `-s` is omitted — prefer the env var over CLI flags so the secret is not visible in `ps`.

### `bore server`

| Flag | Default | Purpose |
|---|---|---|
| `--min-port <PORT>` | `1024` | Lower bound for tunnel ports the server will assign or accept. |
| `--max-port <PORT>` | `65535` | Upper bound for tunnel ports. |
| `-s, --secret <SECRET>` | unset | Require this HMAC secret on every client handshake. Read from `BORE_SECRET` env when unset. |
| `--bind-addr <IP>` | `0.0.0.0` | Interface for the control listener (default port `7835/tcp`). |
| `--bind-tunnels <IP>` | value of `--bind-addr` | Interface visitors hit for the assigned tunnel ports. Useful to keep control on a private VLAN while exposing tunnels on a public IP. |

Always set `--secret` on a public server, even for short engagements. Without it the relay is an open redirector that any third party can register tunnels on.

## Operator Patterns

### Reverse shell callback on a deterministic port

```bash
# Operator (own VPS already running `bore server --secret $S`)
bore local 4444 --to relay.example.com --port 4444 --secret "$S" &
nc -lvnp 4444     # or msfconsole multi/handler, sliver, etc.

# Victim payload connects to relay.example.com:4444 and lands on the local listener.
```

### Payload / loader hosting

```bash
python3 -m http.server 8000 --bind 127.0.0.1 &
bore local 8000 --to relay.example.com --port 8000 --secret "$S"
# Deliver: http://relay.example.com:8000/loader.exe
```

Pair with a one-shot file server (`python -m RangeHTTPServer`, `miniserve --auth`) and stop bore immediately after the callback.

### OAST collector for SSRF / XXE / blind RCE

bore exposes a raw TCP port — perfect for a local `interactsh-server`, `tcpdump`, or custom Python listener that needs to record arbitrary inbound bytes:

```bash
sudo tcpdump -i lo -A -s0 port 5555 -w /tmp/oast.pcap &
bore local 5555 --to relay.example.com --port 5555 --secret "$S"
# Trigger: payload calls back to relay.example.com:5555
```

For HTTP-shaped callbacks with a real UI prefer `webhook-site` or `interactsh`; use bore when you need raw TCP, custom protocols, or full packet capture.

### Inbound reach into a NAT'd lab from a jump host

Run `bore server` on a reachable jump host; on each isolated lab VM run a long-running `bore local` to publish RDP/SSH/HTTP for the operator. This avoids opening firewall rules per VM but exposes those ports to anyone who knows the relay + port; gate with `--secret` and OS-level firewall rules.

### Authenticated multi-operator relay

A self-hosted server with a strong `--secret` plus a narrow `--min-port/--max-port` range lets a team share one VPS without the bore.pub trust assumptions. Distribute the secret out-of-band and rotate after each engagement.

## Hardening Checklist

- Self-host on owned infrastructure for anything sensitive; treat `bore.pub` as a public test relay only.
- Set `--secret` on every public server (`openssl rand -hex 32`). Pass via `BORE_SECRET` env var, not CLI.
- Restrict tunnel port range with `--min-port/--max-port` so the server cannot be reused as a generic open proxy.
- Bind control to a private interface or restrict `7835/tcp` with `iptables`/`ufw` to operator source IPs.
- Add OS-level firewall allowlists for the tunnel port range, scoped to the expected client IPs of the engagement.
- Run the server as an unprivileged user inside a hardened systemd unit; cap port range above 1024 to avoid `CAP_NET_BIND_SERVICE`.
- Stop tunnels as soon as the test window ends. bore has no built-in idle timeout.
- bore has no built-in transport encryption between client and server — the wire is plaintext TCP. Place the server behind a WireGuard/SSH overlay if you need confidentiality on the control channel itself.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `error: server rejected authentication` | Secret mismatch or server expects auth and client did not provide. | Match `--secret` / `BORE_SECRET` on both ends; check for trailing whitespace. |
| `error: port not available` | Requested `--port` already in use or outside server range. | Drop `--port` to get a random one, or widen `--min-port/--max-port`. |
| Visitors hang / connection reset | Local service not listening or bound to `127.0.0.1` while bore tries `localhost` over IPv6. | Bind the service to `0.0.0.0` or pass `--local-host 127.0.0.1` explicitly. |
| Tunnel works once then silent | bore exits when the control connection drops; no auto-reconnect. | Wrap in systemd / `while true; do bore ...; sleep 2; done` for long runs. |
| Public IP reaches the wrong service | bore.pub is multi-tenant; ports rotate. | Use `--port` against a self-hosted server you control. |
| Cloud provider blocks high ports | Some VPS providers block ranges by default. | Pick a range allowed by the provider (e.g. 10000-10100) and reflect it in `--min-port/--max-port`. |
| Docker server cannot map huge port range | Docker iptables rules become slow with thousands of ports. | Use `--net=host` on Linux, or narrow `--min-port/--max-port` to dozens of ports. |

## Resources

| File | When to load |
|---|---|
| `references/usage-matrix.md` | Full client/server flag matrix, self-host hardening recipe, operator playbooks (reverse shell, payload host, OAST, multi-tenant relay), and side-by-side comparison with pinggy/ngrok/chisel/interactsh. |
