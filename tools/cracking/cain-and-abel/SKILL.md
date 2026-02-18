---
name: cain-and-abel
description: "Windows password recovery tool for sniffing, cracking (dictionary/brute-force/cryptanalysis), and decoding stored credentials. Use when recovering Windows hashes, cracking captured handshakes, or decoding cached credentials on Windows systems."
license: MIT
compatibility: "Windows only; GUI application; legacy tool (last updated 2014)"
metadata:
  author: AeonDave
  version: "1.0"
---

# Cain & Abel

Windows GUI password recovery — sniffer, hash cracker, credential decoder.

## Quick Start

1. Download from oxid.it (legacy) or archive
2. Run as Administrator
3. Select **Cracker** tab → Add hashes
4. Right-click hash → **Dictionary Attack** / **Brute-Force Attack** / **Rainbow Table**

## Core Features

| Feature | Purpose |
|---------|---------|
| Sniffer | Capture network credentials (ARP poisoning) |
| Cracker | Dictionary, brute-force, cryptanalysis of hashes |
| Decoders | Decode stored passwords (LSA, VNC, dialup) |
| Network | ARP poisoning, route discovery |
| Wireless | WEP/WPA capture and crack |
| Certificate | Certificate collector via MITM |

## Hash Types Supported

MD5, SHA-1, LM, NTLM, NTLMv2, MySQL, MS-SQL, Oracle, Cisco PIX/IOS, VNC, RADIUS, WPA.

## Common Workflows

**Crack NTLM from SAM dump:**
1. Cracker tab → `+` → Add NT hashes from SAM
2. Right-click → Dictionary Attack → point to wordlist

**ARP poison + credential capture:**
1. Sniffer tab → Enable sniffer
2. ARP tab → Add victim + gateway
3. Passwords tab → view captured creds

> **Note**: Use only on authorized systems. Cain & Abel triggers most AV.

## Resources

| File | When to load |
|------|--------------|
| `references/` | Hash import formats and dictionary sources |
