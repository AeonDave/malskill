---
name: revshellgen
description: "Interactive Python reverse-shell generator with auto listener setup, encoding support, and shell-type selection. Use when generating modern reverse shell payloads from CLI, choosing payloads by runtime availability, and speeding up operator workflows without manual one-liner editing."
license: GPL-3.0
compatibility: "Python 3.6+; Linux/macOS; pip install revshellgen; github.com/t0thkr1s/revshellgen"
metadata:
  author: AeonDave
  version: "1.0"
---

# RevShellGen

Modern interactive reverse-shell generator with payload selection, encoding options, and built-in listener assistance.

## Quick Start

```bash
# install
pip install revshellgen

# run interactive workflow
revshellgen

# alt source install
git clone https://github.com/t0thkr1s/revshellgen
cd revshellgen
pip3 install -r requirements.txt
python3 revshellgen.py
```

## Why RevShellGen

Compared to static cheat sheets, RevShellGen provides:
- interface-driven payload selection
- runtime-friendly shell catalog (bash/python/powershell/socat/etc.)
- URL/Base64 encoding options
- automatic clipboard copy
- listener helper behavior in one workflow

## Typical Operator Flow

1. Select local callback IP (auto-detected interfaces shown)
2. Set callback port
3. Choose payload family by target runtime
4. Choose encoding only if injection context requires it
5. Copy generated command
6. Start/verify listener
7. Execute payload on target

## Payload Family Selection

| Target runtime | Suggested payload |
|---|---|
| Linux with bash + /dev/tcp | bash |
| Python available, shell constrained | python |
| Netcat with mkfifo possible | netcat mkfifo |
| Socat available | socat / socat tty |
| Windows cmd/powershell context | powershell |

## PTY Upgrade (Linux targets)

After callback shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
export TERM=xterm
stty rows 50 cols 180
```

## OPSEC Guidance

- Use non-default callback ports in monitored environments.
- Prefer shortest payload that works for current foothold.
- Avoid unnecessary encoding unless required by exploit channel.
- Clear command artifacts where engagement scope allows cleanup.

## Integration Patterns

- Use with `revshells` for web-based fast fallback payloads.
- Use with `shellerator` when bind/webshell mode is explicitly needed.
- Use with `reverse-ssh` or `pwncat` to stabilize fragile initial shells.

## Resources

| File | When to load |
|---|---|
| `references/workflow-and-payload-mapping.md` | Deep selection strategy, troubleshooting broken payloads, and listener reliability tips |
