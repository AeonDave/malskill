# Linux EDR/XDR Evasion — Detail

Load when a target runs Linux runtime-security tooling (Falco, Tetragon, Tracee, Aqua, Elastic Defend Linux, CrowdStrike Falcon Linux, SentinelOne Linux) or a hardened server host with auditd + eBPF sensors.

Windows patterns in the parent `SKILL.md` (syscall dispatch, ETW patching, HWBP, module stomp, SilentMoonwalk) do **not** apply to Linux. Do not port them. Linux evasion is dominated by three questions:

1. Which kernel hooks (kprobe / tracepoint / fentry / LSM BPF) does the sensor actually attach?
2. Can the syscall be routed around the hookpoint (io_uring, direct read/write over open fd, vsyscall)?
3. Is the sensor storing state in a BPF map without `security_bpf_map` LSM enforcement?

Everything below flows from those three questions.

---

## 1. Sensor Fingerprinting First

Do sensor enum **before** deploying any evasion. Blind evasion in the wrong direction is louder than doing nothing.

```bash
# Loaded BPF programs, attach points, and owning maps
bpftool prog list -j | jq -r '.[] | "\(.id) \(.type) \(.name) \(.attach_type // "")"'
bpftool prog show id <id> --pretty          # incl. map_ids, run_time_ns, run_cnt

# LSM BPF programs enforcing map/policy hooks
bpftool prog list | grep -i lsm

# Kprobes registered by any tool (Falco, Tracee, custom)
cat /sys/kernel/debug/kprobes/list           # requires CAP_SYS_ADMIN or root
cat /sys/kernel/tracing/available_events     # tracepoints available

# Kernel hardening state
sysctl kernel.unprivileged_bpf_disabled      # 1 = need CAP_BPF for load
sysctl kernel.unprivileged_userns_clone      # 1 = userns escape feasible
sysctl kernel.yama.ptrace_scope              # 0=any, 1=parent-only, 2=cap_sys_ptrace, 3=disabled
sysctl kernel.dmesg_restrict                 # 1 = dmesg admin-only
zgrep -E 'CFI|IBT|LOCKDOWN|MODULE_SIG_FORCE|BPF_LSM' /boot/config-$(uname -r)

# Audit rules — auditd is a separate telemetry channel from eBPF
auditctl -l 2>/dev/null | grep -E 'execve|bpf|ptrace|init_module|memfd'

# Running EDR agents
ps auxef | grep -Ei 'falco|tetragon|tracee|elastic-agent|sentinel|csagent|xdragent'
```

**Decision routing after enum**:

| Enum result | Implied evasion path |
|---|---|
| No LSM BPF, no `-S bpf` audit rule | BPF map poisoning viable — see §5 |
| `sys_enter_execve` kprobe or tracepoint loaded | Prefer memfd + interpreter over ELF drop (§3), or LKM autoload persistence (§9) |
| No `io_uring_enter` tracepoint / kprobe | io_uring covers openat/read/write/connect blind (§2) |
| CFI + IBT + `LOCKDOWN_INTEGRITY_MAX` | LKM rootkit path dead; use eBPF-only (§4) or userland |
| `ptrace_scope >= 2` | ptrace-based injection needs CAP_SYS_PTRACE; prefer `/proc/pid/mem` (§7) |
| `unprivileged_userns_clone=1` | Container escape + CAP_BPF acquisition viable (§8) |

---

## 2. io_uring — the Coverage Gap

`io_uring_enter` submits a batch of asynchronous operations from an SQ ring. The kernel executes openat/read/write/connect/sendmsg/recvmsg/statx/unlink/rename/mkdirat/close/accept/splice internally without dispatching them as individual syscalls. Sensors that hook `sys_enter_openat`, `sys_enter_connect`, etc. see **nothing**.

**Supported operations (kernel 5.11+)**: `IORING_OP_NOP`, `READV`, `WRITEV`, `FSYNC`, `READ_FIXED`, `WRITE_FIXED`, `POLL_ADD`, `SENDMSG`, `RECVMSG`, `TIMEOUT`, `ACCEPT`, `ASYNC_CANCEL`, `LINK_TIMEOUT`, `CONNECT`, `FALLOCATE`, `OPENAT`, `CLOSE`, `FILES_UPDATE`, `STATX`, `READ`, `WRITE`, `FADVISE`, `MADVISE`, `SEND`, `RECV`, `OPENAT2`, `EPOLL_CTL`, `SPLICE`, `PROVIDE_BUFFERS`, `REMOVE_BUFFERS`, `TEE`, `SHUTDOWN`, `RENAMEAT`, `UNLINKAT`, `MKDIRAT`, `SYMLINKAT`, `LINKAT`.

