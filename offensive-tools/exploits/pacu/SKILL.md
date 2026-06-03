---
name: pacu
description: "Auth/lab ref: modular AWS exploitation framework for authorized cloud assessments."
license: BSD-3-Clause
compatibility: "Linux, macOS, WSL; Python 3.7+."
metadata:
  author: AeonDave
  version: "1.0"
---

# Pacu

Session-based AWS exploitation framework.

## Scope and authorization

Use Pacu only with explicit authorization and with awareness of AWS acceptable-use and testing policy constraints.

Upstream is clear: you are responsible for ensuring the engagement and modules are permitted in the target environment.

## Installation

```bash
# Preferred on Kali / modern Python environments
pipx install git+https://github.com/RhinoSecurityLabs/pacu.git

# Simpler pip path
pip3 install -U pacu

# Docker alternative
docker run -it rhinosecuritylabs/pacu:latest
```

## Interactive Quick Start

```bash
pacu
```

First launch creates or resumes a **session**. Sessions store keys and collected data.

Inside Pacu:

```text
set_keys
whoami
list
help iam__privesc_scan
run iam__enum_permissions
run iam__privesc_scan
```

## Core Workflow

### 1. Create session and load credentials

Use `set_keys` to provide:

- alias
- access key ID
- secret access key
- optional session token

### 2. Identify who you are

```text
whoami
```

Do this immediately after loading creds. It anchors the rest of the assessment.

### 3. Enumerate available modules

```text
list
help module_name
```

### 4. Execute high-value modules

```text
run iam__enum_permissions
run iam__privesc_scan
```

`iam__privesc_scan` is one of the highest-value starting points when IAM abuse is in scope.

## CLI Mode

```bash
pacu --help
pacu --list-modules
pacu --session mysession --whoami
pacu --session mysession --module-name iam__privesc_scan --exec
```

Useful for reproducible commands, wrappers, or scripted lab flows.

## Why Pacu is useful

Upstream highlights that Pacu:

- stores data in a local SQLite-backed workflow
- reduces redundant API calls and logging noise versus ad hoc scripting
- keeps command logging for reporting and timeline building
- provides module-oriented attack paths across enumeration, privesc, exfiltration, and abuse

## Practical Notes

- Start with identity and permission enumeration before running noisier exploitation modules.
- Keep region scope intentional. Broad scans create logs quickly.
- Prefer modules that answer a concrete question instead of running everything blindly.
- Export or preserve session artifacts for reporting.

## Caveats

- Pacu is powerful but opinionated; understand what a module will do before executing it.
- Docker mounts of `~/.aws` are convenient but expose host credentials to the container.
- Cloud authorization, provider policy, and customer scope matter more than tool convenience.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the upstream wiki for module catalog details and installation edge cases.
