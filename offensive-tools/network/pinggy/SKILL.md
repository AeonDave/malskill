---
name: pinggy
description: "Auth/lab ref: Pinggy localhost tunneling service for HTTP(S), TCP, UDP, TLS, and TLSTCP tunnels over SSH, Pinggy CLI, Docker, GUI app, Node.js SDK, or Python SDK."
license: MIT
compatibility: "some features require Pinggy Pro or Enterprise."
metadata:
  author: AeonDave
  version: "1.0"
---

# Pinggy

Public reverse tunnels to localhost using SSH remote forwarding or the Pinggy CLI. Use for authorized dev/test ingress, webhook capture, controlled lab callbacks, and temporary remote access without router port forwarding.

## Scope Guard

- Confirm the exposed service, audience, time window, and authorization before creating a public URL or port.
- Default to short-lived tunnels, strong app-layer auth, and IP allowlists for anything sensitive.
- Do not expose admin consoles, databases, model servers, MCP tools, or shells to the internet without explicit access controls and owner approval.
- Prefer `tls` for end-to-end encrypted HTTPS services when Pinggy must not inspect HTTP content; HTTP tunnels terminate at Pinggy to provide debugger and header features.

## Choose the Mode

| Need | Mode | Pattern | Notes |
|---|---|---|---|
| Share web app/API/webhook | `http` default | `ssh -p 443 -R0:localhost:8000 free.pinggy.io` | Provides HTTP+HTTPS URLs, debugger, auth, header manipulation. |
| Expose arbitrary TCP service | `tcp` | `ssh -p 443 -R0:localhost:22 tcp@free.pinggy.io` | Returns host+port; use for SSH, databases, listeners, raw protocols. |
| End-to-end HTTPS by SNI | `tls` | `ssh -p 443 -R0:localhost:8443 tls@free.pinggy.io` | No public TCP port; visitor connects to generated domain on 443; local service terminates TLS. |
| TCP with optional TLS wrapper | `tlstcp` | `ssh -p 443 -R0:localhost:8000 tlstcp@free.pinggy.io` | Gives TCP port plus TLS endpoint that terminates at Pinggy then forwards plaintext. |
| Expose UDP service | `udp` | `./pinggy --type udp -l 8000` | UDP requires Pinggy CLI/Docker; SSH-only form is not supported. |
| Persistent name/port | Pro token | `ssh -p 443 -R0:localhost:8000 TOKEN@pro.pinggy.io` | Use token, dashboard, custom/persistent domains, persistent TCP/UDP ports. |

## Quick Starts

```bash
# HTTP(S) via OpenSSH
ssh -p 443 -R0:localhost:8000 free.pinggy.io

# HTTP(S) with QR code in terminal
ssh -p 443 -R0:localhost:8000 qr@free.pinggy.io

# TCP tunnel to local SSH
ssh -p 443 -R0:localhost:22 tcp@free.pinggy.io

# TLS tunnel to local HTTPS service
ssh -p 443 -R0:localhost:8443 tls@free.pinggy.io

# CLI equivalents
pinggy -l 8000
pinggy --type tcp -l 22
pinggy --type udp -l 51820

# Docker HTTP tunnel on Linux
docker run --net=host -it pinggy/pinggy -p 443 -R0:localhost:8000 a.pinggy.io
```

On Windows, if `localhost` fails through OpenSSH, retry with `127.0.0.1`.

## SSH Grammar

```text
ssh -p443 -R0:<local_host>:<local_port> [more -R rules] [<token>+<keywords>@]a.pinggy.io [remote options]
```

Useful SSH flags:

| Flag | Use |
|---|---|
| `-p 443` | Pinggy listens on 443 to pass most egress firewalls. |
| `-R0:localhost:PORT` | Expose exactly one local service; Pinggy assigns remote URL/port. |
| `-L4300:localhost:4300` | Open local access to the Web Debugger UI/API. |
| `-t` | Allocate TTY; needed for rich UI and command-line options like auth/header controls. |
| `-T` | Disable rich terminal UI for scripts. |
| `-N` | Disables remote command execution; avoid when using debugger/header/auth features. |

Username keywords are joined with `+`: `TOKEN+tcp+force@a.pinggy.io`, `qr@a.pinggy.io`, `TOKEN+tls@pro.pinggy.io`.

| Keyword | Effect |
|---|---|
| `http`, `tcp`, `tls`, `tlstcp` | Select tunnel type; HTTP is default. |
| `qr`, `aqr` | Print Unicode or ASCII QR code for quick mobile access. |
| `auth` | Force SSH password prompt compatibility; any string/blank password is acceptable. |
| `force` | Disconnect an existing tunnel using the same token before reconnecting. |

## HTTP Controls

Append these after the SSH destination and use `-t`:

```bash
# Basic auth; username/password cannot contain ':'
ssh -p 443 -R0:localhost:8000 -t free.pinggy.io b:user:pass

# Multiple bearer keys: visitor sends Authorization: Bearer <key>
ssh -p 443 -R0:localhost:8000 -t free.pinggy.io k:key1 k:key2

# IP/CIDR allowlist
ssh -p 443 -R0:localhost:8000 -t free.pinggy.io w:203.0.113.10/32

# HTTPS-only redirect, CORS preflight pass-through, original URL header
ssh -p 443 -R0:localhost:8000 -t free.pinggy.io x:https x:passpreflight x:fullurl

# Local service expects HTTPS/TLS
ssh -p 443 -R0:localhost:8443 -t free.pinggy.io x:localServerTls:example.com

# Header manipulation: append, remove, update
ssh -p 443 -R0:localhost:8080 -t free.pinggy.io a:X-Lab:pinggy r:Referer u:Host:example.com
```

Other controls:

