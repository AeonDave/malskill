# C BOF — API Reference (Cobalt Strike 4.12)

Load when writing or debugging C BOFs against the Beacon API, argument parser, and output helpers.

---

## 1. Data Parsing API

Parse arguments packed by the Aggressor `bof_pack()` function.

| Function | Signature | Description |
|----------|-----------|-------------|
| `BeaconDataParse` | `void BeaconDataParse(datap* parser, char* buffer, int size)` | Initialize parser on a packed argument buffer. |
| `BeaconDataPtr` | `char* BeaconDataPtr(datap* parser, int size)` | Read a raw pointer of `size` bytes. |
| `BeaconDataInt` | `int BeaconDataInt(datap* parser)` | Read a 4-byte integer. |
| `BeaconDataShort` | `short BeaconDataShort(datap* parser)` | Read a 2-byte short. |
| `BeaconDataLength` | `int BeaconDataLength(datap* parser)` | Read the length prefix of the next blob. |
| `BeaconDataExtract` | `char* BeaconDataExtract(datap* parser, int* size)` | Extract string/binary blob. Memory managed by Beacon. |

### Parsing order

Arguments must be read in the **exact order** they were packed by the CNA
script. Misaligned reads cause garbage data or crashes.

---

## 2. Format Buffer API

Build complex output without manual memory management.

| Function | Description |
|----------|-------------|
| `BeaconFormatAlloc(&fmt, maxsz)` | Allocate a format buffer on the Beacon heap. |
| `BeaconFormatReset(&fmt)` | Reset buffer position to 0. |
| `BeaconFormatAppend(&fmt, text, len)` | Append raw bytes. |
| `BeaconFormatPrintf(&fmt, fmtstr, ...)` | Append formatted text. |
| `BeaconFormatInt(&fmt, value)` | Append a 4-byte int. |
| `BeaconFormatToString(&fmt, &size)` | Get pointer and length of the buffer content. |
| `BeaconFormatFree(&fmt)` | Free the buffer (automatic at BOF exit). |

---

## 3. Output API

| Function | Signature | Description |
|----------|-----------|-------------|
| `BeaconOutput` | `void BeaconOutput(int type, const char* data, int len)` | Send raw/binary data to the operator. |
| `BeaconPrintf` | `void BeaconPrintf(int type, const char* fmt, ...)` | Formatted output to the Beacon console. |
| `BeaconDownload` | `BOOL BeaconDownload(const char* filename, const char* buffer, unsigned int length)` | Download a file to the operator. |
| `BeaconGetOutputData` | `char* BeaconGetOutputData(int* outLen)` | Retrieve accumulated output data from the current BOF execution. |

### Output type constants

| Constant | Value | Meaning |
|----------|-------|---------|
| `CALLBACK_OUTPUT` | `0x0` | Standard output |
| `CALLBACK_OUTPUT_OEM` | `0x1e` | OEM-encoded output |
| `CALLBACK_OUTPUT_UTF8` | `0x20` | UTF-8 output |
| `CALLBACK_ERROR` | `0x0d` | Error output |
| `CALLBACK_FILE` | `0x02` | File download start |
| `CALLBACK_FILE_WRITE` | `0x08` | File download chunk |
| `CALLBACK_FILE_CLOSE` | `0x09` | File download end |
| `CALLBACK_SCREENSHOT` | `0x03` | Screenshot data |
| `CALLBACK_CUSTOM` | `0x1000` | Custom callback (range start) |
| `CALLBACK_CUSTOM_LAST` | `0x13ff` | Custom callback (range end) |

---

## 4. Token API

| Function | Description |
|----------|-------------|
| `BeaconUseToken(HANDLE token)` | Impersonate using the given token. |
| `BeaconRevertToken()` | Revert to the Beacon's default token. |
| `BeaconIsAdmin()` | Returns `TRUE` if current context is elevated. |

---

## 5. Spawn & Inject API

| Function | Description |
|----------|-------------|
| `BeaconGetSpawnTo(x86, buffer, length)` | Get the configured spawnto path. |
| `BeaconInjectProcess(hProc, pid, payload, p_len, p_offset, arg, a_len)` | Inject payload into an existing process. |
| `BeaconInjectTemporaryProcess(pInfo, payload, p_len, p_offset, arg, a_len)` | Inject into a temporary (sacrificial) process. |
| `BeaconSpawnTemporaryProcess(x86, ignoreToken, si, pInfo)` | Spawn a temporary process for injection. |
| `BeaconCleanupProcess(pInfo)` | Cleanup a spawned temporary process. |

