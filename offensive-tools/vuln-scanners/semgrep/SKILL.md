---
name: semgrep
description: "Auth/lab ref: fast static analysis tool for finding security vulnerabilities, misconfigurations, and secrets in source code."
license: LGPL-2.1
compatibility: "Linux / macOS / Windows."
metadata:
  author: AeonDave
  version: "1.0"
---

# semgrep

Static analysis for security — find vulns, secrets, misconfigs in source code.

## Quick Start

```bash
# Modern syntax: semgrep scan (older: semgrep --config)
semgrep scan --config p/owasp-top-ten .

# Scan for secrets
semgrep --config p/secrets .

# Full security audit
semgrep --config p/security-audit .
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--config <cfg>` | Rule config: file, directory, URL, or registry rule (`p/...`) |
| `--lang <lang>` | Force language (python/javascript/java/go/etc.) |
| `--include <glob>` | Include only matching files |
| `--exclude <glob>` | Exclude matching files |
| `--severity <level>` | Filter: ERROR / WARNING / INFO |
| `--json` | JSON output |
| `--output <file>` | Save output to file |
| `--sarif` | SARIF format output (for GitHub/VS Code integration) |
| `--junit-xml` | JUnit XML output (for CI) |
| `--no-git-ignore` | Don't respect .gitignore |
| `--metrics off` | Disable telemetry |
| `--timeout <n>` | Per-file timeout (default 30s) |
| `--max-memory <n>` | Max memory per file (MB) |
| `-j <n>` | Parallelism (default: CPU count) |
| `--quiet` | Suppress non-finding output |
| `-v` | Verbose |
| `--validate` | Validate rules before running |
| `--test` | Test rules against test cases |
| `--autofix` | Apply auto-fixes where available |
| `--dryrun` | Show fixes without applying |
| `--pro` | Enable Pro engine (cross-file dataflow analysis) |
| `--exclude-rule <id>` | Skip specific rule ID |
| `--rewrite-rule-ids` | Prefix rule IDs with config path |
| `--scan-unknown-extensions` | Scan files with unknown extensions |

## Registry Rule Sets

| Config | What it finds |
|--------|--------------|
| `p/owasp-top-ten` | OWASP Top 10 vulnerabilities |
| `p/security-audit` | Broad security audit rules |
| `p/secrets` | Hardcoded API keys, tokens, passwords |
| `p/ci` | CI/CD configuration issues |
| `p/supply-chain` | Supply chain / dependency issues |
| `p/javascript` | JavaScript-specific security |
| `p/python` | Python security patterns |
| `p/java` | Java security patterns |
| `p/go` | Go security patterns |
| `p/php` | PHP security patterns |
| `p/react` | React-specific issues |
| `p/flask` | Flask web framework issues |
| `p/django` | Django web framework issues |
| `p/nodejs` | Node.js security patterns |
| `p/terraform` | Terraform IaC misconfigs |
| `p/dockerfile` | Dockerfile security issues |
| `p/kubernetes` | Kubernetes manifest issues |
| `p/sql-injection` | SQL injection patterns |
| `p/xss` | Cross-site scripting |
| `p/command-injection` | OS command injection |
| `p/ssrf` | Server-side request forgery |
| `p/jwt` | JWT misconfiguration |
| `p/crypto` | Weak cryptography patterns |
| `p/express` | Express.js security issues |
| `p/java-spring` | Spring Framework security |
| `p/insecure-transport` | HTTP instead of HTTPS, no TLS |

## Common Workflows

```bash
# Full security audit of a project
semgrep --config p/security-audit \
        --config p/secrets \
        --config p/owasp-top-ten \
        --severity WARNING \
        --json -o findings.json \
        /path/to/project

# Scan only Python files
semgrep --config p/python --include="*.py" .

# Scan for secrets (fast, high value)
semgrep --config p/secrets --quiet --json .

# Scan specific language
semgrep --config p/java --lang java src/

# Multiple configs
semgrep --config p/sql-injection \
        --config p/command-injection \
        --config p/xss \
        --json -o injection_findings.json .

# Exclude test files and dependencies
semgrep --config p/security-audit \
        --exclude="*test*" \
        --exclude="*vendor*" \
        --exclude="*node_modules*" \
        --exclude="*__pycache__*" \
        .

# Scan for insecure cryptography
semgrep --config r/generic.crypto .

# Scan IaC
semgrep --config p/terraform infra/
semgrep --config p/dockerfile Dockerfile
semgrep --config p/kubernetes k8s/
```

## Output Parsing

```bash
# JSON output structure
semgrep --config p/secrets --json -o secrets.json .

# Extract findings:
cat secrets.json | jq '.results[] | {rule: .check_id, file: .path, line: .start.line, msg: .extra.message}'

# Count by severity:
cat findings.json | jq '[.results[].extra.severity] | group_by(.) | map({severity: .[0], count: length})'

# Find unique files with findings:
cat findings.json | jq -r '.results[].path' | sort -u

# High/critical only:
cat findings.json | jq '.results[] | select(.extra.severity == "ERROR") | {rule: .check_id, file: .path, line: .start.line}'

# SARIF output for GitHub Advanced Security:
semgrep --config p/security-audit --sarif -o results.sarif .
```

## Writing Custom Rules

```yaml
# rules/custom-sqli.yaml
rules:
  - id: raw-sql-from-input
    patterns:
      - pattern: |
          cursor.execute($QUERY + $USER_INPUT)
      - pattern-not: |
          cursor.execute($QUERY, ($PARAM,))
    message: "SQL query constructed from user input — potential SQLi"
    severity: ERROR
    languages: [python]
    metadata:
      category: security
      cwe: CWE-89

  - id: hardcoded-secret
    pattern-either:
      - pattern: |
          $KEY = "..."
          ...
          $API = $KEY
      - pattern: |
          password = "..."
    pattern-not:
      - pattern: |
          password = ""
    message: "Hardcoded secret detected"
    severity: WARNING
    languages: [python, javascript, java]
```

```yaml
# rules/xss-flask.yaml
rules:
  - id: flask-render-string-unsafe
    patterns:
      - pattern: |
          flask.render_template_string($TMPL)
      - pattern-not: |
          flask.render_template_string("...")
    message: "render_template_string with variable — potential SSTI/XSS"
    severity: ERROR
    languages: [python]
    fix: |
      flask.render_template("safe_template.html")
```

```bash
# Test custom rule:
semgrep --config rules/ --validate
semgrep --config rules/custom-sqli.yaml /path/to/code

# Run all rules in directory:
semgrep --config ./rules/ .
```

## High-Value Patterns for Code Review

```bash
# Find SQL concatenation (SQLi):
semgrep --config p/sql-injection --json .

# Find eval() usage:
semgrep -e 'eval(...)' --lang python .
semgrep -e 'eval(...)' --lang javascript .

# Find exec() in Python:
semgrep -e 'os.system(...)' --lang python .
semgrep -e 'subprocess.call($X, shell=True)' --lang python .

# Find hardcoded AWS keys:
semgrep -e '"AKIA..."' --lang generic .

# Find debug flags in production:
semgrep -e 'DEBUG = True' --lang python .
semgrep -e 'app.run(debug=True)' --lang python .

# Find JWT without verification:
semgrep -e 'jwt.decode($TOKEN, options={"verify_signature": False})' --lang python .
```

## Resources

| File | When to load |
|------|--------------|
| `references/rule-writing.md` | Custom rule patterns, metavariables, advanced matching |
