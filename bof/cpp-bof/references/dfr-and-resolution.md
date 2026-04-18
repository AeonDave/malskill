# DFR and runtime resolution for C++ BOFs

## Strategy selection

1. **Standard `DECLSPEC_IMPORT`** — for small/medium BOFs (<30 imports)
2. **typedef + `GetProcAddress`** — for large API surfaces (GDI+, COM, DirectX)
3. **Feature-guarded headers** — enable only needed import sets per BOF

## Standard DFR

```cpp
/* ── KERNEL32 ─────────────────────────────────────────── */
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$CloseHandle(HANDLE);
DECLSPEC_IMPORT HMODULE WINAPI KERNEL32$LoadLibraryA(LPCSTR);
DECLSPEC_IMPORT FARPROC WINAPI KERNEL32$GetProcAddress(HMODULE, LPCSTR);
```

## Runtime resolve pattern (C++ style)

```cpp
typedef HDC     (WINAPI *fnGetDC)(HWND);
typedef BOOL    (WINAPI *fnBitBlt)(HDC, int, int, int, int, HDC, int, int, DWORD);
typedef int     (WINAPI *fnGetSystemMetrics)(int);

static fnGetDC           pGetDC = NULL;
static fnBitBlt          pBitBlt = NULL;
static fnGetSystemMetrics pGetSystemMetrics = NULL;

static BOOL ResolveAPIs(void) {
    HMODULE hGdi32  = KERNEL32$LoadLibraryA("gdi32.dll");
    HMODULE hUser32 = KERNEL32$LoadLibraryA("user32.dll");
    if (!hGdi32 || !hUser32) return FALSE;

    pGetDC           = (fnGetDC)KERNEL32$GetProcAddress(hUser32, "GetDC");
    pBitBlt          = (fnBitBlt)KERNEL32$GetProcAddress(hGdi32, "BitBlt");
    pGetSystemMetrics = (fnGetSystemMetrics)KERNEL32$GetProcAddress(hUser32, "GetSystemMetrics");

    return (pGetDC && pBitBlt && pGetSystemMetrics);
}
```

Call `ResolveAPIs()` at the top of `go()` before using any resolved pointer.

## GDI+ flat API (no C++ wrapper classes)

The GDI+ C++ wrapper classes (`Gdiplus::Bitmap`, etc.) are **not usable** in
BOFs because `using namespace Gdiplus` creates COMDAT section conflicts with
the Beacon loader. Use the **flat C API** from `gdiplus.dll`:

```cpp
typedef int (WINAPI *fnGdiplusStartup)(ULONG_PTR*, void*, void*);
typedef void (WINAPI *fnGdiplusShutdown)(ULONG_PTR);
typedef int (WINAPI *fnGdipCreateBitmapFromHBITMAP)(HBITMAP, HPALETTE, void**);
typedef int (WINAPI *fnGdipSaveImageToStream)(void*, CLSID*, void*);
```

## COM / IStream usage

```cpp
typedef HRESULT (WINAPI *fnCreateStreamOnHGlobal)(HGLOBAL, BOOL, LPSTREAM*);
HMODULE hOle32 = KERNEL32$LoadLibraryA("ole32.dll");
fnCreateStreamOnHGlobal pCreateStream =
    (fnCreateStreamOnHGlobal)KERNEL32$GetProcAddress(hOle32, "CreateStreamOnHGlobal");

IStream* pStream = NULL;
pCreateStream(NULL, TRUE, &pStream);
/* ... use pStream->Write(), pStream->Seek() ... */
pStream->Release();
```

## Dual-build support

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
```

BOF build: `build_bof.sh mybof.cpp` (adds `-DBOF`).
EXE build: `x86_64-w64-mingw32-g++ -o mybof.exe mybof.cpp`.
