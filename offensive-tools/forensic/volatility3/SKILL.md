---
name: volatility3
description: "Auth/lab ref: Volatility3 memory forensics; process, module, network, registry, file, and suspicious-artifact triage from RAM images."
license: VSL-1.0
compatibility: "Python 3.6+; Linux/macOS/Windows."
metadata:
  author: AeonDave
  version: "2.2"
---

# Volatility 3

Memory forensics — extract processes, network state, credentials, files, and malware artifacts from RAM images.

## Installation

```bash
pip install volatility3
# or
git clone https://github.com/volatilityfoundation/volatility3 && cd volatility3 && pip install -e .

# Verify
python3 vol.py --help

# Alias (convenience)
alias vol='python3 /path/to/volatility3/vol.py'
```

## Symbol Tables (Windows)

Volatility 3 auto-downloads symbol tables for most Windows versions. If offline:

```bash
# Download ISF symbol packs from:
# https://github.com/volatilityfoundation/volatility3/releases (windows.zip, mac.zip, linux.zip)
# Extract to: volatility3/volatility3/symbols/

# Verify symbols available
python3 vol.py -f memory.raw isfinfo
```

---

## Base Syntax

```bash
python3 vol.py -f <memory_image> <plugin>
python3 vol.py -f memory.raw windows.pslist   # Windows plugin
python3 vol.py -f memory.raw linux.pslist     # Linux plugin
```

Output to file:
```bash
python3 vol.py -f memory.raw windows.pslist > pslist.txt 2>/dev/null
```

---

## Windows Plugins — Full Reference

### Process Analysis

```bash
# List processes (flat, fast)
python3 vol.py -f memory.raw windows.pslist

# Process tree (shows parent/child relationships)
python3 vol.py -f memory.raw windows.pstree

# Process scan (finds hidden/unlinked processes)
python3 vol.py -f memory.raw windows.psscan

# Compare pslist vs psscan — differences = hidden processes
diff <(python3 vol.py -f memory.raw windows.pslist 2>/dev/null | awk '{print $2}' | sort) \
     <(python3 vol.py -f memory.raw windows.psscan 2>/dev/null | awk '{print $2}' | sort)

# Detailed process info (PID, PPID, handles, threads, path)
python3 vol.py -f memory.raw windows.cmdline     # command line of each process
python3 vol.py -f memory.raw windows.dlllist     # DLLs loaded per process
python3 vol.py -f memory.raw windows.handles     # open handles (files, registry, mutexes)

# Filter by PID
python3 vol.py -f memory.raw windows.dlllist --pid 1234
python3 vol.py -f memory.raw windows.handles --pid 1234
```

**Key fields in pslist:**
- `PID` / `PPID` — process and parent ID
- `ImageFileName` — process name (max 15 chars — truncated!)
- `CreateTime` — when process started
- `Offset(V)` — virtual memory address

**Suspicious indicators:**
- `svchost.exe` with no parent `services.exe`
- `explorer.exe` with parent other than `userinit.exe`
- Duplicate `lsass.exe`, `csrss.exe`, `smss.exe`
- Process name with extra space or unicode lookalike

### Network Analysis

```bash
# Active and recently closed connections
python3 vol.py -f memory.raw windows.netstat

# All network artifacts (broader)
python3 vol.py -f memory.raw windows.netscan

# Sort by PID for process correlation
python3 vol.py -f memory.raw windows.netscan 2>/dev/null | sort -k5 -n
```

**Fields:** LocalAddr, LocalPort, ForeignAddr, ForeignPort, State, PID, Owner, Created

### Memory Region Analysis

```bash
# Virtual address descriptors (mapped memory regions per process)
python3 vol.py -f memory.raw windows.vadinfo --pid 1234

# Find VAD regions with executable + write (RWX) — injection indicator
python3 vol.py -f memory.raw windows.vadinfo 2>/dev/null | grep -E "RWX|PAGE_EXECUTE_READWRITE"

# Memory map for a process
python3 vol.py -f memory.raw windows.memmap --pid 1234

# Dump all memory pages of a process
python3 vol.py -f memory.raw windows.memmap --pid 1234 --dump
```

### Code Injection Detection

```bash
# Scan for injected code / process hollowing
python3 vol.py -f memory.raw windows.malfind

# Malfind with dump (extract suspicious regions)
python3 vol.py -f memory.raw windows.malfind --dump --pid 1234

# Output: PID, process name, start address, VAD flags, MZ header bytes
# MZ header in rwx region = classic injected PE
```

**Malfind output pattern — injection:**
```
4608    explorer.exe    0x400000  PAGE_EXECUTE_READWRITE  MZ....
```

### DLL and Module Analysis

```bash
# Loaded DLLs per process
python3 vol.py -f memory.raw windows.dlllist

# Hidden/unlinked DLLs (rootkit indicator)
python3 vol.py -f memory.raw windows.ldrmodules

# Compare ldrmodules vs dlllist — discrepancies = hidden DLL
python3 vol.py -f memory.raw windows.ldrmodules 2>/dev/null | grep "False"

# Kernel modules (drivers)
python3 vol.py -f memory.raw windows.modules
python3 vol.py -f memory.raw windows.modscan   # includes unlinked
```

