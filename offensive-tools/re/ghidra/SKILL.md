---
name: ghidra
description: "NSA's open-source reverse engineering suite with disassembler, decompiler, P-Code IL, and Ghidra/Python scripting. Use when statically analyzing malware, firmware, or binaries to understand logic, recover algorithms, apply type information, diff binaries, or run headless batch analysis."
license: MIT
compatibility: "Java 17+; Linux/macOS/Windows; GUI + headless; github.com/NationalSecurityAgency/ghidra"
metadata:
  author: AeonDave
  version: "1.0"
---

# Ghidra

NSA open-source RE suite — disassembler + decompiler + scripting for static analysis.

## Installation

```bash
# Download from https://github.com/NationalSecurityAgency/ghidra/releases
# Requires JDK 17+ (21 recommended)
# Extract and run:
./ghidraRun           # Linux/macOS
ghidraRun.bat         # Windows
```

## Quick Start

1. New Project → Import File → target binary
2. Double-click to open CodeBrowser → **Yes** to auto-analysis
3. Symbol Tree → Functions → double-click to view disassembly + decompiler

## Key Windows

| Window | Purpose |
|--------|---------|
| Symbol Tree | Functions, labels, namespaces, imports, exports |
| Decompiler | C pseudocode of selected function |
| Listing | Assembly/disassembly view |
| Data Type Manager | Struct/enum/typedef definitions |
| Program Trees | Segments and sections |
| Defined Strings | All string references |
| Function Call Graph | Call tree visualization |
| Bytes | Raw hex view |

## Navigation Shortcuts

| Key | Action |
|-----|--------|
| `G` | Go to address/label |
| `L` | Rename symbol/function/variable |
| `T` | Set data type |
| `;` | Add comment |
| `Ctrl+Shift+E` | Search all text in decompiler |
| `Ctrl+Shift+F` | Find references to |
| `F` | Edit function signature |
| `D` | Define data at cursor |
| `P` | Create function |
| `Ctrl+E` | Export to C/header |

## Scripting

### Ghidra Python (Jython — built-in)

```python
# Script Manager → New → Python
# Available globals: currentProgram, currentAddress, monitor, state

from ghidra.program.model.symbol import SourceType

# List all functions
fm = currentProgram.getFunctionManager()
for func in fm.getFunctions(True):
    print(f"{func.getEntryPoint()}: {func.getName()}")

# Find suspicious imports
for func in fm.getExternalFunctions():
    name = func.getName()
    if any(api in name for api in ['VirtualAlloc', 'CreateRemoteThread',
                                    'WriteProcessMemory', 'NtUnmap']):
        refs = getReferencesTo(func.getEntryPoint())
        for ref in refs:
            print(f"  Suspicious: {name} called from {ref.getFromAddress()}")
```

### Search for crypto constants

```python
# Find AES S-box in binary
from ghidra.program.model.mem import MemoryAccessException

aes_sbox = bytes([0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5])
mem = currentProgram.getMemory()
addr = mem.findBytes(currentProgram.getMinAddress(), aes_sbox, None, True, monitor)
while addr is not None:
    print(f"AES S-box at {addr}")
    refs = getReferencesTo(addr)
    for ref in refs:
        func = getFunctionContaining(ref.getFromAddress())
        if func:
            print(f"  Used by {func.getName()}")
    addr = mem.findBytes(addr.add(1), aes_sbox, None, True, monitor)
```

### Rename functions by pattern

```python
# Auto-rename functions that call specific APIs
for func in currentProgram.getFunctionManager().getFunctions(True):
    body = func.getBody()
    calls = getReferencesFrom(func.getEntryPoint())
    for block in body:
        pass
    # Simpler: check decompiled output
    decomp = ghidra.app.decompiler.DecompInterface()
    decomp.openProgram(currentProgram)
    result = decomp.decompileFunction(func, 30, monitor)
    if result and result.getDecompiledFunction():
        code = result.getDecompiledFunction().getC()
        if 'VirtualAlloc' in code and 'WriteProcessMemory' in code:
            func.setName("likely_injector_" + str(func.getEntryPoint()),
                         SourceType.USER_DEFINED)
```

## Headless Analysis

```bash
# Run analysis without GUI
analyzeHeadless /path/to/project ProjectName \
    -import /path/to/binary \
    -postScript MyScript.py \
    -scriptPath /path/to/scripts

# Batch process multiple binaries
analyzeHeadless /path/to/project ProjectName \
    -import /path/to/samples/ \
    -recursive \
    -postScript ExtractStrings.py
```

## Common Workflows

### Malware static analysis

1. Import → auto-analyze
2. **Symbol Tree → Imports**: check suspicious APIs
3. **Defined Strings** → search: `http`, `password`, `cmd`, `exec`
4. **Decompiler** → trace from `main`/entrypoint through key code paths
5. **Cross-references**: on encryption functions, network calls, file operations
6. Create structs for C2 config structures via **Data Type Manager**

### Struct recovery

```
1. Select data in Listing → Right-click → Data → Create Structure
2. Edit fields in Structure Editor → set types, names, array sizes
3. Apply struct to memory: Right-click data → Data → MyStruct
4. Decompiler auto-updates to use struct field names
```

### Function signature override

```
# When decompiler gets calling convention wrong:
1. Right-click function → Edit Function Signature
2. Set calling convention (stdcall, cdecl, fastcall, thiscall)
3. Add/correct parameter types and names
4. Decompiler re-analyzes with correct types
```

### Version tracking (binary diffing)

```
1. Window → Version Tracking
2. Source: older binary, Destination: newer binary
3. Run correlators: Exact Function, Data Match, Reference
4. Review matched/unmatched functions
5. Apply matches to propagate names and types
```

### P-Code analysis

```python
# P-Code is Ghidra's intermediate representation
# Useful for architecture-independent analysis
decomp = ghidra.app.decompiler.DecompInterface()
decomp.openProgram(currentProgram)
func = getFunctionAt(currentAddress)
result = decomp.decompileFunction(func, 30, monitor)
hf = result.getHighFunction()
for block in hf.getBasicBlocks():
    it = block.getIterator()
    while it.hasNext():
        op = it.next()
        print(f"  {op.getSeqnum().getTarget()}: {op.getMnemonic()} {op}")
```

## Resources

| File | When to load |
|------|--------------|
| [references/scripting-guide.md](references/scripting-guide.md) | Ghidra Python/Java script patterns and API reference |
| [references/headless-analysis.md](references/headless-analysis.md) | Batch processing and headless workflow recipes |
