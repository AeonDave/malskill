---
name: wifite
description: "Auth/lab ref: Automated Wi-Fi auditing wrapper for WEP/WPA/WPA2/PMKID workflows with minimal operator input."
license: MIT
compatibility: "Python 3; Linux."
metadata:
  author: AeonDave
  version: "1.0"
---

# Wifite

Automated Wi‑Fi attack wrapper for rapid WPA/WEP/PMKID triage and capture workflows.

## Quick Start

```bash
pip install wifite   # or: apt install wifite

# Full auto (scan and attack all visible networks)
sudo wifite

# Target specific BSSID
sudo wifite --bssid AA:BB:CC:DD:EE:FF

# WPA handshake only + crack with wordlist
sudo wifite --wpa --dict /usr/share/wordlists/rockyou.txt

# PMKID attack
sudo wifite --pmkid
```

## Why Use It

Choose `wifite` when you need:
- rapid all-in-one Wi‑Fi attack orchestration
- quick triage of multiple nearby APs
- less manual command sequencing than `aircrack-ng`
- fast PMKID / WPA capture attempts during early assessment

## Core Flags

| Flag | Purpose |
|------|---------|
| `--bssid MAC` | Target specific AP |
| `--essid NAME` | Target by SSID name |
| `--channel N` | Target channel |
| `--wpa` | Only WPA targets |
| `--wep` | Only WEP targets |
| `--pmkid` | PMKID attack (clientless) |
| `--dict FILE` | Wordlist for cracking |
| `--no-deauth` | Skip deauth (stealth) |
| `--timeout N` | Attack timeout (s) |
| `--crack` | Auto-crack after capture |

## Common Workflows

**Automated PMKID + crack:**
```bash
sudo wifite --pmkid --dict rockyou.txt
```

**WPA handshake capture only (no crack):**
```bash
sudo wifite --wpa --no-crack
# Handshake saved to ~/hs/
# Crack later: aircrack-ng ~/hs/*.cap -w rockyou.txt
```

## Practical Notes

- `wifite` is only as good as the adapter and dependencies underneath it.
- When automation hides too much detail, fall back to `aircrack-ng`.
- For passive discovery and RF awareness, start with `kismet` instead.

## Best Fit

| Need | Better fit |
|------|------------|
| Fast automated WPA/PMKID flow | `wifite` |
| Manual control of capture/injection | `aircrack-ng` |
| Passive Wi‑Fi / Bluetooth / RF recon | `kismet` |

## Resources

| File | When to load |
|------|--------------|
| `references/dependency-troubleshooting.md` | For dependency expectations, common failures, and when to switch back to manual tooling |
