# PEB / TEB / LDR Reference

Load when walking the PEB, TEB, or loader lists for module discovery, environment inspection, or API resolution.

---

## TEB (Thread Environment Block) — x64

Per-thread structure, first field is `NT_TIB`. Accessed via `gs:[0]`.

| Offset | Field | Type | Notes |
|--------|-------|------|-------|
| 0x00 | ExceptionList | PVOID | Unused on x64 (was x86 SEH chain head) |
| 0x08 | StackBase | PVOID | Thread stack high address |
| 0x10 | StackLimit | PVOID | Thread stack low address (growing down) |
| 0x18 | SubSystemTib | PVOID | Reserved |
| 0x20 | FiberData | PVOID | Or Version (union) |
| 0x28 | ArbitraryUserPointer | PVOID | Free for userland use |
| 0x30 | Self | PTEB | Pointer to this TEB (used as `gs:[0x30]` dereference) |
| 0x40 | ClientId.UniqueProcess | HANDLE | PID |
| 0x48 | ClientId.UniqueThread | HANDLE | TID |
| 0x58 | ThreadLocalStoragePointer | PVOID | TLS slot array base |
| 0x60 | ProcessEnvironmentBlock | PPEB | **PEB pointer** — the workhorse |
| 0x68 | LastErrorValue | ULONG | `GetLastError()` storage |
| 0x1480 | TlsSlots[64] | PVOID[64] | Static TLS (indices 0..63) |
| 0x1780 | TlsLinks | LIST_ENTRY | Dynamic TLS chain |

**Direct access patterns**

```c
// x64 inline (MSVC intrinsic)
#include <intrin.h>
PTEB teb = (PTEB)__readgsqword(0x30);
PPEB peb = (PPEB)__readgsqword(0x60);

// x64 GNU inline ASM
__asm__("mov %%gs:0x60, %0" : "=r"(peb));

// ARM64 — TEB is x18 (platform register)
PTEB teb = (PTEB)__getReg(18);
```

**Do not use**: `NtCurrentTeb()` macro expands to exactly the `gs:[0x30]` read. Direct gs access avoids a function call but produces identical code under optimization.

---

## PEB (Process Environment Block) — x64

Per-process. Single instance mapped into each process's VA space.

| Offset | Field | Type | Notes |
|--------|-------|------|-------|
| 0x00 | InheritedAddressSpace | BOOLEAN | |
| 0x01 | ReadImageFileExecOptions | BOOLEAN | |
| 0x02 | **BeingDebugged** | BOOLEAN | Anti-debug check reads this |
| 0x03 | BitField | UCHAR | Bit 0: ImageUsesLargePages, bit 1: IsProtectedProcess, bit 3: IsLegacyProcess |
| 0x08 | Mutant | HANDLE | |
| 0x10 | **ImageBaseAddress** | PVOID | Main .exe base |
| 0x18 | **Ldr** | PPEB_LDR_DATA | Loaded module list |
| 0x20 | ProcessParameters | PRTL_USER_PROCESS_PARAMETERS | Cmdline, envp, stdio handles |
| 0x38 | ProcessHeap | PVOID | Default process heap |
| 0x68 | **ApiSetMap** | PAPI_SET_NAMESPACE | api-ms-win-* resolution table |
| 0x80 | TlsExpansionCounter | ULONG | |
| 0x120 | OSMajorVersion | ULONG | e.g., 10 |
| 0x124 | OSMinorVersion | ULONG | |
| 0x128 | OSBuildNumber | USHORT | e.g., 26100 (24H2) |
| 0x2D8 | TlsExpansionBitmap | PVOID | Dynamic TLS index bitmap |
| 0x320 | HeapTracingEnabled | BIT | Page heap / verifier |

Offsets above 0x100 drift across builds more than earlier ones. For anything past 0x120 verify against your target build via WinDbg `dt nt!_PEB`.

**Anti-debug quick check**: `BeingDebugged` flag is the classic IsDebuggerPresent equivalent. Trivial to bypass; trivial to detect the bypass. Never rely on it.

---

## PEB_LDR_DATA

Doubly linked lists of loaded modules, three separate orderings.

