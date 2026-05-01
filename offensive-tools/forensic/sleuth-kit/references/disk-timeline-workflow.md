# Sleuth Kit — Deep Reference

## Offset Calculation

Partition offset in bytes = `Start_sector × sector_size`

Sector size is almost always 512 bytes. Find Start_sector from `mmls` output.

```bash
mmls disk.img
# Example output:
# 002:  000:000  0000002048  0001026047  0001024000  Linux (0x83)
#                ^ Start=2048

# Offset in bytes:
python3 -c "print(2048 * 512)"   # = 1048576

# Use with all TSK commands:
fls -o 2048 disk.img
fsstat -o 2048 disk.img
```

---

## File System Type Reference

| FS type | fsstat output | Notes |
|---------|---------------|-------|
| NTFS | `File System Type: NTFS` | Windows; use inode 0 for $MFT |
| ext4 | `File System Type: Ext4` | Linux; root inode = 2 |
| FAT32 | `File System Type: FAT32` | USB/SD; no inode concept |
| exFAT | `File System Type: exFAT` | Large USB |
| HFS+ | `File System Type: HFS+` | macOS |
| APFS | via Autopsy/libfsapfs | macOS Big Sur+ |

```bash
# Check FS type
fsstat -o 2048 disk.img | head -3
```

---

## ext4 Journal Recovery

```bash
# Locate journal inode (usually inode 8)
istat -o 2048 disk.img 8

# Dump raw journal
icat -o 2048 disk.img 8 > journal.raw

# Analyze with ext4magic (more powerful for ext4 undelete)
sudo apt install ext4magic
ext4magic disk.img -a $(date -d "2 hours ago" +%s) -f /     # recover last 2h
ext4magic disk.img -r -d recovered/   # bulk recover
```

---

## FAT32/exFAT Specifics

```bash
# FAT has no real inodes — fls uses sequential allocation units
fls -o 2048 fat_disk.img

# Deleted entries: marked with 0xE5 in directory entry
fls -r -o 2048 fat_disk.img | grep "^\*"

# Recover by reallocated clusters (use photorec/foremost for carving)
foremost -i fat_disk.img -o carved_output/
```

---

## NTFS Deep Dive

```bash
# $MFT — master file table (inode 0)
icat -o 2048 disk.img 0 > MFT.raw
# Parse with python-ntfs or mftdump.py

# $Bitmap — track allocated/unallocated blocks
icat -o 2048 disk.img 6 > bitmap.raw

# $LogFile — NTFS transaction journal (recent changes even after deletion)
icat -o 2048 disk.img 2 > logfile.raw

# $UsnJrnl — USN change journal (file create/modify/delete history)
icat -o 2048 disk.img -s 2 > usnjrnl.raw   # $J stream
# Parse: python3 -c "import mft; ..."  or use usnjrnl.py

# Alternate Data Streams
fls -o 2048 disk.img | grep "::"
icat -o 2048 disk.img <inode>:<stream>

# $Recycle.Bin
fls -r -o 2048 disk.img | grep -i "recycle\|\$R\|\$I"
```

---

## File Carving Integration

When file content is lost (blocks overwritten) but structure is gone, use carvers:

```bash
# foremost (by file type)
sudo apt install foremost
foremost -i disk.img -o carve_output/ -c /etc/foremost.conf

# Carve specific types only
foremost -t jpg,png,zip,pdf -i disk.img -o carve_output/

# scalpel (faster, configurable)
sudo apt install scalpel
scalpel disk.img -o scalpel_output/

# photorec (GUI/CLI, many file types)
sudo apt install testdisk   # includes photorec
photorec disk.img           # interactive

# binwalk (firmware/embedded images)
binwalk -e disk.img -C binwalk_output/
```

---

## Timeline: Timezone Normalization

```bash
# mactime outputs in local timezone of analysis machine
# Force UTC
TZ=UTC mactime -b bodyfile.txt > timeline_utc.txt

# Force specific timezone
TZ=America/New_York mactime -b bodyfile.txt > timeline_ny.txt

# Multi-source timeline merge (disk + memory):
# 1. TSK bodyfile
fls -r -m / -o 2048 disk.img > disk_bodyfile.txt
# 2. Volatility shimcache as bodyfile (manual)
# 3. mactime merges multiple bodyfiles
mactime -b disk_bodyfile.txt -b mem_bodyfile.txt > merged_timeline.txt
```

---

## E01 Image Support

```bash
# ewf-tools for E01 on Linux
sudo apt install libewf-dev ewf-tools

# Mount E01 to use with TSK
sudo ewfmount image.E01 /mnt/ewf/
# Now use /mnt/ewf/ewf1 as disk image
mmls /mnt/ewf/ewf1
fls -r -o 2048 /mnt/ewf/ewf1

# Convert E01 → raw dd (for tool compatibility)
ewfexport image.E01 -t output -f raw
mv output.raw output.dd

# Verify E01 integrity
ewfverify image.E01
```

---

## Encrypted Volume Detection

```bash
# Detect BitLocker (NTFS + BitLocker header)
fsstat -o 2048 disk.img | grep -i "BitLocker\|FVE"
mmls disk.img   # look for partition type 0x27 (recovery) or unusual sizes

# VeraCrypt containers
file suspected_container.bin   # "data" or encrypted blob
# Attempt with known password:
veracrypt --text --mount suspected_container.bin /mnt/tc --password "password"

# LUKS (Linux encryption)
file disk.img   # "LUKS encrypted file"
cryptsetup open disk.img unlocked_vol --type luks --key-file keyfile
mount /dev/mapper/unlocked_vol /mnt/luks
```

---

## Quick Reference: Common Inodes

| NTFS Inode | Object |
|-----------|--------|
| 0 | `$MFT` — master file table |
| 1 | `$MFTMirr` — MFT backup |
| 2 | `$LogFile` — NTFS transaction log |
| 5 | `.` root directory |
| 6 | `$Bitmap` — allocation bitmap |
| 8 | `$BadClus` — bad cluster list |
| 9 | `$Secure` — security descriptors |
| 10 | `$UpCase` — uppercase table |

| ext2/3/4 Inode | Object |
|---------------|--------|
| 1 | bad blocks |
| 2 | root directory |
| 8 | journal |
| 11 | first user inode |
