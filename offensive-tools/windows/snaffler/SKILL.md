---
name: snaffler
description: "Audit accessible Windows shares and file exposure with Snaffler; choose discovery boundaries, rule configuration, and structured evidence output."
license: MIT
compatibility: "Windows .NET; access is evaluated using the running identity."
metadata:
  author: AeonDave
  version: "1.1"
---

# Snaffler

Separate share visibility from file-content findings. A rule match is a review candidate, not proof of a valid credential or a severity rating.

## Workflow

1. Record the executable version and identity. Use [upstream releases](https://github.com/SnaffCon/Snaffler/releases) and the matching option definitions.
2. Choose host discovery, an explicit host list, or a local directory. Start with share listing when file contents are unnecessary.
3. Keep the results and effective rules together. Review matches before assigning impact.

```powershell
# Share listing only for explicit hosts
.\Snaffler.exe -s -n fileserver1,fileserver2 -a -o shares.log

# Audit a local fixture without computer/share discovery
.\Snaffler.exe -s -i C:\audit-fixture -o findings.log -v data

# TSV is a switch; -o supplies the filename
.\Snaffler.exe -s -n fileserver1 -a -y -o shares.tsv

# Generate the configurable rule/options template
.\Snaffler.exe -z generate
```

## Options that are easy to confuse

| Option | Meaning |
|---|---|
| `-n` | Explicit hosts or a host-list file; disables computer discovery |
| `-i` | Directory input; disables computer/share discovery |
| `-a` | Share listing only; skips file enumeration |
| `-o` / `-s` | Output file / stdout |
| `-t JSON` / `-y` | JSON log format / TSV formatting; select one output format |
| `-r N` | Maximum file size in bytes for content searching |
| `-m DIR` / `-l N` | Copy matched files to DIR / maximum copy size; listing does not require copying |
| `-x N` | Thread count, not exclusions; upstream warns against values below four |
| `-z FILE` | TOML configuration, including rules |

- The color labels reflect rule triage priorities; validate the actual content and exposure.
- Host restriction does not substitute for share/file exclusion rules. Inspect the generated configuration for that job.
- File reads and SMB access are observable; results depend on ACLs, availability, and traversal errors.
- Logs can include matched content. Redact values in reports while preserving path, rule, identity, and evidence location.

Source: [SnaffCon usage and configuration](https://github.com/SnaffCon/Snaffler).
