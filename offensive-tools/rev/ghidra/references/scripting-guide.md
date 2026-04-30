# Ghidra — Python/Java Scripting Reference

## Setup

### GUI: Script Manager
`Window → Script Manager` (or `Ctrl+Alt+S`) → New → choose language (Java/Python)

### Python (Jython 2.7 — built-in)
Available globals in scripts:
```python
currentProgram      # Program object
currentAddress      # Current cursor address
currentLocation     # Program location
monitor             # TaskMonitor (progress + cancel)
state               # ScriptState
askString(title, msg)   # User input dialog
popup(msg)          # Popup message
println(msg)        # Print to Script Console
```

### Java scripts
Same globals but as Java method calls. Prefer Python for quick work.

## Core API Patterns

### Function enumeration

```python
fm = currentProgram.getFunctionManager()

# All functions
for func in fm.getFunctions(True):
    print(f"{func.getEntryPoint()}: {func.getName():40s} {func.getBody().getNumAddresses()} bytes")

# Functions in address order
for func in fm.getFunctionsNoStubs(True):
    if not func.isExternal():
        print(func.getName())

# Get function by address
addr = currentProgram.getAddressFactory().getAddress("0x401000")
func = fm.getFunctionAt(addr)
```

### Symbol and reference analysis

```python
sm = currentProgram.getSymbolTable()
rm = currentProgram.getReferenceManager()

# Find all calls to an import
target_sym = sm.getSymbols("VirtualAlloc")
for sym in target_sym:
    for ref in rm.getReferencesTo(sym.getAddress()):
        from_addr = ref.getFromAddress()
        func = fm.getFunctionContaining(from_addr)
        if func:
            print(f"  {sym.getName()} called from {func.getName()} @ {from_addr}")

# Get all imports
for sym in sm.getExternalSymbols():
    print(f"  {sym.getName()}  {sym.getParentNamespace().getName()}")

# Get cross-references from an address
for ref in rm.getReferencesFrom(currentAddress):
    print(f"  -> {ref.getToAddress()} ({ref.getReferenceType()})")
```

### Search for crypto constants

```python
from ghidra.program.model.mem import MemoryAccessException

def find_bytes(pattern_bytes):
    """Search for byte pattern in all memory blocks."""
    mem = currentProgram.getMemory()
    results = []
    pattern = bytes(pattern_bytes)
    mask = None
    start = currentProgram.getMinAddress()
    while True:
        addr = mem.findBytes(start, bytes(pattern_bytes), mask, True, monitor)
        if addr is None:
            break
        results.append(addr)
        start = addr.add(1)
    return results

# AES S-box
AES_SBOX = [0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5]
matches = find_bytes(AES_SBOX)
for addr in matches:
    refs = list(rm.getReferencesTo(addr))
    func_names = []
    for ref in refs:
        f = fm.getFunctionContaining(ref.getFromAddress())
        if f: func_names.append(f.getName())
    print(f"  AES S-box @ {addr} refs: {func_names}")

# ChaCha20 constant "expand 32-byte k"
CHACHA = list(b'expand 32-byte k')
for addr in find_bytes(CHACHA):
    print(f"  ChaCha20 constant @ {addr}")
```

### Decompiler API

```python
from ghidra.app.decompiler import DecompInterface

decomp = DecompInterface()
decomp.openProgram(currentProgram)

def decompile(func):
    result = decomp.decompileFunction(func, 60, monitor)
    if result and result.decompileCompleted():
        return result.getDecompiledFunction().getC()
    return None

# Find injection-related functions
for func in fm.getFunctions(True):
    code = decompile(func)
    if code and 'VirtualAlloc' in code and 'CreateRemoteThread' in code:
        print(f"  Potential injector: {func.getName()} @ {func.getEntryPoint()}")
        print(code[:500])
```

### Data types and structs

```python
dtm = currentProgram.getDataTypeManager()

# Find existing struct
from ghidra.program.model.data import StructureDataType, DataTypeConflictHandler

# Create a new struct
struct = StructureDataType("C2_Config", 0)
struct.add(dtm.getDataType("/dword"), 4, "ip_addr", "C2 IP as DWORD")
struct.add(dtm.getDataType("/word"), 2, "port", "C2 port")
struct.add(dtm.getDataType("/byte"), 1, "flags", "Feature flags")
struct.add(dtm.getDataType("/TerminatedCString"), -1, "key", "Encryption key")

# Add to type manager
dtm.addDataType(struct, DataTypeConflictHandler.DEFAULT_HANDLER)

# Apply to address
from ghidra.program.model.listing import DataUtilities
from ghidra.program.model.data import ClearDataMode

DataUtilities.createData(currentProgram, currentAddress, struct, -1,
                         False, ClearDataMode.CLEAR_ALL_CONFLICT_DATA)
```

