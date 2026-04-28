# Verified Constraints — EDR Evasion

Hard constraints discovered through testing. Each entry caused a crash, detection, or silent failure before being identified.

## Syscall Dispatch

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| `masked_syscall` (RSP manipulation) in TP worker thread | RSP corruption → crash or undefined behavior | TP workers have non-standard stack layout; RSP tricks that work on main thread fail |
| `spoofed_syscall` (NtContinue) in console-attached process | Crash (exception dispatch conflict) | Console subsystem has its own exception handling that conflicts with NtContinue context replay |
| `spoofed_syscall` in any non-main thread | Crash | Synthetic stack frame references main thread's `BaseThreadInitThunk` frame; TP workers have different unwind chains |

## Memory Allocation

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| Module stomp + DLL_THREAD_ATTACH + CLR threads | Crash on thread creation | CLR spawns threads → each triggers DllMain on stomped DLL → crash because DLL code is overwritten |
| NtMapViewOfSection(RX) when section max_prot is only RW | `STATUS_SECTION_PROTECTION (0xC000004E)` | Section max_prot must be superset of all view protections |
| PAGE_EXECUTE_WRITECOPY after COW | VAD shows `MEM_PRIVATE + PAGE_EXECUTE_READWRITE` | Kernel promotes XWC to RWX after copy-on-write fault — no evasion benefit |
| RX-only allocation for self-modifying PIC | SEH stack overflow in TP worker | AV fires on first write → SEH chain walks entire stack → overflow because TP worker stack is small |
| PE header stomp on beacon payload | BOF/execute-assembly crash | CS beacon queries its own PE headers at runtime for BOF dispatch |

## ETW/AMSI

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| ETW patch via `VirtualProtect(RX→RW) → write → RX` on `ntdll .text` | Deterministic usermode-hook alert before payload runs | `VirtualProtect` on ETW exports is the noisy pattern; use indirect `NtWriteVirtualMemory` on self instead |
| ETW byte-patch left active past loader handoff | `ntdll .text` integrity sweep catches modified bytes | Restore original bytes before `execute_shellcode` / long-lived beacon transfer |
| Bare `C3` ETW patch | Caller may observe non-zero garbage in `rax` | Use `33 C0 C3` (`xor eax,eax; ret`) for stable `STATUS_SUCCESS` |
| HWBP VEH + Donut/Fritter `-g 1` (guard page VEH) | One handler shadows the other | Both register first-chance VEH; only one fires. Use `-g 0` |
| Fritter `-g 0` required, not `-g 1` | Guard page AV conflicts with HWBP single-step | Same VEH priority collision |

## Console / Tool Mode

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| AllocConsole when console already inherited | S1 detection signal + double console | Console-subsystem processes already have a console; check `GetConsoleWindow()` first |
| FreeConsole + AttachConsole with .NET tools | `Console.Out` broken (CLR caches handles) | CLR captures console handles at startup; detach/reattach invalidates them |

## PIC Generators

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| Fritter `-g 0` self-modifies at runtime | AV if RX-only; must provide writable memory | Patches import stubs and resolves pointers in-place during PIC initialization |
| CLR hosting via COM + Costura.Fody packed assemblies | `TypeInitializationException` in `<Module>.cctor` | Costura's module initializer can't locate embedded assemblies when loaded via CLR COM hosting |
| Fritter for .NET without `-r v4.0.30319` | Wrong CLR version loads (2.0 instead of 4.0) | Explicit runtime version required in Fritter command line |

## Post-Execution Cleanup

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| PE header stomp only (0x1000 bytes) | ~860KB of decrypted PIC loader body + embedded PE remains in memory | Fritter body extends well beyond first page; zero entire buffer |
| Unmap views before zeroing | Fritter signatures visible in memory dump | Zero the RW view first, then unmap both views |

## SilentMoonwalk / Inline Assembly

| Constraint | Failure mode | Context |
|------------|-------------|------|
| LLVM reserves `rbx` — cannot use `out("rbx")` | LLVM error "rbx is used internally by LLVM and cannot be used as an operand for inline asm" | Occurs when gadget is `jmp rbx`. Fix: use `inlateout("rcx")` + `inlateout("r11")` to pin synth/gadget inputs and push/pop rbx manually |
| Reading syscall result in a separate `asm!` block after a match | LLVM may reuse rax as scratch between match join and second asm block | Declare `out("rax") result` directly inside each match arm, do not use a follow-up asm |
| Pre-prolog address used as chain frame | Unwinder computes negative or wrong frame size → stack walk crash | Only use addresses past the prolog (`addr >= func_begin + prolog_size`) |
| Frame size from SUB RSP only (not PUSH_NONVOL) | Synthetic stack frames don't match `.pdata` UNWIND_INFO → WinDbg/CrowdStrike unwinder detects mismatch | Parse full UNWIND_INFO including PUSH_NONVOL (+8 each), ALLOC_SMALL, ALLOC_LARGE entries |
| Unbounded spinlock on synthetic stack buffer | TP worker blocks indefinitely if VEH fires concurrently | Use bounded spin (e.g. 4096 iters) with fallback to `indirect_syscall` |

## E10 Payload Syscall Interception