**Not covered** (must still use standard syscalls): `execve`, `execveat`, `clone`, `fork`, `ptrace`, `bpf`, `finit_module`, `mmap`, most `prctl`. These remain full-signal.

**Detection surface (2025-2026)**:

| Sensor | Coverage | Notes |
|---|---|---|
| Falco < 0.40 | No `io_uring_enter` rule by default | Blind; io_uring for file/net I/O is free |
| Falco ≥ 0.40 | Tracepoint on `io_uring_enter`, minimal rules | Sees submission count, not per-op semantics |
| Tetragon (kprobe mode) | Same as Falco | Cannot introspect ring contents from tracepoint |
| Tetragon (LSM mode) | LSM hooks `security_file_open`, `security_socket_connect` fire from io_uring's kernel path — **not bypassable** | The correct defensive answer; still uncommon in production |
| Tracee | Adds io_uring event set in recent versions | Verify with `tracee --list \| grep io_uring` |
| Elastic Defend Linux | Ships io_uring rules 8.13+ | Verify agent version before assuming blindness |

**Rules**:

- Use io_uring for openat/read/write/connect/sendmsg on hosts where the sensor is Falco < 0.40 or an old Tetragon without LSM mode.
- Do **not** try io_uring for execve or process creation — no `IORING_OP_EXECVE` exists; those syscalls stay visible.
- One `io_uring_enter` call can batch dozens of ops; keep count low to avoid completion-event correlation.
- LSM BPF (`bpftool prog list | grep lsm`) neutralizes this vector entirely because `security_file_open` fires regardless of dispatch path.

**Bash builtin PoC pattern (0xMatheuZ)**: loadable Bash builtin (`enable -f ./uwriteb uwriteb`) invokes `io_uring_write` from bash's PID. Tetragon (kprobe mode) reports no write event; process attribution goes to `/usr/bin/bash` with no argv trail.

---

## 3. Fileless Execution — memfd + fexecve

Baseline pattern:

```c
int fd = syscall(SYS_memfd_create, "", MFD_CLOEXEC);   // empty name; avoid memfd:<label> tell
write(fd, elf_bytes, elf_size);                        // or io_uring WRITE_FIXED for §2 coverage
fexecve(fd, argv, envp);                               // execveat(fd, "", argv, envp, AT_EMPTY_PATH)
```

**Elastic Defend 9.4.0+ signal**: records `process.Ext.memfd.name`, `.flags`, `.pid`, and correlates `memfd_create` → `write` → `execveat(fd, "", ..., AT_EMPTY_PATH)` within a short window. Rule "Potential Fileless Execution Sequence" fires on that chain.

**Falco default**: catches `execve` of `/proc/self/fd/<N>` and `memfd:<name>` since v0.35. Blind on empty memfd name only if the rule uses substring match on `memfd:`.

**OPSEC rules**:

| Do | Don't |
|---|---|
| Pass empty name to `memfd_create` (`""` not `"beacon"`) | Use memorable names — they land in `/proc/<pid>/maps` |
| Chain via legit interpreter: `curl → perl -e '...memfd...'` | Direct `execve` from freshly-spawned parent — parent/child correlation trivial |
| Use `MFD_CLOEXEC \| MFD_ALLOW_SEALING` and seal after write | Leave `MFD_EXEC` flag set (kernel 6.3+; explicit executable memfd) |
| Fill payload via `io_uring WRITE_FIXED` to hide the write | Multiple `write()` calls — ordered writes make sequence rules easier |
| `fexecve` from a different pid than the one that filled the fd (parent writes, `posix_spawn` execs) | Same-pid write+exec — classic sequence fires immediately |

**Deleted-file variant**: `open(O_TMPFILE, /tmp)` → write → `linkat(AT_EMPTY_PATH)` skipped → `fexecve`. No dirent, no unlink event, but `/proc/<pid>/exe` resolves to `/tmp/#<inode>` (deleted). File-integrity monitors on `/tmp` see nothing.

**Interpreter loaders** (rank by signal): `awk` < `perl` < `python3` < `bash` < `sh`. Prefer `awk`/`perl` — less common in analyst rulesets, richer syscall surface than sh.

---

