# Memory analysis workflow

Use memory evidence to reconstruct active execution state, detect fileless or injected behavior, recover transient secrets, and correlate runtime activity with disk and network evidence.

## Contents

- [Intake and image sanity](#1-intake-and-image-sanity)
- [Establish process reality](#2-establish-process-reality)
- [Map runtime behavior](#3-map-runtime-behavior)
- [Injection and evasion checks](#4-injection-and-evasion-checks)
- [Credential and secret recovery](#5-credential-and-secret-recovery)
- [Extraction strategy](#6-extraction-strategy)
- [Cross-source validation](#7-cross-source-validation)
- [Linux kdump and crash triage](#8-linux-kdump-and-crash-triage)
- [Output](#9-output)

Primary tool skills:

- `offensive-tools/forensic/volatility3/` — process, network, registry, module, handle, and memory-region analysis.
- `offensive-tools/forensic/yara/` — scan memory and dumps for code/config patterns.
- `offensive-tools/forensic/capa/` — classify dumped processes, shellcode, and unpacked binaries by capability.

## 1) Intake and image sanity

Before interpretation:

- Record image source, OS family, acquisition tool, acquisition time, and suspected timezone.
- Hash memory image and work from a copy.
- Identify OS/kernel/build profile from Volatility banners and symbol resolution.
- If symbols fail or plugin output is empty, fix image/profile handling before drawing conclusions.

## 2) Establish process reality

Build the process model first. Most memory findings are process-context findings.

Checklist:

- Process list and parent-child tree.
- Process creation times and exit times.
- Command lines and environment variables.
- Duplicate system process names in odd paths.
- Suspicious parents: Office/browser spawning shells, script hosts, service managers, temp executables.
- Security tooling processes and tamper indicators.

Quality gate: suspicious process claims need at least one reason beyond the name.

## 3) Map runtime behavior

For suspicious processes and system-wide context, collect:

- Active/listening sockets, remote peers, ports, protocols.
- Loaded modules/DLLs/shared objects and unusual load paths.
- Handles to files, registry keys, mutexes, sections, devices, named pipes.
- Command history, clipboard, console buffers, where available.
- Registry hives and autorun keys from memory when disk is unavailable.

Correlate sockets with `pcap-analysis.md` and `network-technique` before asserting C2.

## 4) Injection and evasion checks

Prioritize process regions and module anomalies:

- RWX or execute-write memory regions.
- Private executable memory without backing file.
- PE/ELF headers in heap or anonymous mappings.
- Hollowing indicators: image path says one binary, memory image differs.
- Unlinked or hidden processes/modules.
- Thread start addresses outside known image ranges.
- Hooked userland APIs or unusual trampoline bytes.
- On Linux, cross-view linked modules against memory scans, then correlate scan-only candidates with kernel logs and tracepoint/ftrace ownership. Deduplicate repeated socket descriptors before counting sessions; treat environment variables as pivots into lineage and privilege state, not standalone proof.

Scan suspicious regions with YARA before dumping everything. Use capa on dumps to identify capabilities such as injection, credential access, persistence, encryption, or C2.

## 5) Credential and secret recovery

Memory may contain transient material that never touches disk:

- LSASS/credential provider material on Windows.
- Browser/session tokens, API tokens, OAuth refresh tokens.
- SSH agents, private keys, database connection strings.
- Crypto keys, ransomware file keys, config decrypted at runtime.

Handle extracted secrets as sensitive evidence. Record where they came from and avoid using them unless the engagement explicitly permits validation.

## 6) Extraction strategy

Dump selectively:

1. Process executable image or suspicious VAD/region.
2. Specific injected region or shellcode candidate.
3. Module/config/resource blobs tied to process behavior.
4. Credential material only when required and authorized.

For each dump, preserve:

- Source image hash, plugin name/version, process PID, virtual offset/range.
- Dump hash and filename.
- Reason for extraction.
- Follow-up status: YARA, capa, strings, static RE, dynamic run.

## 7) Cross-source validation

Memory is strong for "what was running at acquisition time"; it is weaker for long-range chronology.

Validate key claims against:

- Disk artifacts: Prefetch, AmCache/ShimCache, LNK, scheduled tasks, service entries, shell history.
- PCAP/Zeek: process socket peer matches DNS/TLS/HTTP traffic.
- Event logs: process creation, service install, PowerShell, Defender/AV.
- Reverse engineering: dumped payload capability matches observed behavior.

Unmatched memory-only findings should be reported as transient until corroborated.

## 8) Linux kdump and crash triage

Use this path when the evidence is a Linux `vmcore`, kdump, or `makedumpfile`
output and a debug `vmlinux` is available. Preserve and hash both inputs; keep
the source dump immutable.

### Normalize the dump format and symbols

Do not infer the format from the filename. A `makedumpfile -F` flattened stream
is not a normal vmcore. If the installed `crash` rejects it, convert it without
overwriting the source:

```bash
sha256sum vmcore.flat vmlinux
makedumpfile -R vmcore < vmcore.flat          # flattened stream on stdin
makedumpfile --reassemble vmcore.0 vmcore.1 vmcore  # --split output
crash -s -i crash.cmd vmlinux vmcore
```

`-R` is for flattened input; `--reassemble` is for files made with `--split`.
Use a `vmlinux` built for the crashed kernel, not the capture kernel. Confirm
the architecture and the `RELEASE`/`VERSION` shown by `crash`'s `sys` command,
then record the debug image's build ID and hash:

```bash
readelf -h vmlinux | grep -E 'Class|Machine'
readelf -n vmlinux | grep -i 'Build ID'
```

If the original kernel ELF is available, compare its `.note.gnu.build-id` to
the debug image. A compressed kdump often does not carry a separately readable
build ID; in that case record the limitation and require exact release,
architecture, and package provenance before relying on symbols.

A release, architecture, or build-ID mismatch is a symbol/provenance failure;
stop and obtain the matching debug image instead of trusting translated frames.

### First-pass `crash` commands

Run focused commands first and preserve their raw output:

```text
sys                         # dump identity, panic, release, date, CPUs
log                         # exact Oops/panic and module-load messages
ps                         # all tasks
ps -p <PID>                 # parent chain for one task
ps -a <PID>                 # argv/environment for a user task
set <PID>                   # select task context
bt                          # selected task's stack
bt -a                       # stacks for all CPUs/tasks (larger output)
net                         # devices and addresses
net -n <PID>                # device view in the task's network namespace
net -s <PID>                # sockets owned by the task
files <PID>                 # file descriptors and paths
mod                         # loaded modules, BASE/SIZE, known object file
sym <address>               # address-to-symbol translation
sym -m <module>             # symbols attributed to one module
```

If a process identity or privilege matters, retain its `TASK` pointer from
`ps` and inspect the parent and credentials directly:

```text
struct task_struct.parent <TASK_ADDR>
struct task_struct.cred <TASK_ADDR>
struct cred <CRED_ADDR>
```

Record `uid.val`, `euid.val`, `fsuid.val`, and `user_ns`; a UID of zero is
namespace-relative and is not by itself proof of host-root privilege. Correlate
the credential with the parent chain, command line, open files, and module/load
records before asserting execution or privilege escalation.

### Interpret panic and module frames correctly

- The `RIP:` line in `log`, and the `[exception RIP: ...]` line in `bt`, identify
  the instruction that faulted. In a kdump reached through `crash_kexec`, `bt`
  frame `#0` can instead be a crash handler such as `machine_kexec`; that frame
  is not automatically the vulnerable function.
- `mod`'s `BASE` is the module's runtime virtual address, not a filesystem path.
  Its `OBJECT FILE` column is available only when crash knows the object; a
  missing object path does not justify inventing one. A path supplied to
  `mod -s` is analyst input, not proof of where the module was loaded from.
- `sym -m <module>` and `sym -q cleanup_module` help resolve module symbols.
  `cleanup_module` is commonly the generated/ABI alias for a module's exit hook;
  when it resolves to the same address as `<module>_exit`, count one function,
  not two independent hooks.

## 9) Output

Produce:

- Suspect process map: PID, PPID, path, command line, start time, reason.
- Network correlation list: process-to-session/domain mapping.
- Injection/evasion table: process, region, protection, evidence.
- Extracted artifact list with hashes and follow-up results.
- Confidence labels: direct memory fact, corroborated finding, inferred interpretation.

## Common pitfalls

- Treating `pslist` alone as complete; compare process and pool views for hidden/unlinked objects.
- Ignoring symbol/profile errors and accepting empty output.
- Dumping every process before defining hypotheses.
- Claiming persistence from memory-only presence.
- Running dumped malware without isolation or without preserving hashes.
