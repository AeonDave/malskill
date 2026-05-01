# PE Reverse Engineering Supplement

Load this after `triage.md` and `re-workflow.md` when the target is a native Windows PE. This file only covers PE-specific pivots: loader behavior, resources, TLS, import reconstruction, and section anomalies.

## PE-only fast checks

```bash
r2 sample.exe -q -c "iI;iS;ii;ie;izz;q"
strings -a -e l sample.exe | grep -iE "powershell|cmd.exe|run|registry|service|mutex"
```

Prioritize these questions:

1. **Managed or native?** If CLR metadata exists, pivot to `dotnet-rev.md`.
2. **Packed or loader-style?** Few imports, high-entropy `.text`, or RWX sections mean unpack first.
3. **Resource-heavy?** Check `.rsrc` early for config blobs, stage-2 payloads, icons, and manifests.
4. **Pre-entry execution?** TLS callbacks or CRT initializers may run before `main`.

## Loader-aware workflow

### 1. Map the file layout

- Section names, permissions, and entropy are more useful than raw strings alone.
- Suspicious patterns:
	- executable + writable section
	- entry point outside `.text`
	- tiny import table with complex behavior
	- oversized `.rsrc` or overlay data

```bash
r2 sample.exe -q -c "iS;q"
rabin2 -O sample.exe    # overlay / appended data if present
```

### 2. Inspect PE-specific metadata

- **Imports**: injection, crypto, service, registry, COM, or networking APIs
- **Exports**: DLL command handlers, plugin entrypoints, COM registration helpers
- **Manifest**: requested privileges, auto-elevation hints, CLR/runtime version
- **Relocations**: stripped relocations can hint at packers/manual mapping
- **Signing**: valid signature helps provenance; invalid signature can still be a clue

### 3. Check pre-main execution paths

- **TLS callbacks**: anti-debug, unpacking stubs, early config decryptors
- **CRT initializers**: `_initterm`, global constructors, C++ static objects
- **SEH/VEH registration**: used for control-flow tricks or hidden logic

```text
PE workflow order: TLS callbacks -> CRT startup -> entry point -> worker threads
```

### 4. Treat `.rsrc` as an analysis target, not decoration

Common uses:

- encrypted configs or shellcode blobs
- embedded DLL/EXE stage loaders
- ransom notes or extension lists
- decoy UIs hiding a malicious worker thread

If imports are thin but `.rsrc` is large, extract resources before deep decompilation.

### 5. Unpacking and import reconstruction

When a PE allocates memory, writes code, and transfers execution, capture the **post-unpack** image rather than over-analyzing the stub.

```text
stub -> VirtualAlloc/WriteProcessMemory/memcpy -> jump/call into new region -> dump -> rebuild IAT
```

After the dump:

- confirm OEP lands in plausible code
- rebuild imports before trusting decompilation
- rerun `triage.md` on the dumped image

## Format-specific checklists

### Malware / loader checklist

- `VirtualAlloc`, `VirtualProtect`, `WriteProcessMemory`, `CreateRemoteThread`
- `LoadLibrary` / `GetProcAddress` resolver loops
- mutex strings, service names, scheduled task XML, Run keys
- overlay/config appended after last section

### Installer / trojanized app checklist

- manifest requesting admin privileges
- dropped MSI/service driver helpers
- signed outer wrapper but unsigned inner payload
- UI thread clean, worker thread suspicious

### Patch-diff checklist

- new bounds checks in parsing code
- import changes (`WinVerifyTrust`, crypto, URL parsing)
- resource/template changes affecting protocol or file format handling

## Common pitfalls

- **Reading only imports**: shellcode loaders resolve APIs dynamically.
- **Ignoring TLS**: the interesting code may run before the debugger reaches the entry point.
- **Skipping `.rsrc`**: many families keep config or stage-2 there.
- **Diffing packed builds**: unpack both versions first or the diff is mostly noise.
- **Forgetting the overlay**: appended data often contains config, shellcode, or encrypted payloads.

