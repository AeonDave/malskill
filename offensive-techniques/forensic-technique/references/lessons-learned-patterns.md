# Lessons learned patterns for forensic investigations

## Purpose

Codify reusable investigation lessons from recurring incident patterns.

Use this reference when you need fast, high-confidence answers from mixed artifacts (EVTX, registry hives, MFT, PCAP, memory, firmware dumps, API traces).

## Contents

1. Objective-to-artifact mapping
2. Windows EVTX and PowerShell
3. Registry persistence
4. MFT triage
5. PCAP extraction
6. API trace reconstruction
7. Linux live response
8. Firmware/OpenWrt
9. Memory and hibernation
10. Cloud-sync SQLite WAL history
11. Native configuration proof
12. Objective-driven reporting

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

## 10) Cloud-sync SQLite WAL history

Use when the live sync database shows only the latest object at a path but the
question depends on an earlier creation or replacement.

1. Preserve and hash the database, `-wal`, and `-shm` as one evidence set; work
   only on copies.
2. Parse the WAL as a 32-byte header followed by 24-byte frame headers and
   page-sized payloads. Accept only the continuous frame chain with matching
   salts and valid checksums.
3. Treat a nonzero database-size field in a frame header as a commit boundary.
   Prefer opening a database copy with a WAL prefix ending at that frame so
   SQLite materializes the snapshot. For raw page replay, write each page at
   `(page_number - 1) * page_size`, truncate to the committed page count, and
   update page 1's big-endian database-size field at bytes 28–31 before query.
4. Track same-path objects by resource ID, eTag/version, size, and hash. A path
   is a logical name; it does not prove that two rows describe one incarnation.
5. Define timestamp semantics before answering "created": local placeholder
   creation, first hydration, server-side change, download receipt, and a later
   same-path replacement are distinct events.
6. Corroborate the selected instant with sync-engine logs and NTFS evidence.
   For OneDrive, a typical remote-add sequence is receipt, realization work
   item, create-file intent, placeholder creation, then hydration. USN
   `FILE_CREATE` independently anchors the local namespace event.

When a OneDrive `.odlgz` stream has an `EBFGONED` wrapper, locate or remove the
wrapper before gzip decoding and supply the collection's `general.keystore`
when required by the parser. A raw decompression failure is not proof that the
log is empty.

## 11) Native configuration proof

Use static bytes and call-site semantics rather than printable-string output
when a recovered executable supplies an endpoint, target list, or ordered
configuration.

- Trace the decoder caller to recover the exact pointer, key, and length.
  Ciphertext may contain NULs and control bytes that ordinary string scanners
  omit.
- Convert RVA/VA to file offsets through the section table. For RIP-relative
  `LEA`, start from the next instruction and then apply any later `ADD`/`SUB`
  adjustment before dereferencing.
- Reproduce integer transforms at their real width. Mask after every
  `NOT`/`ADD`/`SUB`/`XOR`, normalize rotate counts modulo the word size, and
  handle a zero rotate without shifting by the word size. For `ROL32`, set
  `n &= 31`; return `x & 0xffffffff` when `n == 0`, otherwise compute
  `((x << n) | (x >> (32 - n))) & 0xffffffff`. Compare the final value with
  the use site rather than a decompiler literal.
- Decode Windows GUIDs from memory with little-endian `Data1`, `Data2`, and
  `Data3`; the remaining eight bytes retain byte order. Map known-folder GUIDs
  only after this conversion.
- Prove list order from the pointer array and loop stride, not from string or
  GUID placement in the data section. Prove "first endpoint" from call order
  and path construction, not merely from all decoded hosts and paths.

Record the source offsets, arithmetic width, decoded length, and consuming call
for every derived value so another analyst can reproduce it without executing
the sample.

## 12) Reporting template for objective-driven forensics

For each answer include:

- **Answer:** exact value
- **Artifact:** file/log/plugin output and location
- **Evidence pointer:** timestamp, record id, stream id, inode/entry id, or offset
- **Confidence:** direct / corroborated / inferred
- **Notes:** decoding/normalization steps if any

This format prevents over-interpretation and keeps findings reproducible.
