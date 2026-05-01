# tcpdump — Deep Reference

## tshark Equivalents

tshark is the CLI version of Wireshark — richer protocol dissection than tcpdump, same PCAP format.

```bash
sudo apt install tshark wireshark-common

# Basic read
tshark -r capture.pcap

# Display filter (Wireshark syntax, richer than BPF)
tshark -r capture.pcap -Y "http.request.method == POST"
tshark -r capture.pcap -Y "dns.qry.name contains evil.com"
tshark -r capture.pcap -Y "tcp.dstport == 4444"
tshark -r capture.pcap -Y "frame contains flag{"

# Extract specific fields
tshark -r capture.pcap -Y "http" -T fields -e ip.src -e http.host -e http.request.uri -e http.user_agent
tshark -r capture.pcap -Y "dns" -T fields -e ip.src -e dns.qry.name -e dns.resp.addr

# Follow TCP stream (reassemble session)
tshark -r capture.pcap -z follow,tcp,ascii,0    # stream 0
tshark -r capture.pcap -z follow,tcp,raw,0 | xxd | head

# Extract HTTP objects
tshark -r capture.pcap --export-objects http,/tmp/http_objects/

# Statistics
tshark -r capture.pcap -z conv,tcp    # TCP conversations
tshark -r capture.pcap -z io,phs      # protocol hierarchy
tshark -r capture.pcap -z endpoints,ip  # endpoint stats

# Write filtered PCAP
tshark -r capture.pcap -Y "ip.dst == 10.10.10.5" -w filtered.pcap
```

### tcpdump → tshark equivalents

| tcpdump | tshark |
|---------|--------|
| `tcpdump -r file.pcap` | `tshark -r file.pcap` |
| `tcpdump -r f.pcap 'port 80'` | `tshark -r f.pcap -Y "tcp.port==80"` |
| `tcpdump -A -r f.pcap` | `tshark -r f.pcap -x` |
| `tcpdump -r f.pcap 'host X'` | `tshark -r f.pcap -Y "ip.addr==X"` |
| `tcpdump -r f.pcap -w out.pcap 'port 80'` | `tshark -r f.pcap -Y "tcp.port==80" -w out.pcap` |

---

## scapy: Python PCAP Parsing

```python
from scapy.all import rdpcap, IP, TCP, UDP, DNS, DNSQR, Raw

# Load PCAP
packets = rdpcap('capture.pcap')

# Iterate packets
for pkt in packets:
    if IP in pkt:
        print(pkt[IP].src, "→", pkt[IP].dst)

# Filter TCP packets
tcp_pkts = [p for p in packets if TCP in p]

# Extract HTTP payloads
for pkt in packets:
    if TCP in pkt and Raw in pkt:
        payload = pkt[Raw].load
        if b'GET' in payload or b'POST' in payload:
            print(payload.decode(errors='replace'))

# DNS queries
for pkt in packets:
    if DNS in pkt and pkt.haslayer(DNSQR):
        print(pkt[DNSQR].qname.decode())

# Find flag in payloads
import re
flag_re = re.compile(rb'flag\{[^\}]+\}')
for pkt in packets:
    if Raw in pkt:
        m = flag_re.search(pkt[Raw].load)
        if m:
            print(f"[MATCH] {m.group()}")

# Extract all strings from payloads
from scapy.all import conf
strings = set()
for pkt in packets:
    if Raw in pkt:
        for s in re.findall(rb'[\x20-\x7e]{6,}', pkt[Raw].load):
            strings.add(s.decode())
print('\n'.join(sorted(strings)))
```

---

## TCP Stream Reassembly

```bash
# tcpflow: reassemble TCP streams to files
sudo apt install tcpflow
tcpflow -r capture.pcap -o streams/
ls streams/   # one file per TCP session

# Extract and search strings
strings streams/* | grep -iE "flag|password|key|secret"

# ngrep: grep on packet payloads
sudo apt install ngrep
ngrep -I capture.pcap -q "flag{" 'port 80'
ngrep -I capture.pcap -q "password" ''

# Follow specific TCP stream in tshark
# First identify stream number:
tshark -r capture.pcap -Y "ip.addr==10.10.10.5 && tcp.port==1337" -T fields -e tcp.stream | head -1
# Then extract stream N:
tshark -r capture.pcap -z "follow,tcp,ascii,N" > stream.txt
```

