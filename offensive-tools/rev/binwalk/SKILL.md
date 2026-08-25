---
name: binwalk
description: "Auth/lab ref: Firmware analysis and extraction tool for identifying and extracting embedded file systems, compressed archives, executable code, and crypto keys from binary blobs."
license: MIT
compatibility: "Python 3; Linux/macOS/WSL."
metadata:
  author: AeonDave
  version: "1.1"
---

# Binwalk

Firmware analysis and extraction — identify and extract embedded files from binary blobs.

## Contents

- [Safe triage before extraction](#safe-triage-before-extraction)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Flags](#core-flags)
- [Common Workflows](#common-workflows)
- [Python API](#python-api)
- [Emulation after extraction](#emulation-after-extraction)
- [Resources](#resources)

## Safe triage before extraction

Follow the [firmware workflow](../../../offensive-techniques/reversing-technique/references/firmware-rev.md) before extraction. Binwalk-specific invariant: start with a signature/entropy scan; make `-eM` and `--dd ".*"` opt-in; use a fresh `-C` directory plus `-d`, `-n`, and `-j`; and enforce total output bytes with an external monitor/quota because Binwalk v2 has no total-output flag. `-j` limits each carved input region, but an external extractor may still decompress it into a larger tree.

On MCPwn, use `firmware_analyze` or `binwalk_analyze` with `detach=True`. `firmware_analyze` exposes the external aggregate tree budget; `binwalk_analyze` does so only when `extract=true`, because scan-only mode creates no extraction tree. `unblob_analyze` is also detached and session-owned. `auto_malware_hunt` defaults to scan-only, so request recursive extraction explicitly only after triage.

## Installation

```bash
# Debian/Ubuntu
sudo apt install binwalk

# pip
pip install binwalk

# From source (latest)
git clone https://github.com/ReFirmLabs/binwalk && cd binwalk
sudo python setup.py install

# Install extraction dependencies (important)
sudo apt install mtd-utils gzip bzip2 tar arj lhasa p7zip p7zip-full \
    cabextract cramfsswap squashfs-tools sleuthkit default-jdk lzop srecord
```

## Quick Start

```bash
# Scan firmware for signatures
binwalk firmware.bin

# Extract selected signatures with explicit count/per-file bounds
binwalk -e -n 1000 -j 268435456 -C ./extracted firmware.bin

# Bounded recursive extraction (only after format-first triage)
binwalk -eM -d 3 -n 5000 -j 268435456 -C ./extracted firmware.bin
```

## Core Flags

| Flag | Purpose |
|------|---------|
| (none) | Signature scan (default) |
| `-e` | Extract found files |
| `-M` | Recursive/matryoshka extraction |
| `-E` | Entropy analysis |
| `-A` | Disassemble CPU opcodes |
| `-W` | Hexdiff between files |
| `-R STRING` | Search for raw string |
| `-C DIR` | Set output directory |
| `-q` | Quiet mode |
| `-D TYPE:EXT:CMD` | Custom extraction rule |
| `-d N` | Limit recursive extraction depth |
| `-n N` | Limit number of extracted files |
| `-j N` | Limit each extracted file's size |
| `-l N` | Limit input bytes scanned |
| `--dd ".*"` | Carve every matching signature; high expansion risk |
| `-H N` | Set the floating-point high entropy-edge threshold for entropy scans (`-E`) |
| `-m FILE` | Custom magic/signature file |

## Common Workflows

### Full firmware analysis pipeline

```bash
# 1. Initial signature scan
binwalk firmware.bin

# 2. Entropy analysis (detect encrypted/compressed regions)
binwalk -E firmware.bin
# High entropy (>0.9) = encrypted or compressed
# Low entropy (<0.5) = plaintext/code
# Plot to file:
binwalk -E --save firmware.bin

# 3. Extract recursively with explicit bounds
binwalk -eM -d 3 -n 5000 -j 268435456 firmware.bin -C ./extracted/

# 4. Identify filesystems
ls ./extracted/
# Common: squashfs-root/, jffs2-root/, cramfs-root/
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

### Compare firmware versions

```bash
# Hexdiff two firmware images
binwalk -W firmware_v1.bin firmware_v2.bin

# Save diff output
binwalk -W firmware_v1.bin firmware_v2.bin > diff_report.txt
```

### Custom signature scanning

```bash
# Search for specific patterns
binwalk -R "\x7fELF" firmware.bin            # Find ELF headers
binwalk -R "MZ" firmware.bin                  # Find PE headers
binwalk -R "SSH-" firmware.bin                # Find SSH keys/banners

# Use custom magic file
binwalk -m custom_signatures.magic firmware.bin
```

### Manual extraction

```bash
# Extract specific region by offset and size
dd if=firmware.bin of=extracted_blob.bin bs=1 skip=OFFSET count=SIZE

# Binwalk with custom extraction rule
binwalk -D "gzip:gz:gunzip '{filename}'" firmware.bin

# Extract raw bytes at known offset
binwalk --dd ".*" --offset=0x10000 --length=0x50000 firmware.bin
```

## Python API

```python
import binwalk

# Scan for signatures
for module in binwalk.scan('firmware.bin', signature=True, quiet=True):
    for result in module.results:
        print(f"  0x{result.offset:08X}: {result.description}")

# Entropy analysis
for module in binwalk.scan('firmware.bin', entropy=True, quiet=True):
    for result in module.results:
        print(f"  0x{result.offset:08X}: entropy={result.description}")

# Extract
binwalk.scan('firmware.bin', signature=True, extract=True, quiet=True,
             directory='./output/')
```

## Emulation after extraction

```bash
# After extracting a Linux-based firmware:
# 1. Find the root filesystem
ls ./extracted/squashfs-root/

# 2. Emulate with QEMU user-mode (for ARM/MIPS binaries)
# Copy qemu-static into the filesystem
cp $(which qemu-arm-static) ./squashfs-root/usr/bin/
sudo chroot ./squashfs-root/ /usr/bin/qemu-arm-static /bin/sh

# 3. Or use firmadyne/FirmAE for full system emulation
# https://github.com/firmadyne/firmadyne
```

## Resources

| File | When to load |
|------|--------------|
| [references/firmware-analysis.md](references/firmware-analysis.md) | Firmware filesystem types and QEMU emulation workflows |
| [references/custom-signatures.md](references/custom-signatures.md) | Writing custom binwalk signature files |
