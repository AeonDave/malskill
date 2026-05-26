# Pinggy Usage Matrix

Use this reference when the user asks for all Pinggy use cases, protocol selection, offensive-lab pairings, or how Pinggy fits with other tools.

## Protocol-to-Use Mapping

| Protocol | Best for | Avoid when |
|---|---|---|
| HTTP(S) | Web apps, APIs, webhooks, request replay, header manipulation, Basic/Bearer auth, IP allowlist. | End-to-end privacy is required; Pinggy terminates HTTP(S). |
| TCP | SSH, databases, raw services, callback listeners, arbitrary client/server protocols. | Browser-friendly HTTPS URL is required. |
| TLS | End-to-end encrypted HTTPS/TLS where local service owns certificates/SNI. | Need Pinggy web debugger/header modification. |
| TLSTCP | TCP services where visitors benefit from TLS wrapping at Pinggy. | Local service must see the visitor TLS session end-to-end. |
| UDP | WireGuard labs, UDP game servers, telemetry/IoT/multiplayer protocol tests. | Only OpenSSH is available; use CLI/Docker instead. |

## Documented Application Families

Pinggy quickstarts and docs cover these practical categories:

| Family | Examples | Recommended tunnel |
|---|---|---|
| Python/web frameworks | Django, Flask, FastAPI-style local APIs, Jupyter Notebook | HTTP with auth/IP allowlist; TLS for sensitive notebooks. |
| JavaScript/web frameworks | Express, React, Next.js, Nuxt, Svelte, Vue, Node services | HTTP; use `u:Host` if framework validates hostnames. |
| CMS and web servers | Apache, Nginx, Drupal, Joomla, Laravel, WordPress, Ghost, WAMP, XAMPP | HTTP; custom domain for realistic virtual-host testing. |
| DevOps dashboards | GitLab, Portainer, Netdata, Traefik, Kubernetes services | HTTP/TCP with strict `w:` allowlist and app auth. |
| Databases/caches | PostgreSQL, MySQL/MariaDB, MSSQL, MongoDB, Redis | TCP with allowlist; prefer temporary credentials and lab data. |
| Webhook providers | GitHub, GitLab, Slack, Stripe, Shopify, Razorpay, PayPal, Telegram, Twilio, WhatsApp, Discord | HTTP with Web Debugger and replay. |
| IoT/home lab | Raspberry Pi, Home Assistant, IP cameras, SSH into Linux/Mac/Windows/IoT | TCP for SSH/raw access; HTTP for dashboards; Pro for persistent endpoints. |
| File sharing | `python3 -m http.server`, `pinggy --serve`, Nextcloud | HTTP with Basic/Bearer auth and short lifetime. |
| AI/local tools | Ollama/Open WebUI, LM Studio, OpenLLM, ComfyUI, n8n, Langflow, MCP servers, Jan, Obsidian/Memos | HTTP/TLS with strong auth; never expose tool-capable agents unauthenticated. |
| Games/voice/UDP | Minecraft, Foundry VTT, WireGuard-style UDP labs | TCP or UDP depending on service; reserve persistent port for stable clients. |

## Offensive Lab Patterns

All patterns assume explicit authorization and owned lab infrastructure.

### 1. Webhook Capture and Replay

1. Run the local app/API.
2. Start HTTP tunnel with debugger: `ssh -p 443 -R0:localhost:PORT -L4300:localhost:4300 a.pinggy.io`.
3. Register the HTTPS URL in the webhook provider.
4. Inspect payloads in `http://localhost:4300`, then replay modified requests locally.
5. Pair with Burp/ZAP/mitmproxy when deeper request mutation or scanner integration is needed.

### 2. Controlled Reverse Callback Receiver

1. Start an owned local listener on a chosen port.
2. Start a TCP tunnel: `ssh -p 443 -R0:localhost:PORT tcp@free.pinggy.io`.
3. Use the returned host and port as the callback destination in the authorized lab.
4. Capture local traffic with tcpdump/Wireshark and keep server-side logs.

Use this for reachability and handler testing; do not use Pinggy as covert persistence.

### 3. Public-Facing Scanner Harness

