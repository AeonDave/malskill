---
name: sleuth-kit
description: "The Sleuth Kit (TSK): command-line file-system forensics toolkit. Use for low-level disk image analysis, file recovery, timeline generation, and file-system metadata inspection when you need precise, scriptable forensic workflows."
license: IPL-1.0
compatibility: "Linux/macOS/Windows builds; CLI and C library. sleuthkit.org"
metadata:
  author: AeonDave
  version: "1.0"
---

# The Sleuth Kit

Low-level, scriptable disk forensics toolkit.

## Quick Start

```bash
# identify partition layout
mmls disk.img

# inspect file system details
fsstat -o <partition_offset> disk.img

# list files recursively with metadata
fls -r -m / -o <partition_offset> disk.img > bodyfile.txt

# build timeline
mactime -b bodyfile.txt > timeline.csv
```

## Core Use Cases

- Recover deleted/hidden files from image-based evidence.
- Inspect inode/metadata directly.
- Create MACB timelines for event reconstruction.
- Feed timelines into broader IR narrative.

## Practical Flow

1. Determine partition boundaries (`mmls`).
2. Validate file system parameters (`fsstat`).
3. Enumerate artifacts (`fls`).
4. Extract target evidence (`icat`, `tsk_recover`).
5. Generate and review timeline (`mactime`).

## Resources

| File | When to load |
|------|--------------|
| `references/disk-timeline-workflow.md` | Offset handling, recovery patterns, and timeline triage |
