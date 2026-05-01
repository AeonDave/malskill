# Threads and APCs Reference

Thread creation, context manipulation, APC queues (user / kernel / Special), thread hijacking primitives, and the detection surface for each.

---

## Thread lifecycle

### Creation via NtCreateThreadEx

```c
NTSTATUS NtCreateThreadEx(
    PHANDLE             ThreadHandle,          // OUT
    ACCESS_MASK         DesiredAccess,         // THREAD_ALL_ACCESS typical
    POBJECT_ATTRIBUTES  ObjectAttributes,      // usually NULL
    HANDLE              ProcessHandle,         // target process
    PVOID               StartRoutine,          // entry point
    PVOID               Argument,              // passed in rcx to StartRoutine
    ULONG               CreateFlags,           // THREAD_CREATE_FLAGS_*
    SIZE_T              ZeroBits,
    SIZE_T              StackSize,
    SIZE_T              MaximumStackSize,
    PPS_ATTRIBUTE_LIST  AttributeList          // PS_ATTRIBUTE_* entries
);
```

### CreateFlags

| Flag | Value | Meaning |
|---|---|---|
| THREAD_CREATE_FLAGS_CREATE_SUSPENDED | 0x0001 | Thread starts suspended; resume with NtResumeThread |
| THREAD_CREATE_FLAGS_SKIP_THREAD_ATTACH | 0x0002 | Skip DLL_THREAD_ATTACH notifications on DllMain chain |
| THREAD_CREATE_FLAGS_HIDE_FROM_DEBUGGER | 0x0004 | Thread is hidden from `CreateToolhelp32Snapshot` / debugger |
| THREAD_CREATE_FLAGS_HAS_SECURITY_DESCRIPTOR | 0x0010 | ObjectAttributes carries a SD |
| THREAD_CREATE_FLAGS_ACCESS_CHECK_IN_TARGET | 0x0020 | Access check performed in target process's context |
| THREAD_CREATE_FLAGS_SKIP_LOADER_INIT | 0x0080 | **Skip LdrInitializeThunk**; thread jumps straight to StartRoutine |
| THREAD_CREATE_FLAGS_BYPASS_PROCESS_FREEZE | 0x0100 | Thread can run even if process is frozen (UWP) |

**Offensive use of flags**:

- `SKIP_THREAD_ATTACH` on a shellcode thread: avoids calling `DllMain(DLL_THREAD_ATTACH)` across every loaded DLL. Necessary because many DLLs assume threads have proper TEB init — a raw shellcode thread may crash one of them. Also reduces visibility: no `DLL_THREAD_ATTACH` cascade means fewer breadcrumbs.

- `HIDE_FROM_DEBUGGER` sets `NtSetInformationThread(ThreadHideFromDebugger)` internally. Thread is invisible to `OpenThread` from a debugger and to standard toolhelp snapshots.

- `SKIP_LOADER_INIT` bypasses `LdrInitializeThunk` entirely. Thread's first user-mode instruction is your StartRoutine. Powerful but fragile — if your code calls any function that needs TLS or CRT state, undefined behavior.

### AttributeList (PS_ATTRIBUTE_LIST)

Critical for advanced thread creation. Each attribute is an `{attr_id, size, value}` triple.

| Attribute | Value | Purpose |
|---|---|---|
| PS_ATTRIBUTE_PARENT_PROCESS | ... | PPID spoofing (for NtCreateUserProcess) |
| PS_ATTRIBUTE_MITIGATION_OPTIONS | ... | Per-process mitigation mask |
| PS_ATTRIBUTE_TEB_ADDRESS | ... | Custom TEB address |

For thread creation, PS_ATTRIBUTE list is usually NULL. For `NtCreateUserProcess` (process creation), it is the central control channel.

---

## CONTEXT structure (x64)

Full thread register state. Used by `NtGetContextThread` / `NtSetContextThread`.

