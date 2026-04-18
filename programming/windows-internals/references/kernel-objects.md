# Kernel Objects & Callbacks

Everything in NT — processes, threads, files, events, sections, tokens, registry keys, ALPC ports — is an object managed by the Object Manager. Each object sits under a type (`nt!_OBJECT_TYPE`), has a header (`nt!_OBJECT_HEADER`), a name in the object namespace (optional), a security descriptor, and a reference count. Kernel callbacks let drivers hook object lifecycle transitions; EDRs rely on those hooks to observe process/thread/image events without userland cooperation. This reference covers the kernel-side structures malware has to model correctly to hide from, and the callback surface defenders use to see it.

## EPROCESS

`nt!_EPROCESS` is the kernel's per-process control block. Field offsets shift build to build — use `dt nt!_EPROCESS` in WinDbg against the live kernel for ground truth. The following fields are the load-bearing ones for offensive/defensive work:

| Field | Semantic |
|---|---|
| `Pcb` (KPROCESS) | Scheduler state: `DirectoryTableBase` (CR3 physical), thread list heads, affinity, ready queue |
| `ProcessLock` (EX_PUSH_LOCK) | Protects EPROCESS mutations |
| `UniqueProcessId` | PID (`HANDLE`) |
| `ActiveProcessLinks` | Doubly-linked list of all EPROCESSes — root at `PsActiveProcessHead` |
| `VadRoot` (RTL_AVL_TREE) | AVL tree of Virtual Address Descriptors — authoritative memory map |
| `ObjectTable` (`_HANDLE_TABLE*`) | Per-process handle table |
| `Token` (`_EX_FAST_REF`) | Low 4 bits are reference count, upper bits point to `_TOKEN` |
| `WorkingSetLock` | Protects working-set state |
| `Peb` | User-mode PEB pointer (valid in process context only) |
| `Wow64Process` (`_EWOW64PROCESS*`) | Non-NULL for WoW64 processes — holds 32-bit PEB |
| `InheritedFromUniqueProcessId` | PPID |
| `ImageFileName[15]` | Short ANSI image name (truncated) |
| `SeAuditProcessCreationInfo` | Full image name (`UNICODE_STRING`) captured at create time |
| `ImageFilePointer` (`_FILE_OBJECT*`) | File object backing the image |
| `ImagePathHash` | Hash used for AppLocker/WDAC lookups |
| `Protection` (PS_PROTECTION) | PP/PPL byte — Type:3, Audit:1, Signer:4 |
| `SignatureLevel` / `SectionSignatureLevel` | Code integrity policy for new mappings |
| `MitigationFlags` / `MitigationFlags2` | DEP/ASLR/CFG/image-load policy bits |
| `Job` (`_EJOB*`) | Associated job object |
| `Session` | Session object for the terminal session |
| `ExitStatus` | Final NTSTATUS when exiting |
| `PicoContext` | WSL1 / Pico-provider state |

`MitigationFlags` bits (offensive-relevant):

| Bit | Name | Effect |
|---|---|---|
| `ControlFlowGuardEnabled` | 0 | CFG enforces valid indirect-call targets |
| `ControlFlowGuardExportSuppressionEnabled` | 1 | Export suppression |
| `ControlFlowGuardStrict` | 2 | Strict CFG (fail on unknown targets) |
| `DisallowStrippedImages` | 3 | Block images missing load config |
| `ForceRelocateImages` | 4 | Force ASLR on images without DYNAMIC_BASE |
| `HighEntropyASLREnabled` | 5 | 64-bit ASLR entropy |
| `StackRandomizationDisabled` | 6 | Debug flag |
| `ExtensionPointDisable` | 7 | Block AppInit_DLLs, WinEvent hooks, IMEs |
| `DisableDynamicCode` | 8 | ACG — block RWX/later-W |
| `DisableDynamicCodeAllowOptOut` | 9 | Per-thread opt-out via SetThreadInformation |
| `DisableDynamicCodeAllowRemoteDowngrade` | 10 | Remote-process disable allowed |
| `AuditDisableDynamicCode` | 11 | Audit-only mode |
| `DisallowWin32kSystemCalls` | 12 | Block user32/gdi32 syscalls (Chromium renderer) |
| `AuditDisallowWin32kSystemCalls` | 13 | Audit-only |
| `EnableFilteredWin32kAPIs` | 14 | Per-API filter |
| `AuditFilteredWin32kAPIs` | 15 | Audit-only |
| `DisableNonSystemFonts` | 16 | Block non-system fonts |
| `AuditNonSystemFontLoading` | 17 | |
| `PreferSystem32Images` | 18 | Search system32 first |
| `ProhibitLowILImageMapping` | 19 | Block mapping low-IL images |
| `SignatureMitigationOptIn` | 20 | Microsoft-signed only |
| `AuditBlockNonMicrosoftBinaries` | 21 | |
| `AuditBlockNonMicrosoftBinariesAllowStore` | 22 | |
| `LoaderIntegrityContinuityEnabled` | 23 | CIG |
| `AuditLoaderIntegrityContinuity` | 24 | |
| `EnableModuleTamperingProtection` | 25 | |
| `EnableModuleTamperingProtectionNoInherit` | 26 | |
| `RestrictIndirectBranchPrediction` | 27 | Spectre v2 mitigation |
| `IsolateSecurityDomain` | 28 | |
| `EnableExportAddressFilter` | 29 | EAF — breakpoints on Kernel32 exports |
| `AuditExportAddressFilter` | 30 | |
| `EnableExportAddressFilterPlus` | 31 | EAF+ with additional modules |

