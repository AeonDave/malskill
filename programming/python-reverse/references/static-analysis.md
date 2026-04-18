# Static analysis: Strings, imports, entropy

## String extraction

### Raw ASCII/UTF-8 strings

```python
import re

def extract_strings(data: bytes, min_len: int = 4) -> list[tuple[int, str]]:
    """Extract printable ASCII strings and their offsets."""
    results = []
    current = b""
    offset = 0
    
    for i, byte in enumerate(data):
        if 32 <= byte <= 126 or byte in (9, 10, 13):  # Printable + whitespace
            if not current:
                offset = i
            current += bytes([byte])
        else:
            if len(current) >= min_len:
                results.append((offset, current.decode("ascii", "ignore")))
            current = b""
    
    return results

# Usage
with open("binary", "rb") as f:
    strings = extract_strings(f.read())
    for offset, s in strings:
        print(f"0x{offset:x}: {s}")
```

### Pattern detection

```python
import re

# URLs
url_pattern = rb"https?://[^\s\x00]+"
# IPs
ip_pattern = rb"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
# Paths
path_pattern = rb"[A-Z]:\\[^\x00]+"  # Windows paths
```

### Tools

- `strings` command (built-in): `strings binary | grep -i password`
- pwntools: `binary.search(b"pattern")`
- Custom Python: use regex on raw binary data

---

## Import enumeration

### PE imports

```python
import pefile

pe = pefile.PE("binary.exe")

for dll in pe.DIRECTORY_ENTRY_IMPORT:
    print(f"DLL: {dll.dll.decode()}")
    for imp in dll.imports:
        print(f"  {imp.name.decode()}")
```

### ELF dynamic symbols

```python
from elftools.elf.elffile import ELFFile

with open("binary", "rb") as f:
    elf = ELFFile(f)
    dynsym = elf.get_section_by_name(".dynsym")
    
    for symbol in dynsym.iter_symbols():
        if symbol.entry.st_info.bind == "STB_DYNAMIC":
            print(f"Import: {symbol.name}")
```

### Suspicious API detection

Common injection/evasion APIs:

```python
SUSPICIOUS = {
    # Injection
    "VirtualAlloc", "VirtualAllocEx", "WriteProcessMemory", "CreateRemoteThread",
    # Evasion
    "IsDebuggerPresent", "GetTickCount64", "SetUnhandledExceptionFilter",
    # Process
    "OpenProcess", "TerminateProcess", "CreateProcessA", "CreateProcessW",
    # Memory
    "HeapAlloc", "RtlAllocateHeap", "RtlCopyMemory",
}
```

---

## Entropy analysis

### Shannon entropy per block

```python
import math

def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    ent = 0.0
    for f in freq:
        if f > 0:
            p = f / n
            ent -= p * math.log2(p)
    return ent

# Block-by-block analysis
def entropy_map(data: bytes, block_size: int = 1024) -> list[float]:
    """Map entropy per block."""
    return [shannon_entropy(data[i:i+block_size]) 
            for i in range(0, len(data), block_size)]

# Find high-entropy regions
with open("binary", "rb") as f:
    data = f.read()
    for i, ent in enumerate(entropy_map(data)):
        if ent > 6.5:  # Threshold for likely compression/encryption
            print(f"Block {i} (offset 0x{i*1024:x}): entropy {ent:.2f}")
```

### Interpretation

- Entropy 0.0 - 2.0: All zeros or highly repetitive (padding, tables)
- Entropy 2.0 - 4.5: Mostly plaintext (code, strings)
- Entropy 4.5 - 7.0: Mixed or compressed
- Entropy 7.0 - 8.0: Encrypted or random (shellcode, packed payloads)

---

## Sections and memory layout

```python
from pwn import ELF

binary = ELF("./binary")

for section in binary.sections:
    name = section.name
    addr = section.header["sh_addr"]
    size = section.header["sh_size"]
    flags = section.header["sh_flags"]
    
    # Check flags
    writable = bool(flags & 0x1)
    executable = bool(flags & 0x4)
    
    print(f"{name:16} {hex(addr):12} {hex(size):10} "
          f"{'W' if writable else '-'}{'X' if executable else '-'}")
```

### Red flags

- RWX sections: Non-standard; suggests JIT or malware
- Missing RELRO: No relocation hardening
- High-entropy .text: Likely obfuscated or polymorphic

---

## References

- https://pypi.org/project/pefile/
- https://github.com/eliben/pyelftools
