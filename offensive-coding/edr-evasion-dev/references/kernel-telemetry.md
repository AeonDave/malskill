# Kernel-Visible Signals (Usermode Cannot Patch)

Load when deciding **which detections you cannot avoid at all** and must instead make indistinguishable from legitimate behavior. This is the ceiling on any userland-only evasion strategy.

Rule: every technique in the parent `SKILL.md` (indirect syscalls, ETW byte-patch, HWBP, sleep obfuscation, module stomp, LD_PRELOAD, io_uring) suppresses **usermode** telemetry. Signals emitted from **kernel context** — before the syscall returns to userland — bypass all of them. Design around them, don't try to hide them.

---

## Windows Kernel-Fired Signals

### Kernel callback registrations

EDRs register callbacks with these APIs; the callback fires inside the kernel, **before** the syscall returns:

| Callback | Trigger | Emits |
|---|---|---|
| `PsSetCreateProcessNotifyRoutineEx` | Every process create/exit | Parent PID, image path, cmdline, token, PPID (from kernel, not PEB) |
| `PsSetCreateThreadNotifyRoutine` | Every thread create (local or remote) | Owning process, start address, target process |
| `PsSetLoadImageNotifyRoutine` | Every image load (DLL/EXE, including `SEC_IMAGE` remaps) | Image base, size, path, load reason |
| `CmRegisterCallbackEx` | Registry pre/post op | Full key path, operation, access mask, caller PID |
| `ObRegisterCallbacks` (pre-op / post-op) | Handle open on `PsProcessType`, `PsThreadType`, `IoFileObjectType` | Requested access — kernel **reduces the mask** before usermode sees the handle |
| `FltRegisterFilter` (minifilter) | Every file I/O op via IRP_MJ_* | File path, operation, buffer, caller PID |
| Kernel ETW-TI providers (`Microsoft-Windows-Threat-Intelligence`) | Injection, RWX transitions, protected-process access, KUSER_SHARED_DATA reads | Emits from kernel; **not** suppressed by usermode patch of `EtwEventWrite` |

### What each callback prevents

- **`PsSetCreateThreadNotifyRoutine`** fires on APC-injected thread starts, thread-hijack `SetContext`, and `NtCreateThreadEx`. **Waiting Thread Hijacking** avoids `SuspendThread`, not the thread-create notification for the eventual RIP redirect target — target-thread rewrite via `SetContextThread` on an existing thread does not itself trip create-notify, but any new-thread creation does.
- **`ObRegisterCallbacks` pre-op on `PsProcessType`** reduces `PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_CREATE_THREAD` off returned handles when the caller is not on the EDR's allowlist. **Usermode cannot re-elevate the mask**; a duplicated handle inherits the reduced mask. This is why classic `OpenProcess(target, PROCESS_ALL_ACCESS)` for cross-process injection frequently returns a handle without VM_WRITE even from an elevated context.
- **Kernel PPID recording**: `PsSetCreateProcessNotifyRoutineEx` receives the **real** creating process ID from `PspInsertProcess`. `PROC_THREAD_ATTRIBUTE_PARENT_PROCESS` sets the PEB `InheritedFromUniqueProcessId` — but the kernel notify routine sees the **actual** creator. EDRs correlate: if PEB PPID ≠ notify PID → "PPID spoofing" flag. Skill §13 already noted this; this reference is where the reason lives.

### ETW-TI event set (kernel provider, unpatchable)

The `Microsoft-Windows-Threat-Intelligence` provider is registered by kernel and emits from kernel context. Usermode `NtWriteVirtualMemory` on `ntdll!EtwEventWrite` does **not** affect it. Key events:

| Event | Emitted by | Meaning for evasion |
|---|---|---|
| `AllocExecuteVirtualMemory` (24) | `NtAllocateVirtualMemory` / `NtProtectVirtualMemory` when granting `PAGE_EXECUTE_*` | Any RWX or W→X transition on private memory logs here. Module-stomp writes stay under RX, so no event. |
| `ProtectVirtualMemory` (25) | `NtProtectVirtualMemory` | Permission change on any region. Byte-patch ETW (§5) via `NtWriteVirtualMemory` avoids this because it never calls Protect. |
| `WriteVirtualMemory` (26) | `NtWriteVirtualMemory` cross-process | Fires for **cross-process** writes; self-writes (`HANDLE = -1`) log with self as target — routine-looking. |
| `CreateThread` (27) | `NtCreateThreadEx` | Thread start address logged; unbacked-memory start = high signal. |
| `CreateProcess` (28) | `NtCreateProcessEx` and family | Full parent chain, real PPID. |
| `MapView` (37) | `NtMapViewOfSection` with `SEC_IMAGE` | Every image remap logs. AP3 unmap/remap cycle in sleep fires this at each cycle. |
| `ReadProcessMemory` (18) | `NtReadVirtualMemory` cross-process | Credential-dumping analog; noise for benign SDK use. |