`MitigationFlags2` (newer, partial):

| Bit | Name |
|---|---|
| 0 | `EnableRopStackPivot` (audit/enforce) |
| 1 | `AuditRopStackPivot` |
| 2 | `EnableRopCallerCheck` |
| 3 | `AuditRopCallerCheck` |
| 4 | `EnableRopSimExec` |
| 5 | `AuditRopSimExec` |
| 6-7 | CET user/kernel shadow stack |
| 8-11 | CET strict mode, compatible mode, etc. |
| 12+ | Intel CET/IBT policy |

## ETHREAD

`nt!_ETHREAD` per-thread control block:

| Field | Semantic |
|---|---|
| `Tcb` (KTHREAD) | Scheduler state — TEB pointer, StackBase/StackLimit, InitialStack, Affinity, State, Priority, Context switches |
| `CreateTime` | KeQueryPerformanceCounter at thread creation |
| `ExitTime` / `ExitStatus` | Populated on exit |
| `Cid` (CLIENT_ID) | UniqueProcess=PID, UniqueThread=TID |
| `KeyedWaitChain` | For KEVENT chains |
| `ThreadLock` | Per-thread push lock |
| `ThreadListEntry` | Links into EPROCESS->ThreadListHead |
| `IrpList` | Pending IRPs targeting this thread |
| `TopLevelIrp` | Currently processed IRP |
| `DeviceToVerify` | File-system verify state |
| `StartAddress` | User-mode thread entry (captured; spoofable) |
| `Win32StartAddress` | Win32 thread entry (`RtlUserThreadStart` target) |
| `LpcReplyChain` | ALPC |
| `ImpersonationInfo` (`_PS_IMPERSONATION_INFORMATION*`) | Thread impersonation token + level |
| `CrossThreadFlags` | HideFromDbg, SystemThread, HardErrorsAreDisabled, BreakOnTermination, SkipCreationMsg, SkipTerminationMsg, CopyTokenOnOpen, ThreadIoPriority, ThreadPagePriority, RundownFail |
| `SameThreadPassiveFlags` | ActiveExWorker, ExWorkerCanWaitUser, MemoryMaker |
| `SameThreadApcFlags` | LpcReceivedMsgIdValid, LpcExitThreadCalled, AddressSpaceOwner, OwnsProcessWorkingSetExclusive/Shared, SuppressSymbolLoad, Prefetching, OwnsVadExclusive, SystemPagePriorityActive |
| `CachedEventLogEnabled` | Event log fast-path |

`KTHREAD` sub-fields worth knowing:

