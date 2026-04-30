# Kismet Distributed Capture & Logging

## Why Kismet

Kismet is strongest when you need **passive** multi-protocol RF visibility and not just Wi‑Fi cracking.

Use it for:
- passive Wi‑Fi discovery
- hidden SSID / client observation
- Bluetooth and other RF collection with supported hardware
- multi-sensor capture
- long-running logging and later analysis

## Basic Local Start

```bash
kismet -c wlan0
```

Web UI typically runs on port `2501`.

## Logging Formats

Kismet can log to multiple formats. The important one to know is the unified SQLite-based `kismetdb` logfile.

Useful capture style:

```bash
kismet -c wlan0 --log-prefix /tmp/kismet --log-types pcapppi
```

## Distributed Capture Model

Kismet supports remote capture over TCP / websockets.

This is useful when:
- the analyst box is not in the best RF position
- you want multiple sensors across a building/site
- you want one central collector with several remote radios

## When Kismet Beats Aircrack-ng

| Need | Better fit |
|---|---|
| Passive RF recon | Kismet |
| Long-running sensor logging | Kismet |
| Hidden SSID / rogue device visibility | Kismet |
| Fast handshake capture workflow | Aircrack-ng / Wifite |

## Bluetooth / Multi-RF Notes

With proper hardware, Kismet can collect beyond Wi‑Fi:
- Bluetooth
- Zigbee / 802.15.4
- other RF data sources

The limiting factor is almost always hardware + driver support.

## API Use

Kismet exposes a REST API, which makes it strong for automation and sensor pipelines.

Typical use cases:
- polling discovered devices
- integrating with dashboards
- triggering processing workflows after capture

## Hardware Guidance

- Use reliable Linux-supported adapters first.
- Validate monitor mode and channel hopping behavior before long runs.
- For specialized RF, pick hardware explicitly supported by Kismet and the target protocol.

## Source Pointers

- Kismet official site: 2025 major release, REST API, distributed capture, kismetdb