## 4. eBPF Rootkit vs LKM — the 2025 Tradeoff

| Property | LKM (ftrace / kprobe hooks) | eBPF program (verifier-bound) | Hybrid |
|---|---|---|---|
| Load requirement | `CAP_SYS_MODULE`, module signing bypass if `LOCKDOWN_CONFIDENTIALITY` | `CAP_BPF` (5.8+) or `CAP_SYS_ADMIN` | Both |
| Control-flow modification | Arbitrary (ftrace stub, direct call rewrite) | Only tail-calls between BPF progs; verifier blocks arbitrary flow | Arbitrary via LKM |
| Persistence | Survives reboot via modprobe/systemd autoload | Dies on `bpftool prog delete` / reboot | LKM anchors, eBPF blinds |
| Visibility | `lsmod`, `/sys/module`, `/proc/modules` — hide via list unlink | `bpftool prog list`, `bpftool map list` — hide via bpf() intercept | Depends |
| Kernel 6.1+ hardening | CFI-CLANG blocks direct call rewrites; use ftrace | Verifier accepts LSM BPF; enforcement side becomes strict | Same |
| Best PoC | Reptile, KoviD, Diamorphine, Adrishya, Singularity (ftrace) | bad-bpf, TripleCross, Boopkit | Singularity |

**Rule**: on kernel ≥ 6.1 with `LOCKDOWN_INTEGRITY_MAX` and `MODULE_SIG_FORCE=y`, LKM is dead — a signed module is required and BYOVD-analog is rare on Linux. Use eBPF-only path when privesc gives `CAP_BPF`; use LKM only on legacy hosts where lockdown is permissive.

### 4a. eBPF sensor blinding via competing BPF program

When another BPF program already hooks the same kprobe/tracepoint the sensor uses, the kernel dispatches to both. Attach a program that **filters events for your PID** before the sensor's ringbuf write:

1. Load your program with `bpf(BPF_PROG_LOAD)` at the same attach point (`raw_tracepoint/sys_enter_execve`, `kprobe/security_file_open`, etc.).
2. Compare `bpf_get_current_pid_tgid()` against a `hidden_pids` map.
3. If match: `return 0` (drop) — the raw tracepoint sensor still fires its handler, but if you hook after theirs, you cannot suppress theirs; you must attach `fentry/fexit` on the sensor's own helper functions (`bpf_ringbuf_output`, `bpf_perf_event_output`) with an ftrace hook that filters ringbuf writes by the calling program's map ID.
4. That last step requires **kernel-mode code**, i.e. an LKM setting up ftrace on `bpf_ringbuf_output` — this is Singularity's design.

**Pure userspace BPF map poisoning (no LKM)** works only when the sensor uses BPF maps for allowlists/blocklists **without** `security_bpf_map` LSM enforcement:

- Falco stores syscall monitor flags in an `interesting_sys[]` BPF map. `bpftool map update id <N> key <syscall_nr> value 0` disables monitoring for that syscall for the duration of your operation. Restore before exit.
- Verify LSM enforcement first: `bpf(BPF_MAP_UPDATE_ELEM, target_map)` returning `-EPERM` means `security_bpf_map` is denying you.

### 4b. Signature avoidance for LKM

- `.modinfo` section leaks author, description, license — strip before packaging, or set to plausible values (`license=GPL v2`, `author=Linus Torvalds`) that match common noise.
- `init_module`/`finit_module` events include the module blob's SHA-256 in Elastic Defend 9.4.0+ — rotate byte-level layout per deployment.
- Modern kernels expose `/proc/kallsyms` (root-only if `kptr_restrict=2`). Do not resolve symbols by name at init — resolve by pattern-matching from a known-address anchor (kallsyms is auditable).
- ftrace hooks appear in `/sys/kernel/tracing/enabled_functions` when enabled — hide by hooking `ftrace_ops_list_func` to filter your own entries.

---

## 5. LSM BPF — What Cannot Be Dropped From Userspace

LSM hooks execute inside the kernel's security path (`security_file_open`, `security_bprm_check`, `security_socket_connect`, `security_bpf_map`, `security_kernel_module_request`, etc.) **before** the operation completes. Return `-EPERM` from a Tetragon LSM policy blocks the syscall from user perspective, not just logs it.

**Cannot be evaded from userspace**:

