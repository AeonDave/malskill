# PE Reverse Engineering Supplement

Load this after `triage.md` and `re-workflow.md` when the target is a native Windows PE. This file focuses on PE-specific pivots: loader behavior, RVA/file-offset mapping, data directories, resources, TLS callbacks, import reconstruction, unpacking, and Windows mitigation context.

## Table of contents

- [PE-only fast checks](#pe-only-fast-checks)
- [Loader-aware workflow](#loader-aware-workflow)
- [Import, export, and API-resolution pivots](#import-export-and-api-resolution-pivots)
- [Pre-entry execution paths](#pre-entry-execution-paths)
- [Resources, overlay, and signatures](#resources-overlay-and-signatures)
- [Unpacking and import reconstruction](#unpacking-and-import-reconstruction)
- [Mitigation and exploitability handoff](#mitigation-and-exploitability-handoff)
- [Format-specific checklists](#format-specific-checklists)
- [Common pitfalls](#common-pitfalls)
- [Research trail](#research-trail)

## PE-only fast checks

```bash
r2 sample.exe -q -c "iI;iS;ii;ie;izz;q"
rabin2 -I sample.exe
rabin2 -S sample.exe
rabin2 -i sample.exe
rabin2 -E sample.exe
rabin2 -O sample.exe
strings -a -e l sample.exe | grep -iE "powershell|cmd.exe|run|registry|service|mutex|http|user-agent"
```

Windows-native alternatives:

```text
dumpbin /headers sample.exe
dumpbin /imports sample.exe
dumpbin /exports sample.dll
dumpbin /loadconfig sample.exe
sigcheck -m sample.exe
```

Answer these before deep decompilation:

1. **Managed or native?** If the CLR runtime header exists, pivot to `dotnet-rev.md`.
2. **Packed or loader-style?** Few imports, high-entropy code, RWX sections, or entrypoint outside normal code means unpack first.
3. **What is mapped at runtime?** Distinguish raw file offsets, RVAs, VAs, overlay bytes, and certificate data.
4. **Pre-entry execution?** TLS callbacks, CRT initializers, or loader notifications may run before the apparent entry point.
5. **How are APIs resolved?** Static imports, delay imports, forwarded exports, API Set redirection, or hash-based PEB walking require different evidence.
6. **Which mitigations matter?** `DYNAMIC_BASE`, `NX_COMPAT`, `GUARD_CF`, SafeSEH, `/GS`, and CET change exploitability assumptions.

## Loader-aware workflow

### 1. Map PE geometry before trusting addresses

PE analysis constantly switches between raw file offsets, RVAs, and VAs:

- **Raw file offset**: byte position in the file on disk.
- **RVA**: virtual address minus image base after mapping.
- **VA**: process virtual address after image base selection.
- **Section raw data**: `PointerToRawData` and `SizeOfRawData` in the section header.
- **Section memory range**: `VirtualAddress` and `VirtualSize`; sections are aligned by `SectionAlignment`, raw data by `FileAlignment`.

RVA-to-file-offset gate:

```text
Find section where:
  section.VirtualAddress <= RVA < section.VirtualAddress + max(section.VirtualSize, section.SizeOfRawData)

Then:
  file_offset = section.PointerToRawData + (RVA - section.VirtualAddress)
```

Caveats that matter during RE:

- Data-directory RVAs do **not** need to point to a section named `.idata`, `.rsrc`, `.tls`, etc.; section names are conventions, not loader truth.
- The Certificate Table data-directory entry is an exception: its `VirtualAddress` is a **file offset**, not an RVA, and certificates are not mapped into process memory.
- Overlay bytes after the last section are not mapped by the normal image loader. Packers and installers often use them anyway.
- `SizeOfRawData` can be larger than `VirtualSize`, or `VirtualSize` can imply zero-filled memory beyond disk bytes.
- Corkami-style malformed/tiny PEs prove why parser agreement is evidence: if `pefile`, `rabin2`, `dumpbin`, and the Windows loader disagree, debug the loader behavior, not only the file parser.

### 2. Read data directories as the loader's index

Prioritize these Optional Header data directories:

| Directory | Why it matters |
|---|---|
| Export Table | DLL API surface, forwarded exports, ordinal-only handlers, plugin callbacks |
| Import Table | Static dependency and first-pass API capability map |
| Resource Table | Configs, embedded stages, manifests, icons, version metadata |
| Exception Table / `.pdata` | x64 unwind info, SEH clues, stack-walk correctness, ROP/unwind handoff |
| Certificate Table | Authenticode material; file-offset data, not mapped memory |
| Base Relocation Table | ASLR viability and manual-mapping clues |
| TLS Table | Pre-entry callbacks and static TLS state |
| Load Config Table | SafeSEH, CFG, security cookie, Guard flags, loader flags |
| IAT | Loader-patched imported function pointers |
| Delay Import Descriptor | APIs resolved on first use, often missed in import-only triage |
| CLR Runtime Header | Managed-code pivot; do not treat as pure native until ruled out |

### 3. Reconstruct the loader timeline

Use this mental model when a debugger seems to “skip” important code:

```text
Map image -> apply base relocations -> resolve static imports -> process loader metadata
-> run TLS callbacks -> CRT startup/global constructors -> AddressOfEntryPoint/DllMain
-> worker threads, delay imports, dynamic LoadLibrary/GetProcAddress resolution
```

Important details:

- If the image is not loaded at `ImageBase`, the loader applies `.reloc` base relocations. If relocations are stripped, rebasing can fail or force fixed-base assumptions.
- Static imports populate the IAT before user entry. Delay imports are resolved by helper thunks later, often at the first call site.
- TLS callbacks are invoked before normal entry and on later thread attach/detach events.
- CRT startup initializes `/GS` cookie state and runs C/C++ global constructors before user `main`/`WinMain`.
- DLLs may do meaningful work in `DllMain`, exported functions, TLS callbacks, COM registration exports, or service entrypoints; do not anchor only on EXE-style `main`.

### 4. Correlate static and dynamic loader evidence

Static metadata tells you what the file claims. Dynamic evidence tells you what Windows actually maps and calls.

Useful dynamic breakpoints/watchpoints:

- `kernel32!LoadLibraryA/W`, `kernelbase!LoadLibraryExW`, `ntdll!LdrLoadDll`
- `kernel32!GetProcAddress`, `ntdll!LdrGetProcedureAddress`
- `kernel32!VirtualAlloc`, `ntdll!NtAllocateVirtualMemory`, `kernel32!VirtualProtect`, `ntdll!NtProtectVirtualMemory`
- `kernel32!WriteProcessMemory`, `ntdll!NtWriteVirtualMemory`, `RtlMoveMemory`, `memcpy`
- `CreateThread`, `CreateRemoteThread`, `NtCreateThreadEx`, threadpool APIs
- TLS callback addresses and `AddressOfEntryPoint`

When static and dynamic views disagree, preserve both: the delta often identifies a packer, manual mapper, anti-analysis trick, or parser-abuse sample.

## Import, export, and API-resolution pivots

### Static imports and IAT

The import directory identifies DLLs and imported names/ordinals. The Import Lookup Table describes imports by name or ordinal; the IAT has the same initial shape but is overwritten by the loader with real function VAs.

RE signals:

- A direct `call qword ptr [rip + __imp_Function]` indicates an imported code symbol via IAT indirection.
- A thunk like `Function: jmp qword ptr [__imp_Function]` is the PE analogue of an ELF PLT-style stub.
- Import-by-ordinal hides names; resolve against the exact DLL version when behavior matters.
- Forwarded exports make one DLL export point to another DLL's symbol, such as `KERNEL32` forwarding to `NTDLL`/`KERNELBASE` paths.
- API Set redirection can make imports appear to target `api-ms-win-*` facade DLLs while the loader resolves host DLLs at runtime.

### Delay imports

Delay-load descriptors hold a delay IAT and delay import name table. The helper updates pointers when the function is first called.

Practical workflow:

1. List normal imports and delay imports separately.
2. Break on delay helper code or `LdrLoadDll`/`LdrGetProcedureAddress`.
3. Trigger the relevant feature path.
4. Re-snapshot the IAT/delay IAT after resolution.

### Dynamic API resolution and API hashing

Packed or evasive samples often avoid a useful import table.

Common patterns:

- PEB walk through `PEB->Ldr` module lists.
- Export-directory iteration over `AddressOfNames`, `AddressOfNameOrdinals`, and `AddressOfFunctions`.
- Hash loops over DLL and API names, then indirect calls through resolved pointers.
- Late `LoadLibrary`/`GetProcAddress` calls after string decryption.

Evidence to capture:

- Hash constants and normalization rules (case-folding, rotate direction, seed).
- Resolved DLL/API pairs at runtime.
- Call site using the resolved pointer.
- Whether resolution happens before or after unpacking/string decryption.

## Pre-entry execution paths

### TLS callbacks

TLS callback addresses live in the TLS directory as a null-terminated array. They run before the declared entrypoint and can run again for thread events.

Common offensive/RE uses:

- anti-debug checks before your entrypoint breakpoint
- unpacking or section permission changes
- import table tampering
- early config decryption
- fake callback arrays to confuse parsers

Fast checks:

```text
dumpbin /headers sample.exe      # TLS directory RVA/size
r2 sample.exe -q -c "iI;is~TLS;iz~tls;q"
```

### CRT initializers and exception registration

After TLS, CRT startup may call `_initterm`/global constructors before user code. C++ objects, static initialization, SEH/VEH registration, and security-cookie initialization can all appear here.

Do not label CRT as noise until you identify where control leaves generic runtime code and enters sample-specific logic.

## Resources, overlay, and signatures

### `.rsrc` is structured data, not decoration

The resource table is a Type -> Name -> Language tree. Each leaf points to raw resource data.

Common high-value resource types:

- `RT_RCDATA`: encrypted config, shellcode, DLL/EXE stage, license blob.
- `RT_VERSION`: company/product/version inconsistencies and campaign metadata.
- `RT_MANIFEST`: requested privileges, UAC behavior, DPI/compatibility settings.
- `RT_STRING`, dialogs, icons: decoys, ransom notes, UI flows, localization hints.

If imports are thin but `.rsrc` is large or high-entropy, extract resources before decompiling the stub.

### Overlay and appended data

Overlay data starts after the highest raw section end. It is common in installers, SFX archives, droppers, and packers.

Treat overlay as a separate artifact:

- hash it independently
- run `strings`/entropy on it
- try archive extraction (`7z`, `binwalk`) when magic bytes appear
- correlate file offsets referenced by the stub with overlay ranges

### Authenticode and certificate table traps

The Attribute Certificate Table is file data, not mapped image memory. Authenticode hashing excludes the checksum field and certificate table, and data past the end of the last section has special handling. Therefore:

- a signature does not mean “no appended data”
- appended data does not automatically explain whether signature validation succeeds
- verify with a real trust check (`sigcheck`, `WinVerifyTrust`) before drawing provenance conclusions

## Unpacking and import reconstruction

When a PE allocates memory, writes code, changes permissions, and transfers execution, analyze the unpacked image rather than overfitting the stub.

```text
stub -> allocate/write/decrypt -> set RX/RWX -> transfer to OEP -> dump -> rebuild IAT -> rerun triage
```

### OEP discovery gates

Look for one or more of these before dumping:

- execution leaves the original packed section and enters newly executable memory
- a large memory region becomes executable after `VirtualProtect`/`NtProtectVirtualMemory`
- import resolver loops finish and API pointers are stable
- long jump/call returns from a decompression/decryption loop into plausible compiler output
- strings and imports suddenly become meaningful in memory
- thread start address lands in the unpacked region

### Dump and repair checklist

After dumping:

1. Set the correct image base and OEP.
2. Rebuild imports with the runtime IAT, not the stub's minimal import table.
3. Fix section permissions/sizes enough for the decompiler to reason correctly.
4. Preserve the original sample and dump as separate layers.
5. Rerun `triage.md` on the dumped image.
6. Validate at least one behavior from the dump against runtime traces.

Recommended evidence block:

```text
Original SHA256:
Packer/stub indicators:
Allocation/protection API trace:
OEP evidence:
Dump tool and settings:
IAT rebuild evidence:
Behavior validated after dump:
Unresolved anti-dump/anti-debug notes:
```

## Mitigation and exploitability handoff

For memory-corruption work, record mitigations per module, not just for the main EXE.

| Mitigation | PE evidence | RE/exploitability meaning |
|---|---|---|
| ASLR | `DYNAMIC_BASE`, `.reloc`, actual runtime base | Rebasing needs relocations; `/HIGHENTROPYVA` increases 64-bit entropy when effective |
| DEP | `NX_COMPAT`, memory permissions | Stack/heap data execution assumptions change; focus on code-reuse or permission changes |
| CFG | `GUARD_CF`, Load Config Guard flags/table | Indirect calls are checked against valid call targets on CFG-aware systems |
| SafeSEH | x86 Load Config SE handler table | SEH overwrite viability changes for 32-bit modules |
| SEHOP | OS/runtime policy plus SEH chain behavior | Exception-chain attacks need runtime validation, not only file metadata |
| `/GS` | Load Config security cookie plus function prologues | Stack overwrite needs cookie leak/bypass or non-cookie path |
| CET | Extended DLL characteristics / platform policy | Shadow-stack/IBT affects return/indirect-branch assumptions |

Before claiming exploitability, pivot to `binary-exploitation-capability.md` and preserve:

- exact module and version
- architecture and subsystem
- runtime base addresses
- section permissions
- relevant data directories
- mitigation flags and OS policy
- crash/control evidence

## Format-specific checklists

### Malware / loader checklist

- `VirtualAlloc`, `VirtualProtect`, `WriteProcessMemory`, `CreateRemoteThread`, `NtCreateThreadEx`
- `LoadLibrary` / `GetProcAddress` / PEB export-walking resolver loops
- mutex strings, service names, scheduled task XML, Run keys, COM registration
- TLS callbacks, VEH/SEH registration, loader snaps, unusual load config
- overlay/config appended after last section
- signed wrapper with unsigned or memory-only inner payload

### Installer / trojanized app checklist

- manifest requesting admin privileges
- dropped MSI/service/driver helpers
- legitimate UI thread but suspicious worker thread
- resources or overlay containing encrypted payloads
- mismatched version info, PDB path, certificate identity, or timestamp story

### Vulnerability-hunting checklist

- parser entrypoints from file-open, decompression, image/audio/archive libraries, IPC, RPC, named pipes
- module-specific ASLR/DEP/CFG/SafeSEH context before exploit assumptions
- exception/unwind metadata if crashes involve C++ exceptions or x64 unwinding
- allocator and size calculations around attacker-controlled lengths

### Patch-diff checklist

- new bounds checks in parsing code
- import changes (`WinVerifyTrust`, crypto, URL parsing, decompression)
- resource/template changes affecting protocol or file format handling
- load-config or mitigation flag changes between builds
- packed builds unpacked before diffing

## Common pitfalls

- **Confusing RVA with file offset**: certificate tables and overlay data are the classic foot-guns.
- **Reading only imports**: shellcode loaders resolve APIs dynamically or through delay imports.
- **Ignoring TLS**: the interesting code may run before the debugger reaches the entry point.
- **Skipping `.rsrc`**: many families keep config, stages, or manifests there.
- **Trusting section names**: the loader follows headers and data directories, not your expectations.
- **Diffing packed builds**: unpack both versions first or the diff is mostly packer noise.
- **Forgetting module scope**: mitigations and relocations are per image; injected or loaded DLLs may differ from the main EXE.
- **Overtrusting signatures**: Authenticode helps provenance only after real validation and overlay/certificate-table review.

## Research trail

- [Microsoft PE/COFF specification](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format) — ground truth for headers, data directories, RVA semantics, imports, resources, relocations, TLS, load config, and Authenticode hashing.
- [Corkami PE corpus](https://github.com/corkami/pocs/tree/master/PE) — adversarial PE edge cases for parser skepticism: tiny PEs, TLS tricks, broken imports, overlays, reloc abuse, CFG oddities, and malformed section geometry.
- [MaskRay, Linker notes on PE/COFF](https://maskray.me/blog/2023-12-03-linker-notes-on-pe-coff) — import libraries, `__imp_` symbols, import thunks, MinGW differences, and ELF-vs-PE linking contrasts.
- [Microsoft `/guard:cf`](https://learn.microsoft.com/en-us/cpp/build/reference/guard-enable-control-flow-guard) — CFG compiler/linker behavior and `dumpbin /loadconfig` verification.
- [Microsoft `/DYNAMICBASE`](https://learn.microsoft.com/en-us/cpp/build/reference/dynamicbase-use-address-space-layout-randomization) — ASLR header behavior and `/HIGHENTROPYVA` dependency.
- Corelan, Black Hat unpacking material, and malware RE handbooks — practical OEP discovery, dumping, import reconstruction, and anti-debug workflow patterns.
