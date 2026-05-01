# Lessons learned patterns for forensic investigations

## Purpose

Codify reusable investigation lessons from recurring incident patterns.

Use this reference when you need fast, high-confidence answers from mixed artifacts (EVTX, registry hives, MFT, PCAP, memory, firmware dumps, API traces).

## 1) Objective-to-artifact mapping first

Before parsing data, map each objective to the **lowest-cost decisive artifact**.

- Identity/credentials used in HTTP auth → PCAP HTTP headers (`Authorization`, cookies, body fields)
- Windows defense tampering → PowerShell Operational EVTX (4104), Security/System EVTX, registry keys
- VM/sandbox checks → PowerShell script blocks + WMI queries + process checks + registry/service probes
- File/process injection chain → API trace logs + process metadata + memory indicators
- MFT timeline reconstruction → `$MFT` parser output (entry number, timestamps, flags, path)
- Linux live backdoor behavior → process tree + command lineage + package/library version checks
- Firmware/OpenWrt compromises → extracted rootfs overlay, init scripts, service startup links

## 2) Windows EVTX + PowerShell playbook

### High-value channels and artifacts

- `Microsoft-Windows-PowerShell/Operational` (4104 ScriptBlock)
- Security event logs (process creation / account activity)
- Sysmon (if present): process creation, network, registry
- Defender operational logs (threat actions: quarantine, blocked, allowed)

### Practical sequence

1. Find suspicious script blocks and decode embedded payloads.
2. Extract all command lines that alter security posture (Defender, AMSI, LSA, Safe Mode, history logging).
3. Build command timeline with exact timestamps.
4. Cross-check with registry modifications and process creation records.
5. Record each finding with: command/key/function + source pointer.

### Quality checks

- Verify command and timestamp from at least one additional source when possible.
- Distinguish “executed command” from “string present in script text”.

## 3) Registry-centric persistence and file-association abuse

Use when startup, shell replacement, or extension-handler abuse is suspected.

- Inspect user hive (`NTUSER.DAT`) for `Run/RunOnce`, shell overrides, logon shell abuse.
- Inspect `UsrClass.dat`/HKCR user scope for extension handler hijacks.
- Track handler command chains (`mshta`, `powershell`, script interpreters).
- Correlate registry change with first spawned process and its parent.

## 4) MFT-focused triage

Use when only `$MFT` or NTFS metadata is provided.

1. Parse MFT into structured table.
2. Filter by:
   - `InUse` false (deleted)
   - hidden/system flags
   - copied/renamed indicators
   - record number pivots
3. Compare create vs modify times to detect post-creation edits.
4. Produce a concise timeline with affected filenames and entry IDs.

## 5) PCAP extraction workflow

### Protocol-first pivots

- LDAP/Kerberos: account enumeration, DN discovery, AD structure leakage
- SMTP: chunked/exfil email flows, attachment/password reuse patterns
- HTTP/Nexus/API traffic: auth headers, endpoint usage, user creation, binary/JAR retrieval
- Custom encrypted channels: infer framing first, then decode/decrypt if key material is recoverable

### Procedure

1. Enumerate unique endpoints/URIs/commands.
2. Reconstruct chronological request-response sequence.
3. Extract credentials, versions, objects, and commands directly from payloads.
4. If encryption is custom, recover algorithm/keys from dropped binary/script and replay decryption offline.

## 6) API trace → injection reconstruction

Use with API monitor-like traces when binary or memory visibility is limited.

1. Identify process discovery APIs (snapshot/enumeration).
2. Identify target process open/handle acquisition.
3. Identify remote allocation/write APIs.
4. Identify remote execution trigger APIs.
5. Map this chain to known injection families and confirm target PID/image.

Report as API chain, not just technique label.

## 7) Linux live-response forensic pattern

Use for active backdoors and compromised servers.

- Observe short-interval process spawns and unusual parentage.
- Recover script contents from referenced temporary files.
- Distinguish normal SSH execution lineage from anomalous non-interactive spawn chains.
- Check vulnerable package/library versions against known compromised ranges.
- Mitigation outcome must be verified by absence of recurring malicious artifacts.

## 8) Firmware/OpenWrt forensic pattern

1. Extract firmware and identify filesystem layers (`squashfs` base + writable overlay).
2. Enumerate init/rc scripts and service symlinks for unauthorized startup entries.
3. Inspect custom binaries/scripts launched by boot services.
4. Separate static backdoor config from periodic fetch/execute behavior.
5. Where architecture-specific binaries are present, choose reverse vs emulation based on objective/time.

## 9) Memory-only and hibernation cases

- For hibernation artifacts, convert to analyzable memory form before standard plugin workflow.
- Build process/sockets/modules baseline first.
- Prioritize hidden/injected/module-anomaly indicators.
- Dump only hypothesis-linked regions/processes to keep chain-of-evidence clean.

## 10) Reporting template for objective-driven forensics

For each answer include:

- **Answer:** exact value
- **Artifact:** file/log/plugin output and location
- **Evidence pointer:** timestamp, record id, stream id, inode/entry id, or offset
- **Confidence:** direct / corroborated / inferred
- **Notes:** decoding/normalization steps if any

This format prevents over-interpretation and keeps findings reproducible.
