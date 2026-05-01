---
name: sleuth-kit
description: |
  CLI file-system forensics toolkit for analyzing disk images (.dd/.img/.E01/.vmdk). Enumerates
  partitions, walks file systems, recovers deleted files, extracts inodes, builds MACB timelines,
  and carves data — all scriptable from the command line. Use on any raw disk image to find files,
  recover deleted content, analyze NTFS/ext4/FAT structures, and build investigation timelines.
license: IPL-1.0
compatibility: "Linux/macOS/Windows. apt install sleuthkit. sleuthkit.org"
metadata:
  author: AeonDave
  version: "2.0"
---

# The Sleuth Kit (TSK)

Scriptable CLI disk forensics — partitions, file systems, deleted file recovery, timeline generation.

## Installation

```bash
# Debian/Ubuntu/Kali
sudo apt install sleuthkit

# macOS
brew install sleuthkit

# Verify
mmls --version
```

---

## Core Commands Overview

| Command | Purpose |
|---------|---------|
| `mmls` | List partitions / volume layout |
| `fsstat` | File system metadata and geometry |
| `fls` | List files and directories (including deleted) |
| `istat` | Inode metadata for a specific file |
| `icat` | Extract file content by inode number |
| `ils` | List inodes |
| `blkcat` | Dump raw data blocks |
| `blkls` | List unallocated blocks |
| `blkstat` | Stats on a specific block |
| `tsk_recover` | Bulk recover deleted files |
| `tsk_gettimes` | Extract MACB timestamps |
| `mactime` | Build timeline from bodyfile |
| `img_stat` | Image format info |
| `sigfind` | Find block signatures (file carving assist) |

---

## Step 1: Partition Layout

```bash
# Show partition table (works on .dd, .img, .E01, .vmdk, .raw)
mmls disk.img

# Example output:
# Slot    Start        End          Length       Description
# 000:  Meta        0000000000   0000000000   0000000001   Safety Table
# 002:  000:000     0000002048   0001026047   0001024000   Linux (0x83)

# Note the 'Start' sector for each partition — needed for offset calculations
```

**Sector size** is usually 512 bytes. Offset in bytes = Start_sector × 512.

---

## Step 2: File System Info

```bash
# Inspect file system (use offset from mmls)
fsstat -o 2048 disk.img

# Key output fields:
#   File System Type: ext4 / NTFS / FAT32
#   Last Mount Point: /
#   Block Size: 4096
```

---

## Step 3: List Files (including deleted)

```bash
# List all files recursively with inode numbers
fls -r -o 2048 disk.img

# Include deleted files (marked with * prefix)
fls -r -o 2048 disk.img | grep "^\*"    # deleted entries only
fls -r -o 2048 disk.img | grep -v "^\*" # allocated entries only

# Show full paths (useful for bodyfile generation)
fls -r -p -o 2048 disk.img

# Filter for specific names
fls -r -o 2048 disk.img | grep -i "flag\|secret\|password\|\.txt\|\.docx"

# List directory only (no recursion)
fls -o 2048 disk.img 2   # inode 2 = root on ext

# NTFS: list specific directory inode
fls -o 2048 disk.img 5   # inode 5 = root on NTFS
```

**Output format:**
```
r/r 12:  filename.txt       (r = regular file, allocated)
r/r * 13: deleted.txt       (* = deleted, may be recoverable)
d/d 14:  dirname/           (d = directory)
```

---

## Step 4: Extract Files by Inode

```bash
# Extract file content using inode number
icat -o 2048 disk.img 12 > recovered_file.txt

# Extract deleted file (if blocks not reallocated)
icat -o 2048 disk.img 13 > deleted_recovered.txt

# View content inline
icat -o 2048 disk.img 12 | strings -n 6

# Detect file type
icat -o 2048 disk.img 12 | file -

# Dump binary safely
icat -o 2048 disk.img 12 | xxd | head -20
```

---

## Step 5: Inode Metadata

```bash
# Show full metadata for an inode (timestamps, size, blocks used)
istat -o 2048 disk.img 12

# MACB timestamps from istat:
#   Modified: file content last changed
#   Accessed: file last read
#   Changed:  metadata last changed (inode)
#   Born:     file creation time (if supported)
```

---

## Step 6: Bulk File Recovery

