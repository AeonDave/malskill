# Wireshark / tshark — Filter Cheatsheet

## Display Filter Syntax

```
ip.addr == 10.0.0.1
ip.src == 10.0.0.1
ip.dst == 10.0.0.1
tcp.port == 80
tcp.dstport == 443
udp.port == 53
!(arp or icmp or dns)         # exclude noise
ip.addr == 10.0.0.1 and tcp.port == 80
http or smb or kerberos
```

## Protocol Filters

| Protocol | Filter | Notes |
|----------|--------|-------|
| HTTP | `http` | HTTP/1.x only |
| HTTPS | `ssl` or `tls` | Encrypted; need key to decrypt |
| SMB | `smb or smb2` | Windows file sharing |
| NTLM | `ntlmssp` | Auth challenge/response |
| Kerberos | `kerberos` | AD authentication |
| DNS | `dns` | Name resolution |
| FTP | `ftp or ftp-data` | Cleartext file transfer |
| SSH | `ssh` | Encrypted, limited insight |
| RDP | `rdp` | Remote desktop |
| LDAP | `ldap` | Directory queries |
| ICMP | `icmp` | Ping/echo |
| ARP | `arp` | MAC resolution |

## Credential Extraction Filters

```
# HTTP POST (login forms)
http.request.method == "POST"

# HTTP Basic auth header
http.authorization

# FTP passwords
ftp.request.command == "PASS"

# Telnet keystrokes
telnet

# NTLM auth
ntlmssp

# NTLM challenge (for relay detection)
ntlmssp.messagetype == 0x00000002

# Kerberos AS-REQ (username enum)
kerberos.msg_type == 10

# Kerberos TGS-REP (for Kerberoasting detection)
kerberos.msg_type == 13

# LDAP binds
ldap.protocolOp == 0

# SNMP community strings
snmp
```

## tshark One-Liners

### HTTP credential extraction

```bash
# POST bodies
tshark -r cap.pcap -Y "http.request.method == POST" \
  -T fields -e ip.src -e http.host -e http.request.uri -e urlencoded-form.value 2>/dev/null

# Authorization headers
tshark -r cap.pcap -Y "http.authorization" \
  -T fields -e ip.src -e http.host -e http.authorization

# Cookies
tshark -r cap.pcap -Y "http.cookie" \
  -T fields -e ip.src -e http.host -e http.cookie
```

### NTLM / SMB

```bash
# Net-NTLMv2 hash extraction (usable with hashcat -m 5600)
tshark -r cap.pcap -Y "ntlmssp.auth.username" \
  -T fields -e ntlmssp.auth.domain -e ntlmssp.auth.username \
  -e ntlmssp.auth.ntresponse -e ntlmssp.ntlmserverchallenge

# SMB shares accessed
tshark -r cap.pcap -Y "smb2.filename" \
  -T fields -e ip.src -e ip.dst -e smb2.filename
```

### DNS Tunneling Detection

```bash
# Long DNS queries (potential exfil)
tshark -r cap.pcap -Y "dns.qry.name.len > 40" \
  -T fields -e ip.src -e dns.qry.name
```

### Statistics

```bash
# Conversation summary
tshark -r cap.pcap -q -z conv,tcp

# Protocol hierarchy
tshark -r cap.pcap -q -z io,phs

# HTTP requests by host
tshark -r cap.pcap -q -z http_srv,tree

# Packet count by IP
tshark -r cap.pcap -q -z endpoints,ip
```

## Decrypt TLS (if key available)

```bash
# Wireshark GUI: Edit → Preferences → Protocols → TLS
# Add (Pre)-Master-Secret log file (from SSLKEYLOGFILE)

# tshark with key log
tshark -r cap.pcap -o "tls.keylog_file:/path/to/sslkeys.log" \
  -Y "http" -T fields -e http.request.full_uri

# Capture with SSLKEYLOGFILE set (Firefox/Chrome)
SSLKEYLOGFILE=/tmp/sslkeys.log firefox &
tshark -i eth0 -w with_keys.pcap
```

## BPF Capture Filters (set at capture time, not display)

```bash
tshark -i eth0 -f "tcp port 80"
tshark -i eth0 -f "tcp port 80 or tcp port 443"
tshark -i eth0 -f "host 10.0.0.5"
tshark -i eth0 -f "net 192.168.1.0/24"
tshark -i eth0 -f "not arp and not icmp"
tshark -i eth0 -f "tcp[tcpflags] & (tcp-syn) != 0"  # SYN packets only
```

## Merge / Split PCAPs

```bash
# Merge multiple pcaps
mergecap -w combined.pcap file1.pcap file2.pcap

# Split by size
editcap -c 10000 large.pcap split_

# Convert formats
editcap -F pcapng capture.pcap output.pcapng
```
