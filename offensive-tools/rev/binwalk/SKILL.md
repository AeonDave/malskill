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

# Extract all found content
binwalk -e firmware.bin
# Output in _firmware.bin.extracted/

# Recursive extraction (matryoshka — nested containers)
binwalk -eM firmware.bin
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
| `-l N` | Limit extraction byte size |
| `--dd ".*"` | Extract everything |
| `-n` | Length scan (no extraction) |
| `-H` | Header signature details |
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

# 3. Extract recursively
binwalk -eM firmware.bin -C ./extracted/

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
