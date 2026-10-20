# Linux syscall dispatch internals (x86-64 focus)

Load when designing low-level tool dispatcher strategies (vDSO, libc, direct syscalls), handling telemetry impacts, or reasoning about evasion surfaces.

For low-level tooling, where the `syscall` instruction executes from is operationally important. Kernel-side telemetry can attribute origin differently depending on whether dispatch comes from vDSO, libc, or your own text section.

---

## x86-64 syscall ABI invariants

Syscall numbers are stable per architecture (`arch/x86/entry/syscalls/syscall_64.tbl`). Hardcode from `<asm/unistd_64.h>` or resolve from the table at compile time. No runtime resolution needed.

Register contract:

- `rax` = syscall number
- `rdi`, `rsi`, `rdx` = args 1-3
- `r10`, `r8`, `r9` = args 4-6
- return value in `rax` (`< 0` means `-errno`)

Critical detail: `syscall` clobbers `rcx` (saves `rip`) and `r11` (saves `rflags`). This is why arg4 is passed in `r10` and not `rcx`.

### aarch64 syscall ABI

- `x8` = syscall number
- `x0`–`x5` = args 1–6
- return value in `x0`
- `svc #0` traps to EL1

---

## Dispatch source patterns

### Mode 1 — vDSO gadget dispatch (indirect)

Call into a `SYSCALL;RET` sequence (`0F 05 C3`) found in `linux-vdso.so.1`. The vDSO is a kernel-mapped ELF shared object in every process's address space, located via `AT_SYSINFO_EHDR` in the auxiliary vector.

The vDSO's `.text` contains `syscall; ret` gadgets inside its exported functions (`__vdso_clock_gettime`, `__vdso_gettimeofday`, `__vdso_getrandom` on 6.11+). Using one as an indirect dispatch target makes the `syscall` instruction execute from kernel-mapped memory, not your code section.

**Kernel version notes:**
- **6.10+**: `mseal()` seals the vDSO mapping — cannot remap/reprotect it to RWX. Gadget extraction from the existing RX mapping is unaffected; injecting custom gadgets into vDSO is blocked.
- **6.11+**: `getrandom()` added to vDSO (x86-64); 6.12 adds aarch64/ppc/s390x/loongarch. New exported function = additional gadget source bytes.

```
Extraction:
1. Read AT_SYSINFO_EHDR from /proc/self/auxv (or getauxval(AT_SYSINFO_EHDR))
2. Validate ELF magic at the returned address
3. Walk program headers, find PT_LOAD segments with PF_X
4. Scan executable bytes for 0F 05 C3 (syscall; ret)
5. Cache the first (or a random) match as the gadget
```

**Telemetry profile**: `syscall` instruction at a vDSO address. eBPF kprobes and seccomp see the same syscall number; the origin address (captured via `pt_regs->ip` or stack walk) points into `[vdso]`. This is the cleanest dispatch source — indistinguishable from a normal vDSO-accelerated time call's entry path.

### Mode 2 — libc gadget fallback (indirect)

Same `0F 05 C3` pattern, scanned from the mapped libc `.text` segment. Every libc `syscall()` wrapper contains the sequence. Parse `/proc/self/maps` to find libc's text range, scan for the gadget.

**Telemetry profile**: `syscall` at a libc address. Normal for any glibc-linked process.

### Mode 3 — direct asm syscall

Issue `syscall` from your own trampoline code (inline asm or `.s` file).

```asm
; x86-64 direct syscall trampoline
my_syscall:
    mov rax, rdi      ; syscall number
    mov rdi, rsi      ; arg1
    mov rsi, rdx      ; arg2
    mov rdx, rcx      ; arg3
    mov r10, r8       ; arg4
    mov r8, r9        ; arg5
    mov r9, [rsp+8]   ; arg6
    syscall
    ret
```

**Telemetry profile**: `syscall` at an address in your module's `.text`. This is the equivalent of Windows “direct syscall” — observable by any stack-walking monitor.

### Mode 4 — runtime raw syscall

Language-specific wrappers (Go's `runtime·syscall6`, Rust's `libc::syscall`). These often inline the `syscall` instruction in the runtime's own text segment.

**Telemetry profile**: same as direct asm — `syscall` from a non-libc, non-vDSO address.

### Mode 5 — seccomp-notify injection

Use `SECCOMP_RET_USER_NOTIF` to intercept a child process's syscall and inject code via `SECCOMP_ADDFD_FLAG_SEND` (Linux 5.14+). The parent installs a seccomp filter on the child, intercepts an `openat` call, and swaps in a malicious shared library FD. Works at any `ptrace_scope` setting. No `LD_PRELOAD`, no `ptrace`, no `process_vm_writev`.

**Constraints**: parent→child only. Requires the parent to install the filter before the child calls `exec`.

