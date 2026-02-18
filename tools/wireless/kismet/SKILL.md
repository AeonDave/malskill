---
name: kismet
description: "Wireless network detector and sniffer supporting Wi-Fi, Bluetooth, Zigbee, and SDR. Use when performing passive wireless reconnaissance, device tracking, or capturing traffic without active injection."
license: MIT
compatibility: "Linux/macOS; apt install kismet; requires compatible wireless adapter"
metadata:
  author: AeonDave
  version: "1.0"
---

# Kismet

Wireless detector and sniffer — passive Wi-Fi, Bluetooth, Zigbee, SDR.

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

## Resources

| File | When to load |
|------|--------------|
| `references/` | GPS setup, Bluetooth adapter config |