```bash
# Recover all deleted files to output directory
tsk_recover -o 2048 disk.img recovered_files/

# Recover allocated + deleted (all)
tsk_recover -a -o 2048 disk.img all_files/

# NTFS-specific (handle ADS)
tsk_recover -o 2048 -e disk.img recovered_files/
```

---

## Step 7: Timeline Generation

```bash
# Build bodyfile (MACB timestamps for every inode)
fls -r -m / -o 2048 disk.img > bodyfile.txt

# Convert bodyfile to sorted timeline
mactime -b bodyfile.txt > timeline.txt

# Filter by date range
mactime -b bodyfile.txt -d 2024-01-01 -D 2024-12-31 > timeline_2024.txt

# Sort timeline by date
sort -t'|' -k1 timeline.txt | head -50

# Find activity spikes
grep "2024-03-15" timeline.txt
```

**Bodyfile format (mactime compatible):**
```
MD5|name|inode|mode_as_string|UID|GID|size|atime|mtime|ctime|crtime
```

---

## NTFS-Specific Tricks

```bash
# List Alternate Data Streams
fls -o 2048 disk.img | grep "::"

# Extract ADS content
icat -o 2048 disk.img <inode>:<stream_name>

# Example: extract ADS named "hidden" from inode 34
icat -o 2048 disk.img 34:hidden > ads_content.bin

# $MFT parsing
ils -o 2048 disk.img | head -20   # list all inodes

# Extract $MFT directly
icat -o 2048 disk.img 0 > MFT.raw   # inode 0 = $MFT on NTFS
```

---

## Searching Raw Blocks

```bash
# Find string pattern in unallocated space
blkls -o 2048 disk.img | strings | grep -i flag

# Find pattern in all blocks (allocated + unallocated)
blkls -a -o 2048 disk.img | strings | grep -i "password\|key\|flag"

# Find file magic bytes (e.g., PNG: 89504E47)
sigfind -b 512 89504E47 disk.img

# Dump specific block for inspection
blkcat -o 2048 disk.img 1234 | xxd | head -30
```

---

## Common Challenge Workflows

### Find flag in disk image

```bash
# 1. Check partitions
mmls disk.img

# 2. List all files (including deleted)
fls -r -o 2048 disk.img | grep -i "flag\|\.txt\|secret"

# 3. Extract by inode
icat -o 2048 disk.img <INODE> > flag.txt
cat flag.txt
```

### Recover deleted file

```bash
# 1. List deleted files
fls -r -o 2048 disk.img | grep "^\* "

# 2. Note inode (e.g., "r/r * 42: deleted_secret.txt")
icat -o 2048 disk.img 42 > recovered.txt

# OR bulk recover all deleted
tsk_recover -o 2048 disk.img recovered/
ls -la recovered/
```

### Find hidden file in unallocated space

```bash
# Search unallocated blocks for magic bytes
sigfind -b 512 FFD8FF disk.img   # JPEG
sigfind -b 512 89504E47 disk.img  # PNG
sigfind -b 512 504B0304 disk.img  # ZIP

# Find strings in unallocated
blkls -o 2048 disk.img | strings -n 8 | grep -iE "flag|CTF|secret|pass"
```

### Build timeline and find anomalous activity

```bash
fls -r -m / -o 2048 disk.img > bodyfile.txt
mactime -b bodyfile.txt > timeline.txt
# Look for suspicious file creation/modification clusters
grep "interesting_date" timeline.txt
```

### Multiple partition image

```bash
# Get all partitions
mmls disk.img
# Analyze each non-meta partition
fsstat -o 2048 disk.img    # partition 1
fsstat -o 1026048 disk.img  # partition 2
fls -r -o 2048 disk.img
fls -r -o 1026048 disk.img
```

---

## Integration

| Tool | Use case |
|------|---------|
| `autopsy` | GUI front-end over TSK for visual investigation |
| `volatility3` | Memory analysis after disk artifacts identified |
| `file` / `xxd` | Identify and inspect extracted files |
| `binwalk` | Carve embedded files from extracted binaries |
| `foremost` / `scalpel` | File carving from raw image blocks |
| `strings` | Quick scan of extracted file content |

## Resources

| File | When to load |
|------|--------------|
| `references/` | Offset calculation guide, NTFS ADS tricks, carving recipes |
