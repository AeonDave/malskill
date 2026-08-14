# Windows execution indicators

## Purpose

Correlate Windows artifacts that show what executed, when it likely executed, and which user or process context was involved.

## Table of contents

- [Core artifact set](#core-artifact-set)
- [Triage workflow](#triage-workflow)
- [LNK analysis cues](#lnk-analysis-cues)
- [Jump List analysis cues](#jump-list-analysis-cues)
- [Prefetch interpretation](#prefetch-interpretation)
- [Windows execution correlation edge cases](#windows-execution-correlation-edge-cases)
- [Timeline synthesis](#timeline-synthesis)
- [SAM `F` LastLogon caveat](#sam-f-lastlogon-caveat)
- [Common pitfalls](#common-pitfalls)

## Core artifact set

| Artifact | Typical location | What it proves |
|---|---|---|
| Prefetch | `C:\Windows\Prefetch\*.pf` | Program execution, run count, last run times, referenced files |
| LNK shortcuts | `%APPDATA%\Microsoft\Windows\Recent`, desktop, downloads | File target, volume serial, timestamps, working directory, user interaction |
| Jump Lists | `%APPDATA%\Microsoft\Windows\Recent\AutomaticDestinations` and `CustomDestinations` | Recent files opened by application, user activity sequence |
| AmCache | `C:\Windows\AppCompat\Programs\Amcache.hve` | Program metadata, first-seen hints, hashes on newer systems |
| ShimCache | SYSTEM hive AppCompatCache | Program path presence and execution-adjacent evidence |
| SRUM | `C:\Windows\System32\sru\SRUDB.dat` | Network/app resource usage by executable and time |
| UserAssist | NTUSER.DAT | GUI program execution by user |
| BAM/DAM | SYSTEM hive `Services\bam\State\UserSettings\<SID>` and `Services\dam\State\UserSettings\<SID>` (Win10 1709+/Win11) | Per-SID last-run time for executables, including background/CLI processes that skip UserAssist |
| ActivitiesCache.db | `%USERPROFILE%\AppData\Local\ConnectedDevicesPlatform\L.<user>\ActivitiesCache.db` | Windows Timeline: apps launched, files opened, focus intervals (opt-in / disabled by default on Win11 22H2+) |
| Run keys/tasks/services | Registry, TaskCache, service registry | Persistence or auto-start execution |
| PowerShell logs | EVTX 4103/4104, PSReadLine | Script content and operator commands |

No single artifact is perfect. Treat each as a signal and corroborate before claiming execution.

## Triage workflow

1. Normalize timezone and host clock offset.
2. Build a candidate executable list from downloads, temp paths, startup locations, and alert paths.
3. Check Prefetch and UserAssist for execution signals.
4. Check LNK and Jump Lists for user interaction and opened documents.
5. Check AmCache/ShimCache for presence and first-seen context.
6. Correlate with EVTX process creation, service/task creation, and PowerShell logs.
7. Tie to network evidence through SRUM, firewall logs, Zeek, or PCAP.

## LNK analysis cues

Useful fields:

- Target path and arguments.
- Working directory.
- Icon path and description.
- MAC timestamps embedded in the shortcut.
- Volume serial and machine identifier.
- Relative path and network path fields.

Interpretation patterns:

- LNK in Recent pointing to a payload in Downloads: user interaction likely.
- LNK with remote target: possible lure or network share execution.
- Icon path mismatch: possible masquerading.
- Shortcut arguments invoking script interpreters: execution chain indicator.

## Jump List analysis cues

- AutomaticDestinations are OLE compound files keyed by application AppID.
- Entries often reveal recently opened files even after deletion.
- Correlate entry timestamps with LNK and Prefetch.
- High-value AppIDs: Office, browsers, archive tools, PDF readers, script editors, RDP clients.

## Prefetch interpretation

Prefetch can show:

- Executable name and path references.
- Run count.
- Last execution times.
- DLLs and files touched during startup.

Caveats:

- Disabled on some servers.
- File presence is not guaranteed after cleanup.
- Program name collisions require path and hash corroboration.
- Prefetch last-run is a launch timestamp, not a process-exit timestamp. Likewise, a USN write to the corresponding `.pf` is Prefetch trace maintenance; use process telemetry or the remote side of a session to establish termination.

## Windows execution correlation edge cases

### Recovering raw UTF-16 Sysmon EVTX slack

An EVTX parser can yield no allocated record for an important Sysmon event even though the file still contains readable UTF-16 strings in record slack or overwritten/adjacent data. Use this only as a recovery pivot:

1. Parse allocated records first and preserve parser errors, skipped-record counts, and event record IDs.
2. If an expected path, timestamp, or command is absent, scan the EVTX read-only for both UTF-16LE alignments. `strings -el <sysmon.evtx>` or a bounded byte scanner can locate paths, hashes, timestamps, and commands.
3. Keep the raw byte offset and the surrounding provider/channel, event ID marker, timestamp, image, and command fields. A string hit alone is not a complete event.
4. Interpret fields only when the Sysmon schema order is intact: Event 1 (`Image`, `CommandLine`), Event 7 (`ImageLoaded`, PE metadata), and Event 11 (`TargetFilename`). Corroborate the recovered hit with a second artifact before reporting execution.
5. Never execute a recovered image or script. Store decoded strings and queries under the case workspace, not beside the evidence.

Raw slack may contain older or neighboring records, so do not infer record order solely from byte offset. Treat the offset as a reproducibility pointer and report the recovered field sequence plus its corroborating artifact.

### USN native attributes and MFT parent resolution

USN `$J` `FILE_CREATE` (`0x100`) is a change reason, not a type assertion. Parse the USN `FileAttributes` bitmask and resolve both the file reference and parent reference through `$MFT`:

- USN `FILE_ATTRIBUTE_DIRECTORY` (`0x10`) is the native directory attribute.
- An NTFS MFT record with header flags `0x01` is an in-use file; `0x03` is an in-use directory (`0x02` adds the directory bit).
- Resolve the parent using the full MFT file reference, including its sequence number, then choose the Win32 `$FILE_NAME` over a DOS alias where both exist.
- Do not classify an extensionless name as a directory. Confirm the type from USN attributes and MFT flags; a file such as `C:\Windows\<name>` can be an in-use file.

If the MFT snapshot lacks the referenced record or has a reused segment, report the path as unresolved and corroborate with Sysmon Event 11 `TargetFilename`, Prefetch path strings, or another current filesystem source. A resolved parent is stronger than a path guessed from the current directory of a command.

### Prefetch, USN, and Sysmon correlation

Build the execution chain in this order:

1. Use Prefetch for executable identity, last-run times, run count, and referenced paths; retain the volume GUID and hash-bearing filename.
2. Use USN create/extend/delete records to establish when the executable, Prefetch file, staging directory, and persistence artifacts were written. Resolve parent paths with `$MFT` before grouping records.
3. Use Sysmon Event 1 for process and command line, Event 7 for loaded-image PE metadata, and Event 11 for file targets. Use PowerShell 4104 or Security 4688 when script/process content is available.
4. Prefer a direct Sysmon + Prefetch + USN match for high confidence. Treat an MFT creation timestamp as context when the MFT is a stale snapshot or was collected after the activity.
5. Record gaps explicitly: missing AmCache does not disprove execution, and a Prefetch hit does not by itself identify the process parent or prove persistence.

## Timeline synthesis

For each suspected execution, produce:

| Field | Example |
|---|---|
| Time | UTC timestamp with source timezone noted |
| User/context | User SID, profile path, process parent if known |
| Artifact chain | LNK + Prefetch + EVTX 4688 + SRUM |
| Confidence | High/Medium/Low |
| Explanation | What each artifact supports and what remains uncertain |

## SAM `F` LastLogon caveat

Some Windows builds and registry parsers expose an account LastLogon value from `SAM\Domains\Account\Users\<RID>\F`. Treat it as an account-state timestamp, not as standalone proof of an interactive session or the latest Security 4624 event:

- Identify the username/RID from the SAM names mapping before reading the `F` value.
- Convert the parser's FILETIME-derived value to UTC and preserve the hive/source pointer.
- Corroborate with profile creation, User Profile Service, Terminal Services, or Security events when the question asks for an interactive login.
- Do not replace a validated account timestamp with a later service logon merely because it appears later in EVTX record order.

## Common pitfalls

- Treating ShimCache as definitive execution proof.
- Ignoring user context when artifacts are machine-wide.
- Mixing local and UTC timestamps.
- Failing to distinguish file opened from program executed.
- Overlooking deleted payloads that remain visible in LNK or Jump List entries.
