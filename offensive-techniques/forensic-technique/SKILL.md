---
name: forensic-technique
description: "Technique-first digital forensics methodology for incident-driven investigations across disk images (E01/DD/RAW), ISO media, memory captures, and network PCAP evidence. Focuses on preservation, triage, timeline reconstruction, artifact correlation, and report-ready findings while mapping each phase to the right forensic tool family without becoming a per-tool command manual."
license: MIT
compatibility: "Linux/Windows/macOS; E01/RAW/DD/ISO/PCAP/memory evidence"
metadata:
  author: AeonDave
  version: "1.2"
  category: forensic
  language: multi
---

# Forensic technique

Goal: produce **defensible, reproducible findings** from heterogeneous evidence.

## When this technique applies

- Potential compromise requiring reconstruction of user/system activity.
- Evidence includes one or more of: disk image, ISO media, RAM dump, PCAP.
- Need to correlate endpoint, filesystem, and network timelines.
- Need report-ready output for incident response, legal, or internal review.

## Boundary with offensive-tools

This skill explains **methodology and decision flow**.
Tool-specific syntax belongs to `offensive-tools/*` skills.

## Agent operating model

The agent should keep this loop:

1. Preserve and scope evidence.
2. Prioritize by volatility and investigative value.
3. Examine source-specific artifacts.
4. Correlate across sources into one timeline.
5. Validate claims with independent corroboration.
6. Report facts, interpretation boundaries, and recommendations.

Do not move to deep extraction/carving before timeline framing and hypothesis definition.

## Core forensic model

1. **Preserve**: isolate evidence, hash, document chain-of-custody.
2. **Collect**: acquire additional required artifacts with minimal alteration.
3. **Examine**: parse artifacts by source type (disk, memory, network).
4. **Correlate**: build a unified timeline across sources.
5. **Conclude**: state what is supported by evidence vs assumptions.
6. **Report**: produce concise, reproducible findings and follow-up actions.

## Evidence-first prioritization

Use volatility and value to decide acquisition/examination order.

1. Live volatile artifacts (RAM, active connections, running processes)
2. Network evidence at risk of rotation (live captures, ephemeral logs)
3. Endpoint high-value non-volatile artifacts (event logs, browser data, registry)
4. Full disk image deep examination
5. Enrichment sources (threat intel, external context)

## Objective-driven workflows

### 1. Disk image investigation (E01/DD/RAW)

Use when you need file-system artifacts, deleted-content recovery, execution traces, and persistence evidence.

- Start with integrity + partition mapping.
- Enumerate file systems and prioritize user/profile, startup, logs, scheduled tasks, shell history.
- Build an initial timeline before deep carving.
- Recover/decode only artifacts linked to hypotheses (do not carve everything by default).
- Validate notable findings in at least one secondary source (e.g., link file + event log + registry).

Primary tool families:
- `offensive-tools/forensic/sleuth-kit/`
- `offensive-tools/forensic/autopsy/`
- `offensive-tools/forensic/ftk-imager/`
- `offensive-tools/forensic/yara/`
- `offensive-tools/forensic/capa/` — capability detection on extracted executables (identifies malware families, TTPs, embedded shellcode)

### 2. ISO media investigation

Use when the evidence is installer-like media, archives, or mounted image content.

- Verify hash and mount read-only.
- Inventory executable/script content and autorun-related metadata.
- Compare bundle contents against expected vendor structure and signatures.
- Extract suspicious binaries/configs for static triage and rule scanning.
- Correlate ISO-delivered artifacts with host execution traces from endpoint evidence.

Primary tool families:
- `offensive-tools/forensic/sleuth-kit/`
- `offensive-tools/rev/binwalk/`
- `offensive-tools/forensic/yara/`

### 3. PCAP/network forensics

Use when reconstructing communication, exfiltration paths, C2 patterns, or lateral movement.

- Build traffic summary first (top talkers, protocols, unusual destinations).
- Pivot by DNS, TLS metadata, HTTP objects, and transfer channels.
- Identify sequencing: initial access indicators, staging, beaconing, bulk transfer.
- Tie network sessions to endpoint process/user context when possible.

Primary tool families:
- `offensive-tools/forensic/zeek/`
- `offensive-tools/forensic/tcpdump/`
- `offensive-tools/network/wireshark/`

### 4. Memory-centered investigation

Use when malware is fileless/injected, or when disk evidence is incomplete.

- Enumerate processes/parents, command lines, sockets, loaded modules.
- Hunt for injected regions and anomalous memory protections.
- Extract process artifacts and correlate with on-disk binaries and PCAP events.
- Treat memory findings as high-confidence for “what was running now,” then confirm persistence on disk.

Primary tool families:
- `offensive-tools/forensic/volatility3/`
- `offensive-tools/forensic/yara/`
- `offensive-tools/forensic/capa/` — classify extracted process dumps or unpacked binaries against malware capability ruleset

### 5. Mixed-source incident reconstruction

Use when you have disk + PCAP + memory and need a single chronology.

- Create source-local timelines first.
- Normalize to a single timezone and clock offset model.
- Merge into one chronology with confidence tags:
  - Direct evidence (observed in source)
  - Corroborated evidence (confirmed by second source)
  - Inference (plausible but unconfirmed)
- Explicitly record competing explanations for ambiguous events.

### 6. Log-centric and objective-driven investigations

Use when evidence is mostly EVTX, registry hives, MFT snapshots, API trace logs, or objective-driven forensic tasks.

- Build an objective-to-artifact map first (which artifact can answer each objective decisively).
- Prefer deterministic extraction over broad hunting (exact key, exact event id, exact stream, exact record).
- For Windows log-heavy cases, prioritize: PowerShell ScriptBlock (4104), process creation (4688/Sysmon 1), service/task creation, Defender/AV alerts, and relevant registry keys.
- For API trace cases, reconstruct sequence by API dependency chain (enumeration → allocation/write → execution).
- Mark each conclusion as: direct artifact fact vs inferred interpretation.

Primary tool families:
- `offensive-tools/forensic/chainsaw/` — rapid EVTX triage: Sigma rule hunting, built-in detection patterns for common attack TTPs, timeline output from multiple log sources

## Practical quality gates

- Chain-of-custody and hash records exist for all primary evidence.
- At least one key claim is corroborated across two independent sources.
- Timeline includes both malicious and benign context to avoid narrative bias.
- Every IOC or behavioral claim has exact source pointer (artifact + timestamp).
- Report distinguishes fact, interpretation, and recommendation.

## Anti-patterns

- Starting with deep carving before timeline and hypothesis framing.
- Treating one artifact as conclusive without corroboration.
- Mixing local-time and UTC evidence without explicit normalization.
- Writing conclusion-first reports and backfilling evidence.

## Required deliverables from the agent

1. Evidence inventory with integrity state.
2. Source-specific findings with exact pointers.
3. Correlated timeline with confidence labels.
4. High-confidence claims vs inference boundary.
5. Report-ready conclusions and next actions.

## Resources

- [references/evidence-preservation.md](references/evidence-preservation.md)
- [references/disk-and-iso-analysis.md](references/disk-and-iso-analysis.md)
- [references/pcap-analysis.md](references/pcap-analysis.md)
- [references/memory-analysis.md](references/memory-analysis.md)
- [references/timeline-correlation.md](references/timeline-correlation.md)
- [references/lessons-learned-patterns.md](references/lessons-learned-patterns.md)
- [scripts/forensic_triage.py](scripts/forensic_triage.py)
