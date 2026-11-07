# Kernel Telemetry Evidence

Load when interpreting kernel-sourced telemetry and distinguishing provider capabilities from collected evidence.

Record the OS build, provider, sensor version, enabled policy, and collection result. Kernel instrumentation, event delivery, and a product's detection decision are separate facts; evidence for one does not establish the others.

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
| `ObRegisterCallbacks` (pre-op / post-op) | Handle open on `PsProcessType`, `PsThreadType`, `ExDesktopObjectType` (the only legal types — file objects need a minifilter) | Requested access — kernel **reduces the mask** before usermode sees the handle |
| `FltRegisterFilter` (minifilter) | Every file I/O op via IRP_MJ_* | File path, operation, buffer, caller PID |
| Kernel ETW-TI providers (`Microsoft-Windows-Threat-Intelligence`) | Injection-shaped kernel operations (cross-process VM ops, exec grants, APCs, context writes) | Emits from kernel; **not** suppressed by usermode patch of `EtwEventWrite` |

### What each callback prevents

- **`PsSetCreateThreadNotifyRoutine`** fires on every new thread (`NtCreateThreadEx`, APC-injected starts). Re-writing RIP of an *existing* thread (`SetContextThread`-style hijack) does **not** trip create-notify — but does fire `EtwTiLogSetContextThread` when the context write is remote (see ETW-TI below).
- **`ObRegisterCallbacks` pre-op on `PsProcessType`** reduces `PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_CREATE_THREAD` off returned handles when the caller is not on the EDR's allowlist. **Usermode cannot re-elevate the mask**; a duplicated handle inherits the reduced mask. This is why classic `OpenProcess(target, PROCESS_ALL_ACCESS)` for cross-process injection frequently returns a handle without VM_WRITE even from an elevated context.
- **Parent and creator identity**: preserve their distinction when interpreting process telemetry. See [the canonical process-creation field guidance](../../windows-internals-dev/references/threads-apcs.md) and the documented `PS_CREATE_NOTIFY_INFO` fields; do not attribute a parent-ID field to the PEB.

### ETW-TI schema and collection evidence

The cited [ETW-TI manifest](https://github.com/repnz/etw-providers-docs/blob/master/Manifests-Win10-18990/Microsoft-Windows-Threat-Intelligence.xml) is a historical Windows 10 build 18990 snapshot. A manifest establishes names and IDs for that snapshot; it does not establish runtime emission conditions, enabled keywords, delivered events, or current vendor coverage.

For event interpretation, retain the provider GUID, event ID/version, schema source, OS build, collection configuration, and observed payload. Resolve identifiers against the matching schema rather than treating this older manifest as a current event catalog. Missing events can reflect collection or configuration gaps; they do not establish that the operation is unobservable.

### Kernel process-audit (independent of ETW-TI)

Security 4688, Sysmon event 1, and process-creation callbacks are distinct evidence sources. Preserve the provider, schema version, and field names; do not assume their parent fields all identify the actual creating process. The callback's parent/creator distinction is documented in [PS_CREATE_NOTIFY_INFO](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/ns-ntddk-_ps_create_notify_info).

### CET / shadow stack

Hardware-enforced backward-edge protection: every `RET` verifies the return address against the shadow stack. Two distinct surfaces — do not conflate them:

- **Kernel-mode shadow stack**: distinct from user-mode protection. [Microsoft's feature documentation](https://learn.microsoft.com/en-us/windows-server/security/kernel-mode-hardware-stack-protection) requires supported hardware, VBS, and HVCI. Record the actual feature state; VBS being enabled or a Windows release label alone does not prove that kernel stack protection is active.
- **User-mode shadow stack**: **opt-in per image** — binaries compiled with `/CETCOMPAT` or processes with the Exploit Protection shadow-stack policy. It is not a blanket 24H2 default. Query it per-process at init: `GetProcessMitigationPolicy(ProcessUserShadowStackPolicy)`.

For user-mode spoofing the governing question is whether the **host process** is CET-enforced:

- `.pdata`-coherent stack spoofing (SilentMoonwalk) constructs frames that pass user-mode unwinding but **do not populate the shadow stack**. In a CET-enforced process the syscall's return-side `RET` finds a mismatch → `#CP (Control Protection)` fault.
- `NtContinue`-based spoof (SKILL.md §1) is CET-safe because the kernel writes both stacks coherently when replaying the CONTEXT.
- **Rule**: on CET-enforced hosts, disable SilentMoonwalk (SKILL.md §1b) and prefer `NtContinue` spoof + real (unspoofed) return path for backed EXE tool mode.
- Sensor-side provenance: [CrowdStrike's feature announcement](https://www.crowdstrike.com/en-us/blog/introducing-falcon-hardware-enhanced-exploit-detection/) describes Intel PT for supported, enabled configurations. It does not establish the previously asserted use of CET shadow-stack contents or a universal syscall-return-address detection rule.

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

1. **Parent attribution and creator identity differ.** Interpret each provider's documented fields; a parent-ID field alone is insufficient to establish the creator.
2. **Reduced access mask cannot be re-elevated.** If `ObRegisterCallbacks` reduces the mask, no usermode `DuplicateHandle` gets it back. Cross-process injection needs an allowlisted caller or a kernel-mode primitive (BYOVD).
3. **CET state is configuration-specific.** A Windows release label does not establish the process's mitigation state or the outcome of an untested execution path.
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
