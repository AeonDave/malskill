# Binary formats: ELF and PE

## ELF (Executable and Linkable Format)

### File header (64 bytes for 64-bit)

```python
import struct

with open("binary", "rb") as f:
    data = f.read(64)
    
magic = data[:4]                           # b"\x7fELF"
ei_class = data[4]                         # 1 (32-bit) or 2 (64-bit)
ei_data = data[5]                          # 1 (little-endian) or 2 (big-endian)
ei_version = data[6]                       # 1 (current)
e_type = struct.unpack("<H", data[16:18])[0]      # 2 (ET_EXEC) or 3 (ET_DYN)
e_machine = struct.unpack("<H", data[18:20])[0]   # 0x3E (x86-64), 0xB7 (AArch64)
e_entry = struct.unpack("<Q", data[32:40])[0]     # Entry point
e_phoff = struct.unpack("<Q", data[32:40])[0]     # Program header offset
e_shoff = struct.unpack("<Q", data[40:48])[0]     # Section header offset
```

### Sections

Important sections:
- `.text`: executable code
- `.data`: initialized data
- `.rodata` (or `.rdata`): read-only data (strings, constants)
- `.bss`: uninitialized data
- `.strtab`: string table (symbol names)
- `.symtab` (if present): symbol table (debug symbols)
- `.plt`: Procedure Linkage Table (lazy binding)
- `.got`: Global Offset Table (dynamic relocs)
- `.relro`: relocation read-only (hardening)

### Symbols and dynamic symbols

```bash
# Strip check (symtab present?)
readelf -s binary | head

# Dynamic symbols (imports)
readelf -sD binary
```

---

## PE (Portable Executable)

### DOS header and PE header

```python
import struct

with open("binary", "rb") as f:
    data = f.read(0x100)
    
dos_magic = data[:2]                       # b"MZ"
e_lfanew = struct.unpack("<I", data[0x3C:0x40])[0]  # Offset to PE header

with open("binary", "rb") as f:
    f.seek(e_lfanew)
    pe_header = f.read(4)                  # b"PE\x00\x00"
    coff_header = f.read(20)               # COFF header
    opt_header = f.read(240)               # Optional header (varies)
```

### Key fields

```python
machine = struct.unpack("<H", coff_header[0:2])[0]       # 0x8664 (x86-64) or 0x14C (x86)
num_sections = struct.unpack("<H", coff_header[2:4])[0]

# From optional header
magic = struct.unpack("<H", opt_header[0:2])[0]          # 0x20B (PE32+) or 0x10B (PE32)
entry_point = struct.unpack("<I", opt_header[16:20])[0]  # Relative to image base
image_base = struct.unpack("<Q", opt_header[24:32])[0]   # Base address
```

### Sections

Important sections:
- `.text`: code
- `.data`: data
- `.rdata` or `.rodata`: read-only data
- `.reloc`: relocation table (ASLR support)
- `.rsrc`: resources (icons, manifests, etc.)

### Imports

Imports are in the Import Directory (part of the optional header). Libraries are listed with their functions.

```python
# Tool: dumpbin /imports binary.exe
```

### Exports

If binary is a DLL, exports are listed in the Export Table.

---

## Comparison: When to use what

| Task | ELF | PE |
|------|-----|-----|
| Linux/Unix binaries | ✅ | — |
| Windows executables/DLLs | — | ✅ |
| macOS binaries | — | (Mach-O) |
| Lazy binding info | `.plt` / `.got.plt` | IAT |
| Symbols available | `.symtab` / `.strtab` | Debug info (separate .pdb) |
| Hardening marker | RELRO flags | /DYNAMICBASE, /NXCOMPAT |

---

## References

- https://en.wikipedia.org/wiki/Executable_and_Linkable_Format
- https://en.wikipedia.org/wiki/Portable_Executable
- https://docs.microsoft.com/en-us/windows/win32/debug/pe-format
