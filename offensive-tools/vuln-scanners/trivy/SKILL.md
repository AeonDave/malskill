---
name: trivy
description: "Auth/lab ref: broad vulnerability scanner for containers, filesystems, repos, IaC, and SBOMs."
license: Apache-2.0
compatibility: "Linux / macOS / Windows."
metadata:
  author: AeonDave
  version: "1.0"
---

# trivy

Container / code / IaC vulnerability scanner — CVEs, misconfigs, secrets.

## Quick Start

```bash
# Scan Docker image
trivy image nginx:latest

# Scan filesystem
trivy fs /path/to/code

# Scan Git repo
trivy repo https://github.com/org/project
```

## Scan Types

| Command | Target |
|---------|--------|
| `trivy image <image>` | Docker/OCI image |
| `trivy fs <path>` | Local filesystem |
| `trivy repo <url>` | Remote git repository |
| `trivy rootfs <path>` | Root filesystem (extracted container) |
| `trivy config <path>` | IaC / config files (Terraform, k8s, Dockerfile) |
| `trivy sbom <file>` | Analyze SBOM file |
| `trivy k8s` | Kubernetes cluster scan |
| `trivy aws` | AWS account misconfiguration scan |
| `trivy vm <path>` | Virtual machine image scan |

## Core Flags

| Flag | Purpose |
|------|---------|
| `--severity <lvl>` | Filter: UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL |
| `--vuln-type <type>` | os / library (both by default) |
| `--scanners <list>` | vuln,secret,misconfig,license |
| `--ignore-unfixed` | Skip vulns without available fix |
| `--format <fmt>` | table / json / sarif / cyclonedx / spdx / template |
| `--output <file>` | Save output to file |
| `--template <tmpl>` | Custom output template |
| `--timeout <n>` | Timeout (default 5m0s) |
| `--exit-code <n>` | Exit code when vulns found (default 0) |
| `--no-progress` | Disable progress bar |
| `--quiet` | Suppress progress + status |
| `--skip-dirs <dirs>` | Skip specific directories |
| `--skip-files <files>` | Skip specific files |
| `--ignore-policy <file>` | OPA policy file to filter findings |
| `--dependency-tree` | Show package dependency graph |
| `--compliance <spec>` | Compliance check: `docker-cis-1.6.0` / `k8s-cis-1.23` / `aws-cis-1.2` |
| `--include-non-failures` | Show passing checks alongside failures |
| `--list-all-pkgs` | Include all packages even without CVEs |
| `--trivyignore <file>` | File with CVE/AVD IDs to ignore (default .trivyignore) |
| `--db-repository <repo>` | Custom vulnerability DB repository |
| `--cache-dir <dir>` | Cache directory |
| `--clear-cache` | Clear cache |
| `--download-db-only` | Download DB and exit |
| `--offline-scan` | Offline mode (use cached DB) |
| `--token <token>` | Server token (trivy server mode) |
| `--platform <os/arch>` | Scan specific platform image variant |

## Common Workflows

```bash
# Container image scan (high/critical only)
trivy image --severity HIGH,CRITICAL nginx:latest

# Image scan with JSON output
trivy image --format json --output nginx_scan.json nginx:latest

# Show only fixable vulnerabilities
trivy image --ignore-unfixed nginx:latest

# Scan image with secrets detection
trivy image --scanners vuln,secret nginx:latest

# Scan private registry image
trivy image --username admin --password secret registry.company.com/app:v1.0

# Filesystem scan (source code + dependencies)
trivy fs --scanners vuln,secret,misconfig /path/to/project

# Git repository scan
trivy repo --scanners vuln,secret https://github.com/target/repo

# IaC/config scan (Terraform, k8s, Dockerfile)
trivy config ./infrastructure/
trivy config --severity HIGH,CRITICAL k8s/

# SBOM generation
trivy image --format cyclonedx --output sbom.json nginx:latest
trivy image --format spdx-json --output sbom.spdx.json nginx:latest

# Analyze existing SBOM
trivy sbom sbom.json

# Kubernetes cluster scan
trivy k8s --severity HIGH,CRITICAL --report summary cluster

# AWS account misconfiguration scan
trivy aws --severity HIGH,CRITICAL --region us-east-1
trivy aws --service s3,iam,ec2 --severity CRITICAL  # specific services

# Compliance benchmarks (CIS, etc.)
trivy image --compliance docker-cis-1.6.0 nginx:latest
trivy k8s --compliance k8s-cis-1.23 cluster

# VM image scan
trivy vm --severity HIGH,CRITICAL machine.vmdk

# Dependency tree (show package relationships)
trivy image --dependency-tree nginx:latest

# Scan with exit code for CI (fail if HIGH+ found)
trivy image --exit-code 1 --severity HIGH,CRITICAL myapp:latest
echo $?  # non-zero = findings found
```

