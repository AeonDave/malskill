# DFR strategies for C BOFs

Use this decision model:

1. **`DECLSPEC_IMPORT` only** for small/medium BOFs (roughly <30 imported APIs)
2. **typedef + `GetProcAddress`** for large API surfaces (GDI+, COM, many NTDLL/ADVAPI calls)
3. **Feature-guarded headers** (`#define INJ_*` before include) to keep per-BOF import sets minimal

## 1) Standard DFR

```c
DECLSPEC_IMPORT HANDLE WINAPI KERNEL32$OpenProcess(DWORD, BOOL, DWORD);
DECLSPEC_IMPORT BOOL   WINAPI KERNEL32$CloseHandle(HANDLE);
```

Pros: simple, readable.  
Cons: can hit linker/import limits in very large BOFs.

## 2) Runtime resolve pattern

```c
typedef BOOL (WINAPI *fnVirtualProtectEx)(HANDLE, LPVOID, SIZE_T, DWORD, PDWORD);
static fnVirtualProtectEx pVirtualProtectEx = NULL;

static BOOL ResolveCore(void) {
    HMODULE hK32 = KERNEL32$GetModuleHandleA("kernel32.dll");
    if (!hK32) return FALSE;
    pVirtualProtectEx = (fnVirtualProtectEx)KERNEL32$GetProcAddress(hK32, "VirtualProtectEx");
    return pVirtualProtectEx != NULL;
}
```

Pros: fewer static imports, better control.  
Cons: requires resolver error handling.

## 3) Feature guards (recommended)

Split import sets by technique and enable only what each BOF needs:

- `INJ_MANUAL_MAP`
- `INJ_HOLLOWING`
- `INJ_STOMP`
- `INJ_PPID_SPOOF`

This avoids dragging broad API sets into every object file.

### Example: feature-guarded injection header

```c
/* injection.h — feature-guarded DFR for injection techniques */

#ifndef INJECTION_H
#define INJECTION_H

#include <windows.h>

/* ── Shared (always included) ─────────────────────────── */
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$OpenProcess(DWORD, BOOL, DWORD);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$CloseHandle(HANDLE);
DECLSPEC_IMPORT LPVOID  WINAPI KERNEL32$VirtualAllocEx(HANDLE, LPVOID, SIZE_T, DWORD, DWORD);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$WriteProcessMemory(HANDLE, LPVOID, LPCVOID, SIZE_T, SIZE_T*);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$VirtualProtectEx(HANDLE, LPVOID, SIZE_T, DWORD, PDWORD);

/* ── Manual mapping ───────────────────────────────────── */
#ifdef INJ_MANUAL_MAP
DECLSPEC_IMPORT HMODULE WINAPI KERNEL32$LoadLibraryA(LPCSTR);
DECLSPEC_IMPORT FARPROC WINAPI KERNEL32$GetProcAddress(HMODULE, LPCSTR);
DECLSPEC_IMPORT SIZE_T  WINAPI KERNEL32$VirtualQuery(LPCVOID, PMEMORY_BASIC_INFORMATION, SIZE_T);
#endif

/* ── Module stomping ──────────────────────────────────── */
#ifdef INJ_STOMP
typedef LONG (NTAPI *pfnNtCreateSection)(PHANDLE, ACCESS_MASK, PVOID, PLARGE_INTEGER, ULONG, ULONG, HANDLE);
typedef LONG (NTAPI *pfnNtMapViewOfSection)(HANDLE, HANDLE, PVOID*, ULONG_PTR, SIZE_T, PLARGE_INTEGER, PSIZE_T, ULONG, ULONG, ULONG);
#endif

/* ── PPID spoofing ────────────────────────────────────── */
#ifdef INJ_PPID_SPOOF
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$InitializeProcThreadAttributeList(LPPROC_THREAD_ATTRIBUTE_LIST, DWORD, DWORD, PSIZE_T);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$UpdateProcThreadAttribute(LPPROC_THREAD_ATTRIBUTE_LIST, DWORD, DWORD_PTR, PVOID, SIZE_T, PVOID, PSIZE_T);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$CreateProcessA(LPCSTR, LPSTR, LPSECURITY_ATTRIBUTES, LPSECURITY_ATTRIBUTES, BOOL, DWORD, LPVOID, LPCSTR, LPSTARTUPINFOA, LPPROCESS_INFORMATION);
#endif

/* ── APC injection ────────────────────────────────────── */
#ifdef INJ_APC
DECLSPEC_IMPORT DWORD   WINAPI KERNEL32$QueueUserAPC(PAPCFUNC, HANDLE, ULONG_PTR);
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$CreateToolhelp32Snapshot(DWORD, DWORD);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$Thread32First(HANDLE, LPTHREADENTRY32);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$Thread32Next(HANDLE, LPTHREADENTRY32);
#endif

#endif /* INJECTION_H */
```

Usage in BOF source — only define the guards you need:

```c
#define INJ_STOMP
#define INJ_PPID_SPOOF
#include "injection.h"
/* Only stomping + PPID spoof imports are pulled in */
```

## Practical quality rules

- Group declarations by DLL, fixed order: KERNEL32 → ADVAPI32 → NTDLL → USER32 → MSVCRT.
- Do not mix naked Win32 symbols and DFR aliases in the same file.
- Keep one resolver function per subsystem (`ResolveNt()`, `ResolveGdi()`, etc.).
- Fail fast if a required symbol cannot be resolved.
