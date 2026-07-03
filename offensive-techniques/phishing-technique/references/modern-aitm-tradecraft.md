# Modern AitM and Non-Email Phishing Tradecraft (2024+)

Load when authorization explicitly covers MFA/session interception, OAuth device code abuse, in-page auth spoofing, chat-platform pivoting, QR delivery, or paste-and-run lures. Every vector below assumes the authorization gate in `SKILL.md` has been cleared.

## 1. AitM PhaaS kit landscape — threat model only

Real-world reverse-proxy AitM kits set the baseline defenders test against. Do **not** deploy them on engagements; understand behavior to justify equivalent authorized infrastructure (Evilginx 3.x / Muraena / Modlishka) and to write realistic detections.

| Kit | Prime target | Distinguishing traits |
|-----|--------------|-----------------------|
| Tycoon 2FA (Storm-1747) | Microsoft 365 / Entra ID | Dominant PhaaS since 2023; disrupted March 2026 but capabilities redistributed; heavy anti-analysis JS, Cloudflare Turnstile, session cookie exfil post-MFA |
| Mamba 2FA | Microsoft 365 (Entra, consumer, SSO) | HTML-attachment lure -> Socket.IO relay to attacker backend; auto-tailors login page to victim tenant branding |
| Sneaky 2FA | Microsoft 365 | Reverse proxy with BitB overlay variant (2025); often behind Cloudflare pages |
| EvilProxy | O365/Google/Okta/GitHub | Historic PhaaS marketplace; templated multi-target reverse proxy |
| Rockstar 2FA / ONNX Store | O365 | Cheap subscription kits; Telegram-based operator dashboards |

Authorized substitution: Evilginx 3.x with a target-specific phishlet, or Muraena for automated rewrite of arbitrary targets.

## 2. Evilginx 3.x + GoPhish integration

Since Evilginx 3.3.0 (Apr 2024) an official GoPhish integration exists via the `kgretzky/gophish` fork. Use it when campaign lifecycle management (target list, template versioning, click stats) must flow through GoPhish while session capture happens in Evilginx.

- Build/install the forked GoPhish binary; standard `config.json` still applies.
- In Evilginx: `config gophish admin_url https://gophish.local:3333`, `config gophish api_key <key>`, `config gophish insecure true` if using self-signed admin TLS.
- Sending profile in GoPhish points at the AitM lure URL Evilginx generates (`lures edit <id> hostname ...`, `lures get-url <id>`).

Non-obvious knobs:
- `blacklist` — auto-blocks bot scanners; set `config blacklist unauth` for engagements or `all` to fail closed.
- `config redirect_url https://<benign>` — decoy for direct hits without a valid lure path.
- `config domains` and `config ipv4 external <addr>` — separate bind vs advertised IP when behind NAT.

## 3. OAuth 2.0 device code phishing

Storm-2372 has abused OAuth `urn:ietf:params:oauth:grant-type:device_code` since Aug 2024 to hijack M365/Entra sessions without a fake login page. Also viable against Google, GitHub, AWS IAM Identity Center.

Flow:
1. Attacker requests device code from real IdP (`POST /devicecode` with client_id of a trusted first-party app, e.g. Microsoft Authentication Broker).
2. IdP returns `user_code`, `device_code`, `verification_uri`.
3. Attacker sends the `user_code` and legit `verification_uri` to victim via chat/email under a plausible pretext (Teams meeting join, SSO re-auth, printer setup).
4. Victim authenticates and consents on the real IdP page.
5. Attacker polls `/token` with `device_code` and receives an access + refresh token bound to the victim.

Detection-relevant traits:
- Sign-in is genuine — no fake page, no reverse proxy, no lookalike domain to hunt.
- `user_code` lifetime is short (15 min typical); pretext must drive immediate action.
- Refresh token grants long-lived access to any resource the requested scope covers (Graph, EWS, Teams).

