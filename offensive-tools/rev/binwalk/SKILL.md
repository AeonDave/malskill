---
name: binwalk
description: "Auth/lab ref: Firmware analysis and extraction (binwalk v3, Rust) — identify and extract embedded file systems, compressed archives, executable code, and crypto keys from binary blobs."
license: MIT
compatibility: "Binwalk v3.1.0 (Rust); CLI flags differ between releases and development builds."
metadata:
  author: AeonDave
  version: "2.0"
---

# Binwalk (v3)

Firmware analysis and extraction — identify and extract embedded files from binary blobs. Binwalk v3 is a Rust rewrite with a different CLI; check `binwalk --version` and `--help` before use.

## Contents

- [Safe triage before extraction](#safe-triage-before-extraction)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Flags](#core-flags)
- [Common Workflows](#common-workflows)
- [v2 → v3 migration notes](#v2--v3-migration-notes)
- [Emulation after extraction](#emulation-after-extraction)
- [Resources](#resources)

## Safe triage before extraction

Follow the [firmware workflow](../../../offensive-techniques/reversing-technique/references/firmware-rev.md) before extraction. Start with a signature/entropy scan; make recursive extraction (`-M`) opt-in; extract into a fresh `--directory` and monitor total output size externally.

On MCPwn, use `firmware_analyze` or `binwalk_analyze` with `detach=True`. `firmware_analyze` exposes the external aggregate tree budget; `binwalk_analyze` does so only when `extract=true`, because scan-only mode creates no extraction tree. `unblob_analyze` is also detached and session-owned. `auto_malware_hunt` defaults to scan-only, so request recursive extraction explicitly only after triage.

## Installation

```bash
# Rust toolchain install (canonical for v3)
cargo install binwalk

# Or grab the release binary / Docker image
# https://github.com/ReFirmLabs/binwalk/releases

# Extraction dependencies (external tools binwalk v3 invokes)
sudo apt install mtd-utils gzip bzip2 tar arj lhasa p7zip p7zip-full \
    cabextract squashfs-tools sleuthkit lzop srecord
```

## Quick Start

```bash
# Scan firmware for signatures
binwalk firmware.bin

# Extract matching signatures
binwalk -e firmware.bin

# Recursive (matryoshka) extraction into a fresh directory
binwalk -e -M --directory ./extracted firmware.bin

# Entropy analysis; inspect the output path reported by Binwalk
binwalk -E firmware.bin
```

## Core Flags

| Flag | Purpose |
|------|---------|
| (none) | Signature scan (default) |
| `-e` | Extract found files |
| `-M` | Recursive/matryoshka extraction |
| `-E` | Entropy analysis |
| `--directory DIR` | Set extraction directory |
| `-q` | Quiet mode |
| `-L` | List supported signatures and extractors |
| `--include SIG` / `--exclude SIG` | Filter signatures by name |
| `--log FILE` | Log JSON results to a file |
| `--threads N` | Parallel scan threads |

For unsupported v2 features, use separate tools for disassembly, byte search, and diffing; enforce extraction quotas externally.

## Common Workflows

### Full firmware analysis pipeline

```bash
# 1. Initial signature scan
binwalk firmware.bin

# 2. Entropy analysis (detect encrypted/compressed regions)
binwalk -E firmware.bin
# High entropy can indicate compression or encryption; it does not distinguish them.

# 3. Extract recursively into a fresh directory
binwalk -e -M --directory ./extracted firmware.bin

# 4. Identify filesystems
find ./extracted/ -type d
# Locate the actual extracted filesystem within offset-specific directories.
```

### Post-extraction analysis

```bash
# Find credentials
find ./extracted/ -type f \( -name "*.conf" -o -name "*.cfg" -o -name "passwd" \
    -o -name "shadow" -o -name "*.key" -o -name "*.pem" \) 2>/dev/null

# Search for hardcoded secrets
grep -rn "password\|secret\|api_key\|token\|admin" ./extracted/ --include="*.conf" --include="*.sh" --include="*.lua"

# Find executables for further reversing
find ./extracted/ -type f -executable | file -f - | grep "ELF"

# Find web interfaces
find ./extracted/ -type f \( -name "*.html" -o -name "*.php" -o -name "*.cgi" \) 2>/dev/null
```

### Raw search (replaces v2 `-R`)

```bash
# Find ELF/PE headers and banners by raw bytes
grep -abo $'\x7fELF' firmware.bin
grep -abo 'MZ' firmware.bin | head
strings -t x firmware.bin | grep -E "SSH-|Dropbear"
```

### Manual extraction

```bash
# Extract a specific region by offset and size
dd if=firmware.bin of=extracted_blob.bin bs=1 skip=OFFSET count=SIZE

```

## v2 → v3 migration notes

- Install v3 using `cargo install binwalk`; pip and v2 source instructions do not install v3.
- v3 does not load v2 magic files; see [references/custom-signatures.md](references/custom-signatures.md) for its Rust signatures.
- The `-W` hexdiff and `-A` opcode-scan features were dropped: use `vbindiff`/`radare2` for the same triage steps.
- v2 extraction bounds are unavailable: use external quotas, scan first and select signatures with `--include`.

## Emulation after extraction

Locate the actual extracted root filesystem first; consult the [firmware workflow](../../../offensive-techniques/reversing-technique/references/firmware-rev.md) for isolated emulation.

## Resources

| File | When to load |
|------|--------------|
| [references/firmware-analysis.md](references/firmware-analysis.md) | Firmware filesystem types and QEMU emulation workflows |
| [references/custom-signatures.md](references/custom-signatures.md) | Load when implementing a custom v3 signature |
