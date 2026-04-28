# Capstone: Disassembly engine

Capstone is a lightweight, multi-architecture disassembler library.

## Basic usage

```python
from capstone import *

# Create disassembler for x86-64
md = Cs(CS_ARCH_X86, CS_MODE_64)

# Disassemble bytes
code = b"\x55\x48\x89\xe5\x48\x83\xec\x10"
for instr in md.disasm(code, 0x1000):
    print(f"0x{instr.address:x}:\t{instr.mnemonic}\t{instr.op_str}")

# Output:
# 0x1000:    push     rbp
# 0x1001:    mov      rbp, rsp
# 0x1004:    sub      rsp, 0x10
```

## Architectures and modes

```python
# x86-64
md = Cs(CS_ARCH_X86, CS_MODE_64)

# x86 (32-bit)
md = Cs(CS_ARCH_X86, CS_MODE_32)

# ARM (32-bit)
md = Cs(CS_ARCH_ARM, CS_MODE_ARM)

# ARM64
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)

# MIPS
md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64)

# PowerPC
md = Cs(CS_ARCH_PPC, CS_MODE_PPC64)
```

## Detail mode (instruction metadata)

```python
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True

for instr in md.disasm(b"\x89\xc0", 0x1000):
    print(f"Operands: {len(instr.operands)}")
    for op in instr.operands:
        if op.type == X86_OP_REG:
            print(f"  Register: {instr.reg_name(op.reg)}")
        elif op.type == X86_OP_MEM:
            print(f"  Memory: [{instr.reg_name(op.mem.base)} + ...]")
        elif op.type == X86_OP_IMM:
            print(f"  Immediate: {hex(op.imm)}")
```

## Syntax highlighting

```python
from capstone import *

md = Cs(CS_ARCH_X86, CS_MODE_64)
md.syntax = CS_OPT_SYNTAX_INTEL       # Intel syntax (default)
# md.syntax = CS_OPT_SYNTAX_ATT       # AT&T syntax

for instr in md.disasm(b"\x89\xc0", 0):
    print(instr.mnemonic, instr.op_str)
```

## Integration with pwntools

```python
from pwn import *

binary = ELF("./binary")

# Disassemble from binary
for instr in binary.disasm(0x400000, 64):
    print(instr)
```

## Common patterns

### Find ROP gadgets

```python
from capstone import *

def find_gadgets(binary_data: bytes, arch, mode, pattern: str, count=10):
    """Simple gadget search (not production-grade)."""
    md = Cs(arch, mode)
    gadgets = []
    
    # Search for instruction sequences
    for offset in range(len(binary_data) - 16):
        try:
            instructions = list(md.disasm(binary_data[offset:offset+16], offset))
            if len(instructions) >= 2:
                seq = " ; ".join(f"{i.mnemonic} {i.op_str}" for i in instructions[:3])
                if pattern in seq:
                    gadgets.append((offset, seq))
        except:
            pass
    
    return gadgets[:count]
```

### Identify function prologues

```python
# Common x86-64 prologue: push rbp; mov rbp, rsp
prologue = b"\x55\x48\x89\xe5"

# Common return: pop rbp; ret
return_seq = b"\x5d\xc3"
```

---

## Anti-patterns

- **Disassembling without context**: Always know the target architecture/endianness first.
- **Assuming every sequence is reachable**: Dead code, unreachable paths, or misaligned offsets can fool naive parsing.
- **Not handling exceptions**: Malformed code, bad offsets, or packed sections cause exceptions; use try/except.

---

## References

- https://www.capstone-engine.org/
- https://github.com/capstone-engine/capstone
