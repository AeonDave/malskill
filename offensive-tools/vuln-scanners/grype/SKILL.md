---
name: grype
description: "Auth/lab ref: fast vulnerability scanner for container images, filesystems, SBOMs, and directories."
license: Apache-2.0
compatibility: "Linux / macOS / Windows."
metadata:
  author: AeonDave
  version: "1.0"
---

# grype

Fast vulnerability scanner with composite risk scoring — CVEs in images, code, SBOMs.

## Quick Start

```bash
# Scan Docker image
grype nginx:latest

# Scan directory
grype dir /path/to/project

# Scan SBOM file
grype sbom:sbom.json

# Only show fixable HIGH+
grype nginx:latest --only-fixed -f high
```

## Scan Targets

```bash
grype <image>                    # Docker/OCI image (pulls from registry)
grype dir:<path>                 # Local filesystem/directory
grype sbom:<file>                # SBOM file (SPDX or CycloneDX)
grype docker-archive:<file>      # Saved Docker archive (.tar)
grype registry:<image>           # Force registry source
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-o, --output <fmt>` | Output format: `table` / `json` / `sarif` / `cyclonedx` / `template` |
| `--file <path>` | Write output to file |
| `-f, --fail-on <sev>` | Exit 2 if severity ≥ level: `critical/high/medium/low/negligible` |
| `--only-fixed` | Show only vulns with available fix |
| `--only-notfixed` | Show only unfixed vulns |
| `--ignore-states <states>` | Ignore fix states: `wont-fix,unknown,fixed,not-affected` |
| `-s, --scope <scope>` | Layer scope: `squashed` (default) / `all-layers` |
| `--sort-by <key>` | Sort: `severity` / `epss` / `risk` / `kev` / `package` |
| `--add-cpes-if-none` | Generate CPEs for packages missing them |
| `--by-cve` | Group by CVE instead of vulnerability ID |
| `--platform <os/arch>` | Platform for multi-arch images (`linux/amd64`) |
| `--distro <dist:ver>` | Override distro detection |
| `--vex <file>` | Apply VEX document for result filtering |
| `--show-suppressed` | Display suppressed findings |
| `-q, --quiet` | Suppress logs |
| `-v` / `-vv` | Verbose / debug |
| `-c, --config <file>` | Config file path |

## Database Management

```bash
grype db status          # Show current DB metadata
grype db check           # Check for updates
grype db update          # Download latest DB
grype db list            # Available databases
grype db search CVE-2021-44228  # Query DB for specific CVE
grype db search --package curl  # Find vulns for package
```

## Risk Scoring

grype provides **composite risk score (0.0–10.0)** combining:
- **CVSS** — base severity
- **EPSS** — 30-day exploitation probability (percentile)
- **KEV** — CISA Known Exploited Vulnerabilities catalog status

```bash
# Sort by risk score (highest = most actionable)
grype nginx:latest --sort-by risk

# Sort by EPSS (exploitation likelihood)
grype nginx:latest --sort-by epss

# Sort by KEV status first
grype nginx:latest --sort-by kev
```

## Common Workflows

```bash
# CI gate: fail on HIGH+ unfixed
grype myapp:latest --only-fixed -f high
echo $?   # 0 = clean, 2 = findings at threshold

# JSON report with all details
grype nginx:latest -o json --file vuln_report.json

# SARIF for GitHub Advanced Security
grype myapp:latest -o sarif --file grype.sarif

# Scan with ignore rules
grype myapp:latest -c .grype.yaml

# Scan all image layers (not just squashed)
grype myapp:latest --scope all-layers

# Scan SBOM from syft
syft nginx:latest -o json | grype sbom:- --output json

# Explain a specific CVE
grype explain --id CVE-2021-44228

# Check if image has any KEV-listed vulns
grype myapp:latest --sort-by kev -o table
```

## Output Parsing

```bash
grype nginx:latest -o json --file scan.json

# Extract findings
cat scan.json | jq '.matches[] | {cve: .vulnerability.id, pkg: .artifact.name, severity: .vulnerability.severity, fix: .vulnerability.fix.versions[0]}'

# Count by severity
cat scan.json | jq '[.matches[].vulnerability.severity] | group_by(.) | map({sev: .[0], count: length})'

# Only CRITICAL with fixes
cat scan.json | jq '.matches[] | select(.vulnerability.severity=="Critical" and (.vulnerability.fix.versions | length > 0)) | {cve: .vulnerability.id, pkg: .artifact.name, fix: .vulnerability.fix.versions[0]}'
```

## Resources

| File | When to load |
|------|--------------|
| `references/config-ignore.md` | .grype.yaml ignore rules, registry auth, syft integration, VEX |
