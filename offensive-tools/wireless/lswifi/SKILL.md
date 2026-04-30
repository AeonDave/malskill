---
name: lswifi
description: "CLI-centric Windows Wi‑Fi scanning tool exposing richer nearby-network data than built-in commands, including RSSI, security details, information elements, 6 GHz Reduced Neighbor Reports, JSON/CSV export, and event watching. Use when auditing nearby Wi‑Fi networks from Windows, exporting scan data, or scripting Windows-native wireless analysis without monitor-mode tooling."
license: BSD-3-Clause
compatibility: "Windows 10+; Python 3.9+; pip install lswifi. Uses Native Wi‑Fi APIs, not raw monitor-mode capture."
metadata:
  author: AeonDave
  version: "1.0"
---

# lswifi

Windows-native CLI Wi‑Fi scanner for richer AP visibility, filtering, export, and event watching.

## Why Use It

Use `lswifi` when you need:
- Wi‑Fi analysis from Windows without Kali/WSL monitor workflows
- richer output than `netsh wlan show networks`
- RSSI, AKM/cipher, RNR and IE decoding
- JSON/CSV/pcapng export for scripting and review

## Quick Start

```powershell
python -m pip install lswifi

# basic scan
lswifi

# stronger-signal networks only
lswifi -t -60

# only matching SSIDs
lswifi -include Office

# JSON export-friendly output
lswifi --json
```

## High-Value Modes

```powershell
# Information elements for a specific BSSID
lswifi -ies 00:11:22:33:44:55

# Watch roaming / scan / connection events
lswifi --watchevents

# 6 GHz / RNR oriented view
lswifi -rnr

# export scan results
lswifi -export
```

## Important Limitation

`lswifi` is **not** traditional over-the-air monitor-mode packet capture. It uses Windows Native Wi‑Fi APIs, so treat it as a Windows-native survey/inspection tool, not as a full packet injection platform.

## Relationship to Other Wireless Skills

| Skill | Best use |
|---|---|
| `lswifi` | Windows-centric scan, export, filtering, event watching |
| `kismet` | Passive multi-sensor / multi-protocol RF visibility |
| `aircrack-ng` | Linux monitor-mode audit and capture workflows |

## Resources

| File | When to load |
|---|---|
| `references/filtering-export-workflows.md` | For practical filters, exports, watch mode, and Windows-specific caveats |
