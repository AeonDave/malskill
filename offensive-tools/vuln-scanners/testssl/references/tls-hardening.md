# TLS Hardening Reference — Findings Interpretation & Remediation

## Protocol Version Guidance

| Protocol | Status | Action |
|----------|--------|--------|
| SSLv2 | Broken | Disable immediately — DROWN, EXPORT |
| SSLv3 | Broken | Disable immediately — POODLE |
| TLS 1.0 | Deprecated | Disable (PCI-DSS requires by 2024) |
| TLS 1.1 | Deprecated | Disable |
| TLS 1.2 | Acceptable | Keep with strong cipher suites |
| TLS 1.3 | Recommended | Enable — mandatory forward secrecy |

## Recommended Cipher Suite Order

### TLS 1.3 (automatic, no configuration needed)
```
TLS_AES_256_GCM_SHA384
TLS_CHACHA20_POLY1305_SHA256
TLS_AES_128_GCM_SHA256
```

### TLS 1.2 (curated list)
```
# Nginx format:
ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256

# Remove from all configs:
# RC4, DES, 3DES, MD5, NULL, EXPORT, anon, ADH, AECDH
```

## testssl.sh Finding IDs Reference

| ID Pattern | Category |
|-----------|---------|
| `SSLv2`, `SSLv3` | Protocol versions |
| `TLS1`, `TLS1_1`, `TLS1_2`, `TLS1_3` | Protocol versions |
| `cert_*` | Certificate issues |
| `cipher_*` | Cipher suite issues |
| `HSTS_*` | HSTS configuration |
| `HPKP_*` | HTTP Public Key Pinning |
| `heartbleed` | Heartbleed vulnerability |
| `CCS` | CCS injection |
| `ticketbleed` | Ticketbleed |
| `ROBOT` | ROBOT attack |
| `BREACH` | BREACH |
| `CRIME_*` | CRIME |
| `POODLE_SSL` | POODLE |
| `SWEET32` | Sweet32 |
| `LOGJAM*` | Logjam |
| `DROWN*` | DROWN |
| `BEAST*` | BEAST |
| `LUCKY13` | Lucky13 |

## Certificate Checks

```bash
# Manual certificate inspection:
openssl s_client -connect target.com:443 -servername target.com < /dev/null 2>/dev/null | \
    openssl x509 -noout -text | grep -A5 "Subject:\|Issuer:\|Validity\|SAN"

# Check expiry:
echo | openssl s_client -connect target.com:443 2>/dev/null | \
    openssl x509 -noout -enddate

# Certificate chain:
openssl s_client -connect target.com:443 -showcerts < /dev/null 2>/dev/null
```

## Key Issues to Report

### Heartbleed (CVE-2014-0160)
```
Severity: Critical
Impact: OpenSSL memory leak → private key, session data, credentials
Check: testssl.sh --heartbleed target.com
Fix: Upgrade OpenSSL, reissue all certificates, revoke old certs, invalidate sessions
```

### POODLE (CVE-2014-3566)
```
Severity: Critical
Impact: MITM via CBC oracle in SSLv3
Check: testssl.sh --poodle target.com
Fix: Disable SSLv3 entirely
```

### ROBOT (Return Of Bleichenbacher's Oracle Threat)
```
Severity: High
Impact: RSA PKCS#1 v1.5 oracle → private key recovery over time
Check: testssl.sh --robot target.com
Fix: Disable RSA key exchange; use ECDHE/DHE only
```

### Sweet32 (CVE-2016-2183)
```
Severity: Medium
Impact: Birthday attack on 3DES (64-bit block cipher)
Check: testssl.sh --sweet32 target.com
Fix: Remove 3DES cipher suites
```

### Logjam
```
Severity: Medium-High
Impact: Downgrade to 512-bit DH export → MITM
Check: testssl.sh --logjam target.com
Fix: Use 2048+ bit DH parameters; disable export ciphers; prefer ECDHE
```

## nginx TLS Configuration Template

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers on;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;
ssl_dhparam /etc/nginx/dhparam.pem;   # openssl dhparam -out dhparam.pem 2048
ssl_ecdh_curve X25519:prime256v1:secp384r1;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
```

## Batch Scanning & Reporting

```bash
# Scan all hosts, collect JSON, aggregate critical findings
for host in $(cat hosts.txt); do
    testssl.sh --jsonfile "json/${host//[:\/]/_}.json" -U --quiet "$host"
done

# Aggregate all critical findings:
cat json/*.json | jq -s 'add | .[] | select(.severity == "CRITICAL") | {host: .ip, id: .id, finding: .finding}' | sort -u

# Generate HTML reports for all hosts
for host in $(cat hosts.txt); do
    testssl.sh -oH "html/${host//[:\/]/_}.html" -U -p -s "$host"
done
```