- LSM emissions have no ringbuffer that userspace controls; drop must happen inside kernel.
- Suppressing them requires either (a) ftrace hook on the LSM function itself (LKM), or (b) unloading the enforcing BPF program (needs `CAP_BPF` and typically detected).
- On kernels with `CONFIG_BPF_LSM=y` + Tetragon LSM policies active, userspace-only techniques from §1–§4 are neutralized.

**Detection**:

```bash
bpftool prog list | grep lsm       # any lsm_* program present means LSM enforcement is live
grep -H "" /sys/kernel/security/lsm  # "capability,landlock,lockdown,yama,integrity,apparmor,bpf" etc.
```

**Rule**: if `lsm` shows entries and `bpf` is in the active LSM list, treat the host as LSM-guarded. Do not attempt userspace-only evasion; either pivot to a different host, or plan an LKM path (§4) if lockdown allows.

---

## 6. Anti-Debug & Anti-Analysis (Passive Preferred)

Same doctrine as Windows in the parent skill: **passive checks generate zero syscalls; invasive checks fire events**. Score multiple weak signals; never hard-fail on one.

| Check | Cost | Notes |
|---|---|---|
| `PTRACE_TRACEME` self-attach | 1 syscall (audit-visible if `-S ptrace`) | Reliable: process can be traced only once; a second attach fails |
| Read `/proc/self/status`, parse `TracerPid:` | 1 open + 1 read | Zero-syscall signal for pure userspace observers; cheap |
| `prctl(PR_SET_DUMPABLE, 0)` | 1 syscall | Blocks future ptrace attach; cheap; benign-looking |
| Timing delta (`clock_gettime(CLOCK_MONOTONIC_RAW)` around a NOP loop) | zero syscall in vDSO on x86_64 | Debugger/single-step latency ~5–500 μs vs baseline ~<1 μs |
| `getauxval(AT_HWCAP)` and `/proc/cpuinfo` for hypervisor bit | 1 read | Sandbox detection; distinguish KVM/QEMU from cloud (many clouds are KVM too — noisy alone) |
| `/proc/self/task` count sanity | 1 open + N reads | If expected N threads but N+1, debugger attached a helper thread |
| Static compilation (musl) | build-time | Neutralizes LD_PRELOAD-based tracing and libc-hook rootkits at once |
| SIGSYS handler probe | install handler + issue known-blocked syscall | Sandbox seccomp filters raise SIGSYS on blocked syscalls — detect the filter's shape |

**Anti-LD_PRELOAD**: static musl binary is the strongest single lever. If dynamic linking is unavoidable, verify `getenv("LD_PRELOAD")` is unset and `open("/etc/ld.so.preload", O_RDONLY)` returns ENOENT before proceeding.

**Do not** use invasive tricks by default:

- `ptrace(PTRACE_TRACEME)` — audit signature, "typical malware" heuristic
- Repeatedly polling `/proc/self/status` in tight loop — pattern-matchable
- CPUID hypervisor probe followed by early exit — behavioral rule catches "check + exit" pattern

---

## 7. In-Memory Execution and Injection

| Technique | Kernel visibility | Best-fit target |
|---|---|---|
| `memfd_create` + `fexecve` (§3) | Elastic 9.4.0+ full chain; Falco `execve` of `memfd:` | Fileless drop, LD_PRELOAD-free |
| Interpreter one-liner (perl/awk) | execve of interpreter + argv | Fastest; hides real payload in encoded argv/stdin |
| `ptrace(PTRACE_ATTACH)` + `PTRACE_POKEDATA` + `PTRACE_SETREGS` | Every ptrace op is audit + eBPF visible | Loud; only if target sensor lacks ptrace hooks |
| `/proc/<pid>/mem` direct write | 1 open + 1 write, file-integrity dependent | Cheaper than ptrace; requires `ptrace_scope <= 1` or same-uid + `PR_SET_DUMPABLE=1` |
| `process_vm_writev` | 1 syscall, monitored less than ptrace | Same access rules as `/proc/pid/mem`; more efficient |
| GOT/PLT overwrite (post-load) | Zero syscalls after the initial write | Requires pre-existing write primitive; invisible to kprobe sensors |
| DT_DEBUG r_brk hijack | Zero syscalls | Requires patched ELF or in-memory ELF header edit; complex |

**Rules**:

- Prefer `process_vm_writev` and `process_vm_readv` over ptrace when the target sensor has ptrace rules but no `-S process_vm_writev`.
- `/proc/<pid>/mem` writes work only when `ptrace_scope <= 1` or Yama LSM allows same-UID access; check first.
- If injecting into a systemd unit, the parent is `systemd` — kernel process-audit records that as the origin, which is legitimate-looking.