### Credential Extraction

**v2.28+**: `windows.hashdump`, `windows.cachedump`, and `windows.lsadump` were removed. Use registry hive dump + secretsdump instead.

```bash
# Dump all registry hives from memory to a directory
mkdir hives
python3 vol.py -f memory.raw -o hives windows.registry.hivelist --dump
# Output: hives/registry.SAM.<addr>.hive, registry.SYSTEM.<addr>.hive, registry.SECURITY.<addr>.hive, etc.

# Offline credential extraction (impacket — shell glob expands to actual filename)
secretsdump.py \
  -sam hives/registry.SAM.*.hive \
  -system hives/registry.SYSTEM.*.hive \
  -security hives/registry.SECURITY.*.hive \
  LOCAL
# Output: Administrator:500:aad3b435...:NTHASH:::  LSA secrets, cached domain hashes

# Legacy (Volatility < 2.28 only — will error on 2.28+):
python3 vol.py -f memory.raw windows.hashdump
python3 vol.py -f memory.raw windows.cachedump
python3 vol.py -f memory.raw windows.lsadump
```

**Note**: First run requires internet to fetch the ntkrnlmp symbol pack for the target OS version. Run foreground or in a persistent session — background jobs (e.g. `nohup &`) may be killed when the shell idles.

### Registry

```bash
# List registry hives in memory
python3 vol.py -f memory.raw windows.registry.hivelist

# Print registry key value
python3 vol.py -f memory.raw windows.registry.printkey --key "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"

# Dump full hive (offline parsing with regedit/regripper)
python3 vol.py -f memory.raw windows.registry.hivelist --dump
```

### File Extraction

```bash
# Scan for file objects in memory
python3 vol.py -f memory.raw windows.filescan

# Find specific file
python3 vol.py -f memory.raw windows.filescan 2>/dev/null | grep -i ".exe"
python3 vol.py -f memory.raw windows.filescan 2>/dev/null | grep -i "flag"

# Dump file by virtual address (from filescan output)
python3 vol.py -f memory.raw windows.dumpfiles --virtaddr 0xXXXXXXXXXXXX

# Dump all files (slow on large dumps)
python3 vol.py -f memory.raw windows.dumpfiles

# Dump process executable
python3 vol.py -f memory.raw windows.procdump --pid 1234
```

### Process and Memory Dump

```bash
# Dump full process memory
python3 vol.py -f memory.raw windows.memmap --pid 1234 --dump

# Dump process executable (pe header reconstruction)
python3 vol.py -f memory.raw windows.procdump --pid 1234

# Dump specific DLL from process
python3 vol.py -f memory.raw windows.dlllist --pid 1234 --dump

# Extract strings from dumped memory
strings -n 8 pid.1234.0x400000.dmp | grep -i flag
```

### User and Session

```bash
# Logged-on users / session info
python3 vol.py -f memory.raw windows.sessions
python3 vol.py -f memory.raw windows.getservicesids

# Environment variables per process
python3 vol.py -f memory.raw windows.envars --pid 1234

# Clipboard content
python3 vol.py -f memory.raw windows.clipboard
```

### Other Useful Plugins

```bash
# Scheduled tasks
python3 vol.py -f memory.raw windows.scheduled_tasks

# Services (name, state, binary path)
python3 vol.py -f memory.raw windows.svcscan

# Mutexes (malware often creates unique mutex)
python3 vol.py -f memory.raw windows.handles --pid 1234 2>/dev/null | grep Mutant

# Atoms (message hooks, global vars)
python3 vol.py -f memory.raw windows.atoms

# Detect process hooks
python3 vol.py -f memory.raw windows.ssdt
```

---

## Linux Plugins

```bash
# Supplied custom ISF: -s takes the directory containing the JSON, not the JSON path
python3 vol.py -s /path/to/symbols -f memory.raw linux.pslist.PsList

# Processes and runtime context
python3 vol.py -f memory.raw linux.pslist.PsList
python3 vol.py -f memory.raw linux.pstree.PsTree
python3 vol.py -f memory.raw linux.psscan.PsScan
python3 vol.py -f memory.raw linux.psaux.PsAux
python3 vol.py -f memory.raw linux.envars.Envars

# Network and files
python3 vol.py -f memory.raw linux.sockstat.Sockstat
python3 vol.py -f memory.raw linux.sockscan.Sockscan
python3 vol.py -f memory.raw linux.lsof.Lsof
python3 vol.py -f memory.raw linux.proc.Maps
python3 vol.py -f memory.raw linux.pagecache.Files

# Kernel state and rootkit pivots
python3 vol.py -f memory.raw linux.lsmod.Lsmod
python3 vol.py -f memory.raw linux.malware.hidden_modules.Hidden_modules
python3 vol.py -f memory.raw linux.malware.modxview.Modxview
python3 vol.py -f memory.raw linux.malware.check_modules.Check_modules
python3 vol.py -f memory.raw linux.kmsg.Kmsg
python3 vol.py -f memory.raw linux.tracing.tracepoints.CheckTracepoints
python3 vol.py -f memory.raw linux.tracing.ftrace.CheckFtrace
```

