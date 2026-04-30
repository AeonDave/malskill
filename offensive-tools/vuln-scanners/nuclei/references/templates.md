# Nuclei — Templates, Custom Writing & Tag Reference

## Template Directory Structure

```
~/.local/nuclei-templates/
├── cves/                    # CVE-based detections
│   ├── 2021/CVE-2021-44228.yaml
│   └── ...
├── exposed-panels/          # Admin panel discovery
├── exposures/               # Exposed files/configs/tokens
│   ├── configs/
│   ├── files/
│   └── tokens/
├── misconfiguration/        # Misconfigurations
├── default-logins/          # Default credential checks
├── takeovers/               # Subdomain takeover
├── technologies/            # Tech fingerprinting
├── vulnerabilities/         # General vulns
│   ├── wordpress/
│   ├── apache/
│   └── ...
├── network/                 # Network-level (DNS, TCP)
└── http/                    # HTTP-based checks
```

## Tag Reference

### Severity Levels

| Severity | Use Case |
|----------|---------|
| `critical` | RCE, full auth bypass, data exfil |
| `high` | Privilege escalation, stored XSS, SQLi |
| `medium` | Reflected XSS, CSRF, info disclosure |
| `low` | Minor misconfigs, version disclosure |
| `info` | Tech detection, panel discovery |

### Useful Tag Combos

```bash
# Attack surface map (no vulns, just tech/panels)
nuclei -l hosts.txt -tags tech,panel -severity info,low

# Quick wins (high-value, fast templates)
nuclei -l hosts.txt -tags panel,default-login,exposure -severity medium,high,critical

# CVE-focused engagement
nuclei -l hosts.txt -tags cve -severity critical,high,medium

# Full exposure check
nuclei -l hosts.txt -tags exposure,misconfig,takeover

# Injection testing
nuclei -l urls.txt -tags xss,sqli,ssrf,lfi -severity medium,high,critical

# Specific products
nuclei -l hosts.txt -tags wordpress,jira,gitlab,jenkins
```

## Custom Template Structure

```yaml
id: custom-token-exposure

info:
  name: Custom API Token Exposure
  author: yourname
  severity: high
  description: Detects exposed API tokens in response
  tags: exposure,custom

http:
  - method: GET
    path:
      - "{{BaseURL}}/config.js"
      - "{{BaseURL}}/assets/config.json"

    matchers-condition: and
    matchers:
      - type: status
        status:
          - 200

      - type: regex
        regex:
          - "api[_-]?key[\"']?\\s*[:=]\\s*[\"'][a-zA-Z0-9]{20,}"
          - "secret[_-]?key[\"']?\\s*[:=]\\s*[\"'][a-zA-Z0-9]{20,}"

    extractors:
      - type: regex
        regex:
          - "api[_-]?key[\"']?\\s*[:=]\\s*[\"']([a-zA-Z0-9]{20,})[\"']"
        group: 1
```

## Template Variables

| Variable | Value |
|----------|-------|
| `{{BaseURL}}` | Full base URL (`https://target.com`) |
| `{{RootURL}}` | Protocol + host only |
| `{{Host}}` | Hostname |
| `{{Port}}` | Port number |
| `{{Path}}` | URL path |
| `{{Scheme}}` | `http` or `https` |

## Matcher Types

```yaml
matchers:
  # Status code
  - type: status
    status: [200, 201]

  # Word in response body
  - type: word
    words: ["admin panel", "dashboard"]
    condition: or  # or / and

  # Regex
  - type: regex
    regex: ["version [0-9]+\\.[0-9]+"]

  # Response size
  - type: size
    size: [1234, 5678]

  # Binary
  - type: binary
    binary: ["504B0304"]  # ZIP magic bytes

  # DSL expression
  - type: dsl
    dsl:
      - "status_code == 200 && contains(body, 'admin')"
      - "response_time > 5000"  # time-based blind
```

## Extractor Types

```yaml
extractors:
  # Regex with capture group
  - type: regex
    regex: ["version: ([0-9.]+)"]
    group: 1

  # JSON path
  - type: json
    json: [".version", ".build.number"]

  # XPath
  - type: xpath
    xpath: ["//title/text()"]

  # Key-Value
  - type: kval
    kval: ["X-Powered-By", "Server"]
```

## Multi-Step Templates (Flow)

```yaml
http:
  - id: login
    method: POST
    path:
      - "{{BaseURL}}/login"
    body: "user=admin&pass=admin"
    matchers:
      - type: word
        words: ["dashboard"]

  - id: admin-action
    method: GET
    path:
      - "{{BaseURL}}/admin/users"
    headers:
      Cookie: "{{session}}"  # from previous step
```

## Output Processing

```bash
# JSONL output → parse findings
nuclei -l hosts.txt -severity high,critical -jsonl -o findings.jsonl

# Parse
cat findings.jsonl | jq -r '"\(.info.severity|ascii_upcase) \(.info.name) \(.host)"'

# Count by severity
cat findings.jsonl | jq -r '.info.severity' | sort | uniq -c | sort -rn

# Extract only URLs
cat findings.jsonl | jq -r '.matched-at'

# Find RCE/critical only
cat findings.jsonl | jq -r 'select(.info.severity=="critical") | "\(.info.name) → \(.matched-at)"'
```

## Rate Tuning

```bash
# Default: 150 req/s, 25 concurrent templates
nuclei -l hosts.txt -rl 50 -c 10        # Gentle
nuclei -l hosts.txt -rl 500 -c 50       # Aggressive (trusted network)
nuclei -l hosts.txt -rl 25 -c 5 -bs 1  # Stealth (one at a time)
```

## Notable Template Families

| Template | Covers |
|----------|--------|
| `CVE-2021-44228` | Log4Shell |
| `CVE-2021-26855` | ProxyLogon (Exchange) |
| `CVE-2022-1388` | F5 BIG-IP Auth Bypass |
| `CVE-2019-19781` | Citrix ADC Path Traversal |
| `CVE-2021-41773` | Apache Path Traversal |
| `exposed-panels/` | Kibana, Grafana, Jenkins, Jira, GitLab, phpMyAdmin, Adminer |
| `exposures/tokens/` | AWS keys, GitHub tokens, Stripe keys, Google API keys |
| `default-logins/` | Tomcat (tomcat:tomcat), JBoss, Grafana (admin:admin), etc. |
