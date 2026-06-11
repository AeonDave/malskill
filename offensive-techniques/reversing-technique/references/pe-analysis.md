# PE and .NET Analysis Procedure

Detailed workflow for analyzing Windows PE executables, DLLs, and .NET assemblies. This supplements the main workflow in SKILL.md — load this reference when the sample is identified as PE.

## Triage

1. Confirm PE format: check `MZ` magic at offset 0, `PE\x00\x00` at `e_lfanew`
2. Determine PE32 vs PE32+ (optional header magic `0x10B` vs `0x20B`)
3. Record: machine type, timestamp, entry point RVA, image base, subsystem, DLL characteristics
4. Check for .NET: look for `IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR` (data directory index 14); if present, this is a .NET assembly

## Section analysis

For each section, record name, virtual size, raw size, entropy, and characteristics flags.

**Red flags:**
- Section with entropy > 7.0 and executable flag — likely packed or encrypted payload
- Section named `.text` with very high entropy — possible in-place encryption
- Non-standard section names (`.vmp`, `.themida`, `.aspack`, `.MPRESS`) — known packers
- Large discrepancy between virtual size and raw size — possible unpacking stub
- Writable + executable sections — self-modifying code

## Import analysis

Use `scripts/iat_analyzer.py` or `r2`/`rabin2`/`pefile` to extract the import table.

**Focus areas:**
- *Injection pattern:* VirtualAllocEx + WriteProcessMemory + CreateRemoteThread
- *Process hollowing:* CreateProcess (suspended) + NtUnmapViewOfSection + WriteProcessMemory + ResumeThread
- *Manual DLL loading:* LoadLibraryA/W, GetProcAddress (indicates runtime API resolution)
- *Evasion:* IsDebuggerPresent, NtQueryInformationProcess, GetTickCount, QueryPerformanceCounter
- *Crypto:* CryptEncrypt/Decrypt, BCrypt*, CNG functions
- *Network:* WinHTTP, WinINet, Winsock, URLDownloadToFile

**Low import count** (< 10 functions) with high entropy = likely packed; real imports resolved at runtime.

## .NET specific

1. Decompile with `ilspycmd -p -o ./decompiled sample.exe`
2. If obfuscated (ConfuserEx, .NET Reactor, SmartAssembly), try `monodis` for IL-level inspection
3. Search decompiled source for: `WebClient`, `HttpClient`, `Process.Start`, `Assembly.Load`, reflection, base64 operations
4. Check for `DllImport` / P/Invoke calls — these bridge to native code
5. Look for embedded resources: `Assembly.GetManifestResourceStream`, resource extractor

## Resource and overlay analysis

1. Parse resource directory (data directory index 2) for embedded binaries, configs, icons with suspicious payloads
2. Check overlay data (anything past the last section's raw data end) — common location for encrypted payloads, configs, or additional stages
3. Check for certificates (data directory index 4) — invalid/self-signed certs, or cert used as data carrier

## Packer identification

Use one of:
- `capa` — reports packing capabilities
- Detect It Easy (`diec`) — signature-based packer identification
- Section names and import patterns (manual)

Common packers: UPX, Themida/WinLicense, VMProtect, ASPack, MPRESS, .NET Reactor, ConfuserEx

For UPX: try `upx -d sample.exe` first. If it fails, the sample may be modified UPX.

## Config extraction strategy

Many malware families store config in predictable locations:
1. **XOR-encrypted in .data or .rdata** — scan for repeating XOR keys, try common key sizes (1, 4, 8, 16, 32 bytes)
2. **Base64 in strings** — decode and check for readable config (JSON, XML, key=value)
3. **Resource section** — extract named resources, check for encrypted blobs
4. **Overlay** — carve data after last section, attempt common decryption
5. **Registry at runtime** — check for registry path strings indicating runtime config storage

## Reverse engineering escalation

When triage and import analysis are insufficient:

1. **Start with entry point** — disassemble entry point function, follow the call chain
2. **Identify the "real" main** — many packers/loaders jump to unpacked code; look for indirect calls/jumps after decryption loops
3. **Focus on network functions** — set xrefs from imported network APIs and trace backwards to find C2 construction
4. **Trace crypto calls** — xrefs from CryptEncrypt/BCrypt* lead to encryption key setup and data being encrypted/decrypted
5. **String references** — from suspicious strings (URLs, registry paths, mutexes), follow xrefs to containing functions

Tool workflow:
- Quick analysis: `r2 -q -c "aaa; afl; s main; pdf" sample.exe` (see `radare2` skill)
- Deep analysis: Ghidra headless or GUI for decompilation (see `ghidra` skill)
- Dynamic: x64dbg for unpacking and runtime analysis (see `x64dbg` skill)
