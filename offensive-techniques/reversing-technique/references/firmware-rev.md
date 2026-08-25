# Firmware Reverse Engineering Supplement

Load this after `triage.md` when the target is a firmware image, extracted update package, or embedded device filesystem. It focuses on container extraction, filesystem pivots, service startup, web/admin surfaces, and emulation handoff.

## Contents

- [Firmware-first workflow](#firmware-first-workflow)
- [High-value triage questions](#high-value-triage-questions)
- [Preserve, identify, then extract within budgets](#1-preserve-identify-then-extract-within-budgets)
- [Review persistence and trust boundaries early](#2-review-persistence-and-trust-boundaries-early)
- [Treat the web interface as a control plane](#3-treat-the-web-interface-as-a-control-plane)
- [Only reverse binaries that matter to the control flow](#4-only-reverse-binaries-that-matter-to-the-control-flow)
- [Emulate after you know the dependencies](#5-emulate-after-you-know-the-dependencies)
- [Common pitfalls](#common-pitfalls)

## Firmware-first workflow

```text
preserve/hash -> identify outer container -> bounded extraction -> filesystem mapping -> startup/persistence review -> embedded binary pivots -> emulation only if needed
```

The goal is to spend time where firmware hides value: configs, init scripts, web handlers, keys, and architecture-specific helpers.

## High-value triage questions

1. **Is it a full image, update package, or single partition?**
2. **What filesystem types are inside?** SquashFS, CramFS, UBIFS, JFFS2, vendor custom.
3. **Where does boot/startup logic live?** init scripts, rc files, service definitions, watchdogs.
4. **What is user-facing?** web UI, RPC daemon, CLI utilities, mobile companion protocol.

## Analysis order that saves time

### 1. Preserve, identify, then extract within budgets

```bash
sha256sum firmware.bin
file firmware.bin
binwalk firmware.bin
```

Keep the original immutable and extract into a fresh directory. Prefer the identified format's native extractor; use recursive carving only when needed, with wall-time, depth, file-count, per-file, and total-output limits. Monitor free space and never execute children on the analyst host. For Binwalk-specific bounds, load the `binwalk` skill.

After extraction, map the tree into roles instead of reading everything linearly:

- **startup**: `/etc/init*`, `/etc/rc*`, init scripts, service files
- **config**: `/etc/config`, `.conf`, `.json`, NVRAM defaults
- **web/admin**: `/www`, CGI, Lua, templates, JS bundles
- **crypto**: keys, certs, SSH material, update verification blobs
- **binaries**: daemons, helpers, protocol parsers

### 2. Review persistence and trust boundaries early

Prioritize:

- privileged daemons started at boot
- debug or factory-mode toggles
- telnet/SSH enable paths
- update/signature verification logic
- watchdog and recovery services that respawn interesting binaries

### 3. Treat the web interface as a control plane

Look for the boundary between HTTP handlers and shell/system helpers.

Common bugs and backdoors:

- command wrappers for ping, traceroute, backup, diagnostics
- hidden endpoints or unauthenticated CGI routes
- default credentials or first-boot bypasses
- weak RPC/auth tokens shared across services

### 4. Only reverse binaries that matter to the control flow

Do not reverse BusyBox clones or standard libs first. Start with binaries that:

- are launched from startup scripts
- service admin/UI requests
- parse update packages or config backups
- touch keys, credentials, or firewall rules

Use `elf-rev.md` for embedded ELF binaries once you know which ones matter.

### 5. Emulate after you know the dependencies

Emulation is most useful after you identify:

- target architecture and endianness
- expected config paths and device nodes
- required libraries and helper binaries
- network services that should listen or call out

Blind emulation first usually turns into yak shaving with serial consoles. Cute yak, wrong day.

## Firmware-specific checklists

### Secrets and trust material

- SSH keys, TLS certs, OEM signing certs
- default users and password hashes
- SNMP communities, API tokens, cloud bootstrap credentials
- hardcoded upgrade URLs and license endpoints

### Service and admin surface

- startup scripts invoking shell with untrusted arguments
- RPC, CGI, Lua, PHP, JS handlers bridging into native helpers
- unsafe file operations for backup/restore/import/export

### Update-chain review

- signature verification present or stubbed
- plaintext vs encrypted update format
- rollback or downgrade acceptance
- model/version checks that can be bypassed trivially

## Common pitfalls

- **Reversing binaries before configs**: firmware logic is often driven by config and init scripts.
- **Ignoring startup order**: the backdoor daemon may be obvious once boot flow is mapped.
- **Treating the UI as separate**: web handlers are often thin wrappers over privileged binaries.
- **Emulating too early**: missing NVRAM, device nodes, or libs will waste time.
- **Missing update verification**: vendor trust logic is often a higher-value target than the main UI.
