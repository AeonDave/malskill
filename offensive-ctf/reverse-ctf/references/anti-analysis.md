# CTF Reverse - Anti-Analysis

Detection surfaces and bypasses: anti-debug, anti-VM, anti-DBI, code integrity, anti-disassembly, and signal/handler runtime tricks. Identify *all* checks before patching any — challenges stack them.

## Table of Contents
- [Linux Anti-Debug](#linux-anti-debug)
- [Windows Anti-Debug](#windows-anti-debug)
- [Anti-VM / Anti-Sandbox](#anti-vm--anti-sandbox)
- [Anti-DBI](#anti-dbi)
- [Code Integrity / Self-Hashing](#code-integrity--self-hashing)
- [Anti-Disassembly](#anti-disassembly)
- [Bypass Playbook](#bypass-playbook)
- [Signal and Handler Runtime Tricks](#signal-and-handler-runtime-tricks)

## Linux Anti-Debug

- **ptrace self-attach** — `ptrace(PTRACE_TRACEME)` returns -1 if already traced. Bypass: `LD_PRELOAD` a fake `ptrace`, patch to `xor eax,eax; ret`, GDB `catch syscall ptrace` + `set $rax=0`, or `echo 0 > /proc/sys/kernel/yama/ptrace_scope`.
- **Double-ptrace watchdog** — a forked child `PTRACE_ATTACH`es the parent to block other debuggers. Kill the watchdog child, then attach.
- **/proc checks** — `/proc/self/status` TracerPid, `/proc/self/maps` (debugger/Frida libs), `/proc/self/exe`. Bypass: hook `fopen`/`fread`, mount-namespace isolation, or GDB break on `fopen` and rewrite the filename to `/dev/null`.
- **Timing** — `rdtsc`, `clock_gettime`, `gettimeofday` deltas. Bypass: NOP the `rdtsc`, Frida/`faketime` time hook, Pin.
- **Signals** — SIGTRAP handler (INT3 caught by debugger ⇒ detected), SIGALRM timeout, SIGSEGV doing real work. Bypass: `handle SIGTRAP nostop pass`, `handle SIGALRM ignore`.
- **Direct syscalls** — bypass `LD_PRELOAD` hooks; must patch the binary or intercept at syscall level (`catch syscall <n>`).

## Windows Anti-Debug

- **PEB** — `BeingDebugged` (offset 0x2), `NtGlobalFlag` (0xBC on x64; `0x70` mask set under debugger). Bypass: ScyllaHide auto-patches; or zero the fields.
- **NtQueryInformationProcess** — `ProcessDebugPort` (7), `ProcessDebugObjectHandle` (0x1E), `ProcessDebugFlags` (0x1F, inverse). Bypass: hook ntdll / ScyllaHide.
- **Heap flags** — process-heap `Flags`/`ForceFlags` differ under a debugger.
- **TLS callbacks** — run *before* the entry point (PE TLS directory → AddressOfCallBacks); commonly call `IsDebuggerPresent`+`ExitProcess`. Bypass: x64dbg Options → Events → break on TLS, patch.
- **Hardware breakpoint scan** — `GetThreadContext` reads Dr0-Dr3. Bypass: use software breakpoints or hook `GetThreadContext` to zero DR.
- **INT3 / CRC scan** — code self-hashing detects `0xCC` and patches. Bypass: hardware breakpoints, patch the comparison, or emulate.
- **Exception-based** — `UnhandledExceptionFilter`/`INT 2D`/`INT 3` behave differently under a debugger.
- **NtSetInformationThread(ThreadHideFromDebugger=0x11)** — hides the thread from debug events. Bypass: hook the call to ignore class 0x11.

## Anti-VM / Anti-Sandbox

- **CPUID** — ECX bit 31 (hypervisor present); brand string at leaf `0x40000000` (`VMwareVMware`, `KVMKVMKVM`, `XenVMMXenVMM`, `Microsoft Hv`). Patch CPUID result or run bare metal.
- **MAC prefixes** — VMware `00:0C:29`/`00:50:56`, VirtualBox `08:00:27`, Hyper-V `00:15:5D`, QEMU `52:54:00`.
- **Timing** — privileged instructions (forced VM exits) are measurably slower under virtualization.
- **Artifacts** — `vm*.sys`/`vbox*` files, `HKLM\…\VMware Tools`, `vmtoolsd.exe`/`VBoxService`, Linux `/sys/class/dmi/id/product_name`.
- **Resources** — CPU count / RAM / disk thresholds. Bypass: configure the VM with 4+ CPUs, 8GB+ RAM, 100GB+ disk.

## Anti-DBI

- **Frida** — `/proc/self/maps` for `frida`/`gadget`, default port 27042, inline-hook prologue checks (`0xE9`/`0xFF`), thread names (`gmain`/`gdbus`), Windows `\\.\pipe\frida-*`. Bypass: hook `strstr` to hide the needle, or early-load the gadget before the anti-DBI runs.
- **Pin / DynamoRIO** — maps entries (`pin-`, `dynamorio`, `drcov`) and instruction-count timing overhead.

## Code Integrity / Self-Hashing

CRC32/SHA over `.text` or function bodies aborts on any modification (breakpoints, patches); a watchdog thread may zero the flag in a loop. Bypass: hardware breakpoints (no code modification), patch the comparison, hook the hash function, emulate (Unicorn/Qiling), or kill the watchdog thread.

## Anti-Disassembly

- **Opaque predicates** — always/never-taken branches; Z3/SMT proves the direction.
- **Junk bytes / overlapping / jump-in-the-middle** — switch to graph-mode disassembly; undefine and re-analyze from the correct offset.
- **Function chunking** — non-contiguous chunks joined by jumps defeat linear boundary detection; append tails / create functions per chunk.
- **Control-flow flattening (OLLVM)** — trace the state variable; the flattened CFG collapses once transitions are known. Variants add bogus flow, instruction substitution, runtime string decryption.
- **Mixed Boolean-Arithmetic (MBA)** — simplify with known identities (`(x&y)+(x|y)==x+y`, `(x|y)&~(x&y)==x^y`) or tools (D-810, GOOMBA, SiMBA/Arybo).

## Bypass Playbook

1. Enumerate every check first: grep for `ptrace`, `IsDebuggerPresent`, `rdtsc`, `cpuid`, `NtQuery`, `GetTickCount`, `/proc/self`, `SIGTRAP`, `alarm`.
2. Static-patch / NOP checks (pwntools, Ghidra) before running.
3. `LD_PRELOAD` (Linux) or ScyllaHide (Windows) to hook returns.
4. If too many to patch, run under **emulation** (Unicorn/Qiling) — no debugger artifacts at all.

| Check | Platform | Bypass |
|-|-|-|
| `ptrace(TRACEME)` | Linux | `LD_PRELOAD`, patch `ret 0`, `catch syscall` |
| `IsDebuggerPresent` / PEB | Windows | ScyllaHide, Frida hook, PEB patch |
| `NtQueryInformationProcess` | Windows | ScyllaHide, hook ntdll |
| `rdtsc` timing | Both | NOP rdtsc, Frida time hook, Pin |
| `/proc/self/status` | Linux | mount namespace, hook `fopen` |
| `alarm(N)` / SIGTRAP | Linux | `handle SIGALRM ignore` / `handle SIGTRAP nostop pass` |
| TLS callback | Windows | break on TLS in x64dbg, patch |
| DR-register scan | Windows | software BPs, hook `GetThreadContext` |
| INT3 scan / CRC | Both | hardware BPs, patch comparison, emulate |
| Frida detection | Both | early-load gadget, hook `strstr` |
| CPUID hypervisor | Both | patch CPUID result, bare metal |
| Thread hiding | Windows | hook `NtSetInformationThread` |

## Signal and Handler Runtime Tricks

Signal handlers hide control flow decompilers cannot model. If a binary installs SIGILL/SIGSEGV/SIGTRAP/SIGFPE handlers early, suspect custom dispatch or code mutation.

- **SIGFPE/SIGILL handler mutates `.text`** — handler `mprotect`s the page R/W/X and rewrites code, or switches x86↔x86-64 mode. Set `handle <sig> nostop pass` and break on the handler body.
- **Trap-Flag self-check** — `pushf; pop reg; and reg,0x100` reads the single-step flag and gates a `cmovz`; single-stepping leaves TF set and silently runs the wrong path. Use **hardware** breakpoints so the instruction runs in normal mode.
- **Parent-patched child** — the parent rewrites child code via `process_vm_writev`; tracing the parent recovers the real bytes: `strace -f -e trace=process_vm_writev -e write=all`.
- **Signal side-channel as oracle** — count signals per candidate (`strace -e signal=SIGFPE | grep -c`); correct characters produce more signals. Likewise hook `signal()`/`sigaction()` via `LD_PRELOAD` — installing the next handler confirms the current character.
- **ConfuserEx / .NET protectors** — they secure the on-disk image, not the post-constructor module. Break on `<Module>.cctor` in dnSpy, let it materialize, Save Module, clean with `de4dot`.
