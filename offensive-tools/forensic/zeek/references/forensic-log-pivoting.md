# Zeek forensic log pivoting

## High-value logs

- `conn.log`: session metadata baseline.
- `dns.log`: domains, query patterns, possible tunneling indicators.
- `http.log`: host, URI, methods, user agents.
- `ssl.log`/`x509.log`: cert and TLS metadata.
- `weird.log`: protocol anomalies worth escalation.

## Fast workflow

1. Run Zeek on pcap.
2. Sort/top count by originator/responders from `conn.log`.
3. Isolate suspicious `uid` and pivot to protocol-specific logs.
4. Flag uncommon methods, odd user agents, rare SNI/cert combinations.
5. Export suspect tuples (time, uid, src/dst, domain/uri) as investigation artifacts.

## Practical tips

- Use JSON logs (`LogAscii::use_json=T`) for easier downstream parsing.
- On live local monitoring, `-C` avoids losing packets due to checksum offload artifacts.
- Keep original pcap immutable; Zeek logs are derived evidence, not replacement.

## Escalation

- Need payload reconstruction -> Wireshark/tshark stream follow.
- Need memory/process context -> Volatility or endpoint EDR artifacts.
