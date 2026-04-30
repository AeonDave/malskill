# grype — Config, Ignore Rules & Integrations

## .grype.yaml Reference

grype looks for config in order: `./.grype.yaml` → `./.grype/config.yaml` → `~/.grype.yaml` → `$XDG_CONFIG_HOME/grype/config.yaml`

```yaml
# .grype.yaml

# Ignore specific vulnerabilities
ignore:
  - vulnerability: CVE-2021-12345
    fix-state: unknown
    reason: "Not exploitable in our config"
    expiration: 2025-12-31
    package:
      name: libcurl
      version: 7.1.5
      type: deb
      location: /usr/lib/x86_64-linux-gnu/libcurl.so.4

  # Ignore entire fix-state category
  - fix-state: wont-fix

  # Ignore low severity across all packages
  - vulnerability: ".*"
    severity: "Low"

# Fail build threshold
fail-on-severity: high

# Only show fixable
only-fixed: false

# Layer scope
scope: squashed   # or all-layers

# Output
output:
  format: table
  file: ""
  pretty: false

# Database
db:
  auto-update: true
  validate-age: true
  max-allowed-built-age: 120h  # 120 hours before considered stale

# Registry authentication
registry:
  insecure-skip-tls-verify: false
  auth:
    - authority: docker.io
      username: myuser
      password: mypassword
    - authority: registry.company.com
      token: my_token
  ca-cert: /path/to/ca.crt

# Logging
log:
  level: warn   # error, warn, info, debug, trace
  quiet: false
```

## Ignore Rule Fields

| Field | Values |
|-------|--------|
| `vulnerability` | CVE ID or regex pattern |
| `fix-state` | `wont-fix` / `unknown` / `fixed` / `not-affected` |
| `package.name` | Package name |
| `package.version` | Specific version |
| `package.type` | `deb`, `rpm`, `npm`, `python`, `go-module`, etc. |
| `package.location` | File path glob |
| `severity` | `Critical`, `High`, `Medium`, `Low`, `Negligible` |
| `reason` | Free text (metadata only) |
| `expiration` | `YYYY-MM-DD` date |

## VEX Integration

VEX (Vulnerability Exploitability eXchange) documents filter results based on actual exploitability:

```bash
# Apply VEX document
grype myapp:latest --vex vex.json

# VEX status values:
# not_affected   - vulnerable code never invoked (reduces false positives ~80%)
# affected       - actually exploitable
# fixed          - patched version deployed
# under_investigation - still analyzing
```

## syft + grype SBOM Workflow

```bash
# Generate SBOM with syft, scan with grype
syft nginx:latest -o json | grype sbom:- --output json

# Generate SPDX SBOM, then scan
syft myapp:latest -o spdx-json --file sbom.spdx.json
grype sbom:sbom.spdx.json

# CycloneDX
syft myapp:latest -o cyclonedx-json --file sbom.cdx.json
grype sbom:sbom.cdx.json -f high

# Install syft
brew install anchore/syft/syft
# or: curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh
```

## GitHub Actions

```yaml
name: Container Vulnerability Scan
on: [push, pull_request]
jobs:
  grype:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .
      - name: Run Grype scan
        uses: anchore/scan-action@v7
        with:
          image: myapp:${{ github.sha }}
          fail-build: true
          severity-cutoff: high
          output-format: sarif
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
```

## grype vs trivy vs osv-scanner

| | grype | trivy | osv-scanner |
|-|-------|-------|-------------|
| Container scanning | Yes | Yes | No |
| Lockfile scanning | Yes | Yes | Yes (primary) |
| SBOM scanning | Yes | Yes | Via lockfiles |
| IaC misconfigs | No | Yes | No |
| Secrets detection | No | Yes | No |
| Risk scoring | CVSS+EPSS+KEV | Severity | Severity |
| False positives | Low | Medium | Very low |

**Use grype when:** Container CVE scanning with EPSS/KEV risk prioritization, VEX integration
**Use trivy when:** All-in-one (vulns + secrets + IaC + k8s)
**Use osv-scanner when:** Lockfile/dependency scanning with lowest false positive rate
