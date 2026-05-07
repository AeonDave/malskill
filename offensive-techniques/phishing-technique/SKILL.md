---
name: phishing-technique
description: "Phishing infrastructure and campaign methodology for authorized red team engagements: domain reconnaissance (dnstwist), GoPhish campaign management, Evilginx2 adversary-in-the-middle setup, email authentication (SPF/DKIM/DMARC), template design, pretext development, and campaign metrics. Use when setting up phishing infrastructure, configuring Evilginx2 or GoPhish, or building phishing campaigns during authorized social engineering assessments."
license: MIT
compatibility: "Linux attack host; GoPhish, Evilginx2, Modlishka; authorized phishing simulations only"
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
- Need to set up GoPhish, Evilginx2, or Modlishka.
- Need domain reconnaissance for lookalike domains.
- Need to configure email authentication for deliverability.

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
- **Tool-family direction**: use reconnaissance and deliverability support first (`dnstwist`, mail-auth workflows), `gophish` for managed campaigns, and `evilginx2` or equivalent only when session interception is explicitly in scope.
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

### 3. Evilginx2 adversary-in-the-middle

Evilginx2 proxies the entire authentication flow, capturing session tokens and bypassing MFA.

```bash
# Configure phishlet for target service
# Set up domain with proper DNS (subdomain → attacker IP)
# Configure TLS certificate (Let's Encrypt)
# Start Evilginx2
evilginx2 -p ./phishlets -t ./templates
```

Phishlet configuration: proxy_pass, redirect_url, auth_tokens, session_cookies.

### 4. Email authentication for deliverability

- **SPF**: authorize sending IPs in TXT record.
- **DKIM**: sign emails with domain private key.
- **DMARC**: set policy (p=none initially, then quarantine/reject).
- Warm up sending IPs gradually.
- Test deliverability against target email gateway before launch.

### 5. Campaign metrics

| Metric | Description | Industry baseline |
|--------|-------------|-------------------|
| Open rate | Recipients who opened | 30-50% |
| Click rate | Recipients who clicked | 10-25% |
| Credential submission | Recipients who entered creds | 5-15% |
| Reporting rate | Reported to security | 5-15% (target >30%) |

## Resources

- `references/phishlet-examples.md` — Evilginx2 phishlet templates for common platforms.
- `references/campaign-templates.md` — email template patterns and landing page designs.