| Constraint | Failure mode | Context |
|------------|-------------|------|
| DR2 fallback with `indirect_syscall6` when target has nargs>6 | 7th argument (e.g. `Options` for NtDuplicateObject) is silently lost | Use `indirect_syscall7` when `extra_count >= 3` |
| Lock ordering: E10_LOCK before SPOOF_BUF_LOCK | Deadlock if both locks are acquired in different orders from different threads | Always: E10_LOCK first, SPOOF_BUF_LOCK second |
| Clearing DR via SetThreadContext requires CONTEXT_DEBUG_REGISTERS flag | SetThreadContext with wrong flags is a no-op | Set `context_flags = CONTEXT_DEBUG_REGISTERS` and zero DR0–DR7 |
| Kernel-level observer can see payload return address in EXCEPTION_CONTEXT | No usermode fix — CONTEXT is captured before VEH handler runs | Acceptable: EDR operates in usermode; accepted known limitation |

## ntdll Unhooking

| Constraint | Failure mode | Context |
|------------|-------------|------|
| NTSTATUS success check using `!= 0` | `STATUS_IMAGE_NOT_AT_BASE` (0x40000003) rejected as error — unhook skipped | Use `(st as i32) < 0` for NT_SUCCESS check, not `st != 0` |
| NtCreateFile on ntdll.dll path | High-confidence IoC (ETW file I/O event on ntdll) | Use `NtOpenSection("\KnownDlls\ntdll.dll")` instead — no file handle |

## PEB Walk / EAT Scan

| Constraint | Failure mode | Context |
|------------|-------------|------|
| Bounds check `names_end_rva > SizeOfImage` rejects valid EAT | All exports return null on some Windows builds (seen on S1) | On in-process mapped modules, `AddressOfNames` may legally extend beyond `SizeOfImage`. Remove the bounds guard |
| Raw pointer dereference `*(ptr as *const u32)` in EAT parsing | Panic on misaligned addresses (e.g. S1's kernel32 build) | Use `ptr::read_unaligned()` for all PE structure field reads |

## Payload Encryption

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| AES implementation code (GF math + ShiftRows + MixColumns) is fingerprinted algorithmically | VT detections increase even with no static S-box table — `0x1b` polynomial + ShiftRows permutation + 14-round structure are AES signatures | Replacing zlib+XOR with AES-CTR raised detections 4→8/71 on VirusTotal |
| AES-256 RCON off-by-one: Rust must call `aes_rcon(i/8 - 1)`, NOT `aes_rcon(i/8)` | Entire AES key schedule produces wrong round keys → wrong keystream → ILLEGAL_INSTRUCTION at RX base | Python `RCON[i//8 - 1]` is 0-indexed (RCON[0]=0x01); `aes_rcon(1)` = 0x02 ≠ 0x01 |
| E12 per-page re-encrypt (eviction) conflicts with W^X writes from Fritter | Eviction XORs per-page key over Fritter's cleartext writes → corruption → crash at Fritter decryption stub (~offset 0xD4FD0) | W^X VEH handler writes Fritter's decrypted bytes into RW view; subsequent eviction overwrites them |

## Process Injection

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| Early Bird APC + modern EDR (2025) | `QueueUserAPC` pointing to non-.text memory is flagged even in suspended processes | Use indirect syscalls for VirtualAllocEx/WriteProcessMemory/NtQueueApcThread; consider Early Cryo Bird variant |
| Thread hijacking `SetThreadContext` in alertable thread | Thread may re-enter alertable wait before shellcode completes → double-execution or crash | Redirect to non-alertable entry if possible, or use waiting-thread hijack on sleeping (non-alertable-wait) thread |
| PPID spoof without token match | EDR kernel callback compares caller PID vs PPID attribute → mismatch logged | Add token impersonation of spoofed parent before CreateProcess call |
| `CREATE_SUSPENDED` flag + immediate QueueUserAPC | Flagged by behavioral EDRs as Early Bird pattern | Use `NtSetInformationJobObject(JOBOBJECT_FREEZE_INFORMATION)` freeze variant instead |

## Anti-Analysis

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| `NtSetInformationThread(ThreadHideFromDebugger)` on CLR thread | CLR may crash — CLR relies on debug events for JIT and exception handling | Apply only to non-CLR native threads |
| Timing check with `Sleep(5000)` RDTSC delta | Some EDRs also accelerate time → false positive exit in production | Use RDTSC + GetTickCount64 cross-validation; threshold >= 3s delta |
| Anti-VM checks before token/privilege elevation | If running as SYSTEM (e.g. service), parent-process and user checks fail benignly | Guard parent/user checks with privilege level test first |

## Sleep Obfuscation

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| All threads use obfuscated_sleep | Deadlock or crash when EDR's own Sleep hook is in the chain | Only beacon thread should encrypt/decrypt; other threads must call original Sleep through trampoline |
| Protection change on image-backed section during sleep | ETW kernel callback fires | Use private or section-backed memory for sleep target, not module-stomped DLL |

## Indirect / Callback-based Execution

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| `spoofed_syscall` or `masked_syscall` inside `timeSetEvent`/threadpool callback | Crash | Callback fires on TP worker thread — same constraints as TP worker syscall dispatch; use `indirect_syscall` only |
| `EnumWindows(shellcode, 0)` with shellcode using `spoofed_syscall` | Crash | Caller thread stack layout not guaranteed; synthetic frames corrupt |
| `QueueUserAPC(shellcode)` targeting CLR thread + module-stomped DLL | DllMain re-entry crash | CLR APC delivery may re-trigger DLL load notification on stomped module |
| Callback-based execution in beacon loop (repeated timer fires) | High EDR suspicion | Multiple callbacks from winmm.dll to private/RWX memory → behavioral pattern; use once for initial exec, not for looping |
