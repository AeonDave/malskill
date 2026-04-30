# Binary Ninja — Python Scripting Recipes

## Setup

```python
# In GUI: View → Script Console (Ctrl+Shift+M)
# Headless:
import binaryninja as bn
bv = bn.load("/path/to/binary")
bv.update_analysis_and_wait()

# `bv` = BinaryView (always the starting point)
# `here` = current cursor address (GUI only)
```

## Core Patterns

### Enumerate functions + calls

```python
# All functions
for func in bv.functions:
    print(f"{func.start:#010x}  {func.name:40s}  {func.total_bytes} bytes")

# Functions calling a specific API
target = "VirtualAlloc"
for func in bv.functions:
    for ref in bv.get_code_refs(bv.get_symbol_by_raw_name(target).address if bv.get_symbol_by_raw_name(target) else 0):
        caller = bv.get_functions_containing(ref.address)
        if caller:
            print(f"  {target} called from {caller[0].name} @ {ref.address:#x}")
```

### Find all calls to suspicious APIs

```python
SUSPICIOUS = [
    'VirtualAlloc', 'VirtualAllocEx', 'VirtualProtect',
    'WriteProcessMemory', 'CreateRemoteThread', 'NtCreateThreadEx',
    'LoadLibraryA', 'LoadLibraryW', 'GetProcAddress',
    'ShellExecuteA', 'ShellExecuteW', 'WinExec',
    'connect', 'send', 'recv', 'InternetOpen', 'InternetConnect',
    'RegSetValueEx', 'RegCreateKey', 'CryptEncrypt', 'CryptDecrypt'
]

for name in SUSPICIOUS:
    sym = bv.get_symbol_by_raw_name(name)
    if sym:
        refs = list(bv.get_code_refs(sym.address))
        if refs:
            print(f"\n[!] {name} ({len(refs)} refs):")
            for ref in refs:
                func = bv.get_functions_containing(ref.address)
                fname = func[0].name if func else "<unknown>"
                print(f"    {ref.address:#x}  in  {fname}")
```

### String analysis

```python
# All strings with code references
KEYWORDS = ['http', 'https', 'cmd', 'exec', 'password', 'token',
            'key', 'encrypt', 'decrypt', 'inject', 'shellcode']

for s in bv.strings:
    if any(kw in s.value.lower() for kw in KEYWORDS):
        refs = list(bv.get_code_refs(s.start))
        if refs:
            ref_funcs = [bv.get_functions_containing(r.address) for r in refs]
            names = [f[0].name for f in ref_funcs if f]
            print(f"{s.start:#x}  '{s.value}'  refs: {names}")
```

### Find crypto constants

```python
# AES S-box first 8 bytes
AES_SBOX    = bytes([0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5])
# AES key expansion constant
AES_RCON    = bytes([0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80])
# ChaCha20 "expand 32-byte k"
CHACHA_CONST = b'expand 32-byte k'

for name, pattern in [('AES S-box', AES_SBOX), ('AES RCON', AES_RCON), ('ChaCha20', CHACHA_CONST)]:
    results = list(bv.find_all_data(bv.start, bv.end, pattern))
    for addr in results:
        refs = list(bv.get_code_refs(addr))
        print(f"[{name}] @ {addr:#x}  {len(refs)} refs")
```

### HLIL traversal — find memory allocations with RWX

```python
from binaryninja import HighLevelILOperation

for func in bv.functions:
    for block in func.hlil:
        for inst in block:
            if inst.operation == HighLevelILOperation.HLIL_CALL:
                callee = str(inst.dest)
                if 'VirtualAlloc' in callee:
                    # Check 4th param (flProtect) for 0x40 (PAGE_EXECUTE_READWRITE)
                    params = inst.params
                    if len(params) >= 4:
                        protect = params[3]
                        print(f"VirtualAlloc @ {inst.address:#x} in {func.name}")
                        print(f"  protect param: {protect}")
```

### MLIL: trace data flow from network receive to execution

```python
from binaryninja import MediumLevelILOperation

for func in bv.functions:
    for block in func.mlil:
        for inst in block:
            if inst.operation == MediumLevelILOperation.MLIL_CALL:
                if any(api in str(inst) for api in ['recv', 'ReadFile', 'InternetReadFile']):
                    print(f"Data input: {func.name} @ {inst.address:#x}")
                    print(f"  Dest vars: {inst.output}")
```

### Auto-rename functions

```python
from binaryninja import SymbolType

def rename_if_match(func, pattern_calls, new_name):
    """Rename func if it calls all APIs in pattern_calls."""
    calls_in_func = set()
    for block in func.hlil:
        for inst in block:
            if inst.operation == HighLevelILOperation.HLIL_CALL:
                calls_in_func.add(str(inst.dest))
    if all(any(p in c for c in calls_in_func) for p in pattern_calls):
        func.name = new_name
        print(f"  Renamed {func.start:#x} → {new_name}")

for func in bv.functions:
    if func.name.startswith("sub_"):
        rename_if_match(func, ['VirtualAlloc', 'WriteProcessMemory', 'CreateRemoteThread'],
                        'inject_shellcode')
        rename_if_match(func, ['connect', 'send', 'recv'], 'c2_communication')
        rename_if_match(func, ['RegCreateKey', 'RegSetValueEx'], 'install_persistence')
```

### Dump binary analysis report

```python
import json

report = {
    "file": bv.file.filename,
    "arch": bv.arch.name,
    "platform": bv.platform.name if bv.platform else None,
    "functions": len(list(bv.functions)),
    "strings": len(list(bv.strings)),
    "imports": [s.name for s in bv.get_symbols() if s.type.name == 'ImportedFunctionSymbol'],
    "exports": [s.name for s in bv.get_symbols() if s.type.name == 'FunctionSymbol'],
    "sections": [{"name": s.name, "start": s.start, "size": s.length} for s in bv.sections.values()],
}
print(json.dumps(report, indent=2))
```

### Batch headless analysis

```python
#!/usr/bin/env python3
"""Analyze all samples in a directory, output CSV."""
import binaryninja as bn
import csv, sys
from pathlib import Path

samples_dir = Path(sys.argv[1])
out = csv.writer(open("analysis.csv", "w"))
out.writerow(["file", "arch", "functions", "imports", "suspicious_apis"])

SUSPICIOUS = ['VirtualAlloc', 'CreateRemoteThread', 'WriteProcessMemory',
              'connect', 'send', 'LoadLibrary']

for sample in samples_dir.iterdir():
    try:
        bv = bn.load(str(sample), update_analysis=True)
        if bv is None:
            continue
        bv.update_analysis_and_wait()
        imports = [s.name for s in bv.get_symbols()
                   if 'Import' in s.type.name]
        found_suspicious = [a for a in SUSPICIOUS if a in imports]
        out.writerow([sample.name, bv.arch.name if bv.arch else "?",
                      len(list(bv.functions)), len(imports),
                      ";".join(found_suspicious)])
        bv.file.close()
    except Exception as e:
        out.writerow([sample.name, "ERROR", str(e), "", ""])
```

## Tags and Comments

```python
# Add a tag to a function
func = bv.get_function_at(0x401000)
tag_type = bv.get_tag_type("Suspicious")  # or create: bv.create_tag_type("Suspicious", "🔴")
func.add_user_address_tag(func.start, tag_type, "potential injector")

# Add comment
bv.set_comment_at(0x401234, "decryption key XOR 0xAA")

# Get all comments
for addr, comment in bv.address_comments.items():
    print(f"{addr:#x}: {comment}")
```