---

## 8. Container / Kubernetes-Specific Vectors

Containers are not a security boundary against modern host-level eBPF EDRs, but they add layers useful for pivoting:

- **Unprivileged userns creation** (`unshare -U`) grants `CAP_BPF` and `CAP_SYS_ADMIN` inside the new namespace when `kernel.unprivileged_userns_clone=1`. Combined with §5-vulnerable BPF map poisoning, that reaches Falco/Tetragon state from a container.
- **runc/leaky-vessels (CVE-2024-21626)** and PID-namespace leaks (CVE-2025-26324) escape to host via `/proc/<host-pid>/root` traversal.
- **Sidecar hiding**: DaemonSet-based sensors (Falco, Tetragon) filter by pod selector; a sibling pod outside the selector is invisible to policy-scoped rules even though the host agent sees all syscalls.
- **Mount namespace**: mounting `tmpfs` over `/etc` inside a namespace shadows files locally. Host EDR still sees the mount syscall; policy filters that lookup pod-scoped may miss the shadow.

**Rule**: containers help hide from **pod-scoped** policies. They do not help against host-level agents. Enumerate the sensor's rule scope (`kubectl get tracingpolicies -A`, Falco rule `container.name` filters) before assuming a container hides you.

---

## 9. Persistence Under eBPF Observation

Weights use the 0–4 scale in `best-practices.md` §2.

| Vector | Weight | Falco/Tetragon default coverage |
|---|---|---|
| `/etc/ld.so.preload` write | 4 | File-integrity rule; `open(O_WRONLY, /etc/ld.so.preload)` fires |
| `/etc/passwd`, `/etc/shadow` edits | 3 | File-integrity, standard rule |
| systemd unit in `/etc/systemd/system/` | 3 | File-write + subsequent `execve` of new service |
| systemd unit in `/run/systemd/system.generator/` (early boot) | 1 | Generators run before most agents attach; verify agent start-delay |
| `~/.bashrc`, `~/.profile` append | 1 | Sourced, not exec'd — no execve event; only file-write signal |
| `~/.ssh/rc` | 1 | Runs in ssh child's context; blends with legitimate login |
| PAM module in `/lib/security/` | 2 | dlopen from `pam_authenticate`; file-integrity on `/lib/security/` catches the drop, not the load |
| Kernel module autoload (`/etc/modprobe.d/*.conf`) | 1 | Deferred load — `finit_module` fires later, attributed to `modprobe` |
| SUID binary drop | 3 | Both file-integrity and `execve` alert on new SUID |
| Docker/Podman socket abuse | 2 | Root inside container via socket; visible as new privileged container |
| Cron `@reboot` via non-root user's crontab | 2 | `crontab -e` opens `/var/spool/cron/crontabs/<user>` (root-owned; file-integrity) |

**Rule**: prefer sourced-file persistence (`.bashrc`, `.ssh/rc`) or deferred-load persistence (systemd generator, modprobe autoload) over anything that requires an immediate `execve` or `open` on `/etc`.

---

## 10. Network C2 Hiding

- **Raw socket + BPF filter (BPFDoor-style)**: `socket(AF_PACKET, SOCK_RAW)` + `setsockopt(SO_ATTACH_FILTER, bpf_prog)` reads from the wire without any listening socket. `netstat`/`ss` show nothing. Trigger on a magic byte pattern; only then open the real C2 socket.
- **XDP-based**: attach XDP program to interface (`bpf(BPF_PROG_LOAD, BPF_PROG_TYPE_XDP)`); handles packets before the network stack. Any userspace socket-tracking sensor sees zero packets. Detection requires LSM BPF or `bpftool prog list` audit.
- **QUIC over 443**: Falco/Tetragon see `connect` to port 443 UDP, no protocol details. Cheap disguise if outbound 443 UDP is allowed. Encrypted client hello (ECH) hides SNI from network inspection.
- **DNS tunnelling**: high-volume DNS queries generate no per-connect events (uses existing resolver socket via getaddrinfo → send); but volume-based rules exist.

**Rule**: raw socket + BPF filter is the classic stealth C2 primitive on Linux and remains effective when `AF_PACKET` socket creation isn't in the sensor's ruleset. Verify with `bpftool prog list` and audit rules.

---

## 11. Signal-Cost Cheatsheet (Linux)

