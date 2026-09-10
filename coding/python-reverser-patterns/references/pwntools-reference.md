# pwntools: Binary interaction library

`pwntools` is the standard Python library for binary exploitation and analysis.

## ELF object

### Loading and metadata

```python
from pwn import *

context.binary = binary = ELF("./binary")  # sets arch/bits/endian/os for asm/disasm

print(binary.arch)        # 'amd64'
print(binary.bits)        # 64
print(binary.entry)       # Entry point address
print(binary.address)     # Load address / image base
print(binary.path)        # Path to binary
binary.checksec()         # prints NX/PIE/canary/RELRO (not a return dict)
```

### Symbols and addresses

```python
func_addr = binary.symbols['main']
string_addr = next(binary.search(b'password'))  # generator of VAs; raises StopIteration if missing
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
for name, got_addr in binary.got.items():
    print(f"GOT[{name}] = {hex(got_addr)}")
for name, plt_addr in binary.plt.items():
    print(f"PLT[{name}] = {hex(plt_addr)}")
```

### Reading from virtual address

```python
data = binary.read(binary.entry, 32)                 # VA → bytes in the file
offset = binary.vaddr_to_offset(binary.entry)        # None if VA is not file-backed
```

---

## String search

### Quick pattern search

```python
# search(needle, writable=False, executable=False) → generator of VAs
# Needle is bytes. No regex flag. Does not search BSS / gaps between segments.
addresses = list(binary.search(b'admin'))
first_addr = next(binary.search(b'flag'))
for addr in binary.search(b'\x55\x48\x89\xe5', executable=True):
    print(hex(addr))
```

---

## Disassembly via pwntools

### Using Capstone (integrated)

```python
# ELF.disasm(address, n_bytes) → str (not an instruction iterator)
print(binary.disasm(binary.entry, 32))

from capstone import Cs, CS_ARCH_X86, CS_MODE_64

md = Cs(CS_ARCH_X86, CS_MODE_64)
for i in md.disasm(binary.read(binary.entry, 64), binary.entry):
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

suspicious = set(binary.got) & INJECTION_APIS

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
- **Searching without offset**: `search` yields VAs; convert with `vaddr_to_offset` when you need a file offset. There is no `regex=` argument.
- **Ignoring section flags**: RWX or missing RELRO indicates non-standard hardening.

---

## References

- https://docs.pwntools.com/en/stable/
- https://github.com/Gallopsled/pwntools
