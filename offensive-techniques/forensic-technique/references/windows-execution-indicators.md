# Windows execution indicators

## Purpose

Correlate Windows artifacts that show what executed, when it likely executed, and which user or process context was involved.

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

## Timeline synthesis

For each suspected execution, produce:

| Field | Example |
|---|---|
| Time | UTC timestamp with source timezone noted |
| User/context | User SID, profile path, process parent if known |
| Artifact chain | LNK + Prefetch + EVTX 4688 + SRUM |
| Confidence | High/Medium/Low |
| Explanation | What each artifact supports and what remains uncertain |

## Common pitfalls

- Treating ShimCache as definitive execution proof.
- Ignoring user context when artifacts are machine-wide.
- Mixing local and UTC timestamps.
- Failing to distinguish file opened from program executed.
- Overlooking deleted payloads that remain visible in LNK or Jump List entries.
