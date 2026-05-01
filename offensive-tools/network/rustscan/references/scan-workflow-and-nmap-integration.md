# RustScan — Deep Reference

## Output Parsing

RustScan outputs open ports then (optionally) passes them to nmap. Understanding both output formats enables automation.

### Plain output parsing

```bash
# RustScan default output (human-readable)
rustscan -a 192.168.1.0/24 --range 1-65535

# Machine-parseable: use -g (greppable nmap format via -oG)
rustscan -a TARGET --range 1-65535 -- -oG scan.gnmap -sV

# Parse greppable nmap output
grep "open" scan.gnmap | awk '{print $2, $5}' | tr ',' '\n' | grep "/open"

# JSON output (nmap XML → convert)
rustscan -a TARGET --range 1-65535 -- -oX scan.xml
# Parse XML with python
python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('scan.xml')
for host in tree.findall('.//host'):
    addr = host.find('address').get('addr')
    for port in host.findall('.//port[@protocol]'):
        if port.find('state').get('state') == 'open':
            portid = port.get('portid')
            service = port.find('service')
            svc = service.get('name','') if service is not None else ''
            print(f'{addr}:{portid} {svc}')
"
```

### Batch target workflow

```bash
# Scan subnet → save port list → targeted nmap
rustscan -a 192.168.1.0/24 --range 1-1000 -b 1000 --timeout 2000 \
  | grep "Open" | awk -F '[:\\[\\]]' '{print $2":"$3}' | sort -u > open_ports.txt

# Re-scan only discovered open ports with nmap full scan
cat open_ports.txt | awk -F: '{print $1}' | sort -u > live_hosts.txt
PORTS=$(cat open_ports.txt | awk -F: '{print $2}' | sort -nu | tr '\n' ',' | sed 's/,$//')
nmap -sV -sC -p "$PORTS" -iL live_hosts.txt -oA full_scan
```

---

## Nmap Script Integration

RustScan's `--` pass-through enables full nmap NSE execution on discovered ports.

### Service Enumeration Scripts

```bash
# SMB: enumeration + vuln check
rustscan -a TARGET -p 445 -- -sV --script smb-enum-shares,smb-enum-users,smb-vuln-ms17-010,smb2-security-mode

# HTTP: title + headers + methods
rustscan -a TARGET -p 80,443,8080,8443 -- -sV --script http-title,http-headers,http-methods,http-server-header

# FTP: anonymous login check
rustscan -a TARGET -p 21 -- -sV --script ftp-anon,ftp-syst,ftp-bounce

# MSSQL: info + auth
rustscan -a TARGET -p 1433 -- -sV --script ms-sql-info,ms-sql-config,ms-sql-empty-password

# LDAP: search + info
rustscan -a TARGET -p 389,636 -- -sV --script ldap-rootdse,ldap-search

# SSH: algorithms + version
rustscan -a TARGET -p 22 -- -sV --script ssh2-enum-algos,ssh-hostkey

# RDP: info + NLA check
rustscan -a TARGET -p 3389 -- -sV --script rdp-enum-encryption,rdp-vuln-ms12-020

# SNMP: community string brute + enum
rustscan -a TARGET -p 161 -- -sU -sV --script snmp-brute,snmp-info,snmp-sysdescr

# WinRM (PowerShell Remoting)
rustscan -a TARGET -p 5985,5986 -- -sV --script http-auth-finder
```

### Vulnerability Scripts

```bash
# EternalBlue (MS17-010)
rustscan -a TARGET -p 445 -- --script smb-vuln-ms17-010 -sV

# BlueKeep (CVE-2019-0708 RDP)
rustscan -a TARGET -p 3389 -- --script rdp-vuln-ms12-020

# Apache Struts
rustscan -a TARGET -p 8080 -- --script http-vuln-cve2017-5638

# Full vuln scan (all vuln category scripts — slow)
rustscan -a TARGET -p 80,443,445 -- --script vuln

# Safe scripts (no exploitation, just detection)
rustscan -a TARGET --range 1-65535 -- -sV --script safe
```

### UDP Services

```bash
# RustScan doesn't do UDP — use nmap directly for common UDP
nmap -sU -p 53,67,68,69,111,123,161,162,500,514,520 TARGET -sV

# NFS/RPC (UDP + TCP)
nmap -p 111 --script rpcinfo TARGET
nmap -p 2049 --script nfs-ls,nfs-showmount TARGET
```

---

## Firewall / IDS Evasion Techniques

### Timing Control

```bash
# Slowest scan — T1 timing for nmap, minimal rate
rustscan -a TARGET --range 1-65535 --timeout 5000 -b 100 -- -T1 -sV

# Spread scans over time (manual loop, 5 ports/sec)
for i in $(seq 1 1000 65535); do
  rustscan -a TARGET --range "$i-$((i+999))" -b 500 --timeout 2000 2>/dev/null
  sleep 5
done
```

### Decoy Scanning (nmap)

