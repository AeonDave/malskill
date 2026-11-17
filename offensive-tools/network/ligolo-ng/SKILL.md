---
name: ligolo-ng
description: "Configure Ligolo-ng agent/proxy tunnels, TUN interfaces, and routes for authorized access to a remote network. Use when applications need routed access rather than a SOCKS wrapper."
license: MIT
compatibility: "Go binary; agent runs on Windows/Linux/macOS x64/ARM64; proxy (operator side) on Linux/macOS/Windows. Requires TUN interface (/dev/net/tun on Linux, wintun.dll on Windows)."
metadata:
  author: AeonDave
  version: "1.0"
---

# Ligolo-ng

The agent connects to an operator-side proxy. A TUN interface and explicit routes send traffic through the selected agent; applications do not need SOCKS configuration.

## Core workflow

```bash
# Linux operator: create the interface before starting the tunnel
sudo ip tuntap add user "$(id -un)" mode tun ligolo
sudo ip link set ligolo up
./proxy -selfcert -laddr 0.0.0.0:11601
```

In the proxy console, run `certificate_fingerprint`. Obtain that value from the trusted operator console, then connect the agent using the extracted binary's actual name:

```powershell
.\agent.exe -connect <operator-ip>:11601 -accept-fingerprint <proxy-certificate-fingerprint>
```

In the proxy console, select the connected agent and start its tunnel:

```text
session
tunnel_start --tun ligolo
```

```bash
# Linux operator: route only the authorized remote subnet
sudo ip route add 10.10.10.0/24 dev ligolo
curl http://10.10.10.5:8080
```

## Best practice

- **Other operator platforms**: follow the [upstream quickstart](https://docs.ligolo.ng/Quickstart/) for Windows Wintun and macOS interface/routing requirements.
- **Listener direction**: `listener_add` listens on the agent and forwards to an address reachable from the proxy. It is not a substitute for routing arbitrary remote services through the TUN.
- `-selfcert` creates a self-signed proxy certificate; the agent must validate its fingerprint. `-ignore-cert` disables verification and is only for isolated lab/debugging use.

## Gotchas

- Creating interfaces and routes requires privileges on the operator machine; the agent can run unprivileged.
- Supported traffic is TCP, UDP, and ICMP echo requests. TCP is translated into agent-side socket connections, not forwarded as raw packets.
- Routing a subnet does not configure the operator's DNS resolver. Verify name resolution separately; the proxy has no general `--dns` option.
- Agent-local loopback access uses the reserved `240.0.0.0/4` mapping, not a listener pointing back at the proxy. Load [local-port documentation](https://docs.ligolo.ng/Localhost/) when accessing agent-local services.

## References

- Upstream: [nicocha30/ligolo-ng](https://github.com/nicocha30/ligolo-ng) (Nicolas Chatelain)
- Load [listener documentation](https://docs.ligolo.ng/Listeners/) when an agent must accept incoming connections.
- Companions: `chisel` (SOCKS alternative when TUN is unavailable), `socat` (manual relay), `ssh-tunneling` (SSH-based pivots)
