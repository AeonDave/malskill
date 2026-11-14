---
name: pspy
description: "Observe short-lived Linux processes and filesystem activity without root. Use to correlate scheduled jobs, process arguments, and timestamps."
license: MIT
compatibility: "Linux; upstream releases provide 32-bit and 64-bit x86 binaries. Other architectures require a matching build."
metadata:
  author: AeonDave
  version: "1.0"
---

# pspy

Observe process execution through procfs scans triggered by polling and inotify events. Capture timestamp, UID, PID, and command line; missed events remain possible.

## Workflow

1. Select the correct architecture. `pspy32`/`pspy64` are static; the smaller `s` variants depend on libc. Check the downloaded binary's help.
2. Choose an observation window from the job schedule or reproducer. Start with process output; enable filesystem output only when it answers the question.
3. Save the log, correlate events with the triggering action, and stop after the needed observation.

```bash
./pspy64 --help
./pspy64 -p -i 1000 > process-observations.log

# Process output plus filesystem events; interval is milliseconds
./pspy64 -pf -i 1000

# Recursive watches versus a single directory without its children
./pspy64 -r /var/www -d /tmp
```

| Option | Meaning |
|---|---|
| `-p` | Print process commands; enabled by default |
| `-f` | Print filesystem events; disabled by default |
| `-i N` | Periodic procfs scan interval in milliseconds |
| `-r DIR` | Recursive inotify watch; repeat for multiple roots |
| `-d DIR` | Non-recursive watch; repeat for multiple directories |
| `--debug` | Include normally hidden errors |

## Interpret correctly

- Inotify triggers a scan; it is not an audit record of every execution. Short-lived processes can still be missed.
- Procfs visibility depends on mount settings, namespaces, and permissions. An empty log does not prove inactivity.
- Broad watches consume inotify resources; inspect startup watch lists and errors before expanding them.
- Lower polling intervals increase overhead. Measure whether a shorter interval captures the missing event.
- Keep logs private: command arguments may contain secrets. Record the observation window and visibility limits with the result.

Sources: [upstream usage](https://github.com/DominicBreuker/pspy), [v1.2.1 release](https://github.com/DominicBreuker/pspy/releases/tag/v1.2.1).
