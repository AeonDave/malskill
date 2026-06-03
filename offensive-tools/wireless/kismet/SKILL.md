---
name: kismet
description: "Auth/lab ref: Passive wireless sniffer, WIDS, and wardriving platform for Wi-Fi, Bluetooth, Zigbee, and other RF sources."
license: MIT
compatibility: "Linux/macOS; requires compatible wireless adapter."
metadata:
  author: AeonDave
  version: "1.0"
---

# Kismet

Passive RF collection, WIDS, and wardriving platform for Wi‑Fi, Bluetooth, Zigbee, and more.

## Quick Start

```bash
apt install kismet

# Start with web UI (port 2501)
kismet -c wlan0

# Open web UI
open http://localhost:2501
# Default creds: kismet/kismet

# Capture to pcap
kismet -c wlan0 --log-types pcapppi
```

## Why Use It

Choose `kismet` when you need:
- passive discovery with minimal RF disturbance
- hidden SSID / client / rogue-device visibility
- long-running sensor logging
- multi-protocol visibility beyond Wi‑Fi
- distributed capture and automation via API

## Key Features

| Feature | Purpose |
|---------|---------|
| AP discovery | SSID, BSSID, channel, encryption, signal |
| Client tracking | Devices associated to APs |
| Bluetooth | BT classic + BLE scanning (with adapter) |
| Zigbee | IoT/sensor network detection |
| GPS integration | Map devices with gpsd |
| Logging | Kismet DB, pcap, JSON, netxml |

## Core Flags

| Flag | Purpose |
|------|---------|
| `-c IFACE` | Capture interface |
| `--no-logging` | Disable logging |
| `--log-prefix DIR` | Log output directory |
| `--log-types TYPE` | Log formats |
| `--daemonize` | Run in background |
| `--override wardriving` | Wardriving mode |

## Common Workflows

**Passive wardriving:**
```bash
kismet -c wlan0 --override wardriving --log-prefix /tmp/wardriving
```

**Capture all traffic for offline analysis:**
```bash
kismet -c wlan0 --log-types pcapppi --log-prefix /tmp/capture
# Analyze with wireshark
```

**Long-running passive logging with unified metadata:**
```bash
kismet -c wlan0 --log-prefix /tmp/kismet
```

## What Makes It Strong

- unified `kismetdb` logging for devices, packets, runtime data, and location
- distributed remote capture over network links
- comprehensive REST API for scripting and integrations
- better fit than cracking tools when the objective is awareness, baselining, or passive detection

## Best Fit

| Need | Better fit |
|------|------------|
| Passive WIDS / sensor platform | `kismet` |
| Handshake capture and cracking | `aircrack-ng` |
| Automated WPA/PMKID attacks | `wifite` |
| Combined Wi‑Fi/Bluetooth/HackRF GUI workflows | `sparrow-wifi` |

## Resources

| File | When to load |
|------|--------------|
| `references/distributed-capture-and-logging.md` | For kismetdb logging, remote capture, API usage, and passive multi-RF positioning |
