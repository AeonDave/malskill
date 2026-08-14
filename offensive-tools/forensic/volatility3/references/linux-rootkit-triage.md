# Linux Kernel-Rootkit Triage

Use this workflow when a Linux memory image shows hidden modules or processes, incomplete diagnostic output, suspicious sockets, kernel taints, or ftrace/tracepoint manipulation.

## Establish trustworthy symbols

1. Hash the memory image and supplied ISF; keep both immutable.
2. Pass `-s` the directory containing the Linux ISF JSON:

```bash
vol -q -s /path/to/symbols -f linux.mem linux.pslist.PsList
```

3. Confirm symbol resolution with two independent views, such as `PsList` and `Lsmod`. Empty output or a plugin exception is a symbol/profile failure until proven otherwise.
4. Capture `vol --version` and `vol -h`; canonical plugin class names change across releases.

## Collect once, filter later

Write each result and stderr to separate files. These views cover the shortest rootkit path:

```bash
vol -q -s "$SYMBOLS" -f "$MEM" linux.pslist.PsList > pslist.tsv 2>pslist.stderr
vol -q -s "$SYMBOLS" -f "$MEM" linux.psaux.PsAux > psaux.tsv 2>psaux.stderr
vol -q -s "$SYMBOLS" -f "$MEM" linux.envars.Envars > envars.tsv 2>envars.stderr
vol -q -s "$SYMBOLS" -f "$MEM" linux.sockstat.Sockstat > sockstat.tsv 2>sockstat.stderr
vol -q -s "$SYMBOLS" -f "$MEM" linux.kmsg.Kmsg > kmsg.tsv 2>kmsg.stderr
vol -q -s "$SYMBOLS" -f "$MEM" linux.lsmod.Lsmod > lsmod.tsv 2>lsmod.stderr
vol -q -s "$SYMBOLS" -f "$MEM" linux.malware.hidden_modules.Hidden_modules > hidden_modules.tsv 2>hidden_modules.stderr
vol -q -s "$SYMBOLS" -f "$MEM" linux.malware.modxview.Modxview > modxview.tsv 2>modxview.stderr
vol -q -s "$SYMBOLS" -f "$MEM" linux.malware.check_modules.Check_modules > check_modules.tsv 2>check_modules.stderr
vol -q -s "$SYMBOLS" -f "$MEM" linux.tracing.tracepoints.CheckTracepoints > tracepoints.tsv 2>tracepoints.stderr
vol -q -s "$SYMBOLS" -f "$MEM" linux.tracing.ftrace.CheckFtrace > ftrace.tsv 2>ftrace.stderr
```

## Interpret module evidence

- Treat `Lsmod` as the linked-list baseline, not a complete inventory.
- A strong hidden-module candidate is `False,False,True` in `Modxview`: absent from procfs/sysfs but present in the memory scan. Corroborate it with `Hidden_modules` and code addresses attributed to the same module.
- Record taints exactly. Out-of-tree and unsigned taints explain provenance; they do not alone prove maliciousness.
- Search `Kmsg` for the module-load record. Its numeric timestamp is seconds since boot, and `Task(<pid>)` identifies the loader even when that process exited before acquisition.

## Attribute hooks correctly

- `CheckTracepoints` identifies the tracepoint, probe address, priority, and owning module.
- `CheckFtrace` maps each ftrace registration to its callback, hooked symbol set, module, and module base.
- Count module-attributed ftrace registrations when asked for installed hooks. Do not count unique callback addresses: one centralized callback can service many registrations.
- A row can name several aliased symbols. Deduplicate only when the question explicitly asks for unique functions rather than registrations.
- Prioritize filesystem/process hiding (`getdents*`), TCP sequence rendering (`tcp4_seq_show`/`tcp6_seq_show`), and packet receive paths (`icmp_rcv`, `tpacket_rcv`) as capability pivots, then confirm ownership by module address.

## Correlate sockets, processes, and environment

- `Sockstat` may show the same socket once per duplicated file descriptor. Deduplicate by `(NetNS, PID, Sock Offset)` before counting sessions.
- Correlate every unusual peer with `PsList`/`PsAux`: parent PID, UID, start time, command line, and process name distinguish a reverse shell from a legitimate service.
- Compare parent and child environments. A control variable present only in a spawned shell is a pivot to UID/EUID, lineage, and command history; it is not proof of privilege escalation by itself.
- Treat an endpoint as C2 only after the socket and process context agree; use PCAP or logs as an additional source when available.

## Quality gate

Report a rootkit finding only when at least two independent structures agree: module cross-view plus hook ownership, kernel log plus module scan, or process/socket correlation. Preserve exact plugin output lines as source pointers.
