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

/* DFR declaration required by helpers */
DECLSPEC_IMPORT BOOL WINAPI KERNEL32$CloseHandle(HANDLE);

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
