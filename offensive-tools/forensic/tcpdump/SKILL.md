---
name: tcpdump
description: |
  CLI packet capture and BPF filter tool. Use to capture network traffic to .pcap files, filter
  existing PCAPs for specific hosts/ports/protocols, extract payloads as ASCII/hex, and quickly
  triage network activity from the command line. Pairs with Wireshark/tshark for deep analysis
  and Zeek for structured log extraction. Essential for network forensics and PCAP investigation.
license: BSD-3-Clause
compatibility: "Linux/macOS/*BSD/Windows (Npcap). apt install tcpdump. tcpdump.org"
metadata:
  author: AeonDave
  version: "2.0"
---

# tcpdump

CLI packet capture + BPF filter. Capture traffic, filter PCAPs, extract payloads, triage network activity.

## Installation

```bash
# Linux
sudo apt install tcpdump

# macOS (preinstalled or)
brew install tcpdump

# Windows: use WinDump + Npcap (or use tshark instead)
```

---

## Core Flags Reference

| Flag | Purpose |
|------|---------|
| `-i <iface>` | Interface to capture on |
| `-r <file>` | Read from PCAP file (instead of live capture) |
| `-w <file>` | Write captured packets to PCAP file |
| `-n` | No DNS resolution (IP addresses only) |
| `-nn` | No DNS + no port name resolution (shows port numbers) |
| `-v` | Verbose output |
| `-vv` | More verbose (full TCP flags, options) |
| `-vvv` | Maximum verbosity |
| `-s <n>` | Snap length (0 = unlimited, capture full packets) |
| `-c <n>` | Capture exactly n packets then stop |
| `-A` | Print packet payload as ASCII |
| `-X` | Print packet payload as hex + ASCII |
| `-XX` | Print packet header + payload as hex + ASCII |
| `-q` | Quiet — minimal output |
| `-e` | Print link-layer header (MAC addresses) |
| `-tttt` | Human-readable timestamps |
| `-D` | List available interfaces |
| `-G <n>` | Rotate capture file every n seconds |
| `-C <n>` | Rotate capture file every n MB |
| `-Z <user>` | Drop privileges after capture starts |
| `host` | BPF primitive — filter by IP |
| `port` | BPF primitive — filter by port |
| `net` | BPF primitive — filter by network |

---

## Capture Patterns

### Basic capture to file

```bash
# List interfaces
tcpdump -D

# Capture all traffic on interface
sudo tcpdump -i eth0 -nn -s 0 -w capture.pcap

# Capture limited packets
sudo tcpdump -i eth0 -nn -s 0 -c 1000 -w capture.pcap

# Capture with timestamps + verbose
sudo tcpdump -i eth0 -nn -s 0 -tttt -w capture.pcap
```

### Targeted captures

```bash
# Specific host
sudo tcpdump -i eth0 -nn -s 0 -w host.pcap 'host 10.10.10.5'

# Specific port
sudo tcpdump -i eth0 -nn -s 0 -w http.pcap 'port 80'

# Port range
sudo tcpdump -i eth0 -nn -s 0 'portrange 8000-9000'

# Specific protocol
sudo tcpdump -i eth0 -nn -s 0 -w dns.pcap 'udp port 53'
sudo tcpdump -i eth0 -nn -s 0 -w icmp.pcap 'icmp'

# HTTP + HTTPS
sudo tcpdump -i eth0 -nn -s 0 -w web.pcap 'port 80 or port 443'

# Exclude noise (focus on external traffic)
sudo tcpdump -i eth0 -nn -s 0 -w external.pcap 'not net 192.168.0.0/16 and not net 10.0.0.0/8'

# SYN packets only (new connections)
sudo tcpdump -i eth0 -nn 'tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0'

# RST packets (connection resets, scan indicators)
sudo tcpdump -i eth0 -nn 'tcp[tcpflags] & tcp-rst != 0'
```

---

## Reading and Filtering Existing PCAPs

```bash
# Read and display
tcpdump -nn -r capture.pcap

# Verbose display
tcpdump -nn -vv -r capture.pcap

# Filter while reading
tcpdump -nn -r capture.pcap 'port 80'
tcpdump -nn -r capture.pcap 'host 10.10.10.5'
tcpdump -nn -r capture.pcap 'src host 10.10.10.5 and dst port 443'

# Write filtered subset to new PCAP
tcpdump -nn -r capture.pcap -w filtered.pcap 'port 80'

# Show only SYN packets (connection initiations)
tcpdump -nn -r capture.pcap 'tcp[tcpflags] == tcp-syn'

# Extract specific time window
tcpdump -nn -r capture.pcap -w window.pcap 'greater 14:30:00 and less 15:00:00'
```

---

## Payload Extraction

```bash
# Print ASCII payload (HTTP, cleartext passwords, etc.)
tcpdump -nn -A -r capture.pcap 'port 80'

# Print hex + ASCII
tcpdump -nn -X -r capture.pcap 'port 21'   # FTP — may expose credentials

# Extract only payload bytes (for file recovery)
tcpdump -nn -A -r capture.pcap 'port 80' | grep -v "^[0-9a-f][0-9a-f]:[0-9a-f]" | grep -v "^$"

# Find strings in PCAP payload
tcpdump -nn -A -r capture.pcap 2>/dev/null | grep -i "password\|passwd\|pass=\|login\|credential"

# HTTP POST body extraction
tcpdump -nn -A -r capture.pcap 'tcp port 80 and (tcp[tcpflags] & tcp-push != 0)' | grep -A 20 "POST"

# Find flags or specific patterns in payloads
tcpdump -nn -A -r capture.pcap 2>/dev/null | grep -iE "flag\{|HTB\{|picoCTF"
```

