# Memory Management Reference

Windows virtual memory, section objects, VADs, NT heap vs Segment heap, LFH, and the Nt* syscall surface that touches it all.

---

## Address space layout (x64)

Windows x64 user-mode VA: 128 TB (`0x0000_0000_0000_0000` .. `0x0000_7FFF_FFFF_FFFF`).
High-entropy ASLR (default on modern builds) randomizes:
- Images — 64-bit VA slots, modules far apart
- Stack — different per thread
- Heap — independent regions per heap
- Mapped sections — randomly placed

Kernel VA: `0xFFFF_8000_0000_0000` and up. Not directly accessible from user mode; requires syscall transition.

---

## Memory states

| State | Meaning |
|---|---|
| Free | No reservation, no backing |
| Reserved | VA range reserved, no physical/pagefile backing, **cannot be accessed** |
| Committed | Backed by physical memory or pagefile. Access permitted per protection |

`MEM_RESERVE | MEM_COMMIT` in one call reserves and commits simultaneously. Separating reserve from commit lets you reserve a large range cheaply, commit sub-ranges as needed.

---

## Page protections (`PAGE_*` values)

| Flag | Value | Meaning |
|---|---|---|
| PAGE_NOACCESS | 0x01 | Any access raises STATUS_ACCESS_VIOLATION |
| PAGE_READONLY | 0x02 | Read permitted, write/execute fault |
| PAGE_READWRITE | 0x04 | Read+write |
| PAGE_WRITECOPY | 0x08 | COW — write triggers private copy |
| PAGE_EXECUTE | 0x10 | Execute only (no read) — rare |
| PAGE_EXECUTE_READ | 0x20 | Execute+read (normal .text) |
| PAGE_EXECUTE_READWRITE | 0x40 | RWX — flagged by EDRs as suspicious |
| PAGE_EXECUTE_WRITECOPY | 0x80 | RX with COW |
| PAGE_GUARD | 0x100 (modifier) | One-shot STATUS_GUARD_PAGE_VIOLATION |
| PAGE_NOCACHE | 0x200 (modifier) | Disables caching |
| PAGE_WRITECOMBINE | 0x400 (modifier) | Write combining |
| PAGE_TARGETS_INVALID | 0x40000000 | CFG: all targets in this region are invalid |
| PAGE_TARGETS_NO_UPDATE | 0x40000000 | CFG: don't update bitmap on this region |

### Protection transition fingerprints

EDRs and ETW-TI flag specific transitions:

| Transition | Signal |
|---|---|
| RW → RX | Benign but tracked |
| RW → RWX | High signal (most legit code never does this) |
| RX → RW → RX (sleep obfuscation) | Very high signal — flags fluctuation monitors |
| New RX allocation | Tracked (JIT engines excepted) |
| New RWX allocation | Flagged immediately |

---

## Nt* virtual memory syscalls

### NtAllocateVirtualMemory

```c
NTSTATUS NtAllocateVirtualMemory(
    HANDLE    ProcessHandle,        // NtCurrentProcess() or remote
    PVOID*    BaseAddress,          // IN/OUT — NULL = pick for us
    ULONG_PTR ZeroBits,             // 0 typical; non-zero limits high bits
    PSIZE_T   RegionSize,           // IN/OUT — rounded up to page
    ULONG     AllocationType,       // MEM_RESERVE | MEM_COMMIT | MEM_TOP_DOWN ...
    ULONG     Protect               // PAGE_*
);
```

**Semantics**:
- `*BaseAddress` NULL → system picks
- `*BaseAddress` non-NULL → hint; rounded down to 64KB allocation granularity
- `*RegionSize` rounded up to page size (4KB typical)
- `MEM_COMMIT` without `MEM_RESERVE` on a reserved range → commits
- `MEM_RESERVE | MEM_COMMIT` on never-touched region → reserves 64KB-aligned, commits pages within

### NtAllocateVirtualMemoryEx (Windows 10 1803+)

Supports `MEM_EXTENDED_PARAMETER` array for placement restrictions (address range, numa node, etc.).

### NtProtectVirtualMemory

```c
NTSTATUS NtProtectVirtualMemory(
    HANDLE  ProcessHandle,
    PVOID*  BaseAddress,        // rounded down to page
    PSIZE_T RegionSize,         // rounded up to page
    ULONG   NewProtect,
    PULONG  OldProtect          // OUT — protection of first page in range
);
```

**Pitfall**: `OldProtect` is the protection of the **first page**, not the whole range. If the range spans pages with differing protection, restoration requires querying each page separately.

### NtQueryVirtualMemory

