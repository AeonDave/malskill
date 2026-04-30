---
name: tcpdump
description: "tcpdump: low-level packet capture and BPF filtering for fast network forensics. Use when doing first-response packet triage, collecting minimal-scope evidence from live interfaces, validating suspicious connections, or building focused PCAPs for later deep analysis in Wireshark/Zeek."
license: BSD-3-Clause
compatibility: "Linux / macOS / *BSD / Windows (Npcap). tcpdump.org"
metadata:
  author: AeonDave
  version: "1.0"
---

# tcpdump

Fast CLI capture and filter tool for network-forensic collection.

## Quick Start

```bash
# list interfaces
tcpdump -D

# capture to file without name resolution
tcpdump -i eth0 -nn -s 0 -w case01.pcap

# targeted capture (DNS + HTTP/S)
tcpdump -i eth0 -nn -s 0 -w web_scope.pcap 'port 53 or port 80 or port 443'

# read capture with packet details
tcpdump -nn -tttt -r case01.pcap
```

## Forensic Capture Patterns

```bash
# suspicious host
tcpdump -i eth0 -nn -s 0 -w host_scope.pcap 'host 10.10.10.25'

# only successful TCP sessions (SYN+ACK)
tcpdump -i eth0 -nn 'tcp[tcpflags] & (tcp-syn|tcp-ack) == (tcp-syn|tcp-ack)'

# exclude noisy internal ranges
tcpdump -i eth0 -nn -s 0 -w ext_only.pcap 'not net 10.0.0.0/8 and not net 192.168.0.0/16'
```

## Practical Flow

1. Start with smallest defensible scope (host, subnet, protocol, time window).
2. Capture with `-nn -s 0 -w` to preserve full packets and avoid resolver noise.
3. Use strict BPF filter to avoid huge files and dropped packets.
4. Stop and hash artifacts immediately (SHA256) outside the tool.
5. Pivot deeper in `wireshark`/`tshark`/`zeek` for protocol-level investigation.

## Resources

| File | When to load |
|------|--------------|
| `references/forensic-capture-flow.md` | BPF recipes, triage tricks, and repeatable packet-forensics workflow |