**Design consequence**:

- **RWX private allocation** always emits event 24. Tool_mode accepts it (short lifetime). Beacon mode avoids it by using module-stomp (image-backed, `PAGE_EXECUTE_READ` only, no exec-alloc event).
- **AP3 unmap/remap sleep cycle** (SKILL.md §3c) emits event 37 twice per sleep. Long-running beacons should jitter sleep intervals so the pattern doesn't repeat identically.
- **NtWriteVirtualMemory self-target** (§5 byte-patch) is quieter than `NtProtectVirtualMemory` because event 26 with target=self blends with legitimate copy-on-write behavior; event 25 with `ntdll .text` as target is anomalous.

### Kernel process-audit (independent of ETW-TI)

Windows Security Event Log (Sysmon-equivalent) records process creates with `NewProcessId`, `SubjectUserSid`, `TokenElevationType`, and the **real** parent from `EPROCESS.InheritedFromUniqueProcessId`. Kernel-side, not usermode. Sysmon EID 1 and Security 4688 record the same. PPID spoofing does not affect Security 4688.

### CET / shadow stack (Windows 11 24H2+)

Hardware-enforced backward-edge protection. Every `RET` verifies the return address against the shadow stack. Kernel unwinders (ETW-TI stack captures) additionally verify shadow stack consistency.

- `.pdata`-coherent stack spoofing (SilentMoonwalk) constructs frames that pass user-mode unwinding but **do not populate the shadow stack**. On CET-enabled ntdll, the syscall's return-side `RET` finds a mismatch → `#CP (Control Protection)` fault. On CET-observing kernel path (ETW-TI stack capture), the shadow-stack chain is examined and a mismatch is reported even if the CPU didn't fault.
- `NtContinue`-based spoof (SKILL.md §1) is kernel-safe because the kernel writes both stacks coherently when replaying the CONTEXT.
- **Rule**: on CET-enforced targets, disable SilentMoonwalk (SKILL.md §1b) and prefer `NtContinue` spoof + real (unspoofed) return path for backed EXE tool mode.
- Detection state: verify via `GetProcessMitigationPolicy(ProcessUserShadowStackPolicy)` before choosing spoof strategy.

### PPL / Protected Processes

Kernel enforces `EPROCESS.Protection.Type`. `OpenProcess` on a PPL from a non-PPL caller returns handle with reduced mask (`ObRegisterCallbacks` semantics). No usermode bypass — the callback runs before your handle is returned. BYOVD is the only usermode-reachable way to modify `EPROCESS.Protection`. LSASS-as-PPL is the canonical target; `MiniDumpWriteDump` on LSASS handle fails without kernel-level access.

---

## Linux Kernel-Fired Signals

### LSM BPF hooks

`security_*` hooks fire inside the kernel security path. A BPF LSM program returning `-EPERM` **denies** the operation before it completes; a logging program emits an event that userspace cannot intercept without also being kernel-mode.

Key hooks used by modern Linux EDRs (Tetragon LSM mode, Elastic Defend, custom BPF-LSM policies):

| LSM hook | Fires on | Bypass path |
|---|---|---|
| `security_bprm_check` | `execve`/`execveat` after ELF parsed | None from userspace; execve is unavoidable |
| `security_file_open` | Any file open, including via io_uring | Neutralizes io_uring evasion for file access |
| `security_socket_connect` | TCP/UDP connect | Neutralizes io_uring for network |
| `security_socket_create(AF_PACKET)` | Raw socket creation | BPFDoor-style detection |
| `security_bpf_map` | Any bpf() map read/write/update | Enforces map-integrity → blocks map poisoning (§4/§5 Linux ref) |
| `security_bpf_prog` | BPF program load | Blocks rogue BPF program installation |
| `security_kernel_load_data`, `security_kernel_module_request` | Kernel module load | Blocks LKM path |
| `security_ptrace_access_check` | ptrace attach | Yama enforcement |
| `security_task_prctl` | `prctl` invocations | Catches passive checks like `PR_SET_DUMPABLE` if policy set |

**Detection**:

```bash
grep -H "" /sys/kernel/security/lsm         # list enabled LSMs; look for "bpf" and "landlock"
bpftool prog list | awk '/lsm/{print $0}'   # loaded LSM BPF programs
```