```c
typedef struct _CONTEXT {
    ULONG64 P1Home, P2Home, P3Home, P4Home, P5Home, P6Home;  // Parameter homes
    ULONG   ContextFlags;        // Which fields are valid
    ULONG   MxCsr;
    USHORT  SegCs, SegDs, SegEs, SegFs, SegGs, SegSs;
    ULONG   EFlags;
    ULONG64 Dr0, Dr1, Dr2, Dr3, Dr6, Dr7;       // Debug registers
    ULONG64 Rax, Rcx, Rdx, Rbx, Rsp, Rbp, Rsi, Rdi;
    ULONG64 R8, R9, R10, R11, R12, R13, R14, R15;
    ULONG64 Rip;
    // union of XMM_SAVE_AREA32 / legacy FPU state
    M128A   Xmm0 .. Xmm15;
    M128A   VectorRegister[26];
    ULONG64 VectorControl;
    ULONG64 DebugControl, LastBranchToRip, LastBranchFromRip,
            LastExceptionToRip, LastExceptionFromRip;
} CONTEXT;           // aligned to 16
```

### ContextFlags — which fields are populated

| Flag | Value | Fields |
|---|---|---|
| CONTEXT_CONTROL | 0x100001 | Rip, Rsp, Rbp, EFlags, segment regs |
| CONTEXT_INTEGER | 0x100002 | Rax..R15 (all GPRs) |
| CONTEXT_SEGMENTS | 0x100004 | Segment registers only |
| CONTEXT_FLOATING_POINT | 0x100008 | XMM0..15, FPU state |
| CONTEXT_DEBUG_REGISTERS | 0x100010 | Dr0..Dr3, Dr6, Dr7 |
| CONTEXT_FULL | CONTROL \| INTEGER \| FP | Common "everything" |

`NtGetContextThread` reads only what `ContextFlags` requests. Set `ContextFlags = CONTEXT_FULL` for typical full snapshot.

---

## Thread suspension / resumption

```c
NtSuspendThread(HANDLE, PULONG PreviousCount);
NtResumeThread(HANDLE,  PULONG PreviousCount);
```

Threads have a suspend count. `NtSuspendThread` increments; `NtResumeThread` decrements. Thread runs when count is 0.

### Cross-process suspension

Requires `THREAD_SUSPEND_RESUME` access on the target thread handle. Which in turn requires `PROCESS_QUERY_LIMITED_INFORMATION` on the process to enumerate threads.

ETW-TI fires `EtwTiLogSuspendResume` for cross-process suspend/resume. Heavily tracked for thread-hijacking detection.

### Suspend during sleep obfuscation

Some sleep techniques (DEEPSLEEP, Foliage) suspend all **other** threads in the current process while encrypting memory and sleeping. Pattern:

1. `NtQuerySystemInformation(SystemProcessInformation)` → walk to our PID's thread list
2. Compare each thread's TID against our own TID (from TEB.ClientId.UniqueThread)
3. For each other thread: `NtOpenThread(THREAD_SUSPEND_RESUME, &cid)` → `NtSuspendThread` → store handle
4. Sleep with memory encryption
5. Decrypt memory
6. For each stored handle: `NtResumeThread` → `NtClose`

If async BOF threads exist, exclude them from suspension — otherwise the process deadlocks or the BOF's thread gets frozen mid-operation.

---

## Thread hijacking

Take control of an **existing** thread by modifying its context, instead of creating a new one.

### Classic hijack sequence

1. Target process has a running thread (say, a worker in a common app)
2. `NtOpenThread(THREAD_GET_CONTEXT | THREAD_SET_CONTEXT | THREAD_SUSPEND_RESUME, tid)`
3. `NtSuspendThread` → wait for genuine suspension (thread may be mid-syscall)
4. `NtGetContextThread(CONTEXT_FULL)` → save original context
5. Allocate shellcode in target, write it
6. Modify context: `Ctx.Rip = shellcode_addr;` — or push return to original Rip onto stack and set Rip to shellcode so it returns naturally
7. `NtSetContextThread(modified_ctx)`
8. `NtResumeThread`

### Detection

- `EtwTiLogContextModification` fires when `NtSetContextThread` changes RIP across processes
- Thread starting to execute from `MEM_PRIVATE` RX region (the shellcode) — high-fidelity IOC
- Suspend/resume pattern on a random thread — correlated signal

