---
name: testssl
description: "testssl.sh: comprehensive TLS/SSL testing script checking protocol support, cipher suites, vulnerabilities (BEAST, POODLE, Heartbleed, ROBOT, DROWN, etc.), and certificate issues. Use when assessing TLS configuration of any HTTPS service — web servers, mail servers, VPNs, or any TLS endpoint."
license: GPL-2.0
compatibility: "Linux / macOS / Windows (WSL/Cygwin). Bash 3.2+, OpenSSL or LibreSSL. git clone https://github.com/drwetter/testssl.sh.git or brew install testssl."
metadata:
  author: AeonDave
  version: "1.0"
---

# testssl.sh

TLS/SSL testing script — protocols, ciphers, vulnerabilities, certificates.

## Quick Start

```bash
# Full scan (all checks)
testssl.sh https://target.com

# Specific port
testssl.sh target.com:8443

# STARTTLS (mail server)
testssl.sh --starttls smtp mail.target.com:25
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-p` | Check protocols (SSLv2/3, TLS 1.0-1.3) |
| `-s` | List cipher suites (preferred + supported) |
| `-f` | Check forward secrecy |
| `-h` | Check HSTS / HPKP |
| `-U` | Test all vulnerabilities |
| `-E` | List cipher suites per protocol |
| `-B` | Heartbleed (OpenSSL vulnerability) |
| `--beast` | BEAST attack check |
| `--breach` | BREACH check |
| `--crime` | CRIME check |
| `--lucky13` | Lucky13 timing attack |
| `--poodle` | POODLE (SSLv3) |
| `--sweet32` | Birthday attacks on 64-bit block ciphers |
| `--logjam` | Logjam (DH key exchange weakness) |
| `--drown` | DROWN attack (SSLv2 overlap) |
| `--ticketbleed` | Ticketbleed (F5 vulnerability) |
| `--robot` | ROBOT attack |
| `--tls-fallback` | TLS_FALLBACK_SCSV check |
| `-e` | List all supported ciphers |
| `--protocols` | List supported protocols only |
| `--server-defaults` | Server defaults (cert, session, etc.) |
| `--server-preference` | Server cipher preference |
| `--client-simulation` | Simulate handshake with common clients |
| `--starttls <proto>` | STARTTLS: smtp / pop3 / imap / ftp / xmpp / ldap |
| `--mx` | Test all MX records of a domain (mail servers) |
| `--file <file>` | Batch mode — one target per line |
| `--mode parallel` | Run batch in parallel (use with `--file`) |
| `--outprefix <str>` | Prefix for all output files in batch mode |
| `--append` | Append to existing output file |
| `--ip <ip>` | Force specific IP for SNI hosts |
| `--proxy <host:port>` | SOCKS5/HTTP proxy |
| `--sneaky` | Sneaky mode (minimal headers) |
| `--ids-friendly` | Avoid IDS trigger patterns |
| `-t <n>` | Timeout per connection |
| `--connect-timeout <n>` | Connection timeout |
| `--openssl <path>` | Specify OpenSSL binary to use |
| `-oJ <file>` | JSON output |
| `-oC <file>` | CSV output |
| `-oH <file>` | HTML output |
| `-oA <file>` | All output formats (adds extensions) |
| `--color <0-3>` | Color output level |
| `--quiet` | Minimal output |
| `--warnings batch` | Batch mode (no interactive prompts) |
| `--parallel` | Parallel testing (faster, less reliable) |
| `--nodns <min>` | Skip DNS reverse lookups |

## Vulnerability Checks (-U runs all)