Load [references/linux-rootkit-triage.md](references/linux-rootkit-triage.md) when a Linux dump shows hidden modules or processes, incomplete network listings, kernel taints, tracepoint/ftrace hooks, or a supplied custom ISF.

---

## Investigation Workflows

### Workflow 1: Full Windows triage

```bash
MEM="memory.raw"
vol() { python3 vol.py -f "$MEM" "$@" 2>/dev/null; }

# Phase 1 — baseline
vol windows.pslist > pslist.txt
vol windows.psscan > psscan.txt
vol windows.pstree
vol windows.netscan > netscan.txt
vol windows.cmdline > cmdline.txt

# Phase 2 — anomaly hunt
diff <(awk '{print $2}' pslist.txt | sort) <(awk '{print $2}' psscan.txt | sort)
grep -E "443|8080|4444|1337" netscan.txt        # suspicious ports
grep -E "Temp|AppData|ProgramData" cmdline.txt  # suspicious paths

# Phase 3 — injection check
vol windows.malfind > malfind.txt
grep -E "MZ|PAGE_EXECUTE_READWRITE" malfind.txt

# Phase 4 — credentials (v2.28+: hivelist dump + secretsdump; see Credential Extraction section)
mkdir -p hives; vol -o hives windows.registry.hivelist --dump
secretsdump.py -sam hives/registry.SAM.*.hive -system hives/registry.SYSTEM.*.hive -security hives/registry.SECURITY.*.hive LOCAL

# Phase 5 — artifacts
vol windows.filescan > filescan.txt
grep -iE "flag|secret|password|\.txt|\.docx" filescan.txt
```

### Workflow 2: Find and extract suspicious process

```bash
# 1. Identify suspicious PID
python3 vol.py -f memory.raw windows.psscan 2>/dev/null | grep -i "cmd\|powershell\|wscript"

# 2. Get command line
python3 vol.py -f memory.raw windows.cmdline --pid 1234

# 3. Check injected memory
python3 vol.py -f memory.raw windows.malfind --pid 1234

# 4. Dump process binary
python3 vol.py -f memory.raw windows.procdump --pid 1234

# 5. Check strings in dumped binary
strings -n 8 pid.1234.*.exe | grep -iE "flag|key|pass|http|C2"
```

### Workflow 3: File extraction from memory

```bash
# Find files of interest
python3 vol.py -f memory.raw windows.filescan 2>/dev/null | grep -iE "flag|\.txt|\.zip|interesting"

# Get virtual address from output (3rd column)
# Example: 0xce89890 .\Users\user\Desktop\flag.txt

# Dump it
python3 vol.py -f memory.raw windows.dumpfiles --virtaddr 0xce89890

# If dump produces .dat file, check type
file file.0xce89890.dat
strings file.0xce89890.dat
```

### Workflow 4: Linux credential recovery

```bash
# Bash history from memory
python3 vol.py -f memory.raw linux.bash.Bash 2>/dev/null

# Find interesting env vars
python3 vol.py -f memory.raw linux.envars.Envars 2>/dev/null | grep -iE "pass|key|flag|secret|token"

# Find and recover cached /etc/shadow pages
python3 vol.py -f memory.raw linux.pagecache.Files --find /etc/shadow
python3 vol.py -f memory.raw linux.pagecache.InodePages --find /etc/shadow --dump
```

---

## Quick Reference — Common Incident Patterns

| Goal | Command |
|------|---------|
| Find hidden processes | `windows.psscan` vs `windows.pslist` diff |
| Find C2 connections | `windows.netscan` → look for unusual foreign IPs/ports |
| Find injected shellcode | `windows.malfind` → MZ header in RWX VAD |
| Recover deleted file | `windows.filescan` → `windows.dumpfiles --virtaddr` |
| Dump credentials | v2.28+: `windows.registry.hivelist --dump` → `secretsdump.py LOCAL`; legacy: `windows.hashdump`/`cachedump`/`lsadump` |
| Find target string in memory | `windows.filescan` grep indicator, then `dumpfiles` |
| Bash history | `linux.bash.Bash` |
| Suspicious env var | `linux.envars.Envars` plus parent/child comparison |
| Network connections | `linux.sockstat.Sockstat` / `windows.netscan` |
| Process command line | `windows.cmdline` |

## Resources

| File | When to load |
|------|--------------|
| [references/windows-memory-triage-flow.md](references/windows-memory-triage-flow.md) | Windows symbol troubleshooting, Vol2-to-Vol3 translation, injection, MFT, and registry workflows. |
| [references/linux-rootkit-triage.md](references/linux-rootkit-triage.md) | Custom Linux ISFs, hidden modules, kernel hook attribution, load provenance, C2/process correlation, and environment pivots. |