---

## 6. Utility API

| Function | Description |
|----------|-------------|
| `toWideChar(src, dst, max)` | Convert a `char*` string to `wchar_t*`. |
| `swap_endianess(value)` | Swap byte order (endianness) of a value. |

---

## 7. Beacon Information API (CS 4.9+)

```c
DECLSPEC_IMPORT BOOL BeaconInformation(PBEACON_INFO info);
```

Returns beacon metadata including version, sleep mask info, heap records,
XOR mask, and allocated memory regions. Key fields of `BEACON_INFO`:

- `version` — CS version (e.g., `0x041200` = 4.12)
- `sleep_mask_ptr`, `sleep_mask_text_size`, `sleep_mask_total_size`
- `beacon_ptr` — Beacon base address
- `heap_records` — heap entries for sleep mask
- `mask[13]` — random XOR mask
- `allocatedMemory` — memory regions info (for UDRL/sleepmask)

---

## 8. Key/Value Store API (CS 4.9+)

Persist data across multiple BOF executions within the same Beacon session.

| Function | Description |
|----------|-------------|
| `BeaconAddValue(key, ptr)` | Associate a key string to a memory address. |
| `BeaconGetValue(key)` | Retrieve a previously stored pointer. Returns `NULL` if not found. |
| `BeaconRemoveValue(key)` | Remove a key-value association. |

> **Note:** Beacon does **not** mask or free the stored memory.
> The BOF is responsible for managing the content's lifetime.

---

## 9. Syscall API (CS 4.10+)

BOFs can use Beacon's built-in syscall mechanism (indirect syscalls).

### Retrieving syscall information

```c
BEACON_SYSCALLS sc;
BeaconGetSyscallInformation(&sc, sizeof(sc));
// Access: sc.syscalls.ntAllocateVirtualMemory.fnAddr, .jmpAddr, .sysnum
```

The `SYSCALL_API` struct provides entries for 35+ NT functions including:
`ntAllocateVirtualMemory`, `ntProtectVirtualMemory`, `ntFreeVirtualMemory`,
`ntOpenProcess`, `ntOpenThread`, `ntClose`, `ntCreateSection`,
`ntMapViewOfSection`, `ntReadVirtualMemory`, `ntWriteVirtualMemory`,
`ntCreateFile`, `ntQuerySystemInformation`, and more.

### Beacon syscall wrappers

Use these instead of standard Win32 calls to leverage Beacon's syscall method:

| Wrapper | Replaces |
|---------|----------|
| `BeaconVirtualAlloc(addr, size, type, protect)` | `VirtualAlloc` |
| `BeaconVirtualAllocEx(hProc, addr, size, type, protect)` | `VirtualAllocEx` |
| `BeaconVirtualProtect(addr, size, newProtect, oldProtect)` | `VirtualProtect` |
| `BeaconVirtualProtectEx(hProc, addr, size, new, old)` | `VirtualProtectEx` |
| `BeaconVirtualFree(addr, size, freeType)` | `VirtualFree` |
| `BeaconVirtualQuery(addr, mbi, length)` | `VirtualQuery` |
| `BeaconOpenProcess(access, inherit, pid)` | `OpenProcess` |
| `BeaconOpenThread(access, inherit, tid)` | `OpenThread` |
| `BeaconCloseHandle(handle)` | `CloseHandle` |
| `BeaconGetThreadContext(hThread, ctx)` | `GetThreadContext` |
| `BeaconSetThreadContext(hThread, ctx)` | `SetThreadContext` |
| `BeaconResumeThread(hThread)` | `ResumeThread` |
| `BeaconUnmapViewOfFile(addr)` | `UnmapViewOfFile` |
| `BeaconDuplicateHandle(...)` | `DuplicateHandle` |
| `BeaconReadProcessMemory(...)` | `ReadProcessMemory` |
| `BeaconWriteProcessMemory(...)` | `WriteProcessMemory` |

---

## 10. Dynamic Function Resolution (DFR)

Declare Win32 functions with the `MODULE$Function` naming convention:

