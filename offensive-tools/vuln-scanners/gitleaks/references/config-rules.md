# gitleaks — Config, Custom Rules & False Positive Reduction

## Config File Structure (.gitleaks.toml)

```toml
# Extend built-in rules (recommended: keep defaults + add your own)
# To extend: use --config pointing to file with [[rules]] additions
# To replace entirely: omit useDefault, define all rules

[[rules]]
id = "custom-api-key"
description = "Detects MyApp API keys"
regex = '''(?i)myapp[_-]?(?:api[_-]?)?key["'\s=:]+([a-zA-Z0-9]{32,})'''
secretGroup = 1          # Which capture group = actual secret
entropy = 3.5            # Shannon entropy minimum (default 3.5)
keywords = ["myapp"]     # Narrow matches to contexts with these keywords
tags = ["apikey", "myapp"]

[rules.allowlist]
regexes = ['''example''', '''test''', '''dummy''']
stopwords = ["placeholder", "changeme", "yourkey"]
paths = ['''.*test.*''', '''.*\.md$''']
commits = ["abc123defabc123"]    # Ignore specific commit SHA
```

## Allowlist Hierarchy

Allowlists can be defined at rule level or globally:

```toml
# Global allowlist (applies to all rules)
[allowlist]
description = "Global false positives"
regexes = ['''AKIAIOSFODNN7EXAMPLE''']    # Known example in docs
paths = ['''.*vendor/.*''', '''.*\.lock$''']
commits = ["deadbeef1234"]
```

## Entropy Thresholds

Shannon entropy measures randomness of a string:

| Entropy | Example | Likely |
|---------|---------|--------|
| < 3.0 | `password` | Word, not a secret |
| 3.0–3.5 | `extremelySecret123` | Borderline |
| 3.5–4.5 | `xD3k9Lm2pQ7...` | Likely a real secret |
| > 4.5 | `8dyfuiRyq=vVc3RRr_edRk-fK` | Almost certainly a secret |

```toml
# Conservative (catch more, more false positives)
entropy = 3.0

# Default balanced
entropy = 3.5

# Strict (fewer false positives, may miss some)
entropy = 4.0
```

## Common Custom Rules

### Generic High-Entropy String
```toml
[[rules]]
id = "high-entropy-string"
description = "High entropy string that may be a secret"
regex = '''["']([a-zA-Z0-9+/]{40,}={0,2})["']'''
secretGroup = 1
entropy = 4.5
```

### Internal Service Token
```toml
[[rules]]
id = "internal-svc-token"
description = "Internal service auth token"
regex = '''(?i)(?:svc|service)[_-]?token["'\s=:]+([a-zA-Z0-9_-]{20,})'''
secretGroup = 1
entropy = 3.8
keywords = ["svc_token", "service_token", "svctoken"]
```

### Database Connection String
```toml
[[rules]]
id = "db-connection-string"
description = "Database connection string with credentials"
regex = '''(?i)(?:postgres|mysql|mongodb|mssql|oracle)://[^:]+:([^@/\s]{8,})@'''
secretGroup = 1
keywords = ["postgres://", "mysql://", "mongodb://"]
```

### JWT Secret
```toml
[[rules]]
id = "jwt-secret"
description = "JWT signing secret"
regex = '''(?i)jwt[_-]?secret["'\s=:]+["']([^"']{10,})["']'''
secretGroup = 1
entropy = 3.5
keywords = ["jwt_secret", "jwtsecret", "jwt-secret"]
```

## Reducing False Positives

### 1. Built-in Stopwords
Gitleaks includes 1479 common programming words (min 4 chars) that suppress findings:
`cache`, `admin`, `build`, `www`, `test`, `example`, `demo`, `mock`, `fake`, `dummy`, etc.

### 2. Add Custom Stopwords
```toml
[rules.allowlist]
stopwords = [
    "placeholder",
    "changeme",
    "yourkey",
    "exampletoken",
    "samplekey",
]
```

### 3. Path Exclusions
```toml
[rules.allowlist]
paths = [
    '''.*test.*''',
    '''.*spec.*''',
    '''.*\.md$''',
    '''.*\.example$''',
    '''.*vendor/.*''',
    '''.*node_modules/.*''',
    '''.*\.lock$''',
]
```

### 4. Baseline to Suppress Known Findings
```bash
# Create baseline from current state
gitleaks git . --report-path .gitleaks-baseline.json

# Future scans ignore baseline findings
gitleaks git . --baseline-path .gitleaks-baseline.json
```

### 5. Allowlist Specific Commits
```toml
[allowlist]
commits = [
    "abc123def456",   # Legacy commit with test data
]
```

### 6. Tuning Regex Specificity
```toml
# Bad (too broad, many false positives):
regex = '''[a-zA-Z0-9]{32}'''

# Better (context-anchored):
regex = '''(?i)api[_-]?key["'\s=:]+([a-zA-Z0-9]{32,})'''

# Best (keyword + structure + group):
regex = '''(?i)(?:aws|amazon)[_-]?access[_-]?key["'\s=:]+([A-Z0-9]{20})'''
```

## Gitleaks vs TruffleHog

| | gitleaks | trufflehog |
|-|----------|------------|
| Speed | Very fast | Slower |
| Verification | No (pattern only) | Yes (tests if secret works) |
| Pre-commit | Yes (ideal) | Possible, heavier |
| Scope | Git + dirs | Git + S3 + Docker + cloud |
| False positives | Higher | Lower (verification helps) |
| Custom rules | TOML config | Custom detectors (Go) |

**Combined approach:**
- gitleaks: pre-commit hook + CI PR blocking (speed)
- trufflehog: weekly full-history scan with verification (coverage)

## CI/CD Patterns

```bash
# GitLab CI — scan only new commits
gitleaks git . --log-opts="${CI_COMMIT_BEFORE_SHA}..${CI_COMMIT_SHA}" \
    --report-format sarif --report-path gl-secret-detection-report.json \
    --exit-code 1

# GitHub Actions — full history
gitleaks git . --report-format sarif --report-path gitleaks.sarif \
    --exit-code 1

# Jenkins — fail build on findings
gitleaks git . --exit-code 1 --no-banner || exit 1
```
