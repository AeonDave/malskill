/**
 * @file       mybof.cpp
 * @brief      <One-line description of the BOF>
 *
 * Technique:  <Name of the technique / tradecraft>
 * MITRE ATT&CK: <TID> (<Technique name>)
 * Target:     x86_64 Windows 10/11, Server 2016+
 *
 * Build:
 *   ../scripts/build_bof.sh mybof.cpp
 *
 * Rules for C++ BOFs:
 *   - No exceptions, no RTTI, no STL, no new/delete
 *   - Wrap go() in extern "C"
 *   - Use RAII for handle/resource cleanup
 *   - Do NOT use 'using namespace' for SDK namespaces (COMDAT conflicts)
 */

#include <windows.h>

extern "C" {
#include "beacon.h"
}

#define BOF_NAME "mybof"  /* <-- Must match file name (without .cpp) */

/* ── KERNEL32 (DECLSPEC_IMPORT — core imports) ────────── */
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$CloseHandle(HANDLE);
DECLSPEC_IMPORT HMODULE WINAPI KERNEL32$LoadLibraryA(LPCSTR);
DECLSPEC_IMPORT FARPROC WINAPI KERNEL32$GetProcAddress(HMODULE, LPCSTR);
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$GetProcessHeap(void);
DECLSPEC_IMPORT LPVOID  WINAPI KERNEL32$HeapAlloc(HANDLE, DWORD, SIZE_T);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$HeapFree(HANDLE, DWORD, LPVOID);
DECLSPEC_IMPORT DWORD   WINAPI KERNEL32$GetLastError(void);

/* ── MSVCRT ───────────────────────────────────────────── */
DECLSPEC_IMPORT void*   __cdecl MSVCRT$memset(void*, int, size_t);
DECLSPEC_IMPORT void*   __cdecl MSVCRT$memcpy(void*, const void*, size_t);
DECLSPEC_IMPORT size_t  __cdecl MSVCRT$strlen(const char*);

/* ── typedef + GetProcAddress (for non-standard DLLs) ─── */
/*
 * When you have many API calls from GDI32, USER32, etc., use this
 * pattern to avoid DECLSPEC_IMPORT linker limits:
 *
 * typedef BOOL (WINAPI *fnBitBlt)(HDC, int, int, int, int, HDC, int, int, DWORD);
 * static fnBitBlt pBitBlt = NULL;
 *
 * Then resolve in ResolveAPIs():
 *   HMODULE h = KERNEL32$LoadLibraryA("gdi32.dll");
 *   pBitBlt = (fnBitBlt)KERNEL32$GetProcAddress(h, "BitBlt");
 */

/* ── RAII handle wrapper ──────────────────────────────── */
class BofHandle {
    HANDLE h_;
public:
    explicit BofHandle(HANDLE h = NULL) : h_(h) {}
    ~BofHandle() {
        if (h_ != NULL && h_ != INVALID_HANDLE_VALUE)
            KERNEL32$CloseHandle(h_);
    }
    operator HANDLE() const { return h_; }
    HANDLE* operator&() { return &h_; }
    bool valid() const { return h_ != NULL && h_ != INVALID_HANDLE_VALUE; }

    BofHandle(const BofHandle&) = delete;
    BofHandle& operator=(const BofHandle&) = delete;
};

/* ── Helpers ──────────────────────────────────────────── */

static void PrintError(const char* context) {
    DWORD err = KERNEL32$GetLastError();
    BeaconPrintf(CALLBACK_ERROR, "[%s] %s failed (error %lu / 0x%lX)",
                 BOF_NAME, context, err, err);
}

extern "C" void go(char* args, int len) {
    datap parser;
    BeaconDataParse(&parser, args, len);

    /* --- Parse arguments (must match CNA bof_pack order) --- */
    int    pid  = BeaconDataInt(&parser);      /* i */
    char*  path = BeaconDataExtract(&parser, NULL); /* z */

    if (pid <= 0) {
        BeaconPrintf(CALLBACK_ERROR, "[%s] Invalid PID: %d", BOF_NAME, pid);
        return;
    }

    BeaconPrintf(CALLBACK_OUTPUT, "[%s] PID=%d path=%s", BOF_NAME, pid, path);

    /* --- Heap allocation example --- */
    HANDLE heap = KERNEL32$GetProcessHeap();
    char* buf = (char*)KERNEL32$HeapAlloc(heap, HEAP_ZERO_MEMORY, 4096);
    if (!buf) {
        PrintError("HeapAlloc");
        return;
    }

    /* --- Your logic here --- */

    /* --- Cleanup --- */
    KERNEL32$HeapFree(heap, 0, buf);

    /* Do not call exit() or return a value. */
}
