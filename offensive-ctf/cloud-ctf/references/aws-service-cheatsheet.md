# AWS Service Quick Reference

## Identity and permissions

```bash
aws sts get-caller-identity                        # who am I? (always run first)
aws iam list-attached-user-policies --user-name <u>
aws iam list-user-policies --user-name <u>
aws iam get-user-policy --user-name <u> --policy-name <p>
aws iam list-groups-for-user --user-name <u>
aws iam list-roles

# Enumerate all reachable permissions (blind)
python3 enumerate-iam.py --access-key AK... --secret-key SK... [--session-token T...]
```

## STS / temporary credentials

```bash
# Configure with session token (ASIA keys)
# In ~/.aws/credentials:
# [profile]
# aws_access_key_id = ASIA...
# aws_secret_access_key = ...
# aws_session_token = ...
```

## S3

```bash
aws s3 ls                                          # list all buckets
aws s3 ls s3://<bucket>/                           # list contents
aws s3 ls s3://<bucket>/ --recursive               # recursive listing

# Versioning — always check for deleted objects
aws s3api list-object-versions --bucket <bucket>
aws s3api get-object --bucket <bucket> --key <file> --version-id <vid> <outfile>

# Download file
aws s3 cp s3://<bucket>/<file> .

# Check bucket policy and ACL
aws s3api get-bucket-policy --bucket <bucket>
aws s3api get-bucket-acl --bucket <bucket>
```

## Secrets Manager

```bash
aws secretsmanager list-secrets
aws secretsmanager describe-secret --secret-id <name>
aws secretsmanager get-secret-value --secret-id <name>

# Multiple versions — common in challenges
aws secretsmanager list-secret-version-ids --secret-id <name>
aws secretsmanager get-secret-value --secret-id <name> --version-id <id>
```

## KMS

```bash
aws kms list-keys
aws kms list-aliases
aws kms describe-key --key-id <key-id>

# Decrypt (input must be raw binary, not base64)
aws kms decrypt --ciphertext-blob fileb://./encrypted.bin --key-id <key-id>
# Decode plaintext from response:
echo "<base64>" | base64 -d > plaintext.ps1

# Verify KMS format: file <blob> → "Windows Precompiled iNF"
# Test encryption:
echo test | aws kms encrypt --key-id <key-id> --plaintext fileb:///dev/stdin
```

## EC2 / Snapshots

```bash
aws ec2 describe-instances
aws ec2 describe-instances --query 'Reservations[].Instances[].{ID:InstanceId,IP:PublicIpAddress,Platform:Platform,Role:IamInstanceProfile}'

# Snapshots owned by current account
ACCT=$(aws sts get-caller-identity --query Account --output text)
aws ec2 describe-snapshots --filters Name=owner-id,Values=$ACCT

# Download snapshot with dsnap
pip install dsnap
dsnap list
dsnap get <snap-id>

# Mount image
guestfish -a <snap-id>.img
><fs> run; list-filesystems; mount /dev/sda1 /; ll /
```

## IMDS (from inside EC2)

```bash
# IMDSv1 (direct)
curl http://169.254.169.254/latest/meta-data/
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/<role-name>

# IMDSv2 (requires token first)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
curl -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>
```

## Directory Service (DS) + WorkDocs

```bash
aws ds describe-directories                        # find directory-id

# WorkDocs — enumerate document activity
aws workdocs describe-activities --organization-id <dir-id>
aws workdocs get-document --document-id <doc-id>
# Grab LARGE thumbnail URL and curl it to download as PNG
```

## SSM Parameter Store

```bash
aws ssm describe-parameters
aws ssm get-parameter --name <name>
aws ssm get-parameters-by-path --path / --recursive --with-decryption
```
