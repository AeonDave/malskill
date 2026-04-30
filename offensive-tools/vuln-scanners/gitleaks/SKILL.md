---
name: gitleaks
description: "gitleaks: fast git secrets scanner detecting hardcoded credentials, API keys, tokens, and passwords in git repositories, directories, and stdin. Use when auditing code for leaked secrets, blocking commits via pre-commit hooks, or integrating secret detection into CI/CD pipelines. Regex + entropy based, highly configurable."
license: MIT
compatibility: "Linux / macOS / Windows. Download binary from github.com/gitleaks/gitleaks/releases or brew install gitleaks. Docker: ghcr.io/gitleaks/gitleaks. Pre-installed on many CI runners."
metadata:
  author: AeonDave
  version: "1.0"
---

# gitleaks

Fast git secrets scanner — API keys, tokens, passwords in repos and files.

## Quick Start

```bash
# Scan git repository (full history)
gitleaks git /path/to/repo

# Scan directory (no git history)
gitleaks dir /path/to/project

# Scan from stdin
cat file.txt | gitleaks stdin

# With report output
gitleaks git . --report-path results.json
```

## Subcommands

| Command | Target |
|---------|--------|
| `gitleaks git <path>` | Git repository + full history |
| `gitleaks dir <path>` | Directory or file (no git) |
| `gitleaks stdin` | Read from stdin |
| `gitleaks version` | Show version |

## Core Flags

| Flag | Purpose |
|------|---------|
| `-c, --config <file>` | Path to `.gitleaks.toml` config |
| `-b, --baseline-path <file>` | Baseline of known issues to ignore |
| `-f, --report-format <fmt>` | Output format: `json` / `csv` / `sarif` / `junit` |
| `--report-path <file>` | Save report to file |
| `-l, --log-level <lvl>` | Log level: debug / info / warn / error |
| `--exit-code <n>` | Exit code when leaks found (default 1) |
| `--no-banner` | Suppress banner |
| `--redact` | Redact secrets in output |
| `--max-target-megabytes <n>` | Skip files larger than N MB |
| `--max-decode-depth <n>` | Decode encoded text (base64 etc.) up to N levels |
| `--max-archive-depth <n>` | Extract and scan archives up to N levels deep |
| `--no-git` | Treat git repo as plain directory |
| `--follow-symlinks` | Follow symbolic links |
| `--log-opts <opts>` | Pass options to `git log` (e.g. commit ranges, branches) |
| `--staged` | Scan staged changes (for pre-commit use) |
| `-v, --verbose` | Show full findings |

## Scanning Patterns

```bash
# Full history scan
gitleaks git . -v

# Specific commit range
gitleaks git . --log-opts="commitA..commitB"

# Last N commits only
gitleaks git . --log-opts="-n 500"

# Specific branch
gitleaks git . --log-opts="feature-branch"

# Since a date
gitleaks git . --log-opts="--since='6 months ago'"

# CI: scan only new commits in PR
gitleaks git . --log-opts="${CI_COMMIT_BEFORE_SHA}..${CI_COMMIT_SHA}"

# Scan staged changes (pre-commit)
gitleaks git . --staged

# Directory scan (source code, no git history)
gitleaks dir /path/to/project -v

# Scan with custom config
gitleaks git . -c .gitleaks.toml --report-path findings.json

# Decode base64 and scan archives
gitleaks dir . --max-decode-depth=3 --max-archive-depth=2
```

## Output Formats

```bash
# JSON (richest output)
gitleaks git . --report-format json --report-path report.json

# SARIF (GitHub Advanced Security)
gitleaks git . --report-format sarif --report-path report.sarif

# CSV
gitleaks git . --report-format csv --report-path report.csv

# JUnit XML (CI test reporting)
gitleaks git . --report-format junit --report-path report.xml

# Parse JSON findings:
cat report.json | jq '.[] | {rule: .RuleID, file: .File, secret: .Secret, commit: .Commit, line: .StartLine}'

# List unique rules triggered:
cat report.json | jq -r '.[].RuleID' | sort -u

# Count findings by rule:
cat report.json | jq 'group_by(.RuleID) | map({rule: .[0].RuleID, count: length})'
```

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.2
    hooks:
      - id: gitleaks
```

```bash
# Manual hook in .git/hooks/pre-commit:
#!/bin/bash
gitleaks protect --staged --verbose
exit $?

# Bypass hook when needed (e.g., legitimate test data)
SKIP=gitleaks git commit -m "message"
```

## GitHub Actions

```yaml
name: Secrets Scan
on: [push, pull_request]
jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0    # Full history needed
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Common Workflows

```bash
# Full audit of repo history
gitleaks git . -v --report-path secrets_audit.json

# Fast check before push (same as pre-commit)
gitleaks git . --staged -v

# Scan with baseline (ignore known findings)
gitleaks git . --baseline-path known.json

# Create baseline from current findings (to suppress later)
gitleaks git . --report-path known.json
# Use known.json as baseline going forward

# CI one-liner (non-zero exit = findings found)
gitleaks git . --exit-code 1 --no-banner -q
echo $?  # 0 = clean, 1 = secrets found

# Scan without git (plain directory)
gitleaks dir ./src --report-path dir_scan.json
```

## Resources

| File | When to load |
|------|--------------|
| `references/config-rules.md` | Custom rule writing, .gitleaks.toml format, entropy tuning, false positive reduction |
