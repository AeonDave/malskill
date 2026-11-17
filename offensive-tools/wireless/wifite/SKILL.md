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
# Kali package; other distributions may package a different revision
sudo apt install wifite

# Start Wifite
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
| `--crack` | Show commands for cracking an existing capture |

## Common Workflows

**Automated PMKID + crack:**
```bash
sudo wifite --pmkid --dict rockyou.txt
```

**WPA handshake capture only (no crack):**
```bash
sudo wifite --wpa --skip-crack
# Default capture directory: ./hs/ (relative to the working directory)
```

## Practical Notes

- The original project points to [kimocoder/wifite2](https://github.com/kimocoder/wifite2) for maintained Wifite 2. Use its installation instructions for source installs; [wifit3](https://github.com/derv82/wifit3) is a separate USB-adapter application, not a drop-in CLI upgrade.
- Check `wifite -h` for the installed version. Timeout options are attack-specific; there is no generic `--timeout` option in the maintained fork's [argument parser](https://github.com/kimocoder/wifite2/blob/master/wifite/args.py).
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
