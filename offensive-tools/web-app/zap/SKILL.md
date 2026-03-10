---
name: zap
description: "OWASP ZAP: open-source web application scanner and intercepting proxy for automated active/passive vulnerability scanning. Use when performing comprehensive web app tests, integrating security scanning into CI/CD pipelines, scripting custom scan logic, or running headless API scans."
license: Apache-2.0
compatibility: "Linux / macOS / Windows. Java 11+. Docker available from zaproxy.org."
metadata:
  author: AeonDave
  version: "1.0"
---

# OWASP ZAP

Open-source web app scanner and intercepting proxy.

## Quick Start

```bash
zap.sh
zap.sh -daemon -port 8090 -host 127.0.0.1
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://target.com
docker run -t owasp/zap2docker-stable zap-full-scan.py -t http://target.com
```

## Scan Types

| Scan | Command | Notes |
|------|---------|-------|
| Baseline | `zap-baseline.py` | Passive only, safe for prod |
| Full scan | `zap-full-scan.py` | Active, potentially destructive |
| API scan | `zap-api-scan.py` | OpenAPI / SOAP / GraphQL targets |

## REST API (daemon mode)

```bash
curl "http://localhost:8090/JSON/spider/action/scan/?url=http://target.com"
curl "http://localhost:8090/JSON/ascan/action/scan/?url=http://target.com"
curl "http://localhost:8090/JSON/core/view/alerts/"
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Authentication config, CI integration, scripting API |
