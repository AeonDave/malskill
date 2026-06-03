---
name: binaryninja
description: "Auth/lab ref: Commercial reverse engineering platform with decompiler, multi-architecture IL system (LLIL/MLIL/HLIL), and Python scripting API."
license: MIT
compatibility: "Windows/Linux/macOS; x86/x64/ARM/MIPS/PPC/RISC-V; binary.ninja."
metadata:
  author: AeonDave
  version: "1.1"
---

# Binary Ninja

Programmable RE platform — disassembler + decompiler + multi-level IL + Python API.

## Quick Start

1. **File → Open** → target binary
2. Wait for auto-analysis (progress bar at bottom)
3. Navigate: **Functions** list (left) → click to view disassembly
4. Toggle views: `Disassembly` / `HLIL` (decompiler) / `MLIL` / `LLIL` / `Graph`
5. Right-click → **Linear View** or **Graph View**

## Key Views

| View | Purpose |
|------|---------|
| Graph | Control flow graph of current function |
| Linear | Linear disassembly (IDA-style) |
| HLIL | High-Level IL — decompiler (C-like pseudocode) |
| MLIL | Medium-Level IL — variables recovered, stack abstracted |
| LLIL | Low-Level IL — close to assembly, normalized |
| Hex | Raw hex editor |
| Strings | All detected strings |
| Cross References | XREF list for selected symbol |

## Navigation

| Key | Action |
|-----|--------|
| `G` | Go to address or symbol |
| `N` | Rename symbol |
| `Y` | Change type |
| `L` | Change label |
| `/` | Add comment |
| `Tab` | Switch between graph/linear |
| `H` | Toggle between IL levels (LLIL→MLIL→HLIL→Disasm) |
| `X` | Cross references |
| `Ctrl+E` | Edit bytes |
| `P` | Create function at cursor |
| `U` | Undefine |
| `D` | Change data type |
| `Ctrl+Shift+M` | Open script console |

## Intermediate Languages (IL)

Binary Ninja's defining feature — layered IL system:

**LLIL** — Low-Level IL: one-to-one with assembly but normalized. Architecture-independent register/flag access.

**MLIL** — Medium-Level IL: stack variables promoted to named variables; constant propagation; dead store elimination. Good for cross-function analysis.

**HLIL** — High-Level IL: decompiler output. Loops, if/else, switch, and variable declarations recovered. Best for human reading.

```python
# Access different IL layers for a function
func = bv.get_function_at(here)
for block in func.hlil:
    for inst in block:
        print(f"  {inst.address:#x}: {inst}")
```

## Python API (Scripting)

### Basics

```python
# Script console: View -> Script Console (or Ctrl+Shift+M)
# Or headless: import binaryninja; bv = binaryninja.load("/path/to/binary")

# List all functions
for func in bv.functions:
    print(f"{func.start:#x}: {func.name}")

# Get function at address
func = bv.get_function_at(0x401000)
print(func.name, func.start, func.total_bytes)
```

### Find suspicious API calls

```python
suspicious = ['VirtualAlloc', 'CreateRemoteThread', 'WriteProcessMemory',
              'LoadLibrary', 'GetProcAddress', 'connect', 'send']

for func in bv.functions:
    for block in func.hlil:
        for inst in block:
            if inst.operation == HighLevelILOperation.HLIL_CALL:
                target = str(inst.dest)
                for s in suspicious:
                    if s.lower() in target.lower():
                        print(f"  {func.name} @ {inst.address:#x} calls {target}")
```

### Extract strings with cross-references

```python
for s in bv.strings:
    if any(kw in s.value.lower() for kw in ['http', 'password', 'key', 'exec']):
        refs = bv.get_code_refs(s.start)
        for ref in refs:
            func = bv.get_functions_containing(ref.address)
            if func:
                print(f"  '{s.value}' referenced in {func[0].name} @ {ref.address:#x}")
```

### Trace data flow (MLIL)

```python
func = bv.get_function_at(0x401234)
for block in func.mlil:
    for inst in block:
        if inst.operation == MediumLevelILOperation.MLIL_CALL:
            if 'VirtualAlloc' in str(inst):
                if len(inst.params) > 3:
                    prot = inst.params[3]
                    print(f"  VirtualAlloc protect={prot} @ {inst.address:#x}")
```

### Batch analysis (headless)

```python
#!/usr/bin/env python3
"""Headless Binary Ninja analysis."""
import binaryninja

bv = binaryninja.load("/path/to/binary", update_analysis=True)
if bv is None:
    exit(1)
bv.update_analysis_and_wait()

print(f"Functions: {len(bv.functions)}")
print(f"Strings: {len(bv.strings)}")
print(f"Sections: {[s.name for s in bv.sections.values()]}")

for func in bv.functions:
    for ref in func.call_sites:
        callee = bv.get_function_at(ref.mlil.dest.constant)
        if callee and not callee.name.startswith("sub_"):
            print(f"  {func.name} -> {callee.name}")

bv.file.close()
```

## Common RE Workflows

### Malware static triage

1. Open sample → wait for analysis
2. **Strings** view → search for URLs, IPs, registry paths, suspicious keywords
3. **Imports** → check for injection/evasion/network APIs
4. Cross-reference suspicious imports → follow to calling functions
5. Switch to **HLIL** for decompiled view of key functions
6. Rename functions as you identify their purpose

### Identify encryption algorithms

```python
# Look for crypto constants (AES S-box)
aes_sbox = bytes([0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5])
results = bv.find_all_data(bv.start, bv.end, aes_sbox)
for addr in results:
    print(f"  AES S-box found at {addr:#x}")
    refs = bv.get_code_refs(addr)
    for ref in refs:
        print(f"    Referenced from {ref.address:#x}")
```

### Firmware analysis

1. **File → Open with Options** → set architecture and base address manually
2. Use **Strings** and **XREF** to find interesting code paths
3. Supports: ARM, Thumb, MIPS, PPC, RISC-V, x86, x64

## Plugins

```
# Install via Plugin Manager: Edit -> Preferences -> Plugin Manager
# Useful plugins:
# - SigMaker: create IDA-compatible signatures
# - Syscall identifier: annotate syscall numbers
# - binja-msdn: auto-annotate WinAPI parameters
```

## Resources

| File | When to load |
|------|--------------|
| [references/scripting-recipes.md](references/scripting-recipes.md) | Python API recipes for common analysis tasks |
| [references/il-guide.md](references/il-guide.md) | LLIL/MLIL/HLIL operation types and traversal patterns |