**Telemetry profile**: seccomp filter installation is visible to audit/eBPF. The injected library loads normally via the dynamic linker — its `syscall` instructions appear from libc/vDSO context.

Reference: Outflank seccomp-notify-injection (December 2025).

### Mode 6 — memfd in-memory execution

Create an anonymous memory-backed file via `memfd_create`, write ELF payload, `fexecve` or `dlopen("/proc/self/fd/N")`. No disk artifact.

**Blocked by**: `vm.memfd_noexec` sysctl (6.3+). Value `1` = default to non-executable memfd; value `2` = reject calls without `MFD_NOEXEC_SEAL`. Check `/proc/sys/vm/memfd_noexec` on target. Container runtimes increasingly set this to `2`.

---

## Robust fallback chain design

A resilient resolution strategy:

1. Parse `AT_SYSINFO_EHDR` from `/proc/self/auxv` to locate vDSO base
2. Validate ELF and scan executable segment for `0F 05 C3`
3. If unavailable, parse `/proc/self/maps` for libc text mapping and rescan
4. Final fallback: direct asm syscall path

This avoids hard failure when vDSO layout differs across kernel/distro builds.

Use `scripts/vdso_gadget_extract.py` to enumerate available gadgets on the running system (Linux only).

---

## Hooking and monitoring landscape

### Where hooks live (what “EDR” means on Linux)

| Layer | Mechanism | What it sees | Bypass path |
|---|---|---|---|
| **Userland** | `LD_PRELOAD` / libc interposition | glibc wrapper calls only | Direct syscall (modes 2–4) |
| **Userland** | `ptrace` (PTRACE_SYSCALL) | All syscalls from traced process | Detect via `/proc/self/status` TracerPid |
| **Kernel** | seccomp-BPF | Syscall number + args at entry | io_uring (avoids syscall entry entirely) |
| **Kernel** | eBPF kprobes/tracepoints | Syscall entry/exit + context | Varies; see eBPF evasion below |
| **Kernel** | LSM hooks (SELinux, AppArmor) | Object-level operations | Limited; LSM checks are in kernel paths |
| **Kernel** | Audit subsystem (`auditd`) | Syscall events per audit rules | io_uring operations not audited on older kernels |

### LD_PRELOAD bypass

`LD_PRELOAD` interposes on dynamically linked glibc wrappers (`open()`, `read()`, `write()`, etc.). Any code that issues `syscall` directly — Go binaries, static musl binaries, inline asm — bypasses the interposition entirely. This is the simplest and most common evasion path.

**Caveat**: `LD_PRELOAD` is stripped by the dynamic linker for setuid/setgid binaries (`AT_SECURE`). Monitor tools that rely on it lose coverage when the target is statically linked or uses a non-glibc runtime.

### seccomp-BPF bypass via io_uring

seccomp filters inspect syscall arguments at the `syscall` entry point. `io_uring` (Linux 5.1+) submits I/O operations via a shared-memory ring buffer; the kernel processes them without a per-operation `syscall` entry, so seccomp filters never fire.

Operations available via io_uring include: `read`, `write`, `openat`, `close`, `connect`, `accept`, `send`, `recv`, `splice`, `statx`, and many more. A process can perform most I/O without issuing a single traditional syscall after the initial `io_uring_setup`.

**Curing** (ARMO, 2025): PoC rootkit that operates entirely via io_uring, demonstrated evasion of Falco and Tetragon. **RingReaper** (2025): post-exploitation agent replacing traditional syscalls with io_uring operations. **Furtex** (2026): toolkit combining raw direct syscalls with io_uring for authorized red-team work.

**Limitation**: io_uring still requires an initial `io_uring_setup` syscall (NR 425) and `io_uring_enter` (NR 426) for submission. These entry points are monitorable. Container seccomp profiles commonly block `io_uring_setup` by default.

**io_uring LSM/audit hook timeline:**

| Kernel | Change |
|---|---|
| 5.1 | io_uring introduced — no LSM, no audit |
| 5.10 | `IORING_REGISTER_RESTRICTIONS` — limit which opcodes a ring accepts |
| 5.16 | SELinux + Smack + audit hooks for io_uring (~5% overhead) |
| 5.19 | `IORING_OP_URING_CMD` merged **without** LSM hooks (regression) |
| ~6.0 | LSM hooks added for `uring_cmd` (commits `cdc1404a`, `2a5840124009`) |
| 6.2 | Kernel docs include "Security hooks for io_uring" section |

