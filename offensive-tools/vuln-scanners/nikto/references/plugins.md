# Nikto — Plugins, Advanced Usage & Custom Checks

## Plugin System

```bash
# List available plugins
nikto -list-plugins

# Run specific plugin
nikto -h http://target.com -Plugins "plugin_name"

# Run multiple plugins
nikto -h http://target.com -Plugins "plugin1;plugin2"
```

## Key Plugins

| Plugin | Checks |
|--------|--------|
| `headers` | HTTP security headers (X-Frame-Options, CSP, HSTS, etc.) |
| `cookies` | Cookie flags (HttpOnly, Secure, SameSite) |
| `auth` | Authentication bypass techniques |
| `cgi` | CGI file/script vulnerabilities |
| `outdated` | Outdated software version detection |
| `paths` | Path traversal attempts |
| `shellshock` | CVE-2014-6271 Shellshock |
| `specials` | Special file checks (.git, .svn, .htaccess) |
| `ms10-070` | IIS padding oracle |

## Security Header Checks

Nikto checks for missing/misconfigured security headers:

| Header | Expected Value |
|--------|---------------|
| `X-Frame-Options` | `DENY` or `SAMEORIGIN` |
| `X-Content-Type-Options` | `nosniff` |
| `X-XSS-Protection` | `1; mode=block` |
| `Strict-Transport-Security` | `max-age=31536000` |
| `Content-Security-Policy` | Present |
| `Referrer-Policy` | Present |

```bash
# Check security headers only
nikto -h http://target.com -Tuning 3 -Plugins "headers"
```

## Authentication Bypass Techniques

```bash
# Try common default credentials
nikto -h http://target.com -id admin:admin
nikto -h http://target.com -id admin:password
nikto -h http://target.com -id root:root

# HTTP digest auth
nikto -h http://target.com -id admin:secret

# With session cookie instead
nikto -h http://target.com -H "Cookie: session=ABCDEF123"

# Bearer token
nikto -h http://target.com -H "Authorization: Bearer eyJhbGc..."
```

## Custom Configuration File

```ini
# ~/.nikto.conf or /etc/nikto.conf
# Override defaults:

# Custom user agent
USERAGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# Timeout
TIMEOUT=10

# Max scan time (seconds)
MAXTIME=300

# Default output format
FORMAT=csv

# Follow redirects
FOLLOWREDIRECTS=1
```

## Mutation Options

```bash
# -mutate <n>: guess additional file names
# 1: Test all files with all root dirs
# 2: Guess for password file names
# 3: Enumerate user names via Apache (/~user type requests)
# 4: Enumerate user names via cgiwrap (/cgi-bin/cgiwrap/~user)
# 5: Attempt to brute force subdomain names
# 6: Attempt to guess directory names from the supplied dictionary

nikto -h http://target.com -mutate 6 -mutate-options /usr/share/dirb/wordlists/common.txt
```

## Batch Scanning Workflow

```bash
# Scan multiple hosts from file (one per line)
# hosts.txt:
# http://target1.com
# https://target2.com:8443
# 192.168.1.1:8080

nikto -h hosts.txt -o batch_results.csv -Format csv

# Parallel scan with xargs
cat hosts.txt | xargs -P 5 -I {} \
    nikto -h {} -o results/{}_scan.txt -Format txt 2>/dev/null

# Pipeline: nmap → nikto
nmap -p 80,443,8080,8443 -oG - 192.168.1.0/24 | \
    awk '/open/{print $2}' | \
    xargs -I {} nikto -h {} -Tuning 23b -o nikto_{}.txt

# Pipeline: httpx → nikto
cat hosts.txt | httpx -silent | \
    while read url; do
        nikto -h "$url" -Tuning 234b -o "nikto_$(echo $url | tr '://' '_').txt"
    done
```

## Output Parsing

```bash
# CSV output → extract findings
nikto -h http://target.com -Format csv -o out.csv
cat out.csv | awk -F',' '{print $7}' | sort -u    # Message column

# XML → parse with xmllint
nikto -h http://target.com -Format xml -o out.xml
xmllint --xpath "//item/description/text()" out.xml

# JSON output (newer versions)
nikto -h http://target.com -Format json -o out.json
cat out.json | jq '.vulnerabilities[] | {id: .id, msg: .msg}'
```

## Custom Database Entries

```bash
# Nikto uses /var/lib/nikto/databases/ for check definitions
# Format: db_tests file
# "ID","Service","HTTP method","URI","Match string (regex)","Match code","Summary","Test category"

# Example custom entry (add to db_tests):
# "099999","www","GET","/custom-admin-page.php","200","","Custom admin page found",2

# Check file for format:
head -5 /usr/share/nikto/databases/db_tests
```

## Useful Flags Combo Reference

```bash
# CTF / Lab (fast, all checks, verbose)
nikto -h http://target.com -Tuning 0123456789abc -Display V

# Production scan (safe, stealth)
nikto -h http://target.com -Tuning 23b -evasion 1,7 -pause 500 -timeout 15

# Internal network scan
nikto -h 10.10.10.1 -p 80,443,8080,8443,8888 -Tuning 23b

# With proxy for Burp intercept
nikto -h http://target.com -useproxy http://127.0.0.1:8080 -nointeractive
```
