# Identity Fabric Enumeration

Concrete URL/payload reference for SSO/IdP fingerprinting and tenant enumeration. Methodology in `osint-technique/SKILL.md`. All probes here are **read-only** unless flagged "deep mode" (auth-log generating, cap at ~20 attempts/tenant).

---

## 1. Microsoft Entra (Azure AD)

### OIDC metadata + tenant GUID
```
GET https://login.microsoftonline.com/{tenant-or-domain}/.well-known/openid-configuration
```
`issuer` field embeds tenant GUID. Regex:
```regex
\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b
```
Detectability: low (passive).

### getuserrealm.srf — managed vs federated
```
GET https://login.microsoftonline.com/getuserrealm.srf?login=<probe>@<domain>
```
JSON `NameSpaceType`: `Managed` | `Federated` | `Unknown`. Federated also returns `FederationBrandName` + `AuthURL` (upstream IdP).

### Autodiscover v2
```
POST https://autodiscover-s.outlook.com/autodiscover/metadata/json/1
Body: {"Email":"<probe>@<domain>"}
```
Presence of protocol endpoint = tenant member.

### Autodiscover IP correlation (passive M365 confirmation)
Works when MX is wrapped by Mimecast/Proofpoint/Barracuda.
```bash
dig +short A autodiscover.target.example
```
M365 Exchange Online IP ranges (common subset): `40.96.0.0/13`, `52.96.0.0/14`, `13.107.6.152/31`, `13.107.18.10/31`, `40.99.0.0/16`, `40.104.0.0/15`, `52.98.0.0/15`. Full list: https://learn.microsoft.com/en-us/microsoft-365/enterprise/urls-and-ip-address-ranges. Hit in range → `M365_CONFIRMED`.

### GetCredentialType — user enum (deep mode)
```
POST https://login.microsoftonline.com/common/GetCredentialType
Content-Type: application/json
Body: {"username":"<email>","isOtherIdpSupported":true,"checkPhones":false,"isRemoteNGCSupported":true,"isCookieBannerShown":false,"isFidoSupported":true,"originalRequest":"","country":"US","forceotclogin":false,"isExternalFederationDisallowed":false,"isRemoteConnectSupported":false,"federationFlags":0}
```
`IfExistsResult`: `0`=exists, `1`=missing, `5`=exists-federated. Logged in tenant audit. Cap 20.

---

## 2. Okta

Slug regex: `[a-z0-9][a-z0-9-]{1,40}\.okta(?:preview)?\.com`. Probe both `.okta.com` + `.oktapreview.com`.

### OIDC fingerprint
```
GET https://<slug>.okta.com/.well-known/openid-configuration
```

### /api/v1/authn user enum (deep mode)
```
POST https://<slug>.okta.com/api/v1/authn
Body: {"username":"<email>","password":"invalid_for_enum"}
```
- `400 E0000004` → missing (or generic password error).
- `401` + `status: PASSWORD_WARN`|`LOCKED_OUT`|`MFA_REQUIRED` → exists.

Audit-logged per attempt. Cap 20.

---

## 3. ADFS

### Passive fingerprint
```
GET https://{domain}/adfs/idpinitiatedsignon.aspx
```
`200 OK` + `urn:com:microsoft:ADFS:` in HTML → ADFS. Version greppable from resource refs.

### Mex (deep mode)
```
GET https://{domain}/adfs/Services/Trust/mex
```
SOAP federation metadata: endpoints, signing certs, supported claims.

---

## 4. Google Workspace

```
GET https://{domain}/.well-known/openid-configuration
```
Workspace-hosted-domain customers expose discovery; `issuer` = `https://accounts.google.com`. MX → `aspmx.l.google.com` = corroboration.

---

## 5. Generic OIDC fingerprint (Keycloak / Auth0 / Ping / OneLogin / Duo)

Probe `/.well-known/openid-configuration` on every alive subdomain. Map `issuer`:

| Product | `issuer` pattern |
|---|---|
| Auth0 | `https://*.auth0.com` |
| OneLogin | `https://*.onelogin.com` |
| Ping | `https://*.pingone.com`, `https://*.pingidentity.com` |
| Duo | `https://*.duosecurity.com` |
| Keycloak | URL contains `/realms/<realm>` |

---

## 6. AWS account-ID extraction

### S3 bucket region (passive)
```
HEAD https://<known-bucket>.s3.amazonaws.com/
```
Response header `x-amz-bucket-region`.

### ARN regex (any response body)
```regex
arn:aws:[a-z0-9\-]+:[a-z0-9\-]*:([0-9]{12}):
```
Capture group = 12-digit account ID.

### AccountId property
```regex
(?i)["']?account[_\-]?id["']?\s*[:=]\s*["']([0-9]{12})["']
```

### Google OAuth client_id
```regex
\b\d{8,}-[a-z0-9]{10,40}\.apps\.googleusercontent\.com\b
```

### MSAL client_id
```regex
(?i)["']?client[_\-]?id["']?\s*[:=]\s*["']([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})["']
```

### OAuth scope
```regex
(?i)["']?scope["']?\s*[:=]\s*["']([^"']+)["']
```

---

## 7. Microsoft 365 deep enumeration

### Teams federation probe
```bash
curl -sk -m 10 "https://login.microsoftonline.com/${D}/.well-known/openid-configuration" | jq -r '.issuer'
curl -sk -m 10 "https://teams.microsoft.com/api/mt/emea/beta/users/<email>/externalsearchv3"
```

