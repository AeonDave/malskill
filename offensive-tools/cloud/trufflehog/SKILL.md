---
name: trufflehog
description: "Find leaked credentials and secrets in git repos, S3 buckets, filesystems, and CI systems using entropy analysis and 700+ detectors. Use when hunting for secrets in large codebases or cloud storage during recon."
license: MIT
compatibility: "Go binary or Docker; Linux/macOS/Windows; github.com/trufflesecurity/trufflehog"
metadata:
  author: AeonDave
  version: "1.0"
---

# TruffleHog

Secret scanner with 700+ detectors — git history, S3, GCS, filesystem, and CI systems.

## Quick Start

```bash
# Docker
docker run --rm trufflesecurity/trufflehog:latest git https://github.com/org/repo

# Binary
trufflehog git https://github.com/org/repo --only-verified

# Local repo
trufflehog git file:///path/to/repo --only-verified

# S3 bucket
trufflehog s3 --bucket=target-bucket
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `git <url>` | Scan git repo |
| `s3` | Scan S3 bucket |
| `filesystem` | Scan local files |
| `--only-verified` | Show only verified secrets |
| `--since-commit SHA` | Scan from commit |
| `--branch NAME` | Scan specific branch |
| `--json` | JSON output |
| `--concurrency N` | Thread count |
| `--include-detectors` | Limit detector types |

## Common Workflows

**Verified secrets only (CI-safe):**
```bash
trufflehog git https://github.com/org/repo --only-verified --json > secrets.json
```

**Full history of internal monorepo:**
```bash
trufflehog git file:///repos/monorepo --json --concurrency 8
```

**S3 audit:**
```bash
trufflehog s3 --bucket internal-assets --only-verified
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Detector list and custom detector config |