Simulation notes for authorized engagements:
- Use a first-party client_id that is allowed by the target tenant; verify Conditional Access does not block device code flow for that client.
- Document token scope, `oid`, `tid`, `appid` in evidence; revoke the refresh token at end of test.
- Register the pretext delivery channel with blue team if announced.

## 4. Browser-in-the-Browser (BitB)

Fake OAuth/SSO popup window rendered as HTML/CSS **inside** the phishing page, matching the victim OS chrome. Popularized 2022 (mrd0x); adopted by Sneaky2FA-style kits in 2025 for SSO providers.

- Only credible when victim expects a real popup (Google/Microsoft/Apple/GitHub OAuth).
- Address bar is faked in DOM — real browsers do not repaint it; screenshots look identical, click-behavior differs (cannot drag the fake window off the tab, address bar not editable).
- Pairs well with reverse-proxy AitM: BitB overlay captures perceived-legit consent, backend proxy relays for MFA.

Authorized delivery: host the HTML lure on the operator domain; do not mimic a domain outside RoE scope even inside the fake chrome.

## 5. Teams and Slack lateral phishing

External-tenant chat messages are now a routine initial-access channel.

Teams (Microsoft 365):
- Default tenant config allows external comms unless `AllowFederatedUsers` / `AllowTeamsConsumer*` are restricted.
- Storm-2372, Midnight Blizzard (2024), Black Basta affiliates used Teams to deliver device code prompts, malicious QuickAssist installs, or ClickFix scripts.
- Tools: `TeamsPhisher` (external-tenant DM + attachment bypass), `ConvoC2`.
- Evidence to collect: sender UPN, target UPN, message body, delivered file/URL, `TenantExternalTag`.

Slack:
- Enterprise Grid + Slack Connect DM allow cross-workspace messaging; abused via typo-squatted workspace names or compromised legit external partners.
- App install phishing: trick user into installing a hostile Slack app that requests broad scopes; refresh tokens rarely expire.

Pretext hygiene: always align with agreed RoE users; avoid consumer accounts unless explicitly in scope.

## 6. Quishing (QR phishing)

QR code embedded in image/PDF/email body defeats URL sandbox scanning by moving the click to the mobile device, which usually sits outside enterprise proxying.

- Encode the lure URL directly, or use a redirector-chain (bit.ly/short.io/legit-marketing-domain -> operator domain).
- Combine with AitM proxy: mobile session cookie is the payoff since mobile MFA prompts often auto-approve.
- Anti-analysis: rendered QR inside an SVG/PNG embedded in a signed PDF; some kits split the code across two images to defeat OCR.

## 7. ClickFix / paste-and-run

Social-engineering primitive first seen Oct 2023 as fake Cloudflare check; now used by APTs and PhaaS affiliates.

Flow:
1. Lure page shows fake "verify you are human" / "fix CAPTCHA" / "install missing font" prompt.
2. Instructs victim to press Win+R (or Cmd+Space) and paste a "verification code" — actually a PowerShell / mshta / bash one-liner already on the clipboard via JS.
3. Payload retrieves stage-2 loader from operator infrastructure.

Related variants: FileFix (drop file with hidden extension), fake reCAPTCHA, fake browser update.

For authorized simulation: measure paste-execution rate as a distinct metric from click-through; blue-team detections should look for `clipboardData.setData` + rapid `Win+R`/`powershell` execution in EDR telemetry.

## 8. Evidence and cleanup checklist

- Captured tokens: record `appid`, scope, `iss`, `oid`, `tid`, expiry; store encrypted; revoke at engagement close (`Revoke-MgUserSignInSession`, admin consent removal).
- AitM logs: preserve Evilginx `data.db`, phishlet YAML, redirector HTML, GoPhish campaign export.
- Domain and TLS: document registrar, WHOIS, ACME account; hand off or sinkhole per RoE.
- Screenshots of every fake UI element (BitB overlay, ClickFix prompt) for the report.
