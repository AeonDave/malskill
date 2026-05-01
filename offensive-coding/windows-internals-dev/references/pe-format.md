# PE / COFF Format Reference

The Portable Executable (PE) format is the Windows executable container. Every `.exe`, `.dll`, `.sys`, `.efi`, and in-memory loaded module is PE. COFF object files (`.obj`, BOFs) are a subset.

Authoritative source: [Microsoft PE Format documentation](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format).

---

## Overall layout

```
+------------------------+  file offset 0
| IMAGE_DOS_HEADER       |  "MZ", contains e_lfanew
| ... DOS stub ...       |
+------------------------+  file offset = e_lfanew
| IMAGE_NT_HEADERS       |  "PE\0\0" + FileHeader + OptionalHeader
+------------------------+
| IMAGE_SECTION_HEADERS[]|  one per section, size = NumberOfSections
+------------------------+
| ... raw sections ...   |  .text, .rdata, .data, .pdata, .reloc, .tls, ...
+------------------------+
```

When the kernel loader maps a PE into memory:
- Each section's `VirtualAddress` is the RVA where the section begins
- Memory addresses inside the image = `DllBase + RVA`
- `RawDataAddress` (file offset) and `VirtualAddress` (memory RVA) differ because section alignment differs in file vs memory (`FileAlignment` typically 0x200, `SectionAlignment` typically 0x1000)

---

## IMAGE_DOS_HEADER

Minimal — only two fields matter.

```c
typedef struct _IMAGE_DOS_HEADER {
    WORD  e_magic;      // Must be 0x5A4D "MZ"
    WORD  e_cblp;
    // ... 14 more reserved/obsolete fields ...
    LONG  e_lfanew;     // Offset to IMAGE_NT_HEADERS. Must be > 0 and < file size.
} IMAGE_DOS_HEADER;      // sizeof = 64
```

Validate: `e_magic == 0x5A4D`, `e_lfanew > 0`, `e_lfanew + sizeof(IMAGE_NT_HEADERS) <= image_size`.

---

## IMAGE_NT_HEADERS (x64)

```c
typedef struct _IMAGE_NT_HEADERS64 {
    DWORD                   Signature;        // 0x00004550 "PE\0\0"
    IMAGE_FILE_HEADER       FileHeader;       // 20 bytes
    IMAGE_OPTIONAL_HEADER64 OptionalHeader;   // 240 bytes on x64
} IMAGE_NT_HEADERS64;
```

### IMAGE_FILE_HEADER

| Offset | Field | Notes |
|--------|-------|-------|
| 0x00 | Machine | 0x8664 (AMD64), 0xAA64 (ARM64), 0x14C (i386) |
| 0x02 | NumberOfSections | |
| 0x04 | TimeDateStamp | Unix epoch (can be randomized for reproducible builds) |
| 0x08 | PointerToSymbolTable | Obsolete in PE (COFF only) |
| 0x0C | NumberOfSymbols | 0 for PE |
| 0x10 | SizeOfOptionalHeader | 240 for PE32+, 224 for PE32 |
| 0x12 | Characteristics | `IMAGE_FILE_DLL` = 0x2000, `IMAGE_FILE_EXECUTABLE_IMAGE` = 0x0002 |

### IMAGE_OPTIONAL_HEADER64 — key fields

| Offset (from OptHdr base) | Field | Notes |
|---|---|---|
| 0x00 | Magic | 0x20B = PE32+ (x64), 0x10B = PE32 (x86) |
| 0x10 | AddressOfEntryPoint | RVA |
| 0x18 | ImageBase | Preferred load address (may be relocated) |
| 0x20 | SectionAlignment | Memory alignment, usually 0x1000 |
| 0x24 | FileAlignment | File alignment, usually 0x200 |
| 0x38 | SizeOfImage | Total mapped size (used by VirtualAlloc) |
| 0x50 | DllCharacteristics | Mitigation flags (ASLR, NX, CFG, etc.) |
| 0x88 | NumberOfRvaAndSizes | Usually 16 |
| 0x8C | DataDirectory[16] | **Array of {RVA, Size} entries** |

