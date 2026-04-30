# Volatility3 Windows memory triage flow

## Baseline sequence

```bash
python3 vol.py -f mem.raw windows.pslist
python3 vol.py -f mem.raw windows.pstree
python3 vol.py -f mem.raw windows.dlllist
python3 vol.py -f mem.raw windows.cmdline
```

Then expand into targeted plugins based on anomalies.

## Practical pivot logic

- Unknown parent-child chain -> inspect cmdline, loaded modules, handles.
- LSASS/security anomalies -> credential-focused plugins and process memory review.
- Network beacon suspicion -> process + socket correlation plugins.

## Triage tricks

- Capture plugin output to files per plugin for auditability.
- Mark suspicious PIDs early and keep a pivot table (PID, parent, cmdline, start time).
- Compare multiple plugin views before asserting process legitimacy.

## Limitations

- Memory-only view is incomplete without disk/network correlation.
- Some artifacts depend on acquisition quality and OS state.
