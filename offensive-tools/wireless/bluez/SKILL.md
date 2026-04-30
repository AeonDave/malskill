---
name: bluez
description: "BlueZ Bluetooth stack and CLI workflow for Linux, covering bluetoothctl-driven discovery, pairing, BLE inspection, and low-level troubleshooting utilities. Use when scanning Bluetooth Classic or BLE devices, validating adapter state, enumerating services/characteristics, or building Bluetooth reconnaissance workflows on Linux."
license: GPL-2.0 / LGPL-2.1
compatibility: "Linux. Core Bluetooth stack on Linux; recent upstream release 5.86. Includes tools and client workflows such as bluetoothctl and monitor utilities."
metadata:
  author: AeonDave
  version: "1.0"
---

# BlueZ

Linux Bluetooth stack and operator toolkit for Bluetooth Classic and BLE discovery, connection, and debugging.

## Why BlueZ

Use BlueZ as the baseline Bluetooth skill when you need:
- adapter bring-up and health checks
- BLE or Classic discovery from Linux
- pairing / trust / connection workflows
- Bluetooth service and characteristic inspection
- low-level monitoring and debugging

## Quick Start

```bash
# verify controller state
bluetoothctl list
bluetoothctl show

# interactive discovery
bluetoothctl
[bluetooth]# power on
[bluetooth]# agent on
[bluetooth]# default-agent
[bluetooth]# scan on
```

## Core Workflows

### Live device discovery

```bash
bluetoothctl scan on
```

### Pair and trust a device

```bash
bluetoothctl
[bluetooth]# pair AA:BB:CC:DD:EE:FF
[bluetooth]# trust AA:BB:CC:DD:EE:FF
[bluetooth]# connect AA:BB:CC:DD:EE:FF
```

### Low-level monitor / troubleshooting

```bash
btmon
```

Use `btmon` when pairing, advertising visibility, or GATT behavior is unclear.

## Practical Scope

BlueZ is the foundation. Prefer it before niche scanners because:
- it is current and maintained upstream
- it ships the real Linux Bluetooth stack
- it exposes both high-level and low-level workflows

## Notes on Older Utilities

Older tooling such as `gatttool` or some deprecated tools may still appear in guides, but modern workflows should prefer current BlueZ client tooling where possible.

## Relationship to Other Wireless Skills

| Skill | Best use |
|---|---|
| `bluez` | Core Linux Bluetooth discovery, pairing, monitoring |
| `kismet` | Passive multi-RF visibility including Bluetooth with supported hardware |
| `sparrow-wifi` | GUI/agent Bluetooth awareness plus Wi‑Fi/HackRF/Ubertooth workflows |

## Resources

| File | When to load |
|---|---|
| `references/scan-read-debug-workflow.md` | For bluetoothctl, BLE scanning, service inspection, and monitor-first debugging workflows |