If `bpf` is in `/sys/kernel/security/lsm` and any lsm_* program is loaded, **treat every Linux userspace evasion as ineffective**. Pivot host, or plan an LKM path (§4 Linux ref) if lockdown allows.

### Kernel audit subsystem (auditd)

`auditctl` rules generate events entirely inside the kernel. `-S bpf`, `-S ptrace`, `-S init_module` capture syscalls even if every eBPF sensor is blinded. Auditd is a **separate telemetry channel** — evasion focused on eBPF sensors leaves auditd untouched.

Enumeration: `auditctl -l`. If `-S` rules exist for your target syscalls, plan accordingly — auditd cannot be silenced from userland short of `setuid(0)` + `auditctl -e 0` (audit-visible itself).

### IMA / EVM (Integrity Measurement Architecture)

Kernel-computed hashes of executables, loaded modules, and key files. Written to a TPM PCR on some configurations. IMA-audit policy emits every hash mismatch or unknown binary. Evasion is limited: the hash is computed by the kernel from the file bytes at the time of `execve` / `finit_module`. In-memory execution (memfd) still triggers IMA if the policy uses `MEASURE func=BPRM_CHECK`.

Detection: `mount | grep securityfs` shows integrity dir; `cat /sys/kernel/security/ima/policy` shows the active policy.

### Kernel-side process-audit (perf/tracepoint) — sensor-independent

Even without an EDR, tracepoints in the exec path (`sched_process_exec`, `sched_process_fork`, `sched_process_exit`) emit events into perf/ftrace buffers. These are consumable by any userspace reader with `CAP_PERFMON`. Attackers cannot suppress them from userspace; defenders may correlate them offline.

---

## Rules Derived From the Kernel-Signal Set

Concrete constraints, not restatements of general doctrine.

1. **Kernel PPID is real.** PPID spoofing (`SKILL.md` §13) only fools usermode readers that trust the PEB. Any EDR ingesting Security 4688 or `PsSetCreateProcessNotifyRoutineEx` sees the true parent.
2. **Reduced access mask cannot be re-elevated.** If `ObRegisterCallbacks` reduces the mask, no usermode `DuplicateHandle` gets it back. Cross-process injection needs an allowlisted caller or a kernel-mode primitive (BYOVD).
3. **CET / shadow stack breaks user-side unwind spoofing.** SilentMoonwalk on 24H2+ is a fault, not "reduced effectiveness". Verify mitigation status; select spoof strategy accordingly (see `constraints.md` → Syscall Dispatch).
4. **LSM BPF is the Linux ceiling.** With `bpf` LSM enabled and active policies, userspace evasion (io_uring, LD_PRELOAD, memfd, BPF map poisoning) is neutralized. Confirm LSM state before designing the operation.
5. **auditd is orthogonal to eBPF sensors.** Sensor-only evasion leaves auditd untouched. Enumerate `auditctl -l` on every Linux target.
6. **IMA / lockdown determine LKM path viability.** With `MODULE_SIG_FORCE=y` + `LOCKDOWN_INTEGRITY_MAX`, LKM is dead; fall back to eBPF-only means the LSM ceiling above applies harder.

---

## Fingerprinting the Kernel Signal Set

Windows:

```powershell
# Kernel providers registered
logman query providers | Select-String "Threat-Intelligence"
# ETW-TI is available since Windows 10 1809; requires PPL to consume from usermode.

# Mitigation policies for the current process (CET, shadow stack)
Get-ProcessMitigation -Id $PID | Format-List
```

From C/Rust: `GetProcessMitigationPolicy(GetCurrentProcess(), ProcessUserShadowStackPolicy, ...)` returns whether CET is enabled. Same for `ProcessControlFlowGuardPolicy`, `ProcessSignaturePolicy`.

Linux: use the enumeration in `linux-edr-evasion.md` §1. Combine with:

```bash
# LSM stack
cat /sys/kernel/security/lsm
# BPF LSM programs
bpftool prog list | grep -i lsm
# auditd status and rules
auditctl -s; auditctl -l
# IMA
cat /sys/kernel/security/ima/policy 2>/dev/null | head
# Lockdown mode
cat /sys/kernel/security/lockdown 2>/dev/null   # [none] | integrity | confidentiality
```

The combination of `lockdown=confidentiality` + `bpf` LSM + auditd `-S bpf,init_module,ptrace,execve` describes a host where **no usermode-only evasion strategy is credible**. Log the finding and pivot.
