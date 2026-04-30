---
name: zeek
description: "Zeek: network security monitoring and rich protocol logs from PCAP/live traffic. Use when you need forensic pivots across connection, HTTP, DNS, TLS, and anomaly logs, and when converting raw packet data into investigation-ready timelines."
license: BSD-3-Clause
compatibility: "Linux/macOS (primary), package/binary/source installs. zeek.org"
metadata:
  author: AeonDave
  version: "1.0"
---

# Zeek

Protocol-aware network forensics engine that turns packets into high-value logs.

## Quick Start

```bash
# from pcap (JSON logs)
zeek -r sample.pcap LogAscii::use_json=T

# live capture (local interface; checksum offload-friendly)
zeek -i eth0 -C
```

Common output logs: `conn.log`, `dns.log`, `http.log`, `ssl.log`, `weird.log`.

## Core Investigation Pivots

1. Start in `conn.log` for session overview.
2. Pivot by `uid` into `http.log`/`dns.log`/`ssl.log`.
3. Check `weird.log` for malformed/suspicious protocol behavior.
4. Build timeline and top talkers from `conn.log` fields.

## Practical Flow

- PCAP triage -> run Zeek -> identify suspect `uid` -> enrich with protocol logs.
- Extract suspicious domains/URIs/certs from DNS/HTTP/TLS logs.
- Correlate with endpoint artifacts (process execution, persistence, memory findings).

## Resources

| File | When to load |
|------|--------------|
| `references/forensic-log-pivoting.md` | uid-centric flow, quick log queries, and incident triage patterns |
