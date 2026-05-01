# FTK Imager — Deep Reference

## E01 Multi-Segment Image Handling

E01 images may be split into multiple segments (`image.E01`, `image.E02`, `image.E03`, ...).

```bash
# FTK Imager GUI: open only the first segment (.E01) — auto-detects rest

# CLI: point to first segment
ftkimager image.E01 --verify   # handles segments automatically

# ewf-tools (Linux): open first segment only
sudo ewfmount image.E01 /mnt/ewf/
ls /mnt/ewf/   # single ewf1 virtual device, segments merged transparently

# List segment info
ewfinfo image.E01    # shows segment count, hash, acquisition details

# Convert multi-segment E01 → single raw dd
ewfexport image.E01 -t output -f raw
# Output: output.raw (single file, can be huge)
```

---

## ewf-tools Reference

```bash
sudo apt install libewf-dev ewf-tools

# Mount E01 as virtual device
sudo ewfmount image.E01 /mnt/ewf/
# Use /mnt/ewf/ewf1 like a disk device

# Info (metadata, case notes, hash)
ewfinfo image.E01

# Verify integrity
ewfverify image.E01

# Export to different format
ewfexport image.E01 -t output -f raw          # → raw dd
ewfexport image.E01 -t output -f ewf          # → new E01
ewfexport image.E01 -t output -f smart        # → Smart/s01

# Acquire from dd → E01
ewfacquire -t output_case disk.dd
```

---

## Encrypted Disk Handling

### BitLocker

```bash
# Detect BitLocker
fsstat -o 2048 disk.img | grep -i "bitlocker\|FVE"
# Or: mmls shows -FVE-FS- partition type

# Mount with password (Linux)
sudo apt install dislocker
dislocker -V disk.img -u "PASSWORD" -- /mnt/bitlocker/
sudo mount -o loop,ro /mnt/bitlocker/dislocker-file /mnt/cleartext/

# Mount with recovery key
dislocker -V disk.img -p "000000-000000-000000-000000-000000-000000-000000-000000" -- /mnt/bitlocker/

# Get recovery key from AD or TPM dump (DPAPI context)
# Windows: manage-bde -protectors C: -get
```

### VeraCrypt / TrueCrypt

```bash
# Open container
veracrypt --text --mount container.bin /mnt/tc --password "PASSWORD"
# Browse /mnt/tc/

# Dismount
veracrypt --text --dismount /mnt/tc
```

### LUKS (Linux)

```bash
file disk.img   # "LUKS encrypted file, ver 1"

# Open with password
sudo cryptsetup open disk.img luks_vol --type luks
sudo mount /dev/mapper/luks_vol /mnt/luks

# Or with keyfile
sudo cryptsetup open disk.img luks_vol --type luks --key-file keyfile.key
```

---

## Memory Acquisition Tools Reference

| Tool | Platform | Notes |
|------|---------|-------|
| **FTK Imager** | Windows GUI + CLI | `\\.\PHYSICALMEMORY` target |
| **winpmem** | Windows CLI | Open source, raw or WinPmem format |
| **DumpIt** | Windows CLI | Single binary, simple usage |
| **avml** | Linux | Open source, LiME-compatible output |
| **LiME** | Linux kernel module | Most complete, requires compilation |
| **osxpmem** | macOS | macOS memory acquisition |

```bash
# winpmem (Windows)
winpmem_mini_x64.exe memdump.raw

# avml (Linux, no kernel module needed)
sudo avml memdump.raw

# LiME (Linux kernel module)
git clone https://github.com/504ensicsLabs/LiME
cd LiME/src && make
sudo insmod lime-*.ko "path=/tmp/memdump.lime format=lime"
# Output: /tmp/memdump.lime → feed to Volatility3 with linux.* plugins
```

---

## Image Format Conversion Reference

| Source | Target | Tool |
|--------|--------|------|
| `.dd` → `.E01` | ewfacquire -f ewf -t output disk.dd |
| `.E01` → `.dd` | ewfexport image.E01 -t output -f raw |
| `.vmdk` → `.dd` | qemu-img convert -O raw disk.vmdk disk.dd |
| `.vhd` → `.dd` | qemu-img convert -O raw disk.vhd disk.dd |
| `.vhdx` → `.dd` | qemu-img convert -O raw disk.vhdx disk.dd |
| `.qcow2` → `.dd` | qemu-img convert -O raw disk.qcow2 disk.dd |

```bash
# qemu-img (universal converter)
sudo apt install qemu-utils
qemu-img convert -O raw source.vmdk output.dd
qemu-img convert -O raw source.vhd output.dd
qemu-img info source.vmdk   # inspect before converting
```

---

## Mounting Images on Linux (No FTK)

```bash
# Raw .dd / .img
OFFSET=$(python3 -c "import subprocess; out=subprocess.check_output(['mmls', 'disk.dd']).decode(); print([l for l in out.split('\n') if 'Linux' in l or 'FAT' in l or 'NTFS' in l][0].split()[2])")
sudo mount -o loop,ro,offset=$((OFFSET*512)) disk.dd /mnt/image

# Or manually:
mmls disk.dd   # note Start sector (e.g. 2048)
sudo mount -o loop,ro,offset=$((2048*512)) disk.dd /mnt/image

# E01
sudo ewfmount image.E01 /mnt/ewf/
sudo mount -o loop,ro,offset=$((2048*512)) /mnt/ewf/ewf1 /mnt/image

# VMDK (VMware)
sudo modprobe nbd
sudo qemu-nbd -c /dev/nbd0 disk.vmdk
sudo mount -o ro /dev/nbd0p1 /mnt/vmdk

# Unmount
sudo umount /mnt/image
sudo qemu-nbd -d /dev/nbd0   # for nbd
```

---

## Hash Verification Chain

```bash
# At acquisition: record hashes
md5sum disk.dd > disk.dd.md5
sha256sum disk.dd > disk.dd.sha256

# Before analysis: verify
md5sum -c disk.dd.md5
sha256sum -c disk.dd.sha256

# FTK Imager CLI verification
ftkimager disk.dd --verify

# E01 built-in: ewfverify
ewfverify image.E01
```

---

## Triage vs. Full Image Decision

| Situation | Approach |
|-----------|---------|
| Full analysis needed | Full physical image (dd or E01) |
| Time-constrained, specific artifact | Logical collection (FTK Imager → Export Files) |
| Live malware present | RAM first, then disk |
| Cloud/remote system | Agent-based acquisition (WinPmem, avml) |
| VM environment | Suspend VM → copy .vmem/.vmdk directly |
| Encrypted disk + known key | Decrypt → image decrypted volume |