```c
DECLSPEC_IMPORT HANDLE WINAPI KERNEL32$OpenProcess(DWORD, BOOL, DWORD);
DECLSPEC_IMPORT BOOL   WINAPI KERNEL32$CloseHandle(HANDLE);
DECLSPEC_IMPORT BOOL   WINAPI ADVAPI32$OpenProcessToken(HANDLE, DWORD, PHANDLE);
DECLSPEC_IMPORT NTSTATUS NTAPI NTDLL$NtQuerySystemInformation(ULONG, PVOID, ULONG, PULONG);
```

### Common modules

| Module | Typical functions |
|--------|-------------------|
| `KERNEL32` | Process, thread, memory, file, pipe operations |
| `ADVAPI32` | Token, privilege, registry, service operations |
| `NTDLL` | Native API (`Nt*` / `Zw*` / `Rtl*`) |
| `USER32` | Window, message, clipboard operations |
| `SHELL32` | Shell execute, path operations |
| `OLE32` | COM initialization |
| `MSVCRT` | C runtime helpers (`_snprintf`, `memcpy`, etc.) |
| `IPHLPAPI` | Network adapter, routing, ARP |
| `WS2_32` | Winsock (sockets, DNS) |
| `NETAPI32` | User, group, share enumeration |
| `SECUR32` | SSPI, credentials |
| `WINHTTP` | HTTP client operations |

---

## 11. Aggressor Script (CNA) integration

Minimal CNA to register and invoke a BOF:

```sleep
alias mybof {
    local('$handle $args');
    $handle = openf(script_resource("mybof.o"));
    $args   = bof_pack($1, "iz", 1234, "C:\\Windows");
    beacon_inline_execute($1, readb($handle, -1), "go", $args);
    closef($handle);
}

beacon_command_register(
    "mybof",
    "Run mybof BOF",
    "Usage: mybof <pid> <path>"
);
```

### bof_pack format characters

| Char | C Type | Description |
|------|--------|-------------|
| `i` | `int` | 4-byte integer |
| `s` | `short` | 2-byte short |
| `z` | `char*` | Null-terminated ASCII string |
| `Z` | `wchar_t*` | Null-terminated wide string |
| `b` | `char*` | Binary blob (length-prefixed) |

---

## 12. Common errors and fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `undefined reference to 'BeaconPrintf'` | Missing `beacon.h` or wrong include path | Add `-I./assets`, ensure `beacon.h` present |
| `relocation truncated to fit` | Code too large for COFF `.text` | Split functions, use `-ffunction-sections` |
| `.eh_frame` too large | Unwinding tables | Add `-fno-asynchronous-unwind-tables` |
| Crash on `BeaconDataExtract` | Argument order mismatch | Verify CNA `bof_pack` order matches C parse |
| `multiple definition of 'go'` | Duplicate entrypoint | Only one `go()` per BOF |
| Stack overflow | Large local buffers | Use `static` or `BeaconFormatAlloc` |
| `undefined reference to __imp_*` | Missing DFR declaration | Add `DECLSPEC_IMPORT` with `MODULE$Function` |

---

## 13. Local testing without Cobalt Strike

Use [COFFLoader](https://github.com/trustedsec/COFFLoader) or
[RunOF](https://github.com/nettitude/RunOF) to execute BOFs locally.

```bash
./scripts/build_bof.sh mybof.c
COFFLoader.exe mybof.o
```

---

## 14. Framework-specific loader notes

### Cobalt Strike

- CNA integration via `beacon_inline_execute()` and `bof_pack()`
- CS 4.9+: Key/Value Store (`BeaconAddValue`/`GetValue`/`RemoveValue`)
- CS 4.10+: Syscall API (`BeaconGetSyscallInformation`, `BeaconVirtualAllocEx`, etc.)
- CS 4.11+: BeaconGate for intercepting API calls via Sleep Mask

### Sliver

- Requires both x64 and x86 object files in extension bundle
- Uses `extension.json` manifest instead of CNA
- DFR convention identical (`MODULE$Function`)

### Havoc / Brute Ratel / other COFF loaders

- DFR convention is universal across BOF-compatible loaders
- Some loaders may not support all Beacon API functions (KV store, syscall wrappers)
- Always test with the target loader before assuming API availability