### Rename functions by pattern

```python
from ghidra.program.model.symbol import SourceType

RENAME_RULES = [
    (['VirtualAlloc', 'WriteProcessMemory', 'CreateRemoteThread'], 'inject_process'),
    (['connect', 'send', 'recv'], 'c2_communication'),
    (['RegCreateKey', 'RegSetValue'], 'install_persistence'),
    (['CryptEncrypt', 'AesManaged'], 'encrypt_data'),
    (['GetManifestResourceStream', 'Assembly.Load'], 'load_stage2'),
]

decomp = DecompInterface()
decomp.openProgram(currentProgram)

for func in fm.getFunctions(True):
    if not func.getName().startswith("FUN_"):
        continue
    result = decomp.decompileFunction(func, 30, monitor)
    if not result or not result.decompileCompleted():
        continue
    code = result.getDecompiledFunction().getC()
    for apis, new_name in RENAME_RULES:
        if all(api in code for api in apis):
            func.setName(new_name + "_" + str(func.getEntryPoint()),
                         SourceType.USER_DEFINED)
            println(f"Renamed: {func.getEntryPoint()} → {new_name}")
            break
```

### Comment automation

```python
from ghidra.program.model.listing import CodeUnit

# Add plate comment to suspicious functions
listing = currentProgram.getListing()
for func in fm.getFunctions(True):
    code_unit = listing.getCodeUnitAt(func.getEntryPoint())
    if code_unit:
        # Check if it calls suspicious APIs
        code_unit.setComment(CodeUnit.PLATE_COMMENT,
                             "=== AUTO-ANALYZED: potential malicious function ===")
```

## Useful Tricks

### Find all string XREFs containing a keyword

```python
# Find all strings matching keyword, with their callers
def find_string_refs(keyword):
    results = []
    for s in currentProgram.getListing().getDefinedData(True):
        if s.hasStringValue():
            val = str(s.getValue())
            if keyword.lower() in val.lower():
                refs = list(rm.getReferencesTo(s.getAddress()))
                for ref in refs:
                    func = fm.getFunctionContaining(ref.getFromAddress())
                    results.append({
                        "string": val,
                        "addr": s.getAddress(),
                        "ref_from": ref.getFromAddress(),
                        "func": func.getName() if func else "?"
                    })
    return results

for hit in find_string_refs("http"):
    println(f"{hit['addr']}: '{hit['string']}' in {hit['func']}")
```

### Binary patch via scripting

```python
from ghidra.program.model.mem import Memory

mem = currentProgram.getMemory()
# NOP out 5 bytes at address (x86: 0x90 = NOP)
addr = currentProgram.getAddressFactory().getAddress("0x401234")
nops = bytes([0x90] * 5)
mem.setBytes(addr, nops)
println(f"Patched {addr} with NOPs")
```

## P-Code Traversal (Architecture-Independent Analysis)

P-Code = Ghidra's IR. All architectures (x86/ARM/MIPS) lift to same ops.
Write one analysis script, works on all platforms.

```python
from ghidra.program.model.pcode import PcodeOpAST

# Get P-Code for a function (via decompiler high-level form)
from ghidra.app.decompiler import DecompInterface
decomp = DecompInterface()
decomp.openProgram(currentProgram)

func = currentProgram.getFunctionManager().getFunctionAt(currentAddress)
result = decomp.decompileFunction(func, 60, monitor)
high_func = result.getHighFunction()

# Iterate all P-Code ops in function
for pcode_op in high_func.getPcodeOps():
    mnemonic = pcode_op.getMnemonic()       # CALL, LOAD, STORE, etc.
    output = pcode_op.getOutput()           # output Varnode (or None)
    inputs = [pcode_op.getInput(i) for i in range(pcode_op.getNumInputs())]

    # Detect CALL instructions → log callee
    if mnemonic == "CALL":
        callee_addr = inputs[0]
        called_func = currentProgram.getFunctionManager().getFunctionAt(
            callee_addr.getAddress()
        )
        if called_func:
            println(f"  CALL → {called_func.getName()}")

decomp.closeProgram()
```

