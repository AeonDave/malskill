---
name: social-engineering-technique
description: "Social engineering methodology for authorized red team engagements: pretext development, phishing campaign design, vishing, physical social engineering, target research, and security awareness metrics. Use when planning social engineering campaigns, designing pretexts, or assessing human-factor security controls during authorized engagements."
license: MIT
compatibility: "Authorized social engineering engagements only; signed ROE required"
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-techniques
  language: multi
---

# Social Engineering Technique

Goal: assess organizational resilience to human-factor attacks through authorized, controlled social engineering campaigns.

## When this technique applies

- Engagement authorizes phishing, vishing, or physical social engineering.
- Need to design pretexts or campaign narratives.
- Need to measure and report on human-factor security metrics.

## Boundary

- **Phishing infrastructure**: `phishing-technique` (GoPhish, Evilginx2, domain setup).
- **OSINT for target research**: `osint-technique`.
- **Payload delivery**: `offensive-coding/shellcode-dev/`, `offensive-tools/exploits/metasploit/`.

## Authorization gate

Before any social engineering activity:
1. Signed ROE explicitly authorizing social engineering.
2. Confirmed target scope (which users, departments, locations).
3. Authorized techniques (email phishing? vishing? physical?).
4. Data handling policy for any information collected.
5. Emergency contacts and abort procedures.

## Initial triage

Before preparing a campaign, classify the human objective and the safest authorized channel for testing it.

- **Starting state**: is the assessment centered on phishing, vishing, physical access, pretext validation, or awareness metrics?
- **First questions**: what population is in scope, what behaviors are being tested, what realism level is allowed, and what evidence and safety controls are required?
- **Immediate actions**: confirm ROE, choose the scenario type, define pretext category and success criteria, then decide whether supporting infrastructure or OSINT depth is needed.
- **Tool-family direction**: use `osint-technique` and passive research first for target context, move to `phishing-technique` only when the scenario actually requires email or AitM infrastructure, and keep payload/delivery tools as a later support layer.
- **Escalation rule**: prefer the narrowest scenario that measures the control you care about; avoid stacking multiple deception channels without justification.

## Methodology

### 1. Target research

- LinkedIn: job titles, reporting structure, technology stack, group memberships.
- Corporate data: press releases, SEC filings, job postings, conference presentations.
- Technical footprint: email format, mail server vendor, email gateway.

### 2. Pretext development

Common trigger categories:
- **Authority**: impersonate IT, executive leadership, HR, legal, compliance.
- **Urgency**: password expiration, security alert, policy deadline, benefits enrollment.
- **Curiosity**: shared document, voicemail notification, package delivery, invoice.
- **Fear**: account suspension, policy violation notice, security incident.
- **Reward**: bonus notification, gift card, survey completion incentive.

### 3. Phishing campaigns

See `phishing-technique` for infrastructure setup. Key methodology decisions:
- Spear phishing vs. broad campaign (personalization vs. scale).
- Credential harvesting vs. malware delivery vs. MFA relay.
- Single-stage vs. multi-stage (pretext email → landing page → payload).

### 4. Vishing (voice phishing)

- Pretexts: IT support, vendor callback, survey, recruiter.
- Techniques: caller ID spoofing, warm transfer chains, callback numbers.
- Capture: voicemail PINs, VPN credentials, remote access codes.

### 5. Physical social engineering

- Pretexts: maintenance worker, delivery person, new employee, vendor.
- Techniques: tailgating, badge cloning, desk surfing, dumpster diving.
- Capture: badge numbers, access codes, document photos.

### 6. Campaign metrics

| Metric | Description | Industry baseline |
|--------|-------------|-------------------|
| Open rate | Recipients who opened | 30-50% |
| Click rate | Recipients who clicked | 10-25% |
| Credential submission | Recipients who entered creds | 5-15% |
| Payload execution | Recipients who ran attachment | 3-10% |
| Reporting rate | Reported to security | 5-15% (target >30%) |
| Time to first click | Elapsed from send to first click | Typically <5 min |

## Resources

- `references/pretext-library.md` — categorized pretext templates for phishing, vishing, and physical scenarios.
- `references/campaign-planning.md` — campaign design worksheet and metrics tracking template.
