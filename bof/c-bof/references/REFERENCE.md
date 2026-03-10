# C BOF — API Reference (Cobalt Strike 4.12)

Complete reference for Beacon Object File development in C, based on the
official `beacon.h` header (CS 4.x, updated through 4.12).

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
BeaconGetSyscallInformation(&sc, sizeof(sc), TRUE);
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

## 14. Real-world patterns reference

### 14.1 DFR import grouping convention

Always group DFR declarations by DLL module with section headers:

```c
/* ── KERNEL32 ─────────────────────────────────────────── */
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$OpenProcess(DWORD, BOOL, DWORD);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$CloseHandle(HANDLE);

/* ── ADVAPI32 ─────────────────────────────────────────── */
DECLSPEC_IMPORT BOOL    WINAPI ADVAPI32$OpenProcessToken(HANDLE, DWORD, PHANDLE);

/* ── NTDLL ────────────────────────────────────────────── */
DECLSPEC_IMPORT NTSTATUS NTAPI NTDLL$NtQuerySystemInformation(ULONG, PVOID, ULONG, PULONG);

/* ── MSVCRT ───────────────────────────────────────────── */
DECLSPEC_IMPORT int     __cdecl MSVCRT$_snprintf(char*, size_t, const char*, ...);
```

Module order: KERNEL32 → ADVAPI32 → NTDLL → USER32 → MSVCRT → others.
Align return types for readability.

### 14.2 Heap management (HeapAlloc / HeapFree)

Never use `malloc`/`free`/`calloc` in BOFs. Use the process heap:

```c
HANDLE heap = KERNEL32$GetProcessHeap();
void* buf = KERNEL32$HeapAlloc(heap, HEAP_ZERO_MEMORY, size);
/* ... */
KERNEL32$HeapFree(heap, 0, buf);
```

### 14.3 Multi-mode BOF design

Single BOF source, multiple operations via mode integer:

```c
#define MODE_FREEZE   1
#define MODE_DUMP     2
#define MODE_UNFREEZE 3

void go(char* args, int len) {
    datap parser;
    BeaconDataParse(&parser, args, len);
    int mode = BeaconDataInt(&parser);
    switch (mode) {
        case MODE_FREEZE:   do_freeze(&parser);   break;
        case MODE_DUMP:     do_dump(&parser);      break;
        case MODE_UNFREEZE: do_unfreeze(&parser);  break;
        default: BeaconPrintf(CALLBACK_ERROR, "Unknown mode: %d", mode);
    }
}
```

### 14.4 Key/Value Store for persistent state (CS 4.9+)

```c
#define KEY_HANDLE "myBof_handle"
BeaconAddValue(KEY_HANDLE, (char*)hProc);            /* store */
HANDLE h = (HANDLE)BeaconGetValue(KEY_HANDLE);       /* retrieve */
BeaconRemoveValue(KEY_HANDLE);                       /* cleanup */
```

### 14.5 Ntdll dynamic resolution via GetProcAddress

```c
typedef NTSTATUS (NTAPI *fnNtSuspendProcess)(HANDLE);
HMODULE hNtdll = KERNEL32$GetModuleHandleA("ntdll.dll");
fnNtSuspendProcess pSuspend =
    (fnNtSuspendProcess)KERNEL32$GetProcAddress(hNtdll, "NtSuspendProcess");
```

### 14.6 Embedded encrypted payloads

```c
#include "payload.h"  /* enc_payload[], enc_key[], enc_nonce[] */

static void secure_zero(void* ptr, size_t len) {
    volatile unsigned char* p = (volatile unsigned char*)ptr;
    while (len--) *p++ = 0;
}
/* Decrypt → use → secure_zero key material */
```

### 14.7 Process injection (VirtualAllocEx → WriteProcessMemory → CreateRemoteThread)

```c
LPVOID remoteBuf = KERNEL32$VirtualAllocEx(hProc, NULL, sz,
    MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
KERNEL32$WriteProcessMemory(hProc, remoteBuf, payload, sz, NULL);
DWORD oldProt;
KERNEL32$VirtualProtectEx(hProc, remoteBuf, sz, PAGE_EXECUTE_READ, &oldProt);
HANDLE hThread = KERNEL32$CreateRemoteThread(hProc, NULL, 0,
    (LPTHREAD_START_ROUTINE)remoteBuf, NULL, 0, NULL);
```

### 14.8 Named pipe IPC for data exchange

```c
wchar_t pipeName[128];
MSVCRT$_snwprintf(pipeName, 128, L"\\\\.\\pipe\\exfil_%d", pid);
HANDLE hPipe = KERNEL32$CreateNamedPipeW(pipeName,
    PIPE_ACCESS_INBOUND, PIPE_TYPE_BYTE | PIPE_WAIT,
    1, 0, BUFFER_SIZE, 0, NULL);
KERNEL32$ConnectNamedPipe(hPipe, NULL);
```

### 14.9 Error handling helpers

```c
static void PrintWin32Error(const char* ctx) {
    DWORD e = KERNEL32$GetLastError();
    BeaconPrintf(CALLBACK_ERROR, "%s failed (error %lu / 0x%lX)", ctx, e, e);
}

static BOOL EnableDebugPrivilege(void) {
    HANDLE hToken;
    ADVAPI32$OpenProcessToken(KERNEL32$GetCurrentProcess(),
        TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &hToken);
    TOKEN_PRIVILEGES tp;
    tp.PrivilegeCount = 1;
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;
    ADVAPI32$LookupPrivilegeValueA(NULL, "SeDebugPrivilege",
        &tp.Privileges[0].Luid);
    BOOL ok = ADVAPI32$AdjustTokenPrivileges(hToken, FALSE, &tp, 0, NULL, NULL);
    KERNEL32$CloseHandle(hToken);
    return ok;
}
```

### 14.10 Custom struct definitions

When SDK headers are unavailable or too heavy:

```c
#pragma pack(push, 1)
typedef struct _MY_SYSTEM_PROCESS_INFO {
    ULONG  NextEntryOffset;
    ULONG  NumberOfThreads;
    UNICODE_STRING ImageName;
    LONG   BasePriority;
    HANDLE UniqueProcessId;
} MY_SYSTEM_PROCESS_INFO;
#pragma pack(pop)
```

### 14.11 Long-running BOF (message pump)

```c
static BOOL g_running = TRUE;
LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    /* handle WM_INPUT, WM_CLIPBOARDUPDATE, etc. */
    if (msg == WM_DESTROY) { g_running = FALSE; return 0; }
    return USER32$DefWindowProcW(hwnd, msg, wp, lp);
}
void go(char* args, int len) {
    (void)args; (void)len;
    WNDCLASSW wc = {0};
    wc.lpfnWndProc = WndProc;
    wc.lpszClassName = L"BofWorker";
    USER32$RegisterClassW(&wc);
    HWND hwnd = USER32$CreateWindowExW(0, L"BofWorker", NULL, 0,
        0, 0, 0, 0, HWND_MESSAGE, NULL, NULL, NULL);
    MSG msg;
    while (g_running && USER32$GetMessageW(&msg, NULL, 0, 0) > 0) {
        USER32$TranslateMessage(&msg);
        USER32$DispatchMessageW(&msg);
    }
}
```
