---
name: radare2
description: "CLI reverse engineering framework with disassembly, debugging, scripting, and binary patching. Use when analyzing binaries headlessly, scripting RE tasks, patching executables, or working in resource-constrained environments."
license: MIT
compatibility: "C; Linux/macOS/Windows; apt install radare2 or github.com/radareorg/radare2"
metadata:
  author: AeonDave
  version: "1.0"
---

# Radare2

CLI RE framework — disassemble, debug, patch, and script binary analysis.

## Quick Start

```bash
# Open binary (read-only)
r2 ./binary

# Analyze all (auto-analysis)
> aaa

# List functions
> afl

# Disassemble function
> pdf @ main

# Print strings
> iz

# Quit
> q
```

## Essential Commands

| Command | Purpose |
|---------|---------|
| `aaa` | Full auto-analysis |
| `afl` | List all functions |
| `pdf @ FUNC` | Disassemble function |
| `s ADDR` | Seek to address |
| `iz` | Print strings in binary |
| `iS` | List sections |
| `ii` | List imports |
| `px N @ ADDR` | Hex dump N bytes at ADDR |
| `ood` | Reopen in debug mode |
| `dc` | Continue execution |
| `dr` | Show registers |
| `VV` | Visual graph mode |
| `/` | Search bytes/strings |

## Common Workflows

**Quick static triage:**
```
r2 malware.exe
> aaa; afl; iz; ii
> pdf @ sym.main
```

**Patch a jump:**
```
r2 -w ./binary
> s 0x401234       # seek to instruction
> wa jmp 0x401300  # write assembly
> q
```

**Script with r2pipe (Python):**
```python
import r2pipe
r2 = r2pipe.open('./binary')
r2.cmd('aaa')
print(r2.cmd('afl'))
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | r2pipe scripting and debugging shortcuts |