The DataDirectory array begins at OptionalHeader + 0x70. Offset 0x88 in this table above refers to OptionalHeader + 0x88 which is `DataDirectory[0].VirtualAddress` (Export Directory RVA). Easier mental model:

| Index | Directory | Purpose |
|-------|-----------|---------|
| 0 | Export | What this module exports |
| 1 | Import | What this module imports (IAT lookup) |
| 2 | Resource | .rsrc section descriptor |
| **3** | **Exception** | **.pdata RUNTIME_FUNCTION table (x64 SEH)** |
| 4 | Security | Authenticode / certificate table |
| 5 | Relocation | .reloc section for rebasing |
| 6 | Debug | PDB reference |
| 7 | Architecture | Reserved |
| 8 | Global Pointer | IA64 only, zero on x64 |
| **9** | **TLS** | **IMAGE_TLS_DIRECTORY64** |
| 10 | Load Config | Mitigation metadata (CFG bitmap, etc.) |
| 11 | Bound Import | Pre-bound import resolution |
| 12 | IAT | Import Address Table (patched by loader) |
| 13 | Delay Import | Delay-loaded DLLs |
| 14 | COM Descriptor | .NET metadata (CLR header) |
| 15 | Reserved | |

### DllCharacteristics flags to know

| Bit | Name | Meaning |
|-----|------|---------|
| 0x0020 | HIGH_ENTROPY_VA | 64-bit ASLR |
| 0x0040 | DYNAMIC_BASE | ASLR enabled |
| 0x0080 | FORCE_INTEGRITY | Required for kernel callbacks registration |
| 0x0100 | NX_COMPAT | DEP required |
| 0x0200 | NO_ISOLATION | SxS disabled |
| 0x0400 | NO_SEH | No SEH handlers |
| 0x0800 | NO_BIND | Do not bind imports |
| 0x4000 | GUARD_CF | Control Flow Guard enabled |

---

## Sections

Each `IMAGE_SECTION_HEADER` is 40 bytes; the array follows `IMAGE_NT_HEADERS` directly in file.

```c
typedef struct _IMAGE_SECTION_HEADER {
    BYTE    Name[8];              // Not null-terminated if 8 chars
    union {
        DWORD PhysicalAddress;
        DWORD VirtualSize;        // Size of section in memory
    } Misc;
    DWORD   VirtualAddress;       // RVA in mapped image
    DWORD   SizeOfRawData;        // Size in file (padded to FileAlignment)
    DWORD   PointerToRawData;     // File offset of section
    DWORD   PointerToRelocations; // Obsolete for PE
    DWORD   PointerToLinenumbers; // Obsolete
    WORD    NumberOfRelocations;
    WORD    NumberOfLinenumbers;
    DWORD   Characteristics;      // Section flags (see below)
} IMAGE_SECTION_HEADER;
```

### Section characteristics flags

| Flag | Value | Meaning |
|------|-------|---------|
| IMAGE_SCN_CNT_CODE | 0x00000020 | Contains executable code |
| IMAGE_SCN_CNT_INITIALIZED_DATA | 0x00000040 | Initialized data |
| IMAGE_SCN_CNT_UNINITIALIZED_DATA | 0x00000080 | BSS |
| IMAGE_SCN_MEM_DISCARDABLE | 0x02000000 | Discard after load (.reloc typical) |
| IMAGE_SCN_MEM_SHARED | 0x10000000 | Shared between processes |
| IMAGE_SCN_MEM_EXECUTE | 0x20000000 | Executable |
| IMAGE_SCN_MEM_READ | 0x40000000 | Readable |
| IMAGE_SCN_MEM_WRITE | 0x80000000 | Writable |

