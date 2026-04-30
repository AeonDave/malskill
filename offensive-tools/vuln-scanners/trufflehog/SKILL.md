---
name: trufflehog
description: "trufflehog: secrets scanner that finds AND verifies leaked credentials via live API calls. Use when you need to confirm if exposed secrets are still valid, scan beyond git repos (S3, Docker, cloud, CI/CD), or run comprehensive organization-wide audits. 800+ secret types, 700+ with live verification."
license: AGPL-3.0
compatibility: "Linux / macOS / Windows. Download binary from github.com/trufflesecurity/trufflehog/releases or brew install trufflesecurity/trufflehog/trufflehog. Docker: ghcr.io/trufflesecurity/trufflehog."
metadata:
  author: AeonDave
  version: "1.0"
---

# trufflehog

Secrets scanner with live credential verification — finds + validates real active secrets.

## Quick Start

```bash
# Scan local git repo
trufflehog git file://. --only-verified

# Scan GitHub repo
trufflehog git https://github.com/org/repo --only-verified

# Scan filesystem
trufflehog filesystem /path/to/project --only-verified

# JSON output
trufflehog git file://. --only-verified --json
```

## Subcommands (Scan Sources)

| Command | Target |
|---------|--------|
| `trufflehog git <url>` | Git repository (local or remote) |
| `trufflehog github` | GitHub repos / org |
| `trufflehog gitlab` | GitLab repositories |
| `trufflehog filesystem <path>` | Files and directories |
| `trufflehog s3` | AWS S3 buckets |
| `trufflehog docker` | Docker images |
| `trufflehog gcs` | Google Cloud Storage |
| `trufflehog circleci` | CircleCI pipelines |
| `trufflehog jenkins` | Jenkins instances |
| `trufflehog postman` | Postman collections |
| `trufflehog elasticsearch` | Elasticsearch indices |
| `trufflehog stdin` | Read from stdin |

## Core Flags

| Flag | Purpose |
|------|---------|
| `--only-verified` | Output only confirmed-valid secrets (low noise) |
| `--no-verification` | Skip API verification, show all pattern matches |
| `--results <types>` | Filter: `verified,unknown,unverified` (default: all) |
| `--json` | JSON output |
| `--branch <branch>` | Specific branch to scan |
| `--since-commit <sha>` | Scan from commit SHA (CI delta scanning) |
| `--max-depth <n>` | Limit git history depth |
| `--concurrency <n>` | Concurrent workers (default: CPU count) |
| `--max-decode-depth <n>` | Iterative decoding passes (catches base64-encoded secrets) |
| `--include-paths <file>` | File with regex patterns for paths to include |
| `--exclude-paths <file>` | File with regex patterns for paths to exclude |
| `--exclude-globs <globs>` | Comma-separated glob patterns to exclude |
| `--include-detectors <list>` | Enable specific detectors only |
| `--exclude-detectors <list>` | Disable specific detectors |
| `--config <file>` | Custom detector config file |
| `--fail` | Exit non-zero when results found |

## Verification: The Key Differentiator

trufflehog actually tests if secrets work by calling the issuing service API:

| Result | Meaning |
|--------|---------|
| `Verified` | Secret confirmed valid — active, real threat |
| `Unknown` | Verification failed (network error / API unavailable) |
| `Unverified` | Pattern matched but credential invalid/expired |

No data is altered during verification. Only read-only auth checks.

```bash
# CI/CD gate: only verified = real, active secrets
trufflehog git file://. --only-verified --fail
echo $?  # non-zero = live secrets found

# Show verified + unknown (be thorough)
trufflehog git file://. --results=verified,unknown --json

# Skip verification (fast pattern scan only)
trufflehog git file://. --no-verification --json
```

## Common Workflows

```bash
# Scan repo since last CI commit (delta scan)
trufflehog git file://. \
    --since-commit "$CI_COMMIT_BEFORE_SHA" \
    --only-verified --fail

# Scan specific branch
trufflehog git file://. --branch main --only-verified

# Limit to recent 500 commits
trufflehog git file://. --max-depth=500 --only-verified

# Full organization scan (GitHub)
trufflehog github --org=MyOrg \
    --token=$GITHUB_TOKEN \
    --include-members \
    --include-wikis \
    --issue-comments --pr-comments \
    --only-verified --json

# Docker image scan
trufflehog docker --image myapp:latest --only-verified

# S3 bucket scan
trufflehog s3 --bucket my-bucket --only-verified

# Decode base64 / encoded secrets
trufflehog filesystem . --max-decode-depth=3 --only-verified

# Exclude paths
trufflehog git file://. \
    --exclude-paths=exclude.txt \
    --exclude-globs="*.log,*.lock,vendor/*" \
    --only-verified
```

## GitHub Actions

```yaml
name: TruffleHog Secrets Scan
on: [push, pull_request]
jobs:
  trufflehog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: TruffleHog OSS
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD
          extra_args: --only-verified
```

## Output Parsing (JSON)

```bash
trufflehog git file://. --only-verified --json > findings.json

# Key fields in each finding:
# .DetectorName    - type of secret (aws, github, slack, etc.)
# .Verified        - true/false
# .Raw             - redacted secret value
# .SourceMetadata.Data.Git.File   - file path
# .SourceMetadata.Data.Git.Commit - commit SHA
# .SourceMetadata.Data.Git.Email  - author email

# Extract finding summary
cat findings.json | jq '{detector: .DetectorName, file: .SourceMetadata.Data.Git.File, commit: .SourceMetadata.Data.Git.Commit, verified: .Verified}'

# List unique secret types found
cat findings.json | jq -r '.DetectorName' | sort -u

# Only show verified with file+commit context
cat findings.json | jq 'select(.Verified == true) | {type: .DetectorName, file: .SourceMetadata.Data.Git.File, commit: .SourceMetadata.Data.Git.Commit}'
```

## Resources

| File | When to load |
|------|--------------|
| `references/custom-detectors.md` | Custom detector YAML config, verification endpoints, filtering strategy |
