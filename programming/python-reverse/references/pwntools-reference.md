# pwntools: Binary interaction library

`pwntools` is the standard Python library for binary exploitation and analysis.

## ELF object

### Loading and metadata

```python
from pwn import *

binary = ELF("./binary")

print(binary.arch)        # 'amd64'
print(binary.bits)        # 64
print(binary.entry)       # Entry point address
print(binary.address)     # Load address / image base
print(binary.path)        # Path to binary
```

### Symbols and addresses

```python
func_addr = binary.symbols['main']
string_addr = binary.search(b'password')  # First occurrence
```

### Sections

```python
text_section = binary.get_section_by_name('.text')
print(text_section.data[:32])             # First 32 bytes of .text

for section in binary.sections:
    print(f"{section.name}: {hex(section.header['sh_addr'])} - {hex(section.header['sh_size'])}")
```

### Imports and PLT

```python
for import_sym in binary.imports:
    print(f"Import: {import_sym} at {hex(binary.got[import_sym])}")
    
plt_entries = binary.plt
for name, addr in plt_entries.items():
    print(f"PLT[{name}] = {hex(addr)}")
```

### Reading from virtual address

```python
# Read string at virtual address
string_va = 0x400000 + 0x1234
# (Use binary sections to map VA to file offset)
```

---

## String search

### Quick pattern search

```python
from pwn import *

# Search for all occurrences in binary
addresses = list(binary.search(b'admin'))

# Limit results
first_addr = binary.search(b'flag').__next__()

# Search with regex (slower)
for match in binary.search(b'http', regex=True):
    print(hex(match))
```

---

## Disassembly via pwntools

### Using Capstone (integrated)

```python
from pwn import *

binary = ELF("./binary")

# Disassemble from address
asm = binary.disasm(0x400000, 32)  # Disassemble 32 bytes from 0x400000

# Or manually with capstone
from capstone import *

md = Cs(CS_ARCH_X86, CS_MODE_64)
for i in md.disasm(binary.read(0x400000, 64), 0x400000):
    print(f"0x{i.address:x}:\t{i.mnemonic}\t{i.op_str}")
```

---

## Common patterns

### Parse imports and flag suspicious APIs

```python
from pwn import *

binary = ELF("./binary")

INJECTION_APIS = {
    "VirtualAlloc", "VirtualAllocEx", "CreateRemoteThread",
    "WriteProcessMemory", "SetThreadContext",
}

suspicious = set()
for imp in binary.imports:
    if imp in INJECTION_APIS:
        suspicious.add(imp)

if suspicious:
    print(f"Suspicious APIs: {suspicious}")
```

### Find function prologues

```python
from pwn import *

binary = ELF("./binary")

# Search for 0x55 (push rbp on x86-64)
for addr in binary.search(b"\x55\x48\x89\xe5"):  # push rbp; mov rbp, rsp
    print(f"Possible function at {hex(addr)}")
```

---

## Anti-patterns

- **Assuming all imports are resolved at load time**: Some are resolved lazily via PLT/GOT.
- **Searching without offset**: Always track where you are in the VA/file space.
- **Ignoring section flags**: RWX or missing RELRO indicates non-standard hardening.

---

## References

- https://docs.pwntools.com/en/stable/
- https://github.com/Gallopsled/pwntools
