# mitmproxy — Addon API & Advanced Reference

## Addon Hooks

| Hook | Trigger |
|------|---------|
| `request(flow)` | Client sends request (before server) |
| `response(flow)` | Server responds (before client) |
| `tls_start_client(data)` | TLS handshake with client starts |
| `tls_start_server(data)` | TLS handshake with server starts |
| `error(flow)` | Connection error |
| `running()` | mitmproxy started |

## Flow Object Reference

```python
flow.request.method           # GET, POST, etc.
flow.request.pretty_url       # Full URL with host
flow.request.url              # URL without scheme//host
flow.request.host             # Hostname
flow.request.port             # Port
flow.request.path             # Path + query
flow.request.headers          # Headers dict (mutable)
flow.request.content          # Raw bytes
flow.request.text             # Decoded text
flow.request.get_text()       # Body as string
flow.request.query            # Query params dict
flow.request.urlencoded_form  # application/x-www-form-urlencoded body
flow.request.multipart_form   # multipart form body

flow.response.status_code     # 200, 404, etc.
flow.response.headers         # Headers dict (mutable)
flow.response.content         # Raw bytes
flow.response.text            # Decoded text
flow.response.json()          # Parse JSON response
```

## Addon: Credential Logger

```python
from mitmproxy import http
import json, re

class CredLogger:
    def request(self, flow: http.HTTPFlow):
        if flow.request.method != "POST":
            return
        url = flow.request.pretty_url
        body = flow.request.get_text(strict=False)
        if re.search(r'(pass|pwd|password|token|secret|api.?key)', body, re.I):
            with open("credentials.txt", "a") as f:
                f.write(f"URL: {url}\nBODY: {body}\n{'='*60}\n")

addons = [CredLogger()]
```

## Addon: JSON Response Modifier

```python
from mitmproxy import http
import json

def response(flow: http.HTTPFlow):
    if "application/json" in flow.response.headers.get("content-type", ""):
        try:
            data = flow.response.json()
            if "admin" in data:
                data["admin"] = True
                flow.response.text = json.dumps(data)
        except Exception:
            pass
```

## Addon: Replay + Fuzz

```python
from mitmproxy import http, ctx

PAYLOADS = ["' OR 1=1--", "<script>alert(1)</script>", "../../../../etc/passwd"]

class Fuzzer:
    def request(self, flow: http.HTTPFlow):
        if "search" in flow.request.query:
            for p in PAYLOADS:
                req = flow.request.copy()
                req.query["search"] = p
                ctx.master.commands.call("replay.client", [req])

addons = [Fuzzer()]
```

## Filter Syntax (mitmdump / TUI)

| Expression | Matches |
|-----------|---------|
| `~m POST` | POST method |
| `~u example.com` | URL contains |
| `~d example.com` | Domain |
| `~s` | Responses only |
| `~q` | Requests only |
| `~c 200` | Status code |
| `~t application/json` | Content-type |
| `~b password` | Body contains |
| `~h Authorization` | Header contains |
| `~a` | All |
| `~m POST & ~d login` | AND |
| `~m GET | ~m POST` | OR |
| `! ~d google.com` | NOT |

## Upstream Proxy Chaining

```bash
# Route mitmproxy through Burp Suite
mitmproxy -p 8080 --mode upstream:http://127.0.0.1:8081

# Route through SOCKS5
mitmproxy -p 8080 --mode upstream:socks5://127.0.0.1:1080
```

## Certificate Installation

```
# While proxy running, browse to:
http://mitm.it

# Android: install .cer from mitm.it/cert/android
# iOS: install .pem, then trust in Settings > General > About > Certificate Trust
# Linux: cp ~/.mitmproxy/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt && update-ca-certificates
# Windows: Double-click mitmproxy-ca-cert.p12, import to Trusted Root CAs
```

## Save / Replay Flows

```bash
# Save to file
mitmdump -p 8080 -w flows.dump

# Replay saved flows against target
mitmdump -n -r flows.dump --set server_replay_kill_extra=true
```
