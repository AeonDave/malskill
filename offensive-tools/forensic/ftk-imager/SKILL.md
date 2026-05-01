---
name: ftk-imager
description: |
  FTK Imager: forensic acquisition and image viewing tool for disk images, logical files, and memory.
  Use to open and browse .dd/.E01/.img/.vmdk disk images without Autopsy, acquire memory dumps,
  convert image formats, export specific files from images, and verify integrity with hash verification.
  Also provides a free CLI version (ftkimager) for scriptable acquisition.
license: Proprietary (free core edition)
compatibility: "Windows primary GUI. CLI (ftkimager) also available for Linux. exterro.com/ftk-imager"
metadata:
  author: AeonDave
  version: "2.0"
---

# FTK Imager

Disk image browser + acquisition tool — open images, extract files, acquire memory, verify hashes.

## Installation

```bash
# Windows: download FTK Imager from exterro.com/ftk-imager (free registration)
# Install .exe → launches as GUI

# CLI version (Windows + Linux)
# ftkimager.exe (Windows) / ftkimager (Linux) — same flags
# Download: https://accessdata.com/product-download

# Linux CLI: also available as part of some forensic distros (DEFT, REMnux)
```

---

## GUI: Key Use Cases

### Open and browse a disk image

```
File → Add Evidence Item
→ Select Image File
→ Browse to .dd / .E01 / .img / .vmdk / .vhd
→ Image mounts in Evidence Tree on left
```

Navigate the tree to browse partitions and file systems. FTK Imager shows:
- All files (allocated + deleted — deleted shown with red X)
- File metadata (size, timestamps, MD5/SHA1)
- Hex preview of selected file
- Text/image preview pane

### Export files from an image

```
Right-click file or folder in Evidence Tree
→ Export Files...
→ Choose destination
```

Batch export: right-click a directory → Export Files → exports entire subtree.

### Find deleted files

```
Browse to partition root → scroll or look for entries with red X icon
# OR
File → Add Evidence Item → right-click partition → Export Files → includes deleted
```

### Verify image integrity

```
File → Verify Drive/Image
→ Select image → runs MD5 + SHA1 hash → compare with acquisition record
```

### Image format conversion

```
File → Create Disk Image...
→ Source: Existing image
→ Select .dd as output → converts E01 → raw dd
→ or select E01 → converts dd → E01
```

---

## CLI (ftkimager): Scriptable Acquisition and Export

```bash
# Acquire physical disk to E01 image
ftkimager \\.\PhysicalDrive0 output_case --e01 --verify --case-number "2024-001" --examiner "Dave"

# Acquire to raw .dd
ftkimager \\.\PhysicalDrive0 output.dd --verify

# Acquire specific partition
ftkimager \\.\PhysicalDrive0 output --e01 --partition 2

# Verify existing image
ftkimager output.E01 --verify

# List physical devices (Windows)
ftkimager --list-drives

# Acquire memory (volatile RAM dump)
ftkimager \\.\PHYSICALMEMORY memdump.raw --verify

# Export specific file from image by path
ftkimager image.dd --export --data-path "Users\Dave\Desktop\secret.txt" --export-path .
```

---

## Memory Acquisition

```bash
# GUI
File → Capture Memory → select output path → capture

# CLI (Windows, run as admin)
ftkimager \\.\PHYSICALMEMORY memdump.raw --verify

# Output: memdump.raw (raw memory dump)
# Feed to Volatility3 immediately:
python3 vol.py -f memdump.raw windows.pslist
```

---

## Supported Image Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| Raw/DD | `.dd`, `.raw`, `.img` | No compression, universally supported |
| EnCase | `.E01`, `.Ex01` | Compressed, metadata-rich, industry standard |
| SMART | `.s01` | Older EnCase format |
| VMware | `.vmdk` | VM disk — open directly |
| VirtualBox | `.vhd`, `.vhdx` | VM disk |
| AFF | `.aff` | Advanced Forensics Format |

**Conversion priority:** FTK Imager handles all → export to `.dd` for widest tool compatibility.

---

## Hash Verification Workflow

```bash
# After acquisition, FTK Imager generates:
# image.E01 (or .dd)
# image.E01.txt — case notes with MD5/SHA1

# Verify from CLI
ftkimager image.E01 --verify

# Manual hash check
md5sum image.dd
sha256sum image.dd
# Compare with hash in acquisition notes
```

---

## Mounting Images for Analysis

### Mount as read-only drive (Windows GUI)

```
File → Image Mounting
→ Select image
→ Mount Type: Physical & Logical Read Only
→ Drive Letter assigned automatically
```

Now accessible as `F:\` (or assigned letter) — open in Explorer or analyze with tools.

### Mount on Linux (no FTK needed)

```bash
# Mount raw .dd image
sudo losetup -f disk.dd
sudo losetup -a   # find loop device (e.g., /dev/loop0)
sudo mount -o ro,offset=$((2048*512)) /dev/loop0 /mnt/image

# Mount E01 with ewf-tools
sudo apt install libewf-dev ewf-tools
sudo ewfmount image.E01 /mnt/ewf/
sudo mount -o ro,offset=$((2048*512)) /mnt/ewf/ewf1 /mnt/image

# Unmount
sudo umount /mnt/image
sudo ewfunmount /mnt/ewf/
```

---

## E01 Image: Create and Read Without FTK

```bash
# Create E01 from raw dd (using ewfacquire)
ewfacquire -t output_case disk.dd

# Read/convert E01 to dd (using ewfexport)
ewfexport image.E01 -t image -f raw

# Verify E01 integrity (using ewfverify)
ewfverify image.E01

# Mount E01 (ewfmount)
sudo ewfmount image.E01 /mnt/ewf/
```

---

## Common Challenge Workflows

### Open provided disk image and browse

```
GUI: File → Add Evidence Item → Image File → select image
CLI: mount to /mnt/image then use standard tools
```

### Extract specific file from image

```bash
# GUI: navigate to file → right-click → Export Files
# CLI:
ftkimager image.dd --export --data-path "path/to/file.txt" --export-path ./extracted/
```

### Get memory dump from running system (live response)

```bash
# Windows (admin)
ftkimager \\.\PHYSICALMEMORY memdump.raw --verify
# → feed to volatility3
python3 vol.py -f memdump.raw windows.pslist
```

### Convert E01 to dd for broader tool compatibility

```bash
# Using FTK CLI
ftkimager image.E01 converted.dd

# Using ewfexport
ewfexport image.E01 -t converted -f raw
# Output: converted.raw
mv converted.raw converted.dd
```

---

## Integration

| Tool | Use case |
|------|---------|
| `autopsy` | GUI investigation after image acquisition |
| `sleuth-kit` | CLI file system analysis on acquired image |
| `volatility3` | Memory analysis after RAM acquisition |
| `hashcat` | Crack hashes found after extraction |
| `binwalk` | Analyze extracted binary artifacts |
| `strings` / `xxd` | Quick file content inspection |

## Resources

| File | When to load |
|------|--------------|
| `references/` | E01 acquisition parameters, multi-image cases, hash verification workflow |
