---
name: proxychains-ng
description: "proxychains-ng — SOCKS/HTTP proxy wrapper for any TCP command: route nmap, impacket, curl, ssh through pivot tunnels without modifying the tool. Use with chisel/ssh -D/ligolo SOCKS listeners to reach internal networks."
license: MIT
compatibility: "Linux/macOS (LD_PRELOAD mechanism — does not work with static binaries or setuid); config at /etc/proxychains4.conf or proxychains4.conf in cwd."
metadata:
  author: AeonDave
  version: "1.0"
---

# proxychains-ng

LD_PRELOAD wrapper that routes TCP connections from any dynamically-linked binary through SOCKS4/5 or HTTP proxies. The de-facto companion to `chisel` and `ssh -D` pivots: point proxychains at the SOCKS listener, and every tool that doesn't natively support a proxy becomes pivot-aware.

## Core workflow

```bash
# Config: /etc/proxychains4.conf or ./proxychains4.conf
# Last line of the [ProxyList] section = the exit proxy:
#   socks5  127.0.0.1 1080

# Route a command through the tunnel
proxychains4 nmap -sT -Pn -n -p 445 10.10.10.0/24
proxychains4 impacket-smbexec domain/user:pass@10.10.10.5
proxychains4 curl http://10.10.10.5:8080/admin

# Quiet mode (suppress proxychains banner)
proxychains4 -q nmap -sT -Pn 10.10.10.0/24

# Chain multiple proxies (strict_chain = all must be alive; dynamic_chain = skips dead)
# proxychains4.conf: strict_chain → proxy_dns → [socks5 ...] [socks5 ...]
```

## Best practice

- **Nmap through proxychains**: use `-sT` (full TCP connect) — SYN scan (`-sS`) sends raw packets that bypass the SOCKS layer and leak the operator IP.
- **`dynamic_chain` over `strict_chain`**: dynamic skips dead proxies instead of failing the whole chain. Use `strict_chain` only when the order matters.
- **`proxy_dns`** in the config routes DNS through the proxy — without it, DNS leaks via the host resolver and reveals the target's internal hostnames to your DNS server.
- **`quiet_mode`** in the config suppresses the banner on every invocation.
- Custom config file: `proxychains4 -f ./proxychains4.conf <cmd>` — per-engagement config without touching `/etc`.

## Gotchas

- **Static binaries don't work** (no LD_PRELOAD): Go-compiled tools, musl-linked binaries, and setuid programs bypass the wrapper. Use `graftcp` for those, or the tool's native proxy flag.
- ICMP traffic (ping) is not proxied — only TCP connections.
- UDP is not supported in SOCKS4; SOCKS5 requires the server to support UDP ASSOCIATE (most pivots don't).
- DNS resolution inside proxychains is done by the proxy itself (`proxy_dns`) — but nmap still does its own resolution with `-n` flag recommended to avoid double-lookup delays.

## References

- Upstream: [rofl0r/proxychains-ng](https://github.com/rofl0r/proxychains-ng)
- Companions: `chisel` (SOCKS listener via HTTP tunnel), `ssh-tunneling` (`ssh -D` SOCKS), `ligolo-ng` (TUN-based alternative — no proxychains needed)
