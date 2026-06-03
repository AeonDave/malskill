---
name: sparrow-wifi
description: "Auth/lab ref: Linux Wi-Fi and Bluetooth analyzer with GPS, remote agent, JSON API, and SDR integrations including HackRF One and Ubertooth."
license: GPL-3.0
compatibility: "Linux; Python 3.8+; desktop GUI and headless agent modes."
metadata:
  author: AeonDave
  version: "1.0"
---

# Sparrow-WiFi

Integrated Wi‑Fi / Bluetooth / SDR analysis platform for Linux with optional remote agent and HackRF/Ubertooth workflows.

## Why Use Sparrow-WiFi

Choose Sparrow when you need one platform for:
- Wi‑Fi scanning plus Bluetooth awareness
- source hunting / telemetry workflows
- spectrum overlays with HackRF One or Ubertooth One
- remote scanning via a JSON REST agent
- mobile, Pi, drone, or rover-mounted sensors

## Quick Start

```bash
# install deps (common Linux/Kali/Debian path)
git clone https://github.com/ghostop14/sparrow-wifi
cd sparrow-wifi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# run desktop app
sudo venv/bin/python3 ./sparrow-wifi.py
```

## Core Modes

| Component | Use |
|---|---|
| `sparrow-wifi.py` | Desktop GUI for Wi‑Fi/BT/spectrum awareness |
| `sparrowwifiagent.py` | Headless HTTP agent for remote sensors |
| `sparrow-droneid` | Drone RemoteID Wi‑Fi/BLE detection workflow |
| `sparrow-elastic.py` | Optional Elasticsearch / OpenSearch bridge |

## Hardware-Aware Use Cases

### Standard adapter only
- Wi‑Fi scanning
- BLE advertisement scanning
- GPS-assisted mapping

### With HackRF One
- 2.4 GHz and 5 GHz spectral overlays
- broader RF awareness alongside Wi‑Fi scans

### With Ubertooth One
- 2.4 GHz spectrum and deeper Bluetooth visibility

## Remote Agent Workflow

```bash
sudo ./sparrowwifiagent.py
# default API port 8020
```

Example API calls:

```bash
curl http://sensor:8020/wireless/interfaces
curl http://sensor:8020/wireless/networks/wlan0
curl http://sensor:8020/bluetooth/discoverystarta
curl http://sensor:8020/bluetooth/discoverystatus
```

## Why It Belongs in Wireless

Sparrow fills the gap not covered by the current category:
- Bluetooth-first workflows
- HackRF/Ubertooth-assisted spectrum analysis
- remote/headless wireless sensor deployment
- JSON/API-friendly automation

## Relationship to Other Skills

| Skill | Best use |
|---|---|
| `kismet` | Passive WIDS / long-running passive RF logging |
| `aircrack-ng` | Focused Linux monitor-mode capture and cracking workflows |
| `bluez` | Core Bluetooth CLI operations |
| `sparrow-wifi` | Combined Wi‑Fi/Bluetooth/SDR awareness with APIs and sensors |

## Resources

| File | When to load |
|---|---|
| `references/hackrf-bluetooth-agent-workflows.md` | For HackRF One, Bluetooth, remote agent, API, and hardware-selection workflows |
