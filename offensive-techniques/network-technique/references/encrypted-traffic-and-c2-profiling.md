# Encrypted traffic and C2 profiling

Use this when payload content is unavailable but network metadata suggests beaconing, command-and-control, tunneling, or automated malware communication.

## Objective

Classify suspicious encrypted or opaque traffic by combining TLS/JA3/JA4 metadata, DNS behavior, flow timing, endpoint context, and packet-level drilldown. Do not declare C2 from one fingerprint alone.

## 1) Metadata-first collection

Collect the smallest evidence set that can explain the behavior:

- Time window, source host, destination IP/domain, protocol, port, byte counts.
- DNS: query name, answer set, TTL, NXDOMAIN rate, fast-flux signs, DoH/DoT use.
- TLS: SNI, ALPN, certificate issuer/subject/SAN, validity window, JA3/JA4/JA4S when available.
- HTTP(S): user-agent, method cadence, URL shape if visible, response size pattern.
- Flow: connection interval, jitter, burst pattern, upload/download ratio, session duration.
- Endpoint/process context if available: process name, command line, parent, user.

Preferred tools: `offensive-tools/forensic/zeek/`, `offensive-tools/forensic/tcpdump/`, `offensive-tools/network/wireshark/`.

## 2) TLS fingerprinting workflow

JA3 fingerprints the TLS ClientHello; JA4/JA4+ improves resilience against extension-order randomization and adds broader protocol context such as ALPN, SNI behavior, HTTP, SSH, QUIC, and timing-style features.

Use fingerprints as clustering pivots, not final proof:

1. Group flows by JA3/JA4 + destination ASN/domain + process context.
2. Compare against known-good software on the same host class.
3. Look for uncommon libraries in unexpected processes: Go/Node/Python clients from Office, script hosts, temp paths, or service accounts.
4. Check certificate anomalies: self-signed, short-lived, reused certs, mismatched SNI/SAN, rare issuer for the org.
5. Correlate timing: fixed interval plus bounded jitter is stronger than fingerprint alone.

## 3) Beaconing and jitter analysis

C2 often checks in at configurable intervals with optional jitter. Build an interval table:

| Feature | Suspicious when |
|---|---|
| Inter-arrival time | Regular interval or randomized bounded jitter |
| Byte symmetry | Small request, small predictable response over long window |
| Destination stability | Same host/URI path with repeated cadence |
| Sleep pattern | Activity pauses/resumes with user logon or sandbox windows |
| Burst follow-up | Beacon then larger download/upload after command tasking |

False positive controls: software updates, telemetry agents, EDR, browser sync, chat clients, cloud storage, monitoring probes.

## 4) DNS C2 and tunneling cues

Prioritize these pivots:

- High-entropy labels, long subdomains, many unique labels per parent domain.
- TXT/NULL record abuse or unusual query types.
- Low TTL with rapidly changing answers.
- Regular query cadence from one host to rare domains.
- Failed-query bursts, DGAs, or algorithmic-looking labels.

Escalate from Zeek DNS logs to packet drilldown only for domains that change the conclusion.

## 5) Evidence confidence ladder

| Level | Evidence |
|---|---|
| Low | Rare destination or suspicious fingerprint only |
| Medium | Rare fingerprint plus beacon-like timing or DNS anomaly |
| High | Metadata pattern plus endpoint process lineage or malware artifact |
| Confirmed | Process/artifact, network pattern, and payload/config/IOC all align |

Report uncertainty explicitly. "JA3 matches malware family" is not enough if destination/process context contradicts it.

## 6) Handoff

- Need packet reconstruction or file extraction → `forensic-technique` PCAP workflow.
- Need host process validation → `post-exploit-technique` or defensive endpoint collection workflow.
- Need malware config extraction → `reversing-technique` / `malware-analysis`.
