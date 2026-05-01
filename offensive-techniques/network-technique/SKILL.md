---
name: network-technique
description: "Technique-first network investigation methodology for incident-driven triage, service exposure mapping, traffic analysis, and pivoting across scan, packet, and protocol logs. Use when you need to choose the right network tool family per case, reconstruct attacker movement, and produce evidence-backed conclusions without turning the skill into a per-tool command manual."
license: MIT
compatibility: "Linux/Windows/macOS; internal/external networks; PCAP and live traffic"
metadata:
  author: AeonDave
  version: "1.1"
  category: network
  language: multi
---

# Network technique

Goal: move from **network signal to validated finding** quickly, with reproducible triage and clear pivot logic.

## When this technique applies

- Need to triage suspected network intrusion or anomalous traffic.
- Need to map exposed services before deeper testing.
- Need protocol-level reconstruction from PCAP or sensor logs.
- Need cross-source correlation (scan + metadata logs + packets).
- Need scenario-based tool selection instead of one-tool-for-all.

## Boundary with offensive-tools

This skill defines **workflow, triage decisions, and pivot strategy**.
Tool flags and command syntax belong in `offensive-tools/*` skills.

## Agent operating model

The agent should keep this loop:

1. Scope objective and boundary.
2. Classify case type (exposure, traffic, interception, pivot, auth-abuse).
3. Collect minimum high-value evidence first.
4. Pivot and correlate across sources.
5. Validate with independent evidence.
6. Report findings with confidence and containment actions.

Do not increase depth before ensuring timeline/scope normalization and reproducible pivots.

## Core network investigation lifecycle

1. **Scope**: define target boundary, timeframe, and objective.
2. **Triage**: classify the problem type (exposure, traffic anomaly, interception, pivot/tunnel).
3. **Collect**: choose minimum high-value telemetry first.
4. **Pivot**: correlate identities (IP/port/session UID/process/user where available).
5. **Validate**: confirm key claims with independent evidence.
6. **Conclude**: document facts, confidence, and containment/next actions.

## Triage-first decision model

### Case A: “What is exposed right now?”

Use scan-first workflow.

- Fast census for breadth, then deep service validation for precision.
- Separate discovery and validation phases; don’t jump to intrusive probing immediately.

Tool families:
- Discovery breadth: `offensive-tools/network/masscan/`, `offensive-tools/network/rustscan/`
- Validation depth: `offensive-tools/network/nmap/`

### Case B: “What happened on the wire?”

Use metadata-first + packet drilldown workflow.

- Start from connection/protocol summaries.
- Pivot to packet-level only for sessions that materially change conclusions.

Tool families:
- Metadata and protocol logs: `offensive-tools/forensic/zeek/`
- Packet capture or replay context: `offensive-tools/forensic/tcpdump/`
- Deep packet reconstruction: `offensive-tools/network/wireshark/`

### Case C: “Need controlled interception/modification for app-network behavior”

Use proxy/MITM workflow.

- Establish legal/scope approval first.
- Use interception to validate request/response behavior and trust boundaries.

Tool families:
- HTTP(S) interception and replay: `offensive-tools/network/mitmproxy/`
- L2/LAN interception scenarios: `offensive-tools/network/bettercap/`

### Case D: “Need lateral/pivot path into segmented network”

Use tunnel/pivot workflow.

- Validate route assumptions before wide scanning through tunnel.
- Keep pivot traffic scoped to objective-defined targets.
- After tunnel is established, route arbitrary tools through it with proxychains — avoids rebuilding the pivot for each tool.

Tool families:
- Agent-based pivoting: `offensive-tools/network/ligolo-ng/`
- HTTP tunnel fallback: `offensive-tools/network/chisel/`
- Tool routing through SOCKS proxy: `offensive-tools/network/proxychains/`

### Case E: “Suspected credential relay/poisoning or auth abuse”

Use auth-abuse workflow.

- Prioritize evidence of request origin, relay path, and affected protocol surfaces.
- Correlate timing with SMB/LDAP/Kerberos-related logs and host events.

Tool families:
- Poisoning/relay context: `offensive-tools/network/responder/`
- Supporting protocol evidence: `offensive-tools/forensic/zeek/`, `offensive-tools/network/wireshark/`

### Case F: “Need lightweight socket probe, relay, or file transfer without a full tool”

Use netcat workflow.

- Banner grab, port probe, quick TCP/UDP listener, or pipe-based file transfer.
- Use when a full scanner or proxy tool is too heavy or unavailable.
- Keep sessions documented; netcat leaves no persistent state.

Tool families:
- `offensive-tools/network/netcat/`

### Case H: “Windows/Active Directory network enumeration after credential capture”

Use credential-validation and lateral enumeration workflow.

- Validate captured credentials across all reachable Windows hosts before attempting exploitation.
- Enumerate shares, sessions, logged-on users, and local admin rights to identify high-value pivot targets.
- Correlate SMB signing status — unsigned hosts are relay targets; signed hosts require valid credentials.
- Use spray carefully: lockout policies are common in AD environments.

Tool families:
- `offensive-tools/network/crackmapexec/` — SMB/WinRM/LDAP credential validation, share enumeration, command execution, hash spraying

### Case G: “Wireless/RF traffic capture or network presence on 802.11/BLE”

Use wireless investigation workflow.

- Passive monitoring first: capture beacon frames to inventory SSIDs and clients before active association.
- Identify relevant APs: channel, BSSID, encryption type (WPA2/WPA3/OPN).
- Capture four-way handshake or PMKID for offline analysis (pair with `offensive-tools/cracking/`).
- BLE enumeration uses a separate adapter and tool family.

Tool families:
- `offensive-tools/wireless/kismet/` — passive 802.11/BLE survey and logging
- `offensive-tools/wireless/aircrack-ng/` — capture, deauth, handshake collection
- `offensive-tools/wireless/wifite/` — automated multi-target WPA handshake collection

## Quality gates

- Scope, authorization, and time window are explicit.
- At least one finding is corroborated by two independent data sources.
- Any claim of exploitation is separated from exposure-only evidence.
- Output includes exact pivot chain used to reach each conclusion.

## Anti-patterns

- Running deep packet analysis on everything before metadata triage.
- Treating fast scanner output as final truth without validation.
- Mixing data from unmatched time windows and calling it a single narrative.
- Reporting “likely compromised” without a clear evidence chain.

## Required deliverables from the agent

1. Scope model and investigation objective.
2. Case classification and rationale.
3. Evidence chain with pivot sequence.
4. Key findings with confidence labels.
5. Follow-up actions linked to evidence.

## Resources

- [references/triage-and-flow.md](references/triage-and-flow.md)
- [references/tool-selection-cases.md](references/tool-selection-cases.md)
- [references/network-evidence-correlation.md](references/network-evidence-correlation.md)
- [references/scenario-playbooks.md](references/scenario-playbooks.md)
