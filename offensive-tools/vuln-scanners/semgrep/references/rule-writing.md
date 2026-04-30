# semgrep — Custom Rule Writing Reference

## Rule Structure

```yaml
rules:
  - id: rule-id-kebab-case
    pattern: ...           # or patterns: / pattern-either:
    message: "Description of the finding"
    severity: ERROR        # ERROR / WARNING / INFO
    languages: [python]    # list of languages
    metadata:
      category: security   # security / correctness / performance
      cwe: CWE-89
      owasp: A03:2021
```

## Pattern Types

### Single pattern
```yaml
pattern: |
  cursor.execute($SQL + $USER_INPUT)
```

### Pattern with conditions (AND)
```yaml
patterns:
  - pattern: |
      cursor.execute($SQL)
  - pattern-not: |
      cursor.execute($CONST_SQL, ...)
  - pattern-inside: |
      def $FUNC(...):
        ...
```

### Pattern alternatives (OR)
```yaml
pattern-either:
  - pattern: os.system($CMD)
  - pattern: subprocess.call($CMD, shell=True)
  - pattern: subprocess.Popen($CMD, shell=True)
```

### Pattern regex
```yaml
pattern-regex: 'password\s*=\s*["\'][^"\']{8,}["\']'
```

## Metavariables

```yaml
# $VAR — matches any expression/statement
# $...ARGS — matches any number of arguments
# #... — matches any statement in a block

# Example: find any function called with user input
pattern: |
  $FUNC(request.GET.$PARAM)
# Matches: render(request.GET.name), eval(request.GET.code), etc.
```

## Metavariable Patterns

```yaml
# Match metavariable against a pattern:
patterns:
  - pattern: |
      $FUNC($ARG)
  - metavariable-pattern:
      metavariable: $FUNC
      pattern-either:
        - pattern: eval
        - pattern: exec
        - pattern: compile
```

## Metavariable Regex

```yaml
patterns:
  - pattern: $KEY = "..."
  - metavariable-regex:
      metavariable: $KEY
      regex: '(?i)(password|passwd|secret|api_key|token)'
```

## Autofix

```yaml
rules:
  - id: use-https
    pattern: "http://$URL"
    fix: "https://$URL"
    message: "Use HTTPS instead of HTTP"
    severity: WARNING
    languages: [generic]
```

## Common Security Rule Patterns

### SQL Injection (Python)
```yaml
- id: python-sqli-string-concat
  patterns:
    - pattern-either:
        - pattern: cursor.execute($Q + $I)
        - pattern: cursor.execute($Q % $I)
        - pattern: cursor.execute(f"... {$I} ...")
  message: "String concatenation in SQL query — potential SQLi"
  severity: ERROR
  languages: [python]
  metadata:
    cwe: CWE-89
    owasp: A03:2021
```

### Command Injection (Python)
```yaml
- id: python-cmd-injection
  pattern-either:
    - pattern: os.system($CMD)
    - pattern: os.popen($CMD)
    - pattern: subprocess.call($CMD, ..., shell=True)
    - pattern: subprocess.run($CMD, ..., shell=True)
  pattern-not:
    - pattern: os.system("...")
    - pattern: subprocess.run("...", ...)
  message: "Command injection risk — user input in shell command"
  severity: ERROR
  languages: [python]
```

### Hardcoded Secrets
```yaml
- id: hardcoded-password
  patterns:
    - pattern: $KEY = "$VALUE"
    - metavariable-regex:
        metavariable: $KEY
        regex: '(?i)(password|passwd|secret|api.?key|access.?key|auth.?token)'
    - metavariable-regex:
        metavariable: $VALUE
        regex: '.{8,}'
  pattern-not:
    - pattern: $KEY = ""
    - pattern: $KEY = os.environ[...]
    - pattern: $KEY = os.getenv(...)
  message: "Hardcoded credential: $KEY = $VALUE"
  severity: WARNING
  languages: [python, javascript, java, go]
```

