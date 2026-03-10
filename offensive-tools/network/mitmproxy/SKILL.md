---
name: mitmproxy
description: "mitmproxy: interactive TLS-capable HTTP/HTTPS proxy for intercepting, inspecting, modifying, and replaying web traffic. Use when proxying application traffic during web app tests, modifying requests/responses on the fly, or scripting request interception with Python addons."
license: MIT
compatibility: "Linux / macOS / Windows. pip install mitmproxy. Python 3.8+."
metadata:
  author: AeonDave
  version: "1.0"
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

## Resources

| File | When to load |
|------|--------------|
| `references/` | Addon API reference, transparent proxy setup |