Information classes:
- `MemoryBasicInformation` (default) → MEMORY_BASIC_INFORMATION struct
- `MemoryWorkingSetInformation`
- `MemoryMappedFilenameInformation` → full path of backing file (if section-backed)
- `MemoryRegionInformation` (newer)
- `MemoryImageInformation` (newer) → IMAGE_INFORMATION: is it an image, where's ImageBase, SizeOfImage

```c
typedef struct _MEMORY_BASIC_INFORMATION {
    PVOID     BaseAddress;
    PVOID     AllocationBase;
    DWORD     AllocationProtect;
    SIZE_T    RegionSize;
    DWORD     State;        // MEM_FREE / RESERVE / COMMIT
    DWORD     Protect;      // Current protection
    DWORD     Type;         // MEM_IMAGE / MAPPED / PRIVATE
} MEMORY_BASIC_INFORMATION;
```

**MemoryType field is gold for defenders**:
- `MEM_PRIVATE` → allocated via NtAllocateVirtualMemory, no file backing
- `MEM_MAPPED` → NtMapViewOfSection of a file other than an image
- `MEM_IMAGE` → loaded PE

Unbacked RX memory (MEM_PRIVATE + PAGE_EXECUTE_*) is one of the strongest shellcode IOCs.

### NtWriteVirtualMemory / NtReadVirtualMemory

Cross-process access primitives. Require handle with appropriate access rights:
- Read: `PROCESS_VM_READ`
- Write: `PROCESS_VM_OPERATION | PROCESS_VM_WRITE`

ETW-TI fires `EtwTiLogWriteVm` on cross-process writes. No fire on same-process writes (`ProcessHandle == -1`).

### NtFreeVirtualMemory

```c
NTSTATUS NtFreeVirtualMemory(
    HANDLE  ProcessHandle,
    PVOID*  BaseAddress,
    PSIZE_T RegionSize,
    ULONG   FreeType           // MEM_RELEASE or MEM_DECOMMIT
);
```

- `MEM_RELEASE`: `*RegionSize` must be 0, `*BaseAddress` must equal the allocation base. Releases reserved+committed back to free.
- `MEM_DECOMMIT`: decommits pages within reservation. Range can be partial.

---

## Section objects

Sections are file-backed or pagefile-backed memory mappings. Used internally by the loader for every DLL/EXE, by memory-mapped files, and by offensive techniques (process hollowing, module stomping, phantom DLL hollowing).

### Lifecycle

1. `NtCreateSection` → kernel section object, referenced by handle
2. `NtMapViewOfSection` → maps the section into a process VA space as a view
3. `NtUnmapViewOfSection` → removes the view (section object persists until handle close)

### NtCreateSection

```c
NTSTATUS NtCreateSection(
    PHANDLE             SectionHandle,       // OUT
    ACCESS_MASK         DesiredAccess,       // SECTION_ALL_ACCESS typical
    POBJECT_ATTRIBUTES  ObjectAttributes,    // NULL or name-bound
    PLARGE_INTEGER      MaximumSize,         // size for pagefile-backed; NULL = use file size for file-backed
    ULONG               PageAttributes,      // initial page protection
    ULONG               SectionAttributes,   // SEC_IMAGE / SEC_COMMIT / SEC_RESERVE / SEC_NOCACHE / SEC_FILE
    HANDLE              FileHandle           // for file-backed; NULL for pagefile-backed
);
```

**Key SectionAttribute flags**:

| Flag | Value | Meaning |
|---|---|---|
| SEC_IMAGE | 0x01000000 | File is a PE; kernel parses and applies section protections from PE headers |
| SEC_FILE | 0x00800000 | Plain file mapping (data) |
| SEC_COMMIT | 0x08000000 | Commit at map time |
| SEC_RESERVE | 0x04000000 | Reserve at map time |
| SEC_LARGE_PAGES | 0x80000000 | 2MB pages (requires SeLockMemoryPrivilege) |
| SEC_NO_CHANGE | 0x00400000 | Protection locked once set |

**SEC_IMAGE specifics**: kernel parses DOS/NT headers, creates appropriate section views with per-section protections. Allows legitimate PE loading. Used by Reflective PE loaders, process hollowing, and Phantom DLL Hollowing (via transacted file).

### NtMapViewOfSection

```c
NTSTATUS NtMapViewOfSection(
    HANDLE          SectionHandle,
    HANDLE          ProcessHandle,        // target process
    PVOID*          BaseAddress,          // IN/OUT
    ULONG_PTR       ZeroBits,
    SIZE_T          CommitSize,
    PLARGE_INTEGER  SectionOffset,
    PSIZE_T         ViewSize,
    DWORD           InheritDisposition,   // ViewShare / ViewUnmap
    ULONG           AllocationType,       // 0 typical; MEM_RESERVE if view should not commit
    ULONG           Win32Protect
);
```

