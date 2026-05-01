---
name: zeek
description: |
  Protocol-aware network analysis engine that converts raw PCAP or live traffic into structured logs
  (conn.log, dns.log, http.log, ssl.log, files.log, etc.). Use on any .pcap/.pcapng file to extract
  DNS queries, HTTP requests/responses, TLS certificates, file transfers, connection summaries, and
  anomalies. Faster and more structured than Wireshark for scripted analysis. Integrates with zeek-cut
  and standard UNIX tools for rapid investigation.
license: BSD-3-Clause
compatibility: "Linux/macOS primary. apt install zeek. zeek.org. Also available via Docker."
metadata:
  author: AeonDave
  version: "2.1"
---

# Zeek

PCAP → structured protocol logs. Extracts DNS, HTTP, TLS, files, connections into queryable log files.

## Installation

```bash
# Debian/Ubuntu/Kali
sudo apt install zeek
# or
sudo apt install zeek-core zeekctl

# macOS
brew install zeek

# Docker (no install)
docker run -v $(pwd):/pcap -w /pcap zeek/zeek zeek -r capture.pcap

# Verify
zeek --version
```

---

## Basic Usage

```bash
# Analyze PCAP — generates log files in current directory
zeek -r capture.pcap

# JSON output (easier to parse)
zeek -r capture.pcap LogAscii::use_json=T

# Live capture
zeek -i eth0 -C   # -C ignores checksum errors (common on virtualized interfaces)

# Analyze with all scripts (more detailed output)
zeek -r capture.pcap local
```

---

## Log Files Reference

After running Zeek, logs appear in the current directory:

| Log file | Content |
|----------|---------|
| `conn.log` | All TCP/UDP/ICMP connections: IPs, ports, bytes, duration, state |
| `dns.log` | DNS queries and responses — domains, record types, answers |
| `http.log` | HTTP requests/responses — method, URI, host, user-agent, status, mime |
| `ssl.log` | TLS handshakes — SNI, certificate subject, version, cipher |
| `x509.log` | Certificate details — subject, issuer, validity |
| `files.log` | Files transferred — MD5, SHA1, MIME, source/dest |
| `smtp.log` | Email metadata |
| `ftp.log` | FTP commands and responses |
| `ssh.log` | SSH connection details |
| `dhcp.log` | DHCP requests/leases |
| `weird.log` | Protocol anomalies — malformed packets, unusual behavior |
| `notice.log` | Zeek-generated alerts (scanning, brute force, etc.) |
| `capture_loss.log` | Packet drops during capture |

---

## zeek-cut: Fast Log Querying

`zeek-cut` extracts specific columns from Zeek tab-separated logs.

```bash
# Extract specific fields from conn.log
cat conn.log | zeek-cut id.orig_h id.resp_h id.resp_p proto bytes_recv

# Extract DNS query names
cat dns.log | zeek-cut query

# Top DNS queries
cat dns.log | zeek-cut query | sort | uniq -c | sort -rn | head 20

# HTTP hostnames + URIs
cat http.log | zeek-cut host uri | sort -u

# TLS SNI names
cat ssl.log | zeek-cut server_name | sort | uniq -c | sort -rn

# Unique destination IPs + ports
cat conn.log | zeek-cut id.resp_h id.resp_p | sort -u
```

---

## Investigation Workflows

### Workflow 1: PCAP quick triage

```bash
zeek -r capture.pcap 2>/dev/null

# Top talkers (most bytes sent)
cat conn.log | zeek-cut id.orig_h orig_bytes | sort -t$'\t' -k2 -rn | head 10

# Top destinations
cat conn.log | zeek-cut id.resp_h id.resp_p | sort | uniq -c | sort -rn | head 20

# Protocols seen
cat conn.log | zeek-cut proto | sort | uniq -c

# Connection states (S1=established, RSTO=reset, SF=normal close, etc.)
cat conn.log | zeek-cut conn_state | sort | uniq -c | sort -rn
```

### Workflow 2: DNS analysis

```bash
# All queried domains
cat dns.log | zeek-cut query | sort | uniq -c | sort -rn

# DNS over specific port (look for DNS tunneling on non-53)
cat conn.log | zeek-cut id.resp_p proto | grep "^53" | wc -l

# Unusually long DNS names (tunneling indicator)
cat dns.log | zeek-cut query | awk 'length($0) > 50'

# DNS answers (what IPs domains resolved to)
cat dns.log | zeek-cut query answers | grep -v "-"

# Failed DNS lookups
cat dns.log | zeek-cut query rcode_name | grep -v "NOERROR"

# Find specific domain
cat dns.log | zeek-cut ts query answers | grep "evil.com"
```

### Workflow 3: HTTP analysis

```bash
# All HTTP hosts + URIs
cat http.log | zeek-cut host uri method status_code | head 50

# POST requests (data exfiltration / form submits)
cat http.log | zeek-cut host uri method | grep "^POST\|	POST"
# or
awk -F'\t' '$13 == "POST"' http.log | zeek-cut host uri

# User agents (malware often uses static or unusual UAs)
cat http.log | zeek-cut user_agent | sort | uniq -c | sort -rn

# File downloads
cat http.log | zeek-cut host uri resp_mime_types | grep -v "text/html\|text/css\|image"

# Unusual status codes
cat http.log | zeek-cut host uri status_code | grep -v "200\|301\|302\|304"

# Find specific string in URIs
cat http.log | zeek-cut uri | grep -i "shell\|cmd\|upload\|admin\|backdoor"
```

### Workflow 4: TLS/SSL certificate analysis

