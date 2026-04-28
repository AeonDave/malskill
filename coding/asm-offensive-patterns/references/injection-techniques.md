# Code Injection Techniques

Detailed patterns for process injection and shellcode execution without standard thread creation APIs.

---

## Fiber-Based Shellcode Runner

```
ConvertThreadToFiber(NULL)          -> hMainFiber
CreateFiber(0, shellcode_fn, NULL)  -> hPayloadFiber
SwitchToFiber(hPayloadFiber)        -> jumps directly to shellcode
```

No `CreateThread` / `CreateRemoteThread` — avoids thread-creation monitoring hooks.

## Threadless Callback Injection

Overwrite a function pointer in the target process (e.g. `NtWaitForSingleObject` trampoline) so the next natural call executes shellcode. No thread creation, no APC, no `SetThreadContext`.

```
1. Find a rarely-called function pointer in the target (e.g. callback in TLS, vectored handler list)
2. VirtualAllocEx + WriteProcessMemory (write shellcode to target)
3. Overwrite function pointer → shellcode address
4. Target process calls the function normally → shellcode runs
5. Shellcode restores original pointer, chains to next stage
```

## Module Stomping / DLL Hollowing

Load a legitimate signed DLL, overwrite its `.text` with shellcode:
```
1. LoadLibraryEx("amsi.dll", DONT_RESOLVE_DLL_REFERENCES)
2. VirtualProtect(entrypoint, RW) → memcpy(shellcode) → VirtualProtect(RX)
3. CreateThread(entrypoint) → thread starts at "legitimate" DLL address
```
Benefits: backed memory, signed module origin, no unbacked RWX regions.

## Phantom DLL Hollowing (TxF)

Use NTFS Transacted File operations to create a section from a modified-in-transaction DLL:
```
1. CreateFileTransacted("legitimate.dll")
2. WriteFile(shellcode into .text section)   ← file modified only in transaction
3. NtCreateSection(SEC_IMAGE) from transacted handle
4. NtRollbackTransaction()                   ← disk file unchanged
5. NtMapViewOfSection() → view contains shellcode but backing file is clean
```
File-backed mapping points to the original signed DLL. Signature checks pass.

## APC Early-Bird Injection

```
CreateProcess(... CREATE_SUSPENDED)
VirtualAllocEx + WriteProcessMemory  (write shellcode)
QueueUserAPC(shellcode_ptr, main_thread, 0)
ResumeThread   -> APC dispatched before any user code runs (pre-TLS)
```

## Waiting Thread Hijack

Overwrite saved RIP of a sleeping thread (in `Sleep`/`WaitFor*` frame).
Thread resumes → executes shellcode. No `SetThreadContext` needed.
