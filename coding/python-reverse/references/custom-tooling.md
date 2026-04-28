# Custom tooling: Analysis scripts

Build deterministic, reusable analysis tools using Python's struct, pwntools, and custom parsing.

## Entropy heatmap (block-by-block analysis)

```python
#!/usr/bin/env python3
"""
Entropy heatmap: identify encrypted/compressed regions in a binary.
"""

import math
import sys
from pathlib import Path

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

def entropy_per_block(data: bytes, block_size: int = 1024) -> list[float]:
    """Compute entropy for each block."""
    return [shannon_entropy(data[i:i+block_size])
            for i in range(0, len(data), block_size)]

if __name__ == "__main__":
    binary = Path(sys.argv[1]).read_bytes()
    
    print(f"[*] Binary size: {len(binary)} bytes")
    print(f"[*] Analyzing with block size 1024...")
    
    entropy = entropy_per_block(binary)
    
    for i, ent in enumerate(entropy):
        offset = i * 1024
        if ent > 6.5:
            print(f"[!] Block {i} (0x{offset:x}): entropy {ent:.2f} (likely encrypted/compressed)")
        elif ent < 2.0:
            print(f"    Block {i} (0x{offset:x}): entropy {ent:.2f} (likely padding/zeros)")
```

## Binary section diff

```python
#!/usr/bin/env python3
"""
Compare two binaries structurally: headers, sections, entropy.
"""

import struct
import sys
from pathlib import Path

def parse_pe_headers(data: bytes) -> dict:
    """Extract PE header info."""
    if data[:2] != b"MZ":
        return None
    
    e_lfanew = struct.unpack("<I", data[0x3C:0x40])[0]
    if e_lfanew + 4 > len(data) or data[e_lfanew:e_lfanew+4] != b"PE\x00\x00":
        return None
    
    coff_off = e_lfanew + 4
    machine = struct.unpack("<H", data[coff_off:coff_off+2])[0]
    num_sec = struct.unpack("<H", data[coff_off+2:coff_off+4])[0]
    
    return {
        "machine": machine,
        "num_sections": num_sec,
        "pe_offset": e_lfanew,
    }

def compare_binaries(bin_a: Path, bin_b: Path):
    """Compare two PE binaries."""
    data_a = bin_a.read_bytes()
    data_b = bin_b.read_bytes()
    
    hdr_a = parse_pe_headers(data_a)
    hdr_b = parse_pe_headers(data_b)
    
    if not hdr_a or not hdr_b:
        print("[!] One or both binaries are not valid PE files")
        return
    
    print(f"[*] Binary A size: {len(data_a)}, sections: {hdr_a['num_sections']}")
    print(f"[*] Binary B size: {len(data_b)}, sections: {hdr_b['num_sections']}")
    
    if len(data_a) != len(data_b):
        print(f"[!] Size mismatch: {len(data_a) - len(data_b)} bytes")
    
    # Section-by-section comparison (stub; expand as needed)
    print("[*] For detailed section diff, use: cmp -l binary_a binary_b")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <binary_a> <binary_b>")
        sys.exit(1)
    
    compare_binaries(Path(sys.argv[1]), Path(sys.argv[2]))
```

## Import Address Table (IAT) dump with suspicious API detection

```python
#!/usr/bin/env python3
"""
Dump IAT and flag suspicious API combinations (injection, evasion, etc.).
"""

import pefile
import sys
from pathlib import Path

INJECTION_APIS = {
    "VirtualAlloc", "VirtualAllocEx", "VirtualProtect", "VirtualProtectEx",
    "WriteProcessMemory", "NtWriteVirtualMemory",
    "CreateRemoteThread", "CreateRemoteThreadEx", "RtlCreateUserThread",
}

EVASION_APIS = {
    "IsDebuggerPresent", "CheckRemoteDebuggerPresent",
    "NtQueryInformationProcess", "GetTickCount", "GetTickCount64",
}

PROCESS_APIS = {
    "OpenProcess", "CreateProcessA", "CreateProcessW",
}

def check_iat(binary_path: str):
    """Dump IAT and flag suspicious patterns."""
    try:
        pe = pefile.PE(binary_path)
    except Exception as e:
        print(f"[!] Failed to parse {binary_path}: {e}")
        return
    
    if not hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        print("[!] No import directory found")
        return
    
    suspicious = set()
    
    for dll in pe.DIRECTORY_ENTRY_IMPORT:
        dll_name = dll.dll.decode("utf-8", "ignore")
        print(f"\n[*] {dll_name}")
        
        for imp in dll.imports:
            func_name = imp.name.decode("utf-8", "ignore")
            
            if func_name in INJECTION_APIS:
                print(f"  [INJECTION] {func_name}")
                suspicious.add(func_name)
            elif func_name in EVASION_APIS:
                print(f"  [EVASION]  {func_name}")
                suspicious.add(func_name)
            elif func_name in PROCESS_APIS:
                print(f"  [PROCESS]  {func_name}")
            else:
                print(f"  {func_name}")
    
    print(f"\n[*] Suspicious APIs found: {len(suspicious)}")
    for api in sorted(suspicious):
        print(f"  - {api}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <binary.exe>")
        sys.exit(1)
    
    check_iat(sys.argv[1])
```

---

## Anti-patterns

- **Hardcoding offsets**: Use struct module or libraries like pwntools/pefile to compute offsets dynamically.
- **Not handling malformed binaries**: Always validate magic bytes and header offsets.
- **Mixing file offset and virtual address**: Keep them separate; use section mapping.

---

## References

- https://docs.python.org/3/library/struct.html
- https://pypi.org/project/pefile/
- https://github.com/Gallopsled/pwntools