| Field | Semantic |
|---|---|
| `InitialStack`, `StackBase`, `StackLimit`, `KernelStack` | Kernel stack bounds — used by KASLR, stack walks |
| `Teb` | User-mode TEB (NULL for system threads) |
| `TrapFrame` (`_KTRAP_FRAME*`) | Saved user-mode register context on kernel entry |
| `FirstArgument` | First arg to thread start |
| `ContextSwitches` | Useful for liveness |
| `State` | KTHREAD_STATE enum (Running, Ready, Standby, Terminated, Waiting, Transition, DeferredReady, GateWait) |
| `WaitReason` | Why blocked |
| `WaitListEntry` | Dispatcher wait list |
| `Queue` | KQUEUE for I/O completion |
| `Process` (`_KPROCESS*`) | Parent KPROCESS |
| `UserAffinity`, `Affinity`, `IdealProcessor` | Scheduling |
| `ApcState` (KAPC_STATE) | User and kernel APC queues, in-progress APC |
| `ApcStatePointer[2]` | Current and saved APC state (for attach) |
| `SavedApcState` | Saved when attached to another process |
| `SpecialApcDisable` | Non-zero = special APCs blocked |
| `Header` (DISPATCHER_HEADER) | Waitable object header |

## KPCR / KPRCB

Per-CPU processor control region (`nt!_KPCR`) and control block (`nt!_KPRCB`):

- `KPCR` addressed via `gs:[0]` in kernel mode on x64. Mirrors many KPRCB fields at low offsets for fast access.
- `KPCR->Prcb` points at the `KPRCB`.
- `KPRCB->CurrentThread` = running KTHREAD on this CPU.
- `KPRCB->NextThread`, `KPRCB->IdleThread` — scheduler slots.
- `KPRCB->DpcQueue`, `KPRCB->DpcStack`, `KPRCB->DpcRoutineActive` — DPC dispatch.
- `KPRCB->InterruptCount`, `KPRCB->KernelTime`, `KPRCB->UserTime` — perf counters.
- `KPRCB->IsrDpcStats` — ISR/DPC profiling.
- `KPCR->TssBase` → `KTSS64` with RSP0/RSP1/RSP2 (ring 0/1/2 stacks), IST[7] (interrupt stacks for NMI/double-fault/machine-check), IOPB.

On ARM64, `KPCR` is reached via `TPIDR_EL1`. Same logical layout, different arch details.

## Handle table

`_HANDLE_TABLE`:

| Field | Semantic |
|---|---|
| `NextHandleNeedingPool` | ULONG, hands out next index |
| `ExtraInfoPages` | Aux state |
| `TableCode` | Pointer to level-0 array — low bits encode depth (0=single, 1=two-level, 2=three-level) |
| `QuotaProcess` | Process charged for handle quota |
| `HandleTableList` | Global list — root at `nt!HandleTableListHead` (older builds) |
| `UniqueProcessId` | Owner PID |
| `HandleCount` / `HandleTableLock` | Stats and sync |

Handle values are `4 * index` (low 2 bits reserved for user flags: `OBJ_INHERIT`, `OBJ_PROTECT_CLOSE`). The table is a 1-/2-/3-level array of `HANDLE_TABLE_ENTRY`:

```c
struct _HANDLE_TABLE_ENTRY {
    union {
        // 0x0: GrantedAccess is low bits, ObjectPointerBits high
        ULONG_PTR VolatileLowValue;       // low: ref count + attributes
        ULONG_PTR LowValue;
        struct _HANDLE_TABLE_ENTRY_INFO* InfoTable;
    };
    union {
        ULONG_PTR HighValue;              // high: GrantedAccess + NoRightsUpgrade
        struct _HANDLE_TABLE_ENTRY* NextFreeHandleEntry;
        union _EXHANDLE LeafHandleValue;
    };
};
```

On x64 the object pointer is compressed: `(LowValue & 0xFFFFFFFFFFFFFFF0) | 0xFFFF000000000000` (sign-extended 44-bit). `HighValue` holds `GrantedAccess` (low 25 bits) and attribute bits (`Attributes` top byte).

## OBJECT_HEADER

Every Object Manager object is preceded by `_OBJECT_HEADER` in kernel memory:

```c
struct _OBJECT_HEADER {
    LONG  PointerCount;         // kernel references
    union {
        LONG HandleCount;       // user-mode handles
        PVOID NextToFree;
    };
    EX_PUSH_LOCK Lock;
    UCHAR TypeIndex;            // obfuscated: real = (TypeIndex XOR ObHeaderCookie XOR (address >> 8)) & 0xFF
    UCHAR TraceFlags;
    UCHAR InfoMask;             // bitmap of optional header presence
    UCHAR Flags;                // DefaultSecurityQuota, ExclusiveObject, PermanentObject, KernelOnlyAccess, etc.
    union {
        PVOID ObjectCreateInfo;
        PVOID QuotaBlockCharged;
    };
    PVOID  SecurityDescriptor;
    QUAD   Body;                // object body starts here — type-specific
};
```

