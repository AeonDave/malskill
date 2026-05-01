---
name: autopsy
description: |
  GUI digital forensics platform built on The Sleuth Kit. Use to investigate disk images (.dd/.E01/.img/.vmdk)
  for deleted files, browser history, registry artifacts, keyword matches, file carving, and timeline analysis.
  Fastest way to visually triage a disk image: open image, run ingest modules, search artifacts.
  Supports NTFS, FAT, ext2/3/4, HFS+, APFS. Works on Windows natively; Linux via CLI build.
license: Apache-2.0
compatibility: "Windows (primary GUI). Linux: autopsy-core via apt or build from source. autopsy.com"
metadata:
  author: AeonDave
  version: "2.0"
---

# Autopsy

GUI disk forensics over The Sleuth Kit — deleted files, browser artifacts, registry, keyword search, timeline.

## Installation

```bash
# Windows: download MSI installer from autopsy.com (recommended)

# Linux (Kali)
sudo apt install autopsy    # CLI-only version (browser-based at localhost:9999)

# Linux GUI: requires Java + dependencies
# https://www.autopsy.com/download/

# Launch (Linux CLI version)
autopsy
# Opens: http://localhost:9999/autopsy in browser
```

---

## Quick Start: Open a Disk Image

1. **New Case** → enter case name, examiner, output path
2. **Add Data Source** → select image type:
   - `Disk Image or VM File` — `.dd`, `.raw`, `.E01`, `.vmdk`, `.vhd`
   - `Local Disk` — live disk (write-blocker recommended)
   - `Logical Files` — individual files or directories
3. **Configure Ingest Modules** (see below)
4. Wait for ingest, then explore results in the **Tree** pane

---

## Ingest Modules — What to Enable

| Module | What it finds | Enable for |
|--------|--------------|-----------|
| **Recent Activity** | Browser history, downloads, searches, USB devices | Always |
| **Hash Lookup** | Known-bad/known-good files via hash sets | Always |
| **File Type Identification** | Magic byte file type detection | Always |
| **Keyword Search** | Regex/literal string search across all files | Always |
| **Email Parser** | Outlook PST/OST, mbox email artifacts | Email investigations |
| **Embedded File Extractor** | Files inside ZIP/RAR/Office docs | Always |
| **EXIF Parser** | GPS + metadata from images | Photo investigations |
| **Extension Mismatch Detector** | Files renamed to hide true type | Always |
| **Android Analyzer** | Android DB artifacts | Mobile forensics |
| **Interesting Files** | Pre-defined suspicious file patterns | Always |
| **PhotoRec Carver** | Carve deleted/unallocated files | Deleted file recovery |

**Recommended minimal set for fast triage:**
`Recent Activity` + `File Type Identification` + `Keyword Search` + `Embedded File Extractor` + `PhotoRec Carver`

---

## Navigation: Tree Pane

After ingest, the left tree exposes:

```
Data Sources
└── disk.img
    ├── vol1 (NTFS, 50GB)
    │   ├── $OrphanFiles      ← deleted files with no parent dir
    │   ├── Users/
    │   ├── Windows/
    │   └── ...
Results
├── Extracted Content
│   ├── Bookmarks
│   ├── Cookies
│   ├── Downloads
│   ├── History
│   ├── Installed Programs
│   ├── Recent Documents
│   ├── Recycle Bin
│   ├── Search History
│   └── Web Form Autofill
├── Extension Mismatch Detected
├── Interesting Files
├── Keyword Hits
├── Metadata
└── Tags
Views
├── File Types
│   ├── Images
│   ├── Videos
│   ├── Documents
│   └── Executables
├── Deleted Files
└── File Size
```

---

## Key Workflows

### Find deleted files

```
Views → Deleted Files
# or
Data Sources → vol1 → $OrphanFiles
# Sort by name, extension, or date
```

Right-click → **Extract File(s)** to recover.

### Keyword search

```
Tools → Keyword Search (or press Ctrl+F)
```

Options:
- **Exact Match** — literal string
- **Substring Match** — contains string  
- **Regex** — full regex pattern

