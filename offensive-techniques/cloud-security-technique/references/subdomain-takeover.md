# Subdomain Takeover

## Purpose

Discover and validate dangling DNS records that could allow an attacker to claim a subdomain and serve content under the target's origin.

## When to load this reference

- Bug bounty or pentest scope includes subdomain takeover.
- Need to enumerate and validate takeover candidates.
- Need to distinguish between vulnerable and non-vulnerable states.

## Boundary

- **Subdomain enumeration**: `recon-technique` (passive + active discovery).
- **Tool skills**: `offensive-tools/recon/subfinder/`, `offensive-tools/recon/dnsx/`, `offensive-tools/vuln-scanners/nuclei/`.

## Authorization gate

1. Confirm scope (root domains, wildcard scope rules).
2. Confirm whether the program permits claiming takeover-vulnerable resources for PoC (most prefer report-only).
3. Refuse to claim resources unless explicitly authorized in writing.

---

## 1. Enumeration

Combine passive and active sources:

```bash
# Passive
subfinder -d <domain> -all -silent -o passive.txt
amass enum -passive -d <domain> -o amass.txt
curl -s "https://crt.sh/?q=%25.<domain>&output=json" | jq -r '.[].name_value' | sort -u

# Active brute force (rate-limited)
puredns bruteforce wordlist.txt <domain> -r resolvers.txt -l 100

# Merge, dedupe, resolve
sort -u all_subs.txt | dnsx -a -cname -resp -silent -o resolved.txt
```

## 2. Fingerprinting

Look at CNAME targets. Common takeover-vulnerable patterns:

| CNAME contains | Service | Fingerprint |
|----------------|---------|-------------|
| `s3.amazonaws.com`, `s3-website-*` | AWS S3 | `NoSuchBucket` |
| `github.io` | GitHub Pages | "There isn't a GitHub Pages site here" |
| `herokuapp.com`, `herokudns.com` | Heroku | "No such app" |
| `azurewebsites.net`, `cloudapp.net` | Azure | "Web App not found" |
| `cloudfront.net` | CloudFront | "Bad request: ERROR" |
| `fastly.net` | Fastly | "Fastly error: unknown domain" |
| `shopify.com`, `myshopify.com` | Shopify | "Sorry, this shop is currently unavailable" |
| `unbouncepages.com` | Unbounce | "The requested URL was not found" |
| `pantheonsite.io` | Pantheon | "The gods are wise..." |
| `tumblr.com` | Tumblr | "Whatever you were looking for doesn't currently exist" |
| `wordpress.com` | WordPress | "Do you want to register..." |
| `surge.sh` | Surge | "project not found" |
| `bitbucket.io` | Bitbucket | "Repository not found" |

## 3. Automated validation

```bash
# subjack
subjack -w resolved.txt -t 50 -timeout 30 -ssl -c fingerprints.json -v

# nuclei takeover templates
nuclei -l live_subs.txt -t http/takeovers/ -rl 50

# nuclei DNS templates for dangling records
nuclei -l all_subs.txt -t dns/ -rl 50
```

## 4. Validation rules

- Confirm the CNAME resolves to a deprovisioned service.
- Verify the service's specific error page/fingerprint.
- Do NOT claim the resource unless explicitly authorized.
- Document: subdomain, CNAME target, service type, fingerprint evidence.