### SharePoint subdomain probe
```bash
STEM=$(echo $D | cut -d. -f1)
for s in "" "-my" "-admin"; do
  curl -sk -m 10 -I "https://${STEM}${s}.sharepoint.com/" -w '%{http_code}\n'
done
```

**Read results correctly:**
- `200` → tenant provisioned (INFO, not anonymous access).
- `200` + redirect to `/sites/<x>/Lists/<y>/AllItems.aspx?guestaccesstoken=...` (via dorks) → HIGH (data exposure).
- `401`/`403` → tenant exists, auth required (INFO).
- `404`/NXDOMAIN → not provisioned at this stem (check CT logs for vanity).

PowerShell variant:
```powershell
$STEM = ($D -split '\.')[0]
foreach ($s in @("","-my","-admin")) {
  try {
    $r = Invoke-WebRequest -Uri "https://${STEM}${s}.sharepoint.com/" -Method Head -UseBasicParsing -TimeoutSec 10
    "${STEM}${s}.sharepoint.com -> HTTP $($r.StatusCode)"
  } catch {
    $c = $_.Exception.Response.StatusCode.value__
    if ($c) { "${STEM}${s}.sharepoint.com -> HTTP $c" }
  }
}
```

### OneDrive personal site
```bash
USER_TOKEN=$(echo "alice@acme.com" | tr '@.' '__')
curl -sk -m 10 -I "https://acme-my.sharepoint.com/personal/${USER_TOKEN}/Documents/" -w '%{http_code}\n'
# 401 = exists; 404 = not provisioned
```

### M365 OAuth client_id discovery in JS
```bash
curl -sk -m 10 "https://app.target/main.js" | \
  grep -oE 'clientId["'\''[:=]+ ?["'\'']?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
```

### Device-code endpoint discovery (passive)
```bash
curl -sk -m 10 "https://login.microsoftonline.com/${D}/v2.0/.well-known/openid-configuration" | jq '.device_authorization_endpoint'
```
Non-null + no tenant restriction → MEDIUM (device-code phishing surface present).

> Device-code **phishing execution** (issuing a real code, sending it to a victim) is social engineering and lives in [phishing-technique](../../phishing-technique/). OSINT scope ends at presence/absence of the endpoint.

### Power Platform / Dynamics URLs
- `*.crm.dynamics.com` (regions: `crm`, `crm2`–`crm15`).
- `*.api.crm.dynamics.com` (Web API).
- `make.powerapps.com`, `flow.microsoft.com` (auth-required dashboards).

### Severity map
| Finding | Severity |
|---|---|
| SharePoint/OneDrive tenant discovered | INFO |
| Anonymous share link discovered | HIGH |
| `device_authorization_endpoint` enabled | MEDIUM |
| Multi-tenant OAuth app with broad Graph scopes | HIGH |

---

## 8. GraphQL field-suggestion enumeration (introspection-disabled)

> **Scope:** OSINT covers passive *recognition* of misconfigured GraphQL surfaces (introspection on/off, suggestion leakage, presence of subscriptions). Active schema reconstruction, alias-batching rate-limit bypass, depth-bomb testing, and authenticated subscription enumeration are recon/web-exploit work — see [web-exploit-technique](../../web-exploit-technique/) and [recon-technique](../../recon-technique/).

When introspection returns `"GraphQL introspection is disabled"`, Apollo + most libs still emit "did you mean" suggestions by default — a single read-only probe is enough to flag the finding.

### Detect
```bash
curl -sk -m 10 -X POST "$T/graphql" -H 'Content-Type: application/json' \
  -d '{"query":"{ __schema { types { name } } }"}' | jq -r '.errors[0].message'
```

### Trigger suggestions
```bash
curl -sk -m 10 -X POST "$T/graphql" -H 'Content-Type: application/json' \
  -d '{"query":"{ usre { id } }"}' | jq -r '.errors[].message'
# "Cannot query field \"usre\" ... Did you mean \"user\", \"users\", \"userById\"?"
```

Iterate over seed wordlist (`SecLists/Discovery/Web-Content/graphql.txt`, clairvoyance defaults). Stop when no new suggestions.

### Tools
- `clairvoyance -w wordlist.txt -o schema.json https://target/graphql` — auto field-suggestion.
- `graphql-cop` — introspection/batching/depth/suggestion audit.
- `InQL` — Burp extension.
- `GraphQL Voyager` — visualize reconstructed schema.

### Other introspection-disabled techniques

**Alias batching** (per-request rate-limit bypass):
```json
{"query":"{ a:user(id:1){name} b:user(id:2){name} c:user(id:3){name} }"}
```
Test 100+ aliases/request.

**Depth bypass:**
```json
{"query":"{ user { friends { friends { friends { friends { id } } } } } }"}
```

**WebSocket subscription enum:**
```bash
wscat -c "wss://target/graphql" -s graphql-ws
> {"type":"connection_init"}
> {"id":"1","type":"start","payload":{"query":"subscription { __schema { types { name } } }"}}
```

**Batched bypass** (some servers process all even if first fails):
```json
[{"query":"{ __schema { types { name } } }"},{"query":"{ user(id:1){name} }"}]
```

### Severity
| Finding | Severity |
|---|---|
| Field-suggestion recovers 50+ fields | MEDIUM `MISCONFIG` |
| Alias batching not rate-limited | MEDIUM |
| Unauth subscription endpoint | MEDIUM |