### XSS (JavaScript)
```yaml
- id: js-innerhtml-injection
  pattern-either:
    - pattern: $EL.innerHTML = $USER_DATA
    - pattern: $EL.outerHTML = $USER_DATA
    - pattern: document.write($USER_DATA)
  message: "Direct DOM manipulation with potentially tainted data — XSS risk"
  severity: WARNING
  languages: [javascript, typescript]
```

### JWT without verification
```yaml
- id: jwt-no-verify
  pattern-either:
    - pattern: jwt.decode($TOKEN, options={"verify_signature": False, ...})
    - pattern: jwt.decode($TOKEN, verify=False)
    - pattern: jwt.decode($TOKEN, algorithms=["none"])
  message: "JWT decoded without signature verification"
  severity: ERROR
  languages: [python]
```

## Testing Rules

```yaml
# In source file, add test comments:
# ruleid: rule-id-kebab-case  ← should match
# ok: rule-id-kebab-case     ← should NOT match

# Python test file:
password = "hunter2"  # ruleid: hardcoded-password
password = os.getenv("PASSWORD")  # ok: hardcoded-password
```

```bash
# Run rule tests:
semgrep --test --config rules/ tests/
```

## Taint Mode (Data Flow Tracking)

Traces user input from source → through code → to dangerous sink. Requires Pro or OSS with supported rules.

```yaml
rules:
  - id: flask-sqli-taint
    mode: taint
    message: "User input flows into SQL query — potential SQLi"
    severity: ERROR
    languages: [python]
    metadata:
      cwe: CWE-89
    # Where tainted data enters:
    pattern-sources:
      - pattern: flask.request.args.get(...)
      - pattern: flask.request.form.get(...)
      - pattern: flask.request.json
      - pattern: flask.request.values.get(...)
    # Where tainted data must NOT flow:
    pattern-sinks:
      - pattern: $DB.execute($QUERY)
      - pattern: $CURSOR.execute($QUERY)
      - pattern: $CONN.execute($QUERY)
    # What sanitizes the data (removes taint):
    pattern-sanitizers:
      - pattern: sqlalchemy.text(...)    # parameterized query
      - pattern: $DB.execute($Q, $PARAMS)  # parameterized
```

```yaml
  - id: flask-cmd-injection-taint
    mode: taint
    message: "User input reaches OS command execution"
    severity: ERROR
    languages: [python]
    pattern-sources:
      - pattern: flask.request.args.get(...)
      - pattern: flask.request.form[...]
    pattern-sinks:
      - pattern: os.system(...)
      - pattern: subprocess.run(..., shell=True)
      - pattern: subprocess.call(..., shell=True)
      - pattern: os.popen(...)
    pattern-sanitizers:
      - pattern: shlex.quote(...)
```

```yaml
  - id: express-xss-taint
    mode: taint
    message: "User input rendered without escaping — XSS risk"
    severity: ERROR
    languages: [javascript, typescript]
    pattern-sources:
      - pattern: req.query.$PARAM
      - pattern: req.body.$PARAM
      - pattern: req.params.$PARAM
    pattern-sinks:
      - pattern: res.send(...)
      - pattern: res.write(...)
      - pattern: $EL.innerHTML = ...
    pattern-sanitizers:
      - pattern: DOMPurify.sanitize(...)
      - pattern: escapeHtml(...)
```

## Rule Severity Guide

| Severity | Use When |
|----------|---------|
| `ERROR` | Direct security vulnerability, injection, auth bypass |
| `WARNING` | Potential issue, needs review, bad practice |
| `INFO` | Informational, style, low-severity suggestion |

## Running Custom + Registry Rules

```bash
# Mix registry and custom:
semgrep --config p/owasp-top-ten \
        --config p/secrets \
        --config ./custom-rules/ \
        --severity WARNING \
        --json -o findings.json \
        /path/to/project
```
