---
name: mitmproxy
description: "Auth/lab ref: interactive TLS-capable HTTP/HTTPS proxy for intercepting, inspecting, modifying, and replaying web traffic."
license: MIT
compatibility: "Linux / macOS / Windows; Python 3.8+."
metadata:
  author: AeonDave
  version: "1.1"
---

# mitmproxy

Interactive HTTP/HTTPS MITM proxy.

## Quick Start

```bash
mitmproxy -p 8080
mitmweb -p 8080
mitmdump -p 8080 -w traffic.dump
```
Install CA cert: browse to `http://mitm.it` while proxy is running.

## Modes

| Mode | Command | Use case |
|------|---------|----------|
| Regular proxy | `mitmproxy` | Browser/tool proxying |
| Transparent | `--mode transparent` | Intercept without proxy config |
| Reverse | `--mode reverse:http://target` | Reverse proxy |
| SOCKS5 | `--mode socks5` | SOCKS proxy |

## TUI Keybindings

| Key | Action |
|-----|--------|
| `Enter` | Inspect request |
| `e` | Edit request/response |
| `r` | Replay request |
| `f` | Set filter |
| `i` | Set intercept filter |

## Python Addon

```python
from mitmproxy import http

def request(flow: http.HTTPFlow):
    if flow.request.method == "POST":
        print(flow.request.pretty_url, flow.request.get_text())
```
```bash
mitmproxy -s addon.py
```

## Useful Addons

```python
# Dump all POST bodies
from mitmproxy import http

def request(flow: http.HTTPFlow):
    if flow.request.method == "POST":
        with open("posts.txt", "a") as f:
            f.write(f"{flow.request.pretty_url}\n{flow.request.get_text()}\n---\n")
```

```python
# Modify response (e.g. replace token)
def response(flow: http.HTTPFlow):
    if "api/auth" in flow.request.pretty_url:
        flow.response.text = flow.response.text.replace(
            '"role":"user"', '"role":"admin"'
        )
```

```python
# Add header to all requests (e.g. auth bypass)
def request(flow: http.HTTPFlow):
    flow.request.headers["X-Admin"] = "true"
    flow.request.headers["X-Forwarded-For"] = "127.0.0.1"
```

## Transparent Proxy Setup (Linux)

```bash
# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Redirect traffic to mitmproxy (iptables)
iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 8080
iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 443 -j REDIRECT --to-port 8080

# Start in transparent mode
mitmproxy --mode transparent --showhost -p 8080
```

## CLI Filtering (mitmdump)

```bash
# Capture only POST requests
mitmdump -p 8080 -w traffic.dump "~m POST"

# Capture by domain
mitmdump -p 8080 -w traffic.dump "~d example.com"

# Show only responses with 2xx status
mitmdump -p 8080 "~s ~c 2"
```

## Resources

| File | When to load |
|------|--------------|
| `references/addons.md` | Full addon API reference, filter syntax, transparent proxy iptables, upstream proxy chaining |