### Process hollowing layout

1. Create child process suspended (`CreateProcessW` with `CREATE_SUSPENDED`)
2. Get child's main thread context → entry point IP, PEB pointer
3. `NtUnmapViewOfSection(child_handle, child_peb_image_base)` — remove original image
4. `NtAllocateVirtualMemory` at original ImageBase in child
5. `NtWriteVirtualMemory` — copy malicious PE and apply relocations
6. `NtSetContextThread` — set child thread RIP to malicious entry point
7. `NtResumeThread` — child starts executing payload

### Module stomping

Instead of unmapping, overwrite a **legitimately loaded** DLL's `.text` with shellcode:
1. Load a non-essential signed DLL (e.g., `ARIA-debug-0.dll`, `XpsPrint.dll`)
2. `NtProtectVirtualMemory` on its `.text` → RW
3. Overwrite with shellcode
4. `NtProtectVirtualMemory` → RX
5. Invoke via DLL's exported entry (intercepted by shellcode)

Detection: `MEM_IMAGE` page with modified content vs on-disk file hash mismatches. Defender queries `MemoryMappedFilenameInformation` and can compare.

### Phantom DLL Hollowing (TxF)

Uses the deprecated Transactional NTFS (TxF) to create a file you can write to, map as SEC_IMAGE, then roll back — the mapped view persists but the file has no on-disk artifact.

1. `CreateFileTransacted` — open transaction handle
2. `CreateFile*(txf_handle)` on a path you want to masquerade as — opens a private copy
3. Write shellcode to the private copy
4. `NtCreateSection(SEC_IMAGE, file_handle)` — maps the private copy
5. `NtRollbackTransaction` — discards on-disk changes; the mapped section persists
6. Map the section in a target process

TxF is deprecated but still supported through Win11 24H2. Kernel ETW tracks TxF operations.

---

## Heaps

Heap = a manager of dynamically-sized allocations inside a reserved VA region.

### NT Heap (legacy, pre-Win10)

Used by `HeapCreate` / `HeapAlloc` before the Segment Heap. Still default for many processes that don't opt into Segment Heap.

Data structures:
- `HEAP` — process heap descriptor, with segment pointers, free lists, LFH context
- `HEAP_SEGMENT` — contiguous VA range backing the heap
- `HEAP_ENTRY` — 16-byte header prepended to every allocation (contains size, flags, checksum)

**Heap layout hunters** — malware often stores payloads in heap. Scanning a process heap via `HeapWalk` reveals allocation patterns.

### Segment Heap (Windows 10+ default for UWP, Edge, many apps)

Full replacement for NT Heap. Introduced to reduce fragmentation and improve multi-core scalability. Opt-in per-process via `FRONT_END_HEAP_TYPE` registry key or `IMAGE_LOAD_CONFIG.HeapInformation`.

Structures:
- `_SEGMENT_HEAP` — root descriptor. Contains LfhContext, SegContexts[], LargeAllocMetadata
- `_HEAP_LFH_CONTEXT` — LFH state: per-size-class buckets with subsegment arrays
- `_HEAP_SUBSEGMENT` — contains blocks of one size class, with bitmap of free/used slots

Allocation path:
1. Size ≤ 0x200 → VS (Variable Size) allocator
2. 0x200 < Size ≤ 0x3FF0 → LFH
3. Size > 0x3FF0 → Segment allocator (direct VA)
4. Very large (>some threshold) → Large Blocks list

### Low Fragmentation Heap (LFH)

LFH is a front-end allocator that kicks in after a size class is "activated" — typically after ~17 consecutive allocations of near-same-size blocks.

Features:
- **Size-class buckets**: allocations are bucketed into one of ~128 size classes
- **Subsegment pool**: each bucket has 1+ subsegments, each holding fixed-size blocks
- **Per-size popularity tracking**: unused size classes don't waste memory
- **Randomized first-fit**: newer LFH variants pick a randomly selected free slot in the bitmap, mitigating deterministic heap exploitation

Heap exploitation depends on predictable layout — LFH randomization raises the bar considerably.

### Heap-related telemetry

- `NtCreateHeap` / `RtlCreateHeap` — no direct ETW event, but LoadImage for the process capturing ntdll init
- Large allocations (>1MB) via heap → observable as `NtAllocateVirtualMemory` of that size
- Heap overflow to committed guard page → STATUS_HEAP_CORRUPTION, terminating

