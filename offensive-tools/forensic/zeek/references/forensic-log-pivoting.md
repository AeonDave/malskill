# Zeek — Deep Reference

## Complete Log Field Reference

### conn.log

```
ts uid id.orig_h id.orig_p id.resp_h id.resp_p proto service
duration orig_bytes resp_bytes conn_state missed_bytes history
orig_pkts orig_ip_bytes resp_pkts resp_ip_bytes
```

`conn_state` values:
| State | Meaning |
|-------|---------|
| `SF` | Normal SYN+data+FIN — full connection |
| `S0` | SYN only — no response (filtered/down) |
| `S1` | Established, not terminated (captured mid-session) |
| `S2` | Initiator closed, responder still open |
| `S3` | Responder closed, initiator still open |
| `REJ` | SYN+RST — port closed |
| `RSTO` | Originator sent RST |
| `RSTR` | Responder sent RST |
| `OTH` | No SYN, mid-flow |

### dns.log

```
ts uid id.orig_h id.orig_p id.resp_h id.resp_p proto trans_id
rtt query qclass qclass_name qtype qtype_name rcode rcode_name
AA TC RD RA Z answers TTLs rejected
```

### http.log

```
ts uid id.orig_h id.orig_p id.resp_h id.resp_p
trans_depth method host uri referrer version user_agent
request_body_len response_body_len status_code status_msg
resp_mime_types filename tags
```

### ssl.log

```
ts uid id.orig_h id.orig_p id.resp_h id.resp_p
version cipher curve server_name resumed next_protocol established
cert_chain_fuids client_cert_chain_fuids
subject issuer validation_status ja3 ja3s
```

### files.log

```
ts fuid tx_hosts rx_hosts conn_uids source depth
analyzers filename duration local_orig is_orig seen_bytes
total_bytes missing_bytes overflow_bytes timedout
md5 sha1 sha256 extracted extracted_cutoff
```

---

## JSON Log Parsing with jq

```bash
# Run Zeek in JSON mode
zeek -r capture.pcap LogAscii::use_json=T

# Parse conn.log with jq
cat conn.log | jq -r '[.["id.orig_h"], .["id.resp_h"], .["id.resp_p"], .proto] | @tsv'

# Top destination IPs from conn.log JSON
cat conn.log | jq -r '."id.resp_h"' | sort | uniq -c | sort -rn | head

# DNS queries from JSON
cat dns.log | jq -r '.query' | sort | uniq -c | sort -rn

# HTTP POST with body
cat http.log | jq 'select(.method == "POST") | {host, uri, request_body_len}'

# Large response bodies (potential data delivery)
cat http.log | jq 'select(.response_body_len > 100000) | {host, uri, response_body_len}'
```

---

## JA3 / JA3S TLS Fingerprinting

JA3 fingerprints TLS client hello; JA3S fingerprints server hello.

```bash
# Zeek generates JA3/JA3S in ssl.log (requires ssl-fingerprinting package)
# Install: zkg install salesforce/ja3

# View JA3 hashes
cat ssl.log | zeek-cut ja3 ja3s server_name | sort -u

# Known malware JA3 hashes (examples):
# 51c64c77e60f3980eea90869b68c58a8 — Metasploit Meterpreter
# 6734f37431670b3ab4292b8f60f29984 — Cobalt Strike
# de9f0a2d14c6a3f8d7ddd0c31b5fcfe5 — IcedID
grep "51c64c77e60f3980eea90869b68c58a8\|6734f37431670b3ab4292b8f60f29984" ssl.log

# Compare client JA3 across sessions (same malware = same JA3)
cat ssl.log | zeek-cut ja3 | sort | uniq -c | sort -rn
```

---

## DNS Tunneling Detection

```bash
# Long subdomain queries (tunneling encodes data in labels)
cat dns.log | zeek-cut query | awk 'length > 50' | sort | uniq -c | sort -rn

# High query rate to single domain (automated tunneling)
cat dns.log | zeek-cut query | sed 's/.*\.\(.*\.\w\+\)$/\1/' | sort | uniq -c | sort -rn | head

# Unusual record types (TXT, NULL common in tunneling)
cat dns.log | zeek-cut qtype_name | sort | uniq -c | sort -rn
# TXT and NULL types over non-trivial count = suspicious

# High entropy domain names (base32/base64 encoded data)
cat dns.log | zeek-cut query | python3 -c "
import sys, math, collections
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    freq = collections.Counter(line)
    entropy = -sum((c/len(line)) * math.log2(c/len(line)) for c in freq.values())
    if entropy > 4.0 and len(line) > 30:
        print(f'{entropy:.2f} {line}')
" | sort -rn | head 20
```

---

## Zeek Scripting: Custom Detection

### Script to detect large DNS responses (tunneling)

```zeek
# dns-large-responses.zeek
event dns_message(c: connection, is_orig: bool, msg: dns_msg, len: count)
{
    if (!is_orig && len > 512)
        print fmt("Large DNS response: %s %s len=%d", c$id$orig_h, msg$query, len);
}
```

```bash
zeek -r capture.pcap dns-large-responses.zeek
```

### Script to detect C2 beaconing (regular intervals)

```zeek
# beacon-detect.zeek
global conn_times: table[addr, addr] of vector of time;

event connection_established(c: connection)
{
    local key = [c$id$orig_h, c$id$resp_h];
    if (key !in conn_times)
        conn_times[key] = vector();
    conn_times[key] += network_time();
}

event zeek_done()
{
    for ([src, dst] in conn_times) {
        local times = conn_times[src, dst];
        if (|times| > 10) {
            print fmt("Potential beacon: %s -> %s (%d connections)", src, dst, |times|);
        }
    }
}
```

### Script to extract files from HTTP

```bash
# Built-in file extraction
zeek -r capture.pcap frameworks/files/extract-all-files.zeek FileExtract::PREFIX="extracted/"
ls extracted/
file extracted/*
```

---

## zeek-cut Cheatsheet

```bash
# Syntax: cat <log> | zeek-cut field1 field2 ...

# conn.log
cat conn.log | zeek-cut ts id.orig_h id.resp_h id.resp_p proto duration

# dns.log
cat dns.log | zeek-cut ts query qtype_name answers

# http.log
cat http.log | zeek-cut ts id.orig_h host uri method status_code user_agent

# ssl.log
cat ssl.log | zeek-cut ts id.orig_h server_name ja3 validation_status

# files.log
cat files.log | zeek-cut ts tx_hosts rx_hosts filename mime_type md5
```

---

## Common Grep Patterns on Zeek Logs

```bash
# Find any flag-like string across all logs
grep -rh "flag{" *.log 2>/dev/null

# Find specific IP in all logs
grep "10.10.10.99" conn.log http.log dns.log ssl.log

# Cleartext credentials in HTTP
grep -i "password\|passwd\|pass=" http.log

# Base64 in URI (potential encoded payload)
cat http.log | zeek-cut uri | grep -E "[A-Za-z0-9+/]{40,}={0,2}"

# Find file downloads by extension
cat http.log | zeek-cut uri | grep -iE "\.exe$|\.bat$|\.ps1$|\.dll$|\.sh$"
```