```bash
# Use decoy IPs to obscure source (nmap feature)
rustscan -a TARGET -p 80,443 -- -D 192.168.1.100,192.168.1.101,ME

# Randomize source port (avoid port-based blocking)
rustscan -a TARGET -p 445 -- --source-port 53
```

### Interface / Source IP

```bash
# Bind to specific interface
rustscan -a TARGET --range 1-65535 -- -e eth1

# Via proxychains (TCP only)
proxychains rustscan -a TARGET --range 1-1024 --timeout 5000 -b 100
```

### Fragment Packets (nmap)

```bash
rustscan -a TARGET -p 80 -- -f  # 8-byte fragment
rustscan -a TARGET -p 80 -- -ff # 16-byte fragment
rustscan -a TARGET -p 80 -- --mtu 24
```

---

## Port State Interpretation

| State | Meaning |
|-------|---------|
| `open` | Port accepting connections |
| `closed` | Port reachable but no listener (RST response) |
| `filtered` | No response or ICMP unreachable (firewall present) |
| `open\|filtered` | Can't determine — UDP or filtered TCP |
| `unfiltered` | Reachable but open/closed unknown (ACK scan) |

```bash
# ACK scan — map firewall rules (stateful vs stateless)
# Stateful firewall: all ports appear filtered
# Stateless/no firewall: closed ports appear unfiltered
nmap -sA -p 1-1000 TARGET

# Window scan — fingerprint OS from TCP window size
nmap -sW -p 80 TARGET

# Null/Xmas/FIN scans — bypass some stateless firewalls
nmap -sN TARGET  # Null
nmap -sX TARGET  # Xmas
nmap -sF TARGET  # FIN
# Response: no response = open|filtered; RST = closed
```

---

## Service-to-Tool Pipeline

After rustscan + nmap -sV identifies services, pivot to targeted tools:

| Port/Service | Next tool | Key command |
|------------|-----------|-------------|
| 21 FTP | ftp, hydra | `ftp TARGET` (anon login); `hydra -L users -P pass ftp://TARGET` |
| 22 SSH | ssh, hydra | `ssh-keyscan TARGET`; `hydra -l user -P pass ssh://TARGET` |
| 25 SMTP | swaks, nmap | `nmap --script smtp-enum-users,smtp-open-relay TARGET` |
| 80/443 HTTP | gobuster, nikto, ffuf | `gobuster dir -u http://TARGET -w /usr/share/wordlists/dirb/common.txt` |
| 139/445 SMB | crackmapexec, enum4linux | `crackmapexec smb TARGET -u '' -p '' --shares` |
| 389/636 LDAP | ldapsearch, ldapdomaindump | `ldapsearch -H ldap://TARGET -x -b "" -s base` |
| 1433 MSSQL | impacket mssqlclient | `mssqlclient.py sa:pass@TARGET` |
| 3306 MySQL | mysql | `mysql -h TARGET -u root -p` |
| 5432 PostgreSQL | psql | `psql -h TARGET -U postgres` |
| 5985/5986 WinRM | evil-winrm | `evil-winrm -i TARGET -u user -p pass` |
| 6379 Redis | redis-cli | `redis-cli -h TARGET info` |
| 8080 Tomcat | curl, msfvenom | `curl http://TARGET:8080/manager/html` |

---

## Subnet and CIDR Handling

```bash
# Single host
rustscan -a 10.10.10.5

# CIDR
rustscan -a 10.10.10.0/24

# Range notation
rustscan -a 10.10.10.1-10.10.10.50

# List from file
rustscan -a $(cat hosts.txt | tr '\n' ',')
# or use nmap with -iL (pass through)
rustscan -a 10.0.0.0/24 -- -iL extra_hosts.txt

# Exclude hosts
rustscan -a 10.0.0.0/24 -- --exclude 10.0.0.1,10.0.0.2

# Output only IPs of live hosts (fast ping sweep first)
nmap -sn 10.0.0.0/24 -oG - | grep "Up" | awk '{print $2}' > live_hosts.txt
rustscan -a $(cat live_hosts.txt | tr '\n' ',') --range 1-65535
```

---

## Performance Benchmarks and Tuning

| Batch size | Timeout | Network | Recommended for |
|-----------|---------|---------|----------------|
| 500 | 1500ms | LAN | Internal networks, lab |
| 2000 | 1500ms | LAN | Fast internal scans |
| 5000 | 1500ms | LAN | Very fast when ports mostly closed |
| 100 | 3000ms | VPN/WAN | Pivoted scans, remote targets |
| 50 | 5000ms | WAN | Slow remote targets, high latency |

```bash
# Auto-tune: RustScan adjusts automatically by default
# Override for specific scenarios:

# Aggressive LAN scan
rustscan -a 10.0.0.0/24 --range 1-65535 -b 3000 --timeout 1000

# Conservative VPN scan
rustscan -a 10.0.0.1 --range 1-65535 -b 100 --timeout 4000

# Check scan rate: watch RustScan output for "scanned in X seconds"
# If seeing drops: reduce -b, increase --timeout
```