| Option | Purpose |
|---|---|
| `x:xff[:Header-Name]` | Add source IP header, or use a custom header name. |
| `x:noreverseproxy` | Disable default reverse-proxy headers for HTTP tunnels. |
| `x:passpreflight` | Let unauthenticated CORS preflight requests pass when auth is enabled. |
| `a:Header:Value` | Append request header. |
| `r:Header` | Remove request header. |
| `u:Header:Value` | Replace request header; useful for `Host`. |

## Web Debugger

```bash
ssh -p 443 -R0:localhost:8080 -L4300:localhost:4300 a.pinggy.io
# Open http://localhost:4300
# API examples: GET /urls, GET /ipwhitelist
```

Use it to inspect requests/responses, replay modified HTTP requests, verify webhook payloads, and compare proxy headers before involving Burp, ZAP, mitmproxy, or app logs. Do not use HTTP debugger mode for secrets that Pinggy should not see; choose `tls` instead.

## Multi-Forwarding and Domains

Pro tokens can route multiple services through one session, especially with wildcard custom domains.

```bash
ssh -p 443 \
  -R http//app.example.com:1:localhost:3000 \
  -R http//api.example.com:1:localhost:8080 \
  -R tcp//ssh.example.com/34567:1:localhost:22 \
  -R 1:localhost:80 \
  TOKEN@pro.pinggy.io
```

Listen address syntax: `[schema//]hostname[/port][@name]`. Schemas include `http`, `tcp`, `tls`, `tlstcp`, and `udp`. Custom domains use CNAME where possible; apex/root domains use relay setup. Relay-based custom domains do not support UDP, so use persistent subdomains/ports for UDP.

## Offensive Lab Synergies

Use Pinggy as the public ingress layer; pair it with specialist tools locally.

| Workflow | Pinggy role | Pair with |
|---|---|---|
| Webhook and API testing | Public HTTPS receiver to localhost | Burp Suite, ZAP, mitmproxy, curl, jq, app logs |
| Controlled reverse-callback labs | Public TCP port to an owned listener | ncat/socat, Metasploit handlers, tcpdump, Wireshark |
| External service validation | Temporary public host/port for owned service | nmap, httpx, nuclei, testssl, browser devtools |
| Header/auth edge cases | Modify `Host`, XFF, bearer/basic auth, CORS | Burp Repeater, ZAP Manual Request, mitmproxy scripts |
| IoT and remote admin | TCP tunnel to SSH/dashboard on owned device | ssh, scp, rsync, netdata, Home Assistant |
| Database or cache demos | TCP tunnel with allowlist to local DB | psql, mysql, redis-cli, mongosh, sqlmap only against owned labs |
| UDP service tests | CLI/Docker UDP tunnel | WireGuard lab, game servers, VoIP/game protocol tooling |
| Reverse proxy routing | Wildcard domain + multi-forwarding | Traefik, nginx, Kubernetes port-forward, Docker Compose |

When an operation needs SOCKS pivoting through a compromised host, prefer chisel. Use Pinggy when a public SaaS ingress endpoint is acceptable and fast setup matters more than stealth or routing.

## CLI, SDK, Docker, and APIs

```bash
# CLI install and basic use
npm install -g pinggy
pinggy --help
pinggy -l 8000
pinggy --type tcp -l 22
pinggy --serve /path/to/files

# Saved configs and auto-start
pinggy config save my-tunnel -l 3000 TOKEN@pro.pinggy.io
pinggy start my-tunnel
pinggy start --all
pinggy start --all --remote-management <API_KEY>
```

- CLI has auto-reconnect, JSON-style saved configuration, file-server mode, logging, and remote management.
- Node.js SDK: use `@pinggy/pinggy`, `pinggy.forward({ forwarding: "localhost:5000" })`, then read `tunnel.urls()`.
- Python SDK: install `pinggy`, then `pinggy.start_tunnel(forwardto="localhost:8000")`.
- Pro API can list active tunnels and query session history with `Authorization: Bearer <API_KEY>`.

## Egress-Constrained Clients

```bash
# HTTP proxy with nc/ncat
ssh -p443 -R0:localhost:4000 -o ProxyCommand="nc -X connect -x 192.0.2.10:3128 %h %p" a.pinggy.io
ssh -p443 -R0:localhost:4000 -o ProxyCommand="ncat --proxy-type http --proxy 192.0.2.10:3128 %h %p" a.pinggy.io

# SSH-over-SSL when only TLS egress is allowed
ssh -p443 -R0:localhost:4000 -o ProxyCommand="openssl s_client -quiet -connect %h:%p" a.pinggy.io
ssh -p7878 -R0:localhost:4000 -o ProxyCommand="ncat --ssl %h %p" a.pinggy.io
```

Use these only when policy allows outbound proxy/TLS tunneling. On Windows, PuTTY proxy settings or installed OpenSSL/ncat can fill the same role.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Password prompt | Press Enter, type any string, or generate an SSH key for long-running tunnels. |
| Windows tunnel cannot reach service | Replace `localhost` with `127.0.0.1`. |
| URL changes | Free tunnels are random and time-limited; use Pro persistent subdomain/custom domain. |
| UDP not working with SSH | Use Pinggy CLI or Docker; SSH-only UDP is not supported. |
| Advanced options ignored | Add `-t` and avoid `-N`. |
| Token already active | Stop it in dashboard or use `TOKEN+force@...`. |
| Sensitive data visible in debugger | Switch from HTTP to `tls` and terminate TLS locally. |
| Public exposure too broad | Add `b:`, `k:`, `w:`, shorten runtime, or bind local service to a disposable lab instance. |

## Resources

| File | When to load |
|---|---|
| `references/usage-matrix.md` | Full use-case coverage, offensive lab pairings, quickstart recipe taxonomy, and feature-to-protocol mapping. |