**Typical page protections at load time**:
- `.text` (code) → PAGE_EXECUTE_READ (RX, **not** RWX)
- `.rdata` (const data, IAT, exports) → PAGE_READONLY (R) — **except** IAT which becomes PAGE_READWRITE during loader resolution then RX/R
- `.data` → PAGE_READWRITE (RW)
- `.pdata` → PAGE_READONLY

### Standard section names

| Name | Purpose |
|------|---------|
| .text | Executable code |
| .data | Initialized read-write data |
| .rdata | Initialized read-only data (strings, const, imports, exports) |
| .bss | Uninitialized data (zeroed at load) |
| .pdata | x64 exception unwind info (RUNTIME_FUNCTION array) |
| .xdata | UNWIND_INFO structures pointed to by .pdata |
| .reloc | Base relocations for ASLR |
| .rsrc | Resources (icons, version, manifest) |
| .tls | TLS directory + initializer |
| .CRT | CRT init/term callbacks |
| .didat | Delay-load imports |

---

## Export Table (DataDirectory[0])

### IMAGE_EXPORT_DIRECTORY

```c
typedef struct _IMAGE_EXPORT_DIRECTORY {
    DWORD   Characteristics;
    DWORD   TimeDateStamp;
    WORD    MajorVersion;
    WORD    MinorVersion;
    DWORD   Name;                    // RVA to module name string
    DWORD   Base;                    // Ordinal base (usually 1)
    DWORD   NumberOfFunctions;       // Count of EAT entries
    DWORD   NumberOfNames;           // Count of name entries (<= NumberOfFunctions)
    DWORD   AddressOfFunctions;      // RVA to DWORD array (EAT)
    DWORD   AddressOfNames;          // RVA to DWORD array of name RVAs
    DWORD   AddressOfNameOrdinals;   // RVA to WORD array of ordinal indices
} IMAGE_EXPORT_DIRECTORY;
```

### Name → function resolution

1. Iterate `AddressOfNames[i]` for `i` in `0..NumberOfNames`. Each is an RVA to a null-terminated ASCII string.
2. Match (or hash-match) against target name.
3. On match, read `AddressOfNameOrdinals[i]` — a 16-bit index into EAT.
4. Read `AddressOfFunctions[ordinal]` — this is the function's RVA, or a forwarder marker (see below).
5. Function address = `DllBase + function_RVA`.

**Subtle**: NumberOfFunctions >= NumberOfNames. Some exports are by ordinal only (no name). If you need ordinal-only exports, index `AddressOfFunctions` directly by `(ordinal - Base)`.

### Forwarded exports

If a function's `AddressOfFunctions[i]` RVA falls **within** the export directory's `[RVA, RVA+Size)` range, it is not a function but a forwarder string — a null-terminated ASCII `"dll.function"` or `"dll.#ordinal"`.

```c
DWORD exp_dir_rva  = nt->OptionalHeader.DataDirectory[0].VirtualAddress;
DWORD exp_dir_size = nt->OptionalHeader.DataDirectory[0].Size;
DWORD fn_rva       = eat[ordinal];

if (fn_rva >= exp_dir_rva && fn_rva < exp_dir_rva + exp_dir_size) {
    // Forwarder — parse the string
    const char* fwd = (const char*)(dll_base + fn_rva);
    // e.g., "KERNELBASE.GetProcAddress" or "NTDLL.RtlAllocateHeap"
    // Split on '.', resolve target module, recurse
} else {
    return dll_base + fn_rva;
}
```

Forwarders chain (sometimes 2–3 levels) — implement as a loop with a max iteration count (say 8) to avoid infinite cycles in malformed images.

---

## Import Table (DataDirectory[1]) and IAT (DataDirectory[12])

### IMAGE_IMPORT_DESCRIPTOR

One per imported DLL. Array terminated by a zero-filled entry.

```c
typedef struct _IMAGE_IMPORT_DESCRIPTOR {
    DWORD OriginalFirstThunk;  // RVA to INT (Import Name Table) — read-only
    DWORD TimeDateStamp;
    DWORD ForwarderChain;
    DWORD Name;                // RVA to DLL name (ASCII)
    DWORD FirstThunk;          // RVA to IAT — patched by loader
} IMAGE_IMPORT_DESCRIPTOR;
```

