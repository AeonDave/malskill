# Binary Ninja — IL Guide: LLIL / MLIL / HLIL

## IL Hierarchy

```
Assembly
   ↓
LLIL  — Low Level IL: normalized assembly, architecture-independent
   ↓
MLIL  — Medium Level IL: variables recovered, stack abstracted, propagation
   ↓
HLIL  — High Level IL: decompiler output, loops/if/switch recovered
```

Each level is available as SSA form (Single Static Assignment) for analysis:
`func.llil_ssa`, `func.mlil_ssa`, `func.hlil_ssa`

## HLIL Operations (Most Used)

| Operation | Meaning |
|-----------|---------|
| `HLIL_CALL` | Function call (`inst.dest` = callee, `inst.params` = args) |
| `HLIL_ASSIGN` | Assignment (`inst.dest`, `inst.src`) |
| `HLIL_IF` | Conditional (`inst.condition`, `inst.true`, `inst.false`) |
| `HLIL_WHILE` | While loop |
| `HLIL_FOR` | For loop |
| `HLIL_RETURN` | Return (`inst.src`) |
| `HLIL_DEREF` | Dereference pointer |
| `HLIL_ADD/SUB/MUL` | Arithmetic |
| `HLIL_XOR/AND/OR` | Bitwise |
| `HLIL_CONST` | Constant value (`inst.constant`) |
| `HLIL_VAR` | Variable reference (`inst.var`) |

## HLIL Traversal

```python
from binaryninja import HighLevelILOperation as HLOP

func = bv.get_function_at(0x401000)

# Iterate all instructions
for block in func.hlil:
    for inst in block:
        print(f"  {inst.address:#x}: {inst.operation.name}: {inst}")

# Find all calls with their callee names
for block in func.hlil:
    for inst in block:
        if inst.operation == HLOP.HLIL_CALL:
            dest = inst.dest
            # dest can be a symbol, a constant, or a variable
            if dest.operation == HLOP.HLIL_CONST_PTR:
                sym = bv.get_symbol_at(dest.constant)
                name = sym.name if sym else f"sub_{dest.constant:#x}"
            elif dest.operation == HLOP.HLIL_VAR:
                name = f"<var: {dest.var.name}>"
            else:
                name = str(dest)
            params = [str(p) for p in inst.params]
            print(f"  CALL {name}({', '.join(params)})")
```

## MLIL Traversal + Variable Tracking

```python
from binaryninja import MediumLevelILOperation as MLOP

func = bv.get_function_at(0x401234)

# Find return value of VirtualAlloc → track usage
alloc_results = []
for block in func.mlil:
    for inst in block:
        if inst.operation == MLOP.MLIL_CALL:
            if 'VirtualAlloc' in str(inst.dest):
                if inst.output:
                    alloc_results.extend(inst.output)

# Find where those variables are used
for block in func.mlil:
    for inst in block:
        src_str = str(inst)
        for var in alloc_results:
            if str(var) in src_str:
                print(f"  Alloc result used @ {inst.address:#x}: {inst}")
```

## LLIL Traversal

```python
from binaryninja import LowLevelILOperation as LLOP

func = bv.get_function_at(0x401000)

# Find all memory writes (potential shellcode writes)
for block in func.llil:
    for inst in block:
        if inst.operation == LLOP.LLIL_STORE:
            dest_expr = str(inst.dest)
            size = inst.size
            src = str(inst.src)
            print(f"  STORE [{dest_expr}] ({size} bytes) = {src} @ {inst.address:#x}")
```

## IL SSA Form

SSA adds version numbers to variables (no variable reuse). Better for data flow.

```python
# HLIL SSA
func_ssa = func.hlil.ssa_form
for block in func_ssa:
    for inst in block:
        print(f"  {inst}")

# Get definitions and uses of a variable
var = func.hlil.vars[0]  # first variable
defs = func.hlil.ssa_form.get_ssa_var_definition(var)
uses = func.hlil.ssa_form.get_ssa_var_uses(var)
```

## Lifting Architecture-Specific Code

```python
# Check if architecture was correctly identified
print(f"Arch: {bv.arch.name}")
print(f"Platform: {bv.platform.name if bv.platform else 'None'}")

# Manually set arch (for shellcode/firmware)
# bv.arch = binaryninja.Architecture['x86_64']

# Force re-analysis
bv.update_analysis_and_wait()
```

## IL for Malware Analysis — Cheatsheet

```python
from binaryninja import HighLevelILOperation as HLOP

def analyze_function(func):
    """Comprehensive function analysis using HLIL."""
    calls = []
    strings_used = []
    crypto_ops = []

    for block in func.hlil:
        for inst in block:
            # Calls
            if inst.operation == HLOP.HLIL_CALL:
                dest_str = str(inst.dest)
                calls.append((inst.address, dest_str, [str(p) for p in inst.params]))

            # Assignments from constants (inline strings, keys)
            if inst.operation == HLOP.HLIL_ASSIGN:
                if inst.src.operation == HLOP.HLIL_CONST:
                    val = inst.src.constant
                    # Check if it's a string pointer
                    s = bv.get_string_at(val)
                    if s:
                        strings_used.append((inst.address, s.value))

            # XOR operations (common in obfuscation/encryption)
            if inst.operation == HLOP.HLIL_ASSIGN:
                if 'xor' in str(inst.src).lower() or '^' in str(inst.src):
                    crypto_ops.append((inst.address, str(inst)))

    return {"calls": calls, "strings": strings_used, "crypto": crypto_ops}

# Analyze all non-library functions
for func in bv.functions:
    if not func.name.startswith("_") and not func.name.startswith("j_"):
        result = analyze_function(func)
        if result["calls"] or result["strings"] or result["crypto"]:
            print(f"\n=== {func.name} @ {func.start:#x} ===")
            for addr, dest, params in result["calls"]:
                print(f"  CALL {dest}({', '.join(params[:3])}) @ {addr:#x}")
            for addr, s in result["strings"]:
                print(f"  STRING '{s}' @ {addr:#x}")
            for addr, op in result["crypto"]:
                print(f"  CRYPTO {op} @ {addr:#x}")
```

## Switching IL Levels (GUI)

| Shortcut | Action |
|----------|--------|
| `H` | Cycle: Disasm → LLIL → MLIL → HLIL |
| `Escape` | Return to previous view |

Tip: Use HLIL for understanding logic, MLIL for data flow, LLIL for exact semantics, Disassembly for exact bytes.
