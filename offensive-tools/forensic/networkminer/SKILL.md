---
name: networkminer
description: "Auth/lab ref: Network artifact extraction from PCAP files with NetworkMiner."
license: Freeware
compatibility: "Windows/Linux (via Mono in many setups); GUI-first workflow."
metadata:
  author: AeonDave
  version: "1.0"
---

# NetworkMiner

Session-centric network forensics and object extraction from PCAP evidence.

## When to use

- You need rapid host/session overview from `.pcap`/`.pcapng` files.
- You need extracted files, credentials, DNS/HTTP metadata, or transferred objects.
- You need evidence-first triage before deep packet dissection.
- You need to pivot quickly from network traces to investigation artifacts.

## Core workflow

1. Load PCAP and enumerate hosts, sessions, and protocols.
2. Review extracted objects (files, credentials, parameters, certificates).
3. Build communication sequence by source/destination and service.
4. Export relevant artifacts for corroboration with endpoint evidence.
5. Record exact packet/session references for each conclusion.

## High-value analyst views

- Host and endpoint inventory
- Parameters, credentials, and metadata extraction
- File/object extraction with hashes
- DNS/HTTP/TLS indicators and session timelines

## Practical analyst tips

- Start with broad host/session triage, then pivot to suspicious flows.
- Validate extracted credentials or payload claims against packet context.
- Keep exports organized per case objective (not per protocol only).
- Correlate extracted artifacts with endpoint timelines for confidence uplift.

## Common pitfalls

- Treating extracted strings as confirmed execution evidence.
- Ignoring retransmissions/fragmentation effects on interpretation.
- Losing traceability by exporting artifacts without packet/session references.
- Performing deep extraction before defining investigative objectives.

## Output expectations

- Host/session summary aligned to investigation objectives.
- Extracted artifacts list (files, credentials, metadata) with source references.
- Timeline-ready network findings for cross-source correlation.