### Counter: return-to-shellcode hijack

Instead of setting `Rip = shellcode`, push `Rip` onto the thread's own stack and set `Rip = shellcode`. Shellcode executes, then does `ret` which pops the original Rip. No persistent change to thread behavior — the hijack is a one-shot invocation.

Still leaves a context modification event, but reduces forensic footprint.

---

## APCs — Asynchronous Procedure Calls

An APC is a function the kernel queues to run in the context of a specific thread. Two flavors based on who can queue them:

- **Kernel-mode APC** — queued by kernel code (drivers, I/O completion)
- **User-mode APC** — queued by user-mode code via `NtQueueApcThread*`

And two flavors based on delivery:

- **Normal APC** — requires target thread to be in **alertable** state
- **Special APC** — delivered without alertable requirement

### Alertable state

A thread enters alertable state when blocking in one of:
- `SleepEx(ms, TRUE)`
- `WaitForSingleObjectEx(handle, timeout, TRUE)`
- `WaitForMultipleObjectsEx(..., TRUE)`
- `MsgWaitForMultipleObjectsEx(..., MWMO_ALERTABLE)`
- `SignalObjectAndWait(..., TRUE)`

When alertable **and** the thread has queued APCs, the thread processes them before returning from the wait. If the wait resumed because APCs fired, the wait returns `WAIT_IO_COMPLETION` (0xC0).

Threads that never enter alertable state (the common case for typical worker threads) never process user APCs. This is why classic `QueueUserAPC` injection often fails: the target has no alertable state.

### NtQueueApcThread

```c
NTSTATUS NtQueueApcThread(
    HANDLE ThreadHandle,
    PKNORMAL_ROUTINE ApcRoutine,   // function(NormalContext, SystemArg1, SystemArg2)
    PVOID NormalContext,
    PVOID SystemArg1,
    PVOID SystemArg2
);
```

Target thread must be alertable to process.

### NtQueueApcThreadEx (Win10 RS5+)

Adds optional "UserApcReserveHandle" parameter. Using `QUEUE_USER_APC_SPECIAL_USER_APC` as the flag (the 0x1 special marker in the handle slot) creates a **Special User APC** — delivers on **user-mode transition**, not requiring alertable state.

### NtQueueApcThreadEx2 (Win11)

Adds API support for further parameter control. Cleaner replacement for the old `Ex` variant's handle-as-flag hack.

### APC injection technique

Classic APC injection:
1. Target thread exists and periodically sleeps alertable (rare in practice)
2. Allocate remote shellcode
3. `NtQueueApcThread(target_thread, shellcode_addr, NULL, NULL, NULL)`
4. Wait for thread to enter alertable state → APC fires → shellcode runs

Modern variant with Special User APC:
1. Target thread exists (any thread)
2. Allocate remote shellcode
3. `NtQueueApcThreadEx(target_thread, (HANDLE)0x1, shellcode_addr, ...)` — Special APC
4. Fires on next user-mode transition (any syscall return by the thread)

"Early Bird" APC injection:
1. `NtCreateUserProcess(target_binary, CREATE_SUSPENDED)` — child starts suspended
2. Shellcode written via `NtWriteVirtualMemory`
3. `NtQueueApcThread(child_main_thread, shellcode)`
4. `NtResumeThread(child_main_thread)`
5. Thread resumes → first alertable point is inside `LdrInitializeThunk` → shellcode fires before main program begins

Early Bird is distinctive because it beats AV-based load-time scanning: shellcode runs in what looks like a legitimate process before the real entry point runs.

### ETW-TI on APCs

`EtwTiLogQueueApcThread` fires for every cross-process `NtQueueApcThread*`. High-signal. Queuing APCs to your own threads does not fire (same-process).

---

## APC detection and evasion

### Detection indicators

- `NtQueueApcThread*` where source process != target process → ETW-TI
- Thread resumes from alertable wait with APC that points to unbacked memory → high signal
- LdrInitializeThunk path executes APC pointing to non-loader memory → very high signal (Early Bird)

### Evasion considerations