`InfoMask` controls which optional headers exist immediately BEFORE `_OBJECT_HEADER` in memory (reverse-stacked):

| Bit | Optional header | Offset (negative from `_OBJECT_HEADER`) |
|---|---|---|
| 0x01 | `_OBJECT_HEADER_CREATOR_INFO` | size 0x20 |
| 0x02 | `_OBJECT_HEADER_NAME_INFO` | size 0x20 |
| 0x04 | `_OBJECT_HEADER_HANDLE_INFO` | size 0x10 |
| 0x08 | `_OBJECT_HEADER_QUOTA_INFO` | size 0x20 |
| 0x10 | `_OBJECT_HEADER_PROCESS_INFO` | size 0x10 |
| 0x20 | `_OBJECT_HEADER_AUDIT_INFO` | size 0x10 |
| 0x40 | `_OBJECT_HEADER_PADDING_INFO` | |
| 0x80 | `_OBJECT_HEADER_EXTENDED_INFO` | |

`ObpInfoMaskToOffset[InfoMask & 0x7F]` gives cumulative size to walk back.

## Object types

`nt!ObTypeIndexTable[]` is an array of `_OBJECT_TYPE*`. Decoding the real type:

```c
PUCHAR pHeader = (PUCHAR)pObject - sizeof(OBJECT_HEADER) + FIELD_OFFSET(OBJECT_HEADER, Body);
UCHAR tIdxRaw = ((OBJECT_HEADER*)pHeader)->TypeIndex;
UCHAR idx = tIdxRaw ^ ObHeaderCookie ^ ((ULONG_PTR)pHeader >> 8);
POBJECT_TYPE type = ObTypeIndexTable[idx];
```

`ObHeaderCookie` is a single byte exported (kernel-private) at `nt!ObHeaderCookie`. Introduced as anti-abuse on Win10.

Common type names (in `\ObjectTypes` namespace): `Process`, `Thread`, `Job`, `Token`, `DebugObject`, `File`, `Directory`, `SymbolicLink`, `Key`, `Event`, `Mutant`, `Semaphore`, `Section`, `Port`, `ALPC Port`, `WaitCompletionPacket`, `IoCompletion`, `Timer`, `IRTimer`, `Desktop`, `WindowStation`, `TpWorkerFactory`, `TmTm`, `TmTx`, `TmRm`, `TmEn`, `RegistryTransaction`, `UserApcReserve`, `IoCompletionReserve`, `ActivityReference`, `PsSiloContextPaged`, `PsSiloContextNonPaged`, `Partition`, `EnergyTracker`, `CoreMessaging`.

`OBJECT_TYPE` carries a `_OBJECT_TYPE_INITIALIZER` with method pointers:

| Hook | Purpose |
|---|---|
| `DumpProcedure` | Debug dump |
| `OpenProcedure` | Fired on handle open — object-type-specific |
| `CloseProcedure` | Fired on user-mode `NtClose` |
| `DeleteProcedure` | Fired when reference count drops to 0 |
| `ParseProcedure` / `ParseProcedureEx` | Name-based lookup in parent directory |
| `SecurityProcedure` | Security descriptor ops |
| `QueryNameProcedure` | Returns object path |
| `OkayToCloseProcedure` | Veto handle close |

Process/Thread objects also carry `CallbackList` head used by `ObRegisterCallbacks`.

## Object namespace

