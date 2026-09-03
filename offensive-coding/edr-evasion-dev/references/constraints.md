# Verified Constraints — EDR Evasion

Hard constraints discovered through testing. Each entry caused a crash, detection, or silent failure before being identified.

## Syscall Dispatch

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| `masked_syscall` (RSP manipulation) in TP worker thread | RSP corruption → crash or undefined behavior | TP workers have non-standard stack layout; RSP tricks that work on main thread fail |
| `spoofed_syscall` (NtContinue) in console-attached process | Crash (exception dispatch conflict) | Console subsystem has its own exception handling that conflicts with NtContinue context replay |
| `spoofed_syscall` in any non-main thread | Crash | Synthetic stack frame references main thread's `BaseThreadInitThunk` frame; TP workers have different unwind chains |
| SilentMoonwalk `.pdata` spoof on CET-enforced ntdll (Windows 11 24H2+) | `#CP` control-protection fault at terminal `RET`; kernel unwinder shadow-stack mismatch even when no CPU fault | Query `GetProcessMitigationPolicy(ProcessUserShadowStackPolicy)`. If enforced, disable SMW and use `NtContinue` spoof (kernel writes both stacks coherently). Detail: `kernel-telemetry.md` → CET |
| Identical synthetic call-stack repeated across many syscalls | CrowdStrike Falcon 8.5+ (2025) ML flags "call-stack pattern rigidity" | Vary gadget selection across the ntdll gadget pool per SMW build; or skip SMW in tool_mode (backed EXE) where real ntdll stacks are legitimate |

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
| AMSI provider re-registration (register malicious CLSID under `\CurrentControlSet\Services\WinDefend\AMSI`) | 2025 Defender + S1 monitor AMSI provider CLSID changes | Do not use in production; deterministic 2025 detection. Prefer no-AMSI-touch in tool_mode |
| Usermode ETW patch on `ntdll!EtwEventWrite` for kernel ETW-TI events | No effect | ETW-TI provider fires from **kernel** context. See `kernel-telemetry.md` → Windows Kernel-Fired Signals |

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
| Fixed-interval `NtDelayExecution` + identical spoofed stack + zero business activity during sleep + syscall burst on wake | Elastic Defend 9.0+ "Hunt-Sleeping-Beacons" rule fires after 3–5 iterations | Jitter delay (min-max range), vary SMW gadget selection per cycle, or interleave benign file/registry reads to break the "idle then burst" pattern. Tool_mode avoids entirely (one-shot) |
| VEH registration for W^X write interception | `RtlAddVectoredExceptionHandler` is hooked by S1/Defender; registration itself logged | Skill §0 minimalism gate: prefer private RWX + XOR re-encrypt over dual-view W^X on hardened targets |

## Indirect / Callback-based Execution

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| `spoofed_syscall` or `masked_syscall` inside `timeSetEvent`/threadpool callback | Crash | Callback fires on TP worker thread — same constraints as TP worker syscall dispatch; use `indirect_syscall` only |
| `EnumWindows(shellcode, 0)` with shellcode using `spoofed_syscall` | Crash | Caller thread stack layout not guaranteed; synthetic frames corrupt |
| `QueueUserAPC(shellcode)` targeting CLR thread + module-stomped DLL | DllMain re-entry crash | CLR APC delivery may re-trigger DLL load notification on stomped module |
| Callback-based execution in beacon loop (repeated timer fires) | High EDR suspicion | Multiple callbacks from winmm.dll to private/RWX memory → behavioral pattern; use once for initial exec, not for looping |

## Disproven Assumptions — Do Not Reintroduce

Assumptions falsified by S1/CS/Defender testing (each cost measurable time or produced a detection regression). Read this before adding an evasion feature "just in case".

| Assumption | Reality | Fix |
|------------|---------|-----|
| Selective ETW suppression will satisfy S1 (CLR-aware) | S1 correlates `CLR loaded` + `CLR ETW absent` = bypass, regardless of who suppressed it | Disable DR0 entirely instead of trying to filter CLR-only |
| More HWBP coverage = better evasion (expand 4→11 targets) | Every active DR is a "breakpoint without debugger" signal; re-issued indirect_syscall adds "direct syscall from patched library" | Remove ALL HWBP from tool_mode |
| Indirect syscall > direct ntdll stubs (for backed EXE) | S1 validates syscall RIP against ntdll stub entries; gadget dispatch fires "direct syscall from patched library". Real hooked stubs generate **zero** syscall indicators on a backed EXE | PEB-resolved direct `Nt*` calls for backed EXE; save indirect_syscall for unbacked contexts |
| Gating call sites (with `if false {}`) removes bytes | At `opt-level=0`, all function bodies compile regardless of reachability; dead code retains `0F 05` (syscall) and `mov eax,ecx; jmp r11` gadget bytes | `#[cfg]`-gate the *definitions*, not the call sites; verify with `objdump` |
| VEH registration is invisible if handler is a no-op | S1 signatures on the `AddVectoredExceptionHandler` **call pattern** in `.text`, not the handler body | `#[cfg]`-gate the entire VEH registration block for tool_mode |
| SilentMoonwalk helps a backed EXE | Backed `.text` is already a legitimate return address; SMW adds indirect_syscall + VEH + HWBP = 3 indicators for zero gain | Skip SMW in tool_mode; keep it only for beacon (unbacked) |
| More evasion features = better evasion | A 1,472-line minimal beacon (no VEH/HWBP/unhooking) evades fully; a 6,126-line "everything on" build is detected. Each added feature added 1–3 real indicators | §0 minimalism: start minimal, add only after confirming a real signal it must suppress |
| A more OS-correct reflective entrypoint fixes Rust shellcode | Switching a Rust cdylib loader from exported-`DllMain` first to `AddressOfEntryPoint`/`_DllMainCRTStartup` first can regress: the exported path may reach beacon+HTTP resolve while entrypoint-first stops server contact | Preserve the loader/payload lifecycle that already reaches the beacon; add breadcrumbs around the failing runtime primitive instead of rewriting loader entry order |

