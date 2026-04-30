---
name: volatility3
description: "Volatility 3: open-source memory forensics framework. Use when investigating live-memory artifacts such as running processes, injected code, credentials residue, persistence, and malware behavior from RAM images."
license: VSL-1.0
compatibility: "Python-based; Linux/macOS/Windows analysis host. github.com/volatilityfoundation/volatility3"
metadata:
  author: AeonDave
  version: "1.0"
---

# Volatility 3

Memory-forensics framework for deep volatile artifact analysis.

## Quick Start

```bash
# list plugin families
python3 vol.py --help

# basic process listing
python3 vol.py -f memdump.raw windows.pslist

# process tree
python3 vol.py -f memdump.raw windows.pstree

# account hash extraction (when applicable)
python3 vol.py -f memdump.raw windows.hashdump
```

## Investigation Flow

1. Confirm image provenance (acquisition tool/time/source).
2. Run baseline process plugins (`pslist`, `pstree`).
3. Pivot into suspicious processes/modules/handles/network artifacts.
4. Correlate memory findings with disk/network timelines.
5. Export structured findings with plugin outputs preserved.

## Practical Tips

- Run broad baseline plugins first; avoid tunnel vision on one IOC.
- Keep raw command outputs as evidence attachments.
- Treat plugin output as leads; corroborate before conclusions.

## Resources

| File | When to load |
|------|--------------|
| `references/windows-memory-triage-flow.md` | Plugin sequencing, pivots, and common DFIR triage shortcuts |
