# Binwalk — Firmware Analysis & QEMU Emulation

## Contents

- [Filesystem Types in Firmware](#filesystem-types-in-firmware)
- [Post-Extraction Analysis](#post-extraction-analysis)
- [QEMU Emulation](#qemu-emulation)
- [Entropy Analysis](#entropy-analysis)
- [Bypassing Encryption](#bypassing-encryption)
- [Useful Binwalk Flags for Deep Analysis](#useful-binwalk-flags-for-deep-analysis)
- [Struct Recovery from NVRAM/Config](#struct-recovery-from-nvramconfig)

## Filesystem Types in Firmware

| Filesystem | Magic / Signature | Tool to Mount/Extract |
|-----------|-------------------|----------------------|
| SquashFS | `hsqs`, `sqsh` | `unsquashfs -d out/ fs.squashfs` |
| JFFS2 | `\x85\x19\x03\x20` | `jefferson jffs2.img -d out/` |
| CramFS | `0x28cd3d45` | `mount -t cramfs -o loop cramfs.img /mnt` |
| UBIFS | `\x31\x18\x10\x06` | `ubireader_extract_files ubi.img` |
| ext2/3/4 | `\x53\xEF` | `mount -o loop ext.img /mnt` |
| YAFFS2 | `\x03\x00\x00\x00` | `unyaffs2 yaffs2.img -d out/` |
| eCos FS | — | Manual extraction |
| TAR | `ustar` | `tar -xf archive.tar` |
| CPIO | `070701` | `cpio -idm < archive.cpio` |

## Post-Extraction Analysis

### Identify device credentials

```bash
# Fresh directory produced by the bounded extraction workflow below.
EXTRACTED="./extracted"

# Password hashes
find "$EXTRACTED" -name "passwd" -o -name "shadow" 2>/dev/null | \
    xargs grep -h ":" 2>/dev/null | grep -v "^#"

# Config files with credentials
grep -rni "password\|passwd\|secret\|apikey\|api_key\|token" \
    "$EXTRACTED" --include="*.conf" --include="*.cfg" \
    --include="*.json" --include="*.ini" --include="*.sh" \
    --include="*.lua" --include="*.xml" 2>/dev/null | head -50

# Private keys
find "$EXTRACTED" -name "*.pem" -o -name "*.key" -o -name "*.crt" \
    -o -name "id_rsa" -o -name "id_dsa" 2>/dev/null
```

### Map the attack surface

```bash
# All executables (by magic, not extension)
find "$EXTRACTED" -type f | xargs file 2>/dev/null | \
    grep -E "ELF|PE32" | awk -F: '{print $1}'

# Web server scripts
find "$EXTRACTED" -name "*.cgi" -o -name "*.php" \
    -o -name "*.asp" -o -name "*.lua" 2>/dev/null

# Network services config
find "$EXTRACTED" -name "inetd.conf" -o -name "xinetd.d" \
    -o -name "init.d" -o -name "rcS" 2>/dev/null | xargs ls -la 2>/dev/null

# Running services (from init scripts)
find "$EXTRACTED" -path "*/init.d/*" -o -path "*/rc.d/*" 2>/dev/null | \
    xargs grep -l "start\|daemon\|listen" 2>/dev/null
```

### Identify architecture for QEMU

```bash
file "$EXTRACTED/bin/sh" 2>/dev/null
# ARM: "ELF 32-bit LSB executable, ARM"
# MIPS: "ELF 32-bit MSB executable, MIPS"
# x86: "ELF 32-bit LSB executable, Intel 80386"
```

## QEMU Emulation

### User-mode emulation (single binary)

```bash
# Install QEMU static binaries
sudo apt install qemu-user-static

# Copy appropriate static binary into extracted filesystem
cp $(which qemu-arm-static) "$EXTRACTED/usr/bin/"
# or: qemu-mips-static, qemu-mipsel-static, qemu-aarch64-static

# Chroot and execute
sudo chroot "$EXTRACTED" /usr/bin/qemu-arm-static /bin/sh
sudo chroot "$EXTRACTED" /usr/bin/qemu-arm-static /bin/busybox sh
```

### Full system emulation with FirmAE

```bash
# FirmAE: automated firmware emulation
git clone --recursive https://github.com/pr0v3rbs/FirmAE
cd FirmAE && sudo ./download.sh && sudo ./install.sh

# Run emulation
sudo ./run.sh -r <brand> <firmware.bin>
# -r = run, -a = analyze, -d = debug

# Access emulated web interface
# FirmAE outputs the emulated IP address
```

### Network interception during emulation

```bash
# Set up tap interface for capturing traffic
sudo ip tuntap add tap0 mode tap
sudo ifconfig tap0 192.168.100.1 up

# Start QEMU with tap networking
qemu-system-arm -M versatilepb \
    -kernel kernel.img \
    -initrd rootfs.cpio.gz \
    -netdev tap,id=net0,ifname=tap0,script=no \
    -device virtio-net,netdev=net0 \
    -serial stdio

# Capture on tap interface
tcpdump -i tap0 -w capture.pcap
```

## Entropy Analysis

High entropy = compressed or encrypted data.

```bash
binwalk -E firmware.bin
# Entropy graph:
# ~1.0 = encrypted or compressed (random-looking)
# ~0.7-0.9 = compressed (patterns exist)
# ~0.0-0.5 = plaintext/code

# Save plot (requires matplotlib)
binwalk -E --save firmware.bin
# Creates firmware.bin.png
```

Interpretation:
- **Uniform high entropy block** → encrypted payload (find decryption routine)
- **Rising then flat** → compressed section
- **Low entropy** → code or text data
- **Alternating** → structured data with padding

## Bypassing Encryption

```bash
# Step 1: Identify if firmware is encrypted (high entropy from start)
binwalk -E firmware.bin

# Step 2: Find the decryption stub (low entropy section at the start)
# This is the bootloader that decrypts the main payload

# Step 3: Emulate/run the decryption stub
# Option A: qemu-user-mode on the decryptor binary
# Option B: use Frida/GDB to extract decrypted data at runtime
# Option C: firmware update protocol analysis (many use AES-CBC with static key)

# Step 4: Search for keys in the decryption stub
strings firmware.bin | grep -E "^[A-F0-9]{32}$"  # AES-128 hex key
strings firmware.bin | grep -E "^[A-Za-z0-9+/]{44}=$"  # Base64 AES-256 key
```

## Useful Binwalk Flags for Deep Analysis

```bash
# Hexdiff between two firmware versions to find changes
binwalk -W old_fw.bin new_fw.bin

# Extract with explicit Binwalk bounds; keep logs inside the monitored output tree
mkdir -p ./extracted
binwalk -eM -d 3 -n 5000 -j 268435456 -C ./extracted --verbose firmware.bin \
  >./extracted/binwalk.log 2>&1

# Scan for specific pattern not in default signatures
binwalk -R "\x7FELF\x02\x01\x01" firmware.bin  # 64-bit ELF headers

# Scan with increased block size (for large files)
binwalk --block=8192 firmware.bin

# Disable scan of specific signature
binwalk --disable-extractor firmware.bin
```

## Struct Recovery from NVRAM/Config

```bash
# Many routers store config in /nvram or mtd partitions
# After extraction, parse with:

# Option 1: strings
strings nvram.bin | head -100

# Option 2: binwalk for any embedded structures
binwalk nvram.bin

# Option 3: Python manual parse (common TLV format)
python3 -c "
import struct
data = open('nvram.bin', 'rb').read()
offset = 0
while offset < len(data):
    if data[offset:offset+4] == b'\x00\x00\x00\x00':
        break
    key_end = data.index(b'\x00', offset)
    key = data[offset:key_end].decode('ascii', errors='replace')
    val_end = data.index(b'\x00', key_end + 1)
    val = data[key_end+1:val_end].decode('ascii', errors='replace')
    if key and val:
        print(f'{key} = {val}')
    offset = val_end + 1
"
```