| Flag | Vulnerability | Impact |
|------|--------------|--------|
| `--heartbleed` | Heartbleed (CVE-2014-0160) | Memory leak → private key |
| `--ccs` | CCS Injection (CVE-2014-0224) | MITM |
| `--ticketbleed` | Ticketbleed (CVE-2016-9244) | Memory leak |
| `--robot` | ROBOT (RSA PKCS#1 oracle) | RSA key recovery |
| `--breach` | BREACH | HTTP compression info leak |
| `--crime` | CRIME | TLS compression info leak |
| `--beast` | BEAST | CBC mode attack (TLS 1.0) |
| `--poodle` | POODLE | SSLv3 CBC attack |
| `--sweet32` | Sweet32 | 3DES birthday attack |
| `--logjam` | Logjam | DH 512/1024-bit export weakness |
| `--drown` | DROWN | SSLv2 cross-protocol attack |
| `--lucky13` | Lucky13 | CBC timing attack |
| `--tls-fallback` | Downgrade fallback | Missing SCSV |
| `--freak` | FREAK | Export RSA key exchange |
| `--rc4` | RC4 biases | Statistical attacks |

```bash
# Individual vuln flags (short form):
# -H heartbleed  -I CCS  -T ticketbleed  --BB ROBOT  -R renegotiation
# -C CRIME  -B BREACH  -O POODLE  -Z fallback  -W SWEET32
# -F FREAK  -D DROWN  -J LOGJAM  -A BEAST  -L LUCKY13  -4 RC4
```

## Protocol & Cipher Assessment

```bash
# Protocol support check
testssl.sh -p target.com
# Look for: SSLv2 (critical), SSLv3 (critical), TLS 1.0/1.1 (warn)

# Cipher suites
testssl.sh -s target.com
# Look for: NULL, EXPORT, DES, RC4, 3DES (all bad)
# Want: AESGCM, CHACHA20, ECDHE (good)

# Check for forward secrecy (PFS)
testssl.sh -f target.com
# ECDHE/DHE = PFS available; RSA key exchange = no PFS

# Full cipher enumeration
testssl.sh -E target.com
```

## Common Workflows

```bash
# Full assessment with all checks
testssl.sh -U -p -s -h -f --server-defaults target.com

# Quick vuln check only (fast)
testssl.sh -U --quiet target.com

# STARTTLS mail server
testssl.sh --starttls smtp mail.target.com:587
testssl.sh --starttls imap mail.target.com:143

# JSON output for reporting
testssl.sh --jsonfile report.json -U target.com

# HTML report
testssl.sh -oH report.html -U -p -s target.com

# All formats at once
testssl.sh -oA report -U -p -s -f target.com
# Creates: report.json, report.csv, report.html

# Client simulation (browser compatibility)
testssl.sh --client-simulation target.com

# Batch scan with built-in file mode (one target per line):
# targets.txt can contain: host:port, -t smtp host:587, etc.
testssl.sh --file targets.txt --warnings batch -U --quiet

# Parallel batch scan (built-in):
testssl.sh --file targets.txt --mode parallel --warnings batch \
    -oA pentest-$(date +%Y%m%d)  # creates .json .csv .html per target

# Test all mail servers (MX records) for domain:
testssl.sh --mx example.com

# Stealth / IDS-evasion mode:
testssl.sh --sneaky --ids-friendly --nodns min -U target.com
```

## Key Findings for Reports

| Finding | Severity | Recommendation |
|---------|----------|---------------|
| SSLv2 enabled | Critical | Disable immediately |
| SSLv3 enabled | Critical | Disable (POODLE) |
| TLS 1.0 enabled | Medium/High | Disable if possible |
| Heartbleed | Critical | Patch OpenSSL |
| ROBOT | High | Disable RSA key exchange |
| NULL ciphers | Critical | Remove |
| EXPORT ciphers | Critical | Remove |
| RC4 ciphers | High | Remove |
| 3DES (Sweet32) | Medium | Remove |
| DH < 2048-bit | Medium | Use 2048+ bit DH |
| Self-signed cert | Medium | Replace with trusted CA |
| Expired cert | High | Renew certificate |
| No HSTS | Low/Medium | Add Strict-Transport-Security |
| No PFS | Medium | Enable ECDHE ciphers |
| SHA1 certificate | Medium | Replace with SHA256+ |

## Output Parsing

```bash
# Extract findings from JSON
cat report.json | jq '.[] | select(.severity != "OK" and .severity != "INFO") | {id: .id, severity: .severity, finding: .finding}'

# Count by severity
cat report.json | jq '[.[] | .severity] | group_by(.) | map({severity: .[0], count: length})'

# Extract certificate info
cat report.json | jq '.[] | select(.id | startswith("cert")) | {id: .id, finding: .finding}'

# Find critical/high findings only
cat report.json | jq '.[] | select(.severity == "CRITICAL" or .severity == "HIGH") | {id, finding}'
```

## Resources

| File | When to load |
|------|--------------|
| `references/tls-hardening.md` | TLS configuration best practices, cipher suite recommendations, HSTS setup |
