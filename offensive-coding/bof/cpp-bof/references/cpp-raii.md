# C++ BOF RAII patterns and safe features

All RAII wrappers live in the `bof` namespace, matching `assets/bof_helpers.hpp`.
Include after `beacon.h`:

```cpp
extern "C" { #include "beacon.h" }
#include "bof_helpers.hpp"
```

## RAII wrappers

### Handle wrapper

```cpp
namespace bof {

class Handle {
    HANDLE h_;
public:
    explicit Handle(HANDLE h = NULL) : h_(h) {}
    ~Handle() {
        if (h_ && h_ != INVALID_HANDLE_VALUE)
            KERNEL32$CloseHandle(h_);
    }
    operator HANDLE() const { return h_; }
    HANDLE* operator&() { return &h_; }
    HANDLE get() const { return h_; }
    bool valid() const { return h_ && h_ != INVALID_HANDLE_VALUE; }
    HANDLE release() { HANDLE tmp = h_; h_ = NULL; return tmp; }
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
};
```

### Heap buffer wrapper

```cpp
class HeapBuf {
    void*  buf_;
    SIZE_T size_;
public:
    explicit HeapBuf(SIZE_T size) : buf_(nullptr), size_(0) {
        buf_ = KERNEL32$HeapAlloc(KERNEL32$GetProcessHeap(), HEAP_ZERO_MEMORY, size);
        if (buf_) size_ = size;
    }
    ~HeapBuf() {
        if (buf_) KERNEL32$HeapFree(KERNEL32$GetProcessHeap(), 0, buf_);
    }
    void* get() const { return buf_; }
    SIZE_T size() const { return size_; }
    bool valid() const { return buf_ != nullptr; }
    template<typename T = void> T* as() const { return static_cast<T*>(buf_); }
    HeapBuf(const HeapBuf&) = delete;
    HeapBuf& operator=(const HeapBuf&) = delete;
};
```

### Format buffer wrapper

```cpp
class Format {
    formatp fmt_;
public:
    explicit Format(int size) { BeaconFormatAlloc(&fmt_, size); }
    ~Format() { BeaconFormatFree(&fmt_); }
    void append(const char* data, int len) { BeaconFormatAppend(&fmt_, (char*)data, len); }
    void append_int(int value) { BeaconFormatInt(&fmt_, value); }
    char* to_string(int* size) { return BeaconFormatToString(&fmt_, size); }
    void reset() { BeaconFormatReset(&fmt_); }
    Format(const Format&) = delete;
    Format& operator=(const Format&) = delete;
};
```

### Registry key wrapper

```cpp
class RegKey {
    HKEY key_;
public:
    explicit RegKey(HKEY k = NULL) : key_(k) {}
    ~RegKey() { if (key_) ADVAPI32$RegCloseKey(key_); }
    operator HKEY() const { return key_; }
    HKEY* operator&() { return &key_; }
    bool valid() const { return key_ != NULL; }
    RegKey(const RegKey&) = delete;
    RegKey& operator=(const RegKey&) = delete;
};

} /* namespace bof */
```

## Factory RAII for borrowed resources

Some Win32 resources have different cleanup paths depending on how they were
obtained. Use factory methods with a discriminator instead of multiple classes:

```cpp
class GdiDC {
    HDC hdc_;
    bool own_;   /* true = DeleteDC, false = ReleaseDC(hwnd) */
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
```

Same pattern applies to any resource with dual cleanup (e.g., `CloseHandle`
vs `FindClose`, `RegCloseKey` on different root keys).

## Safe C++ feature matrix

| Feature | Safe? | Notes |
|---------|-------|-------|
| Classes / structs (stack) | Yes | No heap dependency |
| RAII (destructors) | Yes | Automatic cleanup on scope exit |
| Templates | Yes | Compile-time only; watch code bloat |
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
| Global objects with ctors | **No** | Constructors will not run |

## Common pitfalls

| Problem | Cause | Solution |
|---------|-------|----------|
| `undefined reference to __cxa_*` | Exception tables linked | Add `-fno-exceptions` |
| `undefined reference to __dso_handle` | Global destructors | Avoid static objects with destructors |
| `undefined reference to operator new` | Heap allocation | Use stack or `HeapAlloc` |
| Name mangling hides `go` | Missing `extern "C"` | Wrap `go()` in `extern "C"` |
| `.text` section too large | Template bloat | Reduce template instantiations |
| `vtable` errors | Virtual functions | Avoid or use `-fno-rtti` carefully |
| COMDAT section conflicts | `using namespace` SDK | Never use `using namespace Gdiplus` etc. |
| Too many DECLSPEC_IMPORT | Linker limits (30+ DFRs) | Switch to typedef + GetProcAddress pattern |
