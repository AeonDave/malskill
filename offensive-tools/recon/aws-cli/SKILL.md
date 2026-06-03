---
name: aws-cli
description: "Auth/lab ref: AWS CLI v2 for interacting with AWS services from the terminal."
compatibility: "Linux, Windows, macOS; AWS CLI version 2 recommended."
metadata:
  author: AeonDave
  version: "1.0"
---

# AWS CLI

Cloud control-plane access from a shell. Great for enumeration, dangerous for the incautious.

## When to use AWS CLI

Use AWS CLI when you need to:

- confirm who you are in AWS and which account you reached
- enumerate common resources such as S3, EC2, IAM, or Lambda
- script repeatable cloud recon without living in the console
- validate permissions and region/profile assumptions quickly

## Quick Start

```bash
# Confirm version and identity
aws --version
aws sts get-caller-identity

# List S3 buckets and EC2 instances
aws s3 ls
aws ec2 describe-instances --output json
```

## High-Value Workflows

### Identity, profile, and region sanity

```bash
aws sts get-caller-identity --profile default
aws configure list
```

### Core enumeration examples

```bash
aws s3 ls
aws iam list-users
aws ec2 describe-instances --region us-east-1 --output json
aws lambda list-functions --output json
```

### Safer structured output

```bash
aws ec2 describe-instances --query "Reservations[].Instances[].InstanceId" --output text
aws s3api list-buckets --output json
```

## Practical Notes

- Prefer explicit `--profile` and `--region` in notes, scripts, and repeatable workflows.
- Start with read-only enumeration unless the task explicitly requires mutation.
- `s3 ls` and `s3api list-buckets` together usually answer the first bucket-discovery question quickly.
- This skill also covers simple S3 bucket reconnaissance; a separate wrapper-only skill is unnecessary.

## Caveats

- AWS CLI is an API client, not a safety rail; many commands can mutate or destroy resources.
- Missing region/profile context is the classic cause of misleading empty output.
- Version 2 is the supported baseline for current features and docs.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the AWS CLI v2 user guide for install, auth, profile precedence, and service-specific commands.