---

## VADs — Virtual Address Descriptors (kernel-side)

Every allocation is tracked by a VAD tree (AVL) in the EPROCESS. `MmGetVadTree`, `vadroot` in EPROCESS.

### VAD entry fields (relevant to forensics)

- `StartingVpn`, `EndingVpn` — page numbers (divide by 0x1000 for VA)
- `u.VadFlags` — VadType (MemImageMap, MemFileMap, MemPrivate), Protection
- `ControlArea` — for mapped sections, points to section info
- `SubSection` — for SEC_IMAGE mappings, per-section protection
- `MemCommit` bit, `PrivateMemory` bit

### What defenders see via VAD walk

The kernel-side VAD tree is the **ground truth** of what memory exists in a process. Hiding from PEB LDR lists does not hide from VAD:
- ReflectivelyLoaded PE → VAD shows `MemPrivate` region of image size with RX protection, but VadType is not MemImageMap → mismatch signal
- Stomped module → VadType is MemImageMap but content diverges from file on disk

Tools like Volatility walk VAD to find "hidden" modules. Moneta, PE-sieve, Hollows Hunter inspect user-mode proxies of VAD data.

---

## Memory-scanning heuristics (defender side)

When defenders scan a process for malicious memory, they apply these rules:

| Rule | Flag severity |
|---|---|
| `MEM_PRIVATE` with `PAGE_EXECUTE_*` | High (shellcode typical signature) |
| `MEM_IMAGE` with page content differing from on-disk | High (stomped/patched DLL) |
| `MEM_IMAGE` with VadType=MemImageMap but no entry in PEB Ldr | High (unlinked module) |
| `MEM_PRIVATE` executable regions containing PE header bytes | Very high (reflective PE in RWX) |
| Thread starting at RIP inside MEM_PRIVATE | Medium |
| Large `PAGE_EXECUTE_READWRITE` region | High |
| `PAGE_NOACCESS` pages near stack that don't match guard page pattern | Medium (injection canary) |

Counter-patterns:
- Load payload as `SEC_IMAGE` via phantom DLL hollowing → VadType is MemImageMap, but on-disk content matches (because the file was rolled back)
- Use Dharma-style direct map: allocate RX region then immediately memset headers to zero (no PE header bytes)
- Proxy shellcode execution via legit RX (module stomping)

---

## Kernel memory structures (peek only — deeper in `kernel-objects.md`)

- `MiSessionSpace` / `MiSystemVa` — regions of kernel VA
- `_MMVAD_SHORT` / `_MMVAD_LONG` — per-allocation kernel descriptors
- `_MM_SESSION_SPACE` — per-session address space (win32k.sys etc.)
- Large pages, transition PTEs, prototype PTEs — MMU-level details

---

## Mitigations on memory operations

### ASLR

- Enabled via `IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE`. Required for DLLs loaded into protected processes.
- High-entropy ASLR (`IMAGE_DLLCHARACTERISTICS_HIGH_ENTROPY_VA`) → 64-bit image base randomization.
- Kernel-space ASLR randomizes ntoskrnl, HAL, PFN database locations.

### DEP / NX

- Enforced by NX bit in PTE. Set for any page without `PAGE_EXECUTE_*`.
- `SetProcessDEPPolicy` turns it permanently on.
- OptOut / AlwaysOff modes still exist for legacy compatibility.

### ASR — Attack Surface Reduction

Defender-driven. Blocks specific operations:
- Office apps creating child processes
- Process executions of downloaded content
- `CreateRemoteThread` from specific processes
- Credential stealing from LSASS

### Arbitrary Code Guard (ACG)

Opt-in via `SET_PROCESS_MITIGATION_POLICY`. Blocks:
- New executable allocations
- Protection transitions to executable
- Writable code

Breaks JIT engines. Chrome enables for renderer processes.

### Code Integrity Guard (CIG)

Only signed images may be loaded. Used by Defender processes, Edge renderer.

---

## Offensive allocation patterns

### Sleep obfuscation memory flow

```
State A (running):
  shellcode region protection: RX
  GOT/heap: RW
  stack: RW

Preparing to sleep:
  Transition: shellcode RX → RW          (NtProtectVirtualMemory)
  Transform: XOR/MBA encrypt shellcode
  Optionally: encrypt GOT/heap tracked entries

Sleeping:
  shellcode: RW (encrypted bytes, non-executable)
  Sleep for duration (NtDelayExecution)

Waking:
  Transform: decrypt shellcode
  Transition: shellcode RW → RX
  Optionally: decrypt heap

State A (running) again
```