```
# Common patterns to search:
flag{.*}
password:
-----BEGIN.*KEY-----
[A-Za-z0-9+/]{20,}=    # base64
\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b   # IP addresses
```

Results appear under `Results → Keyword Hits`. Click entry → view source file + highlighted match.

### Browser artifact analysis

```
Results → Extracted Content → History
Results → Extracted Content → Downloads  
Results → Extracted Content → Bookmarks
Results → Extracted Content → Cookies
Results → Extracted Content → Search History
```

Filter by date. Sort by timestamp to reconstruct activity sequence.

### Timeline analysis

```
Tools → Timeline (clock icon on toolbar)
```

- Zoom to specific time range
- Filter by event type: File System / Web Activity / Registry / Log
- Pinpoint when suspicious files were created/accessed
- Correlate browser activity with file system events

### File type mismatch detection

```
Results → Extension Mismatch Detected
```

Files where magic bytes don't match extension — hidden data technique.

```bash
# CLI equivalent to find mismatches
file /path/to/extracted/* | grep -v "matches"
```

### File carving (PhotoRec integration)

Autopsy runs PhotoRec automatically when module enabled. Results appear under:
```
Results → Extracted Content → Carved Files
# or
Data Sources → vol1 → $CarvedFiles
```

Useful for: JPEGs/PNGs hidden in unallocated space, ZIP archives, PDF fragments.

---

## Registry Analysis

Autopsy extracts registry hives from Windows images automatically.

```
Data Sources → vol1 → Windows/System32/config/
# SAM, SYSTEM, SECURITY, SOFTWARE hives available as files

# Extract hive, then analyze with:
# - RegRipper (regripper.exe / rip.pl)
# - Registry Explorer (Eric Zimmermann tools)
# - python-registry (Python parsing)
```

Common registry paths to check:
```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run    # startup
HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run    # user startup
HKLM\SYSTEM\CurrentControlSet\Services               # services
HKLM\SAM\SAM\Domains\Account\Users                  # user accounts
NTUSER.DAT\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs  # recent files
NTUSER.DAT\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RunMRU       # run dialog history
```

---

## Searching for Hidden/Embedded Data

### Stegano indicators

```
# Look for unusual files in image:
Views → File Types → Images
# Sort by size — oversized images may contain hidden data
# Cross-check with steghide/zsteg/stegsolve after extraction
```

### Encrypted or compressed containers

```
Results → Extracted Content (look for .zip, .7z, .rar, .veracrypt)
# or keyword search for "PK" (ZIP magic), "Rar!" (RAR magic), "7z" (7zip magic)
```

### NTFS Alternate Data Streams

Autopsy doesn't surface ADS directly — use Sleuth Kit CLI:

```bash
# After finding target volume offset
fls -o 2048 disk.img | grep "::"   # ADS entries have "::" in name
icat -o 2048 disk.img <inode>:<stream> > ads_content
```

---

## Export and Reporting

```
# Export files
Right-click file → Extract File(s)

# Tag files for report
Right-click → Add File Tag → Notable Item

# Generate report
Tools → Generate Report
# Select: HTML Report / Excel / KML / etc.
# Include: Tagged files / Keyword hits / All results
```

---

## CLI Mode (Linux)

```bash
# Launch web UI
autopsy &
# Access at http://localhost:9999/autopsy

# CLI: create case + add image via TSK directly (see sleuth-kit skill)
mmls disk.img
fls -r -o 2048 disk.img | grep -i "flag\|secret"
icat -o 2048 disk.img <inode> > extracted_file
```

---

## Integration

| Tool | Use case |
|------|---------|
| `sleuth-kit` | CLI complement for scriptable extraction |
| `binwalk` | Analyze extracted binaries/firmware |
| `volatility3` | After extracting memory dump artifact |
| `wireshark` | After finding .pcap in disk image |
| `hashcat` | Crack password hashes found in SAM/registry |
| `steghide` / `zsteg` | Check images found for steganography |
| `strings` | Quick scan of extracted files |

## Resources

| File | When to load |
|------|--------------|
| `references/` | Ingest module selection guide, registry artifact map, timeline interpretation |
