# osv-scanner — Config, Ignore Rules & Strategy

## osv-scanner.toml

Config is **directory-specific** — place it in the directory being scanned.
It does NOT propagate to child directories (create separate configs per subdirectory).

**Override all directory configs:** `osv-scanner scan --config /global/config.toml`

```toml
# osv-scanner.toml

# Ignore specific vulnerability IDs
[[IgnoredVulns]]
id = "GO-2022-0968"
ignoreUntil = "2025-12-31"   # Optional expiry date (YYYY-MM-DD)
reason = "Third-party dep, monitoring for upstream patch"

[[IgnoredVulns]]
id = "GHSA-1234-5678-90ab"
# No expiry = ignored indefinitely (document a reason!)

# Package-level overrides (granular control)
[[PackageOverrides]]
name = "lodash"
version = "4.17.20"
ecosystem = "npm"
ignore = true                        # Skip ALL checks (vuln + license)
effectiveUntil = "2025-06-30"
reason = "Evaluating replacement, tracking separately"

[[PackageOverrides]]
name = "requests"
ecosystem = "PyPI"
vulnerability.ignore = true          # Skip vulnerability scanning only
license.ignore = true                # Skip license checking only

[[PackageOverrides]]
name = "internal-lib"
ecosystem = "npm"
license.override = ["MIT", "0BSD"]   # Override detected license

# Go version override (improves accuracy for Go modules)
GoVersionOverride = "1.21.0"   # Without "go" prefix
```

## PackageOverrides Fields

| Field | Purpose |
|-------|---------|
| `name` | Package name |
| `version` | Specific version (omit = match all versions) |
| `ecosystem` | `npm`, `PyPI`, `Go`, `Maven`, `crates.io`, etc. |
| `group` | Maven group ID |
| `ignore` | Skip all checks (boolean) |
| `vulnerability.ignore` | Skip vulnerability scanning only |
| `license.ignore` | Skip license checking only |
| `license.override` | Specify custom license list |
| `effectiveUntil` | Expiry date `YYYY-MM-DD` |
| `reason` | Documentation string |

## Reachability Analysis

`--experimental-call-analysis` traces vulnerable function calls through the code.
Only flags vulnerabilities where the vulnerable code is actually called.

Reduces false positives significantly for large dependency trees.

Supported: **Go**, **Python**, **Java** (in development)

```bash
# Enable reachability
osv-scanner scan source -r . --experimental-call-analysis

# JSON output includes reachability info
osv-scanner scan source -r . \
    --experimental-call-analysis \
    --format json -o results.json
```

## Multi-lockfile Scanning

```bash
# Explicit lockfiles
osv-scanner scan source \
    -l frontend/package-lock.json \
    -l backend/requirements.txt \
    -l services/auth/go.sum

# Recursive (auto-detect all lockfiles)
osv-scanner scan source -r . --format json

# Recursive with config
osv-scanner scan source -r . --config osv-scanner.toml
```

## Offline Mode

```bash
# Download databases for offline use
osv-scanner scan source --download-offline-databases /tmp/osv-db -r .

# Use cached databases (no network)
osv-scanner scan source --offline-vulnerabilities \
    --download-offline-databases /tmp/osv-db \
    -r .
```

## osv-scanner vs grype vs trivy

| | osv-scanner | grype | trivy |
|-|-------------|-------|-------|
| False positives | Very low | Low | Medium |
| Lockfile support | 19+ formats | Limited | Yes |
| Container scanning | Yes | Yes (primary) | Yes |
| IaC scanning | No | No | Yes |
| Secrets detection | No | No | Yes |
| Risk scoring | Severity | CVSS+EPSS+KEV | Severity |
| Reachability | Yes (experimental) | Via VEX | No |
| PR delta scanning | Yes (GH Action) | No | No |

**Use osv-scanner when:**
- Scanning lockfiles/dependencies (best lockfile coverage)
- Need lowest false positive rate
- Blocking PRs that introduce new vulnerabilities (delta scanning action)
- Need reachability analysis for Go/Python

**Use grype when:**
- Container image scanning with risk prioritization
- Need EPSS/KEV scoring for triage
- VEX document integration

**Use trivy when:**
- Need one tool for everything (containers + secrets + IaC + k8s)
