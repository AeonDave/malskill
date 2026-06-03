---
name: checksec
description: "Auth/lab ref: Linux binary and kernel hardening inspection tool for RELRO, canary, NX, PIE, RPATH, RUNPATH, symbols, fortify, and kernel config checks."
compatibility: "Linux primary; macOS can inspect Linux files with limits; Go-based releases plus historical bash usage."
metadata:
  author: AeonDave
  version: "1.0"
---

# checksec

Quick hardening triage for ELF binaries and Linux kernels.

## When to use checksec

Use checksec when you need to answer questions like:

- Is PIE enabled?
- Is there a stack canary?
- Is NX enforced?
- Is RELRO partial or full?
- Are symbols stripped?
- What kernel hardening settings are enabled?

This is often the **first command** in pwn/reversing triage.

## Quick Start

```bash
# Inspect one binary
checksec file /bin/ls

# JSON output for automation
checksec file /bin/ls --output json

# Kernel hardening survey
checksec kernel
```

## Output Modes

```bash
checksec file ./target --output cli
checksec file ./target --output json
checksec file ./target --output yaml
checksec file ./target --output xml
```

Use machine-readable output when feeding exploit notes, parsers, or dashboards.

## Common Workflows

### Pwn triage

```bash
checksec file ./vuln
```

Interpret quickly:

- **No PIE** → static code addresses stay stable
- **No canary** → stack overflow path is simpler
- **NX enabled** → likely ret2libc/ROP instead of raw stack shellcode
- **Partial RELRO** → GOT overwrite may still be viable

### Batch or scripted inspection

```bash
checksec file ./target --output json
```

### Kernel review

```bash
checksec kernel
checksec kernel --output json
```

Useful for local privesc context or hardening audits.

### Fortify-focused check

```bash
checksec fortifyProc 1
```

Use when you want deeper fortify coverage rather than just the summary row in normal binary output.

## Cross-Compiled / Offline Filesystem Use

Upstream notes two important limits:

- kernel checks must run on the live system you actually want to assess
- file checks work offline except fortify may need the target libc context

For offline target filesystems, consider pairing checksec with native `readelf` if the environment is stripped down.

## Practical Notes

- Current upstream has moved toward a Go implementation and is faster than the old bash-heavy workflow.
- Checksec is a triage tool, not a full exploitability oracle.
- Always pair the result with real reversing: `readelf`, `objdump`, debugger output, and vulnerability context.

## Caveats

- A "hardened" binary can still be exploitable.
- A missing mitigation does not guarantee an easy exploit.
- On non-Linux hosts some checks are limited.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use upstream examples for the latest subcommands and output schema.