| Offset | Field | Type |
|--------|-------|------|
| 0x00 | Length | ULONG |
| 0x04 | Initialized | BOOLEAN |
| 0x08 | SsHandle | HANDLE |
| 0x10 | InLoadOrderModuleList | LIST_ENTRY |
| 0x20 | InMemoryOrderModuleList | LIST_ENTRY |
| 0x30 | InInitializationOrderModuleList | LIST_ENTRY |
| 0x40 | EntryInProgress | PVOID |
| 0x48 | ShutdownInProgress | BOOLEAN |

Each `LIST_ENTRY` head contains `Flink` and `Blink` pointers. The list is circular — walking back to the original list-head pointer signals completion.

**Which list to walk?**

- `InLoadOrderModuleList` — load order. First entry is the main executable
- `InMemoryOrderModuleList` — layout order in VA. First entry is ntdll.dll (loader init constraint)
- `InInitializationOrderModuleList` — constructor call order. Main exe **not** in this list

For offensive module hunting, use InMemoryOrder — ntdll is always first, kernel32/kernelbase second/third.

---

## LDR_DATA_TABLE_ENTRY — x64

One entry per loaded module. Embedded inside each of the three module lists via different LIST_ENTRY fields.

| Offset | Field | Type | Notes |
|--------|-------|------|-------|
| 0x00 | InLoadOrderLinks | LIST_ENTRY | Links for load-order list |
| 0x10 | InMemoryOrderLinks | LIST_ENTRY | Links for memory-order list |
| 0x20 | InInitializationOrderLinks | LIST_ENTRY | Links for init-order list |
| 0x30 | **DllBase** | PVOID | Module base address (== `ImageBase` at load) |
| 0x38 | EntryPoint | PVOID | AddressOfEntryPoint + DllBase |
| 0x40 | SizeOfImage | ULONG | Virtual size of mapped image |
| 0x48 | **FullDllName** | UNICODE_STRING | `\??\C:\...\foo.dll` |
| 0x58 | **BaseDllName** | UNICODE_STRING | `foo.dll` |
| 0x68 | FlagGroup | ULONG | See flags table below |
| 0x6C | ObsoleteLoadCount | USHORT | |
| 0x6E | TlsIndex | USHORT | Static TLS index |
| 0x78 | TimeDateStamp | ULONG | |

### Important flags (FlagGroup bitfield)

