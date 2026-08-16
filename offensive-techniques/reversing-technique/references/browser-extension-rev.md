# Browser Extension Reverse Engineering Supplement

Load this when the artifact is a Chrome/Edge/Firefox extension (`.crx`, `.xpi`, or an extracted extension directory) and the job is to recover permissions, injected logic, storage, traffic handling, or credential/signing behavior.

## Packaging and entry points

Prefer an extracted directory from the browser profile or unpack with `7z`/`unzip` when possible. Start at `manifest.json` and classify the model:

- **MV3**: `background.service_worker`, `host_permissions`, `declarativeNetRequest`
- **MV2**: `background.scripts` / background page, event pages, classic `webRequest`
- **Firefox**: similar WebExtension model, but API support can differ

Map every declared entry point before reading source:
- background page / service worker
- `content_scripts`
- popup / options / devtools page
- rulesets (`declarativeNetRequest`)
- externally reachable endpoints (`externally_connectable`, native host)

## Permission triage

High-signal manifest permissions:

- `<all_urls>` or broad `host_permissions` — page-wide DOM or traffic reach
- `webRequest` + `webRequestBlocking` — inline request/response tampering
- `cookies`, `tabs`, `history`, `downloads`, `clipboardRead`, `clipboardWrite`
- `debugger` — browser debugging/control surface
- `nativeMessaging` — host escape into a local companion process
- `externally_connectable` / `onMessageExternal` — webpage-to-extension trust boundary

Treat broad permissions as an attack-surface map, not proof. The next step is to locate the actual consumer code.

## Data-flow audit

Trace these channels explicitly:

1. **Page -> content script**
   - DOM reads, injected forms, intercepted tokens
2. **Content script -> background/service worker**
   - `chrome.runtime.sendMessage`, `chrome.tabs.sendMessage`, `Port` messaging
3. **External page -> extension**
   - `externally_connectable`, `onMessageExternal`, custom origin allowlists
4. **Extension -> local host**
   - `nativeMessaging` manifests, stdin/stdout framing with the native helper
5. **Persistent state**
   - `chrome.storage.local/sync/session`, IndexedDB, cached tokens, allowlists, signing keys

Content scripts run in an **isolated world**. If they must touch page variables directly, look for a bridge via injected `<script>` tags or `window.postMessage`.

## Dynamic workflow

- Load the unpacked extension in developer mode.
- For **MV3**, inspect the service worker from `chrome://extensions`; it sleeps and respawns, so log durable events and re-check lifecycle assumptions.
- Watch `chrome.runtime.lastError` on failed message/API paths.
- Use DevTools Network + Sources for fetch/XHR/WebSocket initiated by the extension, not just the page.

If the logic is heavily obfuscated or bundled, pivot to the JS workflow (`document-script-analysis.md`) for webpack module recovery, eval tracing, and request-signing reconstruction.

## What to recover

Aim to name:
- which pages/origins the extension can touch
- where credentials/tokens are read, stored, or forwarded
- which messages cross trust boundaries and with what validation
- whether request modification is declarative (`declarativeNetRequest`) or imperative (`webRequest` handlers)
- whether a native host or external webpage can drive privileged actions

## Common mistakes

- Reading only `manifest.json` and never tracing the consumer code.
- Treating MV3 service workers like always-on background pages.
- Forgetting `content_scripts` are isolated from page JS unless a bridge is built.
- Missing `onMessageExternal` / `externally_connectable` trust edges.
- Auditing page traffic but not extension-originated fetch/XHR/WebSocket requests.