Both `OriginalFirstThunk` (INT) and `FirstThunk` (IAT) point to parallel arrays of `IMAGE_THUNK_DATA` entries. Each entry is a `ULONGLONG` on x64.

### IMAGE_THUNK_DATA semantics

- **High bit set** (`0x8000000000000000`): low 31 bits = ordinal number
- **High bit clear**: RVA to `IMAGE_IMPORT_BY_NAME` structure: `{ WORD Hint; CHAR Name[]; }`

Loader walks INT, resolves each name/ordinal, overwrites the parallel IAT slot with the resolved function address. After loader init, reading an IAT slot returns a function pointer.

**Offensive relevance**:
- Hooking imports = patching IAT slots. Unhooking = restoring original IAT.
- Reflective loading skips IAT population by design — must implement import resolution manually.
- Delay-load imports (DataDirectory[13]) resolve lazily on first call via `__delayLoadHelper2`.

---

## Relocations (DataDirectory[5])

When a DLL loads at an address other than its preferred `ImageBase`, all absolute addresses in code and data must be patched. The `.reloc` section describes which bytes need patching.

### IMAGE_BASE_RELOCATION (block header)

```c
typedef struct _IMAGE_BASE_RELOCATION {
    DWORD VirtualAddress;  // RVA of the 4KB page this block describes
    DWORD SizeOfBlock;     // Total bytes including header and entries
} IMAGE_BASE_RELOCATION;
// Followed by (SizeOfBlock - 8) / 2 entries of WORD:
//   High 4 bits: type (see below)
//   Low 12 bits: offset within the 4KB page
```

### Common relocation types

| Type | Value | Meaning |
|------|-------|---------|
| IMAGE_REL_BASED_ABSOLUTE | 0 | Padding, skip |
| IMAGE_REL_BASED_HIGHLOW | 3 | 32-bit absolute (x86) |
| **IMAGE_REL_BASED_DIR64** | **10** | **64-bit absolute (x64) — the one that matters** |

### Applying relocations

```c
ULONGLONG delta = (ULONGLONG)actual_base - nt->OptionalHeader.ImageBase;

DWORD reloc_rva  = nt->OptionalHeader.DataDirectory[5].VirtualAddress;
DWORD reloc_size = nt->OptionalHeader.DataDirectory[5].Size;

PBYTE block = actual_base + reloc_rva;
PBYTE end   = block + reloc_size;

while (block < end) {
    PIMAGE_BASE_RELOCATION hdr = (PIMAGE_BASE_RELOCATION)block;
    DWORD count = (hdr->SizeOfBlock - 8) / 2;
    PWORD entries = (PWORD)(hdr + 1);

    for (DWORD i = 0; i < count; i++) {
        WORD type   = entries[i] >> 12;
        WORD offset = entries[i] & 0xFFF;

        if (type == 10) {  // DIR64
            PULONGLONG target = (PULONGLONG)(actual_base + hdr->VirtualAddress + offset);
            *target += delta;
        }
    }
    block += hdr->SizeOfBlock;
}
```

---

## TLS Directory (DataDirectory[9])

Runs callbacks before `DllMain` / entry point.

### IMAGE_TLS_DIRECTORY64

```c
typedef struct _IMAGE_TLS_DIRECTORY64 {
    ULONGLONG StartAddressOfRawData;   // VA (not RVA!) to initialized TLS data start
    ULONGLONG EndAddressOfRawData;     // VA to end
    ULONGLONG AddressOfIndex;          // VA to DWORD that receives TLS slot index
    ULONGLONG AddressOfCallBacks;      // VA to null-terminated array of PIMAGE_TLS_CALLBACK
    DWORD     SizeOfZeroFill;
    DWORD     Characteristics;
} IMAGE_TLS_DIRECTORY64;
```