---

## BPF Filter Syntax Reference

### Primitives

```bash
host 192.168.1.1          # src or dst IP
src host 192.168.1.1      # source IP only
dst host 192.168.1.1      # destination IP only
net 192.168.1.0/24        # CIDR network
src net 10.0.0.0/8
port 80                   # src or dst port
src port 1234
dst port 443
portrange 1024-65535
tcp                       # protocol
udp
icmp
arp
```

### Operators

```bash
and / &&                  # both conditions
or / ||                   # either condition
not / !                   # negation
```

### Complex filters

```bash
# Traffic between two hosts
'host 192.168.1.1 and host 192.168.1.2'

# From source to specific port
'src host 10.10.10.5 and dst port 4444'

# Any of multiple ports
'port 80 or port 8080 or port 8443'

# Exclude specific host from capture
'not host 10.0.0.1'

# TCP SYN-ACK only (established connections)
'tcp[tcpflags] & (tcp-syn|tcp-ack) == (tcp-syn|tcp-ack)'

# Large packets (data transfer detection)
'greater 1400'

# VLAN traffic
'vlan'

# IPv6
'ip6'

# HTTP GET requests (match method in payload)
'tcp port 80 and tcp[((tcp[12:1] & 0xf0) >> 2):4] = 0x47455420'   # "GET "
```

---

## Investigation Workflows

### Workflow 1: Quick PCAP triage

```bash
# Overview — what hosts, ports, protocols?
tcpdump -nn -q -r capture.pcap | awk '{print $3, $5}' | sort | uniq -c | sort -rn | head 30

# Unique source IPs
tcpdump -nn -r capture.pcap | awk '{print $3}' | cut -d. -f1-4 | sort | uniq -c | sort -rn

# Unique destination ports
tcpdump -nn -r capture.pcap | grep -oP 'dst \d+\.\d+\.\d+\.\d+\.\K\d+' | sort | uniq -c | sort -rn
```

### Workflow 2: Extract cleartext credentials

```bash
# FTP (port 21)
tcpdump -nn -A -r capture.pcap 'port 21' | grep -iE "USER|PASS"

# HTTP Basic Auth
tcpdump -nn -A -r capture.pcap 'port 80' | grep -i "Authorization: Basic"

# Telnet
tcpdump -nn -A -r capture.pcap 'port 23'

# SMTP credentials
tcpdump -nn -A -r capture.pcap 'port 25' | grep -iE "auth|user|pass"
```

### Workflow 3: Detect port scanning

```bash
# Many SYN packets from same source (SYN scan)
tcpdump -nn -r capture.pcap 'tcp[tcpflags] == tcp-syn' | awk '{print $3}' | \
  cut -d. -f1-4 | sort | uniq -c | sort -rn | head

# RST flood (close scan, rejected ports)
tcpdump -nn -r capture.pcap 'tcp[tcpflags] & tcp-rst != 0' | wc -l

# UDP probe packets (UDP scan)
tcpdump -nn -r capture.pcap 'udp' | awk '{print $5}' | sort | uniq -c | sort -rn
```

### Workflow 4: Find C2 beaconing

```bash
# Regular intervals from same source to same dest
tcpdump -nn -r capture.pcap 'host SUSPECT_IP' | awk '{print $1}' | \
  awk 'NR>1{printf "%.1f\n", $1-prev} {prev=$1}' | sort | uniq -c | sort -rn | head

# Long-duration connection (persistent C2)
# → look for connections with many packets over long time window
```

### Workflow 5: Extract files from PCAP

```bash
# Better with Wireshark: File → Export Objects → HTTP
# CLI alternative with tcpflow:
sudo apt install tcpflow
tcpflow -r capture.pcap -o output_dir/

# Or with NetworkMiner (Windows GUI)
# Or reassemble TCP streams with tshark:
tshark -r capture.pcap -z follow,tcp,raw,0 2>/dev/null | xxd -r -p > stream0.bin
```

---

## Useful Combinations

```bash
# Live capture → immediate grep (no file)
sudo tcpdump -i eth0 -nn -A 2>/dev/null | grep -i "password\|flag\|secret"

# Save and display simultaneously
sudo tcpdump -i eth0 -nn -s 0 -w capture.pcap | tcpdump -nn -r -

# Rotate files every 5 minutes (long capture)
sudo tcpdump -i eth0 -nn -s 0 -G 300 -w "capture_%Y%m%d_%H%M%S.pcap"

# Split large PCAP into smaller chunks
tcpdump -nn -r huge.pcap -w small.pcap -C 100  # 100MB chunks

# Count packets by protocol
tcpdump -nn -q -r capture.pcap | awk '{print $2}' | sort | uniq -c | sort -rn

# Convert PCAP to text for grep
tcpdump -nn -tttt -r capture.pcap > capture.txt
grep -i "interesting_string" capture.txt
```

---

## Integration

| Tool | Use case |
|------|---------|
| `wireshark` / `tshark` | Deep protocol dissection, file extraction, stream following |
| `zeek` | Convert PCAP to structured logs (dns.log, http.log, etc.) |
| `strings` | Quick string extraction from raw PCAP |
| `scapy` (Python) | Scripted PCAP parsing and packet manipulation |
| `tcpflow` | TCP stream reassembly and file extraction from PCAP |
| `binwalk` | Carve embedded files from reassembled streams |
| `yara` | Scan packet payloads for patterns |

## Resources

| File | When to load |
|------|--------------|
| `references/` | BPF filter recipes, tshark equivalents, complex protocol analysis patterns |
