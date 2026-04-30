# Wifite Dependency & Troubleshooting Notes

## What Wifite Is Best At

Wifite is an **automation wrapper** around common Wi‑Fi attack flows. It is useful when speed matters more than manual orchestration.

Use it when you want:
- rapid WPA/WEP/PMKID targeting
- one-command attack workflow
- quick triage of multiple nearby APs

Use `aircrack-ng` directly when you need more control.

## Dependency Reality

Wifite depends on other tools and adapter capabilities. It is not standalone magic.

Check for:
- monitor-mode capable Wi‑Fi adapter
- aircrack-ng suite installed
- hashcat or other cracking tooling if doing offline cracking
- optional PMKID companion tools depending on distro packaging

## Typical Flows

### Full auto

```bash
sudo wifite
```

### Specific AP

```bash
sudo wifite --bssid AA:BB:CC:DD:EE:FF
```

### PMKID focused

```bash
sudo wifite --pmkid
```

### Capture only

```bash
sudo wifite --wpa --no-crack
```

## Common Problems

| Problem | Cause | Fix |
|---|---|---|
| No targets found | monitor mode/interface issue | validate adapter and monitor interface |
| Deauth ineffective | PMF/MFP or injection limitations | fall back to passive/manual capture |
| Auto crack weak | bad wordlist fit | export capture and crack offline with better workflow |
| Tool errors on startup | missing suite dependencies | validate `aircrack-ng`, `iw`, and related packages |

## When Not To Use Wifite

Avoid it when:
- you need precise packet-level control
- the engagement emphasizes low-noise manual validation
- you are troubleshooting adapter/driver issues

In those cases, start with `aircrack-ng` or `kismet`.

## Source Pointers

- Wifite usage conventions
- Aircrack-ng suite integration expectations