Syscall weights on the same 0–4 scale as `best-practices.md` §2. Aim to keep weight-3+ syscall count below 5 in any 60-second window.

| Syscall | Weight | Notes |
|---|---|---|
| `execve`, `execveat` | 3 | Universally monitored |
| `connect`, `bind`, `listen`, `accept*` | 3 | Network rules ubiquitous |
| `ptrace` | 3 | Malware heuristic |
| `bpf` (with `-S bpf` audit rule) | 3 | If audit rule loaded |
| `init_module`, `finit_module`, `delete_module` | 3 | Kernel module load/unload |
| `openat` on `/etc/*`, `/root/*`, `/proc/*/mem` | 3 | File-integrity rules |
| `openat(/etc/ld.so.preload, O_WRONLY)` | 4 | Rootkit-persistence signature |
| `memfd_create` (Elastic 9.4.0+) | 2 | Blind on Falco < 0.35 |
| `io_uring_enter` | 2 (1 on Falco < 0.40) | Batch payload not introspected by tracepoint |
| `process_vm_writev`, `process_vm_readv` | 2 | Rarely rule-covered vs ptrace |
| `mprotect(PROT_EXEC)` on `PROT_WRITE` region | 2 | RWX-analog; some rules exist |
| `prctl`, `getpriority`, `clock_gettime` | 0 | Passive-check territory |
| `read`, `write` (regular fd) | 0 | Too high volume to alert on |
| `mmap`, `mprotect(RW)`, `brk`, `madvise` | 1 | Rare alert unless anomalous flags |
| `getdents64` on `/proc` (process enum) | 1 | Volume-tolerated |

---

## 12. Malware Family Recipes (2024-2026)

Common combined recipes seen in Sedexp, BPFDoor variants, Symbiote, WolfsBane, Pumakit, Perfctl:

- **Fileless staging**: `curl → openssl decrypt → perl -e '...memfd... fexecve'` — 2-3 signals total, none tied to a dropped file.
- **LD_PRELOAD libc-hook rootkit** (Symbiote): hooks `readdir`, `open`, `stat`, `fopen` in every dynamically linked process. Blind to static musl binaries and to `getdents64` callers.
- **Kernel + eBPF hybrid** (Pumakit): LKM hooks `kallsyms_lookup_name`, installs ftrace hooks on syscall entry, loads a companion BPF program that filters ringbuf outputs. When LKM is unloaded, eBPF alone survives with reduced capability.
- **Raw socket beacon** (BPFDoor 2024/2025): AF_PACKET + BPF filter on ICMP or specific TCP flags. No listening socket. Wakes only on magic packet; opens outbound TLS or reverse shell to attacker.
- **Systemd persistence + tmpfiles** (Perfctl): drops helper binary to `/tmp/.X11-lock/`, registers `/etc/tmpfiles.d/` entry, so system re-creates it on cleanup. Runs via systemd generator.

**Rule**: pick one recipe per operation; do not combine LKM + LD_PRELOAD + memfd + BPF poisoning + raw socket in one binary. Feature accumulation adds signals faster than it hides them (same doctrine as Windows §0 Evasion Minimalism).

---

## 13. Verification Checklist Before Deployment

Before flipping evasion features on for a Linux target:

1. `bpftool prog list -j` captured; confirm sensor's programs identified.
2. `bpftool map dump id <sensor_map>` — know the shape of the sensor's state.
3. LSM enforcement confirmed absent for the maps you plan to poison.
4. `sysctl` snapshot: `unprivileged_bpf_disabled`, `unprivileged_userns_clone`, `yama.ptrace_scope`, `dmesg_restrict`, `kptr_restrict`.
5. `auditctl -l` reviewed — you know which syscalls trip auditd independently of eBPF.
6. Kernel config grep for `CFI_CLANG`, `BPF_LSM`, `LOCKDOWN_LSM`, `MODULE_SIG_FORCE` — determines LKM path viability.
7. Elastic Defend / CrowdStrike / SentinelOne agent version identified — if the agent post-dates the technique's known-blind window, do not use that technique.
8. Container context established (`cat /proc/1/cgroup`, `readlink /proc/self/ns/*`) — pod-scoped rule blindness only helps in-container.
9. Static vs dynamic binary decision made — musl static defeats one entire class of userspace observation.
10. Payload rotation confirmed — no reused SHA-256 across deployments.

Skipping any step turns "known-blind window" into "hoped-blind window."
