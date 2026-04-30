# ZAP — Automation Framework, REST API & CI/CD

## Automation Framework YAML Reference

Full workflow with authentication:

```yaml
env:
  contexts:
    - name: Target-App
      urls:
        - https://target.com
      includePaths:
        - https://target.com.*
      excludePaths:
        - https://target.com/logout.*
      authentication:
        method: form
        parameters:
          loginPageUrl: https://target.com/login
          loginRequestData: username={%username%}&password={%password%}
          usernameParameter: username
          passwordParameter: password
        verification:
          method: response
          loggedInRegex: "Logout"
          loggedOutRegex: "Login"
      sessionManagement:
        method: cookie
      users:
        - name: TestUser
          credentials:
            username: testuser@example.com
            password: password123

  parameters:
    failOnError: true
    progressToStdout: true

jobs:
  - type: spider
    parameters:
      maxDuration: 5      # minutes
      maxDepth: 10
      maxChildren: 20
      acceptCookies: true
      requestWaitTime: 200

  - type: spiderAjax
    parameters:
      maxDuration: 3
      browserId: chrome-headless

  - type: passiveScan-wait
    parameters:
      maxDuration: 10

  - type: activeScan
    parameters:
      policy: Default Policy
      maxScanDurationInMins: 30
      maxRuleDurationInMins: 5
      threadPerHost: 2
      delayInMs: 0

  - type: alertFilter
    rules:
      - ruleId: 10016         # Web Browser XSS Protection
        newRisk: False Positive
      - ruleId: 10096         # Timestamp Disclosure
        newRisk: Informational
        url: https://target.com/api/health

  - type: report
    parameters:
      template: traditional-html-plus
      reportFile: zap-report.html
      reportTitle: Security Scan Report
      reportDescription: Automated scan results
    risks:
      - high
      - medium
      - low
      - info
```

```bash
# Run automation
./zap.sh -cmd -autorun automation.yaml
docker run --rm -v $(pwd):/zap/wrk zaproxy/zap-stable zap.sh \
    -cmd -autorun /zap/wrk/automation.yaml
```

## REST API Reference

### Authentication

```bash
ZAP_KEY="your_key_here"
ZAP="http://localhost:8080"

# Start daemon with API key
zap.sh -daemon -port 8080 -config api.key=$ZAP_KEY
```

### Spider & Active Scan Flow

```bash
# 1. Access target through ZAP proxy to seed the tree
curl --proxy http://localhost:8080 https://target.com/

# 2. Run spider
SPIDER_ID=$(curl -s "$ZAP/JSON/spider/action/scan/?url=https://target.com&apikey=$ZAP_KEY" | jq -r '.scan')

# 3. Wait for spider
while true; do
    STATUS=$(curl -s "$ZAP/JSON/spider/view/status/?scanId=$SPIDER_ID&apikey=$ZAP_KEY" | jq -r '.status')
    [ "$STATUS" = "100" ] && break
    echo "Spider: $STATUS%" && sleep 5
done

# 4. Active scan
ASCAN_ID=$(curl -s "$ZAP/JSON/ascan/action/scan/?url=https://target.com&recurse=true&apikey=$ZAP_KEY" | jq -r '.scan')

# 5. Wait for active scan
while true; do
    STATUS=$(curl -s "$ZAP/JSON/ascan/view/status/?scanId=$ASCAN_ID&apikey=$ZAP_KEY" | jq -r '.status')
    [ "$STATUS" = "100" ] && break
    echo "Scan: $STATUS%" && sleep 10
done

# 6. Get alerts
curl -s "$ZAP/JSON/core/view/alerts/?baseurl=https://target.com&apikey=$ZAP_KEY" | \
    jq '.alerts[] | {risk: .risk, name: .name, url: .url}'

# 7. Count by risk
curl -s "$ZAP/JSON/core/view/alerts/?apikey=$ZAP_KEY" | \
    jq '[.alerts[].risk] | group_by(.) | map({risk: .[0], count: length})'

# 8. Generate HTML report
curl "$ZAP/OTHER/core/other/htmlreport/?apikey=$ZAP_KEY" -o report.html
```

## Python Client

```python
# pip install zaproxy
from zapv2 import ZAPv2
import time

zap = ZAPv2(
    apikey='MYKEY',
    proxies={'http': 'http://127.0.0.1:8080', 'https': 'http://127.0.0.1:8080'}
)

target = 'https://target.com'

# Spider
print("Spidering...")
scanid = zap.spider.scan(target)
while int(zap.spider.status(scanid)) < 100:
    print(f"Spider: {zap.spider.status(scanid)}%")
    time.sleep(2)

# Active scan
print("Active scanning...")
scanid = zap.ascan.scan(target, recurse=True)
while int(zap.ascan.status(scanid)) < 100:
    print(f"Scan: {zap.ascan.status(scanid)}%")
    time.sleep(5)

# Get alerts
alerts = zap.core.alerts(baseurl=target)
high = [a for a in alerts if a['risk'] == 'High']
print(f"Found {len(alerts)} alerts ({len(high)} High)")

for alert in sorted(alerts, key=lambda a: ['High','Medium','Low','Informational'].index(a['risk'])):
    print(f"[{alert['risk']}] {alert['name']}: {alert['url']}")
```

## GitHub Actions Patterns

```yaml
# Baseline scan (safe for every PR)
- uses: zaproxy/action-baseline@v0.12.0
  with:
    target: 'https://staging.target.com'
    rules_file_name: '.zap/rules.tsv'

# Full scan (nightly)
- uses: zaproxy/action-full-scan@v0.10.0
  with:
    target: 'https://staging.target.com'

# API scan
- uses: zaproxy/action-api-scan@v0.7.0
  with:
    target: 'https://target.com/openapi.json'
    format: openapi
```

### rules.tsv (alert overrides)

```tsv
# ruleId	IGNORE|WARN|FAIL
10096	IGNORE
10038	WARN
10202	FAIL
```

## SARIF Output for GitHub Code Scanning

```bash
# Generate SARIF
docker run --rm zaproxy/zap-stable zap-baseline.py \
    -t https://target.com \
    -J results.json \
    --sarif results.sarif

# Upload via GitHub Actions
- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```
