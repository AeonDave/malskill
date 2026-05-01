# PCAP analysis workflow

## Purpose

Turn packet evidence into a clear activity sequence without drowning in packet-level noise.

## 1) Triage pass

- Build protocol hierarchy and top endpoints.
- Mark uncommon protocols/ports and rare external destinations.
- Identify candidate windows for initial access, beaconing, staging, and transfer.

## 2) Protocol pivots

- DNS: suspicious domains, DGAs, failed bursts, unusual query entropy.
- TLS: SNI/cert anomalies, self-signed or short-lived cert behavior.
- HTTP: suspicious URIs, object transfer patterns, unusual user agents.
- SMB/RDP/remote admin: movement and credential-use indicators.

## 3) Sequence reconstruction

- Create ordered session list (who initiated, direction, bytes, interval).
- Separate short repetitive beacon-like sessions from interactive sessions.
- Highlight transitions from discovery to execution to exfil-like transfers.

## 4) Endpoint correlation requirements

For every high-risk session, attempt to map:
- endpoint process,
- endpoint user/session,
- corresponding disk/memory artifact.

If no endpoint mapping exists, classify as unattributed network evidence.

## 5) Quality checks

- Verify timezone alignment with endpoint evidence.
- Confirm that packet loss or capture gaps do not invalidate claims.
- Distinguish observed traffic from inferred intent.

## 6) Output

- Session summary table (src, dst, protocol, purpose hypothesis).
- Ordered narrative of key network events.
- IOC set (domains, IPs, URIs, hashes where available).
