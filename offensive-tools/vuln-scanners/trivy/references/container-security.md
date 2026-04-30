# Container Security — Trivy Findings & Hardening Reference

## Docker Image Scanning Workflow

```bash
# Full scan with all findings:
trivy image --severity CRITICAL,HIGH,MEDIUM \
    --scanners vuln,secret,misconfig \
    --format json -o image_scan.json \
    myapp:latest

# Scan before push (CI gate):
trivy image --exit-code 1 \
    --severity CRITICAL,HIGH \
    --ignore-unfixed \
    myapp:latest
```

## Common Misconfigurations

### Dockerfile Issues

| Finding | Risk | Fix |
|---------|------|-----|
| Running as root | Priv escalation | Add `USER nonroot` |
| `ADD` instead of `COPY` | Auto-extraction risks | Use `COPY` |
| `--no-cache` missing | Stale packages | Add `--no-cache` or `rm -rf /var/cache/apt` |
| Secrets in ENV/ARG | Key exposure in layers | Use Docker secrets or env at runtime |
| curl-pipe-bash | Supply chain attack | Verify checksums |
| Latest tag | Uncontrolled updates | Pin to digest |

```dockerfile
# Bad:
FROM ubuntu
RUN curl https://example.com/install.sh | bash
ENV API_KEY=supersecret123
USER root

# Good:
FROM ubuntu:22.04@sha256:abc123...
RUN apt-get update && apt-get install -y --no-install-recommends \
    package && rm -rf /var/lib/apt/lists/*
RUN useradd -r -u 1001 appuser
USER 1001
```

### Kubernetes Misconfigurations

| Finding | Risk | Fix |
|---------|------|-----|
| `privileged: true` | Full host access | Remove |
| `hostPID: true` | Process namespace escape | Remove |
| `hostNetwork: true` | Network namespace bypass | Remove |
| No resource limits | DoS / noisy neighbor | Add `resources.limits` |
| `runAsRoot: true` or unset | Priv escalation | Set `runAsNonRoot: true` |
| `allowPrivilegeEscalation` unset | Escalation risk | Set to `false` |
| `readOnlyRootFilesystem: false` | Container escape | Set to `true` |
| No network policy | Lateral movement | Add NetworkPolicy |
| `hostPath` mounts | Host filesystem access | Use PVC instead |
| `capabilities` not dropped | Excessive kernel access | Drop `ALL`, add only needed |

```yaml
# Hardened pod security context:
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  seccompProfile:
    type: RuntimeDefault
  capabilities:
    drop: ["ALL"]
    add: ["NET_BIND_SERVICE"]  # only if needed
```

## Trivy + Kubernetes Integration

```bash
# Scan entire cluster:
trivy k8s --severity HIGH,CRITICAL --report summary cluster

# Scan specific namespace:
trivy k8s --severity HIGH,CRITICAL -n production

# Scan specific resource:
trivy k8s --severity HIGH,CRITICAL deployment/myapp

# JSON output:
trivy k8s --format json -o k8s_scan.json cluster

# Generate SBOM for cluster:
trivy k8s --format cyclonedx -o cluster_sbom.json cluster
```

## SBOM Generation & Analysis

```bash
# Generate CycloneDX SBOM:
trivy image --format cyclonedx --output sbom.cdx.json nginx:latest

# Generate SPDX SBOM:
trivy image --format spdx-json --output sbom.spdx.json nginx:latest

# Scan SBOM for vulnerabilities:
trivy sbom sbom.cdx.json --severity HIGH,CRITICAL

# Use SBOM for offline scanning:
trivy sbom sbom.cdx.json --offline-scan
```

## Secrets Found in Images

```bash
# Common secrets trivy detects in image layers:
# - AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
# - GITHUB_TOKEN / GH_TOKEN
# - Private RSA/EC keys (-----BEGIN RSA PRIVATE KEY-----)
# - Database connection strings
# - Docker registry credentials

# Scan image for secrets:
trivy image --scanners secret --format json myapp:latest | \
    jq '.Results[] | select(.Secrets != null) | .Secrets[] | {type: .Title, file: .StartLine, match: .Match}'

# Check image history for secrets in ENV:
docker history --no-trunc myapp:latest | grep -i "secret\|password\|key\|token"
```

## Multi-Stage Build Scanning

```bash
# Scan specific stage:
trivy image --platform linux/amd64 myapp:builder
trivy image --platform linux/amd64 myapp:latest

# Compare builder vs runtime image (runtime should have fewer packages):
trivy image --format json myapp:builder | jq '[.Results[].Vulnerabilities[]] | length'
trivy image --format json myapp:latest | jq '[.Results[].Vulnerabilities[]] | length'
```

## CI/CD Pipeline Integration

```yaml
# GitHub Actions complete example:
name: Container Security Scan
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
          ignore-unfixed: true
      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

## Vulnerability Prioritization

```bash
# Focus on: CRITICAL + fixable first
trivy image --severity CRITICAL --ignore-unfixed \
    --format json myapp:latest | \
    jq '.Results[] | .Vulnerabilities[]? | {cve: .VulnerabilityID, pkg: .PkgName, current: .InstalledVersion, fix: .FixedVersion}' | \
    sort -u

# OS-level vs app-level:
trivy image --vuln-type os myapp:latest     # Only OS package CVEs
trivy image --vuln-type library myapp:latest  # Only app dependency CVEs

# Check if base image has known CVEs:
trivy image --vuln-type os ubuntu:20.04
```
