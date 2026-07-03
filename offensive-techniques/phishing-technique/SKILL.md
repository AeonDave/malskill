---
name: phishing-technique
description: "Authorized simulation: email/social campaign infrastructure; domain hygiene, SPF/DKIM/DMARC, GoPhish/Evilginx planning, metrics."
license: MIT
compatibility: "GoPhish/Evilginx 3.x/Muraena/Modlishka planning context; modern AitM PhaaS kits (Tycoon2FA, Mamba2FA, Sneaky2FA, EvilProxy) are threat-model only, not offensive tooling. Authorized email/social simulations only."
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-techniques
  language: multi
---

# Phishing Technique

Goal: design, configure, and operate phishing infrastructure that models real adversary tradecraft while staying inside written rules of engagement.

## When this technique applies

- Engagement authorizes phishing or social engineering.
- Need to set up GoPhish, Evilginx (v3.x), Muraena, or Modlishka.
- Need domain reconnaissance for lookalike domains.
- Need to configure email authentication for deliverability.
- Need MFA/session interception via AitM proxy, device code flow abuse, or Browser-in-the-Browser when explicitly authorized.

## Boundary

- **Pretext design and awareness training**: `social-engineering-technique`.
- **Payload generation**: `offensive-coding/shellcode-dev/`, `offensive-tools/exploits/metasploit/`.
- **Post-exploitation**: `post-exploit-technique`.

## Authorization gate

Before generating any live-target infrastructure configuration, confirm:
1. Engagement ID and signed ROE.
2. Target scope (domains, IP ranges, user populations).
3. Authorized techniques (credential harvesting? MFA relay? session token capture?).
4. Infrastructure ownership (domains registered by/for client?).
5. Blue team notification status (blind or announced?).
6. Data handling (retention and destruction policy for captured credentials).

If any are missing, produce configuration as lab reference only.

## Initial triage

Before building infrastructure, classify the engagement objective and the minimum campaign design needed to test it safely.

- **Starting state**: is the goal credential capture, MFA/session interception, awareness measurement, or delivery of a broader social-engineering scenario?
- **First questions**: what techniques are authorized, what population is in scope, what level of realism is required, and what evidence is needed for success?
- **Immediate actions**: validate ROE, choose campaign type, decide whether lookalike domains, mail delivery, or AitM infrastructure are actually required, then build only that slice.
- **Tool-family direction**: use reconnaissance and deliverability support first (`dnstwist`, mail-auth workflows), `gophish` for managed campaigns, and `evilginx` (v3.x) or `muraena` only when session interception is explicitly in scope. Real-world PhaaS kits (Tycoon2FA, Mamba2FA, Sneaky2FA, EvilProxy) inform threat modelling; they are not authorized offensive tooling.
- **Escalation rule**: start with the least invasive infrastructure that can answer the assessment question.

## Methodology

### 1. Domain reconnaissance with dnstwist

```bash
# Generate all permutations and resolve
dnstwist --registered example.com

# Show only live domains with MX records
dnstwist --registered --mxcheck example.com

# Homoglyph-only (Unicode lookalikes)
dnstwist --registered --homoglyphs example.com

# Broad scan with GeoIP and banner grabbing
dnstwist --registered --geoip --banners example.com
```

Focus on: registered domains with A records that also have MX records. Flag any that serve content with high ssdeep similarity to the target.

### 2. GoPhish campaign setup

GoPhish provides campaign management, email delivery, click tracking, and credential capture.

Key configuration steps:
- Configure sending profiles (SMTP relays, API-based senders).
- Design landing pages (clone target login, capture creds, redirect to legitimate site).
- Create email templates (authority/urgency/curiosity triggers).
- Define groups and launch campaign.
- Monitor metrics: open rate, click rate, credential submission rate, reporting rate.

### 3. Evilginx (v3.x) adversary-in-the-middle

Evilginx proxies the entire authentication flow, capturing credentials and post-MFA session cookies. Upstream repo is still `kgretzky/evilginx2` but current major is v3.x and the binary is `evilginx`. v3.3+ ships an official GoPhish integration (`kgretzky/gophish` fork).

```bash
# DNS: wildcard subdomain -> attacker IP; open 80/443
# TLS: Let's Encrypt handled automatically by Evilginx
# Layout: ./phishlets (YAML) and ./redirectors (HTML lures)
sudo ./evilginx -p ./phishlets -t ./redirectors
```

Phishlet YAML keys (v1.x format, still current for the community build): `proxy_hosts`, `sub_filters`, `auth_tokens`, `credentials`, `login`, `landing_path`, `js_inject`, `auth_urls`. Evilginx Pro 5.0.0 introduces Phishlets 2.0 with a `landing_url` field and structured request/response transformations.

### 4. Modern AitM and non-email vectors (2024+ tradecraft)

Covered in depth in `references/modern-aitm-tradecraft.md`. Load when authorization includes MFA/session interception, OAuth device code abuse, Browser-in-the-Browser, Teams/Slack lateral phishing, quishing, or ClickFix-style paste-and-run lures.

### 5. Email authentication for deliverability

- **SPF**: authorize sending IPs in TXT record.
- **DKIM**: sign emails with domain private key.
- **DMARC**: set policy (p=none initially, then quarantine/reject).
- Warm up sending IPs gradually.
- Test deliverability against target email gateway before launch.

### 6. Campaign metrics

| Metric | Description | Industry baseline |
|--------|-------------|-------------------|
| Open rate | Recipients who opened | 30-50% |
| Click rate | Recipients who clicked | 10-25% |
| Credential submission | Recipients who entered creds | 5-15% |
| Reporting rate | Reported to security | 5-15% (target >30%) |

## Resources

- `references/modern-aitm-tradecraft.md` — 2024+ tradecraft: AitM PhaaS kit landscape, OAuth device code phishing, BitB, Teams/Slack lateral phishing, quishing, ClickFix.
