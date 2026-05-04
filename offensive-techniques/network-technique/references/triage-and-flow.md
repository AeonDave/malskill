# Triage and flow

## Purpose

Provide a deterministic first-pass process that routes investigations to the right network workflow quickly.

## 1) Intake questions (always first)

- What is the objective? (exposure map, incident reconstruction, interception test, pivoting)
- What is the evidence source? (live traffic, PCAP, sensor logs, scan output)
- What is the time window and scope boundary?
- What is the risk tolerance? (safe discovery vs intrusive testing)

## 2) First-pass classification

- **Exposure problem**: unknown open ports/services or attack surface drift.
- **Traffic behavior problem**: suspicious sessions, unusual DNS/TLS/HTTP patterns.
- **Interception/testing problem**: need to inspect/modify application traffic.
- **Pivot/reachability problem**: target is behind segmentation.
- **Auth-abuse problem**: suspicious relay/poisoning/credential events.

## 3) Collection order by signal value

1. Existing high-level metadata (conn/protocol logs, historical scan baseline).
2. Focused scan/validation for suspect hosts/services.
3. Focused packet capture for sessions that change hypothesis confidence.
4. Optional interception or tunnel testing if required by objective.

NetFlow, sFlow, IPFIX, cloud flow logs, or Zeek `conn.log` can replace full packet capture for initial scoping when payload visibility is unavailable. Use metadata to bound host pairs, timing, byte counts, and protocol hypotheses; escalate to packets only when content or protocol semantics materially affect confidence.

## 4) Pivot discipline

Use stable pivots in this order:
- time window → host pair → protocol → session identifier → payload/artifact.

Never pivot only on a single IOC string without confirming context.

## 5) Evidence confidence labels

- **High**: same conclusion supported by two independent sources.
- **Medium**: one direct source + one contextual source.
- **Low**: plausible interpretation without corroboration.

## 6) Exit criteria

- Root question answered or narrowed with explicit uncertainty.
- Reproducible sequence documented.
- Containment/hardening actions tied directly to evidence.
