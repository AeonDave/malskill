/**
 * @file       mybof.c
 * @brief      <One-line description of the BOF>
 *
 * Technique:  <Name of the technique / tradecraft>
 * MITRE ATT&CK: <TID> (<Technique name>)
 * Target:     x86_64 Windows 10/11, Server 2016+
 *
 * Architecture notes:
 *   <Describe approach, data flow, multi-mode logic if any.>
 *
 * Build:
 *   ../scripts/build_bof.sh mybof.c
 *
 * CNA usage:
 *   beacon> mybof <arg1> <arg2>
 */

#include <windows.h>
#include "beacon.h"

#define BOF_NAME "mybof"  /* <-- Must match file name (without .c) */

/* ── KERNEL32 ─────────────────────────────────────────── */
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$GetProcessHeap(void);
DECLSPEC_IMPORT LPVOID  WINAPI KERNEL32$HeapAlloc(HANDLE, DWORD, SIZE_T);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$HeapFree(HANDLE, DWORD, LPVOID);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$CloseHandle(HANDLE);
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$GetCurrentProcess(void);
DECLSPEC_IMPORT DWORD   WINAPI KERNEL32$GetLastError(void);

/* ── ADVAPI32 ─────────────────────────────────────────── */
/* DECLSPEC_IMPORT BOOL WINAPI ADVAPI32$OpenProcessToken(HANDLE, DWORD, PHANDLE); */

/* ── NTDLL ────────────────────────────────────────────── */
/* DECLSPEC_IMPORT NTSTATUS NTAPI NTDLL$NtQuerySystemInformation(ULONG, PVOID, ULONG, PULONG); */

/* ── MSVCRT ───────────────────────────────────────────── */
DECLSPEC_IMPORT void*   __cdecl MSVCRT$memset(void*, int, size_t);
DECLSPEC_IMPORT void*   __cdecl MSVCRT$memcpy(void*, const void*, size_t);

/* ── Helpers ──────────────────────────────────────────── */

static void PrintError(const char* context) {
    DWORD err = KERNEL32$GetLastError();
    BeaconPrintf(CALLBACK_ERROR, "[%s] %s failed (error %lu / 0x%lX)",
                 BOF_NAME, context, err, err);
}

void go(char* args, int len) {
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
