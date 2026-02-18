---
name: scoutsuite
description: "Multi-cloud security auditing tool for AWS, Azure, GCP, and others. Use when assessing cloud misconfigurations, reviewing IAM policies, security groups, storage permissions, and generating audit reports."
license: MIT
compatibility: "Python 3; pip install scoutsuite; Linux/macOS/Windows; github.com/nccgroup/ScoutSuite"
metadata:
  author: AeonDave
  version: "1.0"
---

# ScoutSuite

Multi-cloud security auditor — AWS, Azure, GCP, OCI, Alibaba Cloud.

## Quick Start

```bash
pip install scoutsuite

# AWS (uses default ~/.aws/credentials profile)
scout aws

# Azure
scout azure --cli

# GCP
scout gcp --project PROJECT_ID

# Output in specific dir
scout aws -r ./report-dir
```

## Common Flags

| Flag | Purpose |
|------|---------|
| `aws/azure/gcp/oci` | Cloud provider |
| `--profile NAME` | AWS named profile |
| `--regions us-east-1` | Limit to regions |
| `--services s3,iam` | Limit to services |
| `--skip-services ec2` | Skip services |
| `-r DIR` | Output directory |
| `--no-browser` | Don't open HTML report |
| `--max-workers N` | Parallelism |

## Common Workflows

**Full AWS audit:**
```bash
scout aws --profile pentest-account -r ./aws-report
```

**Azure with MFA:**
```bash
az login
scout azure --cli -r ./azure-report
```

**Open HTML report:**
```bash
# Report auto-opens; or manually:
start ./aws-report/scoutsuite-report/index.html
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Finding categories and remediation guidance |
