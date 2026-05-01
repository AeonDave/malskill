# Tool selection by case

## Purpose

Map common network investigation scenarios to the most effective tool families.

## Case matrix

| Scenario | Primary family | Secondary family | Why this order |
|---|---|---|---|
| Large network exposure census | `masscan` / `rustscan` | `nmap` | Fast breadth first, precision second |
| Targeted service fingerprinting | `nmap` | `wireshark` | Version/script context before packet deep dive |
| Suspicious DNS/TLS behavior | `zeek` | `wireshark` | Metadata pivots quickly, packets for confirmation |
| HTTP(S) app-flow inspection | `mitmproxy` | `wireshark` | Request/response semantics first, packet verification as needed |
| LAN interception suspicion | `bettercap` context + network logs | `wireshark` | Validate ARP/L2 behavior with packet evidence |
| Segmented network reachability | `ligolo-ng` / `chisel` | `nmap` | Establish path, then scoped recon |
| Credential relay suspicion | `responder` context + protocol logs | `zeek` / `wireshark` | Attribute relay path and protocol evidence |

## Practical selection rules

- If scope is broad and unknown: start with fast discovery, not deep inspection.
- If claim requires payload proof: include packet-level confirmation.
- If encrypted traffic limits visibility: pivot on metadata (SNI, JA3/JA4-like fingerprints, timing, flow asymmetry).
- If time-critical triage: prioritize conn/dns/http/tls summaries before full PCAP archaeology.

## Safety and quality checks

- Keep scan rates aligned to environment sensitivity.
- Prefer read-observe workflows before modify-intercept workflows.
- Separate “can reach service” from “service is exploitable” in reporting.