- Self-APC (same process) avoids cross-process ETW-TI — of limited offensive utility but useful for internal control flow manipulation
- Point APC at legitimate module code, jump to shellcode via register/gadget dance — reduces "APC to unbacked memory" signal
- Special User APCs on ProtectedProcess targets — fails due to ACL

### The `NtTestAlert` shortcut

```c
NtTestAlert();
```

Drains the current thread's APC queue immediately. If you queued an APC to your own thread, `NtTestAlert` forces it to run. Used in self-APC techniques to avoid waiting for natural alertable transitions.

---

## Thread stack and guard pages

Each thread has a dedicated stack. Layout:

```
High addresses (TEB.StackBase)
┌─────────────────┐
│ StackBase ───────┼─ end of stack (stack grows down)
│                 │
│ Committed pages │
│                 │
│ StackLimit ──────┼─ current low point
│                 │
│ Guard page      │ one page with PAGE_GUARD | PAGE_READWRITE
│                 │
│ Reserved pages  │ unfilled stack reservation
│                 │
│ Stack limit     │ lower end of reservation
└─────────────────┘
Low addresses
```

Growth mechanic: if thread touches the guard page, kernel catches `STATUS_GUARD_PAGE_VIOLATION`, commits a new page below, clears the guard, sets a new guard one page down, resumes thread. Transparent to user code if `__chkstk` is used.

### Stack bound overflow

If thread allocates more than the reserved stack, access hits an uncommitted, unreserved page → `STATUS_STACK_OVERFLOW`. Thread's own SEH usually cannot catch it (no stack left to run handler). Crash.

---

## PPID spoofing via PS_ATTRIBUTE_PARENT_PROCESS

During process creation (`NtCreateUserProcess`), attach an attribute identifying a **different** parent process:

```c
PS_ATTRIBUTE attrs[1];
attrs[0].Attribute = PS_ATTRIBUTE_PARENT_PROCESS;
attrs[0].Size      = sizeof(HANDLE);
attrs[0].ValuePtr  = (PVOID)hExplorerProcess;
```

Kernel treats explorer.exe as the parent, so the new process inherits its SID / security context in the sense of "who launched me" telemetry (Event ID 4688 shows the attribute-supplied parent).

Requires `PROCESS_CREATE_PROCESS` access on the target "parent". With explorer.exe (running as the user), a medium-integrity caller may not have rights. With a higher-privileged parent, you need that privilege.

**Ground truth**: the kernel still tracks the **real** parent in `EPROCESS.InheritedFromUniqueProcessId`. Tools reading EPROCESS directly (ProcessHacker/SystemInformer) see the real lineage.

---

## Thread access rights

| Right | Value | Enables |
|---|---|---|
| THREAD_TERMINATE | 0x0001 | TerminateThread |
| THREAD_SUSPEND_RESUME | 0x0002 | Suspend/Resume |
| THREAD_GET_CONTEXT | 0x0008 | GetContext |
| THREAD_SET_CONTEXT | 0x0010 | SetContext |
| THREAD_QUERY_INFORMATION | 0x0040 | QueryInformationThread |
| THREAD_SET_INFORMATION | 0x0020 | SetInformationThread |
| THREAD_SET_THREAD_TOKEN | 0x0080 | Impersonation |
| THREAD_IMPERSONATE | 0x0100 | Impersonate |
| THREAD_DIRECT_IMPERSONATION | 0x0200 | DirectImpersonation |
| THREAD_ALL_ACCESS | 0x1FFFFF | Everything |

Use lower bitmask when possible — opening LSASS threads with `THREAD_ALL_ACCESS` is high signal; `THREAD_QUERY_INFORMATION` alone often suffices for enumeration.

---

## Process object rights (relevant for thread ops on remote processes)

| Right | Value | Enables |
|---|---|---|
| PROCESS_CREATE_THREAD | 0x0002 | NtCreateThreadEx in this process |
| PROCESS_VM_OPERATION | 0x0008 | Alloc, Free, Protect |
| PROCESS_VM_READ | 0x0010 | Read memory |
| PROCESS_VM_WRITE | 0x0020 | Write memory |
| PROCESS_QUERY_INFORMATION | 0x0400 | Query info, open token |
| PROCESS_QUERY_LIMITED_INFORMATION | 0x1000 | Limited query (enough for most things) |
| PROCESS_SUSPEND_RESUME | 0x0800 | NtSuspendProcess / NtResumeProcess |
| PROCESS_ALL_ACCESS | 0x1FFFFF | Everything |

