---
name: social-engineering-technique
description: "Authorized simulation: social-engineering methodology; pretexts, email/voice/physical exercises, target research, metrics, scope controls."
license: MIT
compatibility: "Authorized social engineering engagements only; signed ROE required."
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
- AI voice/video cloning (2024+): treat any pretext impersonating a specific executive, colleague, or relative as a deepfake candidate. Publicly documented incidents include the Arup HK$200M ($25M) deepfake video-conference fraud (May 2024) and the July 2024 Ferrari CEO WhatsApp+voice-clone attempt foiled by an out-of-band verification question. FBI IC3 PSA I-120324 (Dec 2024) warns on cloned-voice financial fraud. For authorized simulation: pre-register the cloned voice profile with blue team, use a shared out-of-band verification word as safety net, and measure detection rate as a distinct metric.

### 5. Modern vectors (2024+)

Human-layer evolutions that must be modelled when the engagement authorizes multi-channel social engineering.

- **Callback phishing / TOAD (telephone-oriented attack delivery)**: benign-looking email (fake invoice, subscription renewal, DocuSign) with a callback number; live operator on the line talks the victim into installing a legitimate RMM (AnyDesk, Splashtop, Zoho Assist, ScreenConnect, Atera) for hands-on-keyboard access. Origin BazarCall 2021; still dominant in 2024–2025 via Luna Moth / Silent Ransom Group (UNC3753, Storm-0252) against US legal and financial firms. Measure: callback rate, RMM-install rate, mean time-to-hangup after security team is notified.
- **Help-desk MFA-reset vishing (post-number-matching evolution)**: since MS mandatory number-matching (Feb 2023) neutralised classic push-bombing, adversaries pivoted to calling the IT help desk impersonating a locked-out employee to force MFA re-registration, FIDO2 removal, or password reset. Scattered Spider / Octo Tempest / UNC3944 tradecraft — CISA AA23-320A + FBI/CISA 2025 update. Push-bombing still combined with vishing ("IT support here — approve the prompt so we can fix your ticket"). Test both channels: measure help-desk identity-verification bypass rate, and end-user prompt-approval rate under pretext.
- **Multi-channel chained pretexts**: email lure → SMS/WhatsApp follow-up from spoofed number → voice call from same identity. Cross-channel consistency defeats single-channel awareness training; report per-channel drop-off.
- **Quishing, BitB, OAuth device-code, ClickFix**: delivery vectors — see `phishing-technique/references/modern-aitm-tradecraft.md`.

### 6. Physical social engineering

- Pretexts: maintenance worker, delivery person, new employee, vendor.
- Techniques: tailgating, badge cloning, desk surfing, dumpster diving.
- Capture: badge numbers, access codes, document photos.

### 7. Campaign metrics

| Metric | Description | Industry baseline |
|--------|-------------|-------------------|
| Open rate | Recipients who opened | 30-50% |
| Click rate | Recipients who clicked | 10-25% |
| Credential submission | Recipients who entered creds | 5-15% |
| Payload execution | Recipients who ran attachment | 3-10% |
| Reporting rate | Reported to security | 5-15% (target >30%) |
| Time to first click | Elapsed from send to first click | Typically <5 min |

## Cross-references

- `phishing-technique` — email/AitM infrastructure, PhaaS threat model, quishing, BitB, OAuth device-code, ClickFix.
- `osint-technique` — target research feeding pretext development.
- `report-generation-technique` — turning campaign metrics into stakeholder-ready findings.
