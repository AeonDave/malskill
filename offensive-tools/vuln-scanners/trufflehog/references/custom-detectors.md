# trufflehog — Custom Detectors, Config & Scanning Strategy

## Custom Detector Config (YAML)

```yaml
# config.yaml
detectors:
  - name: MyAppToken
    keywords:
      - myapp
      - myapp_token
    regex:
      myapp_token: 'myapp_[a-zA-Z0-9]{32}'
    entropy: 3.5
    exclude_words:
      - example
      - placeholder
      - changeme
    verify:
      - endpoint: https://api.myapp.com/auth/verify
        headers:
          - "Content-Type: application/json"
        unsafe: true   # Skip TLS verification for internal endpoints
```

```bash
# Use custom config
trufflehog filesystem /path/to/scan --config=config.yaml
trufflehog git file://. --config=config.yaml --only-verified
```

## Config Fields

| Field | Purpose |
|-------|---------|
| `name` | Detector display name |
| `keywords` | Any match triggers regex scan (fast pre-filter) |
| `regex` | Named patterns (RE2 syntax — no lookaheads) |
| `entropy` | Minimum Shannon entropy (3.0–4.5, default 3.5) |
| `exclude_words` | Strings that disqualify a match (false positive reduction) |
| `verify.endpoint` | POST endpoint — 200 response = verified |
| `verify.headers` | Request headers for verification |
| `unsafe` | Skip TLS verification for endpoint |

## Verification Flow

trufflehog POSTs JSON with regex captures to the endpoint:
```json
{"myapp_token": "myapp_abc123xyz..."}
```
- 200 response → secret marked `Verified`
- Non-200 → `Unverified`
- Network error → `Unknown`

## Path Filtering

```bash
# exclude.txt (newline-separated regex):
# vendor/
# .*\.lock$
# .*test.*
# .*\.min\.js$

trufflehog git file://. \
    --exclude-paths=exclude.txt \
    --exclude-globs="*.log,*.tmp,node_modules/*,vendor/*" \
    --only-verified
```

## Detector Filtering

```bash
# Only scan for AWS and GitHub secrets
trufflehog git file://. --include-detectors=aws,github --only-verified

# Exclude low-signal detectors
trufflehog git file://. --exclude-detectors=generic,entropy --only-verified

# List available detector names (check help output)
trufflehog --help
```

## Result Type Strategy

| Use Case | Flag |
|----------|------|
| CI/CD gate (block on real threats) | `--only-verified --fail` |
| Audit (see all with context) | `--results=verified,unknown` |
| Fast pattern scan (no API calls) | `--no-verification` |
| Thorough review (all matches) | `--results=verified,unverified,unknown` |

## CI/CD Patterns

```bash
# GitHub Actions — block on verified secrets
trufflehog git file://. \
    --since-commit "$GITHUB_EVENT_BEFORE" \
    --only-verified --fail

# GitLab CI — scan delta
trufflehog git file://. \
    --since-commit "${CI_COMMIT_BEFORE_SHA}" \
    --only-verified --fail

# Full repo audit (weekly cron job)
trufflehog git file://. \
    --max-depth=unlimited \
    --only-verified \
    --json > /tmp/secrets-audit-$(date +%Y%m%d).json
```

## Multi-Environment Scanning

```bash
# GitHub entire organization
trufflehog github \
    --org=MyOrg \
    --token=$GITHUB_TOKEN \
    --include-members \
    --include-wikis \
    --issue-comments --pr-comments \
    --only-verified --json

# Docker image layers
trufflehog docker --image nginx:latest --only-verified

# S3 bucket
trufflehog s3 --bucket my-data-bucket --only-verified

# Chained encoded secrets (base64 in base64)
trufflehog filesystem . --max-decode-depth=3 --only-verified
```

## Performance Tuning

```bash
# Increase concurrency (default = CPU count)
trufflehog git file://. --concurrency=16 --only-verified

# Limit depth for CI speed
trufflehog git file://. --max-depth=100 --only-verified

# Exclude large generated files
trufflehog git file://. \
    --exclude-globs="*.min.js,*.lock,dist/*,build/*" \
    --only-verified
```

## trufflehog vs gitleaks

| | trufflehog | gitleaks |
|-|------------|----------|
| Verification | Yes (live API) | No (pattern only) |
| Speed | Slower | Very fast |
| Scope | Git + S3 + Docker + cloud | Git + dirs |
| Pre-commit | Heavy | Ideal |
| False positives | Low (verification filters) | Higher |
| Custom rules | YAML config | TOML config |

**Recommended layered strategy:**
```
Pre-commit:    gitleaks --staged          → fast block at commit
CI/CD PR:      trufflehog --only-verified → verified-only gate
Weekly audit:  trufflehog --max-depth=0   → full history verification
Cloud scan:    trufflehog s3/docker/gcs   → multi-environment coverage
```
