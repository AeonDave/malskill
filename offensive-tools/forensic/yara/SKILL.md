---
name: yara
description: "YARA: pattern-matching engine for malware and artifact classification. Use for triage scanning of suspicious files, memory dumps, and extracted payloads with reproducible rules and low-friction automation."
license: BSD-3-Clause
compatibility: "Windows/Linux/macOS CLI + yara-python. github.com/virustotal/yara"
metadata:
  author: AeonDave
  version: "1.0"
---

# YARA

Rule-based detection for forensic triage and malware family classification.

## Quick Start

```bash
# compile/check rules
yara -w rules.yar sample.bin

# recursive scan
yara -r rules.yar evidence_dir/

# print matching strings
yara -s rules.yar suspicious.bin
```

## Practical Forensic Use

- Scan extracted artifacts from Autopsy/TSK workflows.
- Triage dropped payload collections quickly.
- Validate hypotheses with family/behavioral signatures.

## Rule-writing Flow

1. Define objective (family, behavior, artifact class).
2. Add robust strings (avoid over-generic literals).
3. Build strict condition logic.
4. Test against benign + malicious corpus.
5. Tune false positives before operational use.

## Resources

| File | When to load |
|------|--------------|
| `references/rule-quality-and-triage-flow.md` | Rule hygiene, false-positive control, and deployment patterns |