**Note**: these are VAs (absolute), not RVAs. They get relocated. In your own PE builder, emit them as DIR64 relocations pointing to your callback array.

### Callback signature

```c
VOID NTAPI TlsCallback(PVOID DllHandle, DWORD Reason, PVOID Reserved);
// Reason: DLL_PROCESS_ATTACH(1), DLL_THREAD_ATTACH(2),
//         DLL_THREAD_DETACH(3), DLL_PROCESS_DETACH(0)
```

### Callback execution order

At **process init**, for a statically-linked .exe:
1. All TLS callbacks of all statically-imported DLLs fire with DLL_PROCESS_ATTACH
2. Main exe's TLS callbacks fire
3. CRT init runs
4. Main exe entry point runs

**For a DLL loaded via LoadLibrary**:
1. TLS callbacks fire with DLL_PROCESS_ATTACH (for the **current** thread only)
2. DllMain fires
3. For each **subsequent** thread created: callbacks fire with DLL_THREAD_ATTACH

**Existing threads do not get DLL_THREAD_ATTACH.** This is a common source of "my TLS callback only fires for new threads" confusion.

### Malware relevance

TLS callbacks run before the entry point and before most debuggers break. Classic anti-analysis:
- Place `IsDebuggerPresent` check in first TLS callback
- Place unpacking stub in TLS callback
- Run before `main()` — debugger breakpoints at `main` are bypassed

To register a TLS callback from C/C++ source (MSVC):

```c
#pragma section(".CRT$XLB", long, read)

void NTAPI on_tls_event(PVOID h, DWORD reason, PVOID r) {
    if (reason == DLL_PROCESS_ATTACH) {
        // runs here before main()
    }
}

__declspec(allocate(".CRT$XLB"))
PIMAGE_TLS_CALLBACK p_tls_cb = on_tls_event;

// Prevent linker from dropping (needed for DLLs; .exe handled by CRT)
#ifdef _WIN64
    #pragma comment(linker, "/INCLUDE:_tls_used")
    #pragma comment(linker, "/INCLUDE:p_tls_cb")
#else
    #pragma comment(linker, "/INCLUDE:__tls_used")
    #pragma comment(linker, "/INCLUDE:_p_tls_cb")
#endif
```

---

## .pdata / .xdata — Exception and Unwind Data (DataDirectory[3])

x64 calling convention is **table-based**: there is no frame pointer by default. Unwinding for exceptions (and for offensive call-stack spoofing) relies on a per-function descriptor in `.pdata`.

See `references/exception-unwind.md` for full coverage. Summary here:

- `.pdata` is an array of `RUNTIME_FUNCTION` entries, sorted by `BeginAddress`
- Each `RUNTIME_FUNCTION` = `{BeginAddress, EndAddress, UnwindInfoAddress}` — all RVAs
- `UnwindInfoAddress` points into `.xdata` to an `UNWIND_INFO` structure
- `UNWIND_INFO` describes how to reverse the prologue: how much RSP was allocated, which callee-saved registers were pushed, where the frame pointer was established

The entire gadget discovery pipeline for DESYNC stack spoofing operates on `.pdata` scans.

---

## COFF Object Files (BOFs)

A COFF `.obj` file is a **subset** of PE:
- No `IMAGE_DOS_HEADER`
- No `IMAGE_NT_HEADERS` — file starts directly with `IMAGE_FILE_HEADER`
- No IAT / import table — unresolved symbols are marked in the symbol table
- Sections are present but **have file-relative relocations** (each section has its own reloc array)
- Symbol table and string table present (PE typically has them stripped)

### COFF-specific structures

**Relocation entry (10 bytes, unpadded)**:

```c
struct COFF_RELOC {
    DWORD VirtualAddress;    // offset within section
    DWORD SymbolTableIndex;  // index into symbol table
    WORD  Type;              // relocation type
};
// NOTE: This is 10 bytes on disk. If you declare it as a C struct,
// compiler may pad it to 12 bytes — use #pragma pack(push,1).
```