| Bit | Name | Meaning |
|-----|------|---------|
| 0x04 | ImageDll | Is a DLL (not the main exe) |
| 0x100 | LoadNotificationsSent | `PsSetLoadImageNotifyRoutine` callbacks fired |
| 0x800 | ProcessStaticImport | Loaded as static import (not LoadLibrary'd) |
| 0x1000 | InLegacyLists | Present in the three LIST_ENTRY chains |
| 0x2000 | InIndexes | Present in LdrpModuleBaseAddressIndex etc. |
| 0x80000 | ProcessAttachCalled | `DllMain(DLL_PROCESS_ATTACH)` returned |
| 0x100000 | ProcessAttachFailed | DllMain returned FALSE — queued for unload |
| 0x80000000 | (reserved) | |

**Offensive relevance**: clearing `InLegacyLists` and `InIndexes` hides a module from both the classic walk and the modern index lookup. Does not hide from the VAD-based walk the kernel uses for `PsSetLoadImageNotifyRoutine`.

---

## UNICODE_STRING

Appears in LDR_DATA_TABLE_ENTRY, OBJECT_ATTRIBUTES, many others.

```c
typedef struct _UNICODE_STRING {
    USHORT Length;          // in BYTES, not characters
    USHORT MaximumLength;   // in BYTES
    PWSTR  Buffer;          // UTF-16LE, not null-terminated in struct
} UNICODE_STRING;           // sizeof = 16 on x64
```

`Length` is always byte count. For character count, divide by `sizeof(WCHAR) == 2`. Buffer is **not guaranteed** null-terminated — always respect Length when reading.

---

## Module walk — canonical pattern

```c
// All casts shown for clarity; real code uses offsets into volatile memory.
PTEB teb = (PTEB)__readgsqword(0x30);
PPEB peb = teb->ProcessEnvironmentBlock;
PPEB_LDR_DATA ldr = peb->Ldr;

// Head is the list_entry inside PEB_LDR_DATA itself — not a module
PLIST_ENTRY head = &ldr->InMemoryOrderModuleList;
PLIST_ENTRY curr = head->Flink;

while (curr != head) {
    // InMemoryOrderLinks is at offset 0x10 of LDR_DATA_TABLE_ENTRY
    // curr points INTO InMemoryOrderLinks, so subtract 0x10 to reach entry base
    PLDR_DATA_TABLE_ENTRY entry = (PLDR_DATA_TABLE_ENTRY)((PBYTE)curr - 0x10);

    if (entry->BaseDllName.Buffer && entry->BaseDllName.Length > 0) {
        // Case-insensitive compare against target hash
        uint32_t h = hash_unicode_ci(entry->BaseDllName.Buffer,
                                     entry->BaseDllName.Length / sizeof(WCHAR));
        if (h == TARGET_HASH) {
            return entry->DllBase;
        }
    }

    curr = curr->Flink;
}
return NULL;
```

**Why hash and not strcmp?** Plaintext "ntdll.dll" inside the binary is a signature. Hashes computed at compile time (via `constexpr` in C++, `const fn` in Rust, build script in Go) evade string scanning. Use DJB2, FNV-1a, or a keyed variant.

**Case-insensitive hashing** — module names are compared case-insensitively by Windows. Fold to lowercase both at compile time (target hash) and runtime (module name bytes) before mixing.

---

## ApiSetMap — resolving api-ms-win-*

Modern Windows exposes "API set" virtual DLLs that redirect to host modules. The mapping lives in PEB.ApiSetMap.

### API_SET_NAMESPACE

| Offset | Field | Type | Notes |
|--------|-------|------|-------|
| 0x00 | Version | ULONG | 6 on Win10/11 |
| 0x04 | Size | ULONG | Total size of namespace blob |
| 0x08 | Flags | ULONG | |
| 0x0C | Count | ULONG | Number of API set entries |
| 0x10 | EntryOffset | ULONG | RVA from namespace base to entry array |
| 0x14 | HashOffset | ULONG | RVA to hash entry array (sorted by hash) |
| 0x18 | HashFactor | ULONG | Multiplier for name hashing |

### API_SET_HASH_ENTRY

```c
struct API_SET_HASH_ENTRY {
    ULONG Hash;   // FNV-1a style of lowercased name (minus prefix/suffix)
    ULONG Index;  // Index into entry array
};
```

### API_SET_NAMESPACE_ENTRY

```c
struct API_SET_NAMESPACE_ENTRY {
    ULONG Flags;
    ULONG NameOffset;     // RVA to name (wide string, not null-terminated)
    ULONG NameLength;     // bytes
    ULONG HashedLength;   // bytes used in hash (trims version suffix like "-l1-1-0")
    ULONG ValueOffset;    // RVA to value array
    ULONG ValueCount;     // usually 1; can be >1 with host-specific overrides
};
```

### API_SET_VALUE_ENTRY

```c
struct API_SET_VALUE_ENTRY {
    ULONG Flags;
    ULONG NameOffset;     // RVA to alias name (if any, else 0)
    ULONG NameLength;
    ULONG ValueOffset;    // RVA to target DLL name
    ULONG ValueLength;    // bytes
};
```

### Resolution algorithm

1. Strip `"api-"` or `"ext-"` prefix and the trailing `.dll`
2. Trim to `HashedLength` boundary (cuts the `-l1-1-0` suffix before hashing)
3. Lowercase
4. Compute hash (simple multiplicative: `hash = hash * HashFactor + lowercase_wchar`)
5. Binary search `API_SET_HASH_ENTRY[]` array
6. On hit, follow `Index` into `API_SET_NAMESPACE_ENTRY[]`
7. Read first `API_SET_VALUE_ENTRY`, extract target DLL name at `ValueOffset`

**Why this matters**: LoadLibrary("api-ms-win-core-sysinfo-l1-1-0.dll") works because kernel32 → kernelbase resolves the name via this same table. If you are walking PEB.Ldr looking for kernelbase, you may not find "api-ms-win-*" entries because they are resolved to host DLLs before LDR insertion. If you hard-code "kernel32.dll" as your target, you will hit kernel32 — but modern code paths increasingly route through kernelbase.

---

## Hash resolution primitives

### Compile-time module hash (C, DJB2)

```c
#define DJB2_SEED 5381u

// case-insensitive, operates on wchar_t as bytes
constexpr uint32_t djb2_ci_w(const wchar_t* s) {
    uint32_t h = DJB2_SEED;
    for (; *s; ++s) {
        wchar_t c = (*s >= L'A' && *s <= L'Z') ? (*s + 32) : *s;
        h = ((h << 5) + h) ^ (uint32_t)c;  // h*33 ^ c
    }
    return h;
}

#define HASH_NTDLL  djb2_ci_w(L"ntdll.dll")
```

Rust equivalent uses `const fn`; Go uses a `go generate` pass or build-time constant.

### Runtime hash against UNICODE_STRING

```c
static uint32_t djb2_ci_from_us(const UNICODE_STRING* us) {
    uint32_t h = DJB2_SEED;
    USHORT nchars = us->Length / sizeof(WCHAR);
    for (USHORT i = 0; i < nchars; ++i) {
        WCHAR c = us->Buffer[i];
        if (c >= L'A' && c <= L'Z') c += 32;
        h = ((h << 5) + h) ^ (uint32_t)c;
    }
    return h;
}
```

Keep hash function identical at compile and runtime; any divergence (signed vs unsigned, char vs wchar) breaks the match.

---

## PEB command-line spoofing

`PEB.ProcessParameters` → `RTL_USER_PROCESS_PARAMETERS.CommandLine` is a `UNICODE_STRING`. Overwriting the `Buffer`, `Length`, and `MaximumLength` fields changes what tools like Process Explorer report for the running process.

**Important caveats**:
- EDR and forensic tools that capture command line at **process creation** via `PsSetCreateProcessNotifyRoutineEx` see the original — post-creation spoofing is invisible to them
- `ImagePathName` and `CommandLine` are separate `UNICODE_STRING`s; overwrite both for consistency
- Buffer should point to memory the process owns — do not point to a stack local that will go out of scope

Typical sequence for remote spoofing:
1. `NtQueryInformationProcess(PROCESS_BASIC_INFORMATION)` to get remote PEB address
2. `NtReadVirtualMemory(peb + 0x20, &params_ptr)` → RTL_USER_PROCESS_PARAMETERS address
3. `NtReadVirtualMemory(params_ptr + 0x70, &cmdline_us)` → original UNICODE_STRING
4. `NtAllocateVirtualMemory` in target for new buffer, write spoofed string
5. `NtWriteVirtualMemory` to overwrite Length, MaximumLength, Buffer fields

---

## Thread stacks and guard pages

`TEB.StackBase` and `TEB.StackLimit` bracket the current thread's committed stack. Below StackLimit is a single-page **guard page** (PAGE_GUARD | PAGE_READWRITE). Touching it raises `STATUS_GUARD_PAGE_VIOLATION`, which the kernel converts to a normal commit and expands the stack. Reserved-but-not-committed pages extend further down; hitting those raises `STATUS_STACK_OVERFLOW`.

**Offensive relevance**: `__chkstk` in MSVC-generated prologues pre-touches stack pages when a function allocates more than a page. Emitting ASM that allocates >4KiB without going through `__chkstk` will skip the guard page and crash.

---

## Version drift — what to re-verify per build

Stable across Windows 10 1809 → Windows 11 24H2:
- TEB 0x30 Self, 0x40 ClientId, 0x58 Tls, 0x60 PEB, 0x68 LastError
- PEB 0x02 BeingDebugged, 0x10 ImageBaseAddress, 0x18 Ldr, 0x20 ProcessParameters, 0x68 ApiSetMap
- PEB_LDR_DATA list offsets
- LDR_DATA_TABLE_ENTRY 0x00..0x78 (above 0x78 drifts)

Drift-prone (re-verify per build):
- PEB ≥ 0x100 (session ID, heap compatibility info, DTLS, etc.)
- ETHREAD / EPROCESS — any kernel structure, always drifts
- TEB ≥ 0x1800 — post-TLS fields (WoW64 context, Win32ClientInfo)

**Tooling for verification**:
- WinDbg: `dt nt!_PEB`, `dt ntdll!_PEB_LDR_DATA`
- Vergilius Project (vergiliusproject.com): pre-computed offsets per build
- System Informer source (`phnt/include/ntpsapi.h`): maintained NTAPI headers