**Who executes these transitions?** Not the shellcode itself — it would need to stay executable during its own encryption. A **trampoline** in a separate RX page (never encrypted) runs the encrypt/decrypt/protect sequence. The trampoline has to resolve NtProtectVirtualMemory + NtDelayExecution addresses and SSNs once at init.

### Defender signature for fluctuating memory

EtwTi `FluctuationMonitor` captures the RX↔RW↔RX pattern on the **same region** within a short window. Strong signal. Counter: use different regions each iteration (moving target), or use module stomping with transitions that match legitimate hot-patch behavior.

---

## Kernel memory primitives for rootkits (brief)

- `MmGetSystemRoutineAddress("RoutineName")` — resolve kernel symbols (or walk ntoskrnl's export table)
- `ExAllocatePool2(POOL_FLAG_*, Size, Tag)` — kernel pool allocation (post-Win10 1903)
- `MmAllocateContiguousMemorySpecifyCache` — for DMA
- `MmMapIoSpace` — map physical addresses
- `MmProbeAndLockPages` — lock pages for DMA

Pool memory has tags (4-byte ASCII) — unique per driver, allows `!poolused` WinDbg attribution. Using "randomized" tags is a common rootkit evasion that itself is an IOC.

---

## Common syscall bundles

### Allocate + write + execute (classic shellcode runner)

```
NtAllocateVirtualMemory(RW)  → addr
NtWriteVirtualMemory(addr, shellcode)
NtProtectVirtualMemory(addr, RX)
NtCreateThreadEx(start=addr)
```

Signature: all four syscalls from same thread in rapid sequence. Correlation rule in most EDRs.

### Alloc-free-pattern (sleep obfuscation with fresh region each iter)

```
loop:
  NtAllocateVirtualMemory(size=N, RW) → new_addr
  NtWriteVirtualMemory(new_addr, payload_copy)
  NtProtectVirtualMemory(new_addr, RX)
  // continue execution in new_addr
  NtFreeVirtualMemory(old_addr, MEM_RELEASE)
```

Avoids same-region fluctuation signal. Costs time per iteration.

### Section roundtrip (module-stomping alternative)

```
NtCreateSection(SEC_COMMIT, pagefile) → hSection
NtMapViewOfSection(hSection, curr_proc, RW) → local_view
write shellcode to local_view
NtMapViewOfSection(hSection, remote_proc, RX) → remote_view
// shellcode now in remote without NtWriteVirtualMemory
```

Avoids cross-process `NtWriteVirtualMemory`, which triggers `EtwTiLogWriteVm`. But `NtMapViewOfSection` cross-process with `SEC_COMMIT + RX` is itself an IOC.

---

## Debug registers (DR0–DR7)

Hardware breakpoints. Per-thread context. Fields in `CONTEXT`:
- `Dr0`..`Dr3` — breakpoint addresses
- `Dr6` — status register (which DR triggered)
- `Dr7` — control register (enable bits, length, type)

Use:
- Userland anti-debug: check `Dr0..Dr3` nonzero → debugger attached
- HWSyscall bypass: set DR0 on syscall instruction, use VEH to modify RAX at hit
- Hardware page monitoring: DR with L-type "on access" — limited to 4 addresses

Windows 10+ records DR modifications via ETW-TI in recent builds.

---

## KPP / PatchGuard / Kernel Patch Protection

Periodically scans critical kernel structures for modification. Detects:
- SSDT modifications
- IDT modifications
- MSR modifications (LSTAR, etc.)
- Function prologue patches in ntoskrnl / HAL
- GDT modifications

On detection: BSOD (`KERNEL_SECURITY_CHECK_FAILURE` or `CRITICAL_STRUCTURE_CORRUPTION` 0x109).

Modern rootkits avoid KPP-watched structures, instead:
- Hook kernel callbacks (not KPP-watched)
- BYOVD (vulnerable driver primitives)
- Virtualization-level (under hypervisor; requires Ring -1 code)

---

## Summary: key memory invariants

- Reserved pages are inaccessible. Committed pages are accessible per their Protect.
- Allocation granularity is 64KB. Page granularity is 4KB.
- Protection changes are page-granular; `OldProtect` reports first page only.
- `MEM_PRIVATE` with execute protection is the most common shellcode signature.
- Cross-process `NtReadVirtualMemory`/`NtWriteVirtualMemory` always triggers ETW-TI.
- VADs are authoritative; PEB lists are hints from userland.
- Section-based injection avoids VM syscalls but creates its own telemetry.
