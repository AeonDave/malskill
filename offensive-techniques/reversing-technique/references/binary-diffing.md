# Binary Diffing and Symbol Recovery

Load after `triage.md` when comparing two versions of the same binary or recovering symbols in stripped libraries.

---

## Category 1: Decision Tree

```
Two binary versions (same target)?
  └── Yes → Binary diff workflow (§2)
        ├── IDA available → BinDiff (§2.3)
        └── No IDA → radiff2 + Ghidra VT (§2.1, §2.2)

Stripped binary with unknown symbols?
  └── Known library (libc, OpenSSL, zlib, etc.)?
        ├── Yes → FLIRT signatures (§3.1) or Ghidra FID (§3.2)
        └── No → GoReSym / language-specific (→ languages.md)

Stripped binary, origin partially known?
  └── Have the original .a / .o files?
        ├── Yes → Build FLIRT sig from .a (§3.1)
        └── No → Ghidra SigKit from a known clean binary (§3.3)
```

---

## Category 2: Binary Diff (Two Versions)

### 2.1 radiff2 (radare2, CLI-first)

```bash
# Basic diff: changed bytes
radiff2 old_binary new_binary

# Function-level diff with call graph (output as dot)
radiff2 -g main old_binary new_binary | dot -Tpng -o diff.png

# Code diff mode: show changed instructions
radiff2 -C old_binary new_binary

# JSON output for scripting
radiff2 -j old_binary new_binary | python3 -m json.tool | head -80
```

**Focus strategy:**
1. Run `radiff2 -C` → note function names with the most changed basic blocks
2. Load both versions in `radare2` or Ghidra in side-by-side windows
3. Priority: functions where an `if` or bounds check was added (typical security patch)

### 2.2 Ghidra Version Tracking (VT)

Version Tracking correlates functions between two Ghidra projects and scores matches:

```
1. Import both binaries as separate Ghidra projects
2. Tools → Version Tracking → New Session
   - Source: old (vulnerable) binary
   - Destination: new (patched) binary
3. Run correlators in order:
   a. Exact Symbol Name Match (score 10.0) — high confidence
   b. Exact Function Body Match (score 10.0) — identical functions
   c. Duplicate Function Body Match — copies
   d. Reference Address Correlator — propagates via call graph
   e. Data Match Correlator — string-anchored matches
4. Accept high-score matches (≥ 8.0) automatically; review 5.0–7.9 manually
5. Filter for UNMATCHED functions in destination → these are new or heavily changed
```

**What to look for in changed functions:**
- Added `if (len > MAX)` → likely buffer overflow fix
- Added null pointer check before dereference → use-after-free or null-deref fix
- Added `free(ptr)` path → memory leak fix
- Changed loop termination condition → off-by-one fix
- New call to sanitize/escape function → injection fix

### 2.3 BinDiff (IDA Pro required)

```
1. Analyze both binaries in IDA Pro → export .idb/.i64
2. BinDiff → Diff Databases → select old.idb and new.idb
3. Functions view: sorted by similarity score (0.0 = identical, 1.0 = completely different)
4. Drill into functions with similarity 0.3–0.7 (changed but recognizable)
5. Side-by-side graph diff → colored edges show added/removed basic blocks
```

**BinDiff CLI (for automation):**
```bash
bindiff --primary old.idb --secondary new.idb --output_dir ./diff/
# Produces .BinDiff SQLite database
python3 - << 'EOF'
import sqlite3, sys
db = sqlite3.connect('diff.BinDiff')
cur = db.execute('''
  SELECT f1.name, f2.name, similarity, confidence
  FROM function f1 JOIN function f2 ON f1.id = f2.primaryid
  WHERE similarity < 0.9
  ORDER BY similarity ASC LIMIT 30
''')
for row in cur: print(row)
EOF
```

---

## Category 3: Symbol Recovery in Stripped Binaries

### 3.1 FLIRT signatures (IDA Pro)

FLIRT (Fast Library Identification and Recognition Technology) matches functions against pre-built signature libraries.

**Use pre-built sigs (IDA):**
```
IDA → View → Open Subviews → Signatures → Insert
# IDA ships with sigs for common MSVC/GCC/Clang runtimes
# Community sigs: https://github.com/push0ebp/sig-database
```

**Build custom FLIRT sig from static library:**
```bash
# FLAIR tools (shipped with IDA): pelf/pcf/plb + sigmake
# For Linux .a (ar archive):
pelf libssl.a libssl.pat          # Parse ELF objects → .pat pattern file
sigmake libssl.pat libssl.sig     # Compile → .sig

# Resolve collisions: edit libssl.exc (auto-generated), re-run sigmake
sigmake -n "OpenSSL 3.0" libssl.pat libssl.sig

# Install: copy libssl.sig to <IDA>/sig/pc/
```

**Build sig from shared library:**
```bash
# Use plb (for PE/COFF) or pelf (ELF)
pelf libssl.so libssl.pat
sigmake libssl.pat libssl.sig
```

### 3.2 Ghidra Function ID (FID)

```
1. Ghidra → Tools → Function ID → Create new FID database
   - Name: "OpenSSL-3.0-x86_64"
   - Save as: openssl_3.0.fidb

2. Populate from known binary (same lib, clean version):
   - Open known binary in Ghidra (with symbols)
   - Tools → Function ID → Populate FID database
   - Select your .fidb, confirm
   
3. Apply to stripped binary:
   - Open stripped binary
   - Tools → Function ID → Search FID databases
   - Select .fidb → Apply results (confidence threshold: 1.0 minimum for auto-accept)

4. Review matches in Functions window — tagged symbols update decompiler output
```

