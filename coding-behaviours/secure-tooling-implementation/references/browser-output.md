# Browser output and message boundaries

Load when a security tool displays hostile artifacts, URLs or model output in a browser, or accepts messages from another window/frame. Keep original evidence separate from its display representation.

## Render data without granting execution

- For logs, names, code and plain text, use `textContent` or framework text binding. Build fixed structure with DOM APIs; do not concatenate artifact data into `innerHTML`, event handlers, scripts or CSS.
- Parse links with `URL` against an explicit base and allow only the schemes and destinations needed by the feature. An escaped label does not make a `javascript:` URL safe. Do not treat a same-site sibling as an authorized origin or redirect destination.
- When rich HTML is required, use the exact supported safe sanitizer API, such as `Element.setHTML()`, or a maintained sanitizer with an explicit policy. Test what content survives in both native and fallback paths. If neither path is available, display text or an explicit unavailable preview; never fall back to raw insertion.
- `setHTMLUnsafe()`, `parseHTMLUnsafe()` and ordinary HTML parsing do not sanitize by default. Avoid serializing sanitized nodes and reparsing them through an unsafe sink. Sanitizer output modified afterward needs renewed review. See the [HTML parsing and insertion contract](https://html.spec.whatwg.org/multipage/dynamic-markup-insertion.html).
- Treat embedded data as a separate parser boundary. `JSON.stringify()` alone does not safely embed hostile values inside an HTML `<script>` element: a literal closing script tag can end it even for `type="application/json"`. Prefer separately served JSON or a framework's context-safe serializer; for a standalone file, use an embedding format that cannot contain a literal `<`, decode as data, and render with safe sinks. See [script data-block restrictions](https://html.spec.whatwg.org/multipage/scripting.html#restrictions-for-contents-of-script-elements).
- A preview in `srcdoc` or a blob URL is not automatically isolated. CSP inheritance, origin, iframe sandbox tokens, navigation and message privileges still apply. Prefer inert text for hostile documents; when a rendered preview is necessary, define and test its isolation contract rather than granting scripts and same-origin access by default. See [CSP inheritance](https://www.w3.org/TR/CSP3/#security-inherit-csp).

## Trusted Types and CSP

Use [Trusted Types](https://www.w3.org/TR/trusted-types/) to constrain reviewed injection paths on supporting targets. The type name does not certify safety: audit policy callbacks, default policies, parser options and the actual sink. A policy that returns hostile input unchanged defeats the boundary. A tinyfill cannot reproduce browser-enforced sink checks.

Keep sanitization effective when enforcement is unavailable. For deployment, test framework/dependency sink usage, policy-name restrictions and failures under the effective CSP; a report-only policy reports violations without blocking them. Safe native sanitization and an `innerHTML`-based library fallback may have different Trusted Types requirements.

CSP supplements safe rendering. `connect-src` governs `fetch` and XHR; switching between them does not bypass it. It is not a complete outbound firewall, and loopback binding/CORS do not replace authentication or authorization on a local service. Audit each resource and action path actually exposed. See [CSP directives](https://www.w3.org/TR/CSP3/#directives).

## Cross-window messages

- For tuple origins, require an exact trusted scheme/host/port, not substring, suffix or same-site matching. Validate message shape, allowed operation and values before acting; origin acceptance alone is not permission for every command.
- Check `event.source` against the intended window/frame when instance identity matters. Reject serialized `"null"` as an origin allowlist entry: unrelated opaque contexts can share that string. A deliberate sandbox integration needs a separately established peer/channel and narrow capabilities, including navigation/reload handling.
- Send confidential data with an exact `targetOrigin`; a wildcard is not a trusted-peer check. For intentionally opaque peers, design a bounded channel instead of broadening ordinary origin checks. See the [HTML messaging security contract](https://html.spec.whatwg.org/multipage/web-messaging.html#security-postmsg).

## Control outbound resource loading

- Sanitized markup may still load images or other resources. For an offline or sensitive evidence viewer, disallow remote resource-bearing markup or render controlled local assets. Verify requests in the browser; removing scripts is not a no-network guarantee.
- Do not prefetch/prerender arbitrary evidence URLs or action links. Speculative navigation can cause requests before a click, execute page code, consume resources and use stale state. Limit any such optimization to explicitly selected application-owned routes whose side effects and activation behavior are understood. See [speculation rules for complex sites](https://developer.chrome.com/docs/web-platform/implementing-speculation-rules).
- When external scripts/styles are permitted, pin reviewed assets. SRI requires a trusted expected digest; deriving it from the same untrusted response is not independent verification. Cross-origin integrity-protected resources also need the appropriate CORS response. Prefer bundled resources for promised offline delivery. See [Subresource Integrity](https://www.w3.org/TR/SRI/).

## Boundary checks

Select checks for the implemented boundaries: a harmless execution marker in rich HTML, closing-script text in embedded data, a disallowed URL scheme, remote-image markup, and messages from a wrong origin and wrong source. Where present, exercise native and fallback sanitizer paths, missing dependencies and the effective CSP in the real renderer. Confirm literal evidence is preserved separately, unsafe effects do not occur, and failures remain visible. Use owned test endpoints; rendering hostile content must not contact its original infrastructure to prove a boundary.
