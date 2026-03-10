---
name: gitleaks
description: "Detect hardcoded secrets (API keys, tokens, credentials) in git repos and files. Use when auditing source code, CI pipelines, or commit history for leaked secrets in red-team or pre-engagement recon."
license: MIT
compatibility: "Go binary; Linux/macOS/Windows; github.com/gitleaks/gitleaks"
metadata:
  author: AeonDave
  version: "1.0"
---

# Gitleaks

Detect hardcoded secrets in git repos, files, and CI pipelines.

## Quick Start

```bash
# Scan current git repo
gitleaks detect --source . -v

# Scan a remote repo
gitleaks detect --source https://github.com/org/repo

# Scan specific path (non-git)
gitleaks detect --source /path/to/dir --no-git

# Generate report
gitleaks detect --source . -r report.json -f json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `detect` | Scan for secrets |
| `protect` | Pre-commit hook mode |
| `--source PATH` | Target path or URL |
| `--no-git` | Scan filesystem (not git history) |
| `-r FILE` | Report output file |
| `-f FORMAT` | Output format (json/csv/sarif) |
| `-v` | Verbose |
| `--config FILE` | Custom rules config |
| `--branch NAME` | Scan specific branch |
| `--log-opts` | Git log options (e.g. `--all`) |

## Common Workflows

**Full history scan:**
```bash
gitleaks detect --source . --log-opts="--all" -r leaks.json -f json
```

**CI pipeline integration (fail on leak):**
```bash
gitleaks detect --source . --exit-code 1
```

**Custom rule for internal tokens:**
```toml
# .gitleaks.toml
[[rules]]
id = "internal-api-key"
regex = '''MYAPP_[A-Z0-9]{32}'''
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Custom rule examples and CI config |