## Scanners

```bash
# Vulnerability scanning (default)
trivy image --scanners vuln nginx:latest

# Secret scanning
trivy fs --scanners secret .

# Misconfiguration scanning
trivy config --scanners misconfig ./k8s/

# All scanners combined
trivy fs --scanners vuln,secret,misconfig,license .
```

## Secret Detection

```bash
# Secrets trivy finds:
# - AWS access keys / secret keys
# - GitHub tokens
# - Slack tokens
# - Private keys (RSA/DSA/EC)
# - Database URLs with credentials
# - Docker registry credentials
# - Generic API keys and passwords

# Scan filesystem for secrets:
trivy fs --scanners secret --format json -o secrets.json /path/to/project

# Scan image filesystem for secrets:
trivy image --scanners secret --format json myapp:latest

# Custom secret config:
cat > custom-secret-config.yaml << 'EOF'
rules:
  - id: custom-api-key
    category: general
    title: Custom API Key
    severity: HIGH
    regex: 'MYAPI_[A-Z0-9]{32}'
EOF
trivy fs --secret-config custom-secret-config.yaml --scanners secret .
```

## Misconfiguration Detection

```bash
# What trivy checks for misconfigs:
# - Dockerfile: root user, ADD vs COPY, insecure curl-pipe-bash
# - Terraform: public S3 buckets, unrestricted SGs, no encryption
# - Kubernetes: privileged containers, missing resource limits, host PID/network
# - Helm: default values, insecure settings
# - Docker Compose: privileged mode, bind mounts to sensitive paths

trivy config --severity HIGH,CRITICAL ./terraform/
trivy config ./k8s/
trivy config Dockerfile
```

## Output Parsing

```bash
# JSON output structure
trivy image --format json -o scan.json nginx:latest

# Extract CVE list:
cat scan.json | jq '.Results[] | .Vulnerabilities[]? | {cve: .VulnerabilityID, pkg: .PkgName, severity: .Severity, fixed: .FixedVersion}'

# Critical vulns only:
cat scan.json | jq '.Results[] | .Vulnerabilities[]? | select(.Severity == "CRITICAL") | {cve: .VulnerabilityID, pkg: .PkgName}'

# Count by severity:
cat scan.json | jq '[.Results[] | .Vulnerabilities[]? | .Severity] | group_by(.) | map({severity: .[0], count: length})'

# Find vulns with fixes available:
cat scan.json | jq '.Results[] | .Vulnerabilities[]? | select(.FixedVersion != null and .FixedVersion != "") | {cve: .VulnerabilityID, current: .InstalledVersion, fixed: .FixedVersion}'

# SARIF output for GitHub Advanced Security:
trivy image --format sarif -o trivy.sarif myapp:latest
```

## .trivyignore File

```bash
# .trivyignore — suppress specific findings
cat > .trivyignore << 'EOF'
# CVE to ignore (add comment with expiry date)
CVE-2022-1234  # false positive - not exploitable in our config, review 2025-01-01
CVE-2021-5678  # dependency locked by framework, no fix available
EOF

trivy image --trivyignore .trivyignore nginx:latest
```

## CI Integration

```bash
# GitHub Actions:
# - uses: aquasecurity/trivy-action@master
#   with:
#     image-ref: 'myapp:latest'
#     format: 'sarif'
#     output: 'trivy-results.sarif'
#     severity: 'CRITICAL,HIGH'
#     exit-code: '1'
#     ignore-unfixed: true

# GitLab CI:
# container_scan:
#   image: aquasec/trivy:latest
#   script:
#     - trivy image --exit-code 1 --severity HIGH,CRITICAL $CI_REGISTRY_IMAGE:$CI_COMMIT_TAG

# Pre-commit hook:
trivy fs --exit-code 1 --severity CRITICAL --scanners secret .
```

## Resources

| File | When to load |
|------|--------------|
| `references/container-security.md` | Container hardening, Docker security best practices, k8s scanning |
