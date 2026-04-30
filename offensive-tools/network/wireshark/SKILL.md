---
name: wireshark
description: "Wireshark: network and wireless protocol analyzer for capturing and inspecting packets. Use when analysing pcap files, triaging network-forensics evidence, capturing live traffic, following streams, extracting files or credentials from captures, inspecting 802.11 management/data traffic, reviewing EAPOL or WPA-Enterprise handshakes, or investigating network anomalies during red team operations. CLI equivalent: tshark."
license: GPL-2.0
compatibility: "Linux / macOS / Windows. Official installer at wireshark.org. tshark included."
metadata:
  author: AeonDave
  version: "1.1"
---

# Wireshark / tshark

Packet capture and protocol analysis for wired and 802.11 wireless traffic.

## Quick Start (tshark CLI)

```bash
tshark -i eth0 -w capture.pcap
tshark -r capture.pcap -Y "http" -T fields -e http.host -e http.request.uri
tshark -r capture.pcap -Y "ntlmssp" -T fields -e ip.src -e ntlmssp.auth.username

# Wireless examples
tshark -r wifi.pcap -Y "wlan.fc.type_subtype == 0x08" -T fields -e wlan.bssid -e wlan.ssid
tshark -r wifi.pcap -Y "eapol"
tshark -r wifi.pcap -Y "tls.handshake.certificate"
```

## Key Display Filters

| Filter | Purpose |
|--------|---------|
| `tcp.port == 445` | SMB traffic |
| `http.request.method == "POST"` | POST requests |
| `ftp.request.command == "PASS"` | FTP passwords |
| `ntlmssp` | NTLM auth |
| `kerberos` | Kerberos traffic |
| `dns` | DNS queries |
| `ip.addr == 10.0.0.5` | Traffic to/from IP |
| `eapol` | WPA/WPA2 4-way handshake traffic |
| `wlan.fc.type == 0` | 802.11 management frames |
| `wlan.fc.type_subtype == 0x08` | Beacon frames |
| `wlan.fc.type_subtype == 12` | Deauthentication frames |
| `wlan.bssid == 00:11:22:33:44:55` | Traffic for one AP |
| `tls.handshake.certificate` | Certificates inside WPA-Enterprise / TLS handshakes |

## Common Workflows

### Triage a `.pcap` before deep inspection

```bash
# What protocols dominate the capture?
tshark -r capture.pcap -q -z io,phs

# Which hosts talk the most?
tshark -r capture.pcap -q -z endpoints,ip

# Which client/server pairs matter?
tshark -r capture.pcap -q -z conv,tcp

# Fast protocol shortlist for common CTF / IR pivots
tshark -r capture.pcap -Y "http or dns or smb or ftp or smtp or kerberos or ntlmssp"
```

Start with protocol hierarchy, endpoints, and conversations before diving into single packets. This reduces noise and helps you pick the stream, host, or protocol worth following.

### Follow TCP stream

```bash
# tshark
tshark -r capture.pcap -q -z follow,tcp,ascii,0
tshark -r capture.pcap -q -z follow,http,ascii,0
tshark -r capture.pcap -q -z follow,tcp,raw,0

# Wireshark GUI: right-click packet → Follow → TCP Stream
```

Use Follow Stream to reconstruct the application view of a connection. In the GUI you can save the stream as ASCII for quick reading or Raw when you want to decode or carve the payload offline.

### Find flags, tokens, and suspicious strings

```bash
# Broad content hunt
tshark -r capture.pcap -Y 'frame contains "flag" || http contains "flag" || dns contains "flag"'

# Look for cookies / bearer-style tokens / auth headers
tshark -r capture.pcap -Y "http.authorization || http.cookie"

# Search for form submissions
tshark -r capture.pcap -Y 'http.request.method == "POST"'
```

In the GUI use `Edit -> Find Packet` with a display filter, string, hex value, or regex when you need to jump quickly to a secret, hostname, URI, or magic byte sequence inside a large capture.