**Community FID databases:**
- Ghidra-extensions repo: various libc, MSVC CRT, OpenSSL versions

### 3.3 Ghidra BSim (large-scale similarity search)

For deduplicating or matching across many binaries (large codebase):
```
Tools → BSim → Create H2 Database (or PostgreSQL for large scale)
Ingest known binaries with symbols → then query stripped target
Results show similar functions across different compilation units
```

### 3.4 SigKit (community Ghidra script)

Generates Ghidra function ID entries from loaded binaries without the full FID workflow:
```
# Install via Ghidra Script Manager
# Script: SigKit.java or via extension
# Usage: run on a symbolized binary → export signature DB → apply to stripped target
```

---

## Category 4: Practical Tips

**When FLIRT/FID recovers names but something looks off:**
- The lib version may differ — check `strings binary | grep -i "openssl\|version"` to pin the exact version
- Inlined functions won't match — their bodies are absorbed into callers; this is expected

**When diffing without any symbols:**
- Use string anchors: find a unique string in old binary → locate the same string in new binary → compare surrounding functions
- Export tables (DLLs/SOs): exported function offsets are usually stable; diff by export name

**When the patch adds a new function not in the old binary:**
- Ghidra VT shows it as UNMATCHED in the destination
- Check its call sites: it is often a new sanitizer called from an existing function

**Automation stub (Python + radiff2 JSON):**
```python
import subprocess, json, sys

old, new = sys.argv[1], sys.argv[2]
result = subprocess.run(['radiff2', '-j', old, new], capture_output=True, text=True)
data = json.loads(result.stdout)

for entry in data.get('diff', []):
    if entry.get('type') == 'changed':
        print(f"Changed: {entry.get('name', '?')} offset={hex(entry.get('addr', 0))}")
```

---

## Category 5: Windows Update acquisition for n-day patch diffing

The diff workflows above assume you already have the two versions. For a Microsoft Patch-Tuesday n-day, obtaining and reconstructing the two full binaries is the hard part — extracted patch files are **deltas, not PEs**.

### Get the update

- Microsoft Update Catalog (`catalog.update.microsoft.com`), search `YYYY-MM <build> x64 cumulative` (e.g. `2024-06 22H2 x64 cumulative`); download the `.msu`.
- Shortcut for a single binary: **Winbindex** (`winbindex.m417z.com`) links direct downloads of specific file versions, skipping the whole delta dance below.

### Extract

```powershell
expand.exe -F:* update.msu .\ext\            # -> WSUSSCAN.cab + <name>_PSFX.cab + .xml
expand.exe -F:* .\ext\*_PSFX.cab .\patch\    # -> component-store tree (slow: tens of thousands of files)
```

Component folders are prefixed by platform (`amd64`/`x86`/`wow64`/`msil`) and hold differential subfolders:
- `f` — **forward** delta (base `.1` -> this patch level)
- `r` — **reverse** delta (this patch level -> base `.1`)
- `n` — **null** delta (a whole new file, just compressed; apply to an empty buffer)

### Reconstruct full binaries (deltas are not PEs)

A file under `f`/`r`/`n` is a delta: 4-byte little-endian **CRC32** of the body, then `PA30` magic at **offset 4** (legacy `PA19`). Apply with `msdelta.dll!ApplyDeltaB`; the standard tool is wumb0's `delta_patch.py` (`-n` null, `-l` legacy). To produce two diffable versions from one on-disk file, **reverse then forward**:

```powershell
# find a delta already staged on a live 1:1 host if you don't want to extract two full months
Get-ChildItem -Recurse C:\Windows\WinSxS\ | ? { $_.Name -eq "ntoskrnl.exe" }
python delta_patch.py -i ntoskrnl.exe -o ntoskrnl.old.exe .\r\ntoskrnl.exe <prev-month>\f\ntoskrnl.exe
python delta_patch.py -i ntoskrnl.exe -o ntoskrnl.new.exe .\r\ntoskrnl.exe <this-month>\f\ntoskrnl.exe
```

Verify each output hash against the `<sha256>` in the paired `.manifest` before diffing. Then feed `ntoskrnl.old.exe`/`.new.exe` into §2 (BinDiff/Ghidra VT/`ghidriff`).

### High-value binary targets

Prioritize by historical LPE/RCE density: `ntoskrnl.exe`, `win32k*.sys`/`win32kfull.sys` (LPE), `afd.sys` (LPE), `clfs.sys` (recurrent 0-day LPE), `http.sys` (RCE), `srv2.sys` (SMB RCE), `ksecdd.sys`, `localspl.dll`/`spoolsv.exe` (spooler), `cldflt.sys`, `mskssrv.sys`. A patched function that adds a bounds/return-value/`WAIT_OBJECT_0` check is the usual fix site.

---

## Tool citations

- `radare2` / `radiff2` — CLI binary diffing, graph diff output
- `ghidra` — Version Tracking, Function ID, BSim; `ghidriff` for headless CLI diff reports (`--json-format` for downstream analysis) — see `offensive-tools/rev/ghidra`
- `IDA Pro` + BinDiff — high-fidelity function matching (commercial); Diaphora as the free IDA/Ghidra alternative
- FLAIR tools (`pelf`, `sigmake`) — build FLIRT sigs from static libs (ships with IDA)
- `expand.exe` + `delta_patch.py` (`msdelta!ApplyDeltaB`) — Windows Update MSU/CAB extraction and delta reconstruction
- `strings`, `nm` — quick anchoring before formal diff
