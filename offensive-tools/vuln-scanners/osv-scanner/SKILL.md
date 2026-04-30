---
name: osv-scanner
description: "osv-scanner: Google's dependency vulnerability scanner using the OSV.dev database (30+ ecosystem sources). Use when scanning lockfiles and dependency manifests for CVEs with minimal false positives. Supports 19+ lockfile formats across 11+ languages. Best choice for PR gates on dependency changes."
license: Apache-2.0
compatibility: "Linux / macOS / Windows. Download binary from github.com/google/osv-scanner/releases or go install github.com/google/osv-scanner/cmd/osv-scanner@latest. brew install osv-scanner."
metadata:
  author: AeonDave
  version: "1.0"
---

# osv-scanner

Google's dependency scanner — lockfiles + SBOMs, minimal false positives.

## Quick Start

```bash
# Scan directory (auto-detect lockfiles)
osv-scanner scan source -r .

# Scan specific lockfile
osv-scanner scan source --lockfile package-lock.json

# Scan container image
osv-scanner scan image nginx:latest

# JSON output
osv-scanner scan source -r . --format json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-l, --lockfile <file>` | Scan specific lockfile |
| `-r, --recursive` | Recursively find lockfiles in directory |
| `--format <fmt>` | Output: `json` / `vertical` / `html` / `sarif` |
| `-o, --output-file <file>` | Save output to file |
| `--serve` | Serve HTML report at localhost:8000 |
| `--experimental-call-analysis` | Reachability analysis (skip unused vuln code) |
| `--all-packages` | Include packages without CVEs in JSON output |
| `--no-resolve` | Disable transitive dependency resolution |
| `--offline-vulnerabilities` | Use cached local DB (no network) |
| `--download-offline-databases <dir>` | Cache DB locally |
| `--licenses` | Check license compliance |
| `--config <file>` | Config file (overrides directory-level configs) |
| `--verbosity <level>` | `info` / `warning` / `error` |

## Supported Lockfiles (19+ formats)

| Language | Files |
|----------|-------|
| Go | `go.mod`, `go.sum` |
| JavaScript | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `bun.lock` |
| Python | `requirements.txt`, `poetry.lock`, `Pipfile.lock`, `pdm.lock`, `pylock.toml`, `uv.lock` |
| Java | `pom.xml`, `gradle.lockfile`, `gradle/verification-metadata.xml` |
| Rust | `Cargo.lock` |
| Ruby | `Gemfile.lock`, `gems.locked` |
| PHP | `composer.lock` |
| .NET | `packages.config`, `packages.lock.json` |
| Dart | `pubspec.lock` |
| Elixir | `mix.lock` |
| Haskell | `cabal.project.freeze`, `stack.yaml.lock` |

## Common Workflows

```bash
# Full project scan (recursive)
osv-scanner scan source -r /path/to/project

# Multiple specific lockfiles
osv-scanner scan source \
    -l package-lock.json \
    -l requirements.txt \
    -l go.sum

# Container image scan
osv-scanner scan image myapp:latest --format json

# Reachability analysis (reduces false positives)
osv-scanner scan source -r . --experimental-call-analysis

# HTML interactive report
osv-scanner scan source -r . --format html --serve

# Offline scan (use cached DB)
osv-scanner scan source -r . --offline-vulnerabilities

# CI gate: fail on any finding
osv-scanner scan source -r . --format sarif -o results.sarif
echo $?   # non-zero = vulnerabilities found

# License compliance check
osv-scanner scan source -r . --licenses --format json
```

## Output Parsing

```bash
osv-scanner scan source -r . --format json -o scan.json

# Extract findings
cat scan.json | jq '.results[].packages[].vulnerabilities[] | {id: .id, package: .packages[0].package.name, severity: .database_specific.severity}'

# Count by ecosystem
cat scan.json | jq '[.results[].packages[] | select(.vulnerabilities | length > 0) | .package.ecosystem] | group_by(.) | map({eco: .[0], count: length})'

# List affected packages
cat scan.json | jq -r '.results[].packages[] | select(.vulnerabilities | length > 0) | "\(.package.name) \(.package.version) (\(.package.ecosystem))"'
```

## GitHub Actions

```yaml
name: OSV Scanner
on:
  pull_request:
  schedule:
    - cron: "0 0 * * 0"  # Weekly full scan

jobs:
  # PR scan: only new vulnerabilities introduced in PR
  scan-pr:
    uses: google/osv-scanner-action/.github/workflows/osv-scanner-reusable-pr.yml@v2
    with:
      scan-args: |-
        --lockfile=./package-lock.json
        --lockfile=./requirements.txt
      fail-on-vuln: true
      upload-sarif: true

  # Scheduled full scan
  scan-full:
    if: github.event_name == 'schedule'
    uses: google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml@v2
    with:
      scan-args: |-
        -r .
      fail-on-vuln: true
```

## Resources

| File | When to load |
|------|--------------|
| `references/config-ignore.md` | osv-scanner.toml config, ignore rules, package overrides, comparison with grype/trivy |