**Audit gap persists**: no confirmed upstream per-operation audit records for io_uring. Falco, Tetragon (default config), and Microsoft Defender for Linux remain blind to io_uring operations as of mid-2025 (ARMO's Curing PoC). Google disabled io_uring on Android, ChromeOS, and production servers (2023).

### eBPF evasion surface

eBPF programs attached to syscall tracepoints or kprobes can monitor all syscall activity from kernel context. Evasion approaches:

- **eBPF rootkits**: attach eBPF programs that intercept `bpf()` itself, hiding their own map/program entries from userspace tools like `bpftool`. LinkPro (Synacktiv, 2025): kretprobes on getdents + sys_bpf, XDP for pre-stack packet processing, port-knocking activation. VoidLink (Check Point, 2026): kprobe on `__sys_recvmsg` to tamper with buffers, hides connections from `ss`/`netstat`.
- **Telemetry pipeline attack (SPiCa)**: intercept `bpf_ringbuf_submit` so events are dropped before the monitoring engine reads them — attacks the data plane, not the control plane.
- **Telemetry suppression**: eBPF programs that produce no output — the EDR generates no events. (0xB33SM0K3R, 2025.)
- **Pre-LSM argument rewriting**: eBPF programs that rewrite syscall arguments (e.g., pathnames) before LSM checks evaluate them. (LID project, 2026; targets AppArmor.)
- **Real-world eBPF malware**: BPFDoor (2025 variants) — IPv6 + DNS-port C2 (port 53), rotates through daemon names. Symbiote (2025 variants) — eBPF filter accepts IPv4+IPv6 across TCP/UDP/SCTP on rotating non-standard ports.

**BPF token (kernel 6.9)**: delegates limited eBPF privileges to unprivileged processes via bpffs. A privileged daemon creates a token; the kernel checks permissions against the token, not the caller's capabilities. Enables containers to run BPF inside user namespaces. `kernel.unprivileged_bpf_disabled` defaults to `2` (off) in recent kernels.

**Detection of eBPF rootkits**: live `bpftool prog list` cannot be trusted on a suspect host. Datadog proposes detecting at load time by flagging programs using the override-return helper. Memory forensics (Volatility with eBPF-aware plugins) or verified boot chains remain the reliable path.

---

## .eh_frame — the Linux analog of Windows .pdata

ELF `.eh_frame` (and its index `.eh_frame_hdr`) is the structural equivalent of PE `.pdata`: it contains DWARF Call Frame Information (CFI) records that describe how to unwind each function's stack frame.

### Structural comparison

| Aspect | Windows .pdata | Linux .eh_frame |
|---|---|---|
| Format | `RUNTIME_FUNCTION` array (12 bytes each) | DWARF CFI records (variable length) |
| Sorting | Sorted by `BeginAddress` (PE spec) | Sorted by PC range in `.eh_frame_hdr` |
| Lookup | Binary search on RVA | Binary search via `.eh_frame_hdr` index |
| Unwinding | `UNWIND_CODE` opcodes (`UWOP_*`) | DWARF CFI opcodes (`DW_CFA_*`) |
| Coverage | Mandatory for x64 code that touches the stack | Optional but present in all non-stripped ELF |

### Offensive relevance

`.eh_frame` is relevant for **call-stack spoofing on Linux** (the analog of SilentMoonwalk/DESYNC on Windows):

- Walk `.eh_frame_hdr` to find functions with specific prologue patterns (frame pointer setup, callee-saved register saves)
- Compute frame sizes from DWARF CFI rules
- Build synthetic stack frames that satisfy the unwinder

**State of the art (Windows only)**: BYOUD (KlezVirus, Black Hat Europe 2025) is the first CET-compliant stack spoofing framework — manipulates `.pdata`/`.xdata` unwind metadata without touching return addresses, seven manipulation techniques. LACUNA-Chain: six-layer spoofing via `.pdata` lacunae, claims to defeat ETW-Ti + kernel callbacks + CET shadow stack.

**Linux .eh_frame stack spoofing is an open field** — no published PoC or framework exists. The primitives are available (`.eh_frame_hdr` is sorted and searchable, CFI rules are computable), but no one has assembled them into a working spoof.

**New attack surface**: kernel-side `.eh_frame` parsing is under development (2026 RFC patchset: `unwind_user` with `.eh_frame` support). Caps CFI instruction processing at 16,384 to prevent malicious `.eh_frame` from causing infinite loops. Malformed `.eh_frame` sections could target the kernel unwinder.

For `.eh_frame` format details: [corsix.org/content/elf-eh-frame](https://www.corsix.org/content/elf-eh-frame). For stack unwinding mechanics: [MaskRay's unwinding notes](https://maskray.me/blog/2020-11-08-stack-unwinding).

---

## Wrapper correctness patterns

Useful defensive wrapper habits:

- Return fast on zero-length buffers in `read` and `write`
- For string syscalls like `openat`, ensure explicit NUL termination
- For syscalls writing kernel-side structs (for example `pipe2`), use correctly sized raw buffers and convert explicitly
- Normalize negative returns into `errno` at wrapper boundaries

---

## Telemetry and troubleshooting implications

When behavior differs between hosts:

- Verify which dispatch source is active (vDSO/libc/direct)
- Verify ABI register placement for 4-6 arg syscalls (`r10` especially)
- Confirm that fallback did not silently switch execution mode
- Compare kernel version, vDSO mapping, and libc build
- Check if seccomp-BPF filters are active (`/proc/self/status` → `Seccomp: 2`)
- Check active eBPF programs (`bpftool prog list`, if the host is trusted)

---

## Decision matrix: dispatch mode selection

```
Target monitoring profile:
│
├── LD_PRELOAD only (basic HIDS, some container agents)
│   └── Direct syscall (mode 3) bypasses entirely.
│       Any statically linked or Go binary is already immune.
│
├── seccomp-BPF (container runtimes, sandbox policies)
│   └── seccomp inspects at syscall entry. io_uring operations
│       bypass the filter after initial setup.
│       On kernel 6.x+: io_uring LSM hooks may close this gap.
│
├── eBPF kprobes/tracepoints (Falco, Tetragon, commercial EDR)
│   └── Kprobes see all syscall entries regardless of dispatch source.
│       io_uring avoids the syscall entry path entirely.
│       vDSO indirect dispatch does NOT help here (kprobe fires regardless).
│       eBPF rootkits can suppress the monitoring itself.
│
├── Audit subsystem (auditd, compliance logging)
│   └── Audit rules fire on syscall entry. io_uring operations
│       were not audited on kernels < 6.1; newer kernels add audit hooks.
│
└── ptrace (strace, GDB, some sandboxes)
    └── ptrace sees all syscalls. Detect via TracerPid in /proc/self/status.
        No dispatch-mode bypass; must detach or evade the tracer itself.
```

---

## Kernel hardening per version (security-relevant for tooling)

| Kernel | Feature | Offensive impact |
|---|---|---|
| 6.1 | kCFI (forward-edge CFI, Clang) | Indirect call targets must match type signature |
| 6.2 | FineIBT (Intel CET IBT + kCFI) | Hardware-enforced indirect branch targets |
| 6.3 | `memfd_create` noexec (`MFD_NOEXEC_SEAL`) | Blocks fileless execution when `vm.memfd_noexec` ≥ 1 |
| 6.7 | Landlock ABI v4 (TCP bind + connect) | Unprivileged network sandboxing |
| 6.9 | BPF token | Containers can run scoped eBPF without CAP_BPF |
| 6.10 | `mseal()` syscall | Seals vDSO/vvar/code mappings against remap/reprotect |
| 6.10 | Landlock ABI v5 (device ioctl) | `LANDLOCK_ACCESS_FS_IOCTL_DEV` restricts device ioctls |
| 6.11 | vDSO `getrandom()` (x86-64) | New vDSO function = additional gadget source |
| 6.12 | IPE LSM (Integrity Policy Enforcement) | Restricts execution to dm-verity protected binaries |
| 6.12 | Landlock ABI v6 (signal + UNIX socket scoping) | Unprivileged signal and abstract socket restrictions |

Check target kernel version with `uname -r`. kCFI/FineIBT are compile-time; most server distros do not enable them. `mseal()` and `memfd_noexec` are runtime-relevant.

### Landlock progression (unprivileged, no CAP required)

| ABI | Kernel | Capability |
|---|---|---|
| v1 | 5.13 | Filesystem access control |
| v2 | 5.19 | Cross-directory rename/link (REFER) |
| v3 | 6.2 | File truncation |
| v4 | 6.7 | TCP bind + connect filtering |
| v5 | 6.10 | Device ioctl restriction |
| v6 | 6.12 | Signal scoping + abstract UNIX socket scoping |

Each ABI is backward-compatible. Use `landlock_create_ruleset()` with the highest ABI needed, fall back on `ENOSYS` or lower ABI.

---

## Frequent mistakes

- Treating all “direct syscall” implementations as observably identical
- Assuming `rcx` carries arg4 on x86-64 syscall entry
- Skipping fallback design and breaking on hosts with unusual vDSO layout
- Handling negative syscall returns as valid payload instead of `errno`
- Assuming `LD_PRELOAD` hooks see all syscalls (Go, static musl, inline asm bypass them)
- Assuming io_uring bypasses all monitoring (kernel 6.x+ adds LSM/audit hooks for io_uring; container seccomp profiles block `io_uring_setup` by default)
- Trusting `bpftool` output on a host that may have eBPF rootkits hiding their own programs
- Using `memfd_create` for fileless execution without checking `vm.memfd_noexec` sysctl (blocks on value ≥ 1)
- Assuming vDSO can be remapped RWX for gadget injection (blocked by `mseal()` on 6.10+)
- Confusing the Linux and Windows problems: Linux doesn't need runtime syscall-number resolution, only dispatch-source selection