### Confirmed indicator reductions

| Change | Reduction real? | Notes |
|--------|-----------------|-------|
| Private RWX (drop mapped-section W^X in tool_mode) | Yes | Section kernel signal eliminated |
| Disable ETW DR0 entirely | Yes | ~8→~4 indicators, "ETW bypassed" eliminated |
| Eliminate syscall/VEH/HWBP call sites for tool_mode | Yes | ~4→~1, three indicators gone |
| Selective ETW (CLR-only DR0) | No | S1 still detects the CLR gap |
| Expand HWBP targets 4→11 | No | More DRs = more signals |
| Gate call sites only (dead functions retained) | No | Dead code keeps signature bytes |
| Entrypoint-first Rust reflective load | No | Regressed live shellcode contact |

**Irreducible remainder**: "Malicious shellcode execution" (private RWX + PEB walk + dynamic API resolution). Everything else is negotiable; this is the floor.

## CrowdStrike-Specific Regressions

Distinct from S1 findings. Never combine these three patterns with any usermode-evasion implant.

| Pattern | Detection signature | Delta on VT |
|---------|--------------------|-------------|
| **PE header stomp** (`map → execute → zero first 0x1000`) | CS shellcode-loader signature (missing PE header on RWX region) | 60%→90% |
| **AMSI propagation inside `NtCreateThreadEx` hook** (PEB walk + resolve `AmsiScanBuffer` + `SetThreadContext` inside the hook body) | CS SharpBlock signature | 60%→90% |
| **Removing `panic_abort`** from a Rust build | Reintroduces Rust unwinding strings (`attempt to divide by zero`, `library/core/src/…`) | Static string signature |

**Rule**: always use `build-std = ["std", "panic_abort"]` + `panic = "immediate-abort"`. Do PEB walks and AMSI resolution on the TP worker thread, never inside a hook body. Never zero the PE header in-place; if header removal is needed, do it in a fresh copy in unmodified memory.

## Linux Sensor Coverage Constraints

Load `linux-edr-evasion.md` for the full model. Selected traps that map to Windows-analog mistakes:

| Constraint | Failure mode | Context |
|------------|-------------|---------|
| Assuming io_uring bypasses all monitoring | Falco ≥ 0.40, Tetragon LSM mode, Elastic Defend 8.13+ hook `io_uring_enter` or `security_file_open` | Verify sensor version; LSM BPF (`bpftool prog list \| grep lsm`) neutralizes io_uring evasion entirely |
| `memfd_create("beacon", ...)` with memorable name | Elastic Defend 9.4.0+ correlates memfd name in sequence rules; `memfd:beacon` in `/proc/<pid>/maps` | Empty name (`""`) minimizes signal; still fires for the Elastic sequence detection |
| Same-pid `write` + `fexecve` on memfd | "Fileless execution sequence" rule fires deterministically | Parent writes memfd, `posix_spawn` execs from a child — breaks same-pid correlation |
| Dynamic-linked payload for LD_PRELOAD-hooked host | libc-wrapper rootkits (Symbiote-family) hook every open/read/execve | Compile static (musl) — defeats LD_PRELOAD-based tracing at build time |
| BPF map poisoning without `security_bpf_map` LSM check | On LSM-enforced hosts, `bpf(BPF_MAP_UPDATE_ELEM)` returns `-EPERM` and the failure itself is logged | Check `bpftool prog list \| grep lsm` before attempting; fall back to non-map-based approach |
| Kernel module drop with `MODULE_SIG_FORCE=y` + `lockdown=integrity` | `finit_module` fails with `-EKEYREJECTED`; failure logged by auditd | Verify `cat /sys/kernel/security/lockdown` and `zgrep MODULE_SIG_FORCE /boot/config-$(uname -r)` before LKM path |
| ptrace-based injection with `kernel.yama.ptrace_scope >= 2` | `PTRACE_ATTACH` fails without CAP_SYS_PTRACE | Use `/proc/<pid>/mem` write or `process_vm_writev` if same-UID; otherwise pivot |
