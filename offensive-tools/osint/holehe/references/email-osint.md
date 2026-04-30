# Holehe — Email OSINT Reference

## Email Harvesting Sources

### theHarvester (primary tool)

```bash
theHarvester -d target.com -b google,bing,yahoo,linkedin,hunter -l 500 -f results
# Found emails: results.html / results.xml
```

### Google Dorks for Email Discovery

```
site:target.com email OR "@target.com"
"@target.com" filetype:pdf OR filetype:xlsx OR filetype:csv
"@target.com" site:linkedin.com
"@target.com" -site:target.com        # emails leaked on external sites
```

### GitHub Commit Email Extraction

```bash
# All commits from a repo
curl -s "https://api.github.com/repos/<owner>/<repo>/commits?per_page=100" \
  | jq -r '.[].commit.author.email' | sort -u | grep -v "noreply"

# From user's events
curl -s "https://api.github.com/users/<username>/events" \
  | jq -r '.[].payload.commits[]?.author.email' | sort -u
```

### Hunter.io API

```bash
# Find all emails for a domain
curl "https://api.hunter.io/v2/domain-search?domain=target.com&api_key=<KEY>" \
  | jq '.data.emails[].value'

# Verify a specific email
curl "https://api.hunter.io/v2/email-verifier?email=user@target.com&api_key=<KEY>" \
  | jq '.data.status'
```

### Certificate Transparency (email from SSL certs)

```bash
# Crtsh for subdomains (may contain email in SAN)
curl -s "https://crt.sh/?q=%25@target.com&output=json" | jq '.[].common_name' | sort -u
```

## Breach Lookup APIs

### HaveIBeenPwned

```bash
# Check email (requires API key, $3.50/month)
curl -s "https://haveibeenpwned.com/api/v3/breachedaccount/<email>" \
  -H "hibp-api-key: <KEY>" \
  | jq '.[].Name'

# Check if email in paste
curl -s "https://haveibeenpwned.com/api/v3/pasteaccount/<email>" \
  -H "hibp-api-key: <KEY>"
```

### IntelX (intelligence X)

```bash
# Search API (free tier available)
curl -s "https://2.intelx.io/intelligent/search" \
  -H "x-key: <KEY>" \
  -d '{"term":"target@example.com","buckets":[],"timeout":5,"maxresults":20}' \
  | jq '.id'
```

### Dehashed (paid)

```
https://dehashed.com/search?query=email:target@example.com
# Returns: passwords, hashed passwords, usernames, IPs from breaches
```

## Pivot from Email to Full Profile

```
email found
    ├── holehe → active platforms → check each profile
    ├── HIBP → breach data → leaked passwords → hashcat
    ├── Google dork → leaked docs / directory listings
    ├── GitHub → commit history → username, other email
    ├── theHarvester → other emails @ same domain → colleagues
    └── hunter.io → email pattern → generate new targets
         └── e.g. pattern: firstname.lastname@company.com
             → infer other employee emails from LinkedIn
```

## Email Pattern Generation

```python
# Given: John Doe @ company.com
# Hunter.io reveals pattern: {first}.{last}@company.com

formats = [
    "{f}{last}",        # jdoe
    "{first}.{last}",   # john.doe
    "{first}{last}",    # johndoe
    "{first}_{last}",   # john_doe
    "{f}.{last}",       # j.doe
    "{last}{f}",        # doej
]
```

```bash
# Validate generated emails
for email in john.doe@company.com jdoe@company.com johndoe@company.com; do
  holehe "$email" --only-used --json
done
```

## Useful Free Email OSINT Resources

| Resource | URL | Use |
|----------|-----|-----|
| Hunter.io | hunter.io | Email pattern + verification |
| HIBP | haveibeenpwned.com | Breach lookup |
| Snov.io | snov.io | Email finder by domain |
| Clearbit Connect | clearbit.com | Email lookup + enrichment |
| Epieos | epieos.com | Google/social from email |
