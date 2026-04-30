# tcpdump forensic capture flow

## Analyst workflow

1. Define objective (`exfil`, `beaconing`, `credential theft`, `lateral movement`).
2. Choose minimal BPF scope before capture (host/port/protocol/subnet).
3. Capture full packets (`-s 0`) into pcap for evidence portability.
4. Document interface, host timezone, start/stop timestamps, filter used.
5. Validate pcap readability and archive immutable copy.

## Useful BPF filters

```bash
# C2/beacon suspicion (common outbound channels)
'((tcp port 80 or 443 or 8080) or udp port 53) and host 10.10.10.25'

# brute-force/noisy auth over SMB/RDP
'(tcp port 445 or tcp port 3389) and host 10.10.10.50'

# DNS tunneling suspicion
'udp port 53 and greater 200'

# data exfil candidate: large outbound packets
'outbound and greater 1000'
```

## Tricks that save time

- Always use `-nn` in incident response to avoid DNS delays and evidence contamination from resolver lookups.
- Prefer multiple short captures over one massive file; align by incident phase.
- Keep capture filters simple first, then refine iteratively if traffic is too noisy.
- When in doubt, capture broader but for shorter time.

## Escalation path

- Need protocol semantics -> open in Wireshark/tshark.
- Need behavior baselining/log pivots -> process with Zeek.
- Need endpoint artifacts correlation -> align with memory/disk timeline.