Calling `OpenProcess(PROCESS_ALL_ACCESS, ...)` is a red flag. Request the minimum needed.

---

## Fiber API

Fibers are **user-mode cooperative threads** — one OS thread can host multiple fibers, switching between them via `SwitchToFiber`. Fibers share the OS thread's TEB but each has its own stack.

### Fiber primitives

- `ConvertThreadToFiber` / `ConvertThreadToFiberEx` — makes current thread capable of hosting fibers
- `CreateFiber` / `CreateFiberEx` — allocates a new fiber (stack + context)
- `SwitchToFiber(fiber_ptr)` — yield current fiber, resume target
- `DeleteFiber`
- `GetFiberData` / `GetCurrentFiber` — access fiber-local data

### Fiber-based shellcode execution

Pattern: convert thread to fiber, allocate fiber whose start function is the shellcode entry, switch to it. When shellcode `return`s, control transfers to a designated cleanup fiber.

Advantage: fiber-based runners can make the shellcode appear as normal function calls from within legitimate code, using a small ROP-like sequence to restore real thread state after shellcode returns.

Telemetry: `CreateFiber` does not trigger ETW-TI. Fiber state changes happen entirely in user mode. Call stack during shellcode execution looks normal: attacker code → shellcode (one frame).

### Fiber + indirect syscall

Combining fiber-based execution with indirect syscall dispatch is a clean evasion pattern: legitimate-looking stack, no kernel-observable thread manipulation, syscall frames show ntdll.

---

## Thread Name (Windows 10 1607+)

Threads have a name attribute set via `SetThreadDescription` / `NtSetInformationThread(ThreadNameInformation)`. Previously, threads "named" via MSVC debugger exception `0x406D1388` — still supported for compatibility, but the proper API writes to a string field in ETHREAD.

Offensive angle: change thread name to match a legitimate pattern (`"Worker Thread"` etc.) to blend with other threads. Low signal by itself, but reduces uniqueness in EDR heuristics.

---

## Thread pool

Windows Thread Pool API (`SubmitThreadpoolWork`, `CreateThreadpoolIo`, `TpCallbackIndependent`) manages a process-wide pool of worker threads. Every process has one by default (created via `TpInitializeCallbacks` in ntdll init).

Injection via thread pool: queue a work item whose callback is the shellcode. Work items run on thread pool threads, which are legitimate threads with clean stacks. No `NtCreateThreadEx` call. Telemetry reduced.

```c
// Pseudocode
PTP_WORK work = CreateThreadpoolWork(shellcode_callback, NULL, NULL);
SubmitThreadpoolWork(work);
```

Cross-process: you need to queue a work item into a remote thread pool. Its descriptor structures live at known offsets inside the remote process. Documented in [MDSec - The Dark Side of ThreadPool](https://www.mdsec.co.uk) research.

---

## I/O Completion and APC-like callbacks

Overlapped I/O completion via `ReadFile` / `WriteFile` with a completion routine calls back into user-mode via the Special APC mechanism. Same underlying channel.

Can be used for covert execution: register a completion routine with `ReadFileEx`, the routine is queued as an APC when I/O completes. Less suspicious than a direct `QueueUserAPC` because I/O activity normalizes the pattern.

---

## Summary: thread and APC invariants

- Threads start at `LdrInitializeThunk` unless `SKIP_LOADER_INIT` is set
- Alertable wait is required for normal user APCs; Special APCs bypass it
- Cross-process APC, VM write, context modification, suspend/resume all fire ETW-TI
- `NtGetContextThread` / `NtSetContextThread` on a non-suspended thread may fail or return stale state
- Thread stack guard page expands automatically; bypassing guard page raises stack overflow
- Fiber and thread pool give shellcode-friendly execution contexts without direct thread creation
