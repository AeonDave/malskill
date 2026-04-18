/*
 * bof_helpers.hpp — RAII wrappers and utility templates for C++ BOFs.
 *
 * Include after beacon.h. These helpers provide automatic resource cleanup
 * without requiring C++ runtime features (no exceptions, no RTTI, no STL).
 *
 * Usage:
 *   extern "C" {
 *   #include "beacon.h"
 *   }
 *   #include "bof_helpers.hpp"
 */

#ifndef BOF_HELPERS_HPP
#define BOF_HELPERS_HPP

#include <windows.h>

/* DFR declarations required by helpers */
DECLSPEC_IMPORT BOOL   WINAPI KERNEL32$CloseHandle(HANDLE);
DECLSPEC_IMPORT HANDLE WINAPI KERNEL32$GetProcessHeap(void);
DECLSPEC_IMPORT LPVOID WINAPI KERNEL32$HeapAlloc(HANDLE, DWORD, SIZE_T);
DECLSPEC_IMPORT BOOL   WINAPI KERNEL32$HeapFree(HANDLE, DWORD, LPVOID);
DECLSPEC_IMPORT LONG   WINAPI ADVAPI32$RegCloseKey(HKEY);

namespace bof {

/* ---- Handle RAII wrapper ---- */
class Handle {
    HANDLE h_;
public:
    explicit Handle(HANDLE h = NULL) : h_(h) {}

    ~Handle() {
        if (h_ != NULL && h_ != INVALID_HANDLE_VALUE)
            KERNEL32$CloseHandle(h_);
    }

    operator HANDLE() const { return h_; }
    HANDLE* operator&() { return &h_; }
    HANDLE get() const { return h_; }

    bool valid() const {
        return h_ != NULL && h_ != INVALID_HANDLE_VALUE;
    }

    HANDLE release() {
        HANDLE tmp = h_;
        h_ = NULL;
        return tmp;
    }

    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
};

/* ---- Format buffer RAII wrapper ---- */
class Format {
    formatp fmt_;
public:
    explicit Format(int size) {
        BeaconFormatAlloc(&fmt_, size);
    }

    ~Format() {
        BeaconFormatFree(&fmt_);
    }

    void append(const char* data, int len) {
        BeaconFormatAppend(&fmt_, (char*)data, len);
    }

    void append_int(int value) {
        BeaconFormatInt(&fmt_, value);
    }

    char* to_string(int* size) {
        return BeaconFormatToString(&fmt_, size);
    }

    void reset() {
        BeaconFormatReset(&fmt_);
    }

    Format(const Format&) = delete;
    Format& operator=(const Format&) = delete;
};

/* ---- Heap buffer RAII wrapper ---- */
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

    template<typename T = void>
    T* as() const { return static_cast<T*>(buf_); }

    HeapBuf(const HeapBuf&) = delete;
    HeapBuf& operator=(const HeapBuf&) = delete;
};

/* ---- Registry key RAII wrapper ---- */
class RegKey {
    HKEY key_;
public:
    explicit RegKey(HKEY k = NULL) : key_(k) {}

    ~RegKey() {
        if (key_) ADVAPI32$RegCloseKey(key_);
    }

    operator HKEY() const { return key_; }
    HKEY* operator&() { return &key_; }
    bool valid() const { return key_ != NULL; }

    RegKey(const RegKey&) = delete;
    RegKey& operator=(const RegKey&) = delete;
};

/* ---- Logging helpers ---- */
template<typename... Args>
void log(const char* fmt, Args... args) {
    BeaconPrintf(CALLBACK_OUTPUT, (char*)fmt, args...);
}

template<typename... Args>
void err(const char* fmt, Args... args) {
    BeaconPrintf(CALLBACK_ERROR, (char*)fmt, args...);
}

/* ---- Compile-time string length ---- */
template<size_t N>
constexpr size_t strlen_ct(const char (&)[N]) {
    return N - 1;
}

} /* namespace bof */

#endif /* BOF_HELPERS_HPP */
