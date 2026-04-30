# Chisel — Proxychains Config & Tool Compatibility

## proxychains.conf Setup

```ini
# /etc/proxychains4.conf (or ~/.proxychains/proxychains.conf)

# Chain type: dynamic = skip dead proxies; strict = error if proxy dead
dynamic_chain
# strict_chain
# random_chain

# Quiet mode (suppress proxychains output)
quiet_mode

# Proxy DNS through the chain (prevents DNS leaks)
proxy_dns

[ProxyList]
socks5  127.0.0.1 1080
# Can chain multiple proxies:
# socks5  127.0.0.1 1080
# socks5  127.0.0.1 2080
```

```bash
proxychains4 <command>
# or just
proxychains <command>
```

## Tool Usage via Proxychains

### Network scanning

```bash
# nmap (must use -sT connect scan; SYN scan won't work through SOCKS)
proxychains nmap -sT -Pn -p 22,80,445,3389 192.168.1.0/24 -T3

# masscan doesn't work through proxychains (raw sockets)
# Use nmap -sT instead
```

### Active Directory tools

```bash
proxychains nxc smb 192.168.1.0/24
proxychains nxc smb 192.168.1.10 -u user -p pass --shares

proxychains evil-winrm -i 192.168.1.10 -u administrator -p 'Pass123!'

proxychains secretsdump.py domain/user:pass@192.168.1.10

proxychains GetUserSPNs.py corp.local/user:pass -dc-ip 192.168.1.5 -request

proxychains bloodhound-python -u user -p pass -d corp.local -ns 192.168.1.5 -c All
```

### Web

```bash
proxychains curl http://192.168.1.100
proxychains wget http://192.168.1.100/file

# With browser (Firefox)
# Set SOCKS5 proxy in Firefox network settings → 127.0.0.1:1080

# Burp Suite: add SOCKS5 upstream proxy in Project Options → Connections
```

### SSH / RDP

```bash
proxychains ssh user@192.168.1.10

proxychains xfreerdp /v:192.168.1.10 /u:admin /p:pass
```

## DNS Leak Prevention

```ini
# In proxychains.conf — enable this:
proxy_dns
```

Without `proxy_dns`, DNS queries go direct (leak real DNS, may reveal target info).

## Dynamic Chain vs Strict Chain

| Mode | Behavior | Use when |
|------|----------|----------|
| `dynamic_chain` | Skip unreachable proxies | Multiple proxies, some may be down |
| `strict_chain` | Fail if any proxy unreachable | Want guaranteed routing |
| `random_chain` | Random proxy from list | Opsec (different source each request) |

## Foxyproxy (Browser)

For browser-based testing without proxychains:

1. Install FoxyProxy (Firefox/Chrome extension)
2. Add proxy: Type=SOCKS5, Host=127.0.0.1, Port=1080
3. Activate for target domain or all traffic

## Tools That Don't Work with proxychains

| Tool | Reason | Alternative |
|------|--------|-------------|
| `masscan` | Raw sockets | Use nmap -sT |
| `ping` / `nmap -sS` | ICMP/SYN raw | nmap -sT -Pn |
| `nmap -sU` | Raw UDP | Limited; try specific port |
| `crackmapexec` (SMB, raw) | Some modules use raw | Use nxc or add `-no-bruteforce` |

## Port Forward Without proxychains (SSH Local Forward)

If SSH is available on pivot:

```bash
# Attacker: forward attacker:8888 → internal 192.168.1.100:80
ssh -L 8888:192.168.1.100:80 user@<pivot_ip>

# Dynamic SOCKS5 via SSH (alternative to chisel)
ssh -D 1080 user@<pivot_ip> -N
```
