# Memory analysis workflow

Use memory evidence to reconstruct active execution state, detect fileless or injected behavior, recover transient secrets, and correlate runtime activity with disk and network evidence.

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

## 8) Output

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