```python
# Walk data dependency: trace where a variable's value came from
def trace_def_use(varnode, depth=0, visited=None):
    """DFS backwards through P-Code to find data sources."""
    if visited is None:
        visited = set()
    if varnode is None or id(varnode) in visited:
        return
    visited.add(id(varnode))
    indent = "  " * depth
    println(f"{indent}Varnode: {varnode} (addr={varnode.getAddress()})")
    def_op = varnode.getDef()   # P-Code op that defines this varnode
    if def_op:
        println(f"{indent}  Defined by: {def_op.getMnemonic()}")
        for i in range(def_op.getNumInputs()):
            trace_def_use(def_op.getInput(i), depth + 1, visited)
```

## Obfuscation Analysis

### Emulation-based string decryption

```python
from ghidra.app.emulator import EmulatorHelper

# Emulate a decryption function to extract plaintext strings
# without executing malware
emu = EmulatorHelper(currentProgram)

# Set up entry point (e.g., string decrypt function)
decrypt_func_addr = currentProgram.getAddressFactory().getAddress("0x401000")
emu.setExecutionAddress(decrypt_func_addr)

# Set argument in register (calling convention: RCX = encrypted string ptr)
emu.writeRegister("RCX", 0x403000)  # Pointer to encrypted data
emu.writeRegister("RDX", len(encrypted_data))

# Step until return
MAX_STEPS = 10000
for _ in range(MAX_STEPS):
    if not emu.step(monitor):
        break
    # Check if we hit a RET instruction
    pc = emu.getExecutionAddress()
    instr = currentProgram.getListing().getInstructionAt(pc)
    if instr and instr.getMnemonicString() == "RET":
        break

# Read result from return register or output buffer
result_ptr = emu.readRegister("RAX")
result = emu.readMemory(
    currentProgram.getAddressFactory().getAddress(hex(result_ptr)), 256
)
println(f"Decrypted: {bytes(result).split(b'\\x00')[0]}")
emu.dispose()
```

### Detect opaque predicates (always-true/false branches)

```python
# Opaque predicates = fake conditional jumps
# Heuristic: JZ/JNZ immediately after XOR reg, reg (always 0)
from ghidra.program.model.lang import OperandType

listing = currentProgram.getListing()
for func in currentProgram.getFunctionManager().getFunctions(True):
    instrs = list(listing.getInstructions(func.getBody(), True))
    for i, instr in enumerate(instrs[:-1]):
        mnem = instr.getMnemonicString()
        next_mnem = instrs[i+1].getMnemonicString()
        if mnem == "XOR" and next_mnem in ("JZ", "JE"):
            op0 = instr.getOpObjects(0)
            op1 = instr.getOpObjects(1)
            if op0 and op1 and str(op0[0]) == str(op1[0]):  # XOR reg, reg
                println(f"Possible opaque predicate @ {instrs[i+1].getAddress()}")
```

## Binary Diffing (Version Tracking)

```
# GUI workflow:
# 1. Import both binaries, run auto-analysis on each
# 2. Tools → Version Tracking → New Session
# 3. Source program = old; Destination program = new
# 4. Run correlators: Exact Function Bytes → Symbol Name → Structural
# 5. Review matches by score (1.0 = identical, 0.0 = no match)
# 6. Functions with score 0.7-0.99 = candidates for patch changes
```

```python
# Programmatic: identify changed functions between two programs via ghidriff
# CLI: ghidriff old.exe new.exe --output diff_report.md
# GitHub: https://github.com/clearbluejar/ghidriff
#
# Or use PatchDiffCorrelator extension for graduated similarity scoring
# GitHub: https://github.com/threatrack/ghidra-patchdiff-correlator

# Malware use cases:
# - Compare malware variants across campaigns
# - Find new capabilities added in updated sample
# - Track C2 address changes between builds
```

## Python 3 Support (Ghidrathon)

Built-in scripting uses Jython (Python 2.7 EOL). For Python 3:

```bash
# Install Ghidrathon extension:
# https://github.com/mandiant/ghidrathon
# File → Install Extensions → select Ghidrathon .zip
# Restart Ghidra → Script Manager shows "Python 3" language option
#
# Benefit: modern libraries (capstone, yara, pycryptodome) in scripts
```