---

## File Extraction from PCAP

```bash
# tshark: export HTTP objects
tshark -r capture.pcap --export-objects http,extracted_http/

# tshark: export SMB objects
tshark -r capture.pcap --export-objects smb,extracted_smb/

# tshark: export TFTP objects
tshark -r capture.pcap --export-objects tftp,extracted_tftp/

# foremost: carve files from raw PCAP data
foremost -i capture.pcap -o carved/ -t jpg,png,zip,pdf,exe

# binwalk: extract embedded files
binwalk -e capture.pcap -C binwalk_output/

# Manual: extract raw TCP stream
tshark -r capture.pcap -z "follow,tcp,raw,0" > stream0_hex.txt
# Convert hex to binary
python3 -c "import sys; data=''.join(sys.stdin.read().split()); open('stream0.bin','wb').write(bytes.fromhex(data))" < stream0_hex.txt
file stream0.bin
```

---

## Protocol-Specific Extraction

### HTTP credentials (Basic Auth)

```bash
# Base64-encoded "user:pass" in Authorization header
tcpdump -nn -A -r capture.pcap 'port 80' | grep -i "Authorization: Basic" | \
  awk '{print $3}' | base64 -d 2>/dev/null
```

### FTP credentials

```bash
tcpdump -nn -A -r capture.pcap 'port 21' | grep -iE "USER|PASS"
# or
tshark -r capture.pcap -Y "ftp" -T fields -e ftp.request.command -e ftp.request.arg
```

### SMTP credentials

```bash
tshark -r capture.pcap -Y "smtp" -T fields -e smtp.req.command -e smtp.req.parameter
# AUTH LOGIN: credentials are base64 encoded
```

### DNS over port 53

```bash
# All DNS queries with response IPs
tshark -r capture.pcap -Y "dns.flags.response == 1" -T fields \
  -e dns.qry.name -e dns.a -e dns.aaaa | sort -u

# Suspicious TXT records (tunneling)
tshark -r capture.pcap -Y "dns.qry.type == 16" -T fields -e dns.qry.name -e dns.txt
```

---

## pcapng vs pcap

| Feature | pcap | pcapng |
|---------|------|--------|
| Multiple interfaces | No | Yes |
| Interface metadata | No | Yes |
| Name resolution blocks | No | Yes |
| Comments/annotations | No | Yes |
| Timestamps precision | Microsecond | Nanosecond (optional) |
| Tool support | Universal | Most modern tools |

```bash
# Convert pcapng → pcap (for older tools)
tshark -r capture.pcapng -F pcap -w capture.pcap

# Convert pcap → pcapng
tshark -r capture.pcap -F pcapng -w capture.pcapng

# Merge multiple PCAPs
mergecap -w merged.pcap capture1.pcap capture2.pcap capture3.pcap
```

---

## BPF vs Wireshark Display Filters

BPF (tcpdump) filters at capture time; Wireshark/tshark display filters work post-capture on decoded data.

| Intent | BPF (tcpdump) | Display filter (tshark -Y) |
|--------|---------------|--------------------------|
| Port 80 | `port 80` | `tcp.port == 80` |
| HTTP method | (not supported) | `http.request.method == "GET"` |
| DNS name | (not supported) | `dns.qry.name contains "evil.com"` |
| TLS SNI | (not supported) | `tls.handshake.extensions_server_name == "evil.com"` |
| TCP SYN | `tcp[tcpflags] == tcp-syn` | `tcp.flags.syn == 1 && tcp.flags.ack == 0` |
| Source IP | `src host 1.2.3.4` | `ip.src == 1.2.3.4` |
| Payload content | (limited) | `frame contains "flag{"` |

Use BPF for live capture (performance critical); use display filters for post-capture investigation.
