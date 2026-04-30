---
name: zap
description: "OWASP ZAP: free open-source web application scanner and intercepting proxy. Use for automated DAST scanning in CI/CD pipelines, API security testing (OpenAPI/GraphQL/SOAP), passive/active vulnerability scanning, and headless scanning with Docker. Best free alternative to Burp Suite Pro for automated workflows."
license: Apache-2.0
compatibility: "Linux / macOS / Windows. Java 11+. Docker: zaproxy/zap-stable. Download from zaproxy.org. Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.1"
---

# OWASP ZAP

Free web app scanner — active/passive DAST, API scanning, CI/CD integration.

## Quick Start

```bash
# Docker baseline scan (passive, safe for prod)
docker run --rm zaproxy/zap-stable zap-baseline.py -t https://target.com

# Full active scan
docker run --rm zaproxy/zap-stable zap-full-scan.py -t https://target.com

# API scan (OpenAPI spec)
docker run --rm zaproxy/zap-stable zap-api-scan.py \
    -t https://target.com/openapi.json -f openapi

# Daemon mode
zap.sh -daemon -port 8080 -host 127.0.0.1 -config api.key=MYKEY
```

## Scan Scripts

| Script | Mode | Use |
|--------|------|-----|
| `zap-baseline.py` | Passive only | Safe for prod — CI/CD gate |
| `zap-full-scan.py` | Active (attacks) | Comprehensive pentest |
| `zap-api-scan.py` | Active — API focused | OpenAPI / SOAP / GraphQL |

### zap-baseline.py Flags

| Flag | Purpose |
|------|---------|
| `-t <url>` | Target URL |
| `-r <file>` | HTML report output |
| `-J <file>` | JSON report output |
| `-x <file>` | XML report output |
| `-a` | Include alpha-quality passive rules |
| `-d` | Debug mode |
| `-m <min>` | Spider duration (default: 1) |
| `-j` | Use AJAX spider |
| `-z <options>` | Pass options to ZAP directly |
| `-c <config>` | Config file for FAIL/WARN overrides |

### zap-full-scan.py Flags

| Flag | Purpose |
|------|---------|
| `-t <url>` | Target URL |
| `-r <file>` | HTML report output |
| `-m <min>` | Spider duration (minutes) |
| `-z <options>` | ZAP options (e.g., `-config api.key=KEY`) |
| `-a` | Include alpha active rules |
| `-j` | Use AJAX spider |
| `-l <level>` | Alert level: PASS / IGNORE / WARN / FAIL |
| `-s <policy>` | Scan policy |

### zap-api-scan.py Flags

| Flag | Purpose |
|------|---------|
| `-t <file/url>` | OpenAPI/SOAP/GraphQL spec (local or URL) |
| `-f <format>` | Format: `openapi` / `soap` / `graphql` |
| `-r <file>` | HTML report |
| `-J <file>` | JSON report |
| `-n <context>` | Context file |

## Automation Framework (YAML)

Recommended approach for complex scans:

```yaml
# zap-automation.yaml
env:
  contexts:
    - name: Default
      urls:
        - https://target.com
      includePaths:
        - https://target.com.*
  parameters:
    failOnError: true

jobs:
  - type: spider
    parameters:
      maxDuration: 2
      maxDepth: 5

  - type: spiderAjax
    parameters:
      maxDuration: 2

  - type: activeScan
    parameters:
      policy: Default Policy

  - type: report
    parameters:
      template: traditional-html
      reportFile: report.html

  - type: alertFilter
    rules:
      - ruleId: 10016
        newRisk: False Positive
        url: https://target.com/login
```

```bash
zap.sh -cmd -autorun zap-automation.yaml
```

## REST API (Daemon Mode)

```bash
ZAP_KEY=your_api_key
ZAP="http://localhost:8080"

# Start scan
curl "$ZAP/JSON/spider/action/scan/?url=https://target.com&apikey=$ZAP_KEY"

# Wait for spider to complete
curl "$ZAP/JSON/spider/view/status/?scanId=0&apikey=$ZAP_KEY"

# Start active scan
curl "$ZAP/JSON/ascan/action/scan/?url=https://target.com&apikey=$ZAP_KEY"

# Check active scan progress
curl "$ZAP/JSON/ascan/view/status/?scanId=0&apikey=$ZAP_KEY"

# Get alerts
curl "$ZAP/JSON/core/view/alerts/?baseurl=https://target.com&apikey=$ZAP_KEY"

# Generate report
curl "$ZAP/OTHER/core/other/htmlreport/?apikey=$ZAP_KEY" -o report.html
```

## Python API

```python
from zapv2 import ZAPv2

zap = ZAPv2(apikey='MYKEY',
            proxies={'http': 'http://127.0.0.1:8080',
                     'https': 'http://127.0.0.1:8080'})

# Spider
zap.spider.scan('https://target.com')

# Active scan
zap.ascan.scan('https://target.com')

# Get alerts
alerts = zap.core.alerts(baseurl='https://target.com')
for alert in alerts:
    print(f"{alert['risk']}: {alert['name']} @ {alert['url']}")
```

## Authentication Setup

```bash
# Form-based: use Automation Framework
# jobs entry:
# - type: authentication
#   parameters:
#     loginPageUrl: https://target.com/login
#     loginRequestData: username={%username%}&password={%password%}
#     usernameParameter: username
#     passwordParameter: password
#   verification:
#     method: response
#     loggedInRegex: Logout
#     loggedOutRegex: Login
```

## Common Workflows

```bash
# CI/CD passive check (no attacks, no false positives)
docker run --rm \
    -v $(pwd):/zap/wrk \
    zaproxy/zap-stable zap-baseline.py \
    -t https://target.com \
    -r baseline_report.html \
    -J baseline.json

# Full scan with JSON report
docker run --rm \
    -v $(pwd):/zap/wrk \
    zaproxy/zap-stable zap-full-scan.py \
    -t https://target.com \
    -r full_scan.html

# OpenAPI scan
docker run --rm \
    -v $(pwd):/zap/wrk \
    zaproxy/zap-stable zap-api-scan.py \
    -t https://target.com/openapi.json \
    -f openapi \
    -r api_report.html

# GraphQL scan
docker run --rm \
    zaproxy/zap-stable zap-api-scan.py \
    -t https://target.com/graphql \
    -f graphql \
    -r graphql_report.html
```

## GitHub Actions

```yaml
name: ZAP Security Scan
on: [push]
jobs:
  zap_scan:
    runs-on: ubuntu-latest
    steps:
      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.12.0
        with:
          target: 'https://target.com'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a'
```

## ZAP vs Burp Suite Pro

| | ZAP | Burp Suite Pro |
|-|-----|----------------|
| Cost | Free | ~$400/yr |
| CI/CD integration | Excellent | Good |
| Manual testing | Good | Excellent |
| Active scan accuracy | Medium | High |
| API scanning | Yes | Yes |
| Extension ecosystem | Community | BApp Store (commercial) |
| **Use when** | CI/CD, DevSecOps, API testing | Manual pentest, complex apps |

## Resources

| File | When to load |
|------|--------------|
| `references/automation-api.md` | Automation Framework YAML, REST API usage, Python client, CI/CD patterns |
