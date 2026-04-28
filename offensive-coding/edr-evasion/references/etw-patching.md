# ETW Byte-Patching via NtWriteVirtualMemory

Use this pattern only when the loader already has indirect syscalls. `VirtualProtect(RX→RW) → write → restore` on `ntdll .text` is a deterministic usermode-hook signal; `NtWriteVirtualMemory` on self is a different path.

## Why it avoids the earlier detection path

`NtWriteVirtualMemory(-1, self, target_rx_page, patch)` routes the copy through the kernel's `MmCopyVirtualMemory`. On image-backed RX pages, the kernel performs the copy-on-write transition internally, so usermode never calls `VirtualProtect` and never exposes the classic `RX→RW→RX` sequence on `ntdll .text`.

## Required properties

| Property | Why it matters |
|---|---|
| Indirect syscall for `NtWriteVirtualMemory` | Avoids usermode hook telemetry on the write path |
| Self-target (`HANDLE = -1`) | Keeps the write local; kernel handles COW silently |
| Patch both `NtTraceEvent` and `EtwEventWrite` | Covers native and Win32 ETW emission sites |
| Immediate restore | `ntdll .text` must be clean before the next integrity sweep |

## Patch payload

Use `33 C0 C3` (`xor eax,eax; ret`), not bare `C3`.

- `xor eax,eax` guarantees `STATUS_SUCCESS`
- bare `ret` leaves prior `rax` value observable by the caller
- 3 bytes are still short enough for a sub-millisecond patch/restore window

## Timeline

1. Save original first 3 bytes from `NtTraceEvent` and `EtwEventWrite`
2. `Ep()`: indirect `NtWriteVirtualMemory` on self writes `33 C0 C3`
3. Run loader-only activity: decrypt, allocation, stomp/setup
4. `Er()`: indirect `NtWriteVirtualMemory` restores original bytes
5. Only after restore, call `execute_shellcode` / hand off to long-running beacon

Critical rule: do not leave the patch active across the beacon lifetime. The safe window is the short loader phase only.

## Failure cases

| Wrong pattern | Result |
|---|---|
| `VirtualProtect` before/after patch | Usermode hook sees permission change on `ntdll .text` |
| Patch left active after handoff | Integrity sweep catches modified bytes |
| Patch after noisy loader syscalls | ETW stays alive during the interesting part |
| Bare `ret` (`C3`) | Caller may see garbage status in `rax` |

## Implementation note

If the codebase already exposes `HASH_NTWRITEVIRTUALMEMORY`, `HASH_NTTRACEEVENT`, and an indirect `nt_write_virtual_memory()` wrapper, the missing pieces are just: resolve `EtwEventWrite`, save 3 original bytes for both targets, patch, restore, and ensure restore runs before the non-returning handoff.