1. Expose a disposable local service over HTTP/TCP.
2. Scan only the generated Pinggy endpoint you own with tools such as `httpx`, `nmap`, `testssl`, `nuclei`, or browser devtools.
3. Compare external scanner findings with local service logs and Pinggy debugger output.
4. Tear down the tunnel after validation.

### 4. Header and Reverse-Proxy Behavior Testing

- Use `u:Host:<host>` for virtual-host routing tests.
- Use `x:xff` or `x:noreverseproxy` to compare app behavior with and without proxy headers.
- Use `x:fullurl` to pass `X-Pinggy-Url` when the backend needs the original external URL.
- Use `x:passpreflight` with Basic/Bearer auth when browser CORS preflight must reach the backend.

### 5. Remote Device Access

- TCP tunnel `localhost:22` for SSH into owned devices behind NAT/CGNAT.
- HTTP tunnel dashboards such as Home Assistant, Netdata, Portainer, IP-camera web UIs.
- Prefer Pro persistent subdomain/port plus IP allowlist for devices left online longer than a short test.

### 6. Database and Admin Service Demonstrations

- Use TCP tunnels only with throwaway data or test credentials.
- Add IP allowlists and app/database authentication; do not rely on obscurity of random ports.
- Pair clients with `psql`, `mysql`, `redis-cli`, `mongosh`, SQL workbenches, or security tools only in owned labs.

### 7. Kubernetes, Docker, and Reverse Proxy Workflows

- Combine `kubectl port-forward` to localhost with Pinggy HTTP/TCP for external review.
- Combine Traefik/nginx with wildcard custom domain and multi-forwarding to route multiple local services.
- Docker on Linux: use `--net=host`; on macOS/Windows map debugger ports and account for `host.docker.internal`.

## Integration Cheat Sheet

| Local tool | How Pinggy helps |
|---|---|
| Burp Suite / ZAP | Send provider traffic to local app, then inspect/replay in Burp or Pinggy debugger. |
| mitmproxy | Script request/response mutation while Pinggy supplies the public URL. |
| curl / httpie / jq | Validate Pinggy URLs, debugger APIs, webhook payloads, and API responses. |
| nmap / httpx / testssl / nuclei | Validate owned public exposure from an external perspective. |
| ncat / socat | Host controlled TCP listeners or protocol shims behind a Pinggy TCP tunnel. |
| tcpdump / Wireshark / Zeek | Record local-side traffic for evidence and troubleshooting. |
| ssh / scp / rsync | Remote access and file transfer to owned devices over TCP tunnel. |
| proxy-aware tools | Use `ProxyCommand` with nc/ncat/openssl when egress requires HTTP proxy or SSH-over-SSL. |
| SIEM/log pipeline | Forward app and debugger logs into observability; Pinggy Pro APIs can list active/history sessions. |

## Feature Notes and Limits

- Free plan URLs are random and tunnels are time-limited; use Pro for persistent subdomains, custom domains, wildcard domains, persistent TCP/UDP ports, teams, remote device management, and APIs.
- Regions are selected through Pinggy server hostnames/dashboard; `a.pinggy.io` routes to a nearby server.
- Basic auth uses `b:user:pass`; neither field can contain `:`.
- Bearer auth uses `k:key` and expects `Authorization: Bearer <key>`.
- IP allowlist uses `w:IP` or `w:[IP1,IP2,CIDR...]` and silently drops non-matching clients.
- HTTP reverse proxy mode adds forwarding headers by default; disable with `x:noreverseproxy`.
- `Host` header cannot be removed; update it with `u:Host:value`.
- Web Debugger local API includes `/urls` and `/ipwhitelist` on the forwarded debugger port.
- `-R` exposes only the local host/port specified by the user, not the entire machine.
- UDP tunnels require Pinggy CLI or Docker.
- Relay-based root/apex custom domains support HTTP(S), TLS, and TCP, but not UDP.

## Source Anchors

Official Pinggy pages used to shape this reference: homepage, docs quickstart, usages reference, HTTP/TCP/TLS/TLSTCP/UDP tunnel docs, Web Debugger, Basic Auth, Key Auth, IP Whitelist, Live Header Modification, Advanced Options, Multiple Forwardings, Persistent Subdomain, Custom Domain/Relays, CLI, Docker, Remote Devices, Pro API, Client Behind Proxy, Long-running Tunnels, and Quickstart Recipes.