### Extract credentials from capture

```bash
# HTTP POST bodies (logins)
tshark -r capture.pcap -Y "http.request.method == POST" \
  -T fields -e ip.src -e http.host -e http.request.uri -e http.file_data

# FTP passwords
tshark -r capture.pcap -Y "ftp.request.command == PASS" \
  -T fields -e ip.src -e ftp.request.arg

# NTLM hashes
tshark -r capture.pcap -Y "ntlmssp.auth.username" \
  -T fields -e ip.src -e ntlmssp.auth.domain -e ntlmssp.auth.username

# Kerberos usernames
tshark -r capture.pcap -Y "kerberos.CNameString" \
  -T fields -e ip.src -e kerberos.CNameString

# DNS queries
tshark -r capture.pcap -Y "dns.flags.response == 0" \
  -T fields -e frame.time -e ip.src -e dns.qry.name
```

### Export files from pcap

```bash
# HTTP objects (GUI)
# File → Export Objects → HTTP

# via tshark
tshark -r capture.pcap --export-objects http,./exported_files/
```

If the interesting data is not a clean HTTP object, select the bytes or follow the stream and save the result instead. Wireshark can also export selected packet bytes and packet dissections when you need a raw blob, structured text, CSV, or JSON evidence.

### Live capture + immediate output

```bash
# Capture on interface, write pcap, print to stdout
tshark -i eth0 -w capture.pcap -P

# Filter during capture
tshark -i eth0 -f "tcp port 445 or tcp port 80"

# Capture for N seconds
tshark -i eth0 -a duration:60 -w capture.pcap
```

### Inspect 802.11 management and authentication traffic

```bash
# beacons
tshark -r wifi.pcap -Y "wlan.fc.type_subtype == 0x08"

# authentication + deauthentication
tshark -r wifi.pcap -Y "wlan.fc.type_subtype == 11 || wlan.fc.type_subtype == 12"

# EAPOL handshake traffic
tshark -r wifi.pcap -Y "eapol"

# WPA-Enterprise certificates
tshark -r wifi.pcap -Y "tls.handshake.certificate" -T fields -e tls.handshake.certificate
```

### Review decrypted 802.11 captures

If you already recovered the WEP or WPA key, load it in the GUI under:

`Preferences -> Protocols -> IEEE 802.11 -> Decryption Keys`

Or decrypt first with companion tooling and re-open the resulting capture in Wireshark / tshark.

### Forensic `.pcap` workflow for labs, CTFs, and incident triage

1. Open the capture and note the dominant protocols, top talkers, and suspicious endpoints.
2. Filter to likely data-bearing traffic such as `http`, `dns`, `smtp`, `ftp`, `smb2`, or a target `ip.addr`.
3. Use `Statistics -> Conversations` or `Statistics -> Endpoints` to isolate the most relevant flows.
4. Use `Follow -> TCP/HTTP/TLS Stream` on candidate sessions to reconstruct requests, responses, commands, or embedded payloads.
5. Use `Edit -> Find Packet` to search for flags, usernames, filenames, cookies, URIs, or magic strings.
6. Export HTTP objects, selected packet bytes, or stream output, then decode offline if the payload is base64, compressed, XORed, or otherwise transformed.
7. Keep notes on packet numbers, IPs, hostnames, and extracted artifacts so the evidence chain stays reproducible.

## Resources

| File | When to load |
|------|--------------|
| `references/filters.md` | Complete display filter cheatsheet, credential extraction one-liners, stream analysis |
| `references/pcap-forensics-and-ctf-workflows.md` | Step-by-step `.pcap` triage, Follow Stream usage, object extraction, string hunting, and lab / CTF-style workflows |
| `references/wireless-80211-workflows.md` | Wireless display filters, EAPOL / WPA-Enterprise review, frame-type mapping, and tshark workflows for 802.11 captures |
