---
name: ghidra
description: "Auth/lab ref: NSA's open-source reverse engineering suite with disassembler, decompiler, P-Code IL, and Ghidra/Python scripting."
license: MIT
compatibility: "Ghidra 12.2: 64-bit JDK 25; Linux/macOS/Windows. PyGhidra: CPython 3.9–3.15; debugger support has a narrower range."
metadata:
  author: AeonDave
  version: "1.1"
---

# Ghidra

NSA open-source RE suite — disassembler + decompiler + scripting for static analysis.

## Installation

```bash
# Download from https://github.com/NationalSecurityAgency/ghidra/releases
# Ghidra 12.2 requires 64-bit JDK 25
# Extract and run:
./ghidraRun           # Linux/macOS
ghidraRun.bat         # Windows
```

The ordinary launcher starts the GUI; use the PyGhidra launcher below for CPython scripts. The 12.2 [setup guide](https://github.com/NationalSecurityAgency/ghidra/blob/Ghidra_12.2_build/GhidraDocs/GettingStarted.md#minimum-requirements) lists Python 3.9–3.15 for PyGhidra and 3.7–3.14 for debugger support; full source builds have separate requirements.

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

### Ghidra Python (PyGhidra, CPython 3)

For Python scripts, start the GUI with `support/pyghidraRun` (Windows: `pyghidraRun.bat`); the launcher offers to install PyGhidra if needed. Ghidra 12 defaults Python scripts to PyGhidra. Select Jython explicitly with `# @runtime Jython` for compatible legacy scripts. See the [12.2 setup guide](https://github.com/NationalSecurityAgency/ghidra/blob/Ghidra_12.2_build/GhidraDocs/GettingStarted.md#pyghidra-mode).

```python
# Script Manager → New → Python
# Available globals: currentProgram, currentAddress, monitor, state

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

## Headless Analysis

```bash
# Run analysis without GUI
pyghidraRun -H /path/to/project ProjectName \
    -import /path/to/binary \
    -postScript MyScript.py \
    -scriptPath /path/to/scripts

# Batch process multiple binaries
pyghidraRun -H /path/to/project ProjectName \
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
from ghidra.app.decompiler import DecompInterface
decomp = DecompInterface()
decomp.openProgram(currentProgram)
func = getFunctionAt(currentAddress)
if func:
    result = decomp.decompileFunction(func, 30, monitor)
    if result.decompileCompleted() and result.getHighFunction():
        for block in result.getHighFunction().getBasicBlocks():
            it = block.getIterator()
            while it.hasNext():
                op = it.next()
                print(f"  {op.getSeqnum().getTarget()}: {op.getMnemonic()} {op}")
decomp.dispose()
```

## Resources

| File | When to load |
|------|--------------|
| [references/scripting-guide.md](references/scripting-guide.md) | Ghidra Python/Java script patterns and API reference |
| [references/headless-analysis.md](references/headless-analysis.md) | Batch processing and headless workflow recipes |