```bash
# SNI names (what domains TLS connections go to)
cat ssl.log | zeek-cut server_name | sort | uniq -c | sort -rn

# Self-signed or unusual certs
cat ssl.log | zeek-cut server_name validation_status | grep -v "ok\|-"

# TLS version distribution (look for old TLS 1.0/1.1)
cat ssl.log | zeek-cut version | sort | uniq -c

# Certificate subject (from x509.log)
cat x509.log | zeek-cut certificate.subject certificate.issuer | head 20

# JA3 fingerprints (malware TLS fingerprinting)
cat ssl.log | zeek-cut ja3 ja3s server_name | sort -u
```

### Workflow 5: File extraction

```bash
# Files detected in traffic
cat files.log | zeek-cut filename mime_type md5 sha1 tx_hosts

# Extract files from PCAP (requires file extraction script)
zeek -r capture.pcap extract-all-files.zeek
ls extract_files/

# Or with built-in script
zeek -r capture.pcap frameworks/files/extract-all-files.zeek FileExtract::PREFIX="files/"

# Find by MIME type
cat files.log | zeek-cut filename mime_type | grep -i "application/x-executable\|application/x-dosexec\|application/zip"
```

### Workflow 6: Anomaly detection

```bash
# Check weird.log for protocol anomalies
cat weird.log | zeek-cut name peer | sort | uniq -c | sort -rn

# Scan detection in conn.log (many connections, short duration)
cat conn.log | zeek-cut id.orig_h id.resp_h duration | awk -F'\t' '$3 < 0.1' | wc -l

# Long connections (C2 beaconing)
cat conn.log | zeek-cut id.orig_h id.resp_h duration | sort -t$'\t' -k3 -rn | head 10

# Beaconing pattern: many equal-interval connections to same host
cat conn.log | zeek-cut ts id.orig_h id.resp_h | grep "SUSPECT_IP" | awk '{print $1}' | \
  awk 'NR>1{printf "%.0f\n", $1-prev} {prev=$1}' | sort | uniq -c

# Large data transfers (exfiltration)
cat conn.log | zeek-cut id.orig_h id.resp_h orig_bytes resp_bytes | \
  awk -F'\t' '$3 > 1000000 || $4 > 1000000' | sort -t$'\t' -k3 -rn
```

### Workflow 7: Credential and sensitive data hunting

```bash
# HTTP Basic Auth (base64 credentials in headers)
cat http.log | zeek-cut host uri username password | grep -v "^-"

# FTP credentials
cat ftp.log | zeek-cut user password | grep -v "^-\|-$"

# SMTP from/to
cat smtp.log | zeek-cut mailfrom rcptto | grep -v "^-"
```

---

## Common Field Reference

**conn.log key fields:**
```
ts            - timestamp
uid           - unique connection ID (pivot key)
id.orig_h     - source IP
id.orig_p     - source port
id.resp_h     - destination IP
id.resp_p     - destination port
proto         - tcp/udp/icmp
service       - detected protocol
duration      - connection duration
orig_bytes    - bytes sent by originator
resp_bytes    - bytes sent by responder
conn_state    - S1/SF/S0/REJ/RSTO etc
```

**conn_state values:**
| State | Meaning |
|-------|---------|
| `SF` | Normal established + closed |
| `S0` | SYN sent, no response (host down/filtered) |
| `S1` | Established, not closed (ongoing or truncated) |
| `REJ` | Connection rejected (RST) |
| `RSTO` | Originator sent RST |
| `OTH` | Mid-stream/no SYN seen |

---

## Cross-Log Correlation via UID

The `uid` field connects related entries across log files.

```bash
# Find suspicious connection UID
cat conn.log | zeek-cut uid id.resp_h id.resp_p | grep "evil.com_IP"

# Use uid to find HTTP activity
cat http.log | zeek-cut uid host uri | grep "SUSPECT_UID"

# Use uid to find transferred files
cat files.log | zeek-cut uid filename md5 | grep "SUSPECT_UID"

# Full correlation script
UID="CuV6ij35YMRJBbIEr1"
cat conn.log | zeek-cut uid id.orig_h id.resp_h | grep "$UID"
cat http.log | zeek-cut uid host uri method | grep "$UID"
cat files.log | zeek-cut uid filename mime_type md5 | grep "$UID"
```

---

## Quick Tricks

```bash
# Find investigation indicators in HTTP URIs or bodies
cat http.log | zeek-cut uri | grep -iE "token|secret|key|indicator"

# Find cleartext credentials in HTTP
cat http.log | zeek-cut host uri username password | awk -F'\t' '$4 != "-"'

# Convert Zeek timestamps to human-readable
cat conn.log | zeek-cut ts id.resp_h | awk '{print strftime("%Y-%m-%d %H:%M:%S", $1), $2}'

# Count connections per minute (detect bursts)
cat conn.log | zeek-cut ts | awk '{print strftime("%H:%M", $1)}' | uniq -c

# Extract all domains ever queried
cat dns.log | zeek-cut query | sort -u > all_domains.txt
```

---

## Integration

| Tool | Use case |
|------|---------|
| `wireshark` / `tshark` | Deep packet inspection after Zeek identifies the session |
| `tcpdump` | Initial PCAP acquisition |
| `strings` / `binwalk` | Analyze extracted files from `files.log` |
| `jq` | Parse JSON-format Zeek logs |
| `yara` | Scan extracted file objects for malware signatures |
| `openssl` | Inspect certificate details from x509.log |

## Resources

| File | When to load |
|------|--------------|
| `references/` | Zeek scripting basics, custom log fields, DNS tunneling detection, JA3 usage |