Kernel objects form a hierarchy under `\`:

| Path | Contents |
|---|---|
| `\ObjectTypes` | Type objects themselves |
| `\GLOBAL??` | DOS device-name symlinks (`C:`, `HarddiskVolume1`, …) |
| `\Device` | Device objects |
| `\Driver` | Driver objects |
| `\FileSystem` | FS drivers |
| `\KnownDlls` / `\KnownDlls32` | Section objects for DLLs resolved from signed cache |
| `\Sessions\<N>` | Per-session subtree |
| `\Sessions\<N>\BaseNamedObjects` | Session-scoped `BaseNamedObjects` namespace — mutexes/events apps create |
| `\BaseNamedObjects` | Global variant (Session 0) |
| `\Windows\WindowStations` | Window stations |
| `\KernelObjects` | Well-known events (`LowMemoryCondition`, `SystemErrorPortReady`, etc.) |
| `\RPC Control` | RPC ALPC ports |

Tools: `winobj.exe` (Sysinternals), `NtOpenDirectoryObject` + `NtQueryDirectoryObject` programmatically.

Malware surveys `\KnownDlls` to obtain signed section handles for unhooked module images (classic Perun/KnownDlls-unhooking pattern).

## Kernel callbacks

The defender's anchor points. Drivers register callbacks; the kernel fires them on lifecycle events. EDR drivers stack on top of these.

### Process create/exit

```c
NTSTATUS PsSetCreateProcessNotifyRoutine(
    PCREATE_PROCESS_NOTIFY_ROUTINE NotifyRoutine,
    BOOLEAN Remove
);

NTSTATUS PsSetCreateProcessNotifyRoutineEx(
    PCREATE_PROCESS_NOTIFY_ROUTINE_EX NotifyRoutine,
    BOOLEAN Remove
);