**Symbol entry (18 bytes, unpadded)**:

```c
struct COFF_SYMBOL {
    union {
        char ShortName[8];
        struct { DWORD Zeroes; DWORD NameOffset; } LongName;
    } N;
    DWORD Value;
    WORD  SectionNumber;
    WORD  Type;
    BYTE  StorageClass;
    BYTE  NumberOfAuxSymbols;
};
```

### Relocation types (x64) a BOF loader must handle

| Type | Value | Meaning |
|------|-------|---------|
| IMAGE_REL_AMD64_ABSOLUTE | 0 | No relocation |
| IMAGE_REL_AMD64_ADDR64 | 1 | 64-bit VA |
| IMAGE_REL_AMD64_ADDR32 | 2 | 32-bit VA |
| IMAGE_REL_AMD64_ADDR32NB | 3 | 32-bit address without ImageBase |
| IMAGE_REL_AMD64_REL32 | 4 | 32-bit relative displacement (CALL/JMP) |
| IMAGE_REL_AMD64_REL32_1 | 5 | REL32 with -1 byte correction |
| IMAGE_REL_AMD64_REL32_2 | 6 | REL32 with -2 byte correction |
| IMAGE_REL_AMD64_REL32_5 | 9 | REL32 with -5 byte correction |
| IMAGE_REL_AMD64_SECREL | 11 | Section-relative (debug info) |

### BOF loader workflow

1. Parse file header, section headers, symbol table, string table
2. Allocate RW memory for each section (combine section + alignment padding)
3. For each relocation:
   - Look up symbol → either internal (same COFF, add section base) or external (resolve via `__imp_DLL$Func` naming convention)
   - Apply patch based on relocation type
4. Flip section page protection: `.text` → RX, data sections → R/RW as appropriate
5. Call `go()` entry point

External symbol naming for BOFs follows the Cobalt Strike convention: `__imp_DLL$Function` where DLL is the module (e.g., `KERNEL32`) and Function is the export name. Loader parses this, resolves via PEB walk, patches as ADDR64.

---

## PE validation checklist

When parsing a user-supplied PE (sideloading, ad-hoc mapping), validate:

- [ ] `dos->e_magic == 0x5A4D`
- [ ] `dos->e_lfanew > 0 && dos->e_lfanew < image_size - sizeof(IMAGE_NT_HEADERS)`
- [ ] `nt->Signature == 0x00004550`
- [ ] `nt->FileHeader.Machine` matches expected arch
- [ ] `nt->OptionalHeader.Magic == 0x20B` (PE32+) or `0x10B` (PE32)
- [ ] `nt->OptionalHeader.SizeOfImage <= 256 MB` (sanity)
- [ ] `nt->FileHeader.NumberOfSections <= 96` (PE spec limit)
- [ ] For each section: `VirtualAddress + VirtualSize <= SizeOfImage`
- [ ] For each DataDirectory entry used: `VirtualAddress + Size <= SizeOfImage`

Skipping any of these on attacker-controlled PE is a heap overflow waiting to happen.

---

## PE sizing rules for in-memory loaders

- Allocate `SizeOfImage` bytes with `NtAllocateVirtualMemory`
- Copy headers: first `SizeOfHeaders` bytes from file → base
- For each section: copy `SizeOfRawData` bytes from file offset `PointerToRawData` to memory offset `VirtualAddress`
- Zero-fill sections with `VirtualSize > SizeOfRawData` (`.bss`)
- Apply relocations (if `ImageBase` differs from actual)
- Resolve imports: walk IMAGE_IMPORT_DESCRIPTOR, populate IAT
- Apply final page protections per section `Characteristics`
- Call TLS callbacks if `IMAGE_TLS_DIRECTORY` present
- Call DllMain with DLL_PROCESS_ATTACH

Reflective loaders that skip any of these fail on DLLs that depend on them (TLS-heavy DLLs, anything that registers SEH handlers on .pdata, anything using __declspec(dllexport) with IAT-bound exports, etc.).
