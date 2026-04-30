---
name: capa
description: "Mandiant capa: capability detection for executables and sandbox reports. Use to quickly infer what malware can do (persistence, C2, discovery, etc.) and prioritize reverse-engineering effort during forensic triage."
license: Apache-2.0
compatibility: "Windows/Linux/macOS; standalone binaries and Python package. github.com/mandiant/capa"
metadata:
  author: AeonDave
  version: "1.0"
---

# capa

Behavior/capability inference engine for malware triage.

## Quick Start

```bash
# static capability detection
capa suspicious.exe

# verbose evidence locations
capa -vv suspicious.exe

# run against sandbox report (dynamic capa)
capa report.json
```

## Forensic Workflow

1. Run capa on suspicious binary/report.
2. Identify high-impact capabilities (persistence, credential access, exfil).
3. Use `-vv` output to locate evidence in code regions.
4. Prioritize RE/dynamic analysis on highest-risk capabilities.
5. Correlate capability claims with endpoint/network evidence.

## Practical Tips

- Treat capa output as prioritization signal, not final attribution.
- If sample looks packed/obfuscated, prefer unpacking or dynamic report analysis.
- Keep ATT&CK/MBC mapping from output for report consistency.

## Resources

| File | When to load |
|------|--------------|
| `references/capability-driven-triage.md` | Capability interpretation, confidence checks, and RE pivot strategy |