// Ex2 — Win10 1703+, supports PS_CREATE_NOTIFY_INFO with process handle
NTSTATUS PsSetCreateProcessNotifyRoutineEx2(
    PSCREATEPROCESSNOTIFYTYPE NotifyType,
    PVOID NotifyInformation,
    BOOLEAN Remove
);
```

`PS_CREATE_NOTIFY_INFO` carries full process creation context — image file name, command line, parent PID, creating thread/process IDs, file object, and a writable `NTSTATUS CreationStatus` — setting non-success in the callback BLOCKS the create. This is how EDRs veto suspicious spawns.

Limit: max 64 registered callbacks (hard-coded array `PspCreateProcessNotifyRoutine[64]`).

### Thread create/exit

```c
NTSTATUS PsSetCreateThreadNotifyRoutine(PCREATE_THREAD_NOTIFY_ROUTINE);
NTSTATUS PsSetCreateThreadNotifyRoutineEx(
    PSCREATETHREADNOTIFYTYPE Type,  // PsCreateThreadNotifyNonSystem, PsCreateThreadNotifySubsystems
    PVOID NotifyRoutine
);
```

Fires in target-process context for BOTH remote and in-process thread creation. Parameters: ProcessId, ThreadId, Create (BOOLEAN).

Does NOT fire for system threads unless `PsCreateThreadNotifySubsystems` variant requested. Limit: 64.

### Image load

```c
NTSTATUS PsSetLoadImageNotifyRoutine(PLOAD_IMAGE_NOTIFY_ROUTINE);
NTSTATUS PsSetLoadImageNotifyRoutineEx(
    PLOAD_IMAGE_NOTIFY_ROUTINE NotifyRoutine,
    ULONG Flags  // PS_IMAGE_NOTIFY_CONFLICTING_ARCHITECTURE etc.
);
```

Fires for mappings created via `NtCreateSection(SEC_IMAGE)` THEN mapped into a process — includes `LoadDll`, `MapViewOfSection` with SEC_IMAGE. Does NOT fire for manual mapping (private allocations with RWX holding a PE) — that's the evasion blind spot.

Parameters: `UNICODE_STRING ImageName`, `HANDLE ProcessId`, `IMAGE_INFO { ImageAddressingMode; SystemModeImage; ImageMappedToAllPids; ExtendedInfoPresent; MachineTypeMismatch; ImageSignatureLevel; ImageSignatureType; ImagePartialMap; ImageBase; ImageSelector; ImageSize; ImageSectionNumber }`.

If `ExtendedInfoPresent`, parameter is `IMAGE_INFO_EX` which adds `FileObject*`. EDRs use this to scan the backing file on mapping.

### Handle operations (object callbacks)

```c
NTSTATUS ObRegisterCallbacks(
    POB_CALLBACK_REGISTRATION CallbackRegistration,
    PVOID*                    RegistrationHandle
);
```

`OB_CALLBACK_REGISTRATION` registers per-type pre/post handle operation callbacks. Only `PsProcessType` and `PsThreadType` are legal targets (plus `IoFileObjectType` on newer builds for DFS and minifilter-adjacent scenarios, but historically blocked).

Pre-operation callback receives `OB_PRE_OPERATION_INFORMATION`:

```c
struct _OB_PRE_OPERATION_INFORMATION {
    OB_OPERATION Operation;    // OB_OPERATION_HANDLE_CREATE or OB_OPERATION_HANDLE_DUPLICATE
    ULONG KernelHandle : 1;
    PVOID Object;
    POBJECT_TYPE ObjectType;
    PVOID CallContext;
    union _OB_PRE_OPERATION_PARAMETERS* Parameters;
    // Parameters->CreateHandleInformation.DesiredAccess (writable)
    // Parameters->CreateHandleInformation.OriginalDesiredAccess
};
```

Callback can **strip** access bits from `DesiredAccess`, not grant. This is how Defender/EDR drop `PROCESS_VM_WRITE`/`PROCESS_VM_OPERATION`/`PROCESS_CREATE_THREAD` from handles to LSASS.

Altitude constraints: `ObRegisterCallbacks` requires the driver to be signed and have `IMAGE_DLLCHARACTERISTICS_APPCONTAINER`-era signing level. Breaks on unsigned PoCs unless test-signing enabled.

### Registry callbacks

```c
NTSTATUS CmRegisterCallbackEx(
    PEX_CALLBACK_FUNCTION Function,
    PCUNICODE_STRING      Altitude,
    PVOID                 Driver,
    PVOID                 Context,
    PLARGE_INTEGER        Cookie,
    PVOID                 Reserved
);
```

Called for every registry op by anyone in kernel or userland. `REG_NOTIFY_CLASS` enum has ~50 values (`RegNtPreCreateKey`, `RegNtPreSetValueKey`, `RegNtPreDeleteKey`, `RegNtPostOpenKey`, …). Pre-callbacks can fail the operation; post-callbacks observe.

Used by AV for autostart monitoring, offensive tooling for stealth persistence detection.

### Minifilter callbacks

Full FltMgr-based filesystem filtering. Driver registers via `FltRegisterFilter` with an `FLT_REGISTRATION` table listing pre- and post-callbacks per-IRP-major-code (IRP_MJ_CREATE, IRP_MJ_READ, IRP_MJ_WRITE, IRP_MJ_SET_INFORMATION for renames/deletes, IRP_MJ_CLEANUP, IRP_MJ_CLOSE, IRP_MJ_DIRECTORY_CONTROL, IRP_MJ_QUERY_INFORMATION, etc.).

Altitudes (decimal strings 0-429999) enforce load order:

| Range | Class |
|---|---|
| 420000-429999 | Filter |
| 400000-409999 | Anti-virus |
| 380000-389999 | Replication |
| 360000-369999 | Continuous Backup |
| 340000-349999 | Content Screener |
| 320000-329999 | Quota Management |
| 300000-309999 | System Recovery |
| 280000-289999 | Cluster File System |
| 260000-269999 | HSM |
| 240000-249999 | Compression |
| 220000-229999 | Application |
| 200000-209999 | Encryption |
| 180000-189999 | Virtualization |
| 160000-169999 | Physical Quota Management |
| 140000-149999 | Open File |
| 120000-129999 | Security Enhancer |
| 100000-109999 | Copy Protection |
| 80000-89999 | Bottom |
| 40000-49999 | System |

Defender runs at altitude `328010` (WdFilter). Enumerate loaded minifilters: `fltmc.exe` or `FilterGetDosName`/`FilterVolumeFindFirst`.

### Other callback surfaces

| Registration | Fires on |
|---|---|
| `PsSetBoostPriorityFromKernelProcessor` | Priority boosts (rare EDR usage) |
| `PsSetCreatePartitionNotifyRoutine` | Partition object creation |
| `KeRegisterBugCheckCallback` / `KeRegisterBugCheckReasonCallback` | BSOD context capture |
| `IoRegisterShutdownNotification` | Device shutdown |
| `SeRegisterLogonSessionTerminatedRoutine` | Logon session end |
| `IoRegisterPlugPlayNotification` | PnP events |
| `KeRegisterNmiCallback` | NMI (perfmon) |
| `DbgSetDebugPrintCallback` / `DbgSetDebugFilterState` | DbgPrint routing |
| `EtwRegister` / `EtwRegisterClassicProvider` | Event Tracing — providers |
| `WmiRegister` | WMI provider |

## Removing / hiding callbacks (offensive)

Bypass pattern with a kernel-write primitive (BYOVD or legit driver abuse):

1. Locate `PspCreateProcessNotifyRoutine` by:
   - Disassembling `PsSetCreateProcessNotifyRoutineEx` (first `lea rcx, [PspCreateProcessNotifyRoutine]` relative-displacement).
   - Or scanning `PsSetCreateThreadNotifyRoutine` / `PsSetLoadImageNotifyRoutine` for the equivalent array symbol.
2. Each array entry is `EX_FAST_REF` — low 4 bits = ref count, upper bits point to `_EX_CALLBACK_ROUTINE_BLOCK` (a tiny struct `{ EX_RUNDOWN_REF RundownProtect; PEX_CALLBACK_FUNCTION Function; PVOID Context; }`).
3. To zero a slot: mask off low 4 bits, read block, compare `Function` against the EDR driver base range, then overwrite entry with 0.

Defender monitors this via PatchGuard (section 6 below); clearing callbacks raises `CRITICAL_STRUCTURE_CORRUPTION` (BSOD 0x109) typically within 10 minutes to 2 hours.

`ObRegisterCallbacks` blocks are in a linked list on `PsProcessType->CallbackList` / `PsThreadType->CallbackList` — same removal pattern, walk list and unlink.

## PatchGuard (KPP)

Kernel Patch Protection verifies the integrity of critical kernel structures on random intervals. Observed protected objects:

- SSDT, Shadow SSDT (`KiServiceTable`, `W32pServiceTable`)
- IDT
- GDT
- MSRs (LSTAR, STAR, SYSENTER_*)
- Kernel code (`.text` of `ntoskrnl.exe`, `hal.dll`)
- `PsActiveProcessHead`, `PsLoadedModuleList` (selective)
- `PspCreateProcessNotifyRoutine`, `PspCreateThreadNotifyRoutine`, `PspLoadImageNotifyRoutine`
- `KeServiceDescriptorTable`
- Processor-specific structures (KDPC, KIDTENTRY, GDTR/IDTR)

Detection work is done by `KiDpcInterrupt`-scheduled `KiDpcWatchdog` / `KiFilterFiberContext` chains — obfuscated, self-modifying, reschedules at random. Bypasses need to disable PatchGuard before tampering OR operate on non-protected structures (e.g., per-process `EPROCESS->Token` replacement is NOT directly watched).

Common tamper targets NOT in KPP's direct scope:

- `EPROCESS->Token` (swap for SYSTEM token)
- `EPROCESS->Protection` (clear PPL byte)
- `EPROCESS->SignatureLevel` (lower to allow unsigned mappings)
- `EPROCESS->MitigationFlags` (clear DisableDynamicCode)
- `EPROCESS->ImageFileName` / `SeAuditProcessCreationInfo` (image name spoofing post-create)
- Per-minifilter callback blocks (attackable via unlinking from FltMgr structures)

## Driver-object abuse

`DRIVER_OBJECT` holds `MajorFunction[IRP_MJ_MAXIMUM_FUNCTION+1]` — IRP dispatch table. Hijacking a benign driver's dispatch pointer redirects IRPs to attacker code without loading a new driver (useful if `SeLoadDriverPrivilege` unavailable but kernel-write is).

`DRIVER_OBJECT->DriverSection` points at `KLDR_DATA_TABLE_ENTRY` — the kernel's analog of `LDR_DATA_TABLE_ENTRY`. Unlinking from the list hides the driver from `NtQuerySystemInformation(SystemModuleInformation)`.

## Object namespace attacks

- **Junction / symlink shenanigans** in `\??` (user-accessible DOS namespace). Pre-Win10 allowed creating symlinks as unprivileged user; restricted since but still abuseable in specific layouts.
- **Named pipe squatting**: create `\\.\pipe\Name` before the legitimate service does; incoming connections land on attacker.
- **KnownDlls injection (historical)**: sections under `\KnownDlls` are signed and trusted; writing one = persistent code execution across reboots. Requires SYSTEM and bypassed KnownDlls protection.

## BYOVD

"Bring Your Own Vulnerable Driver" — load a Microsoft-signed-but-vulnerable driver, use its IOCTL interface to gain arbitrary kernel R/W.

Classic examples: `gdrv.sys` (Gigabyte), `rtcore64.sys` (MSI Afterburner), `iqvw64.sys` (Intel), `procexp*.sys` (Process Explorer, before signing updates), `dbutil_2_3.sys` (Dell). Microsoft maintains a block-list (`DriverSiPolicy.p7b`) consumed by HVCI; vulnerable drivers on the list fail to load when HVCI is on.

Load requires:

- `SeLoadDriverPrivilege` (Administrator by default) OR service-install.
- Registry key under `HKLM\System\CurrentControlSet\Services\<name>` with `ImagePath`, `Type=1` (kernel driver), `Start=3` (demand).
- `NtLoadDriver(L"\\Registry\\Machine\\System\\CurrentControlSet\\Services\\<name>")`.

HVCI-enabled systems block unsigned kernel code outright; BYOVD still works because the driver IS signed — but the attacker code running via R/W primitive is data-only (DKOM), no code injection into ring 0 directly. Post-HVCI BYOVD effectively DKOM-only.

## Enumerating callbacks defensively

Userland survey tools:

- `kdmapper` (driver mapper) + custom client querying `PspCreateProcessNotifyRoutine`.
- `ProcessHacker` / `SystemInformer` with `KProcessHacker` / `KSystemInformer` driver loaded → shows registered callbacks.
- `ETWInspector` → enumerates ETW provider consumers.
- Sysmon Event 12/13/14 → registry notifications (useful for catching BYOVD service installs).

Offensive reconnaissance pre-attack:

```c
// Read PspCreateProcessNotifyRoutine via kernel-read primitive
for (i = 0; i < 64; i++) {
    EX_FAST_REF entry = read_kernel_u64(pArrayBase + i*8);
    PVOID block = (PVOID)(entry & ~0xFull);
    if (!block) continue;
    PVOID fn = read_kernel_u64(block + 8);  // Function offset in EX_CALLBACK_ROUTINE_BLOCK
    UNICODE_STRING name = resolve_kernel_address_to_module(fn);
    // entry now maps to a driver; skip or blank based on altitude-like heuristic
}
```

## Practical cheat sheet

| Defender vantage | Offensive blind spot |
|---|---|
| `PsSetCreateProcessNotifyRoutineEx2` — sees every spawn | Direct syscall `NtCreateUserProcess` does NOT bypass it — the callback fires in kernel post-creation regardless. Bypass needs callback removal. |
| `PsSetCreateThreadNotifyRoutine` | Fires on `NtCreateThreadEx` and remote thread creation equally. Thread hijacking (existing thread, `NtSetContextThread`) does NOT fire because no new thread. |
| `PsSetLoadImageNotifyRoutine` | Fires on SEC_IMAGE mappings only. Manual PE loading via `NtAllocateVirtualMemory` + relocation + IAT fixup is invisible here. |
| `ObRegisterCallbacks` handle-access strip | Strips access on open, cannot retroactively. Handles opened before driver load retain full access. |
| `CmRegisterCallbackEx` | Sees all registry ops, including transactional. Registry hive direct file I/O (injecting into `\Device\HarddiskVolumeN\Windows\System32\config\SYSTEM`) bypasses — but requires offline or volume-raw access. |
| Minifilter IRP_MJ_CREATE | Sees file opens. Manual IRP construction via `IoBuildSynchronousFsdRequest` and direct `IoCallDriver` bypasses the filter stack if you send to the FS driver directly. Kernel-only. |
| ETW-TI | Invisible to userland. Clearing `EtwThreatIntProvRegHandle` via kernel write silences it; tracked by some newer EDRs. |
| PatchGuard | Catches tampering with a narrow set of structures. Per-process `EPROCESS` field edits are usually safe. |

## References for layout stability

Symbol file (PDB) downloads give authoritative offsets per build. `symchk`, `pdbstr` from WinDbg tools. Mapping symbols at runtime: parse `ntoskrnl.exe`'s `.pdb` via `dbghelp!SymFromName`. For offline/canned offsets, maintain a per-build table (`ntoskrnl.exe` FileVersion → offset of `PsInitialSystemProcess`, `PsActiveProcessHead`, …). Projects like `VX-API` and several PoCs ship this table hardcoded for common LTSC and current release builds.
